"""Host tests for the register-file staleness and ordering engine (increment 1).

These drive the engine with plain integer words via the ``_update_current``
seam, so no profile, mapper, or device is needed.
"""
import pytest

from adf435x.register_file import ADF435xRegisterFile

# Six distinct sentinel words (low 3 bits = register address, for readability).
WORDS = [0xA0, 0xB1, 0xC2, 0xD3, 0xE4, 0xF5]


@pytest.fixture
def rf():
    f = ADF435xRegisterFile()
    f._update_current(WORDS)
    return f


class TestInitialState:
    def test_fresh_file_is_stale(self, rf):
        assert rf.is_stale()

    def test_all_registers_stale_initially(self, rf):
        assert rf.stale_indices() == [0, 1, 2, 3, 4, 5]


class TestFirstCommit:
    def test_emits_all_six_r5_to_r0(self, rf):
        plan = rf.commit()
        assert plan == [(5, 0xF5), (4, 0xE4), (3, 0xD3),
                        (2, 0xC2), (1, 0xB1), (0, 0xA0)]

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
        assert rf.commit() == [(0, 0xAA)]

    def test_r4_only_change_does_not_force_r0(self, rf):
        # R4 is not double-buffered (R2 DB13 disabled), so it writes alone.
        rf.commit()
        rf._update_current([0xA0, 0xB1, 0xC2, 0xD3, 0xEE, 0xF5])
        assert rf.commit() == [(4, 0xEE)]

    def test_r1_change_forces_r0_last(self, rf):
        # R1 is double-buffered: changing it forces an R0 write to latch.
        rf.commit()
        rf._update_current([0xA0, 0xBB, 0xC2, 0xD3, 0xE4, 0xF5])
        assert rf.commit() == [(1, 0xBB), (0, 0xA0)]

    def test_r2_change_forces_r0_last(self, rf):
        rf.commit()
        rf._update_current([0xA0, 0xB1, 0xCC, 0xD3, 0xE4, 0xF5])
        assert rf.commit() == [(2, 0xCC), (0, 0xA0)]

    def test_r1_and_r4_change_gives_fast_retune_order(self, rf):
        # [R4], [R1], R0 -- the cheat-sheet fast-retune, falling out of the diff.
        rf.commit()
        rf._update_current([0xA0, 0xBB, 0xC2, 0xD3, 0xEE, 0xF5])
        assert rf.commit() == [(4, 0xEE), (1, 0xBB), (0, 0xA0)]


class TestOrdering:
    def test_pairs_are_descending_by_index(self, rf):
        indices = [index for index, _ in rf.commit()]
        assert indices == sorted(indices, reverse=True)

    def test_r0_is_written_last_when_present(self, rf):
        rf.commit()
        rf._update_current([0xAA, 0xBB, 0xC2, 0xD3, 0xE4, 0xF5])
        plan = rf.commit()
        assert plan[-1][0] == 0


class TestCommitAll:
    def test_emits_all_six_regardless_of_staleness(self, rf):
        rf.commit()                      # now nothing is stale
        plan = rf.commit_all()
        assert [index for index, _ in plan] == [5, 4, 3, 2, 1, 0]

    def test_marks_everything_written(self, rf):
        rf.commit_all()
        assert not rf.is_stale()


class TestValidation:
    def test_update_current_rejects_wrong_length(self, rf):
        with pytest.raises(ValueError):
            rf._update_current([0, 1, 2])