"""
Register file for the ADF435x family. Tracks the desired configuration and the
words last written to the device, and computes the minimal ordered set of writes
needed to bring the device up to date.

Staleness is derived by diffing the freshly encoded words against the
last-written words, so it can't disagree with a hand-kept flag. Committing is
optimistic: commit and commit_all return the words to write and advance the
last-written cache in the same call. The device is write-only, so a write that
returns without raising is the only confirmation available; if a write raises,
the device state is unknown and you re-program with commit_all.

Double-buffer latching (datasheet Figure 23):
- R1 (phase, modulus) and R2 (R counter, ref doubler/div-by-2, CP current)
  latch on a write to R0 (DBR).
- R4 RF divider select latches on R0 only when R2 DB13 (``double_buffer``)
  is set (DBB). That DB13 state is read from the encoded R2 word, not a
  separate flag, so it stays consistent with the diffed words.
When any of these registers change, commit adds an R0 write even if R0 itself
is unchanged, so the new values take effect.
"""

from . import consts
from .config import ADF435xConfig, FIELD_REGISTER
from .profiles import ADF435xDeviceProfile
from .register_mapper import ADF435xRegisterMapper


class ADF435xRegisterFile:
    """
    Track register state and emit ordered write transactions.

    Parameters
    ----------
    profile : ADF435xDeviceProfile
        Target device; selects the mapper used to encode the configuration.
    config : ADF435xConfig, optional
        Initial configuration. A default ADF435xConfig is used if omitted.
    """

    NUM_REGISTERS = consts.NUM_REGISTERS

    # R1 and R2 are fully double-buffered (DBR); R4 divider is DBB when
    # config.double_buffer is set. See module docstring.
    _DBR_REGISTERS = frozenset(consts.DBR_REGISTER_INDICES)

    def __init__(self, profile: ADF435xDeviceProfile, config=None) -> None:
        self._mapper = ADF435xRegisterMapper(profile)
        self._config = config if config is not None else ADF435xConfig()
        self._current = [0] * self.NUM_REGISTERS
        # None means never written, so every register starts stale.
        self._last_written = [None] * self.NUM_REGISTERS
        self._commit_count = 0
        self._recompute()

    # -- configuration -------------------------------------------------------

    @property
    def config(self) -> ADF435xConfig:
        """The current configuration."""
        return self._config

    def configure(self, **fields) -> None:
        """Update configuration fields and re-encode.

        The update is transactional: if encoding fails (for example, requesting
        a capability the device lacks), every field is restored and the error
        re-raised, leaving the file unchanged.

        Parameters
        ----------
        **fields
            Field name/value pairs, each matching an ADF435xConfig attribute.

        Raises
        ------
        AttributeError
            If a field name is not a known configuration field.
        ValueError
            If the new configuration cannot be encoded. The file is rolled back
            first.
        """
        for name in fields:
            if name not in FIELD_REGISTER:
                raise AttributeError("unknown configuration field: %s" % name)
        previous = {name: getattr(self._config, name) for name in fields}
        dirty = {FIELD_REGISTER[name] for name in fields}
        for name, value in fields.items():
            setattr(self._config, name, value)
        try:
            self._recompute(dirty)
        except ValueError:
            for name, value in previous.items():
                setattr(self._config, name, value)
            self._recompute()
            raise

    def _recompute(self, dirty=None) -> None:
        """Encode configuration into ``_current``.

        Parameters
        ----------
        dirty : set of int or None
            Register indices to re-encode. ``None`` encodes all six (initial
            load and rollback recovery).
        """
        m = self._mapper
        c = self._config
        if dirty is None:
            for i, word in enumerate(m.encode_config(c)):
                self._current[i] = word
            return
        if dirty & {consts.REG0_ADDR, consts.REG1_ADDR}:
            m.check_pll(c.int_n, c.frac, c.mod, c.prescaler)
        for index in dirty:
            self._current[index] = m._encode_register_at(c, index)

    def _update_current(self, words) -> None:
        """Replace the current (desired) words.

        Raises
        ------
        ValueError
            If the wrong number of words is supplied.
        """
        if len(words) != self.NUM_REGISTERS:
            raise ValueError(
                "expected %d words, got %d" % (self.NUM_REGISTERS, len(words)))
        self._current = list(words)

    def current_words(self) -> list:
        """A copy of the six current (desired) register words."""
        return list(self._current)

    # -- staleness -----------------------------------------------------------

    def stale_indices(self) -> list:
        """Register indices whose current word differs from the last written
        one, ascending.
        """
        return [i for i in range(self.NUM_REGISTERS)
                if self._current[i] != self._last_written[i]]

    def is_stale(self) -> bool:
        """True if any register needs writing."""
        return bool(self.stale_indices())

    def dump(self) -> dict:
        """A snapshot of register state for inspection.

        Returns
        -------
        dict
            ``commit_count``, ``is_stale``, and a ``registers`` list giving each
            register's current word, last-written word, and stale flag.
        """
        return {
            "commit_count": self._commit_count,
            "is_stale": self.is_stale(),
            "registers": [
                {"index": i,
                 "current": self._current[i],
                 "last_written": self._last_written[i],
                 "stale": self._current[i] != self._last_written[i]}
                for i in range(self.NUM_REGISTERS)
            ],
        }

    # -- transactions --------------------------------------------------------

    def _r4_divider_double_buffered(self) -> bool:
        """Whether the R4 RF-divider field is double-buffered.

        The state is read from R2 DB13 in the current R2 word rather than a
        separate flag, so the latch decision is derived from the same encoded
        words as staleness and cannot disagree with them (see module
        docstring). When only R4 is stale, the current and last-written R2
        words share the same DB13, so this matches the bit in effect on the
        device when R4 is written.

        Returns
        -------
        bool
            True if R2 DB13 (``double_buffer``) is set in the current R2 word.
        """
        r2_word = self._current[consts.REG2_ADDR]
        return bool((r2_word >> consts.REG2_DOUBLE_BUFFER_POS) & 1)

    def _commit_stale_set(self, stale: set) -> set:
        """Expand *stale* so R0 is included when a latch write is required.

        Parameters
        ----------
        stale : set
            Register indices that differ from the last-written cache.

        Returns
        -------
        set
            The stale set, with R0 added when R1 or R2 changed, or when R4
            changed while the R4 divider is double-buffered (R2 DB13 set).
        """
        if stale & self._DBR_REGISTERS:
            stale = set(stale)
            stale.add(consts.REG0_ADDR)
        elif consts.REG4_ADDR in stale and self._r4_divider_double_buffered():
            stale = set(stale)
            stale.add(consts.REG0_ADDR)
        return stale

    def commit(self) -> list:
        """The minimal set of writes to bring the device up to date.

        Stale registers are returned as (index, word) pairs ordered R5 down to
        R0, so R0 is written last. If a double-buffered register changed (R1,
        R2, or R4 with ``double_buffer`` enabled), R0 is added so its write
        latches the buffered fields. The last-written cache is advanced here,
        assuming the words are written to the device next.

        Returns
        -------
        list of (int, int)
            (register_index, word) pairs in write order, empty if nothing is
            stale.
        """
        stale = set(self.stale_indices())
        if not stale:
            return []
        stale = self._commit_stale_set(stale)
        plan = [(i, self._current[i]) for i in sorted(stale, reverse=True)]
        self._last_written = list(self._current)
        self._commit_count += 1
        return plan

    def commit_all(self) -> list:
        """All six words as the full power-up transaction, ordered R5 down to R0.

        Ignores staleness and always emits every register, for initial
        programming and for recovery after a failed write. Advances the
        last-written cache like commit.

        Returns
        -------
        list of (int, int)
            All six (register_index, word) pairs, R5 down to R0.
        """
        plan = [(i, self._current[i])
                for i in range(self.NUM_REGISTERS - 1, -1, -1)]
        self._last_written = list(self._current)
        self._commit_count += 1
        return plan