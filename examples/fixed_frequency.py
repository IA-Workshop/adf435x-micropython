"""
Program one output frequency and check for lock.

Set ``TARGET_FREQ_HZ``, run the script on the board, and probe RFOUTA. The
default, 200 MHz, is low enough for a 200 MHz oscilloscope. The pins and the
10 MHz reference match the reference setup in docs/hardware.md; change
``PINS`` and ``REF_HZ`` for your board. Walkthrough and other targets to
try: docs/examples/fixed-frequency.md.
"""

from machine import Pin, SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.synthesizer import ADF435xSynthesizer

# --- Settings to change ------------------------------------------------------
TARGET_FREQ_HZ = 200_000_000
REF_HZ = 10_000_000

PINS = {
    "spi_channel": 1,
    "sck": 10,
    "mosi": 11,
    "le": 13,
    "ce": 14,
    "muxout": 9,
}

spi = SPI(
    PINS["spi_channel"],
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    bits=8,
    sck=Pin(PINS["sck"]),
    mosi=Pin(PINS["mosi"]),
)

device = ADF435xDevice(
    spi,
    load_enable_pin=PINS["le"],
    chip_enable_pin=PINS["ce"],
    muxout_pin=PINS["muxout"],
)

synth = ADF435xSynthesizer(device, ADF4351, ref_hz=REF_HZ)

print("Powering up at %.6f MHz" % (TARGET_FREQ_HZ / 1e6))
synth.power_up(frequency_hz=TARGET_FREQ_HZ)

locked = synth.wait_locked(timeout_us=500_000)
print("Target:    %d Hz (%.6f MHz)" % (TARGET_FREQ_HZ, TARGET_FREQ_HZ / 1e6))
print("Achieved:  %d Hz (%.6f MHz)" % (
    synth.achieved_hz,
    synth.achieved_hz / 1e6,
))
print("MUXOUT:    %s" % ("high" if locked else "not high within timeout"))
print("Probe RFOUTA with scope or counter.")
