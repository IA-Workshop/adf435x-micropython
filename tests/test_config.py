"""Config integration for the register file: ADF435xConfig encodes through the
mapper, configure() is transactional, and dump() reports state.
"""

import pytest

from adf435x import consts
from adf435x import register_mapper
from adf435x.config import (
    ALLOWED,
    DEFAULT,
    ENUM,
    FIELD_NAMES,
    FIELD_REGISTER,
    FIELD_SPECS,
    FIELDS,
    KIND,
    NAME,
    POS,
    REG,
    UINT,
    WIDTH,
    ADF435xConfig,
)
from adf435x.profiles import ADF4350, ADF4351
from adf435x.register_file import ADF435xRegisterFile

from conftest import WORKED_WORDS, commit


def _plan_indices(plan: list) -> list:
    """Return the register address (DB2:DB0) of each word in a commit plan."""
    return [word & 0b111 for word in plan]


def _bits(spec):
    """Mask of the register bits a field spec occupies."""
    return ((1 << spec[WIDTH]) - 1) << spec[POS]


class TestFieldSchema:
    """The ``FIELDS`` table is self-consistent and matches the register map."""

    def test_derived_views_match_fields(self):
        """Name, spec, and register views cover exactly the table's fields."""
        names = tuple(spec[NAME] for spec in FIELDS)
        assert FIELD_NAMES == names
        assert len(set(names)) == len(names)
        assert set(FIELD_SPECS) == set(FIELD_REGISTER) == set(names)

    @pytest.mark.parametrize("spec", FIELDS, ids=lambda s: s[NAME])
    def test_register_index_in_range(self, spec):
        """Each field maps to a valid register index (0..5)."""
        assert 0 <= spec[REG] < consts.NUM_REGISTERS

    @pytest.mark.parametrize("spec", FIELDS, ids=lambda s: s[NAME])
    def test_field_inside_data_bits(self, spec):
        """No field reaches the address bits DB2:DB0 or above DB31."""
        assert _bits(spec) & ~0xFFFFFFF8 == 0

    @pytest.mark.parametrize("reg", range(6))
    def test_fields_do_not_overlap(self, reg):
        """Fields in one register occupy disjoint bits (and miss R5's ones)."""
        used = consts.REG5_RESERVED_ONES if reg == consts.REG5_ADDR else 0
        overlap = 0
        for spec in FIELDS:
            if spec[REG] == reg:
                overlap |= used & _bits(spec)
                used |= _bits(spec)
        assert overlap == 0

    @pytest.mark.parametrize(
        "spec", [s for s in FIELDS if s[KIND] == ENUM], ids=lambda s: s[NAME]
    )
    def test_enum_codes_fit_width(self, spec):
        """Every legal enum code fits its bit field."""
        assert all(0 <= v < 1 << spec[WIDTH] for v in spec[ALLOWED])

    @pytest.mark.parametrize(
        "spec", [s for s in FIELDS if s[KIND] == UINT], ids=lambda s: s[NAME]
    )
    def test_uint_minimum_fits_width(self, spec):
        """Every unsigned field's minimum is encodable."""
        assert 0 <= spec[ALLOWED] < 1 << spec[WIDTH]


class TestEncoding:
    """A configuration encodes to the expected register words."""

    def test_worked_regfile_example_words(self, worked_regfile):
        """The data sheet worked example encodes to the known-good words."""
        assert worked_regfile.current_words() == WORKED_WORDS

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_default_config_encodes(self, profile):
        """A default config yields six words on both supported profiles."""
        f = ADF435xRegisterFile(profile)
        assert len(f.current_words()) == 6


class TestInstanceIsolation:
    """Config instances hold per-object state, not shared class attributes."""

    def test_fresh_instances_are_independent(self):
        """Mutating one instance does not leak into another."""
        a = ADF435xConfig()
        b = ADF435xConfig()
        a.int_n = 100
        # b must still hold the default, proving fields are instance state.
        assert b.int_n == FIELD_SPECS["int_n"][DEFAULT]

    def test_defaults_match_field_table(self):
        """A fresh config reflects every default in ``FIELDS``."""
        cfg = ADF435xConfig()
        assert all(getattr(cfg, s[NAME]) == s[DEFAULT] for s in FIELDS)

    def test_init_applies_overrides_only(self):
        """Overrides set only the named fields; the rest keep defaults."""
        cfg = ADF435xConfig(int_n=422, frac=13)
        assert cfg.int_n == 422
        assert cfg.frac == 13
        # mod was not overridden, so it stays at its default.
        assert cfg.mod == FIELD_SPECS["mod"][DEFAULT]

    def test_copy_preserves_all_fields(self):
        """``copy()`` reproduces every field value of the original."""
        original = ADF435xConfig(int_n=422, frac=13, mod=25)
        clone = original.copy()
        for name in FIELD_NAMES:
            assert getattr(clone, name) == getattr(original, name)

    def test_copy_is_independent(self):
        """Mutating a copy does not affect the original."""
        original = ADF435xConfig(int_n=422)
        clone = original.copy()
        clone.int_n = 500
        assert original.int_n == 422


class TestConfigure:
    """``configure()`` validates input and is transactional on failure."""

    def test_rejects_unknown_field(self, worked_regfile):
        """An unknown field name raises before any state changes."""
        with pytest.raises(AttributeError):
            worked_regfile.configure(no_such_field=1)

    def test_init_rejects_unknown_field(self):
        """The config constructor also rejects unknown field names."""
        with pytest.raises(AttributeError):
            ADF435xConfig(no_such_field=1)

    def test_copy_is_independent(self, worked_regfile):
        """A copy of the file's config can be edited without side effects."""
        clone = worked_regfile.config.copy()
        clone.frac = 14
        assert worked_regfile.config.frac == 13
        assert clone.frac == 14

    def test_two_register_files_do_not_share_config(self):
        """Each register file owns a separate default config instance."""
        a = ADF435xRegisterFile(ADF4351)
        b = ADF435xRegisterFile(ADF4351)
        a.configure(muxout=consts.REG2_MUX_DGND)
        # Changing a's config must not touch b's independent default.
        assert a.config.muxout == consts.REG2_MUX_DGND
        assert b.config.muxout == consts.REG2_MUX_DIGITALLOCK

    def test_rolls_back_field_on_failure(self):
        """A rejected value leaves the config field at its prior value."""
        f = ADF435xRegisterFile(ADF4350)
        with pytest.raises(ValueError):
            f.configure(rf_divider=32)  # exceeds the 4350's /16 maximum
        assert f.config.rf_divider == 1

    def test_rolls_back_words_on_failure(self):
        """A rejected value leaves the encoded words unchanged."""
        f = ADF435xRegisterFile(ADF4350)
        before = f.current_words()
        with pytest.raises(ValueError):
            f.configure(rf_divider=32)
        assert f.current_words() == before

    def test_wrong_type_rejected_by_validation(self):
        """A wrong-typed value is a ValueError at validation, not at encode."""
        f = ADF435xRegisterFile(ADF4350)
        with pytest.raises(ValueError, match="must be an integer"):
            f.configure(int_n="not-an-int")

    def test_rolls_back_on_non_value_error(self, monkeypatch):
        """Rollback covers any exception, not just ValueError."""
        # Fail inside encoding once; the file must be restored and the
        # original error re-raised.
        f = ADF435xRegisterFile(ADF4350)
        before_int_n = f.config.int_n
        before_words = f.current_words()
        real_encode = f._mapper.encode_register
        failed = []

        def encode_once_failing(index, config):
            if not failed:
                failed.append(index)
                raise RuntimeError("encoder fault")
            return real_encode(index, config)

        monkeypatch.setattr(f._mapper, "encode_register", encode_once_failing)
        with pytest.raises(RuntimeError):
            f.configure(int_n=100)
        assert f.config.int_n == before_int_n
        assert f.current_words() == before_words


class TestRetune:
    """Retuning re-encodes only affected registers and forces R0 when needed."""

    def test_frac_writes_only_r0(self, worked_regfile):
        """Changing FRAC (an R0 field) writes R0 alone."""
        commit(worked_regfile)
        worked_regfile.configure(frac=14)
        assert _plan_indices(commit(worked_regfile)) == [0]

    def test_mod_forces_r0(self, worked_regfile):
        """Changing MOD (an R1 field) writes R1 then R0 to latch it (DBR)."""
        commit(worked_regfile)
        worked_regfile.configure(mod=50)
        assert _plan_indices(commit(worked_regfile)) == [1, 0]

    def test_divider_writes_r4_and_r0(self, worked_regfile):
        """An R4 divider change plus an R0 change emits R4 then R0."""
        commit(worked_regfile)
        worked_regfile.configure(rf_divider=4, int_n=211)
        assert _plan_indices(commit(worked_regfile)) == [4, 0]

    def test_power_writes_only_r4(self, worked_regfile):
        """Output power (non-buffered R4 field) writes R4 alone."""
        commit(worked_regfile)
        worked_regfile.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert _plan_indices(commit(worked_regfile)) == [4]


class TestSelectiveReencode:
    """Changing one field re-encodes only its register, others intact."""

    def test_frac_only_changes_r0_word(self, worked_regfile):
        """FRAC touches only the R0 word."""
        commit(worked_regfile)
        before = worked_regfile.current_words()
        worked_regfile.configure(frac=14)
        after = worked_regfile.current_words()
        assert after[0] != before[0]
        # Every register past R0 must be byte-identical.
        assert after[1:] == before[1:]

    def test_phase_only_changes_r1_word(self, worked_regfile):
        """Phase touches only the R1 word, not the PLL-paired R0."""
        # phase is an R1 field that shares no encoding with the PLL-paired R0,
        # so changing it must leave every other word byte-identical.
        commit(worked_regfile)
        before = worked_regfile.current_words()
        worked_regfile.configure(phase=2)
        after = worked_regfile.current_words()
        assert after[1] != before[1]
        assert after[0] == before[0]
        assert after[2:] == before[2:]

    def test_muxout_only_changes_r2_word(self, worked_regfile):
        """MUXOUT touches only the R2 word."""
        commit(worked_regfile)
        before = worked_regfile.current_words()
        worked_regfile.configure(muxout=consts.REG2_MUX_DVDD)
        after = worked_regfile.current_words()
        assert after[2] != before[2]
        assert after[0:2] == before[0:2]
        assert after[3:] == before[3:]

    def test_clockdiv_only_changes_r3_word(self, worked_regfile):
        """Clock-divider value touches only the R3 word."""
        commit(worked_regfile)
        before = worked_regfile.current_words()
        worked_regfile.configure(clockdiv_value=100)
        after = worked_regfile.current_words()
        assert after[3] != before[3]
        assert after[0:3] == before[0:3]
        assert after[4:] == before[4:]

    def test_output_power_only_changes_r4_word(self, worked_regfile):
        """Output power touches only the R4 word."""
        commit(worked_regfile)
        before = worked_regfile.current_words()
        worked_regfile.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        after = worked_regfile.current_words()
        assert after[4] != before[4]
        assert after[0:4] == before[0:4]
        assert after[5] == before[5]

    def test_lock_pin_only_changes_r5_word(self, worked_regfile):
        """Lock-pin mode touches only the R5 word."""
        commit(worked_regfile)
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
        """FRAC >= MOD is caught even when only R0 is in the dirty set."""
        # frac (R0) vs mod (R1): the relation is validated even though only R0
        # is in the dirty set.
        commit(worked_regfile)
        with pytest.raises(ValueError, match="must be less than MOD"):
            worked_regfile.configure(frac=worked_regfile.config.mod)

    def test_configure_mod_below_frac_rejected(self, worked_regfile):
        """FRAC >= MOD is caught even when only R1 is in the dirty set."""
        # mod (R1) vs frac (R0): validated when only R1 is dirty.
        commit(worked_regfile)
        with pytest.raises(ValueError, match="must be less than MOD"):
            worked_regfile.configure(mod=worked_regfile.config.frac)

    @staticmethod
    def _count_pll_rule(monkeypatch):
        """Wrap the PLL cross-field rule to record each call."""
        calls = []
        original = register_mapper._rule_pll
        rules = tuple(
            (triggers, (lambda p, c: calls.append(1) or original(p, c)))
            if rule is original
            else (triggers, rule)
            for triggers, rule in register_mapper._RULES
        )
        monkeypatch.setattr(register_mapper, "_RULES", rules)
        return calls

    def test_configure_non_pll_field_skips_check(self, worked_regfile, monkeypatch):
        """Touching only non-PLL registers skips the PLL cross-check."""
        calls = self._count_pll_rule(monkeypatch)
        worked_regfile.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert calls == []

    def test_configure_r0_and_r1_checks_pll_once(self, worked_regfile, monkeypatch):
        """A combined R0+R1 change runs the PLL check exactly once."""
        calls = self._count_pll_rule(monkeypatch)
        worked_regfile.configure(int_n=211, mod=50)
        assert len(calls) == 1


class TestDump:
    """``dump()`` reflects commit count and per-register staleness."""

    def test_clean_after_commit(self, worked_regfile):
        """After a commit the snapshot reports no staleness and a commit."""
        commit(worked_regfile)
        snap = worked_regfile.dump()
        assert snap["is_stale"] is False
        assert snap["commit_count"] == 1
        assert len(snap["registers"]) == 6

    def test_reports_stale_register_after_change(self, worked_regfile):
        """A post-commit change marks the affected register stale."""
        commit(worked_regfile)
        worked_regfile.configure(frac=14)
        snap = worked_regfile.dump()
        assert snap["is_stale"] is True
        # frac lives in R0, so register 0 must show as stale.
        assert snap["registers"][0]["stale"] is True
