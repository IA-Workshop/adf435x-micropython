"""ADF435x configuration fields: the single field table and the config object.

``FIELDS`` describes every register field once: register, bit position and
width, default, kind, legal values, error-message label, and the device
capability it needs. The mapper derives both its encoder and its validator
from this table, so there is no second copy of the layout or the defaults.

``ADF435xConfig`` holds field values only. It does not know the target device
and cannot validate; ``ADF435xRegisterMapper.validate_config`` does that, and
``ADF435xRegisterFile`` calls it at init and on every ``configure()``.
"""

from . import consts

# Field kinds.
BOOL = 0  # 1-bit on/off flag; must be True/False (or 1/0)
UINT = 1  # unsigned integer; must fit the width and be >= its minimum
ENUM = 2  # one of an explicit tuple of codes from ``consts``
DIVIDER = 3  # RF output divider; encoded as log2 via the device profile

# Column indices into a field spec tuple.
NAME, REG, POS, WIDTH, DEFAULT, KIND, ALLOWED, LABEL, CAPABILITY = range(9)


def _field(name, reg, pos, width, default, kind, allowed=None, label=None, cap=None):
    """Build one field spec.

    Parameters
    ----------
    name : str
        Config attribute name.
    reg : int
        Register index (0..5).
    pos, width : int
        Bit position of the least-significant bit, and field width.
    default
        Value a fresh ``ADF435xConfig`` holds. Defaults are PLL-valid
        placeholders, not a tuned frequency plan.
    kind : int
        ``BOOL``, ``UINT``, ``ENUM`` or ``DIVIDER``.
    allowed : int or tuple, optional
        ``UINT``: minimum legal value (default 0). ``ENUM``: legal codes.
    label : str, optional
        Name used in error messages (defaults to *name*).
    cap : str, optional
        ``ADF435xDeviceProfile`` attribute that must be true for a nonzero
        value (for example ``"has_phase_adjust"``).
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
    # INT at the 8/9-prescaler minimum (NMIN = 75) so the default validates.
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
    # MOD range comes from the profile (checked with the PLL rule).
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
    # Must match the loop filter; 7 is the eval-board value, not universal.
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
    # Reserved (always 0) on parts without programmable ABP; see the mapper.
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
    # Legal 1..255 (<= 254 in fast band-select mode; checked as a rule).
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
    """Device configuration, with one instance attribute per register field.

    Defaults are PLL-valid placeholders so a freshly constructed register file
    always encodes six well-formed words. They are not a tuned frequency plan;
    ``adf435x.solver.solve()`` sets the frequency-determining fields.

    Constructing ``ADF435xConfig(**kw)`` checks field names only. To validate
    values, use ``ADF435xRegisterMapper(profile).validate_config(cfg)`` or build
    the config through ``ADF435xRegisterFile.configure()``.

    Parameters
    ----------
    **overrides
        Field name/value pairs; names are those in ``FIELD_NAMES``. Names not
        given keep their default value.

    Raises
    ------
    AttributeError
        If an override names an unknown field.

    Notes
    -----
    Use one ``ADF435xConfig`` instance per ``ADF435xRegisterFile``; do not
    share a config object across multiple register files.

    Examples
    --------
    >>> cfg = ADF435xConfig(int_n=422, frac=13, mod=25)
    >>> cfg.int_n
    422
    >>> cfg.prescaler == ADF435xConfig().prescaler
    True
    """

    def __init__(self, **overrides) -> None:
        """Initialize from defaults, applying any field overrides."""
        for spec in FIELDS:
            setattr(self, spec[NAME], spec[DEFAULT])
        for name, value in overrides.items():
            if name not in FIELD_SPECS:
                raise AttributeError("unknown configuration field: %s" % name)
            setattr(self, name, value)

    def copy(self) -> "ADF435xConfig":
        """Return an independent copy of this configuration.

        Returns
        -------
        ADF435xConfig
            A new instance with the same field values. Mutating the copy does
            not affect the original.
        """
        return ADF435xConfig(**{name: getattr(self, name) for name in FIELD_NAMES})
