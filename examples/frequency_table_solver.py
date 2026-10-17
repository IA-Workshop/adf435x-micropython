"""
ADF435x frequency-table example: plan a table, inspect it, then step through it.

Builds a table of output frequencies from a lower bound to an upper bound in
fixed steps, prints each entry's achieved frequency, error, and MOD, and (when
``RUN_SWEEP`` is True) programs the entries one at a time with ``play_step``
so you can observe the stepped output on a scope.

Planning needs no hardware: with ``RUN_SWEEP = False`` the script only
prints the table. See ``adf435x.sweep`` for the MOD rule.

Hardware assumptions match ``fixed_frequency.py``. Modify pin numbers,
bounds, and step for your setup.
"""

import time

from adf435x.profiles import ADF4351
from adf435x.sweep import FrequencyTable
from adf435x.synthesizer import ADF435xSynthesizer

# --- User settings -----------------------------------------------------------
LOWER_HZ = 190_000_000
UPPER_HZ = 210_000_000
STEP_HZ = 2_000_000
REF_HZ = 10_000_000

# Program each table entry on the device (False = print table only).
RUN_SWEEP = True
HOLD_MS = 500

SPI_CHANNEL = 1
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11
ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14
ADF435X_MUXOUT_PIN = 9


def make_device():
    """Open SPI and build the device handler (hardware only)."""
    from machine import SPI

    from adf435x.device import ADF435xDevice

    spi = SPI(
        SPI_CHANNEL,
        baudrate=1_000_000,
        polarity=0,
        phase=0,
        bits=8,
        sck=SPI_SCK_PIN,
        mosi=SPI_MOSI_PIN,
    )
    return ADF435xDevice(
        spi,
        load_enable_pin=ADF435X_LE_PIN,
        chip_enable_pin=ADF435X_CE_PIN,
        muxout_pin=ADF435X_MUXOUT_PIN,
    )


# Planning never touches the device, so None is fine for a print-only run.
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
