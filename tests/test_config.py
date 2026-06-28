"""Config integration for the register file: ADF435xConfig encodes through the
mapper, configure() is transactional, and dump() reports state.
"""
import pytest

from adf435x import consts
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_file import ADF435xRegisterFile

# Worked-example register words (2112.6 MHz, ADF4351).
WORKED = [0x00D30068, 0x080080C9, 0x18004E42, 0x00800003, 0x0091403C, 0x00580005]


def _plan_indices(plan: list) -> list:
    return [word & 0b111 for word in plan]


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

    def test_rolls_back_on_non_value_error(self):
        # A wrong-typed value raises TypeError during encoding, not ValueError.
        # The file must still be restored and the original error re-raised.
        f = ADF435xRegisterFile(ADF4350)
        before_int_n = f.config.int_n
        before_words = f.current_words()
        with pytest.raises(TypeError):
            f.configure(int_n="not-an-int")
        assert f.config.int_n == before_int_n
        assert f.current_words() == before_words


class TestRetune:
    def test_frac_writes_only_r0(self, worked):
        worked.commit()
        worked.configure(frac=14)
        assert _plan_indices(worked.commit()) == [0]

    def test_mod_forces_r0(self, worked):
        worked.commit()
        worked.configure(mod=50)
        assert _plan_indices(worked.commit()) == [1, 0]

    def test_divider_writes_r4_and_r0(self, worked):
        worked.commit()
        worked.configure(rf_divider=4, int_n=211)
        assert _plan_indices(worked.commit()) == [4, 0]

    def test_power_writes_only_r4(self, worked):
        worked.commit()
        worked.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert _plan_indices(worked.commit()) == [4]


class TestSelectiveReencode:
    def test_frac_only_changes_r0_word(self, worked):
        worked.commit()
        before = worked.current_words()
        worked.configure(frac=14)
        after = worked.current_words()
        assert after[0] != before[0]
        assert after[1:] == before[1:]

    def test_phase_only_changes_r1_word(self, worked):
        # phase is an R1 field that shares no encoding with the PLL-paired R0,
        # so changing it must leave every other word byte-identical.
        worked.commit()
        before = worked.current_words()
        worked.configure(phase=2)
        after = worked.current_words()
        assert after[1] != before[1]
        assert after[0] == before[0]
        assert after[2:] == before[2:]

    def test_muxout_only_changes_r2_word(self, worked):
        worked.commit()
        before = worked.current_words()
        worked.configure(muxout=consts.REG2_MUX_DVDD)
        after = worked.current_words()
        assert after[2] != before[2]
        assert after[0:2] == before[0:2]
        assert after[3:] == before[3:]

    def test_clockdiv_only_changes_r3_word(self, worked):
        worked.commit()
        before = worked.current_words()
        worked.configure(clockdiv_value=100)
        after = worked.current_words()
        assert after[3] != before[3]
        assert after[0:3] == before[0:3]
        assert after[4:] == before[4:]

    def test_output_power_only_changes_r4_word(self, worked):
        worked.commit()
        before = worked.current_words()
        worked.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        after = worked.current_words()
        assert after[4] != before[4]
        assert after[0:4] == before[0:4]
        assert after[5] == before[5]

    def test_lock_pin_only_changes_r5_word(self, worked):
        worked.commit()
        before = worked.current_words()
        worked.configure(lock_pin=consts.REG5_LOCK_LOW)
        after = worked.current_words()
        assert after[5] != before[5]
        assert after[0:5] == before[0:5]


class TestSelectivePllCheck:
    """The cross-register PLL check must still fire on the selective path
    whenever R0 or R1 is touched, and must run only once for the R0/R1 pair.
    """

    def test_configure_frac_ge_mod_rejected(self, worked):
        # frac (R0) vs mod (R1): the relation is validated even though only R0
        # is in the dirty set.
        worked.commit()
        with pytest.raises(ValueError, match="must be less than MOD"):
            worked.configure(frac=worked.config.mod)

    def test_configure_mod_below_frac_rejected(self, worked):
        # mod (R1) vs frac (R0): validated when only R1 is dirty.
        worked.commit()
        with pytest.raises(ValueError, match="must be less than MOD"):
            worked.configure(mod=worked.config.frac)

    def test_configure_non_pll_field_skips_check(self, worked, monkeypatch):
        # Touching only R2..R5 must not invoke the PLL check at all.
        calls = []
        original = worked._mapper.check_pll
        monkeypatch.setattr(
            worked._mapper, "check_pll",
            lambda *a, **k: calls.append(a) or original(*a, **k))
        worked.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert calls == []

    def test_configure_r0_and_r1_checks_pll_once(self, worked, monkeypatch):
        # Changing R0 and R1 together must validate the pair a single time, not
        # once per register.
        calls = []
        original = worked._mapper.check_pll
        monkeypatch.setattr(
            worked._mapper, "check_pll",
            lambda *a, **k: calls.append(a) or original(*a, **k))
        worked.configure(int_n=211, mod=50)
        assert len(calls) == 1


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