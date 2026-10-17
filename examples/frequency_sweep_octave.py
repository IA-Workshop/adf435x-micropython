"""
Sweep across two RF divider boundaries.

With ``allow_divider_change=True`` the table plans each divider band on its
own. A hop that changes the divider waits for lock (if MUXOUT is wired) and
then waits the longer ``BOUNDARY_DWELL_US``, because the VCO takes longer to
settle after a band change. See docs/sweeps.md. Pins and reference are as
in ``fixed_frequency.py``.
"""

from machine import Pin, SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.sweep import FrequencyTable
from adf435x.synthesizer import ADF435xSynthesizer

# --- Settings to change ------------------------------------------------------
# This span crosses two divider boundaries: from /32 to /16 at 137.5 MHz, and
# from /16 to /8 at 275 MHz.
LOWER_HZ = 100_000_000
UPPER_HZ = 300_000_000
STEP_HZ = 25_000_000
REF_HZ = 10_000_000

# Wait after an in-band hop, and after a hop that changes the divider.
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
