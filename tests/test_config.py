"""Config integration for the register file: ADF435xConfig encodes through the
mapper, configure() is transactional, and dump() reports state.
"""
import pytest

from adf435x import consts
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_file import ADF435xRegisterFile

# Worked-example register words (2112.6 MHz, ADF4351).
WORKED = [0x00D30068, 0x080080C9, 0x18004E42, 0x00800003, 0x0091403C, 0x00580005]


@pytest.fixture
def worked():
    f = ADF435xRegisterFile(ADF4351)
    f.configure(int_n=422, frac=13, mod=25,
                band_clk_mode=consts.REG3_BAND_CLK_HIGH,
                rf_divider=2, band_clk_div=20)
    return f


class TestEncoding:
    def test_worked_example_words(self, worked):
        assert worked.current_words() == WORKED

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351],
                             ids=lambda p: p.name)
    def test_default_config_encodes(self, profile):
        f = ADF435xRegisterFile(profile)
        assert len(f.current_words()) == 6


class TestConfigure:
    def test_rejects_unknown_field(self, worked):
        with pytest.raises(AttributeError):
            worked.configure(no_such_field=1)

    def test_rolls_back_field_on_failure(self):
        f = ADF435xRegisterFile(ADF4350)
        with pytest.raises(ValueError):
            f.configure(rf_divider=32)        # exceeds the 4350's /16 maximum
        assert f.config.rf_divider == 1

    def test_rolls_back_words_on_failure(self):
        f = ADF435xRegisterFile(ADF4350)
        before = f.current_words()
        with pytest.raises(ValueError):
            f.configure(rf_divider=32)
        assert f.current_words() == before


class TestRetune:
    def test_frac_writes_only_r0(self, worked):
        worked.commit()
        worked.configure(frac=14)
        assert [i for i, _ in worked.commit()] == [0]

    def test_mod_forces_r0(self, worked):
        worked.commit()
        worked.configure(mod=50)
        assert [i for i, _ in worked.commit()] == [1, 0]

    def test_divider_writes_r4_and_r0(self, worked):
        worked.commit()
        worked.configure(rf_divider=4, int_n=211)
        assert [i for i, _ in worked.commit()] == [4, 0]

    def test_power_writes_only_r4(self, worked):
        worked.commit()
        worked.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert [i for i, _ in worked.commit()] == [4]


class TestDump:
    def test_clean_after_commit(self, worked):
        worked.commit()
        snap = worked.dump()
        assert snap["is_stale"] is False
        assert snap["commit_count"] == 1
        assert len(snap["registers"]) == 6

    def test_reports_stale_register_after_change(self, worked):
        worked.commit()
        worked.configure(frac=14)
        snap = worked.dump()
        assert snap["is_stale"] is True
        assert snap["registers"][0]["stale"] is True