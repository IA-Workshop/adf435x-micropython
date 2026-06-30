"""Pytest configuration and shared fixtures."""

import pytest

from adf435x import consts
from adf435x.config import ADF435xConfig
from adf435x.profiles import ADF4351
from adf435x.register_file import ADF435xRegisterFile
from adf435x.register_mapper import ADF435xRegisterMapper

# Datasheet worked example (ADF4351, 2112.6 MHz, RF divide-by-2).
WORKED_FIELDS = {
    "int_n": 422,
    "frac": 13,
    "mod": 25,
    "band_clk_mode": consts.REG3_BAND_CLK_HIGH,
    "rf_divider": 2,
    "band_clk_div": 20,
}
WORKED_WORDS = [
    0x00D30068,
    0x080080C9,
    0x18004E42,
    0x00800003,
    0x0091403C,
    0x00580005,
]


@pytest.fixture
def mapper():
    """ADF4351 register mapper."""
    return ADF435xRegisterMapper(ADF4351)


@pytest.fixture
def worked_config():
    """Config object for the datasheet worked example."""
    return make_config(**WORKED_FIELDS)


@pytest.fixture
def worked_regfile():
    """Register file programmed to the datasheet worked example."""
    f = ADF435xRegisterFile(ADF4351)
    f.configure(**WORKED_FIELDS)
    return f


def make_config(**fields):
    """Build a config with optional field overrides."""
    c = ADF435xConfig()
    for name, value in fields.items():
        setattr(c, name, value)
    return c


class FakeDevice:
    """Record SPI writes and simulate CE / MUXOUT for synthesizer tests."""

    def __init__(self, *, muxout=0):
        self.writes = []
        self.ce = 0
        self.muxout = muxout
        self.fail_next = False

    def write_registers(self, words):
        """Append *words* to the write log or raise if configured to fail."""
        if self.fail_next:
            self.fail_next = False
            raise OSError("SPI write failed")
        self.writes.extend(words)

    def chip_enable(self):
        """Drive CE high."""
        self.ce = 1

    def chip_disable(self):
        """Drive CE low."""
        self.ce = 0

    def read_muxout(self):
        """Return the simulated MUXOUT level."""
        return self.muxout


@pytest.fixture
def fake_device():
    """Fake SPI/GPIO device for synthesizer tests."""
    return FakeDevice(muxout=1)


@pytest.fixture
def synth(fake_device):
    """ADF4351 synthesizer backed by FakeDevice."""
    from adf435x.profiles import ADF4351
    from adf435x.synthesizer import ADF435xSynthesizer

    return ADF435xSynthesizer(fake_device, ADF4351, 10_000_000)


@pytest.fixture
def mock_machine(monkeypatch):
    """Install a fake ``machine`` module for ``adf435x.device`` tests."""

    class FakePin:
        OUT = 1
        IN = 0

        def __init__(self, pin, mode, value=0):
            self.pin = pin
            self.mode = mode
            self._value = value

        def high(self):
            self._value = 1

        def low(self):
            self._value = 0

        def value(self):
            return self._value

    class FakeSPI:
        def __init__(self):
            self.writes = []

        def write(self, data):
            self.writes.append(bytes(data))

    import sys
    import types

    mod = types.ModuleType("machine")
    mod.Pin = FakePin
    mod.SPI = FakeSPI
    monkeypatch.setitem(sys.modules, "machine", mod)
    return mod
