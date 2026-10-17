"""
Profile-aware register encoder and validator for the ADF435x family.

An ADF435xRegisterMapper turns field values into the six 32-bit register words
of the ADF4350/ADF4351. Both the encoder and the validator are driven by the
field table ``config.FIELDS``; the ``ADF435xDeviceProfile`` supplies what
differs between the two parts.

Validation and encode are split on purpose. Call ``validate_config`` at setup
boundaries (register-file init, ``configure()``, REPL debugging). The encode
path trusts its input: it masks each field to its width and does no range or
capability checks. The one structural step left in encode is the
``rf_divider -> code`` mapping, which has no bit pattern to mask.

Notes
-----
Register field positions and encodings are defined in the register maps that
begin at Figure 23 (p. 14) of both the ADF4350 and ADF4351 data sheets
(R0..R5 in Figures 24..29).
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

# Error-message wording for each profile capability.
_CAPABILITY_TEXT = {
    "has_phase_adjust": "phase adjust",
    "has_fast_band_select": "fast band select",
    "has_charge_cancel": "charge cancellation",
}

# Fixed bits per register: the address in DB2:DB0, plus R5's reserved ones.
_FIXED_BITS = (
    consts.REG0_ADDR,
    consts.REG1_ADDR,
    consts.REG2_ADDR,
    consts.REG3_ADDR,
    consts.REG4_ADDR,
    consts.REG5_RESERVED_ONES | consts.REG5_ADDR,
)

# Data sheet limits used by the cross-field rules.
_LOW_SPUR_MOD_MIN = 50  # p.23
_FAST_BAND_CLK_DIV_MAX = 254  # p.19


def _rule_pll(profile, c):
    """MOD range, FRAC < MOD, and INT range for the selected prescaler."""
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
            "low-spur noise mode needs MOD >= %d (MOD=%d)"
            % (_LOW_SPUR_MOD_MIN, c.mod)
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


# (fields that trigger the rule, rule). A rule runs when any trigger field is
# being validated, so changing one field re-checks its partners.
_RULES = (
    (("int_n", "frac", "mod", "prescaler"), _rule_pll),
    (("phase", "mod"), _rule_phase),
    (("noise_mode", "mod"), _rule_low_spur),
    (("band_clk_mode", "band_clk_div"), _rule_fast_band_clk),
    (("muxout",), _rule_muxout),
)


class ADF435xRegisterMapper:
    """
    Encode and validate ADF435x register words for a specific device profile.

    Parameters
    ----------
    profile : ADF435xDeviceProfile
        The target device. Supplies capability flags, PLL bounds, and the
        RF-divider code mapping.

    Notes
    -----
    Call ``validate_config`` before encoding a configuration that did not come
    through ``ADF435xRegisterFile``. ``encode_register`` assumes valid input.
    """

    def __init__(self, profile: ADF435xDeviceProfile):
        """Bind the mapper to a profile and precompute the encode layout."""
        self._profile = profile
        # Per register: (name, pos, mask, kind) for every field it encodes.
        # Without programmable ABP, DB22 is reserved and left at 0.
        layout = [[] for _ in range(consts.NUM_REGISTERS)]
        for spec in FIELDS:
            if spec[NAME] == "abp" and not profile.has_programmable_abp:
                continue
            mask = (1 << spec[WIDTH]) - 1
            layout[spec[REG]].append((spec[NAME], spec[POS], mask, spec[KIND]))
        self._layout = tuple(tuple(fields) for fields in layout)

    @property
    def profile(self) -> ADF435xDeviceProfile:
        """The device profile this mapper encodes for."""
        return self._profile

    # -- validation ----------------------------------------------------------

    def _check_field(self, spec, value) -> None:
        """Validate one field value against its spec and the profile."""
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
        cap = spec[CAPABILITY]
        if cap is not None and value and not getattr(self._profile, cap):
            raise ValueError(
                "%s does not support %s" % (self._profile.name, _CAPABILITY_TEXT[cap])
            )

    def validate_config(self, config: ADF435xConfig, *, only=None) -> None:
        """Raise ValueError on any configuration violation. Never encodes.

        Parameters
        ----------
        config : ADF435xConfig
            Configuration to validate.
        only : set or frozenset of str, optional
            When ``None``, every field and every cross-field rule is checked.
            Otherwise only the named fields are checked, plus each cross-field
            rule that involves one of them (for example, changing only
            ``prescaler`` re-checks INT against the new minimum).

        Raises
        ------
        ValueError
            On any kind, width, range, membership, capability, divider, or
            cross-field violation, or an unknown field name in *only*.
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
        """Encode one register word from *config*.

        Parameters
        ----------
        index : int
            Register index (0..5).
        config : ADF435xConfig
            Configuration supplying field values; assumed validated.

        Returns
        -------
        int
            The 32-bit register word, address in DB2:DB0.

        Raises
        ------
        ValueError
            If *index* is invalid, or ``rf_divider`` has no divider code.
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
        """Encode all six registers from *config*.

        Returns
        -------
        list of int
            Register words R0 through R5.
        """
        return [self.encode_register(i, config) for i in range(consts.NUM_REGISTERS)]
