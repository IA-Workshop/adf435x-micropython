"""
ADF435x octave-crossing sweep using segmented FrequencyTable planning.

When a sweep spans multiple RF divider bands, ``allow_divider_change=True``
builds an optimized sub-table per band (locked MOD, PLL grid planning within
each segment). Divider-boundary hops use a full register write, wait for lock,
and a longer dwell for cleaner scope traces.

Hardware assumptions match ``fixed_frequency.py``.
"""

from machine import SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.sweep import ADF435xSweeper, FrequencyTable
from adf435x.synthesizer import ADF435xSynthesizer

# --- User settings -----------------------------------------------------------
# Span crosses the divide-by-32 / divide-by-16 boundary near ~137.5 MHz.
LOWER_HZ = 100_000_000
UPPER_HZ = 300_000_000
STEP_HZ = 25_000_000
REF_HZ = 10_000_000

# In-band hop dwell; boundary hops always wait for lock and use BOUNDARY_DWELL_US.
DWELL_US = 100_000
BOUNDARY_DWELL_US = 500_000

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

print(
    "Building segmented table %.1f–%.1f MHz, step %.1f MHz"
    % (LOWER_HZ / 1e6, UPPER_HZ / 1e6, STEP_HZ / 1e6)
)
table = FrequencyTable.from_range(
    synth,
    LOWER_HZ,
    UPPER_HZ,
    STEP_HZ,
    allow_divider_change=True,
)
print("Table has %d entries" % len(table))
print(
    "Divider boundaries at indices:",
    [i for i, e in enumerate(table) if e.divider_boundary],
)
for i in range(len(table)):
    entry = table[i]
    tag = " [boundary]" if entry.divider_boundary else ""
    print(
        "  [%d] %.6f MHz  plan=%d word(s)%s"
        % (i, entry.achieved_hz / 1e6, len(entry.plan), tag)
    )

print("Playing sweep (boundary dwell %d ms)" % (BOUNDARY_DWELL_US // 1000))
ADF435xSweeper(
    synth,
    table,
    dwell_us=DWELL_US,
    boundary_dwell_us=BOUNDARY_DWELL_US,
).run()
print("Sweep complete.")
