"""
ADF435x fixed-frequency example using ADF435xSynthesizer.

Set ``TARGET_FREQ_HZ`` to the desired RF output, run on the board, and probe
RFOUTA with an oscilloscope.

Hardware assumptions (ADF4351 eval board + WeAct RP2350B)
---------------------------------------------------------
- 10 MHz reference on REFIN (R counter = 1, no doubler).
- SPI1: SCK=GP10, MOSI=GP11, LE=GP13, CE=GP14, MUXOUT=GP15.
- 1 MHz SPI, mode 0.

Scope notes
-----------
- Default target is 200 MHz (scope-friendly). For the datasheet golden
  example, use ``TARGET_FREQ_HZ = 2_112_600_000`` (needs sufficient BW).
"""

from machine import SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.synthesizer import ADF435xSynthesizer

# --- User settings -----------------------------------------------------------
TARGET_FREQ_HZ = 200_000_000
REF_HZ = 10_000_000

PINS = {
    "spi_channel": 1,
    "sck": 10,
    "mosi": 11,
    "le": 13,
    "ce": 14,
    "muxout": 15,
}

spi = SPI(
    PINS["spi_channel"],
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    bits=8,
    sck=PINS["sck"],
    mosi=PINS["mosi"],
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

if synth.wait_locked(timeout_ms=500):
    print("Locked (MUXOUT high)")
else:
    print("Not locked within timeout — check loop filter and wiring")

print("Target:    %d Hz" % synth.frequency)
print("Achieved:  %d Hz (%.6f MHz)" % (
    synth.achieved_hz,
    synth.achieved_hz / 1e6,
))
print("Probe RFOUTA to verify.")
