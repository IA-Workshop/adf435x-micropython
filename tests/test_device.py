"""Host tests for ADF435xDevice SPI/GPIO behavior (mock machine module).

The ``mock_machine`` fixture installs a fake ``machine`` module before the
device handler is imported, so these run on CPython with no hardware.
"""

import pytest


@pytest.mark.parametrize(
    "word, expected_bytes",
    [
        (0x00D30068, bytes([0x00, 0xD3, 0x00, 0x68])),
        (0x00000000, bytes([0x00, 0x00, 0x00, 0x00])),
        (0xFFFFFFFF, bytes([0xFF, 0xFF, 0xFF, 0xFF])),
        (0x12345678, bytes([0x12, 0x34, 0x56, 0x78])),
    ],
)
def test_write_register_spi_big_endian(mock_machine, word, expected_bytes):
    """A register word is sent as four big-endian (MSB-first) bytes."""
    # Import inside the test so the fake machine module is already in place.
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    dev = ADF435xDevice(spi, le_pin=1, ce_pin=2)
    dev.write_register(word)

    assert spi.writes == [expected_bytes]


@pytest.mark.parametrize(
    "word",
    [0x00D30068, 0x080080C9, 0x00580005],
)
def test_write_register_le_sequence(mock_machine, word):
    """write_register pulses LE low, high, low around the SPI write."""
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    le = mock_machine.Pin(1, mock_machine.Pin.OUT, value=0)
    dev = ADF435xDevice(spi, le_pin=1, ce_pin=2)
    dev.le_pin = le
    # Record each LE transition by wrapping the pin's low/high methods.
    transitions = []
    original_low = le.low
    original_high = le.high

    def track_low():
        transitions.append(0)
        original_low()

    def track_high():
        transitions.append(1)
        original_high()

    le.low = track_low
    le.high = track_high
    dev.write_register(word)

    # low (clock in) -> high (latch) -> low (idle); LE rests low.
    assert transitions == [0, 1, 0]
    assert le._value == 0


@pytest.mark.parametrize(
    "words",
    [
        [0xF5, 0xE4, 0xA0],
        [0x00D30068, 0x080080C9, 0x18004E42],
        [0x00580005],
    ],
)
def test_write_registers_preserves_order(mock_machine, words):
    """write_registers sends words in the exact order supplied."""
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    dev = ADF435xDevice(spi, le_pin=1, ce_pin=2)
    dev.write_registers(words)

    # Decode the captured big-endian writes back to ints to compare order.
    assert [int.from_bytes(b, "big") for b in spi.writes] == words


def test_read_muxout_requires_pin(mock_machine):
    """read_muxout raises when no MUXOUT pin was configured."""
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2, muxout_pin=None)
    with pytest.raises(RuntimeError, match="MUXOUT"):
        dev.read_muxout()


@pytest.mark.parametrize("pin_level", [0, 1])
def test_read_muxout_returns_pin_level(mock_machine, pin_level):
    """read_muxout returns the raw level of the configured MUXOUT pin."""
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2, muxout_pin=3)
    dev.muxout_pin._value = pin_level
    assert dev.read_muxout() == pin_level


@pytest.mark.parametrize(
    "method, expected_level",
    [
        ("chip_enable", 1),
        ("chip_disable", 0),
    ],
)
def test_chip_enable_disable(mock_machine, method, expected_level):
    """chip_enable drives CE high and chip_disable drives it low."""
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2)
    getattr(dev, method)()
    assert dev.ce_pin._value == expected_level
