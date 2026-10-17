"""Host tests for FrequencyTable building and synthesizer playback."""

import pytest

from adf435x import consts
from adf435x.profiles import ADF4351
from adf435x.sweep import DividerOctaveCrossingError, FrequencyTable
from adf435x.synthesizer import ADF435xSynthesizer, LockTimeoutError
from conftest import FakeChip, FakeDevice

REF_HZ = 10_000_000

# Playback dwells for real; record the sleeps instead.
pytestmark = pytest.mark.usefixtures("no_sleep")

# Exact at the RF output with MODs 3125 and 640 (fPFD 10 MHz, divide-by-1):
# 220 + 1/3125 and 220 + 1/640. Their LCM (400000) exceeds 4095.
_MOD_3125_HZ = 2_200_003_200
_MOD_640_HZ = 2_200_015_625


class TestFromRange:
    """Range tables honor bounds and step."""

    def test_entries_on_requested_points(self, synth):
        """190-210 MHz in 2 MHz steps is exactly 190, 192, ... 210 MHz."""
        table = FrequencyTable.from_range(synth, 190_000_000, 210_000_000, 2_000_000)
        achieved = [table[i].achieved_hz for i in range(len(table))]
        assert achieved == list(range(190_000_000, 210_000_001, 2_000_000))

    def test_upper_bound_appended(self, synth):
        """A step that misses upper_hz still ends on upper_hz."""
        table = FrequencyTable.from_range(synth, 190_000_000, 195_000_000, 2_000_000)
        assert [table[i].target_hz for i in range(len(table))] == [
            190_000_000,
            192_000_000,
            194_000_000,
            195_000_000,
        ]

    def test_single_point_range(self, synth):
        """lower_hz == upper_hz gives one entry."""
        assert len(FrequencyTable.from_range(synth, 200_000_000, 200_000_000, 1)) == 1

    def test_channel_step_for_locked_table(self, synth):
        """MOD 5 at divide-by-16 from 10 MHz is a 125 kHz channel step."""
        table = FrequencyTable.from_range(synth, 190_000_000, 210_000_000, 2_000_000)
        assert table.channel_step_hz == 125_000

    def test_reversed_bounds_rejected(self, synth):
        """lower_hz above upper_hz raises."""
        with pytest.raises(ValueError, match="lower_hz"):
            FrequencyTable.from_range(synth, 210_000_000, 190_000_000, 1_000_000)

    @pytest.mark.parametrize("step", [0, -5])
    def test_non_positive_step_rejected(self, synth, step):
        """step_hz must be positive."""
        with pytest.raises(ValueError, match="step_hz"):
            FrequencyTable.from_range(synth, 190_000_000, 210_000_000, step)

    def test_float_bound_rejected(self, synth):
        """Frequencies are integer hertz."""
        with pytest.raises(TypeError):
            FrequencyTable.from_range(synth, 190e6, 210_000_000, 2_000_000)


class TestModRule:
    """One MOD per divider band when it can hit every point exactly."""

    def test_locked_mod_shared(self, synth):
        """A 25 kHz channel plan shares one MOD across the table."""
        table = FrequencyTable.from_range(synth, 433_050_000, 434_790_000, 25_000)
        assert len({table[i].fields["mod"] for i in range(len(table))}) == 1

    def test_locked_table_is_exact(self, synth):
        """Every point of a locked table is exact."""
        table = FrequencyTable.from_range(synth, 433_050_000, 434_790_000, 25_000)
        assert table.max_error_hz == 0

    def test_fallback_gives_each_point_its_own_mod(self, synth):
        """When no MOD <= 4095 fits all points, each keeps its best MOD."""
        table = FrequencyTable.from_frequencies(synth, [_MOD_3125_HZ, _MOD_640_HZ])
        assert [table[i].fields["mod"] for i in range(2)] == [3125, 640]

    def test_fallback_stays_exact(self, synth):
        """The per-point fallback does not give up accuracy."""
        table = FrequencyTable.from_frequencies(synth, [_MOD_3125_HZ, _MOD_640_HZ])
        assert table.max_error_hz == 0

    def test_locked_segment_keeps_one_pll_mode(self, synth):
        """Integer channels in a fractional table keep frac-N settings."""
        # 190 MHz is integer-N on its own (N = 304); 192 MHz is not.
        table = FrequencyTable.from_range(synth, 190_000_000, 194_000_000, 2_000_000)
        assert {table[i].fields["ldf"] for i in range(len(table))} == {
            consts.REG2_LDF_FRAC_N
        }

    def test_all_integer_segment_uses_int_n_settings(self, synth):
        """A table of integer-N channels uses integer-N settings."""
        table = FrequencyTable.from_frequencies(synth, [190_000_000, 200_000_000])
        assert {table[i].fields["ldf"] for i in range(len(table))} == {
            consts.REG2_LDF_INT_N
        }

    def test_max_error_hz_enforced(self, synth):
        """A table that cannot meet max_error_hz raises."""
        # Halfway between N = 220 and 220 + 1/4095 at fPFD 10 MHz: the
        # nearest reachable output is about 600 Hz away.
        with pytest.raises(ValueError, match="max_error_hz"):
            FrequencyTable.from_frequencies(synth, [2_200_001_221], max_error_hz=100)

    def test_low_spur_mode_mod_at_least_50(self, synth):
        """In low-spur mode a locked MOD is raised to >= 50."""
        synth.regfile.configure(noise_mode=consts.REG2_LOW_SPUR, mod=50)
        table = FrequencyTable.from_range(synth, 190_000_000, 210_000_000, 2_000_000)
        assert table[0].fields["mod"] >= 50


class TestFromFrequencies:
    """Explicit frequency lists."""

    def test_preserves_order(self, synth):
        """Entries follow the caller-supplied order."""
        freqs = [200_000_000, 195_000_000, 205_000_000]
        table = FrequencyTable.from_frequencies(synth, freqs)
        assert [table[i].target_hz for i in range(len(table))] == freqs

    def test_empty_list_raises(self, synth):
        """An empty list is rejected."""
        with pytest.raises(ValueError, match="empty"):
            FrequencyTable.from_frequencies(synth, [])

    def test_divider_crossing_reports_bands(self, synth):
        """A crossing names each divider's band and narrower ranges."""
        with pytest.raises(DividerOctaveCrossingError) as exc:
            FrequencyTable.from_frequencies(synth, [100_000_000, 3_000_000_000])
        err = exc.value
        assert (err.lower_hz, err.upper_hz) == (100_000_000, 3_000_000_000)
        assert err.lower_band_hz[0] <= err.lower_hz <= err.lower_band_hz[1]
        assert err.upper_band_hz[0] <= err.upper_hz <= err.upper_band_hz[1]
        assert "allow_divider_change=True" in str(err)

    def test_allow_divider_change_marks_boundary(self, synth):
        """The entry that starts a new divider is marked."""
        table = FrequencyTable.from_frequencies(
            synth, [100_000_000, 3_000_000_000], allow_divider_change=True
        )
        assert [table[i].divider_boundary for i in range(2)] == [False, True]

    def test_range_boundaries_at_divider_edges(self, synth):
        """100-300 MHz in 25 MHz steps switches divider at 150 and 275 MHz."""
        table = FrequencyTable.from_range(
            synth, 100_000_000, 300_000_000, 25_000_000, allow_divider_change=True
        )
        starts = [
            table[i].target_hz for i in range(len(table)) if table[i].divider_boundary
        ]
        assert starts == [150_000_000, 275_000_000]


class TestEncoding:
    """Entry words follow the synthesizer's settings."""

    def test_words_encode_fields(self, synth):
        """Each entry's words are the encoding of its fields."""
        table = FrequencyTable.from_range(synth, 190_000_000, 194_000_000, 2_000_000)
        mapper = synth.regfile._mapper
        cfg = synth.regfile.config.copy()
        for name, value in table[1].fields.items():
            setattr(cfg, name, value)
        assert table[1].words == mapper.encode_config(cfg)

    def test_settings_change_re_encodes(self, fake_chip):
        """A settings change after building reaches the next hop."""
        synth = ADF435xSynthesizer(fake_chip, ADF4351, REF_HZ)
        table = FrequencyTable.from_range(synth, 190_000_000, 194_000_000, 2_000_000)
        synth.play_step(table, 0)
        synth.set_output_power(consts.REG4_POWER_MINUS_4DBM)
        synth.play_step(table, 1)
        r4 = fake_chip.active_words[consts.REG4_ADDR]
        assert (r4 >> consts.REG4_OUTPUT_POWER_POS) & 3 == consts.REG4_POWER_MINUS_4DBM

    def test_building_does_not_change_synth(self, synth):
        """Building a table leaves the synthesizer's settings alone."""
        before = synth.regfile.current_words()
        FrequencyTable.from_range(synth, 190_000_000, 210_000_000, 2_000_000)
        assert synth.regfile.current_words() == before


class TestPlayback:
    """ADF435xSynthesizer.play / play_step."""

    def test_first_hop_unpowered_writes_all(self, fake_chip):
        """A never-programmed chip gets the full R5..R0 write."""
        synth = ADF435xSynthesizer(fake_chip, ADF4351, REF_HZ)
        table = FrequencyTable.from_range(synth, 190_000_000, 194_000_000, 2_000_000)
        synth.play_step(table, 0)
        assert len(fake_chip.writes) == 6

    def test_play_powers_chip(self, fake_device, synth):
        """play() raises CE when the chip was off."""
        table = FrequencyTable.from_frequencies(synth, [200_000_000])
        synth.play(table)
        assert fake_device.ce == 1 and synth.is_powered

    def test_play_returns_no_timeouts(self, synth):
        """A locked sweep reports zero lock timeouts."""
        table = FrequencyTable.from_range(synth, 190_000_000, 194_000_000, 2_000_000)
        assert synth.play(table, wait_for_lock=True) == 0

    def test_play_step_returns_entry(self, synth):
        """play_step returns the programmed entry and updates frequency."""
        table = FrequencyTable.from_frequencies(synth, [200_000_000, 201_000_000])
        entry = synth.play_step(table, 1)
        assert (entry.achieved_hz, synth.frequency) == (201_000_000, 201_000_000)

    def test_dwell_between_hops(self, synth, monkeypatch):
        """dwell_us sleeps after every in-band hop."""
        sleeps = []
        monkeypatch.setattr("adf435x.synthesizer._sleep_us", sleeps.append)
        table = FrequencyTable.from_frequencies(synth, [200_000_000, 201_000_000])
        synth.power_up(frequency_hz=200_000_000)
        synth.play(table, dwell_us=50_000)
        assert sleeps == [50_000, 50_000]

    def test_wait_for_lock_each_hop(self, synth, monkeypatch):
        """wait_for_lock waits after every hop."""
        calls = []
        monkeypatch.setattr(synth, "wait_locked", lambda **kw: calls.append(1) or True)
        table = FrequencyTable.from_frequencies(synth, [200_000_000, 201_000_000])
        synth.power_up(frequency_hz=200_000_000)
        synth.play(table, wait_for_lock=True)
        assert len(calls) == 2

    def test_boundary_hop_waits_and_dwells(self, synth, monkeypatch):
        """A divider change waits for lock and uses boundary_dwell_us."""
        sleeps, calls = [], []
        monkeypatch.setattr("adf435x.synthesizer._sleep_us", sleeps.append)
        monkeypatch.setattr(synth, "wait_locked", lambda **kw: calls.append(1) or True)
        table = FrequencyTable.from_frequencies(
            synth, [100_000_000, 300_000_000], allow_divider_change=True
        )
        synth.power_up(frequency_hz=100_000_000)
        synth.play(table, dwell_us=10_000, boundary_dwell_us=200_000)
        assert (sleeps, len(calls)) == ([10_000, 200_000], 1)

    def test_no_muxout_skips_lock_wait(self, monkeypatch):
        """Without MUXOUT, boundary hops dwell instead of waiting for lock."""
        synth = ADF435xSynthesizer(FakeDevice(muxout=None), ADF4351, REF_HZ)
        sleeps = []
        monkeypatch.setattr("adf435x.synthesizer._sleep_us", sleeps.append)
        table = FrequencyTable.from_frequencies(
            synth, [100_000_000, 300_000_000], allow_divider_change=True
        )
        synth.power_up(frequency_hz=100_000_000)
        assert synth.play(table, boundary_dwell_us=200_000) == 0
        assert sleeps == [200_000]

    def test_require_lock_raises_on_timeout(self, monkeypatch):
        """require_lock turns a lock timeout into LockTimeoutError."""
        synth = ADF435xSynthesizer(FakeChip(muxout=0), ADF4351, REF_HZ)
        monkeypatch.setattr(synth, "wait_locked", lambda **kw: False)
        table = FrequencyTable.from_frequencies(synth, [200_000_000])
        with pytest.raises(LockTimeoutError):
            synth.play(table, wait_for_lock=True, require_lock=True)

    def test_timeouts_counted(self, monkeypatch):
        """Without require_lock, timeouts are counted, not raised."""
        synth = ADF435xSynthesizer(FakeChip(muxout=0), ADF4351, REF_HZ)
        monkeypatch.setattr(synth, "wait_locked", lambda **kw: False)
        table = FrequencyTable.from_frequencies(synth, [200_000_000, 201_000_000])
        assert synth.play(table, wait_for_lock=True) == 2

    def test_cycles_repeat(self, fake_chip):
        """cycles=2 plays the table twice; the wrap hop is a delta write."""
        synth = ADF435xSynthesizer(fake_chip, ADF4351, REF_HZ)
        table = FrequencyTable.from_frequencies(synth, [200_000_000, 201_000_000])
        synth.play(table, cycles=2)
        # 6 (first) + 1 + 1 (wrap back to entry 0) + 1
        assert len(fake_chip.writes) == 9
