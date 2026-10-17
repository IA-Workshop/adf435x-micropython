"""Host benchmarks for adf435x (CPython or the MicroPython Unix port).

From the repository root::

    python bench/bench.py
    micropython bench/bench.py

Times the solver, table building, and table playback against a do-nothing
device. Results are relative only: the Unix port is not an MCU. On-target
numbers come from the bench (remediation step B7).
"""

import sys
import time

sys.path.insert(0, ".")

from adf435x import ADF4351, ADF435xSynthesizer, FrequencyTable, solve  # noqa: E402

REF_HZ = 10_000_000


class NullDevice:
    """Accepts every call; MUXOUT reads locked."""

    def write_registers(self, words):
        pass

    def chip_enable(self):
        pass

    def chip_disable(self):
        pass

    def read_muxout(self):
        return 1


if hasattr(time, "ticks_us"):

    def now_us():
        return time.ticks_us()

    def elapsed_us(start):
        return time.ticks_diff(time.ticks_us(), start)

else:

    def now_us():
        return time.perf_counter()

    def elapsed_us(start):
        return (time.perf_counter() - start) * 1_000_000


def bench(label, count, fn):
    """Run *fn* *count* times and print the mean in microseconds."""
    start = now_us()
    for i in range(count):
        fn(i)
    print("%-40s %10.1f us" % (label, elapsed_us(start) / count))


def main():
    targets = [35_000_000 + (i * 2_147_483_647) % 4_365_000_000 for i in range(200)]
    bench("solve (arbitrary target)", len(targets), lambda i: solve(targets[i], REF_HZ, ADF4351))
    bench("solve (golden 2112.6 MHz)", 200, lambda i: solve(2_112_600_000, REF_HZ, ADF4351))

    synth = ADF435xSynthesizer(NullDevice(), ADF4351, REF_HZ)
    synth.power_up(frequency_hz=433_050_000)
    bench(
        "FrequencyTable.from_range, 71 points",
        5,
        lambda i: FrequencyTable.from_range(synth, 433_050_000, 434_790_000, 25_000),
    )
    table = FrequencyTable.from_range(synth, 433_050_000, 434_790_000, 25_000)
    synth.play_step(table, 0)
    bench("play_step (in-band hop)", 500, lambda i: synth.play_step(table, 1 + i % 70))
    bench("set_frequency (retune)", 200, lambda i: synth.set_frequency(targets[i] // 2 + 200_000_000))


main()
