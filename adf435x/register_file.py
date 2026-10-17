"""The register file: the six register words wanted, and those last written.

A register is stale when its encoded word differs from the word last
written. ``commit_plan()`` lists the stale words in write order, R5 first,
and adds an R0 write when a double-buffered field needs it to take effect
(data sheet p.12). The register file does no I/O: after writing the plan,
call ``mark_written()``, or ``mark_write_failed()`` if the write raised.
See docs/api-guide.md.
"""

from . import consts
from .config import ADF435xConfig, FIELD_REGISTER
from .profiles import ADF435xProfile
from .register_mapper import ADF435xRegisterMapper


class ADF435xRegisterFile:
    """
    Register state for one chip, and the writes needed to update it.

    Parameters
    ----------
    profile : ADF435xProfile
        The part to encode for.
    config : ADF435xConfig, optional
        Starting configuration (default: a new ``ADF435xConfig``). Do not
        share one config object between register files.
    """

    NUM_REGISTERS = consts.NUM_REGISTERS

    # Registers whose double-buffered fields always wait for R0.
    _DBR_REGISTERS = frozenset(consts.DBR_REGISTER_INDICES)

    def __init__(self, profile: ADF435xProfile, config=None) -> None:
        """Check the starting config and encode all six words."""
        self._mapper = ADF435xRegisterMapper(profile)
        self._config = config if config is not None else ADF435xConfig()
        self._current = [0] * self.NUM_REGISTERS
        # None means never written, so every register starts out stale.
        self._last_written = [None] * self.NUM_REGISTERS
        self._commit_count = 0
        self._config_version = 0
        self._mapper.validate_config(self._config)
        self._recompute()

    # -- configuration -------------------------------------------------------

    @property
    def config(self) -> ADF435xConfig:
        """The live ``ADF435xConfig``.

        Setting its attributes directly skips all checks; use ``configure()``.
        """
        return self._config

    @property
    def config_version(self) -> int:
        """Number of successful ``configure()`` calls.

        A frequency table compares it with the value it last saw to tell
        whether its stored words are out of date. ``load_words()``
        does not change it.
        """
        return self._config_version

    def configure(self, **fields) -> None:
        """Set the given fields, check them, and re-encode.

        All or nothing: if any check fails (usually with ``ValueError``),
        every field is put back and the error is raised again. An unknown
        field name raises ``AttributeError``.
        """
        for name in fields:
            if name not in FIELD_REGISTER:
                raise AttributeError("unknown configuration field: %s" % name)
        previous = {name: getattr(self._config, name) for name in fields}
        dirty = {FIELD_REGISTER[name] for name in fields}
        # Set every value before checking, so rules that span fields (such as
        # INT against the prescaler minimum) see the final values.
        for name, value in fields.items():
            setattr(self._config, name, value)
        try:
            self._mapper.validate_config(self._config, only=frozenset(fields))
            self._recompute(dirty)
        except Exception:
            for name, value in previous.items():
                setattr(self._config, name, value)
            self._recompute()
            raise
        self._config_version += 1

    def _recompute(self, dirty=None) -> None:
        """Re-encode the registers in *dirty*, or all six if it is None.

        Does not check values; callers have already done so.
        """
        m = self._mapper
        c = self._config
        indices = range(self.NUM_REGISTERS) if dirty is None else dirty
        for index in indices:
            self._current[index] = m.encode_register(index, c)

    def load_words(self, fields, words) -> None:
        """Store *fields* and their six encoded *words* without checking.

        For values checked and encoded earlier, such as frequency table
        entries, so playback can skip both steps. *words* (R0 first) must be
        the encoding of the config after *fields* are set; if not, later
        ``configure()`` calls start from a config that does not match the
        chip. Raises ``AttributeError`` for an unknown field and
        ``ValueError`` unless there are exactly six words.
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
        """Return a copy of the six wanted register words, R0 first."""
        return list(self._current)

    # -- staleness -----------------------------------------------------------

    def stale_indices(self) -> list:
        """Return the indices of stale registers, in ascending order.

        A register never written counts as stale.
        """
        return [
            i
            for i in range(self.NUM_REGISTERS)
            if self._current[i] != self._last_written[i]
        ]

    def is_stale(self) -> bool:
        """True if any register needs writing."""
        return bool(self.stale_indices())

    def dump(self) -> dict:
        """Return a dict of the register state, for printing while debugging.

        It holds ``commit_count``, ``is_stale``, and a ``registers`` list with
        each register's wanted word, last-written word and stale flag.
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
        """True if DB13 is set in the wanted R2 word.

        When only R4 is stale, the wanted and last-written R2 words have the
        same DB13, so this is also the setting the chip is using.
        """
        r2_word = self._current[consts.REG2_ADDR]
        return bool((r2_word >> consts.REG2_DOUBLE_BUFFER_POS) & 1)

    def _commit_stale_set(self, stale: set) -> set:
        """Return *stale*, plus R0 if a double-buffered change needs it.

        R0 is added when R1 or R2 changed, or when R4 changed while R2 DB13
        is set.
        """
        if stale & self._DBR_REGISTERS:
            stale = set(stale)
            stale.add(consts.REG0_ADDR)
        elif consts.REG4_ADDR in stale and self._r4_divider_double_buffered():
            stale = set(stale)
            stale.add(consts.REG0_ADDR)
        return stale

    def commit_plan(self) -> list[int]:
        """Return the words to write, R5 first, or [] if nothing is stale.

        Only stale registers are included, plus R0 when a double-buffered
        change needs it. Call ``mark_written()`` once they are written.
        """
        stale = set(self.stale_indices())
        if not stale:
            return []
        stale = self._commit_stale_set(stale)
        return [self._current[i] for i in sorted(stale, reverse=True)]

    def full_plan(self) -> list[int]:
        """Return all six words, R5 first, for power-up or a full rewrite."""
        return [self._current[i] for i in range(self.NUM_REGISTERS - 1, -1, -1)]

    def mark_written(self) -> None:
        """Record that the wanted words are now on the chip."""
        self._last_written = list(self._current)
        self._commit_count += 1

    def mark_write_failed(self) -> None:
        """Forget what was last written, after a failed write.

        Every register is then stale, so the next ``commit_plan()`` rewrites
        all six.
        """
        self._last_written = [None] * self.NUM_REGISTERS
