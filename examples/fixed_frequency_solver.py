"""
ADF435x fixed-frequency example using the PLL solver.

Set ``TARGET_FREQ_HZ`` to the desired RF output, run on the board, and probe
RFOUTA with an oscilloscope. The solver computes INT, FRAC, MOD, prescaler,
RF divider, and band-select fields; the register file encodes and programs
them over SPI.

Hardware assumptions
--------------------
- 10 MHz reference on REFIN (R counter = 1, no doubler).
- ADF4351 on SPI1: SCK=GP10, MOSI=GP11, LE=GP13, CE=GP14.
- Loop filter and VCO match your board (lock depends on the analog front end).

Scope notes
-----------
- Frequencies below ~500 MHz are easier on a mid-range scope (200 MHz BW,
  1 GSa/s). The default target is 200 MHz.
- Higher targets (for example the datasheet 2112.6 MHz example) need a scope
  with sufficient bandwidth.
- ``result.achieved_hz`` may differ slightly from ``TARGET_FREQ_HZ`` when the
  PLL grid cannot hit the target exactly; the printed value is what to expect.

Modify pin numbers and ``TARGET_FREQ_HZ`` for your setup.
"""

from machine import SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile
from adf435x.solver import solve

# --- User settings -----------------------------------------------------------
TARGET_FREQ_HZ = 200_000_000
REF_HZ = 10_000_000

SPI_CHANNEL = 1
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11
ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14


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

device = ADF435xDevice(
    spi,
    load_enable_pin=ADF435X_LE_PIN,
    chip_enable_pin=ADF435X_CE_PIN,
)

regfile = ADF435xRegisterFile(ADF4351)

print("Solving for %.6f MHz" % (TARGET_FREQ_HZ / 1e6))
result = solve(TARGET_FREQ_HZ, REF_HZ, ADF4351)

if result.error_hz != 0:
    print(
        "Note: achieved frequency differs by %d Hz from target"
        % result.error_hz
    )

print("Solver result:")
print("  achieved_hz = %d (%.6f MHz)" % (result.achieved_hz, result.achieved_hz / 1e6))
print("  f_pfd_hz    = %d" % result.f_pfd_hz)
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
write_plan(device, regfile, regfile.commit_all_plan())
print("Wrote register words")

print(
    "RF output should be about %.6f MHz -- probe RFOUTA with your scope"
    % (result.achieved_hz / 1e6)
)

print("Example complete.")
