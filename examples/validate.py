"""
ADF4351 bench validation example — scope/counter checks.

Run from the host (MicroPico **Run current file** or ``mpremote run``). Requires
``adf435x/`` on flash from bulk sync; examples are not bulk-synced (see
``docs/hardware.md``).

Reference pin map (adjust for your MicroPython board):
- 10 MHz REFIN (R counter = 1, no doubler, no ref÷2).
- SPI1: SCK=GP10, MOSI=GP11, LE=GP13, CE=GP14, MUXOUT=GP9.
- 1 MHz SPI, mode 0.

Set ``SELECT`` below, or pass a case name as ``sys.argv[1]`` (``list`` prints
names). Confirm output on RFOUTA with a scope or counter; this script does not
assert pass/fail.
"""

import sys

REF_HZ = 10_000_000
LOCK_TIMEOUT_US = 500_000

PINS = {
    "spi_channel": 1,
    "sck": 10,
    "mosi": 11,
    "le": 13,
    "ce": 14,
    "muxout": 9,
}

# Bench cases — scope-friendly frequencies first, then PLL edge cases.
CASES = (
    ("scope_50mhz", {"kind": "lock", "hz": 50_000_000}),
    ("scope_75mhz", {"kind": "lock", "hz": 75_000_000}),
    ("scope_100mhz", {"kind": "lock", "hz": 100_000_000}),
    ("scope_150mhz", {"kind": "lock", "hz": 150_000_000}),
    ("scope_200mhz", {"kind": "lock", "hz": 200_000_000}),
    ("scope_250mhz", {"kind": "lock", "hz": 250_000_000}),
    ("golden_2112p6mhz", {"kind": "lock", "hz": 2_112_600_000}),
    ("cross_part_scope_137p5mhz", {"kind": "lock", "hz": 137_500_000}),
    ("adf4351_scope_equiv_132p0375mhz", {
        "kind": "lock",
        "hz": 132_037_500,
    }),
    ("adf4351_prescaler_edge_3600mhz", {
        "kind": "lock",
        "hz": 3_600_000_000,
    }),
    ("adf4351_prescaler_over_3700mhz", {
        "kind": "lock",
        "hz": 3_700_000_000,
    }),
    ("narrow_band_sweep", {
        "kind": "sweep",
        "lower_hz": 140_000_000,
        "upper_hz": 145_000_000,
        "step_hz": 1_000_000,
        "dwell_us": 500_000,
    }),
)

CASE_NAMES = tuple(name for name, _ in CASES) + ("list",)

# Edit before run, or override via sys.argv[1].
SELECT = "scope_200mhz"


def make_synth():
    """Build a synthesizer on the maintainer reference pin map."""
    from machine import Pin, SPI

    from adf435x.device import ADF435xDevice
    from adf435x.profiles import ADF4351
    from adf435x.synthesizer import ADF435xSynthesizer

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
    return ADF435xSynthesizer(
        device,
        ADF4351,
        ref_hz=REF_HZ,
        r_counter=1,
        doubler=False,
        rdiv2=False,
    )


def _print_list():
    """Print available case names (no hardware)."""
    print("Available cases:")
    for name in CASE_NAMES:
        print("  %s" % name)
    print("Set SELECT or pass case name as sys.argv[1].")
    print("Scope-friendly sweeps: see frequency_sweep.py.")


def _print_lock_point(slug, target_hz, synth):
    """Program one frequency and print measurement hints."""
    synth.power_up(frequency_hz=target_hz)
    locked = synth.wait_locked(timeout_us=LOCK_TIMEOUT_US)
    print("--- %s ---" % slug)
    print("Target:    %d Hz (%.6f MHz)" % (target_hz, target_hz / 1e6))
    print("Achieved:  %d Hz (%.6f MHz)" % (
        synth.achieved_hz,
        synth.achieved_hz / 1e6,
    ))
    print("MUXOUT:    %s" % ("high" if locked else "not high within timeout"))
    print("Probe RFOUTA with scope or counter.")


def _run_narrow_sweep(synth, spec):
    """Step 140–145 MHz; print each achieved frequency for bench use."""
    from adf435x.sweep import ADF435xSweeper, FrequencyTable

    lower = spec["lower_hz"]
    upper = spec["upper_hz"]
    step = spec["step_hz"]
    dwell = spec["dwell_us"]
    print("--- narrow_band_sweep ---")
    print("Range: %d–%d Hz, step %d Hz, dwell %d us" % (
        lower,
        upper,
        step,
        dwell,
    ))
    print("(Divider exercise; for wide scope sweeps use frequency_sweep.py.)")
    synth.power_up(frequency_hz=lower)
    synth.wait_locked(timeout_us=LOCK_TIMEOUT_US)
    table = FrequencyTable.from_range(synth, lower, upper, step)
    player = ADF435xSweeper(synth, table, dwell_us=dwell)
    while True:
        achieved = player.step()
        if achieved is None:
            break
        print("  Step: %d Hz (%.6f MHz)" % (achieved, achieved / 1e6))
    print("Sweep complete.")


def run(selected):
    """Run the named validation case."""
    if selected == "list":
        _print_list()
        return

    if selected not in CASE_NAMES:
        raise ValueError(
            "Unknown case: %s (try 'list')" % selected
        )

    if selected == "narrow_band_sweep":
        spec = dict(CASES)[selected]
        synth = make_synth()
        _run_narrow_sweep(synth, spec)
        return

    spec = dict(CASES)[selected]
    synth = make_synth()
    _print_lock_point(selected, spec["hz"], synth)


def main():
    """Resolve selection and run one validation case."""
    selected = sys.argv[1] if len(sys.argv) > 1 else SELECT
    run(selected)


if __name__ == "__main__":
    main()
