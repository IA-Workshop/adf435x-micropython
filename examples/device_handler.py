"""
ADF435x device handler example. This example shows how to configure a device
handler, perform a register transacion, and read the value of the MUXOUT pin.

Modify the pin values to correspond to your specific setup.
"""
from machine import Pin, SPI

from adf435x.adf435x_device import ADF435xDevice

# Default pin values, modify as needed
SPI_SCK_PIN        = 10
SPI_MOSI_PIN       = 11

ADF435X_LE_PIN     = 13
ADF435X_CE_PIN     = 14
ADF435X_MUXOUT_PIN = 15

# 1. Create an SPI channel
RP2350_SPI_CHANNEL = 1

spi_handle = SPI(RP2350_SPI_CHANNEL,
                 baudrate=1000000,
                 polarity=0,
                 phase=0,
                 bits=8,
                 sck=SPI_SCK_PIN,
                 mosi=SPI_MOSI_PIN)

# 2. Instantiate an ADF435xDevice
adf_device = ADF435xDevice(spi_handle,
                           load_enable_pin=ADF435X_LE_PIN,
                           chip_enable_pin=ADF435X_CE_PIN,
                           muxout_pin=ADF435X_MUXOUT_PIN)


