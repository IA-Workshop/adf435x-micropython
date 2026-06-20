import array
from machine import Pin, SPI

class ADF4351:
    """
    MicroPython driver for the ADF4351 frequency synthesizer device.
    """
    def __init__(self,
                 spi: SPI,
                 le_pin: int,
                 ce_pin: int,
                 muxout_pin: int):
        # Initialize SPI and GPIO interfaces
        self.spi = spi
        self.le = Pin(le_pin, Pin.OUT, value=0)
        self.ce = Pin(ce_pin, Pin.OUT, value=0)
        self.muxout = Pin(muxout_pin, Pin.IN)


    def enable(self):
        """
        """
        self.ce.high()

    def disable(self):
        """
        """
        self.ce.low()

    def read_muxout(self):
        """
        """
        return self.muxout.value()

    def write_register(self, word: int):
        """
        """
        buf = word.to_bytes(4, 'big')
        self.spi.write(buf)
        self.le.high()
        self.le.low()

    def write_registers(self, words:list[int]):
        """
        """
        for word in words:
            self.write_register(word)
