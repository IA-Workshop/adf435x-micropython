"""Host tests for the register-file staleness and ordering engine.

These drive the engine with plain integer words via ``load_words``,
so no mapper encoding or device is needed for most cases.
"""

import pytest

from adf435x import consts
from adf435x.register_file import ADF435xRegisterFile
from adf435x.profiles import ADF4350, ADF4351
from conftest import commit, commit_all

# Six distinct sentinel words (low 3 bits = register address, for readability).
WORDS = [0xA0, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5]

# R2 DB13: marks the R4 divider as double-buffered (DBB).
DBB_BIT = 1 << consts.REG2_DOUBLE_BUFFER_POS


def _reg_addr(word: int) -> int:
    """Register index encoded in DB2:DB0 of a word."""
    return word & 0b111


def _plan_indices(plan: list) -> list:
    """Return the register index of each word in a commit plan."""
    return [_reg_addr(word) for word in plan]


@pytest.fixture(params=[ADF4350, ADF4351], ids=lambda profile: profile.name)
def rf(request):
    """Register file preloaded with the sentinel words on each profile."""
    f = ADF435xRegisterFile(profile=request.param)
    f.load_words({}, WORDS)
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
    f.load_words({}, words)
    return f


class TestInitialState:
    """A freshly loaded file is stale across all registers."""

    def test_fresh_file_is_stale(self, rf):
        """Never-written registers report stale."""
        assert rf.is_stale()

    def test_all_registers_stale_initially(self, rf):
        """All six registers are stale before the first commit."""
        assert rf.stale_indices() == [0, 1, 2, 3, 4, 5]


class TestFirstCommit:
    """The first commit writes everything in R5->R0 order."""

    def test_emits_all_six_r5_to_r0(self, rf):
        """The plan lists all six words from R5 down to R0."""
        plan = commit(rf)
        assert plan == [0xF5, 0xE4, 0xD3, 0xC2, 0xB1, 0xA0]

    def test_clears_staleness(self, rf):
        """Committing marks every register as written."""
        commit(rf)
        assert not rf.is_stale()

    def test_second_commit_is_empty(self, rf):
        """With nothing changed, a second commit plans no writes."""
        commit(rf)
        assert commit(rf) == []


class TestIncrementalCommit:
    """Only changed registers (plus latch writes) appear in a commit."""

    def test_r0_only_change_writes_only_r0(self, rf):
        """An R0-only change writes R0 alone (no latch needed)."""
        commit(rf)
        rf.load_words({}, [0xAA, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5])
        assert commit(rf) == [0xAA]

    def test_r4_only_change_does_not_force_r0(self, rf):
        """An R4-only change writes R4 alone when DBB is off."""
        # R4 is not double-buffered (R2 DB13 disabled), so it writes alone.
        commit(rf)
        rf.load_words({}, [0xA0, 0xB1, 0xC2, 0xD3, 0xEE, 0xF5])
        assert commit(rf) == [0xEE]

    def test_r1_change_forces_r0_last(self, rf):
        """A double-buffered R1 change appends an R0 latch write."""
        # R1 is double-buffered: changing it forces an R0 write to latch.
        commit(rf)
        rf.load_words({}, [0xA0, 0xBB, 0xC2, 0xD3, 0xE4, 0xF5])
        assert commit(rf) == [0xBB, 0xA0]

    def test_r2_change_forces_r0_last(self, rf):
        """A double-buffered R2 change appends an R0 latch write."""
        commit(rf)
        rf.load_words({}, [0xA0, 0xB1, 0xCC, 0xD3, 0xE4, 0xF5])
        assert commit(rf) == [0xCC, 0xA0]

    def test_r1_and_r4_change_gives_fast_retune_order(self, rf):
        """A combined R1+R4 change emits R4, R1, then the R0 latch."""
        # The fast-retune order the ADF435x cheat sheet gives: [R4], [R1], R0.
        commit(rf)
        rf.load_words({}, [0xA0, 0xBB, 0xC2, 0xD3, 0xEE, 0xF5])
        assert commit(rf) == [0xEE, 0xBB, 0xA0]


class TestDoubleBuffer:
    """R4 divider latching depends on R2 DB13 (the double-buffer bit)."""

    def test_r4_only_forces_r0_when_dbb_enabled(self, rf_dbb):
        """With DBB set, an R4-only change appends an R0 latch write."""
        commit(rf_dbb)
        # Keep DB13 set in R2 so only R4 is stale; DBB then forces R0.
        words = list(WORDS)
        words[consts.REG2_ADDR] |= DBB_BIT
        words[consts.REG4_ADDR] = 0xEE
        rf_dbb.load_words({}, words)
        assert commit(rf_dbb) == [0xEE, 0xA0]

    def test_r2_still_forces_r0_when_dbb_enabled(self, rf_dbb):
        """R2 still latches via R0 regardless of the DBB bit."""
        commit(rf_dbb)
        rf_dbb.load_words({}, [0xA0, 0xB1, 0xCC, 0xD3, 0xE4, 0xF5])
        assert commit(rf_dbb) == [0xCC, 0xA0]

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_enabling_double_buffer_writes_r2_and_r0(self, profile):
        """Enabling double_buffer is an R2 change that latches via R0."""
        f = ADF435xRegisterFile(profile)
        commit(f)
        f.configure(double_buffer=True)
        assert _plan_indices(commit(f)) == [consts.REG2_ADDR, consts.REG0_ADDR]

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_disabling_double_buffer_writes_r2_and_r0(self, profile):
        """Disabling double_buffer also writes R2 then R0."""
        # Disabling is an R2 change too, so it latches via R0 like enabling.
        f = ADF435xRegisterFile(profile)
        f.configure(double_buffer=True)
        commit(f)
        f.configure(double_buffer=False)
        assert _plan_indices(commit(f)) == [consts.REG2_ADDR, consts.REG0_ADDR]

    def test_non_divider_r4_field_forces_r0_when_dbb_enabled(self):
        """With DBB set, any R4 change appends an R0 write."""
        # Output power is not double-buffered, so this R0 write is not
        # strictly needed. It only re-latches the unchanged divider.
        f = ADF435xRegisterFile(ADF4351)
        f.configure(double_buffer=True)
        commit(f)
        f.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert _plan_indices(commit(f)) == [consts.REG4_ADDR, consts.REG0_ADDR]

    def test_non_divider_r4_field_alone_when_dbb_disabled(self):
        """Without DBB, a non-divider R4 change writes R4 alone."""
        f = ADF435xRegisterFile(ADF4351)
        commit(f)
        f.configure(output_power=consts.REG4_POWER_MINUS_4DBM)
        assert _plan_indices(commit(f)) == [consts.REG4_ADDR]

    @pytest.mark.parametrize("profile", [ADF4350, ADF4351], ids=lambda p: p.name)
    def test_r4_only_via_configure_forces_r0_when_dbb_enabled(self, profile):
        """An rf_divider change with DBB set emits R4 then the R0 latch."""
        f = ADF435xRegisterFile(profile)
        commit(f)
        f.configure(double_buffer=True)
        commit(f)
        f.configure(rf_divider=2)
        assert _plan_indices(commit(f)) == [consts.REG4_ADDR, consts.REG0_ADDR]

    def test_r4_and_mod_gives_fast_retune_order_with_dbb(self):
        """A combined R4+MOD change with DBB emits R4, R1, then R0."""
        f = ADF435xRegisterFile(ADF4351)
        commit(f)
        f.configure(double_buffer=True)
        commit(f)
        f.configure(rf_divider=2, mod=50)
        assert _plan_indices(commit(f)) == [
            consts.REG4_ADDR,
            consts.REG1_ADDR,
            consts.REG0_ADDR,
        ]


class TestCommitPlan:
    """``commit_plan`` previews writes without advancing the written cache."""

    def test_plan_leaves_stale_until_mark_written(self, rf):
        """Planning alone keeps the file stale until mark_written is called."""
        commit(rf)
        rf.load_words({}, [0xAA, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5])
        plan = rf.commit_plan()
        assert plan == [0xAA]
        # Cache is untouched by planning, so the file is still stale.
        assert rf.is_stale()
        rf.mark_written()
        assert not rf.is_stale()

    def test_mark_write_failed_restores_staleness(self, rf):
        """mark_write_failed discards the cache so all registers go stale."""
        commit(rf)
        assert not rf.is_stale()
        rf.mark_write_failed()
        assert rf.is_stale()
        assert rf.stale_indices() == [0, 1, 2, 3, 4, 5]

    def test_plan_is_idempotent_without_mark_written(self, rf):
        """Repeated planning returns the same plan and leaves state stale."""
        # Without mark_written the cache is untouched, so repeated planning
        # must return the identical plan and leave staleness unchanged.
        commit(rf)
        rf.load_words({}, [0xAA, 0xBB, 0xC2, 0xD3, 0xE4, 0xF5])
        first = rf.commit_plan()
        second = rf.commit_plan()
        assert first == second == [0xBB, 0xAA]
        assert rf.is_stale()

    def test_full_plan_without_mark_written(self, rf):
        """full_plan previews all six words without writing cache."""
        commit(rf)
        count_before = rf.dump()["commit_count"]
        rf.load_words({}, [0xA8, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5])
        plan = rf.full_plan()
        assert plan == [0xF5, 0xE4, 0xD3, 0xC2, 0xB1, 0xA8]
        # Planning does not write, so staleness and commit count are unchanged.
        assert rf.is_stale()
        assert rf.dump()["commit_count"] == count_before


class TestOrdering:
    """Commit plans are ordered high-to-low with R0 last."""

    def test_pairs_are_descending_by_index(self, rf):
        """Plan indices come out in descending register order."""
        indices = _plan_indices(commit(rf))
        assert indices == sorted(indices, reverse=True)

    def test_r0_is_written_last_when_present(self, rf):
        """When R0 is in the plan it is the final write (latch ordering)."""
        commit(rf)
        # Low 3 bits of each word must match register address (see WORDS).
        rf.load_words({}, [0xA8, 0xB9, 0xC2, 0xD3, 0xE4, 0xF5])
        plan = commit(rf)
        assert _plan_indices(plan)[-1] == 0


class TestCommitAll:
    """``commit_all`` writes every register regardless of staleness."""

    def test_emits_all_six_regardless_of_staleness(self, rf):
        """commit_all emits all six words even when nothing is stale."""
        commit(rf)  # now nothing is stale
        plan = commit_all(rf)
        assert _plan_indices(plan) == [5, 4, 3, 2, 1, 0]

    def test_marks_everything_written(self, rf):
        """commit_all advances the written cache for every register."""
        commit_all(rf)
        assert not rf.is_stale()


class TestLoadPrevalidated:
    """``load_words`` stores fields and words without re-encoding."""

    def test_rejects_wrong_length(self, rf):
        """A word list of the wrong length is rejected."""
        with pytest.raises(ValueError):
            rf.load_words({}, [0, 1, 2])

    def test_rejects_unknown_field(self, rf):
        """An unknown field name is rejected before anything changes."""
        with pytest.raises(AttributeError):
            rf.load_words({"bogus": 1}, WORDS)

    def test_stores_fields(self, rf):
        """Fields land on the config as given (no validation)."""
        rf.load_words({"int_n": 422, "frac": 13}, WORDS)
        assert (rf.config.int_n, rf.config.frac) == (422, 13)

    def test_does_not_advance_config_version(self, rf):
        """Loading precomputed state is not a settings change."""
        before = rf.config_version
        rf.load_words({"int_n": 422}, WORDS)
        assert rf.config_version == before


class TestConfigVersion:
    """``config_version`` counts successful ``configure()`` calls."""

    def test_starts_at_zero(self):
        """A new register file has version 0."""
        assert ADF435xRegisterFile(ADF4351).config_version == 0

    def test_advances_on_configure(self):
        """Each successful configure() advances the version by one."""
        f = ADF435xRegisterFile(ADF4351)
        f.configure(output_power=0)
        f.configure(rf_enable=False)
        assert f.config_version == 2

    def test_failed_configure_does_not_advance(self):
        """A rejected configure() leaves the version unchanged."""
        f = ADF435xRegisterFile(ADF4351)
        with pytest.raises(ValueError):
            f.configure(r_counter=0)
        assert f.config_version == 0
