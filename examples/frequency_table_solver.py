"""
ADF435x frequency-table example using the PLL solver.

Builds a table of achievable output frequencies between a lower and upper
bound, spaced as closely as the hardware grid allows to a requested step.
See ``adf435x.solver.build_frequency_table()`` for the planning logic.

When ``RUN_SWEEP`` is True, the script programs each table entry in order so
you can observe the stepped output on a scope. Set it False to print the table
only.

Hardware assumptions match ``fixed_frequency_solver.py``.

Modify pin numbers, bounds, and step for your setup.
"""

import time

from machine import SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile
from adf435x.solver import build_frequency_table

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


def write_plan(device, regfile, plan):
    """Write a commit plan to the chip and update the register-file cache."""
    try:
        device.write_registers(plan)
        regfile.mark_written()
    except Exception:
        regfile.mark_write_failed()
        raise


print("Building frequency table")
print(
    "  lower = %.3f MHz  upper = %.3f MHz  step = %.3f MHz"
    % (LOWER_HZ / 1e6, UPPER_HZ / 1e6, STEP_HZ / 1e6)
)

table, channel_step_hz = build_frequency_table(
    LOWER_HZ, UPPER_HZ, STEP_HZ, REF_HZ, ADF4351
)

print("PLL channel step at RF = %d Hz (%.3f kHz)" % (
    channel_step_hz,
    channel_step_hz / 1e3,
))
print("Table has %d entries:" % len(table))
for i, entry in enumerate(table):
    print(
        "  [%d] target grid -> %.6f MHz (error %d Hz)"
        % (i, entry.achieved_hz / 1e6, entry.error_hz)
    )

if not RUN_SWEEP:
    print("RUN_SWEEP is False; table only.")
    print("Example complete.")
else:
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

    print("Powering on (CE high)")
    device.chip_enable()

    print("Initial programming (R5..R0)")
    regfile.configure(**table[0].fields)
    write_plan(device, regfile, regfile.commit_all_plan())
    print(
        "  [0] %.6f MHz programmed"
        % (table[0].achieved_hz / 1e6)
    )
    time.sleep_ms(HOLD_MS)

    for i, entry in enumerate(table[1:], start=1):
        regfile.configure(
            int_n=entry.fields["int_n"],
            frac=entry.fields["frac"],
        )
        write_plan(device, regfile, regfile.commit_plan())
        print(
            "  [%d] %.6f MHz programmed"
            % (i, entry.achieved_hz / 1e6)
        )
        time.sleep_ms(HOLD_MS)

    print("Sweep complete -- probe RFOUTA to verify stepped frequencies.")
    print("Example complete.")
