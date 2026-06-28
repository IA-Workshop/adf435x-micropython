"""Shared constants for the ADF435x register map.

This module provides constant definitions for word formats, register
addresses, field positions and widths, and the symbolic encodings of
multi-valued fields. Device-specific differences in how the fields are
implemented are defined in ``profiles``.

Notes
-----
- These constants are defined starting on p. 14 of both the ADF4350 and
ADF4351 datasheets.
- Importing this module is host-safe to facilitate testing. The MicroPython
``const`` builtin is overridden if this module is imported in host-side
CPython so that the values will load properly under pytest. When running on
MicroPython on the device, the real ``const`` is used, so integer constants
are optimized by the compiler.
"""

try:
    from micropython import const
# If MicroPython is not available, override the const definition to return the
# raw values.
except ImportError:

    def const(value):
        return value


# Generic single-bit enable convention for the boolean fields.
DISABLED = const(0)
ENABLED = const(1)

# --- Word Formats -----------------------------------------------------------

WORD_SIZE_BYTES = const(4)  # Each register is one 32-bit word
NUM_REGISTERS = const(6)  # Six registers: R0..R5
CONTROL_POS = const(0)  # Control bits occupy DB2:DB0
CONTROL_WIDTH = const(3)

# Register addresses equal the value of the three control bits (DB2:DB0).
REG0_ADDR = const(0)
REG1_ADDR = const(1)
REG2_ADDR = const(2)
REG3_ADDR = const(3)
REG4_ADDR = const(4)
REG5_ADDR = const(5)
REG_ADDRS = (REG0_ADDR, REG1_ADDR, REG2_ADDR, REG3_ADDR, REG4_ADDR, REG5_ADDR)

# Registers fully double-buffered by a write to R0 (DBR, datasheet Figure 23).
DBR_REGISTER_INDICES = (REG1_ADDR, REG2_ADDR)


# --- Bit field layouts ------------------------------------------------------
# Each field is given the position of its least-significant bit and width, if
# applicable.

# Register 0
REG0_INT_POS = const(15)
REG0_INT_WIDTH = const(16)
REG0_FRAC_POS = const(3)
REG0_FRAC_WIDTH = const(12)

# Register 1
REG1_PHASE_ADJUST_POS = const(28)  # ADF4351 only (reserved on ADF4350)
REG1_PRESCALER_POS = const(27)
REG1_PHASE_POS = const(15)
REG1_PHASE_WIDTH = const(12)
REG1_MOD_POS = const(3)
REG1_MOD_WIDTH = const(12)

# Register 2
REG2_NOISE_MODE_POS = const(29)
REG2_NOISE_MODE_WIDTH = const(2)
REG2_MUXOUT_POS = const(26)
REG2_MUXOUT_WIDTH = const(3)
REG2_DOUBLER_POS = const(25)
REG2_RDIV2_POS = const(24)
REG2_R_COUNTER_POS = const(14)
REG2_R_COUNTER_WIDTH = const(10)
REG2_DOUBLE_BUFFER_POS = const(13)
REG2_CP_CURRENT_POS = const(9)
REG2_CP_CURRENT_WIDTH = const(4)
REG2_LDF_POS = const(8)
REG2_LDP_POS = const(7)
REG2_PD_POLARITY_POS = const(6)
REG2_POWER_DOWN_POS = const(5)
REG2_CP_THREESTATE_POS = const(4)
REG2_COUNTER_RESET_POS = const(3)

# Register 3
REG3_BAND_CLK_MODE_POS = const(23)  # ADF4351 only
REG3_ABP_POS = const(22)  # ADF4351 only
REG3_CHARGE_CANCEL_POS = const(21)  # ADF4351 only
REG3_CSR_POS = const(18)
REG3_CLOCKDIV_MODE_POS = const(15)
REG3_CLOCKDIV_MODE_WIDTH = const(2)
REG3_CLOCKDIV_VALUE_POS = const(3)
REG3_CLOCKDIV_VALUE_WIDTH = const(12)

# Register 4
REG4_FEEDBACK_POS = const(23)
REG4_RF_DIVIDER_POS = const(20)
REG4_RF_DIVIDER_WIDTH = const(3)
REG4_BAND_CLK_DIV_POS = const(12)
REG4_BAND_CLK_DIV_WIDTH = const(8)
REG4_VCO_POWER_DOWN_POS = const(11)
REG4_MTLD_POS = const(10)
REG4_AUX_SELECT_POS = const(9)
REG4_AUX_ENABLE_POS = const(8)
REG4_AUX_POWER_POS = const(6)
REG4_AUX_POWER_WIDTH = const(2)
REG4_RF_ENABLE_POS = const(5)
REG4_OUTPUT_POWER_POS = const(3)
REG4_OUTPUT_POWER_WIDTH = const(2)

# Register 5
REG5_LOCK_PIN_POS = const(22)
REG5_LOCK_PIN_WIDTH = const(2)
REG5_RESERVED_ONES = const(0x180000)  # DB20 and DB19 must be 1


# --- Field value encodings --------------------------------------------------

# R1 prescaler (PR1)
REG1_PRESCALER_4_5 = const(0)
REG1_PRESCALER_8_9 = const(1)

# R2 low-noise / low-spur modes (L2:L1)
REG2_LOW_NOISE = const(0b00)
REG2_LOW_SPUR = const(0b11)

# R2 MUXOUT (M3:M1)
REG2_MUX_THREESTATE = const(0b000)
REG2_MUX_DVDD = const(0b001)
REG2_MUX_DGND = const(0b010)
REG2_MUX_RCOUNTER = const(0b011)
REG2_MUX_NDIVIDER = const(0b100)
REG2_MUX_ANALOGLOCK = const(0b101)
REG2_MUX_DIGITALLOCK = const(0b110)

# R2 lock-detect function (LDF)
REG2_LDF_FRAC_N = const(0)
REG2_LDF_INT_N = const(1)

# R2 lock-detect precision (LDP)
REG2_LDP_10NS = const(0)
REG2_LDP_6NS = const(1)

# R2 phase-detector polarity
REG2_PD_POLARITY_NEGATIVE = const(0)
REG2_PD_POLARITY_POSITIVE = const(1)

# R3 antibacklash pulse width (ABP)
REG3_ABP_6NS = const(0)  # fractional-N
REG3_ABP_3NS = const(1)  # integer-N

# R3 band-select clock mode
REG3_BAND_CLK_LOW = const(0)
REG3_BAND_CLK_HIGH = const(1)  # fast band select (ADF4351)

# R3 clock divider mode (C2:C1)
REG3_CLOCKDIV_OFF = const(0b00)
REG3_CLOCKDIV_FASTLOCK = const(0b01)
REG3_CLOCKDIV_RESYNC = const(0b10)

# R4 feedback select
REG4_FEEDBACK_DIVIDED = const(0)
REG4_FEEDBACK_FUNDAMENTAL = const(1)

# R4 primary and auxiliary output power (D2:D1 / D5:D4)
REG4_POWER_MINUS_4DBM = const(0b00)
REG4_POWER_MINUS_1DBM = const(0b01)
REG4_POWER_PLUS_2DBM = const(0b10)
REG4_POWER_PLUS_5DBM = const(0b11)

# R4 auxiliary output select
REG4_AUX_DIVIDED = const(0)
REG4_AUX_FUNDAMENTAL = const(1)

# R5 lock-detect pin operation (D15:D14)
REG5_LOCK_LOW = const(0b00)
REG5_LOCK_DIGITAL = const(0b01)
REG5_LOCK_HIGH = const(0b11)

# Valid value sets for multi-valued fields (membership checks, not width-only).
REG1_PRESCALER_VALUES = (
    REG1_PRESCALER_4_5,
    REG1_PRESCALER_8_9,
)
REG2_MUXOUT_VALUES = (
    REG2_MUX_THREESTATE,
    REG2_MUX_DVDD,
    REG2_MUX_DGND,
    REG2_MUX_RCOUNTER,
    REG2_MUX_NDIVIDER,
    REG2_MUX_ANALOGLOCK,
    REG2_MUX_DIGITALLOCK,
)
REG2_NOISE_MODE_VALUES = (REG2_LOW_NOISE, REG2_LOW_SPUR)
REG2_LDF_VALUES = (REG2_LDF_FRAC_N, REG2_LDF_INT_N)
REG2_LDP_VALUES = (REG2_LDP_10NS, REG2_LDP_6NS)
REG2_PD_POLARITY_VALUES = (
    REG2_PD_POLARITY_NEGATIVE,
    REG2_PD_POLARITY_POSITIVE,
)
REG3_BAND_CLK_MODE_VALUES = (REG3_BAND_CLK_LOW, REG3_BAND_CLK_HIGH)
REG3_ABP_VALUES = (REG3_ABP_6NS, REG3_ABP_3NS)
REG3_CLOCKDIV_MODE_VALUES = (
    REG3_CLOCKDIV_OFF,
    REG3_CLOCKDIV_FASTLOCK,
    REG3_CLOCKDIV_RESYNC,
)
REG4_FEEDBACK_VALUES = (REG4_FEEDBACK_DIVIDED, REG4_FEEDBACK_FUNDAMENTAL)
REG4_OUTPUT_POWER_VALUES = (
    REG4_POWER_MINUS_4DBM,
    REG4_POWER_MINUS_1DBM,
    REG4_POWER_PLUS_2DBM,
    REG4_POWER_PLUS_5DBM,
)
REG4_AUX_SELECT_VALUES = (REG4_AUX_DIVIDED, REG4_AUX_FUNDAMENTAL)
REG5_LOCK_PIN_VALUES = (REG5_LOCK_LOW, REG5_LOCK_DIGITAL, REG5_LOCK_HIGH)

# Datasheet minimums not implied by field width alone.
REG2_R_COUNTER_MIN = const(1)
REG4_BAND_CLK_DIV_MIN = const(1)
