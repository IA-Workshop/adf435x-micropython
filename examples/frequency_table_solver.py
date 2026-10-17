"""
Plan a frequency table, print it, then step through it.

Prints each entry's achieved frequency, error and MOD. With ``RUN_SWEEP``
True it then programs the entries one at a time with ``play_step()``. With
``RUN_SWEEP`` False it only prints the table and needs no hardware. How MOD
is chosen: docs/sweeps.md. Pins and reference are as in
``fixed_frequency.py``.
"""

import time

from adf435x.profiles import ADF4351
from adf435x.sweep import FrequencyTable
from adf435x.synthesizer import ADF435xSynthesizer

# --- Settings to change ------------------------------------------------------
LOWER_HZ = 190_000_000
UPPER_HZ = 210_000_000
STEP_HZ = 2_000_000
REF_HZ = 10_000_000

# False: print the table only, without touching the hardware.
RUN_SWEEP = True
HOLD_MS = 500

SPI_CHANNEL = 1
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11
ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14
ADF435X_MUXOUT_PIN = 9


def make_device():
    """Open SPI and return an ``ADF435xDevice`` (needs the board)."""
    from machine import Pin, SPI

    from adf435x.device import ADF435xDevice

    spi = SPI(
        SPI_CHANNEL,
        baudrate=1_000_000,
        polarity=0,
        phase=0,
        bits=8,
        sck=Pin(SPI_SCK_PIN),
        mosi=Pin(SPI_MOSI_PIN),
    )
    return ADF435xDevice(
        spi,
        le_pin=ADF435X_LE_PIN,
        ce_pin=ADF435X_CE_PIN,
        muxout_pin=ADF435X_MUXOUT_PIN,
    )


# Planning never uses the device, so None works for a print-only run.
synth = ADF435xSynthesizer(make_device() if RUN_SWEEP else None, ADF4351, REF_HZ)

print(
    "Planning %.3f-%.3f MHz in %.3f MHz steps"
    % (LOWER_HZ / 1e6, UPPER_HZ / 1e6, STEP_HZ / 1e6)
)
table = FrequencyTable.from_range(synth, LOWER_HZ, UPPER_HZ, STEP_HZ)
print(
    "%d entries, channel step %d Hz, worst error %d Hz"
    % (len(table), table.channel_step_hz, table.max_error_hz)
)
for i in range(len(table)):
    entry = table[i]
    print(
        "  [%d] %.6f MHz  error %d Hz  MOD %d"
        % (i, entry.achieved_hz / 1e6, entry.error_hz, entry.fields["mod"])
    )

if not RUN_SWEEP:
    print("RUN_SWEEP is False; table only.")
else:
    for i in range(len(table)):
        entry = synth.play_step(table, i)
        print("  [%d] %.6f MHz programmed" % (i, entry.achieved_hz / 1e6))
        time.sleep_ms(HOLD_MS)
    print("Sweep complete -- probe RFOUTA to verify stepped frequencies.")
