"""Shared constants for the ADF435x register map.

Field positions, widths, and symbolic encodings shared by the ADF4350 and
ADF4351. Device-specific capability differences live in ``profiles``.

Importing this module is host-safe for pytest. When MicroPython is unavailable,
``const`` is replaced with an identity function so constants load under CPython.
On the device, ``const`` marks these as integer constants; other modules still
read them as ordinary attributes (``consts.X``), so expect no cross-module
folding. Legal-value sets for each field live in ``config.FIELDS``.
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


# --- Word formats -----------------------------------------------------------
# SPI shifts one 32-bit word per register write. DB2:DB0 hold the register
# address (0..5) and must match the last three bits of the word.

NUM_REGISTERS = const(6)

REG0_ADDR = const(0)
REG1_ADDR = const(1)
REG2_ADDR = const(2)
REG3_ADDR = const(3)
REG4_ADDR = const(4)
REG5_ADDR = const(5)
REG_ADDRS = (REG0_ADDR, REG1_ADDR, REG2_ADDR, REG3_ADDR, REG4_ADDR, REG5_ADDR)

# R1 and R2 hold double-buffered fields that latch on the next R0 write (DBR,
# data sheet p.12): phase and MOD in R1; doubler, RDIV2, R counter and CP
# current in R2. Their other bits take effect immediately.
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
# Lock-detect function (cycle count) and precision (comparison window).
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

# Lock-detect function: 40 PFD cycles (frac-N) or 5 cycles (int-N).
REG2_LDF_FRAC_N = const(0)
REG2_LDF_INT_N = const(1)

# Lock-detect precision: comparison window of 10 ns or 6 ns. Data sheet p.19
# recommends LDF/LDP = 00 for fractional-N and 11 for integer-N.
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

# Legal lower bounds beyond field width (width allows 0; hardware does not).
REG2_R_COUNTER_MIN = const(1)
REG4_BAND_CLK_DIV_MIN = const(1)
