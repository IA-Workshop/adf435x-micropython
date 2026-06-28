"""Host tests for the register-file staleness and ordering engine.

These drive the engine with plain integer words via the ``_update_current``
seam, so no profile, mapper, or device is needed for most cases.
"""
import pytest

from adf435x import consts
from adf435x.register_file import ADF435xRegisterFile
from adf435x.profiles import ADF4350, ADF4351

# Six distinct sentinel words (low 3 bits = register address, for readability).
WORDS = [0xA0, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5]

# R2 DB13: marks the R4 divider as double-buffered (DBB).
DBB_BIT = 1 << consts.REG2_DOUBLE_BUFFER_POS


def _reg_addr(word: int) -> int:
    """Register index encoded in DB2:DB0 of a word."""
    return word & 0b111


def _plan_indices(plan: list) -> list:
    return [_reg_addr(word) for word in plan]


@pytest.fixture(params=[ADF4350, ADF4351], ids=lambda profile: profile.name)
def rf(request):
    f = ADF435xRegisterFile(profile=request.param)
    f._update_current(WORDS)
    return f


@pytest.fixture(params=[ADF4350, ADF4351], ids=lambda profile: profile.name)
def rf_dbb(request):
    """Register file whose R2 word has DB13 (double_buffer) set.

    The double-buffer state is carried in the encoded R2 word, so the sentinel
    words set DB13 directly rather than relying on a separate config flag.
    """
    f = ADF435xRegisterFile(profile=request.param)
    words = list(WORDS)
    words[consts.REG2_ADDR] |= DBB_BIT
    f._update_current(words)
    return f


class TestInitialState:
    def test_fresh_file_is_stale(self, rf):
        assert rf.is_stale()

    def test_all_registers_stale_initially(self, rf):
        assert rf.stale_indices() == [0, 1, 2, 3, 4, 5]


class TestFirstCommit:
    def test_emits_all_six_r5_to_r0(self, rf):
        plan = rf.commit()
        assert plan == [0xF5, 0xE4, 0xD3, 0xC2, 0xB1, 0xA0]

    def test_clears_staleness(self, rf):
        rf.commit()
        assert not rf.is_stale()

    def test_second_commit_is_empty(self, rf):
        rf.commit()
        assert rf.commit() == []


class TestIncrementalCommit:
    def test_r0_only_change_writes_only_r0(self, rf):
        rf.commit()
        rf._update_current([0xAA, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5])
        assert rf.commit() == [0xAA]

    def test_r4_only_change_does_not_force_r0(self, rf):
        # R4 is not double-buffered (R2 DB13 disabled), so it writes alone.
        rf.commit()
        rf._update_current([0xA0, 0xB1, 0xC2, 0xD3, 0xEE, 0xF5])
        assert rf.commit() == [0xEE]

    def test_r1_change_forces_r0_last(self, rf):
        # R1 is double-buffered: changing it forces an R0 write to latch.
        rf.commit()
        rf._update_current([0xA0, 0xBB, 0xC2, 0xD3, 0xE4, 0xF5])
        assert rf.commit() == [0xBB, 0xA0]

    def test_r2_change_forces_r0_last(self, rf):
        rf.commit()
        rf._update_current([0xA0, 0xB1, 0xCC, 0xD3, 0xE4, 0xF5])
        assert rf.commit() == [0xCC, 0xA0]

    def test_r1_and_r4_change_gives_fast_retune_order(self, rf):
        # [R4], [R1], R0 -- the cheat-sheet fast-retune, falling out of the diff.
        rf.commit()
        rf._update_current([0xA0, 0xBB, 0xC2, 0xD3, 0xEE, 0xF5])
        assert rf.commit() == [0xEE, 0xBB, 0xA0]


class TestDoubleBuffer:
    def test_r4_only_forces_r0_when_dbb_enabled(self, rf_dbb):
        rf_dbb.commit()
        # Keep DB13 set in R2 so only R4 is stale; DBB then forces R0.
        words = list(WORDS)
        words[consts.REG2_ADDR] |= DBB_BIT
        words[consts.REG4_ADDR] = 0xEE
        rf_dbb._update_current(words)
        assert rf_dbb.commit() == [0xEE, 0xA0]

    def test_r2_still_forces_r0_when_dbb_enabled(self, rf_dbb):
        rf_dbb.commit()
        rf_dbb._update_current([0xA0, 0xB1, 0xCC, 0xD3, 0xE4, 0xF5])
        assert rf_dbb.commit() == [0xCC, 0xA0]

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_enabling_double_buffer_writes_r2_and_r0(self, profile):
        f = ADF435xRegisterFile(profile)
        f.commit()
        f.configure(double_buffer=True)
        assert _plan_indices(f.commit()) == [consts.REG2_ADDR, consts.REG0_ADDR]

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_disabling_double_buffer_writes_r2_and_r0(self, profile):
        # Disabling is an R2 change too, so it latches via R0 like enabling.
        f = ADF435xRegisterFile(profile)
        f.configure(double_buffer=True)
        f.commit()
        f.configure(double_buffer=False)
        assert _plan_indices(f.commit()) == [consts.REG2_ADDR, consts.REG0_ADDR]

    def test_non_divider_r4_field_forces_r0_when_dbb_enabled(self):
        # output_power is not double-buffered, but with DB13 set we
        # conservatively latch any R4 change with an R0 write. The redundant
        # R0 re-latches the unchanged divider, which is harmless.
        f = ADF435xRegisterFile(ADF4351)
        f.configure(double_buffer=True)
        f.commit()
        f.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert _plan_indices(f.commit()) == [
            consts.REG4_ADDR, consts.REG0_ADDR]

    def test_non_divider_r4_field_alone_when_dbb_disabled(self):
        # Without DB13, the same non-divider R4 change writes R4 on its own.
        f = ADF435xRegisterFile(ADF4351)
        f.commit()
        f.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert _plan_indices(f.commit()) == [consts.REG4_ADDR]

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_r4_only_via_configure_forces_r0_when_dbb_enabled(self, profile):
        f = ADF435xRegisterFile(profile)
        f.commit()
        f.configure(double_buffer=True)
        f.commit()
        f.configure(rf_divider=2)
        assert _plan_indices(f.commit()) == [
            consts.REG4_ADDR, consts.REG0_ADDR]

    def test_r4_and_mod_gives_fast_retune_order_with_dbb(self):
        f = ADF435xRegisterFile(ADF4351)
        f.commit()
        f.configure(double_buffer=True)
        f.commit()
        f.configure(rf_divider=2, mod=50)
        assert _plan_indices(f.commit()) == [
            consts.REG4_ADDR, consts.REG1_ADDR, consts.REG0_ADDR]


class TestCommitPlan:
    def test_plan_leaves_stale_until_mark_written(self, rf):
        rf.commit()
        rf._update_current([0xAA, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5])
        plan = rf.commit_plan()
        assert plan == [0xAA]
        assert rf.is_stale()
        rf.mark_written()
        assert not rf.is_stale()

    def test_mark_write_failed_restores_staleness(self, rf):
        rf.commit()
        assert not rf.is_stale()
        rf.mark_write_failed()
        assert rf.is_stale()
        assert rf.stale_indices() == [0, 1, 2, 3, 4, 5]

    def test_commit_all_plan_without_mark_written(self, rf):
        rf.commit()
        count_before = rf.dump()["commit_count"]
        rf._update_current([0xA8, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5])
        plan = rf.commit_all_plan()
        assert plan == [0xF5, 0xE4, 0xD3, 0xC2, 0xB1, 0xA8]
        assert rf.is_stale()
        assert rf.dump()["commit_count"] == count_before


class TestOrdering:
    def test_pairs_are_descending_by_index(self, rf):
        indices = _plan_indices(rf.commit())
        assert indices == sorted(indices, reverse=True)

    def test_r0_is_written_last_when_present(self, rf):
        rf.commit()
        # Low 3 bits of each word must match register address (see WORDS).
        rf._update_current([0xA8, 0xB9, 0xC2, 0xD3, 0xE4, 0xF5])
        plan = rf.commit()
        assert _plan_indices(plan)[-1] == 0


class TestCommitAll:
    def test_emits_all_six_regardless_of_staleness(self, rf):
        rf.commit()                      # now nothing is stale
        plan = rf.commit_all()
        assert _plan_indices(plan) == [5, 4, 3, 2, 1, 0]

    def test_marks_everything_written(self, rf):
        rf.commit_all()
        assert not rf.is_stale()


class TestValidation:
    def test_update_current_rejects_wrong_length(self, rf):
        with pytest.raises(ValueError):
            rf._update_current([0, 1, 2])
