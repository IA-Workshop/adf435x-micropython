"""
MicroPython SPI/GPIO handler for ADF435x frequency synthesizers.

Each register write is one 32-bit word on SPI (4 bytes, big-endian), followed
by a load-enable (LE) pulse that latches the shift-register contents into the
active register map. Multi-register updates must be ordered R5 down to R0 per
the datasheet; ``ADF435xRegisterFile.commit_plan()`` produces that order.
"""

from machine import Pin, SPI


class ADF435xDevice:
    """
    SPI and GPIO access to an ADF435x synthesizer.

    Parameters
    ----------
    spi : machine.SPI
        A configured, transmit-capable SPI peripheral.
    load_enable_pin : int
        GPIO number for the load-enable (LE) latch line.
    chip_enable_pin : int
        GPIO number for chip enable (CE).
    muxout_pin : int or None
        GPIO number for the MUXOUT status line, or None if MUXOUT is unused.
    """

    def __init__(
        self,
        spi: SPI,
        load_enable_pin: int,
        chip_enable_pin: int,
        muxout_pin: int | None = None,
    ):
        """Configure SPI and GPIO pins for the target board."""
        self.spi = spi
        self.load_enable_pin = Pin(load_enable_pin, Pin.OUT, value=0)
        self.chip_enable_pin = Pin(chip_enable_pin, Pin.OUT, value=0)
        if muxout_pin is None:
            self.muxout_pin = None
        else:
            self.muxout_pin = Pin(muxout_pin, Pin.IN)
        # Reused for every word so writes do not allocate.
        self._buf = bytearray(4)

    def chip_enable(self) -> None:
        """Drive CE high to power the synthesizer on."""
        self.chip_enable_pin.high()

    def chip_disable(self) -> None:
        """Drive CE low to power the synthesizer off."""
        self.chip_enable_pin.low()

    def read_muxout(self) -> int:
        """Return the raw logic level on the MUXOUT pin.

        Returns
        -------
        int
            0 or 1.

        Raises
        ------
        RuntimeError
            If ``muxout_pin`` was not configured at construction time.
        """
        if self.muxout_pin is None:
            raise RuntimeError("MUXOUT pin was not configured")
        return self.muxout_pin.value()

    def write_register(self, word: int) -> None:
        """Shift one 32-bit register word into the device and latch it.

        Parameters
        ----------
        word : int
            Register value; address is in DB2:DB0 of the word.

        Notes
        -----
        Sequence: LE low -> 4-byte SPI write (big-endian) -> LE high -> LE low.
        LE must be low while clocking data into the input shift register.
        """
        buf = self._buf
        buf[0] = (word >> 24) & 0xFF
        buf[1] = (word >> 16) & 0xFF
        buf[2] = (word >> 8) & 0xFF
        buf[3] = word & 0xFF
        le = self.load_enable_pin
        # LE low while shifting; one 32-bit word, MSB first (big-endian).
        le.low()
        self.spi.write(buf)
        # Rising edge on LE latches the shift register into the active map.
        le.high()
        le.low()

    def write_registers(self, words) -> None:
        """Write register words in caller-supplied order.

        Parameters
        ----------
        words : iterable of int
            Register values to send, one ``write_register`` call each.

        Notes
        -----
        The caller must supply datasheet-correct order (usually R5 down to
        R0). Double-buffered fields in R1, R2, and optionally R4 require a
        final R0 write to latch; see ``ADF435xRegisterFile.commit_plan()``.
        """
        for word in words:
            self.write_register(word)
