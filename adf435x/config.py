"""ADF435x device configuration fields and register mapping."""
from . import consts

# --- Default field values (PLL-valid placeholders) ---------------------------
# Not a tuned frequency plan; the solver sets frequency-determining fields.

# R0: INT at the 8/9-prescaler minimum (datasheet NMIN = 75). Matches the
# default prescaler so check_pll passes without encoding a specific frequency.
_DEFAULT_INT_N = 75

# R0: zero fractional numerator; encodable integer-N placeholder. Int-N
# register optimizations (LDF, ABP, R5) are left to the solver.
_DEFAULT_FRAC = 0

# R1: MOD at the datasheet minimum (2); keeps FRAC < MOD with _DEFAULT_FRAC.
_DEFAULT_MOD = 2

# R1: phase word 1 when phase resync and spur optimization are unused
# (recommended in datasheet Figure 25).
_DEFAULT_PHASE = 1

# R2: minimum legal R-counter divide ratio (REFIN / PFD >= 1).
_DEFAULT_R_COUNTER = 1

# R2: charge-pump current code placeholder (DB12:DB9). Must match the loop
# filter; 7 is the worked-example / typical bench default, not a universal ICP.
_DEFAULT_CP_CURRENT_CODE = 7

# R3: clock-divider count when clock divider mode is off.
_DEFAULT_CLOCKDIV_VALUE = 0

# R4: RF output divide-by-1 (unity); VCO frequency at the output path.
_DEFAULT_RF_DIVIDER = 1

# R4: minimum band-select clock divider (DB19:DB12).
_DEFAULT_BAND_CLK_DIV = 1

# Single schema: field name -> (register index, default value).
_FIELDS = {
    # R0
    "int_n": (consts.REG0_ADDR, _DEFAULT_INT_N),
    "frac": (consts.REG0_ADDR, _DEFAULT_FRAC),
    # R1
    "mod": (consts.REG1_ADDR, _DEFAULT_MOD),
    "prescaler": (consts.REG1_ADDR, consts.REG1_PRESCALER_8_9),
    "phase": (consts.REG1_ADDR, _DEFAULT_PHASE),
    "phase_adjust": (consts.REG1_ADDR, False),
    # R2
    "r_counter": (consts.REG2_ADDR, _DEFAULT_R_COUNTER),
    "cp_current_code": (consts.REG2_ADDR, _DEFAULT_CP_CURRENT_CODE),
    "muxout": (consts.REG2_ADDR, consts.REG2_MUX_DIGITALLOCK),
    "noise_mode": (consts.REG2_ADDR, consts.REG2_LOW_NOISE),
    "doubler": (consts.REG2_ADDR, False),
    "rdiv2": (consts.REG2_ADDR, False),
    "ldf": (consts.REG2_ADDR, consts.REG2_LDF_FRAC_N),
    "ldp": (consts.REG2_ADDR, consts.REG2_LDP_10NS),
    "pd_polarity": (consts.REG2_ADDR, consts.REG2_PD_POLARITY_POSITIVE),
    "double_buffer": (consts.REG2_ADDR, False),
    "power_down": (consts.REG2_ADDR, False),
    "cp_threestate": (consts.REG2_ADDR, False),
    "counter_reset": (consts.REG2_ADDR, False),
    # R3
    "band_clk_mode": (consts.REG3_ADDR, consts.REG3_BAND_CLK_LOW),
    "abp": (consts.REG3_ADDR, consts.REG3_ABP_6NS),
    "charge_cancel": (consts.REG3_ADDR, False),
    "csr": (consts.REG3_ADDR, False),
    "clockdiv_mode": (consts.REG3_ADDR, consts.REG3_CLOCKDIV_OFF),
    "clockdiv_value": (consts.REG3_ADDR, _DEFAULT_CLOCKDIV_VALUE),
    # R4
    "rf_divider": (consts.REG4_ADDR, _DEFAULT_RF_DIVIDER),
    "band_clk_div": (consts.REG4_ADDR, _DEFAULT_BAND_CLK_DIV),
    "feedback": (consts.REG4_ADDR, consts.REG4_FEEDBACK_FUNDAMENTAL),
    "output_power": (consts.REG4_ADDR, consts.REG4_POWER_PLUS_5DBM),
    "rf_enable": (consts.REG4_ADDR, True),
    "mtld": (consts.REG4_ADDR, False),
    "vco_power_down": (consts.REG4_ADDR, False),
    "aux_select": (consts.REG4_ADDR, consts.REG4_AUX_DIVIDED),
    "aux_enable": (consts.REG4_ADDR, False),
    "aux_power": (consts.REG4_ADDR, consts.REG4_POWER_MINUS_4DBM),
    # R5
    "lock_pin": (consts.REG5_ADDR, consts.REG5_LOCK_DIGITAL),
}

_DEFAULTS = {name: default for name, (_, default) in _FIELDS.items()}
FIELD_REGISTER = {name: reg for name, (reg, _) in _FIELDS.items()}
FIELD_NAMES = tuple(_FIELDS)


class ADF435xConfig:
    """Device configuration, with one instance attribute per register field.

    Defaults are PLL-valid placeholders so a freshly constructed register file
    always encodes six well-formed words. They are not a tuned frequency plan;
    the solver (future) sets ``int_n``, ``frac``, ``mod``, ``prescaler``,
    ``rf_divider``, and ``band_clk_div`` for a target output.

    Note: ``frac=0`` selects integer-N mode on the device; int-N register
    optimizations (LDF, ABP, R5 bits) are left to the solver, not applied here.

    Use one ``ADF435xConfig`` instance per ``ADF435xRegisterFile``; do not
    share a config object across multiple register files.
    """

    def __init__(self, **overrides) -> None:
        """Initialize from defaults, applying any field overrides.

        Parameters
        ----------
        **overrides
            Field name/value pairs matching keys in ``FIELD_REGISTER``.

        Raises
        ------
        AttributeError
            If an override names an unknown field.
        """
        for name, value in _DEFAULTS.items():
            setattr(self, name, value)
        for name, value in overrides.items():
            if name not in _FIELDS:
                raise AttributeError("unknown configuration field: %s" % name)
            setattr(self, name, value)

    def copy(self) -> "ADF435xConfig":
        """Return an independent copy of this configuration."""
        return ADF435xConfig(**{
            name: getattr(self, name) for name in _DEFAULTS
        })
