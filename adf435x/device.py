"""SPI and GPIO driver for an ADF4350 or ADF4351 (MicroPython only).

Each register write sends one 32-bit word over SPI, most significant byte
first, then pulses LE (load enable) to latch it. See docs/hardware.md.
"""

from machine import Pin, SPI


class ADF435xDevice:
    """
    SPI and GPIO access to one ADF435x chip.

    Parameters
    ----------
    spi : machine.SPI
        A configured SPI bus that can transmit (mode 0).
    load_enable_pin : int
        GPIO number wired to LE.
    chip_enable_pin : int
        GPIO number wired to CE.
    muxout_pin : int or None
        GPIO number wired to MUXOUT, or None if MUXOUT is not wired.
    """

    def __init__(
        self,
        spi: SPI,
        load_enable_pin: int,
        chip_enable_pin: int,
        muxout_pin: int | None = None,
    ):
        """Set up the LE, CE and MUXOUT pins. LE and CE start low."""
        self.spi = spi
        self.load_enable_pin = Pin(load_enable_pin, Pin.OUT, value=0)
        self.chip_enable_pin = Pin(chip_enable_pin, Pin.OUT, value=0)
        if muxout_pin is None:
            self.muxout_pin = None
        else:
            self.muxout_pin = Pin(muxout_pin, Pin.IN)

        # Reused for every word so writes do not allocate memory.
        self._buf = bytearray(4)

    def chip_enable(self) -> None:
        """Drive CE high to power the chip up."""
        self.chip_enable_pin.high()

    def chip_disable(self) -> None:
        """Drive CE low to power the chip down."""
        self.chip_enable_pin.low()

    def read_muxout(self) -> int:
        """Return the logic level on MUXOUT, 0 or 1.

        Raises ``RuntimeError`` if no MUXOUT pin was given.
        """
        if self.muxout_pin is None:
            raise RuntimeError("MUXOUT pin was not configured")
        return self.muxout_pin.value()

    def write_register(self, word: int) -> None:
        """Shift one 32-bit register word into the chip and latch it.

        The register address is in the low three bits of *word*. LE stays low
        while the four bytes are clocked in, then a rising edge on LE latches
        them.
        """
        buf = self._buf
        buf[0] = (word >> 24) & 0xFF
        buf[1] = (word >> 16) & 0xFF
        buf[2] = (word >> 8) & 0xFF
        buf[3] = word & 0xFF

        le = self.load_enable_pin
        le.low()
        self.spi.write(buf)
        le.high()
        le.low()

    def write_registers(self, words) -> None:
        """Write each word in *words*, in the order given.

        The chip needs R5 first and R0 last. ``ADF435xRegisterFile`` plans
        produce that order.
        """
        for word in words:
            self.write_register(word)
