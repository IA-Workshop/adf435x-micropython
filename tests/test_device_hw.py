"""Hardware-in-the-loop tests (require ``pytest --device`` and eval board)."""

import pytest

from adf435x.profiles import ADF4351
from adf435x.sweep import ADF435xSweeper
from adf435x.synthesizer import ADF435xSynthesizer

REF_HZ = 10_000_000
GOLDEN_HZ = 2_112_600_000


@pytest.fixture
def hw_synth():
    """
    Live synthesizer on the maintainer reference pin map (see agent/HARDWARE.md).

    Skipped unless ``--device`` is passed (see ``conftest.py``).
    """
    from machine import Pin, SPI

    from adf435x.device import ADF435xDevice

    spi = SPI(
        1,
        baudrate=1_000_000,
        polarity=0,
        phase=0,
        bits=8,
        sck=Pin(10),
        mosi=Pin(11),
    )
    device = ADF435xDevice(
        spi,
        load_enable_pin=13,
        chip_enable_pin=14,
        muxout_pin=15,
    )
    return ADF435xSynthesizer(device, ADF4351, ref_hz=REF_HZ)


@pytest.mark.device
def test_power_up_locks_at_golden(hw_synth):
    """MUXOUT reads locked after golden-frequency power-up."""
    hw_synth.power_up(frequency_hz=GOLDEN_HZ)
    assert hw_synth.wait_locked(timeout_us=500_000)


@pytest.mark.device
def test_sweeper_narrow_band(hw_synth):
    """Short in-band sweep completes without error."""
    ADF435xSweeper.run_range(
        hw_synth,
        190_000_000,
        195_000_000,
        1_000_000,
        dwell_us=100_000,
    )
