"""Shared constants for the ADF435x register map.

Field positions, widths, and symbolic encodings shared by the ADF4350 and
ADF4351. Device-specific capability differences live in ``profiles``.

Importing this module is host-safe for pytest. When MicroPython is unavailable,
``const`` is replaced with an identity function so constants load under CPython.
On the device, the real ``const`` lets the compiler fold integer constants.
"""

try:
    from micropython import const
# If MicroPython is not available, override the const definition to return the
# raw values.
except ImportError:

    def const(value):
        """Identity fallback for MicroPython's ``const`` on CPython hosts.

        Parameters
        ----------
        value : int
            The constant value.

        Returns
        -------
        int
            *value* unchanged, so the module imports under pytest.
        """
        return value


# Generic single-bit enable convention for the boolean fields.
DISABLED = const(0)
ENABLED = const(1)

# --- Word formats -----------------------------------------------------------
# SPI shifts one 32-bit word per register write. DB2:DB0 hold the register
# address (0..5) and must match the last three bits of the word.

WORD_SIZE_BYTES = const(4)
NUM_REGISTERS = const(6)
CONTROL_POS = const(0)
CONTROL_WIDTH = const(3)

REG0_ADDR = const(0)
REG1_ADDR = const(1)
REG2_ADDR = const(2)
REG3_ADDR = const(3)
REG4_ADDR = const(4)
REG5_ADDR = const(5)
REG_ADDRS = (REG0_ADDR, REG1_ADDR, REG2_ADDR, REG3_ADDR, REG4_ADDR, REG5_ADDR)

# R1 and R2 latch new values only after a subsequent R0 write (DBR, Figure 23).
DBR_REGISTER_INDICES = (REG1_ADDR, REG2_ADDR)


# --- Bit field layouts ------------------------------------------------------

# Register 0: feedback divider N = INT + FRAC/MOD; fVCO = fPFD * N.
REG0_INT_POS = const(15)
REG0_INT_WIDTH = const(16)
REG0_FRAC_POS = const(3)
REG0_FRAC_WIDTH = const(12)

# Register 1
# Dual-modulus prescaler: 4/5 below VCO threshold, 8/9 above.
REG1_PRESCALER_POS = const(27)
# Fractional modulus; channel step size is fPFD/MOD.
REG1_MOD_POS = const(3)
REG1_MOD_WIDTH = const(12)
# Phase offset word; use 1 when phase resync is unused (Figure 25).
REG1_PHASE_POS = const(15)
REG1_PHASE_WIDTH = const(12)
# ADF4351 only: each R0 write steps output phase; disables band select.
REG1_PHASE_ADJUST_POS = const(28)

# Register 2
# Divides REFIN to set fPFD; minimum divide ratio is 1.
REG2_R_COUNTER_POS = const(14)
REG2_R_COUNTER_WIDTH = const(10)
# Optional reference path multipliers before the R counter.
REG2_DOUBLER_POS = const(25)
REG2_RDIV2_POS = const(24)
# When set (DBB), R4 RF divider latches on R0 write instead of immediately.
REG2_DOUBLE_BUFFER_POS = const(13)
# Routes an internal signal to MUXOUT for lock detect or debug.
REG2_MUXOUT_POS = const(26)
REG2_MUXOUT_WIDTH = const(3)
# Lock-detect function and pulse width.
REG2_LDF_POS = const(8)
REG2_LDP_POS = const(7)
# Charge-pump current code; must match the external loop filter.
REG2_CP_CURRENT_POS = const(9)
REG2_CP_CURRENT_WIDTH = const(4)
REG2_NOISE_MODE_POS = const(29)
REG2_NOISE_MODE_WIDTH = const(2)
REG2_PD_POLARITY_POS = const(6)
REG2_POWER_DOWN_POS = const(5)
REG2_CP_THREESTATE_POS = const(4)
REG2_COUNTER_RESET_POS = const(3)

# Register 3
# ADF4351 fast band-select clock; shorter lock when fPFD is high.
REG3_BAND_CLK_MODE_POS = const(23)
# Antibacklash pulse: 6 ns frac-N, 3 ns int-N. ADF4350 fixed 3 ns (reserved).
REG3_ABP_POS = const(22)
# ADF4351 charge-pump cancellation for integer-N spurs.
REG3_CHARGE_CANCEL_POS = const(21)
# Cycle-slip reduction for faster lock.
REG3_CSR_POS = const(18)
# Divider and timeout for fast-lock and phase-resync sequences.
REG3_CLOCKDIV_MODE_POS = const(15)
REG3_CLOCKDIV_MODE_WIDTH = const(2)
REG3_CLOCKDIV_VALUE_POS = const(3)
REG3_CLOCKDIV_VALUE_WIDTH = const(12)

# Register 4
# Feedback from VCO fundamental vs divided tap before the output divider.
REG4_FEEDBACK_POS = const(23)
# Output divide-by code (log2 of divider, not the divider itself).
REG4_RF_DIVIDER_POS = const(20)
REG4_RF_DIVIDER_WIDTH = const(3)
# Divides R-counter output to produce band-select clock; legal count 1..255.
REG4_BAND_CLK_DIV_POS = const(12)
REG4_BAND_CLK_DIV_WIDTH = const(8)
# Mutes RF output until lock detect asserts.
REG4_MTLD_POS = const(10)
REG4_VCO_POWER_DOWN_POS = const(11)
# Primary and auxiliary output enables and power levels.
REG4_RF_ENABLE_POS = const(5)
REG4_OUTPUT_POWER_POS = const(3)
REG4_OUTPUT_POWER_WIDTH = const(2)
REG4_AUX_ENABLE_POS = const(8)
REG4_AUX_SELECT_POS = const(9)
REG4_AUX_POWER_POS = const(6)
REG4_AUX_POWER_WIDTH = const(2)

# Register 5
# MUXOUT lock-detect pin mode (low, digital lock, high).
REG5_LOCK_PIN_POS = const(22)
REG5_LOCK_PIN_WIDTH = const(2)
# DB20 and DB19 must always be written 1.
REG5_RESERVED_ONES = const(0x180000)


# --- Field value encodings --------------------------------------------------

# Prescaler select: 4/5 for lower VCO, 8/9 for higher VCO.
REG1_PRESCALER_4_5 = const(0)
REG1_PRESCALER_8_9 = const(1)

# Noise mode: default low-noise; low-spur trades phase noise for spurs.
REG2_LOW_NOISE = const(0b00)
REG2_LOW_SPUR = const(0b11)

# MUXOUT source for lock detect, counter readback, or bench debug.
REG2_MUX_THREESTATE = const(0b000)
REG2_MUX_DVDD = const(0b001)
REG2_MUX_DGND = const(0b010)
REG2_MUX_RCOUNTER = const(0b011)
REG2_MUX_NDIVIDER = const(0b100)
REG2_MUX_ANALOGLOCK = const(0b101)
REG2_MUX_DIGITALLOCK = const(0b110)

# Lock detect: frac-N vs int-N counting mode.
REG2_LDF_FRAC_N = const(0)
REG2_LDF_INT_N = const(1)

# Lock-detect pulse width: 10 ns default, 6 ns for faster sampling.
REG2_LDP_10NS = const(0)
REG2_LDP_6NS = const(1)

# Phase-detector polarity must match the loop filter topology.
REG2_PD_POLARITY_NEGATIVE = const(0)
REG2_PD_POLARITY_POSITIVE = const(1)

# Antibacklash pulse: 6 ns for fractional-N, 3 ns for integer-N.
REG3_ABP_6NS = const(0)
REG3_ABP_3NS = const(1)

# Band-select clock: normal vs fast (ADF4351, high fPFD).
REG3_BAND_CLK_LOW = const(0)
REG3_BAND_CLK_HIGH = const(1)

# Clock divider: off, fast-lock timeout, or phase-resync timeout.
REG3_CLOCKDIV_OFF = const(0b00)
REG3_CLOCKDIV_FASTLOCK = const(0b01)
REG3_CLOCKDIV_RESYNC = const(0b10)

# Feedback tap: divided path vs VCO fundamental.
REG4_FEEDBACK_DIVIDED = const(0)
REG4_FEEDBACK_FUNDAMENTAL = const(1)

# Output power levels for primary and auxiliary RF ports.
REG4_POWER_MINUS_4DBM = const(0b00)
REG4_POWER_MINUS_1DBM = const(0b01)
REG4_POWER_PLUS_2DBM = const(0b10)
REG4_POWER_PLUS_5DBM = const(0b11)

# Auxiliary output: divided copy vs VCO fundamental.
REG4_AUX_DIVIDED = const(0)
REG4_AUX_FUNDAMENTAL = const(1)

# Lock-detect pin behavior when MUXOUT is in lock-detect mode.
REG5_LOCK_LOW = const(0b00)
REG5_LOCK_DIGITAL = const(0b01)
REG5_LOCK_HIGH = const(0b11)

# Membership sets for validate_config at setup; not used on hot encode.
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

# Legal lower bounds beyond field width (width allows 0; hardware does not).
REG2_R_COUNTER_MIN = const(1)
REG4_BAND_CLK_DIV_MIN = const(1)
