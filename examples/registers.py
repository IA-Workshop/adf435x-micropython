"""
ADF435x register-file example in MicroPython.

Builds the datasheet worked-example PLL settings (ADF4351 data sheet, p. 21)
through ``ADF435xRegisterFile``, then programs the chip over SPI. RF output is
scaled for bench verification on a mid-range oscilloscope. About 200 MHz
bandwidth, 1 GSa/s is enough to measure the period.

Hardware assumptions
--------------------
- 10 MHz reference on REFIN (R counter = 1, no doubler).
- Loop filter and VCO matching your board (example values encode only; lock
  depends on the analog front end).
- Probe RFOUTA (or your routed output). Expect about 132 MHz:

      fPFD = REFIN / R = 10 MHz
      fVCO = fPFD * (INT + FRAC/MOD) = 10 * 422.52 = 4225.2 MHz
      fOUT = fVCO / RF_divider = 4225.2 / 32 ~= 131.9 MHz

  The data-sheet example uses RF divide-by-2 for 2112.6 MHz; divide-by-32
  keeps the same PLL numbers but brings the output into scope range.
  Catalog slug: ``adf4351_scope_equiv_132p0375mhz`` (see ``examples/validate.py``;
  ADF4351 only).

Modify pin numbers to match your specific setup.
"""

from machine import SPI

from adf435x import consts
from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile

# Default pin values, modify as needed
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11
ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14

SPI_CHANNEL = 1

# Expected RF output with 10 MHz REFIN and the configuration below.
EXPECTED_RFOUT_HZ = 131_912_500


def write_plan(device, regfile, plan):
    """Write a commit plan to the chip and update the register-file cache."""
    try:
        device.write_registers(plan)
        regfile.mark_written()
    except Exception:
        regfile.mark_write_failed()
        raise


print(
    "Opening SPI channel %d (SCK=%d, MOSI=%d)"
    % (SPI_CHANNEL, SPI_SCK_PIN, SPI_MOSI_PIN)
)

spi = SPI(
    SPI_CHANNEL,
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    bits=8,
    sck=SPI_SCK_PIN,
    mosi=SPI_MOSI_PIN,
)

adf = ADF435xDevice(
    spi,
    load_enable_pin=ADF435X_LE_PIN,
    chip_enable_pin=ADF435X_CE_PIN,
)

regfile = ADF435xRegisterFile(ADF4351)
regfile.configure(
    int_n=422,
    frac=13,
    mod=25,
    band_clk_mode=consts.REG3_BAND_CLK_HIGH,
    rf_divider=32,
    band_clk_div=20,
)

print("Configuration:")
print(regfile.dump())

print("Powering on (CE high)")
adf.chip_enable()

print("Initial programming (R5..R0)")
plan = regfile.commit_all_plan()
write_plan(adf, regfile, plan)
print("Wrote %d register words" % len(plan))

print(
    "RF output should be about %.3f MHz -- probe RFOUTA with your scope"
    % (EXPECTED_RFOUT_HZ / 1e6)
)

print("Example complete.")
