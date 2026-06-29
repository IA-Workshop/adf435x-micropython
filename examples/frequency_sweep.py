"""
ADF435x frequency-sweep example using ADF435xSweeper.

Plays a linear table between lower and upper bounds. Probe RFOUTA to see
stepped frequencies.

Hardware assumptions match ``fixed_frequency.py``.
"""

from machine import SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.sweep import ADF435xSweeper
from adf435x.synthesizer import ADF435xSynthesizer

# --- User settings -----------------------------------------------------------
LOWER_HZ = 190_000_000
UPPER_HZ = 210_000_000
STEP_HZ = 2_000_000
REF_HZ = 10_000_000
DWELL_US = 500_000

PINS = {
    "spi_channel": 1,
    "sck": 10,
    "mosi": 11,
    "le": 13,
    "ce": 14,
    "muxout": 15,
}

spi = SPI(
    PINS["spi_channel"],
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    bits=8,
    sck=PINS["sck"],
    mosi=PINS["mosi"],
)

device = ADF435xDevice(
    spi,
    load_enable_pin=PINS["le"],
    chip_enable_pin=PINS["ce"],
    muxout_pin=PINS["muxout"],
)

synth = ADF435xSynthesizer(device, ADF4351, ref_hz=REF_HZ)

# One-shot linear sweep (builds table internally):
print(
    "Sweeping %.1f–%.1f MHz, step %.1f MHz, dwell %d ms"
    % (LOWER_HZ / 1e6, UPPER_HZ / 1e6, STEP_HZ / 1e6, DWELL_US // 1000)
)
ADF435xSweeper.run_range(
    synth,
    LOWER_HZ,
    UPPER_HZ,
    STEP_HZ,
    dwell_us=DWELL_US,
)
print("Sweep complete.")

# Reusable table + manual stepping (commented):
# table = FrequencyTable.from_range(synth, LOWER_HZ, UPPER_HZ, STEP_HZ)
# print("Table has %d entries, channel step %d Hz" % (
#     len(table), table.channel_step_hz,
# ))
# player = ADF435xSweeper(synth, table, dwell_us=DWELL_US)
# while player.step() is not None:
#     pass
