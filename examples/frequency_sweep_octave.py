"""
ADF435x octave-crossing sweep using segmented FrequencyTable planning.

When a sweep spans several RF divider bands, ``allow_divider_change=True``
plans each band separately (one shared MOD per band where possible). A hop
that changes the divider waits for lock (when MUXOUT is wired) and uses the
longer boundary dwell for cleaner scope traces.

Hardware assumptions match ``fixed_frequency.py``.
"""

from machine import Pin, SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.sweep import FrequencyTable
from adf435x.synthesizer import ADF435xSynthesizer

# --- User settings -----------------------------------------------------------
# Span crosses two divider boundaries: /32 to /16 at 137.5 MHz and /16 to /8
# at 275 MHz.
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

print(
    "Building segmented table %.1f-%.1f MHz, step %.1f MHz"
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
for i in range(len(table)):
    entry = table[i]
    tag = " [divider /%d]" % entry.rf_divider if entry.divider_boundary else ""
    print(
        "  [%d] %.6f MHz  MOD=%d  error=%d Hz%s"
        % (i, entry.achieved_hz / 1e6, entry.fields["mod"], entry.error_hz, tag)
    )

print("Playing sweep (boundary dwell %d ms)" % (BOUNDARY_DWELL_US // 1000))
synth.play(table, dwell_us=DWELL_US, boundary_dwell_us=BOUNDARY_DWELL_US)
print("Sweep complete.")
