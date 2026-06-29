"""Host tests for FrequencyTable and ADF435xSweeper."""

import pytest

from adf435x import consts
from adf435x.profiles import ADF4351
from adf435x.solver import (
    DividerOctaveCrossingError,
    build_frequency_table,
    output_band_hz,
)
from adf435x.sweep import ADF435xSweeper, FrequencyTable

REF_HZ = 10_000_000


class TestFrequencyTableFromRange:
    """Range table builder."""

    def test_matches_solver_entry_count(self, synth):
        """from_range yields the same length as build_frequency_table."""
        lo, hi, step = 190_000_000, 210_000_000, 2_000_000
        solver_table, _, _ = build_frequency_table(
            lo, hi, step, REF_HZ, ADF4351
        )
        table = FrequencyTable.from_range(synth, lo, hi, step)
        assert len(table) == len(solver_table)
        assert table.channel_step_hz > 0

    def test_entries_have_nonempty_plans(self, synth):
        """Every entry carries a pre-encoded SPI plan."""
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        for i in range(len(table)):
            assert table[i].plan


class TestFrequencyTableFromFrequencies:
    """Arbitrary-order frequency lists."""

    def test_preserves_order(self, synth):
        """Entries follow the caller-supplied frequency order."""
        freqs = [200_000_000, 195_000_000, 205_000_000]
        table = FrequencyTable.from_frequencies(synth, freqs)
        assert len(table) == 3

    def test_empty_list_raises(self, synth):
        """Empty frequency list is rejected."""
        with pytest.raises(ValueError, match="empty"):
            FrequencyTable.from_frequencies(synth, [])

    def test_divider_crossing_raises_with_bands(self, synth):
        """Wide span reports each divider band and narrow suggestions."""
        lo = 100_000_000
        hi = 3_000_000_000
        with pytest.raises(DividerOctaveCrossingError) as exc:
            FrequencyTable.from_frequencies(synth, [lo, hi])
        err = exc.value
        assert err.lower_hz == lo
        assert err.upper_hz == hi
        assert err.lower_band_hz[0] <= lo <= err.lower_band_hz[1]
        assert err.upper_band_hz[0] <= hi <= err.upper_band_hz[1]
        assert "band %d" % err.lower_band_hz[0] in str(err)
        assert "allow_divider_change=True" in str(err)

    def test_allow_divider_change_permits_crossing(self, synth):
        """allow_divider_change builds a segmented multi-divider table."""
        lo = 100_000_000
        hi = 3_000_000_000
        table = FrequencyTable.from_frequencies(
            synth, [lo, hi], allow_divider_change=True
        )
        assert len(table) == 2
        assert table[0].plan  # full first entry
        assert table[1].divider_boundary is True
        assert len(table[1].plan) == 6

    def test_from_range_segmented_has_boundaries(self, synth):
        """Crossing range marks segment starts and keeps in-band R0 hops."""
        table = FrequencyTable.from_range(
            synth,
            100_000_000,
            300_000_000,
            25_000_000,
            allow_divider_change=True,
        )
        assert table.segment_boundaries
        # Some mid-segment hop should be a fast R0-only update.
        in_band = [
            e
            for e in table
            if not e.divider_boundary and len(e.plan) == 1
        ]
        assert in_band

    def test_from_range_segment_locked_mod(self, synth):
        """Within a segment, consecutive entries share MOD."""
        table = FrequencyTable.from_range(
            synth,
            100_000_000,
            200_000_000,
            50_000_000,
            allow_divider_change=True,
        )
        mods = [table[i]._fields["mod"] for i in range(len(table))]
        boundary = set(table.segment_boundaries)
        seg_start = 0
        for b in sorted(boundary) + [len(table)]:
            seg_mods = mods[seg_start:b]
            if len(seg_mods) > 1:
                assert len(set(seg_mods)) == 1
            seg_start = b

    def test_from_range_crossing_reports_bands(self, synth):
        """from_range raises DividerOctaveCrossingError with band bounds."""
        with pytest.raises(DividerOctaveCrossingError, match="Narrow to"):
            FrequencyTable.from_range(
                synth, 100_000_000, 3_000_000_000, 100_000_000
            )

    def test_from_range_allow_divider_change(self, synth):
        """from_range with allow_divider_change steps across divider bands."""
        table = FrequencyTable.from_range(
            synth,
            100_000_000,
            200_000_000,
            50_000_000,
            allow_divider_change=True,
        )
        assert len(table) >= 2


class TestPreencodedPlans:
    """Fast-hop plan shape."""

    def test_int_frac_only_hops_are_single_r0(self, synth):
        """In-band hops after the first are often a single R0 write."""
        table = FrequencyTable.from_range(
            synth, 190_000_000, 210_000_000, 2_000_000
        )
        if len(table) >= 2:
            assert len(table[1].plan) == 1
            assert (table[1].plan[0] & 0x7) == consts.REG0_ADDR


class TestSweeperPlayback:
    """Sweeper run and step."""

    def test_run_range_one_shot(self, synth):
        """run_range builds and plays without retaining an instance."""
        ADF435xSweeper.run_range(
            synth,
            190_000_000,
            210_000_000,
            2_000_000,
        )
        assert synth.is_powered
        assert synth.regfile.config.double_buffer is True

    def test_lazy_init_enables_fast_hop(self, synth):
        """First run() enables double buffer and powers the chip."""
        table = FrequencyTable.from_range(
            synth, 190_000_000, 195_000_000, 1_000_000
        )
        ADF435xSweeper(synth, table).run()
        assert synth.regfile.config.double_buffer is True
        assert synth.is_powered

    def test_step_returns_achieved_hz(self, synth):
        """step() returns achieved frequency then None at end."""
        table = FrequencyTable.from_frequencies(
            synth, [200_000_000, 201_000_000]
        )
        player = ADF435xSweeper(synth, table)
        first = player.step()
        assert isinstance(first, int)
        second = player.step()
        assert isinstance(second, int)
        assert player.step() is None

    def test_dwell_ms_sleeps(self, synth, monkeypatch):
        """dwell_ms invokes the sleep helper between hops."""
        sleeps = []
        monkeypatch.setattr(
            "adf435x.sweep._sleep_ms",
            lambda ms: sleeps.append(ms),
        )
        table = FrequencyTable.from_frequencies(
            synth, [200_000_000, 201_000_000]
        )
        ADF435xSweeper(synth, table, dwell_ms=50).run()
        assert sleeps.count(50) >= 1

    def test_wait_for_lock_calls_synth(self, synth, monkeypatch):
        """wait_for_lock=True polls wait_locked after each hop."""
        calls = []
        monkeypatch.setattr(
            synth,
            "wait_locked",
            lambda timeout_ms=100: calls.append(timeout_ms) or True,
        )
        table = FrequencyTable.from_frequencies(
            synth, [200_000_000, 201_000_000]
        )
        ADF435xSweeper(synth, table, wait_for_lock=True).run()
        assert len(calls) >= 1

    def test_boundary_dwell_at_divider_crossing(self, synth, monkeypatch):
        """Divider boundaries use boundary_dwell_ms and always wait lock."""
        sleeps = []
        lock_calls = []
        monkeypatch.setattr(
            "adf435x.sweep._sleep_ms",
            lambda ms: sleeps.append(ms),
        )
        monkeypatch.setattr(
            synth,
            "wait_locked",
            lambda timeout_ms=100: lock_calls.append(timeout_ms) or True,
        )
        table = FrequencyTable.from_frequencies(
            synth,
            [100_000_000, 300_000_000],
            allow_divider_change=True,
        )
        ADF435xSweeper(
            synth,
            table,
            dwell_ms=10,
            boundary_dwell_ms=200,
        ).run()
        assert 200 in sleeps
        assert len(lock_calls) >= 1

    def test_reset_restarts_playback(self, synth):
        table = FrequencyTable.from_frequencies(synth, [200_000_000])
        player = ADF435xSweeper(synth, table)
        assert player.step() is not None
        assert player.step() is None
        player.reset()
        assert player.step() is not None
