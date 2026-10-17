"""Register map constants shared by the ADF4350 and ADF4351.

Bit positions (``_POS``), widths (``_WIDTH``) and field codes for the six
registers, R0 to R5. Differences between the two parts are in ``profiles``,
and the legal values of each field are in ``config.FIELDS``. Register maps:
ADF4351 data sheet, Figures 23 to 29 (pp.14 to 17).
"""

try:
    from micropython import const
except ImportError:

    def const(value):
        """Stand-in for MicroPython's ``const()`` on CPython."""
        return value


# --- Words and addresses ----------------------------------------------------
# Each register is one 32-bit word. Bits DB2:DB0 hold its address, 0 to 5.

NUM_REGISTERS = const(6)

REG0_ADDR = const(0)
REG1_ADDR = const(1)
REG2_ADDR = const(2)
REG3_ADDR = const(3)
REG4_ADDR = const(4)
REG5_ADDR = const(5)
REG_ADDRS = (REG0_ADDR, REG1_ADDR, REG2_ADDR, REG3_ADDR, REG4_ADDR, REG5_ADDR)

# Registers whose double-buffered fields wait for the next R0 write (data
# sheet p.12): phase and MOD in R1; doubler, divide-by-2, R counter and
# charge-pump current in R2. Their other bits take effect at once.
DBR_REGISTER_INDICES = (REG1_ADDR, REG2_ADDR)


# --- Bit field layouts ------------------------------------------------------

# R0: N = INT + FRAC/MOD, and fVCO = fPFD * N.
REG0_INT_POS = const(15)
REG0_INT_WIDTH = const(16)
REG0_FRAC_POS = const(3)
REG0_FRAC_WIDTH = const(12)

# R1
REG1_PRESCALER_POS = const(27)
# The VCO step is fPFD / MOD.
REG1_MOD_POS = const(3)
REG1_MOD_WIDTH = const(12)
# Use 1 when phase resync is not used (Figure 25).
REG1_PHASE_POS = const(15)
REG1_PHASE_WIDTH = const(12)
# ADF4351 only. Each R0 write steps the output phase; band select is off.
REG1_PHASE_ADJUST_POS = const(28)

# R2
REG2_R_COUNTER_POS = const(14)
REG2_R_COUNTER_WIDTH = const(10)
REG2_DOUBLER_POS = const(25)
REG2_RDIV2_POS = const(24)
# When set, the R4 RF divider waits for the next R0 write.
REG2_DOUBLE_BUFFER_POS = const(13)
REG2_MUXOUT_POS = const(26)
REG2_MUXOUT_WIDTH = const(3)
# Lock detect: LDF sets the cycle count, LDP the comparison window.
REG2_LDF_POS = const(8)
REG2_LDP_POS = const(7)
# Must suit the loop filter.
REG2_CP_CURRENT_POS = const(9)
REG2_CP_CURRENT_WIDTH = const(4)
REG2_NOISE_MODE_POS = const(29)
REG2_NOISE_MODE_WIDTH = const(2)
REG2_PD_POLARITY_POS = const(6)
REG2_POWER_DOWN_POS = const(5)
REG2_CP_THREESTATE_POS = const(4)
REG2_COUNTER_RESET_POS = const(3)

# R3
# ADF4351 only: fast band-select clock, for a high fPFD.
REG3_BAND_CLK_MODE_POS = const(23)
# Antibacklash pulse width. Reserved on the ADF4350, which is fixed at 3 ns.
REG3_ABP_POS = const(22)
# ADF4351 only: reduces integer-N spurs.
REG3_CHARGE_CANCEL_POS = const(21)
# Cycle-slip reduction, for faster lock.
REG3_CSR_POS = const(18)
# Clock divider for the fast-lock and phase-resync timers.
REG3_CLOCKDIV_MODE_POS = const(15)
REG3_CLOCKDIV_MODE_WIDTH = const(2)
REG3_CLOCKDIV_VALUE_POS = const(3)
REG3_CLOCKDIV_VALUE_WIDTH = const(12)

# R4
# Feedback from the VCO itself, or from after the RF divider.
REG4_FEEDBACK_POS = const(23)
# Holds log2 of the RF divider, not the divider itself.
REG4_RF_DIVIDER_POS = const(20)
REG4_RF_DIVIDER_WIDTH = const(3)
# Band-select clock = fPFD / this value, 1 to 255.
REG4_BAND_CLK_DIV_POS = const(12)
REG4_BAND_CLK_DIV_WIDTH = const(8)
# Mute till lock detect: RF output stays off until the PLL locks.
REG4_MTLD_POS = const(10)
REG4_VCO_POWER_DOWN_POS = const(11)
REG4_RF_ENABLE_POS = const(5)
REG4_OUTPUT_POWER_POS = const(3)
REG4_OUTPUT_POWER_WIDTH = const(2)
REG4_AUX_ENABLE_POS = const(8)
REG4_AUX_SELECT_POS = const(9)
REG4_AUX_POWER_POS = const(6)
REG4_AUX_POWER_WIDTH = const(2)

# R5
# Mode of the LD (lock detect) pin.
REG5_LOCK_PIN_POS = const(22)
REG5_LOCK_PIN_WIDTH = const(2)
# DB20 and DB19 are reserved and must be written as 1.
REG5_RESERVED_ONES = const(0x180000)


# --- Field codes ------------------------------------------------------------

# Prescaler: 4/5 for lower VCO frequencies, 8/9 for higher ones.
REG1_PRESCALER_4_5 = const(0)
REG1_PRESCALER_8_9 = const(1)

# Noise mode: low-spur mode trades phase noise for fewer spurs.
REG2_LOW_NOISE = const(0b00)
REG2_LOW_SPUR = const(0b11)

# MUXOUT source.
REG2_MUX_THREESTATE = const(0b000)
REG2_MUX_DVDD = const(0b001)
REG2_MUX_DGND = const(0b010)
REG2_MUX_RCOUNTER = const(0b011)
REG2_MUX_NDIVIDER = const(0b100)
REG2_MUX_ANALOGLOCK = const(0b101)
REG2_MUX_DIGITALLOCK = const(0b110)

# LDF: lock is reported after 40 (fractional-N) or 5 (integer-N) PFD cycles.
REG2_LDF_FRAC_N = const(0)
REG2_LDF_INT_N = const(1)

# LDP: comparison window of 10 ns or 6 ns. Data sheet p.19 recommends LDF and
# LDP both 0 for fractional-N and both 1 for integer-N.
REG2_LDP_10NS = const(0)
REG2_LDP_6NS = const(1)

# Phase detector polarity; must match the loop filter.
REG2_PD_POLARITY_NEGATIVE = const(0)
REG2_PD_POLARITY_POSITIVE = const(1)

# Antibacklash pulse: 6 ns for fractional-N, 3 ns for integer-N.
REG3_ABP_6NS = const(0)
REG3_ABP_3NS = const(1)

# Band-select clock mode: normal, or fast (ADF4351 only).
REG3_BAND_CLK_LOW = const(0)
REG3_BAND_CLK_HIGH = const(1)

# Clock divider mode: off, fast-lock timer, or phase-resync timer.
REG3_CLOCKDIV_OFF = const(0b00)
REG3_CLOCKDIV_FASTLOCK = const(0b01)
REG3_CLOCKDIV_RESYNC = const(0b10)

# Feedback path: after the RF divider, or the VCO itself.
REG4_FEEDBACK_DIVIDED = const(0)
REG4_FEEDBACK_FUNDAMENTAL = const(1)

# Output power, for both the main and the auxiliary output.
REG4_POWER_MINUS_4DBM = const(0b00)
REG4_POWER_MINUS_1DBM = const(0b01)
REG4_POWER_PLUS_2DBM = const(0b10)
REG4_POWER_PLUS_5DBM = const(0b11)

# Auxiliary output source: after the RF divider, or the VCO itself.
REG4_AUX_DIVIDED = const(0)
REG4_AUX_FUNDAMENTAL = const(1)

# LD pin mode.
REG5_LOCK_LOW = const(0b00)
REG5_LOCK_DIGITAL = const(0b01)
REG5_LOCK_HIGH = const(0b11)

# Smallest legal values where the field width alone would allow 0.
REG2_R_COUNTER_MIN = const(1)
REG4_BAND_CLK_DIV_MIN = const(1)
