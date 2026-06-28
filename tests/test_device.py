"""Host tests for ADF435xDevice SPI/GPIO behavior (mock machine module)."""

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
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    dev = ADF435xDevice(spi, load_enable_pin=1, chip_enable_pin=2)
    dev.write_register(word)

    assert spi.writes == [expected_bytes]


@pytest.mark.parametrize(
    "word",
    [0x00D30068, 0x080080C9, 0x00580005],
)
def test_write_register_le_sequence(mock_machine, word):
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    le = mock_machine.Pin(1, mock_machine.Pin.OUT, value=0)
    dev = ADF435xDevice(spi, load_enable_pin=1, chip_enable_pin=2)
    dev.load_enable_pin = le
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
    from adf435x.device import ADF435xDevice

    spi = mock_machine.SPI()
    dev = ADF435xDevice(spi, load_enable_pin=1, chip_enable_pin=2)
    dev.write_registers(words)

    assert [int.from_bytes(b, "big") for b in spi.writes] == words


def test_read_muxout_requires_pin(mock_machine):
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2, muxout_pin=None)
    with pytest.raises(RuntimeError, match="MUXOUT"):
        dev.read_muxout()


@pytest.mark.parametrize("pin_level", [0, 1])
def test_read_muxout_returns_pin_level(mock_machine, pin_level):
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
    from adf435x.device import ADF435xDevice

    dev = ADF435xDevice(mock_machine.SPI(), 1, 2)
    getattr(dev, method)()
    assert dev.chip_enable_pin._value == expected_level
