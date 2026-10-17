"""
Check the wiring with raw register writes and the MUXOUT pin.

Writes all six registers with MUXOUT set to DVDD (logic high), reads the pin,
then rewrites R2 with MUXOUT set to DGND (logic low) and reads it again. If
the readings follow, SPI, LE and the MUXOUT input all work. No PLL lock is
needed. Change the pin numbers below to match your board.
"""

from machine import Pin, SPI

from adf435x.device import ADF435xDevice

# Pin numbers: change these to match your wiring.
SPI_SCK_PIN = 10
SPI_MOSI_PIN = 11

ADF435X_LE_PIN = 13
ADF435X_CE_PIN = 14
ADF435X_MUXOUT_PIN = 9

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
    sck=Pin(SPI_SCK_PIN),
    mosi=Pin(SPI_MOSI_PIN),
)

adf_device = ADF435xDevice(
    spi_handle,
    load_enable_pin=ADF435X_LE_PIN,
    chip_enable_pin=ADF435X_CE_PIN,
    muxout_pin=ADF435X_MUXOUT_PIN,
)

# Register words for the ADF4351 data sheet worked example (p.21), except
# that the two R2 words route DVDD or DGND to MUXOUT instead of lock detect.
R0 = 0x00D30068
R1 = 0x080080C9
R2_MUXOUT_DVDD = 0x04004E42  # MUXOUT = DVDD (drives the pin high)
R2_MUXOUT_DGND = 0x08004E42  # MUXOUT = DGND (drives the pin low)
R3 = 0x00800003
R4 = 0x0091403C
R5 = 0x00580005


print("Setting CE to high -- powering on device")
adf_device.chip_enable()

# The chip needs R5 first and R0 last.
print("Writing Device Registers -- MUXOUT routed to DVDD (logic high)")
adf_device.write_registers([R5, R4, R3, R2_MUXOUT_DVDD, R1, R0])
print("MUXOUT after init (DVDD):", adf_device.read_muxout())

# MUXOUT is not double-buffered, so writing R2 alone is enough.
print("Writing Device Registers -- MUXOUT routed to DGND (logic low)")
adf_device.write_register(R2_MUXOUT_DGND)
print("MUXOUT after DGND:", adf_device.read_muxout())

print("Setting CE to low -- powering off device")
adf_device.chip_disable()

print("Example complete!")
