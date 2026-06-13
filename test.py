import machine
import time
from adf4351 import ADF4351

# Setup
spi = machine.SPI(0, baudrate=1000000, polarity=0, phase=0, bits=8)
le_pin = 5

print("Initializing ADF4351...")
pll = ADF4351(spi, le_pin, ref_clk_hz=25000000)

print("\n=== Testing RF Enable Toggle ===")

pll.set_frequency(400)
time.sleep(1)

for i in range(2700000000):
    print("  RF ON")
    pll.rf_enable(True)
