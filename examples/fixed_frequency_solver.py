"""
Program one frequency with ``solve()`` and a register file, no synthesizer.

This shows the layers under ``ADF435xSynthesizer``: ``solve()`` works out
the PLL fields, the register file checks and encodes them, and the script
writes the words itself. The printed ``achieved_hz`` can differ slightly
from ``TARGET_FREQ_HZ`` when the target is not exactly reachable (see
docs/frequency-planning.md). The pins and the 10 MHz reference match the
reference setup in docs/hardware.md; change them for your board. MUXOUT is
not used here.
"""

from machine import Pin, SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile
from adf435x.solver import solve

# --- Settings to change ------------------------------------------------------
TARGET_FREQ_HZ = 200_000_000
REF_HZ = 10_000_000

SPI_CHANNEL = 1
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11
ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14


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

device = ADF435xDevice(
    spi,
    le_pin=ADF435X_LE_PIN,
    ce_pin=ADF435X_CE_PIN,
)

regfile = ADF435xRegisterFile(ADF4351)

print("Solving for %.6f MHz" % (TARGET_FREQ_HZ / 1e6))
result = solve(TARGET_FREQ_HZ, REF_HZ, ADF4351)

if result.error_hz != 0:
    print("Note: achieved frequency differs by %d Hz from target" % result.error_hz)

print("Solver result:")
print("  achieved_hz = %d (%.6f MHz)" % (result.achieved_hz, result.achieved_hz / 1e6))
print("  pfd_hz    = %d" % result.pfd_hz)
print("  vco_hz      = %d" % result.vco_hz)
print("  int_n       = %d" % result.fields["int_n"])
print("  frac        = %d" % result.fields["frac"])
print("  mod         = %d" % result.fields["mod"])
print("  rf_divider  = %d" % result.fields["rf_divider"])

regfile.configure(**result.fields)

print("Configuration:")
print(regfile.dump())

print("Powering on (CE high)")
device.chip_enable()

print("Initial programming (R5..R0)")
write_plan(device, regfile, regfile.full_plan())
print("Wrote register words")

print(
    "RF output should be about %.6f MHz -- probe RFOUTA with your scope"
    % (result.achieved_hz / 1e6)
)

print("Example complete.")
