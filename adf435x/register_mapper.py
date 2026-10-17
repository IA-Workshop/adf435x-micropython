"""Check field values and encode them into the six 32-bit register words.

Both jobs are driven by the field table, ``config.FIELDS``, plus the
cross-field rules below. Checking and encoding are separate steps:
``validate_config()`` runs when values are set, and ``encode_register()``
assumes they are legal and only masks each field to its width. Register
maps: data sheet Figures 23 to 29 (pp.14 to 17).
"""

from . import consts
from .config import (
    BOOL,
    CAPABILITY,
    DIVIDER,
    ENUM,
    FIELD_NAMES,
    FIELD_SPECS,
    FIELDS,
    KIND,
    ALLOWED,
    LABEL,
    NAME,
    POS,
    REG,
    UINT,
    WIDTH,
    ADF435xConfig,
)
from .profiles import ADF435xDeviceProfile

# How each profile feature is named in error messages.
_CAPABILITY_TEXT = {
    "has_phase_adjust": "phase adjust",
    "has_fast_band_select": "fast band select",
    "has_charge_cancel": "charge cancellation",
}

# Bits every word of each register carries: its address in DB2:DB0, and
# for R5 the reserved ones.
_FIXED_BITS = (
    consts.REG0_ADDR,
    consts.REG1_ADDR,
    consts.REG2_ADDR,
    consts.REG3_ADDR,
    consts.REG4_ADDR,
    consts.REG5_RESERVED_ONES | consts.REG5_ADDR,
)

# Data sheet limits used by the rules below.
_LOW_SPUR_MOD_MIN = 50  # p.23
_FAST_BAND_CLK_DIV_MAX = 254  # p.19


def _rule_pll(profile, c):
    """Check the MOD range, FRAC < MOD, and the INT range for the prescaler."""
    if c.mod < profile.mod_min:
        raise ValueError("MOD=%d below minimum %d" % (c.mod, profile.mod_min))
    if c.mod > profile.mod_max:
        raise ValueError("MOD=%d above maximum %d" % (c.mod, profile.mod_max))
    if c.frac >= c.mod:
        raise ValueError("FRAC=%d must be less than MOD=%d" % (c.frac, c.mod))
    if c.prescaler == consts.REG1_PRESCALER_4_5:
        int_min = profile.int_min_4_5
    elif c.prescaler == consts.REG1_PRESCALER_8_9:
        int_min = profile.int_min_8_9
    else:
        raise ValueError("prescaler=%d invalid" % c.prescaler)
    if c.int_n < int_min:
        raise ValueError("INT=%d below minimum %d for prescaler" % (c.int_n, int_min))
    if c.int_n > profile.int_max:
        raise ValueError("INT=%d above maximum %d" % (c.int_n, profile.int_max))


def _rule_phase(profile, c):
    """The phase word must be less than MOD (data sheet p.18)."""
    if c.phase >= c.mod:
        raise ValueError("phase=%d must be less than MOD=%d" % (c.phase, c.mod))


def _rule_low_spur(profile, c):
    """Low-spur noise mode needs MOD >= 50 (data sheet p.23)."""
    if c.noise_mode == consts.REG2_LOW_SPUR and c.mod < _LOW_SPUR_MOD_MIN:
        raise ValueError(
            "low-spur noise mode needs MOD >= %d (MOD=%d)" % (_LOW_SPUR_MOD_MIN, c.mod)
        )


def _rule_fast_band_clk(profile, c):
    """Fast band-select mode allows a divider of at most 254 (p.19)."""
    if (
        c.band_clk_mode == consts.REG3_BAND_CLK_HIGH
        and c.band_clk_div > _FAST_BAND_CLK_DIV_MAX
    ):
        raise ValueError(
            "band select clock divider=%d above maximum %d in fast mode"
            % (c.band_clk_div, _FAST_BAND_CLK_DIV_MAX)
        )


def _rule_muxout(profile, c):
    """The N-divider output on MUXOUT stops VCO band select (p.18)."""
    if c.muxout == consts.REG2_MUX_NDIVIDER:
        raise ValueError(
            "MUXOUT N-divider output is not supported: it stops VCO band select"
        )


# (trigger fields, rule). A rule runs when any of its trigger fields is
# checked, so changing one field re-checks the fields it depends on.
_RULES = (
    (("int_n", "frac", "mod", "prescaler"), _rule_pll),
    (("phase", "mod"), _rule_phase),
    (("noise_mode", "mod"), _rule_low_spur),
    (("band_clk_mode", "band_clk_div"), _rule_fast_band_clk),
    (("muxout",), _rule_muxout),
)


class ADF435xRegisterMapper:
    """
    Check and encode register words for one part (an ``ADF435xDeviceProfile``).

    ``encode_register()`` assumes valid input. Call ``validate_config()``
    first on any config that did not come through ``ADF435xRegisterFile``.
    """

    def __init__(self, profile: ADF435xDeviceProfile):
        """Store *profile* and build the per-register encode layout."""
        self._profile = profile

        # For each register, (name, pos, mask, kind) of every field in it.
        # Without a settable ABP, DB22 is reserved and stays 0.
        layout = [[] for _ in range(consts.NUM_REGISTERS)]
        for spec in FIELDS:
            if spec[NAME] == "abp" and not profile.has_programmable_abp:
                continue
            mask = (1 << spec[WIDTH]) - 1
            layout[spec[REG]].append((spec[NAME], spec[POS], mask, spec[KIND]))
        self._layout = tuple(tuple(fields) for fields in layout)

    @property
    def profile(self) -> ADF435xDeviceProfile:
        """The part this mapper encodes for."""
        return self._profile

    # -- validation ----------------------------------------------------------

    def _check_field(self, spec, value) -> None:
        """Check one value against its field spec and the profile."""
        name, kind, label = spec[NAME], spec[KIND], spec[LABEL]
        if kind == BOOL:
            if value not in (0, 1):
                raise ValueError("%s=%s must be True or False" % (label, value))
        elif not isinstance(value, int):
            raise ValueError("%s=%s must be an integer" % (label, value))
        elif kind == UINT:
            if value < 0 or value >= 1 << spec[WIDTH]:
                raise ValueError(
                    "%s=%d does not fit in %d bits" % (label, value, spec[WIDTH])
                )
            if value < spec[ALLOWED]:
                raise ValueError(
                    "%s=%d below minimum %d" % (label, value, spec[ALLOWED])
                )
        elif kind == ENUM:
            if value not in spec[ALLOWED]:
                raise ValueError("%s=%d invalid" % (label, value))
        elif kind == DIVIDER:
            self._profile.divider_code(value)

        # A feature the part lacks must be left off (zero).
        cap = spec[CAPABILITY]
        if cap is not None and value and not getattr(self._profile, cap):
            raise ValueError(
                "%s does not support %s" % (self._profile.name, _CAPABILITY_TEXT[cap])
            )

    def validate_config(self, config: ADF435xConfig, *, only=None) -> None:
        """Raise ``ValueError`` if any value in *config* is illegal.

        With *only* set to a set of field names, check just those fields and
        every rule that involves one of them. Changing only ``prescaler``,
        for example, re-checks INT against the new minimum. An unknown name
        in *only* also raises ``ValueError``.
        """
        names = FIELD_NAMES if only is None else only
        for name in names:
            spec = FIELD_SPECS.get(name)
            if spec is None:
                raise ValueError("unknown configuration field: %s" % name)
            self._check_field(spec, getattr(config, name))
        for triggers, rule in _RULES:
            if only is None or any(name in only for name in triggers):
                rule(self._profile, config)

    # -- encoding ------------------------------------------------------------

    def encode_register(self, index: int, config: ADF435xConfig) -> int:
        """Return the 32-bit word for register *index* (0 to 5).

        *config* is assumed valid. Raises ``ValueError`` for a bad *index*
        or an ``rf_divider`` that has no R4 code.
        """
        if not 0 <= index < consts.NUM_REGISTERS:
            raise ValueError("invalid register index: %d" % index)
        word = _FIXED_BITS[index]
        for name, pos, mask, kind in self._layout[index]:
            value = getattr(config, name)
            if kind == BOOL:
                value = 1 if value else 0
            elif kind == DIVIDER:
                value = self._profile.divider_code(value)
            word |= (value & mask) << pos
        return word

    def encode_config(self, config: ADF435xConfig) -> list:
        """Return all six words, R0 first."""
        return [self.encode_register(i, config) for i in range(consts.NUM_REGISTERS)]
