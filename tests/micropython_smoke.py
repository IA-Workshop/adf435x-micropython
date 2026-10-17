"""Check that the library runs under MicroPython (not collected by pytest).

Run from the repository root on the MicroPython Unix port with
``micropython tests/micropython_smoke.py``. It prints ``SMOKE OK`` on
success; any failure raises. See docs/development.md.
"""

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")


class _PytestStub:
    """Just enough of pytest for conftest.py to import."""

    @staticmethod
    def fixture(func=None, **_kwargs):
        if func is None:
            return lambda f: f
        return func


class _FakePin:
    OUT = 1
    IN = 0

    def __init__(self, pin, mode, value=0):
        self._value = value

    def high(self):
        self._value = 1

    def low(self):
        self._value = 0

    def value(self):
        return self._value


class _FakeSPI:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(bytes(data))


class _MachineStub:
    Pin = _FakePin
    SPI = _FakeSPI


sys.modules["pytest"] = _PytestStub
# Unix port's built-in ``machine`` has no Pin/SPI; shadow it for device.py.
sys.modules["machine"] = _MachineStub

from conftest import WORKED_FIELDS, WORKED_WORDS, FakeDevice  # noqa: E402

import adf435x  # noqa: E402
from adf435x import (  # noqa: E402
    ADF4351,
    ADF435xRegisterFile,
    ADF435xSynthesizer,
    solve,
)
from adf435x.sweep import FrequencyTable  # noqa: E402

REF_HZ = 10_000_000
GOLDEN_HZ = 2_112_600_000


def check(label, ok):
    """Raise with *label* when *ok* is false."""
    if not ok:
        raise AssertionError(label)
    print("ok", label)


def main():
    regfile = ADF435xRegisterFile(ADF4351)
    regfile.configure(**WORKED_FIELDS)
    check("register file encodes golden words", regfile.current_words() == WORKED_WORDS)
    check(
        "commit plan is R5..R0",
        regfile.commit_all_plan() == list(reversed(WORKED_WORDS)),
    )

    result = solve(GOLDEN_HZ, REF_HZ, ADF4351)
    check("solver hits golden exactly", result.achieved_hz == GOLDEN_HZ)
    check(
        "solver golden fields",
        all(result.fields[k] == WORKED_FIELDS[k] for k in ("int_n", "frac", "mod")),
    )

    device = FakeDevice(muxout=1)
    synth = ADF435xSynthesizer(device, ADF4351, REF_HZ)
    synth.power_up(frequency_hz=GOLDEN_HZ)
    check(
        "power-up writes golden R5..R0", device.writes == list(reversed(WORKED_WORDS))
    )
    check("lock detect polls", synth.wait_locked(timeout_us=1_000) is True)

    table = FrequencyTable.from_range(synth, 190_000_000, 210_000_000, 2_000_000)
    check(
        "table hits every 2 MHz point exactly",
        table.max_error_hz == 0 and len(table) == 11,
    )
    before = len(device.writes)
    check(
        "sweep plays without lock timeouts",
        synth.play(table, wait_for_lock=True, boundary_dwell_us=0) == 0,
    )
    check("in-band hops are single R0 writes", len(device.writes) - before <= 6 + 10)
    check("synth ends on the last entry", synth.frequency == 210_000_000)

    from adf435x.device import ADF435xDevice

    spi = _FakeSPI()
    dev = ADF435xDevice(spi, load_enable_pin=13, chip_enable_pin=14)
    dev.write_registers(list(reversed(WORKED_WORDS)))
    check(
        "device shifts 4-byte big-endian words",
        spi.writes[-1] == WORKED_WORDS[0].to_bytes(4, "big"),
    )

    check("package root exports solve", hasattr(adf435x, "solve"))
    print("SMOKE OK")


main()
