from . import consts

class ADF435xConfig:
    """Device configuration, with one attribute per register field.

    Defaults are valid and encodable so a freshly constructed file always has
    six well-formed words. The frequency-determining fields (``int_n``,
    ``frac``, ``mod``, ``prescaler``, ``rf_divider``, ``band_clk_div``,
    ``r_counter``) carry placeholder defaults and are expected to be set from a
    solved frequency plan.
    """

    # R0
    int_n = 0
    frac = 0
    # R1
    mod = 2
    prescaler = consts.REG1_PRESCALER_8_9
    phase = 1
    phase_adjust = False
    # R2
    r_counter = 1
    cp_current_code = 7
    muxout = consts.REG2_MUX_DIGITALLOCK
    noise_mode = consts.REG2_LOW_NOISE
    doubler = False
    rdiv2 = False
    ldf = consts.REG2_LDF_FRAC_N
    ldp = consts.REG2_LDP_10NS
    pd_polarity = consts.REG2_PD_POLARITY_POSITIVE
    double_buffer = False
    power_down = False
    cp_threestate = False
    counter_reset = False
    # R3
    band_clk_mode = consts.REG3_BAND_CLK_LOW
    abp = consts.REG3_ABP_6NS
    charge_cancel = False
    csr = False
    clockdiv_mode = consts.REG3_CLOCKDIV_OFF
    clockdiv_value = 0
    # R4
    rf_divider = 1
    band_clk_div = 1
    feedback = consts.REG4_FEEDBACK_FUNDAMENTAL
    output_power = consts.REG4_POWER_PLUS_5DBM
    rf_enable = True
    mtld = False
    vco_power_down = False
    aux_select = consts.REG4_AUX_DIVIDED
    aux_enable = False
    aux_power = consts.REG4_POWER_MINUS_4DBM
    # R5
    lock_pin = consts.REG5_LOCK_DIGITAL