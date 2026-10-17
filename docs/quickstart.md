# Quickstart

This walks through programming one output frequency and confirming lock.
You need a MicroPython board, an ADF4350 or ADF4351 board (for example the
Analog Devices evaluation board), and a scope, counter, or spectrum analyzer
to see the output.

## 1. Install the library

Copy the `adf435x/` folder to the board so that `import adf435x` works (see
[Installation](../README.md#installation) or [Development](development.md)).

## 2. Wire the board

Connect SPI clock and data, plus two GPIO outputs and, ideally, one input:

| ADF435x pin | Board pin | Direction |
|-------------|-----------|-----------|
| CLK | SPI SCK | output |
| DATA | SPI MOSI | output |
| LE | any GPIO | output |
| CE | any GPIO | output |
| MUXOUT | any GPIO | input (optional, for lock detect) |

Share ground between the boards and feed the reference clock to REFIN.
[Hardware](hardware.md) has the details and a reference pin map.

## 3. Program a frequency

```python
from machine import Pin, SPI

from adf435x import ADF4351, ADF435xSynthesizer
from adf435x.device import ADF435xDevice

spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11))
device = ADF435xDevice(spi, load_enable_pin=13, chip_enable_pin=14, muxout_pin=9)

synth = ADF435xSynthesizer(device, ADF4351, ref_hz=10_000_000)
synth.power_up(frequency_hz=200_000_000)

print("locked:", synth.wait_locked())
print("output:", synth.achieved_hz, "Hz")
```

- `ref_hz` is the frequency of your reference clock, in whole hertz. Use
  `ADF4350` instead of `ADF4351` for that part.
- `power_up()` raises the chip-enable line and writes all six registers.
- `wait_locked()` returns `True` once MUXOUT reports digital lock detect.
  Lock means the PLL has settled; confirm the frequency itself with an
  instrument.

## 4. Change frequency

```python
result = synth.set_frequency(433_920_000)
print(result.achieved_hz, result.error_hz, result.exact)
```

Only the registers that changed are written. `achieved_hz` is the output
rounded to the nearest hertz, `error_hz` is target minus achieved, and
`exact` is `True` when the output is exactly the target. See
[Frequency planning](frequency-planning.md) for when a target cannot be hit
exactly.

## 5. Output controls

```python
from adf435x import consts

synth.set_output_power(consts.REG4_POWER_MINUS_4DBM)  # -4, -1, +2 or +5 dBm
synth.mute()          # RF output off, PLL keeps running
synth.unmute()
synth.power_down()    # chip-enable low; settings are kept
```

## Next steps

- Hop through many frequencies quickly: [Sweeps](sweeps.md).
- Something not working: [Troubleshooting](troubleshooting.md).
- Ready-made scripts: [Examples](examples/index.md).
