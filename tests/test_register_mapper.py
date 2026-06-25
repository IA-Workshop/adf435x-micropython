import pytest

from adf435x import consts
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_mapper import AD435xRegisterMapper


@pytest.fixture
def mapper():
    return AD435xRegisterMapper(ADF4351)


# --- bit-for-bit against the datasheet worked example (2112.6 MHz) ----------

class TestWorkedExample:
    def test_reg0(self, mapper):
        assert mapper.register_0(422, 13) == 0x00D30068

    def test_reg1(self, mapper):
        assert mapper.register_1(25, consts.REG1_PRESCALER_8_9, phase=1) == 0x080080C9

    def test_reg2(self, mapper):
        assert mapper.register_2(1, 7) == 0x18004E42

    def test_reg3(self, mapper):
        assert mapper.register_3(band_clk_mode=consts.REG3_BAND_CLK_HIGH) == 0x00800003

    def test_reg4(self, mapper):
        assert mapper.register_4(2, 20) == 0x0091403C

    def test_reg5(self, mapper):
        assert mapper.register_5() == 0x00580005


# --- control bits and reserved ones ----------------------------------------

class TestStructure:
    @pytest.mark.parametrize("index, word_fn", [
        (0, lambda m: m.register_0(0, 0)),
        (1, lambda m: m.register_1(2, 0)),
        (2, lambda m: m.register_2(1, 0)),
        (3, lambda m: m.register_3()),
        (4, lambda m: m.register_4(1, 20)),
        (5, lambda m: m.register_5()),
    ])
    def test_control_bits(self, mapper, index, word_fn):
        assert word_fn(mapper) & 0b111 == index

    def test_reg5_reserved_ones(self, mapper):
        assert mapper.register_5() & 0x180000 == 0x180000


# --- profile-dependent encoding --------------------------------------------

class TestDividerCode:
    def test_4351_divider_64(self):
        m = AD435xRegisterMapper(ADF4351)
        assert (m.register_4(64, 20) >> consts.REG4_RF_DIVIDER_POS) & 0b111 == 6

    def test_4350_rejects_divider_32(self):
        m = AD435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_4(32, 20)


class TestCapabilityGating:
    def test_4350_rejects_phase_adjust(self):
        m = AD435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_1(2, 0, phase_adjust=True)

    def test_4351_allows_phase_adjust(self):
        m = AD435xRegisterMapper(ADF4351)
        assert (m.register_1(2, 0, phase_adjust=True)
                >> consts.REG1_PHASE_ADJUST_POS) & 1 == 1

    def test_4350_rejects_fast_band_select(self):
        m = AD435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_3(band_clk_mode=consts.REG3_BAND_CLK_HIGH)

    def test_4350_rejects_charge_cancel(self):
        m = AD435xRegisterMapper(ADF4350)
        with pytest.raises(ValueError):
            m.register_3(charge_cancel=True)

    def test_4350_forces_abp_reserved_zero(self):
        # ABP (DB22) is reserved on the 4350; the bit must encode 0 even if a
        # 3 ns pulse is requested.
        m = AD435xRegisterMapper(ADF4350)
        word = m.register_3(abp=consts.REG3_ABP_3NS)
        assert (word >> consts.REG3_ABP_POS) & 1 == 0


# --- validation -------------------------------------------------------------

class TestValidation:
    def test_int_out_of_range(self, mapper):
        with pytest.raises(ValueError):
            mapper.register_0(1 << 16, 0)

    def test_frac_out_of_range(self, mapper):
        with pytest.raises(ValueError):
            mapper.register_0(0, 1 << 12)