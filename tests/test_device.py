"""Host tests for ADF435xDevice SPI/GPIO behavior (mock machine module)."""

import pytest


def test_write_register_spi_and_le(mock_machine):
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    dev = ADF435xDevice(spi, load_enable_pin=1, chip_enable_pin=2)
    dev.write_register(0x00D30068)

    assert spi.writes == [bytes([0x00, 0xD3, 0x00, 0x68])]
    assert dev.load_enable_pin._value == 0


def test_write_registers_preserves_order(mock_machine):
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    dev = ADF435xDevice(spi, load_enable_pin=1, chip_enable_pin=2)
    words = [0xF5, 0xE4, 0xA0]
    dev.write_registers(words)

    assert [int.from_bytes(b, "big") for b in spi.writes] == words


def test_read_muxout_requires_pin(mock_machine):
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2, muxout_pin=None)
    with pytest.raises(RuntimeError, match="MUXOUT"):
        dev.read_muxout()


def test_read_muxout_returns_pin_level(mock_machine):
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2, muxout_pin=3)
    assert dev.read_muxout() == 0
    dev.muxout_pin._value = 1
    assert dev.read_muxout() == 1


def test_chip_enable_disable(mock_machine):
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2)
    dev.chip_enable()
    assert dev.chip_enable_pin._value == 1
    dev.chip_disable()
    assert dev.chip_enable_pin._value == 0
