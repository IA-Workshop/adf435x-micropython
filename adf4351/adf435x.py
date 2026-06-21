from machine import Pin, SPI

class ADF435x:
    """
    MicroPython driver for the ADF435x family of frequency synthesizers. This
    class is a basic transport-level controller that handles SPI and GPIO
    communications with the device.

    Parameters
    ----------
    spi : machine.SPI
        A configured, transmit-capable SPI peripheral in mode 0 (polarity 0,
        phase 0), 8-bit frames, clock at or below the device maximum.
    le_pin : int
        GPIO number for the load-enable (latch) line.
    ce_pin : int
        GPIO number for chip enable.
    muxout_pin : int
        GPIO number for the MUXOUT status line.

    """
    def __init__(self, spi: SPI, le_pin: int, ce_pin: int, muxout_pin: int):
        # Initialize SPI and GPIO interfaces
        self.spi = spi
        self.le = Pin(le_pin, Pin.OUT, value=0)
        self.ce = Pin(ce_pin, Pin.OUT, value=0)
        self.muxout = Pin(muxout_pin, Pin.IN)

        # Power on
        self.chip_enable()

    def chip_enable(self):
        """
        Power on the chip by setting the CE pin to logic high.
        """
        self.ce.high()

    def chip_disable(self):
        """
        Power off the chip by setting the CE pin to logic low.
        """
        self.ce.low()

    def read_muxout(self):
        """
        Read the state of the MUXOUT pin.
        """
        return self.muxout.value()

    def write_register(self, word:int):
        """
        Write a 4-byte register value to the device. This is done by first
        writing the data to the device's input shift register over SPI, then
        latching it by toggling the LE pin.
        """
        # 1. Write the data to the device input shift register over SPI
        self.spi.write(word.to_bytes(4, 'big'))

        # 2. Toggle the LE pin to latch the register value on the device
        self.le.high()
        self.le.low()

