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


def commit(regfile):
    """Plan a minimal write and mark it written, as a successful SPI write would.

    Returns the plan (R5..R0 order); an empty plan marks nothing.
    """
    plan = regfile.commit_plan()
    if plan:
        regfile.mark_written()
    return plan


def commit_all(regfile):
    """Plan a full six-word write and mark it written."""
    plan = regfile.commit_all_plan()
    regfile.mark_written()
    return plan


def make_config(**fields):
    """Build a config with optional field overrides."""
    c = ADF435xConfig()
    for name, value in fields.items():
        setattr(c, name, value)
    return c


class FakeDevice:
    """Record SPI writes and simulate CE / MUXOUT for synthesizer tests.

    Pass ``muxout=None`` to model a board with no MUXOUT pin wired;
    ``read_muxout`` then raises like ``ADF435xDevice`` does.
    """

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
        if self.muxout is None:
            raise RuntimeError("MUXOUT pin was not configured")
        return self.muxout


# Double-buffered bit masks per ADF4351 data sheet p.12 and Figure 23.
# R1: phase DB26:DB15, MOD DB14:DB3. R2: doubler DB25, RDIV2 DB24,
# R counter DB23:DB14, CP current DB12:DB9. These latch on the next R0 write;
# all other bits take effect immediately.
_DBR_MASKS = {
    consts.REG1_ADDR: (0xFFF << 15) | (0xFFF << 3),
    consts.REG2_ADDR: (1 << 25) | (1 << 24) | (0x3FF << 14) | (0xF << 9),
}
# R4 RF divider select DB22:DB20 latches on R0 only while R2 DB13 is set.
_DBB_MASK = 0x7 << 20


class FakeChip(FakeDevice):
    """FakeDevice that also models the chip's register latching.

    ``input_words[n]`` is the last word shifted into register Rn.
    ``active_words[n]`` is what the device is actually using: immediate bits
    update on write, double-buffered bits (``_DBR_MASKS``, and the R4
    divider while R2 DB13 is set) update only on a subsequent R0 write.
    Entries are ``None`` until written.

    The model follows the data sheet text only; bench tests confirm it.
    """

    def __init__(self, *, muxout=0):
        super().__init__(muxout=muxout)
        self.input_words = [None] * consts.NUM_REGISTERS
        self.active_words = [None] * consts.NUM_REGISTERS

    def write_registers(self, words):
        """Log the words as FakeDevice does, then apply chip latching."""
        super().write_registers(words)
        for word in words:
            self._latch(word)

    def _buffered_mask(self, index):
        """Bits of register *index* that wait for an R0 write."""
        if index == consts.REG4_ADDR:
            r2 = self.active_words[consts.REG2_ADDR] or 0
            if (r2 >> consts.REG2_DOUBLE_BUFFER_POS) & 1:
                return _DBB_MASK
            return 0
        return _DBR_MASKS.get(index, 0)

    def _latch(self, word):
        index = word & 0x7
        self.input_words[index] = word
        mask = self._buffered_mask(index)
        old = self.active_words[index]
        if old is None or not mask:
            # First write latches everything; unbuffered registers too.
            self.active_words[index] = word
        else:
            self.active_words[index] = (old & mask) | (word & ~mask)
        if index == consts.REG0_ADDR:
            for r in (consts.REG1_ADDR, consts.REG2_ADDR, consts.REG4_ADDR):
                if self.input_words[r] is not None:
                    self.active_words[r] = self.input_words[r]

    def output_hz(self, ref_hz):
        """Exact RF output frequency from the active words, as a Fraction.

        Assumes fundamental feedback (the only mode this library uses).
        """
        from fractions import Fraction

        r0, r1, r2, _r3, r4, _r5 = self.active_words
        int_n = (r0 >> consts.REG0_INT_POS) & 0xFFFF
        frac = (r0 >> consts.REG0_FRAC_POS) & 0xFFF
        mod = (r1 >> consts.REG1_MOD_POS) & 0xFFF
        r_counter = (r2 >> consts.REG2_R_COUNTER_POS) & 0x3FF
        doubler = (r2 >> consts.REG2_DOUBLER_POS) & 1
        rdiv2 = (r2 >> consts.REG2_RDIV2_POS) & 1
        divider = 1 << ((r4 >> consts.REG4_RF_DIVIDER_POS) & 0x7)
        f_pfd = Fraction(ref_hz * (1 + doubler), r_counter * (1 + rdiv2))
        return (int_n + Fraction(frac, mod)) * f_pfd / divider


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace the synthesizer's sleep with a recorder (no real delay)."""
    sleeps = []
    monkeypatch.setattr("adf435x.synthesizer._sleep_us", sleeps.append)
    return sleeps


@pytest.fixture
def fake_device():
    """Fake SPI/GPIO device for synthesizer tests."""
    return FakeDevice(muxout=1)


@pytest.fixture
def fake_chip():
    """FakeChip with MUXOUT reading locked."""
    return FakeChip(muxout=1)


@pytest.fixture
def synth(fake_device):
    """ADF4351 synthesizer backed by FakeDevice."""
    from adf435x.profiles import ADF4351
    from adf435x.synthesizer import ADF435xSynthesizer

    return ADF435xSynthesizer(fake_device, ADF4351, 10_000_000)


@pytest.fixture
def chip_synth(fake_chip):
    """ADF4351 synthesizer (10 MHz reference) backed by FakeChip."""
    from adf435x.profiles import ADF4351
    from adf435x.synthesizer import ADF435xSynthesizer

    return ADF435xSynthesizer(fake_chip, ADF4351, 10_000_000)


@pytest.fixture
def mock_machine(monkeypatch):
    """Install a fake ``machine`` module for ``adf435x.device`` tests."""

    class FakePin:
        OUT = 1
        IN = 0

        def __init__(self, pin, mode=None, value=0):
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
        def __init__(self, *args, **kwargs):
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
