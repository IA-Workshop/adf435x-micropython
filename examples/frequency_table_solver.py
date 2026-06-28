"""
ADF435x frequency-table example using the PLL solver.

Builds a table of achievable output frequencies between a lower and upper
bound, spaced as closely as the hardware grid allows to a requested step.
The channel spacing is set by MOD and fPFD; this script solves the endpoints,
locks MOD from the lower frequency, enumerates the PLL grid, and picks table
entries nearest each ``lower + n * STEP_HZ`` point.

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
from adf435x.solver import SolveOptions, solve

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


def _achievable_rf_hz(n_num, mod, f_pfd, rf_divider):
    """RF output in hertz for fractional-N numerator *n_num* (N = n_num / mod)."""
    vco_hz = (n_num * f_pfd) // mod
    return vco_hz // rf_divider


def _enumerate_achievable_hz(n_low, n_high, mod, f_pfd, rf_divider):
    """
    List every RF output frequency on the PLL grid from *n_low* to *n_high*.

    Parameters
    ----------
    n_low, n_high : int
        Inclusive fractional-N numerators (INT * MOD + FRAC).
    mod : int
        Fractional modulus.
    f_pfd : int
        PFD frequency in hertz.
    rf_divider : int
        RF output divider.

    Returns
    -------
    list of int
        Sorted unique achievable RF frequencies in hertz.
    """
    freqs = []
    for n_num in range(n_low, n_high + 1):
        freqs.append(_achievable_rf_hz(n_num, mod, f_pfd, rf_divider))
    return sorted(set(freqs))


def _pick_step_grid(achievable_hz, step_hz):
    """
    Select grid points closest to each ``start + n * step`` target.

    Always includes the first and last achievable frequencies in the range.

    Parameters
    ----------
    achievable_hz : list of int
        Sorted achievable frequencies (ascending).
    step_hz : int
        Desired spacing between table entries in hertz.

    Returns
    -------
    list of int
        Selected RF frequencies for the sweep table.
    """
    if not achievable_hz:
        return []
    if step_hz <= 0:
        raise ValueError("step_hz must be positive")

    selected = [achievable_hz[0]]
    while True:
        goal = selected[-1] + step_hz
        if goal > achievable_hz[-1]:
            break
        best = min(achievable_hz, key=lambda f: abs(f - goal))
        if best <= selected[-1]:
            break
        selected.append(best)

    if selected[-1] != achievable_hz[-1]:
        selected.append(achievable_hz[-1])
    return selected


def build_frequency_table(lower_hz, upper_hz, step_hz, ref_hz, profile):
    """
    Build a sweep table between *lower_hz* and *upper_hz*.

    Solves the endpoints, locks MOD from the lower solve, verifies both ends
    share the same RF divider, enumerates the PLL grid, and picks entries
    nearest the requested step.

    Parameters
    ----------
    lower_hz, upper_hz : int
        Frequency bounds in hertz (lower must not exceed upper).
    step_hz : int
        Desired table spacing in hertz.
    ref_hz : int
        Reference input frequency in hertz.
    profile : ADF435xDeviceProfile
        Device profile (ADF4350 or ADF4351).

    Returns
    -------
    tuple of (list, int)
        ``(entries, channel_step_hz)`` where each entry is a ``SolveResult``
        and ``channel_step_hz`` is the RF channel spacing from MOD and fPFD.
    """
    if lower_hz > upper_hz:
        raise ValueError("lower_hz must not exceed upper_hz")

    low = solve(lower_hz, ref_hz, profile)
    mod = low.fields["mod"]
    rf_divider = low.fields["rf_divider"]
    opts = SolveOptions(mod=mod)

    high = solve(upper_hz, ref_hz, profile, options=opts)
    if high.fields["rf_divider"] != rf_divider:
        raise ValueError(
            "Lower and upper frequencies need different RF dividers "
            "(octave crossing); narrow the range"
        )

    f_pfd = low.f_pfd_hz
    channel_step_hz = f_pfd // mod // rf_divider

    n_low = low.fields["int_n"] * mod + low.fields["frac"]
    n_high = high.fields["int_n"] * mod + high.fields["frac"]
    if n_low > n_high:
        n_low, n_high = n_high, n_low

    achievable = _enumerate_achievable_hz(
        n_low, n_high, mod, f_pfd, rf_divider
    )
    table_hz = _pick_step_grid(achievable, step_hz)

    entries = []
    for hz in table_hz:
        entries.append(solve(hz, ref_hz, profile, options=opts))
    return entries, channel_step_hz


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
    plan = regfile.commit_all_plan()
    write_plan(device, regfile, plan)
    print(
        "  [0] %.6f MHz programmed"
        % (table[0].achieved_hz / 1e6)
    )
    time.sleep_ms(HOLD_MS)

    for i, entry in enumerate(table[1:], start=1):
        regfile.configure(**entry.fields)
        plan = regfile.commit_plan()
        write_plan(device, regfile, plan)
        print(
            "  [%d] %.6f MHz programmed"
            % (i, entry.achieved_hz / 1e6)
        )
        time.sleep_ms(HOLD_MS)

    print("Sweep complete -- probe RFOUTA to verify stepped frequencies.")
    print("Example complete.")
