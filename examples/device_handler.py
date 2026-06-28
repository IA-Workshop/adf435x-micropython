"""
ADF435x device handler example. This example shows how to configure a device
handler, perform a register transacion, and read the value of the MUXOUT pin.

Modify the pin values to correspond to your specific setup.
"""

from machine import SPI

from adf435x.device import ADF435xDevice

# Default pin values, modify as needed
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11

ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14
ADF435X_MUXOUT_PIN = 15

# 1. Create an SPI channel
SPI_CHANNEL = 1

print(
    f"Opening SPI channel {SPI_CHANNEL} on pins "
    f"{SPI_SCK_PIN} (SCK), "
    f"{SPI_MOSI_PIN} (MOSI)"
)

spi_handle = SPI(
    SPI_CHANNEL,
    baudrate=1000000,
    polarity=0,
    phase=0,
    bits=8,
    sck=SPI_SCK_PIN,
    mosi=SPI_MOSI_PIN,
)

# 2. Instantiate an ADF435xDevice
adf_device = ADF435xDevice(
    spi_handle,
    load_enable_pin=ADF435X_LE_PIN,
    chip_enable_pin=ADF435X_CE_PIN,
    muxout_pin=ADF435X_MUXOUT_PIN,
)

# 3. Define minimal register words needed for operation. (Taken from ADF4351
#    datasheet worked example, p. 21). R2 is given in two variants that differ
#    only in the MUXOUT source that will drive the pin high, then low, for a
#    basic connectivity test.
R0 = 0x00D30068
R1 = 0x080080C9
R2_MUXOUT_DVDD = 0x04004E42  # MUXOUT = DVDD (drives the pin high)
R2_MUXOUT_DGND = 0x08004E42  # MUXOUT = DGND (drives the pin low)
R3 = 0x00800003
R4 = 0x0091403C
R5 = 0x00580005


# 4. Power on device
print("Setting CE to high -- powering on device")
adf_device.chip_enable()

# 5. Route DVDD to MUXOUT and confirm the pin reads logic high (1)
print("Writing Device Registers -- MUXOUT routed to DVDD (logic high)")
adf_device.write_registers([R5, R4, R3, R2_MUXOUT_DVDD, R1, R0])
print("MUXOUT after init (DVDD):", adf_device.read_muxout())


# 6. Route DGND to MUXOUT and confirm the pin reads logic low (0)
print("Writing Device Registers -- MUXOUT routed to DGND (logic low)")
adf_device.write_register(R2_MUXOUT_DGND)
print("MUXOUT after DGND:", adf_device.read_muxout())


# 7. Power off device
print("Setting CE to low -- powering off device")
adf_device.chip_disable()

print("Example complete!")
