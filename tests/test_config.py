"""Config integration for the register file: ADF435xConfig encodes through the
mapper, configure() is transactional, and dump() reports state.
"""

import pytest

from adf435x import consts
from adf435x.config import (
    ADF435xConfig,
    FIELD_NAMES,
    FIELD_REGISTER,
    _DEFAULTS,
    _FIELDS,
)
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_file import ADF435xRegisterFile

from conftest import WORKED_WORDS


def _plan_indices(plan: list) -> list:
    return [word & 0b111 for word in plan]


class TestFieldSchema:
    def test_derived_views_match_fields(self):
        assert set(_FIELDS) == set(_DEFAULTS) == set(FIELD_REGISTER)
        assert FIELD_NAMES == tuple(_FIELDS)
        for name, (reg, default) in _FIELDS.items():
            assert FIELD_REGISTER[name] == reg
            assert _DEFAULTS[name] == default

    def test_register_indices_in_range(self):
        for name, (reg, _) in _FIELDS.items():
            assert 0 <= reg < consts.NUM_REGISTERS, name


class TestEncoding:
    def test_worked_regfile_example_words(self, worked_regfile):
        assert worked_regfile.current_words() == WORKED_WORDS

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_default_config_encodes(self, profile):
        f = ADF435xRegisterFile(profile)
        assert len(f.current_words()) == 6


class TestInstanceIsolation:
    """Config instances hold per-object state, not shared class attributes."""

    def test_fresh_instances_are_independent(self):
        a = ADF435xConfig()
        b = ADF435xConfig()
        a.int_n = 100
        assert b.int_n == _DEFAULTS["int_n"]

    def test_defaults_match_module_dict(self):
        cfg = ADF435xConfig()
        for name, expected in _DEFAULTS.items():
            assert getattr(cfg, name) == expected

    def test_init_applies_overrides_only(self):
        cfg = ADF435xConfig(int_n=422, frac=13)
        assert cfg.int_n == 422
        assert cfg.frac == 13
        assert cfg.mod == _DEFAULTS["mod"]

    def test_copy_preserves_all_fields(self):
        original = ADF435xConfig(int_n=422, frac=13, mod=25)
        clone = original.copy()
        for name in FIELD_NAMES:
            assert getattr(clone, name) == getattr(original, name)

    def test_copy_is_independent(self):
        original = ADF435xConfig(int_n=422)
        clone = original.copy()
        clone.int_n = 500
        assert original.int_n == 422


class TestConfigure:
    def test_rejects_unknown_field(self, worked_regfile):
        with pytest.raises(AttributeError):
            worked_regfile.configure(no_such_field=1)

    def test_init_rejects_unknown_field(self):
        with pytest.raises(AttributeError):
            ADF435xConfig(no_such_field=1)

    def test_copy_is_independent(self, worked_regfile):
        clone = worked_regfile.config.copy()
        clone.frac = 14
        assert worked_regfile.config.frac == 13
        assert clone.frac == 14

    def test_two_register_files_do_not_share_config(self):
        a = ADF435xRegisterFile(ADF4351)
        b = ADF435xRegisterFile(ADF4351)
        a.configure(muxout=consts.REG2_MUX_DGND)
        assert a.config.muxout == consts.REG2_MUX_DGND
        assert b.config.muxout == consts.REG2_MUX_DIGITALLOCK

    def test_rolls_back_field_on_failure(self):
        f = ADF435xRegisterFile(ADF4350)
        with pytest.raises(ValueError):
            f.configure(rf_divider=32)  # exceeds the 4350's /16 maximum
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
    def test_frac_writes_only_r0(self, worked_regfile):
        worked_regfile.commit()
        worked_regfile.configure(frac=14)
        assert _plan_indices(worked_regfile.commit()) == [0]

    def test_mod_forces_r0(self, worked_regfile):
        worked_regfile.commit()
        worked_regfile.configure(mod=50)
        assert _plan_indices(worked_regfile.commit()) == [1, 0]

    def test_divider_writes_r4_and_r0(self, worked_regfile):
        worked_regfile.commit()
        worked_regfile.configure(rf_divider=4, int_n=211)
        assert _plan_indices(worked_regfile.commit()) == [4, 0]

    def test_power_writes_only_r4(self, worked_regfile):
        worked_regfile.commit()
        worked_regfile.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert _plan_indices(worked_regfile.commit()) == [4]


class TestSelectiveReencode:
    def test_frac_only_changes_r0_word(self, worked_regfile):
        worked_regfile.commit()
        before = worked_regfile.current_words()
        worked_regfile.configure(frac=14)
        after = worked_regfile.current_words()
        assert after[0] != before[0]
        assert after[1:] == before[1:]

    def test_phase_only_changes_r1_word(self, worked_regfile):
        # phase is an R1 field that shares no encoding with the PLL-paired R0,
        # so changing it must leave every other word byte-identical.
        worked_regfile.commit()
        before = worked_regfile.current_words()
        worked_regfile.configure(phase=2)
        after = worked_regfile.current_words()
        assert after[1] != before[1]
        assert after[0] == before[0]
        assert after[2:] == before[2:]

    def test_muxout_only_changes_r2_word(self, worked_regfile):
        worked_regfile.commit()
        before = worked_regfile.current_words()
        worked_regfile.configure(muxout=consts.REG2_MUX_DVDD)
        after = worked_regfile.current_words()
        assert after[2] != before[2]
        assert after[0:2] == before[0:2]
        assert after[3:] == before[3:]

    def test_clockdiv_only_changes_r3_word(self, worked_regfile):
        worked_regfile.commit()
        before = worked_regfile.current_words()
        worked_regfile.configure(clockdiv_value=100)
        after = worked_regfile.current_words()
        assert after[3] != before[3]
        assert after[0:3] == before[0:3]
        assert after[4:] == before[4:]

    def test_output_power_only_changes_r4_word(self, worked_regfile):
        worked_regfile.commit()
        before = worked_regfile.current_words()
        worked_regfile.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        after = worked_regfile.current_words()
        assert after[4] != before[4]
        assert after[0:4] == before[0:4]
        assert after[5] == before[5]

    def test_lock_pin_only_changes_r5_word(self, worked_regfile):
        worked_regfile.commit()
        before = worked_regfile.current_words()
        worked_regfile.configure(lock_pin=consts.REG5_LOCK_LOW)
        after = worked_regfile.current_words()
        assert after[5] != before[5]
        assert after[0:5] == before[0:5]


class TestSelectivePllCheck:
    """The cross-register PLL check must still fire on the selective path
    whenever R0 or R1 is touched, and must run only once for the R0/R1 pair.
    """

    def test_configure_frac_ge_mod_rejected(self, worked_regfile):
        # frac (R0) vs mod (R1): the relation is validated even though only R0
        # is in the dirty set.
        worked_regfile.commit()
        with pytest.raises(ValueError, match="must be less than MOD"):
            worked_regfile.configure(frac=worked_regfile.config.mod)

    def test_configure_mod_below_frac_rejected(self, worked_regfile):
        # mod (R1) vs frac (R0): validated when only R1 is dirty.
        worked_regfile.commit()
        with pytest.raises(ValueError, match="must be less than MOD"):
            worked_regfile.configure(mod=worked_regfile.config.frac)

    def test_configure_non_pll_field_skips_check(self, worked_regfile, monkeypatch):
        # Touching only R2..R5 must not invoke the PLL check at all.
        calls = []
        original = worked_regfile._mapper._check_pll
        monkeypatch.setattr(
            worked_regfile._mapper,
            "_check_pll",
            lambda *a, **k: calls.append(a) or original(*a, **k),
        )
        worked_regfile.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert calls == []

    def test_configure_r0_and_r1_checks_pll_once(self, worked_regfile, monkeypatch):
        # Changing R0 and R1 together must validate the pair a single time, not
        # once per register.
        calls = []
        original = worked_regfile._mapper._check_pll
        monkeypatch.setattr(
            worked_regfile._mapper,
            "_check_pll",
            lambda *a, **k: calls.append(a) or original(*a, **k),
        )
        worked_regfile.configure(int_n=211, mod=50)
        assert len(calls) == 1


class TestDump:
    def test_clean_after_commit(self, worked_regfile):
        worked_regfile.commit()
        snap = worked_regfile.dump()
        assert snap["is_stale"] is False
        assert snap["commit_count"] == 1
        assert len(snap["registers"]) == 6

    def test_reports_stale_register_after_change(self, worked_regfile):
        worked_regfile.commit()
        worked_regfile.configure(frac=14)
        snap = worked_regfile.dump()
        assert snap["is_stale"] is True
        assert snap["registers"][0]["stale"] is True
