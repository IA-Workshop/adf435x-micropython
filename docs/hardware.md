# Hardware

The library works with any MicroPython board that has an SPI transmitter and
three or four GPIO pins. Nothing in `adf435x/` is tied to a particular board:
pins and the SPI bus are chosen by your script.

## Signals

| Signal | Purpose | Notes |
|--------|---------|-------|
| CLK, DATA | Register writes over SPI | One 32-bit word per register, MSB first |
| LE (load enable) | Latches each word | GPIO output; low while shifting, a rising edge latches |
| CE (chip enable) | Powers the chip | GPIO output; low powers down and keeps register contents |
| MUXOUT | Lock detect | GPIO input; optional, but needed for `is_locked()` / `wait_locked()` |
| REFIN | Reference clock | Its frequency is the `ref_hz` you pass in |

The ADF435x has no SPI chip-select; LE does that job, so there is no CS pin
to wire. DATA is only an input, so MISO is not used.

## SPI settings

- **Mode 0** (clock idles low, data sampled on the rising edge), MSB first.
- **Clock:** up to 20 MHz. The examples use 1 MHz, which is easy on wiring;
  at 1 MHz a full six-register write takes about 0.2 ms.
- **Timing:** LE needs 20 ns of setup before the first clock and a 20 ns
  pulse; MicroPython's pin toggling is far slower than that, so no delays
  are needed.

`ADF435xDevice` does the LE handling for you:

```python
from machine import Pin, SPI
from adf435x.device import ADF435xDevice

spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11))
device = ADF435xDevice(spi, load_enable_pin=13, chip_enable_pin=14, muxout_pin=9)
```

Pass `muxout_pin=None` if MUXOUT is not wired. Lock detect then is not
available, and sweeps that change RF divider wait a fixed time instead (see
[Sweeps](sweeps.md#divider-boundaries)).

### Using your own device object

`ADF435xSynthesizer` only needs an object with four methods, so you can wrap
a different SPI driver, a port expander, or a test fake:

| Method | Does |
|--------|------|
| `write_registers(words)` | Write each 32-bit word in order, latching each with LE |
| `chip_enable()` / `chip_disable()` | Drive CE high / low |
| `read_muxout()` | Return 0 or 1; raise `RuntimeError` if MUXOUT is not wired |

## Reference clock

- REFIN accepts 10 MHz to 250 MHz (below 10 MHz the edge rate must be over
  21 V/µs). With the reference doubler on, REFIN must be at most 30 MHz.
- The phase detector (PFD) runs at REFIN × (doubler ? 2 : 1) / (R × (div2 ?
  2 : 1)) and must stay at or below 32 MHz. Choosing these is covered in
  [Frequency planning](frequency-planning.md#choosing-the-reference-path).

## Output range

| Part | Output | VCO | Largest RF divider |
|------|--------|-----|--------------------|
| ADF4351 | 34.375 MHz – 4.4 GHz | 2.2 – 4.4 GHz | ÷64 |
| ADF4350 | 137.5 MHz – 4.4 GHz | 2.2 – 4.4 GHz | ÷16 |

## Loop filter and charge-pump current

The charge-pump current (`cp_current_code`, default 7 as on the evaluation
board) must match your loop filter design. If your board uses a different
filter, set it once after creating the synthesizer:

```python
synth.regfile.configure(cp_current_code=5)
```

## Reference setup

The examples assume this setup; change the pins for your board.

- **MCU:** WeAct RP2350B running MicroPython (any board works)
- **Synthesizer:** ADF4351 evaluation board, its 10 MHz reference, stock
  loop filter, output on RFOUTA

| Signal | GPIO |
|--------|------|
| SCK | GP10 (SPI1) |
| MOSI | GP11 (SPI1) |
| LE | GP13 |
| CE | GP14 |
| MUXOUT | GP9 |

## Bring-up checklist

1. Copy `adf435x/` to the board ([Development](development.md)).
2. Wire SPI, LE, CE, MUXOUT and ground; confirm REFIN is running.
3. Run [`examples/device_handler.py`](../examples/device_handler.py): it
   drives MUXOUT high then low, which proves SPI, LE and the MUXOUT input
   without needing lock.
4. Run [`examples/fixed_frequency.py`](../examples/fixed_frequency.py)
   (200 MHz) and check the output on a scope.
5. Work through the [bench validation catalog](examples/validation.md).

## Lock detect is not a frequency measurement

Digital lock detect on MUXOUT says the loop has settled. It cannot tell you
the output is the frequency you wanted (for example if `ref_hz` does not
match the real reference). Check the output with an instrument at least once
for each new setup.
