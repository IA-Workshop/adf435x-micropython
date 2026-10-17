# Quickstart

This page programs one output frequency and checks that the chip has
[locked](glossary.md#lock) onto it. You need:

- a board running [MicroPython](glossary.md#micropython);
- an ADF4350 or ADF4351 board, such as the Analog Devices [evaluation
  board](glossary.md#evaluation-board);
- an oscilloscope, frequency [counter](glossary.md#counter) or [spectrum
  analyzer](glossary.md#spectrum-analyzer) to see the output.

## 1. Install the library

Copy the `adf435x/` folder to the board so that `import adf435x` works (see
[Installation](../README.md#installation) or [Development](development.md)).

## 2. Wire the board

Connect the [SPI](glossary.md#spi) clock and data lines, two
[GPIO](glossary.md#gpio) outputs and, if you can, one GPIO input:

| ADF435x pin | Board pin | Direction |
|-------------|-----------|-----------|
| CLK | SPI SCK | output |
| DATA | SPI MOSI | output |
| [LE](glossary.md#le) | any GPIO | output |
| [CE](glossary.md#ce) | any GPIO | output |
| [MUXOUT](glossary.md#muxout) | any GPIO | input (optional, for lock detect) |

Connect the two boards' grounds together, and feed the
[reference](glossary.md#reference) clock to the [REFIN](symbols.md#refin)
pin. [Hardware](hardware.md) has the details and a reference pin map.

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

- `ref_hz` is the frequency of your reference clock, in whole hertz. For an
  ADF4350, use `ADF4350` instead of `ADF4351`.
- `power_up()` raises CE and writes all six
  [registers](glossary.md#register).
- `wait_locked()` returns `True` once MUXOUT reports lock. Lock means the
  [PLL](glossary.md#pll) has settled; it does not prove the frequency is
  right, so check it with an instrument.

## 4. Change frequency

```python
result = synth.set_frequency(433_920_000)
print(result.achieved_hz, result.error_hz, result.exact)
```

Only the registers that changed are written. `achieved_hz` is the output
rounded to the nearest hertz, `error_hz` is the target minus the achieved
frequency, and `exact` is `True` when the output is exactly the target.
[Frequency planning](frequency-planning.md) explains when a target cannot be
hit exactly.

## 5. Output controls

```python
from adf435x import consts

synth.set_output_power(consts.REG4_POWER_MINUS_4DBM)  # -4, -1, +2 or +5 dBm
synth.mute()          # RF output off, PLL keeps running
synth.unmute()
synth.power_down()    # chip-enable low; settings are kept
```

Output power is in [dBm](glossary.md#dbm).

## Next steps

- To hop through many frequencies quickly, see [Sweeps](sweeps.md).
- If something does not work, see [Troubleshooting](troubleshooting.md).
- For ready-made scripts, see [Examples](examples/index.md).
