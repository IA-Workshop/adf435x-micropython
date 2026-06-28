"""
Register file for the ADF435x family. Tracks the desired configuration and the
words last written to the device, and computes the minimal ordered set of writes
needed to bring the device up to date.

Staleness is derived by diffing the freshly encoded words against the
last-written words, so it can't disagree with a hand-kept flag.

``commit_plan()`` returns the register words to write (R5 down to R0) without
updating the last-written cache. ``commit()`` is the optimistic shortcut:
``commit_plan()`` followed by ``mark_written()``. After a successful device
write, call ``mark_written()``; if the write fails, call ``mark_write_failed()``
and reprogram with ``commit_all()``.

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
        Initial configuration. A default ``ADF435xConfig`` is used if omitted.
        Do not share one config instance across multiple register files.
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
        Exception
            If the new configuration cannot be encoded. The most common cause is
            a ValueError (out-of-range or unsupported value), but any failure
            during encoding (for example, a TypeError from a wrong-typed value)
            is treated the same way: every field is restored and the original
            error re-raised, leaving the file unchanged.
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
        except Exception:
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

    def commit_plan(self) -> list[int]:
        """Register words to write, ordered R5 down to R0, without updating cache.

        Returns
        -------
        list of int
            32-bit register words in SPI write order. Empty if nothing is stale.
            Register address is in DB2:DB0 of each word.
        """
        stale = set(self.stale_indices())
        if not stale:
            return []
        stale = self._commit_stale_set(stale)
        return [self._current[i] for i in sorted(stale, reverse=True)]

    def commit_all_plan(self) -> list[int]:
        """All six register words, R5 down to R0, without updating cache.

        Returns
        -------
        list of int
            Full power-up / recovery transaction.
        """
        return [self._current[i]
                for i in range(self.NUM_REGISTERS - 1, -1, -1)]

    def mark_written(self) -> None:
        """Record that the planned words were successfully written to the device."""
        self._last_written = list(self._current)
        self._commit_count += 1

    def mark_write_failed(self) -> None:
        """Discard the last-written cache after a failed device write.

        Call before ``commit_all()`` to force a full reprogram.
        """
        self._last_written = [None] * self.NUM_REGISTERS

    invalidate = mark_write_failed

    def commit(self) -> list[int]:
        """Minimal write transaction, advancing the last-written cache.

        Equivalent to ``commit_plan()`` followed by ``mark_written()`` when
        the plan is non-empty.

        Returns
        -------
        list of int
            Register words in SPI write order (R5 down to R0).
        """
        plan = self.commit_plan()
        if plan:
            self.mark_written()
        return plan

    def commit_all(self) -> list[int]:
        """Full six-word transaction, advancing the last-written cache.

        Returns
        -------
        list of int
            All register words in SPI write order (R5 down to R0).
        """
        plan = self.commit_all_plan()
        self.mark_written()
        return plan