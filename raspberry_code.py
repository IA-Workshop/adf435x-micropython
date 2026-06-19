from machine import Pin, SPI, ADC
import time
from adf4351 import ADF4351

# Setup SPI for ADF4351
spi = SPI(0, baudrate=5000000, polarity=0, phase=0, bits=8)
le_pin = 5  # GPIO pin connected to LE (Latch Enable)

# Initialize the PLL
pll = ADF4351(spi, le_pin)
print("ADF4351 initialized")

# Setup photodiode ADC
photodiode = ADC(26)  # GP26 is ADC0

# Function to take a stable reading
def read_photodiode(samples=100, delay_us=100):
    total = 0
    for _ in range(samples):
        total += photodiode.read_u16()
        time.sleep_us(delay_us)
    return total / samples

# ODMR Sweep Parameters
start_freq_mhz = 2700  # 2.8 GHz
end_freq_mhz = 2900    # 2.9 GHz
step_mhz = 1         # 1 MHz steps
settle_ms = 5          # Time for PLL to lock (milliseconds)

print("Starting ODMR Sweep...")
print("Freq(MHz), ADC_Value")

# Perform the sweep
num_steps = int((end_freq_mhz - start_freq_mhz) / step_mhz) + 1

for i in range(num_steps):
    freq_mhz = start_freq_mhz + (i * step_mhz)
    freq_hz = int(freq_mhz * 1e6)
    
    # Set the frequency
    pll.set_frequency(freq_hz)
    
    # Wait for PLL to lock and settle
    time.sleep_ms(settle_ms)
    
    # Measure light intensity
    reading = read_photodiode()

    voltage = reading * 3.3 / 65535
    
    # Output data for graphing
    print(f"{freq_mhz:.3f}, {reading:.0f}, {voltage:.2f}")

print("Sweep Complete")
