"""
Bench checks for an ADF4351: program one test case and print what to expect.

Pick a case with ``SELECT`` below, or pass its name as the first argument;
``list`` prints the names. Check RFOUTA with a scope or frequency counter:
the script reports lock but does not decide pass or fail. The library must
already be on the board (docs/development.md). Pins and the 10 MHz reference
match the reference setup in docs/hardware.md. Case list:
docs/examples/validation.md.
"""

import sys
import time

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

# Frequencies a scope can show come first, then PLL edge cases.
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

# The case to run, unless one is given on the command line.
SELECT = "scope_200mhz"


def make_synth():
    """Return a synthesizer on the reference pin map."""
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
    """Print the case names. Needs no hardware."""
    print("Available cases:")
    for name in CASE_NAMES:
        print("  %s" % name)
    print("Set SELECT or pass case name as sys.argv[1].")
    print("Scope-friendly sweeps: see frequency_sweep.py.")


def _print_lock_point(slug, target_hz, synth):
    """Program one frequency and print what the instrument should show."""
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
    """Step through the sweep in *spec*, printing each achieved frequency."""
    from adf435x.sweep import FrequencyTable

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
    print("(Single /16 band; for wide scope sweeps use frequency_sweep.py.)")
    synth.power_up(frequency_hz=lower)
    synth.wait_locked(timeout_us=LOCK_TIMEOUT_US)
    table = FrequencyTable.from_range(synth, lower, upper, step)
    for i in range(len(table)):
        entry = synth.play_step(table, i)
        locked = synth.wait_locked(timeout_us=LOCK_TIMEOUT_US)
        print(
            "  Step: %d Hz (%.6f MHz)%s"
            % (entry.achieved_hz, entry.achieved_hz / 1e6, "" if locked else " NO LOCK")
        )
        time.sleep_us(dwell)
    print("Sweep complete.")


def run(selected):
    """Run the case named *selected*."""
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
    """Run the case named on the command line, or ``SELECT``."""
    selected = sys.argv[1] if len(sys.argv) > 1 else SELECT
    run(selected)


if __name__ == "__main__":
    main()
