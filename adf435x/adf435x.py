from machine import Pin, SPI

class ADF435x:
    """
    MicroPython device handler for the ADF435x family of frequency
    synthesizers. This class manages basic SPI and GPIO communications between
    the host and device.

    Parameters
    ----------
    spi : machine.SPI
        A configured, transmit-capable SPI peripheral.
    load_enable_pin : int
        GPIO number for the load-enable (latch) line.
    chip_enable_pin : int
        GPIO number for chip enable.
    muxout_pin : int or None
        GPIO number for the MUXOUT status line, or None if MUXOUT is not used.
    """
    def __init__(self,
                 spi: SPI,
                 load_enable_pin: int,
                 chip_enable_pin: int,
                 muxout_pin:  int | None = None):
        """
        Constructor for ADF435xDevice.
        """
        # Initialize SPI and GPIO interfaces
        self.spi = spi
        self.load_enable_pin = Pin(load_enable_pin, Pin.OUT, value=0)
        self.chip_enable_pin = Pin(chip_enable_pin, Pin.OUT, value=0)
        if muxout_pin is None:
            self.muxout_pin = None
        else:
            self.muxout_pin = Pin(muxout_pin, Pin.IN)


    def chip_enable(self):
        """
        Power on the chip by setting the CE pin to logic high.
        """
        self.chip_enable_pin.high()

    def chip_disable(self):
        """
        Power off the chip by setting the CE pin to logic low.
        """
        self.chip_enable_pin.low()

    def read_muxout(self):
        """
        Read the raw level of the MUXOUT pin.
        """
        if self.muxout_pin is None:
            raise RuntimeError("MUXOUT pin was not configured")
        return self.muxout_pin.value()


    def write_register(self, word:int):
        """
        Write a 4-byte register value to the device. This is done by first
        writing the data to the device's input shift register over SPI, then
        latching it by toggling the LE pin.
        """
        # 1. Enforce that the LE pin is set to low before sending data.
        self.load_enable_pin.low()

        # 2. Write the data to the device input shift register over SPI
        self.spi.write(word.to_bytes(4, 'big'))

        # 3. Toggle the LE pin to latch the register value on the device
        self.load_enable_pin.high()
        self.load_enable_pin.low()

    def write_registers(self, words):
        """
        Write a sequence of register words in the order provided.

        Caution
        -------
        The caller is responsible for correctly ordering the register words to
        be written.
        """
        for word in words:
            self.write_register(word)
