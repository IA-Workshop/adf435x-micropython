"""
Set register fields by hand with ``ADF435xRegisterFile``, then program them.

Uses the PLL numbers from the ADF4351 data sheet worked example (p.21) but
with the RF divider at 32 instead of 2, so the output is low enough for a
200 MHz oscilloscope. ADF4351 only, since the ADF4350 cannot divide by 32.
Change the pin numbers for your board. With a 10 MHz reference (symbols as
in docs/symbols.md):

    fPFD = REFIN / R = 10 MHz
    fVCO = fPFD * (INT + FRAC/MOD) = 10 MHz * 422.52 = 4225.2 MHz
    fOUT = fVCO / RF divider = 4225.2 MHz / 32 = 132.0375 MHz
"""

from machine import Pin, SPI

from adf435x import consts
from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile

# Pin numbers: change these to match your wiring.
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11
ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14

SPI_CHANNEL = 1

# Expected output with a 10 MHz reference and the fields below.
EXPECTED_RFOUT_HZ = 132_037_500


def write_plan(device, regfile, plan):
    """Write *plan*, then tell the register file whether it worked."""
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
    sck=Pin(SPI_SCK_PIN),
    mosi=Pin(SPI_MOSI_PIN),
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
    "RF output should be %.4f MHz -- probe RFOUTA with your scope"
    % (EXPECTED_RFOUT_HZ / 1e6)
)

print("Example complete.")
