"""
Register file for the ADF435x family. Tracks the desired configuration and the
words last written to the device, and computes the minimal ordered set of writes
needed to bring the device up to date.

Staleness is derived by diffing the freshly encoded words against the
last-written words, so it can't disagree with a hand-kept flag.

``commit_plan()`` returns the register words to write (R5 down to R0) without
updating the last-written cache. After a successful device write, call
``mark_written()``; if the write fails, call ``mark_write_failed()`` and
reprogram with ``commit_all_plan()``. The register file never performs I/O.

Double-buffer latching (data sheet p.12, Figure 23):
- R1 (phase, modulus) and R2 (R counter, ref doubler/div-by-2, CP current)
  latch on a write to R0 (DBR). Their other bits take effect immediately; the
  register file adds the R0 write whenever R1 or R2 changes, which is always
  safe.
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
        """Build the mapper, validate the config, and encode initial words."""
        self._mapper = ADF435xRegisterMapper(profile)
        self._config = config if config is not None else ADF435xConfig()
        self._current = [0] * self.NUM_REGISTERS
        # None means never written, so every register starts stale.
        self._last_written = [None] * self.NUM_REGISTERS
        self._commit_count = 0
        self._config_version = 0
        self._mapper.validate_config(self._config)
        self._recompute()

    # -- configuration -------------------------------------------------------

    @property
    def config(self) -> ADF435xConfig:
        """The current configuration.

        Returns
        -------
        ADF435xConfig
            The live configuration object. Mutating it directly bypasses
            validation; prefer ``configure()``.
        """
        return self._config

    @property
    def config_version(self) -> int:
        """Count of successful ``configure()`` calls.

        Lets callers holding words encoded from an earlier configuration (for
        example a precomputed frequency table) detect that settings changed.
        ``load_prevalidated()`` does not advance it.
        """
        return self._config_version

    def configure(self, **fields) -> None:
        """Update configuration fields and re-encode.

        The update is transactional: if validation fails (for example,
        requesting a capability the device lacks), every field is restored and
        the error re-raised, leaving the file unchanged.

        Parameters
        ----------
        **fields
            Field name/value pairs, each matching an ADF435xConfig attribute.

        Raises
        ------
        AttributeError
            If a field name is not a known configuration field.
        Exception
            If the new configuration fails validation. The most common cause is
            a ValueError (out-of-range or unsupported value), but any failure
            during validation is treated the same way: every field is restored
            and the original error re-raised, leaving the file unchanged.
        """
        for name in fields:
            if name not in FIELD_REGISTER:
                raise AttributeError("unknown configuration field: %s" % name)
        previous = {name: getattr(self._config, name) for name in fields}
        dirty = {FIELD_REGISTER[name] for name in fields}
        # Apply all new values before validating so cross-field rules (PLL,
        # prescaler vs INT) see the final state.
        for name, value in fields.items():
            setattr(self._config, name, value)
        try:
            self._mapper.validate_config(self._config, only=frozenset(fields))
            # Encode only; bitfield ranges were checked above.
            self._recompute(dirty)
        except Exception:
            # Roll back every touched field and re-encode the restored config.
            for name, value in previous.items():
                setattr(self._config, name, value)
            self._recompute()
            raise
        self._config_version += 1

    def _recompute(self, dirty=None) -> None:
        """Encode configuration into ``_current``.

        Parameters
        ----------
        dirty : set of int or None
            Register indices to re-encode. ``None`` encodes all six (initial
            load and rollback recovery).

        Notes
        -----
        Encode only. Bitfield validation runs at init and ``configure()``;
        this path does not call ``validate_config``.
        """
        m = self._mapper
        c = self._config
        indices = (
            range(self.NUM_REGISTERS) if dirty is None else dirty
        )
        for index in indices:
            self._current[index] = m.encode_register(index, c)

    def load_prevalidated(self, fields, words) -> None:
        """Set fields and their encoded words without validating or encoding.

        For configurations validated and encoded earlier, such as frequency
        table entries built at setup, so playback skips both steps.

        Parameters
        ----------
        fields : dict
            Field name/value pairs to store on the config. Must already be
            valid for this profile.
        words : sequence of int
            Exactly ``NUM_REGISTERS`` words, R0..R5, that encode the config
            *after* *fields* are applied. The caller guarantees this; a
            mismatch makes later ``configure()`` calls re-encode from a
            config that disagrees with what was written.

        Raises
        ------
        AttributeError
            If a field name is unknown.
        ValueError
            If the wrong number of words is supplied.
        """
        if len(words) != self.NUM_REGISTERS:
            raise ValueError(
                "expected %d words, got %d" % (self.NUM_REGISTERS, len(words))
            )
        for name in fields:
            if name not in FIELD_REGISTER:
                raise AttributeError("unknown configuration field: %s" % name)
        for name, value in fields.items():
            setattr(self._config, name, value)
        self._current = list(words)

    def current_words(self) -> list:
        """Return a copy of the six current (desired) register words.

        Returns
        -------
        list of int
            The current words in index order R0..R5. A copy, so callers may
            mutate it freely.
        """
        return list(self._current)

    # -- staleness -----------------------------------------------------------

    def stale_indices(self) -> list:
        """Return register indices that differ from the last-written words.

        Returns
        -------
        list of int
            Indices whose current word differs from the last-written one, in
            ascending order. Registers never written count as stale.
        """
        return [
            i
            for i in range(self.NUM_REGISTERS)
            if self._current[i] != self._last_written[i]
        ]

    def is_stale(self) -> bool:
        """Report whether any register needs writing.

        Returns
        -------
        bool
            True if at least one register is stale.
        """
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
                {
                    "index": i,
                    "current": self._current[i],
                    "last_written": self._last_written[i],
                    "stale": self._current[i] != self._last_written[i],
                }
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
        # R1 and R2 latch on any R0 write (DBR). R4 divider latches on R0 only
        # when R2 DB13 (double_buffer) is set (DBB).
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
        return [self._current[i] for i in range(self.NUM_REGISTERS - 1, -1, -1)]

    def mark_written(self) -> None:
        """Record that the planned words were successfully written to the device."""
        self._last_written = list(self._current)
        self._commit_count += 1

    def mark_write_failed(self) -> None:
        """Discard the last-written cache after a failed device write.

        Every register then counts as stale, so the next ``commit_plan()`` is
        a full reprogram.
        """
        self._last_written = [None] * self.NUM_REGISTERS
