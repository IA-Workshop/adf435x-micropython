"""The register field table and the configuration object.

``FIELDS`` lists every register field once: its register, bit position,
width, default, kind, legal values, the label used in error messages, and
the device capability it needs. ``ADF435xRegisterMapper`` builds both its
encoder and its validator from this table. ``ADF435xConfig`` only holds
field values; checking them is the mapper's job.
"""

from . import consts

# Field kinds.
BOOL = 0  # on/off flag: True/False or 1/0
UINT = 1  # unsigned integer that fits the width, at or above its minimum
ENUM = 2  # one of a tuple of codes from ``consts``
DIVIDER = 3  # RF divider, stored in the register as log2(divider)

# Column indices into a field spec tuple.
NAME, REG, POS, WIDTH, DEFAULT, KIND, ALLOWED, LABEL, CAPABILITY = range(9)


def _field(name, reg, pos, width, default, kind, allowed=None, label=None, cap=None):
    """Build one field spec tuple.

    *pos* is the bit position of the field's lowest bit. *allowed* is the
    minimum for a ``UINT`` (default 0) or the tuple of legal codes for an
    ``ENUM``. *label* names the field in error messages. *cap* names an
    ``ADF435xDeviceProfile`` attribute that must be true before the field
    may be nonzero, such as ``"has_phase_adjust"``.
    """
    if kind == UINT and allowed is None:
        allowed = 0
    return (name, reg, pos, width, default, kind, allowed, label or name, cap)


_R0, _R1, _R2, _R3, _R4, _R5 = consts.REG_ADDRS
_c = consts
_POWER_LEVELS = (
    _c.REG4_POWER_MINUS_4DBM,
    _c.REG4_POWER_MINUS_1DBM,
    _c.REG4_POWER_PLUS_2DBM,
    _c.REG4_POWER_PLUS_5DBM,
)

# fmt: off
FIELDS = (
    # --- R0: N = INT + FRAC/MOD (Figure 24) ---
    # The default INT is the 8/9 prescaler's minimum, 75, so it is legal.
    _field("int_n", _R0, _c.REG0_INT_POS, _c.REG0_INT_WIDTH, 75, UINT, label="INT"),
    _field("frac", _R0, _c.REG0_FRAC_POS, _c.REG0_FRAC_WIDTH, 0, UINT, label="FRAC"),
    # --- R1: prescaler, phase, MOD (Figure 25) ---
    _field(
        "phase_adjust", _R1, _c.REG1_PHASE_ADJUST_POS, 1, False, BOOL,
        cap="has_phase_adjust",
    ),
    _field(
        "prescaler", _R1, _c.REG1_PRESCALER_POS, 1, _c.REG1_PRESCALER_8_9, ENUM,
        (_c.REG1_PRESCALER_4_5, _c.REG1_PRESCALER_8_9),
    ),
    # Phase word 1 is recommended when phase resync is unused (p.18).
    _field("phase", _R1, _c.REG1_PHASE_POS, _c.REG1_PHASE_WIDTH, 1, UINT),
    # The MOD range depends on the part; the mapper's PLL rule checks it.
    _field("mod", _R1, _c.REG1_MOD_POS, _c.REG1_MOD_WIDTH, 2, UINT, label="MOD"),
    # --- R2: reference path, charge pump, lock detect, MUXOUT (Figure 26) ---
    _field(
        "noise_mode", _R2, _c.REG2_NOISE_MODE_POS, _c.REG2_NOISE_MODE_WIDTH,
        _c.REG2_LOW_NOISE, ENUM, (_c.REG2_LOW_NOISE, _c.REG2_LOW_SPUR),
        label="noise mode",
    ),
    _field(
        "muxout", _R2, _c.REG2_MUXOUT_POS, _c.REG2_MUXOUT_WIDTH,
        _c.REG2_MUX_DIGITALLOCK, ENUM,
        (
            _c.REG2_MUX_THREESTATE, _c.REG2_MUX_DVDD, _c.REG2_MUX_DGND,
            _c.REG2_MUX_RCOUNTER, _c.REG2_MUX_NDIVIDER, _c.REG2_MUX_ANALOGLOCK,
            _c.REG2_MUX_DIGITALLOCK,
        ),
        label="MUXOUT",
    ),
    _field("doubler", _R2, _c.REG2_DOUBLER_POS, 1, False, BOOL),
    _field("rdiv2", _R2, _c.REG2_RDIV2_POS, 1, False, BOOL),
    _field(
        "r_counter", _R2, _c.REG2_R_COUNTER_POS, _c.REG2_R_COUNTER_WIDTH, 1, UINT,
        _c.REG2_R_COUNTER_MIN, label="R",
    ),
    _field("double_buffer", _R2, _c.REG2_DOUBLE_BUFFER_POS, 1, False, BOOL),
    # Must suit the loop filter. 7 suits the evaluation board only.
    _field(
        "cp_current_code", _R2, _c.REG2_CP_CURRENT_POS, _c.REG2_CP_CURRENT_WIDTH,
        7, UINT, label="CP current",
    ),
    _field(
        "ldf", _R2, _c.REG2_LDF_POS, 1, _c.REG2_LDF_FRAC_N, ENUM,
        (_c.REG2_LDF_FRAC_N, _c.REG2_LDF_INT_N),
    ),
    _field(
        "ldp", _R2, _c.REG2_LDP_POS, 1, _c.REG2_LDP_10NS, ENUM,
        (_c.REG2_LDP_10NS, _c.REG2_LDP_6NS),
    ),
    _field(
        "pd_polarity", _R2, _c.REG2_PD_POLARITY_POS, 1,
        _c.REG2_PD_POLARITY_POSITIVE, ENUM,
        (_c.REG2_PD_POLARITY_NEGATIVE, _c.REG2_PD_POLARITY_POSITIVE),
    ),
    _field("power_down", _R2, _c.REG2_POWER_DOWN_POS, 1, False, BOOL),
    _field("cp_threestate", _R2, _c.REG2_CP_THREESTATE_POS, 1, False, BOOL),
    _field("counter_reset", _R2, _c.REG2_COUNTER_RESET_POS, 1, False, BOOL),
    # --- R3: band select clock, ABP, CSR, clock divider (Figure 27) ---
    _field(
        "band_clk_mode", _R3, _c.REG3_BAND_CLK_MODE_POS, 1, _c.REG3_BAND_CLK_LOW,
        ENUM, (_c.REG3_BAND_CLK_LOW, _c.REG3_BAND_CLK_HIGH),
        cap="has_fast_band_select",
    ),
    # Reserved, and always written as 0, on the ADF4350 (see the mapper).
    _field(
        "abp", _R3, _c.REG3_ABP_POS, 1, _c.REG3_ABP_6NS, ENUM,
        (_c.REG3_ABP_6NS, _c.REG3_ABP_3NS),
    ),
    _field(
        "charge_cancel", _R3, _c.REG3_CHARGE_CANCEL_POS, 1, False, BOOL,
        cap="has_charge_cancel",
    ),
    _field("csr", _R3, _c.REG3_CSR_POS, 1, False, BOOL),
    _field(
        "clockdiv_mode", _R3, _c.REG3_CLOCKDIV_MODE_POS, _c.REG3_CLOCKDIV_MODE_WIDTH,
        _c.REG3_CLOCKDIV_OFF, ENUM,
        (_c.REG3_CLOCKDIV_OFF, _c.REG3_CLOCKDIV_FASTLOCK, _c.REG3_CLOCKDIV_RESYNC),
    ),
    _field(
        "clockdiv_value", _R3, _c.REG3_CLOCKDIV_VALUE_POS,
        _c.REG3_CLOCKDIV_VALUE_WIDTH, 0, UINT, label="clock divider",
    ),
    # --- R4: feedback, dividers, output stage (Figure 28) ---
    _field(
        "feedback", _R4, _c.REG4_FEEDBACK_POS, 1, _c.REG4_FEEDBACK_FUNDAMENTAL,
        ENUM, (_c.REG4_FEEDBACK_DIVIDED, _c.REG4_FEEDBACK_FUNDAMENTAL),
    ),
    _field(
        "rf_divider", _R4, _c.REG4_RF_DIVIDER_POS, _c.REG4_RF_DIVIDER_WIDTH, 1,
        DIVIDER,
    ),
    # 1 to 255, or at most 254 in fast band-select mode (a mapper rule).
    _field(
        "band_clk_div", _R4, _c.REG4_BAND_CLK_DIV_POS, _c.REG4_BAND_CLK_DIV_WIDTH,
        1, UINT, _c.REG4_BAND_CLK_DIV_MIN, label="band select clock divider",
    ),
    _field("vco_power_down", _R4, _c.REG4_VCO_POWER_DOWN_POS, 1, False, BOOL),
    _field("mtld", _R4, _c.REG4_MTLD_POS, 1, False, BOOL),
    _field(
        "aux_select", _R4, _c.REG4_AUX_SELECT_POS, 1, _c.REG4_AUX_DIVIDED, ENUM,
        (_c.REG4_AUX_DIVIDED, _c.REG4_AUX_FUNDAMENTAL),
    ),
    _field("aux_enable", _R4, _c.REG4_AUX_ENABLE_POS, 1, False, BOOL),
    _field(
        "aux_power", _R4, _c.REG4_AUX_POWER_POS, _c.REG4_AUX_POWER_WIDTH,
        _c.REG4_POWER_MINUS_4DBM, ENUM, _POWER_LEVELS, label="aux power",
    ),
    _field("rf_enable", _R4, _c.REG4_RF_ENABLE_POS, 1, True, BOOL),
    _field(
        "output_power", _R4, _c.REG4_OUTPUT_POWER_POS, _c.REG4_OUTPUT_POWER_WIDTH,
        _c.REG4_POWER_PLUS_5DBM, ENUM, _POWER_LEVELS, label="output power",
    ),
    # --- R5: lock-detect pin (Figure 29) ---
    _field(
        "lock_pin", _R5, _c.REG5_LOCK_PIN_POS, _c.REG5_LOCK_PIN_WIDTH,
        _c.REG5_LOCK_DIGITAL, ENUM,
        (_c.REG5_LOCK_LOW, _c.REG5_LOCK_DIGITAL, _c.REG5_LOCK_HIGH),
    ),
)
# fmt: on

# Lookup views derived from FIELDS.
FIELD_SPECS = {spec[NAME]: spec for spec in FIELDS}
FIELD_NAMES = tuple(spec[NAME] for spec in FIELDS)
FIELD_REGISTER = {spec[NAME]: spec[REG] for spec in FIELDS}


class ADF435xConfig:
    """Register field values, one attribute per field in ``FIELDS``.

    The defaults are legal placeholders, not a frequency plan; ``solve()``
    supplies the frequency fields. The constructor checks field names only
    (``AttributeError`` for an unknown name). Values are checked by
    ``ADF435xRegisterMapper.validate_config()`` or, more usually, by
    ``ADF435xRegisterFile.configure()``. Give each register file its own
    config object.

    Examples
    --------
    >>> cfg = ADF435xConfig(int_n=422, frac=13, mod=25)
    >>> cfg.int_n
    422
    >>> cfg.prescaler == ADF435xConfig().prescaler
    True
    """

    def __init__(self, **overrides) -> None:
        """Start from the defaults, then apply *overrides*."""
        for spec in FIELDS:
            setattr(self, spec[NAME], spec[DEFAULT])
        for name, value in overrides.items():
            if name not in FIELD_SPECS:
                raise AttributeError("unknown configuration field: %s" % name)
            setattr(self, name, value)

    def copy(self) -> "ADF435xConfig":
        """Return an independent copy with the same field values."""
        return ADF435xConfig(**{name: getattr(self, name) for name in FIELD_NAMES})
