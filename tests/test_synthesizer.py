"""Host tests for ADF435xSynthesizer (FakeDevice; no mock_machine required)."""

import pytest

from adf435x import consts
from adf435x.profiles import ADF4351
from adf435x.synthesizer import ADF435xSynthesizer

from conftest import WORKED_WORDS

REF_HZ = 10_000_000
GOLDEN_HZ = 2_112_600_000


class TestSetFrequency:
    """Frequency solve and SPI write path."""

    def test_golden_vector_words(self, synth, fake_device):
        """Golden target produces datasheet WORKED_WORDS on first power-up."""
        synth.power_up(frequency_hz=GOLDEN_HZ)
        # SPI order is R5 down to R0; WORKED_WORDS is indexed R0..R5.
        assert fake_device.writes == list(reversed(WORKED_WORDS))

    def test_set_frequency_after_power_up(self, synth, fake_device):
        """Retune sends a minimal stale plan after initial power-up."""
        synth.power_up(frequency_hz=200_000_000)
        n = len(fake_device.writes)
        synth.set_frequency(210_000_000)
        assert len(fake_device.writes) > n

    def test_returns_solve_result(self, synth):
        """set_frequency returns achieved frequency metadata."""
        synth.power_up()
        result = synth.set_frequency(GOLDEN_HZ)
        assert result.achieved_hz == GOLDEN_HZ
        assert result.error_hz == 0

    def test_frequency_and_achieved_properties(self, synth):
        """Read-only frequency properties track the last retune."""
        synth.power_up(frequency_hz=200_000_000)
        assert synth.frequency == 200_000_000
        assert synth.achieved_hz is not None


class TestWritePath:
    """Plan/mark split on SPI success and failure."""

    def test_mark_written_on_success(self, synth, fake_device):
        """Successful write advances regfile commit count."""
        synth.power_up(frequency_hz=200_000_000)
        assert synth.regfile.dump()["commit_count"] == 1
        assert synth.last_write_ms is not None

    def test_mark_write_failed_on_spi_error(self, synth, fake_device):
        """Failed SPI write invalidates the last-written cache."""
        synth.power_up(frequency_hz=200_000_000)
        fake_device.fail_next = True
        with pytest.raises(OSError):
            synth.set_frequency(210_000_000)
        assert synth.regfile._last_written == [None] * 6

    def test_power_up_full_six_word_write(self, synth, fake_device):
        """power_up sends exactly six register words."""
        synth.power_up(frequency_hz=200_000_000)
        assert len(fake_device.writes) == 6


class TestPowerLifecycle:
    """Chip enable and power state."""

    def test_power_up_enables_ce(self, synth, fake_device):
        """power_up drives chip enable high."""
        synth.power_up()
        assert fake_device.ce == 1
        assert synth.is_powered

    def test_power_down_disables_ce(self, synth, fake_device):
        """power_down drives chip enable low."""
        synth.power_up()
        synth.power_down()
        assert fake_device.ce == 0
        assert not synth.is_powered


class TestLockDetect:
    """MUXOUT lock polling."""

    def test_is_locked_reads_muxout(self, fake_device):
        """is_locked reflects the simulated MUXOUT pin."""
        fake_device.muxout = 1
        synth = ADF435xSynthesizer(fake_device, ADF4351, REF_HZ)
        assert synth.is_locked()

    def test_wait_locked_succeeds_when_muxout_high(self, synth, fake_device):
        """wait_locked returns True when already locked."""
        fake_device.muxout = 1
        assert synth.wait_locked(timeout_ms=10)

    def test_wait_locked_times_out(self, synth, fake_device):
        """wait_locked returns False when MUXOUT stays low."""
        fake_device.muxout = 0
        assert not synth.wait_locked(timeout_ms=5)


class TestOutputControls:
    """Mute and output power touch minimal register set."""

    def test_mute_disables_rf(self, synth):
        """mute sets rf_enable False in config."""
        synth.power_up()
        synth.mute()
        assert synth.regfile.config.rf_enable is False

    def test_unmute_enables_rf(self, synth):
        """unmute restores rf_enable."""
        synth.power_up()
        synth.mute()
        synth.unmute()
        assert synth.regfile.config.rf_enable is True

    def test_set_output_power(self, synth):
        """set_output_power updates the config field."""
        synth.power_up()
        synth.set_output_power(consts.REG4_POWER_MINUS_4DBM)
        assert (
            synth.regfile.config.output_power
            == consts.REG4_POWER_MINUS_4DBM
        )


class TestFastHopMode:
    """Private fast-hop settings for sweeper."""

    def test_enable_fast_hop_sets_double_buffer(self, synth):
        """_enable_fast_hop_mode enables double buffering."""
        synth._enable_fast_hop_mode()
        assert synth.regfile.config.double_buffer is True
        assert synth.regfile.config.ldp == consts.REG2_LDP_6NS

    def test_enable_fast_hop_is_idempotent(self, synth):
        """Second call to _enable_fast_hop_mode is a no-op."""
        synth._enable_fast_hop_mode()
        synth._enable_fast_hop_mode()
        assert synth._fast_hop_mode


class TestConfigureFailure:
    """Transactional configure leaves regfile unchanged on error."""

    def test_invalid_field_not_applied(self, synth, monkeypatch):
        """Bad solver output does not partial-apply or write SPI."""
        synth.power_up(frequency_hz=200_000_000)
        count_before = synth.regfile.dump()["commit_count"]

        def bad_solve(*args, **kwargs):
            from adf435x.solver import SolveResult

            return SolveResult(
                {"int_n": 1},
                0,
                0,
                REF_HZ,
                0,
            )

        monkeypatch.setattr("adf435x.synthesizer.solve", bad_solve)
        with pytest.raises(Exception):
            synth.set_frequency(200_000_000)
        assert synth.regfile.dump()["commit_count"] == count_before
