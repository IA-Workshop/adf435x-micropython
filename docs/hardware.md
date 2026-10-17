# Hardware

The library works with any [MicroPython](glossary.md#micropython) board that
can send on [SPI](glossary.md#spi) and has three or four free
[GPIO](glossary.md#gpio) pins. Nothing in `adf435x/` is tied to one board:
your script chooses the pins and the SPI bus.

## Signals

| Signal | Purpose | Notes |
|--------|---------|-------|
| CLK, DATA | Register writes over SPI | One 32-bit word per [register](glossary.md#register), [MSB](glossary.md#msb) first |
| [LE](glossary.md#le) (load enable) | Latches each word | GPIO output; low while shifting, and a rising edge latches |
| [CE](glossary.md#ce) (chip enable) | Powers the chip | GPIO output; low powers down and keeps register contents |
| [MUXOUT](glossary.md#muxout) | [Lock detect](glossary.md#lock-detect) | GPIO input; optional, but `is_locked()` and `wait_locked()` need it |
| [REFIN](symbols.md#refin) | [Reference](glossary.md#reference) clock input | Its frequency is the `ref_hz` you pass in |

The chip has no SPI chip-select pin; LE does that job. DATA is only an
input, so MISO (data from the chip to the board) is not used.

## SPI settings

- Use SPI mode 0 (the clock rests low, and data is read on its rising edge),
  most significant bit first.
- The clock can be up to 20 MHz. The examples use 1 MHz, which is gentle on
  long wires; at 1 MHz a full six-register write takes about 0.2 ms.
- LE needs 20 ns of setup before the first clock edge and a 20 ns pulse.
  MicroPython toggles pins far more slowly than that, so no delays are
  needed.

`ADF435xDevice` handles LE for you:

```python
from machine import Pin, SPI
from adf435x.device import ADF435xDevice

spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11))
device = ADF435xDevice(spi, load_enable_pin=13, chip_enable_pin=14, muxout_pin=9)
```

Pass `muxout_pin=None` if MUXOUT is not wired. Lock detect is then not
available, and [sweeps](glossary.md#sweep) that change [RF
divider](glossary.md#rf-divider) wait a fixed time instead (see
[Sweeps](sweeps.md#divider-boundaries)).

### Using your own device object

`ADF435xSynthesizer` only needs an object with four methods, so you can wrap
a different SPI driver, a port expander, or a test fake:

| Method | What it does |
|--------|--------------|
| `write_registers(words)` | Write each 32-bit word in order, latching each with LE |
| `chip_enable()` / `chip_disable()` | Drive CE high / low |
| `read_muxout()` | Return 0 or 1; raise `RuntimeError` if MUXOUT is not wired |

## Reference clock

The data sheet specifies REFIN from 10 MHz to 250 MHz. Below 10 MHz the
clock's edges must be fast: its voltage must change faster than 21 V/µs.
With the reference doubler on, REFIN must be at most 30 MHz.

The [PFD](glossary.md#pfd) compares at [fPFD](symbols.md#fpfd) = REFIN × (1
+ D) ÷ (R × (1 + T)), which must stay at or below 32 MHz. Here D is 1 when
the doubler is on, R is the [R counter](glossary.md#r-counter) value, and T
is 1 when divide-by-2 is on. [Frequency
planning](frequency-planning.md#choosing-the-reference-path) covers how to
choose them.

## Output range

| Part | Output | [VCO](glossary.md#vco) | Largest RF divider |
|------|--------|-----|--------------------|
| ADF4351 | 34.375 MHz to 4.4 GHz | 2.2 to 4.4 GHz | ÷64 |
| ADF4350 | 137.5 MHz to 4.4 GHz | 2.2 to 4.4 GHz | ÷16 |

## Loop filter and charge-pump current

The [charge-pump](glossary.md#charge-pump) current (`cp_current_code`,
default 7, the [evaluation board](glossary.md#evaluation-board)'s value)
must suit your [loop filter](glossary.md#loop-filter). If your board's
filter is different, set it once after creating the synthesizer:

```python
synth.regfile.configure(cp_current_code=5)
```

## Reference setup

The examples assume this setup; change the pins for your board.

- Microcontroller: WeAct RP2350B running MicroPython (any board works).
- Synthesizer: the ADF4351 evaluation board with its own 10 MHz reference
  and loop filter, output on [RFOUTA](glossary.md#rfouta).

| Signal | GPIO |
|--------|------|
| SCK | GP10 (SPI1) |
| MOSI | GP11 (SPI1) |
| LE | GP13 |
| CE | GP14 |
| MUXOUT | GP9 |

## Bring-up checklist

1. Copy `adf435x/` to the board ([Development](development.md)).
2. Wire SPI, LE, CE, MUXOUT and ground, and check that REFIN has a clock.
3. Run [`examples/device_handler.py`](../examples/device_handler.py). It
   drives MUXOUT high and then low, which proves SPI, LE and the MUXOUT
   input without needing lock.
4. Run [`examples/fixed_frequency.py`](../examples/fixed_frequency.py) (200
   MHz) and check the output on a scope.
5. Work through the [bench validation cases](examples/validation.md).

## Lock detect is not a frequency measurement

Digital lock detect on MUXOUT says the loop has settled. It cannot tell you
that the output is the frequency you wanted; for example, the loop still
locks if `ref_hz` does not match the real reference. Check the output with
an instrument at least once for each new setup.
