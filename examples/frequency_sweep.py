"""
ADF435x frequency-sweep example using FrequencyTable and play().

Builds a linear table between lower and upper bounds, then plays it. Probe
RFOUTA to see stepped frequencies.

Hardware assumptions match ``fixed_frequency.py``.
"""

from machine import Pin, SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.sweep import FrequencyTable
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
    "muxout": 9,
}

spi = SPI(
    PINS["spi_channel"],
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    bits=8,
    sck=Pin(PINS["sck"]),
    mosi=Pin(PINS["mosi"]),
)

device = ADF435xDevice(
    spi,
    load_enable_pin=PINS["le"],
    chip_enable_pin=PINS["ce"],
    muxout_pin=PINS["muxout"],
)

synth = ADF435xSynthesizer(device, ADF4351, ref_hz=REF_HZ)

table = FrequencyTable.from_range(synth, LOWER_HZ, UPPER_HZ, STEP_HZ)
print(
    "Sweeping %.1f-%.1f MHz: %d entries, worst error %d Hz, dwell %d ms"
    % (LOWER_HZ / 1e6, UPPER_HZ / 1e6, len(table), table.max_error_hz, DWELL_US // 1000)
)
timeouts = synth.play(table, dwell_us=DWELL_US, wait_for_lock=True)
print("Sweep complete (%d lock timeouts)." % timeouts)

# Manual stepping, for example to measure at each point:
# for i in range(len(table)):
#     entry = synth.play_step(table, i)
#     print(entry.achieved_hz)
