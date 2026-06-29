# Hardware

The library is **board-agnostic**. It targets any MicroPython board with SPI
and a few GPIO lines for LE, CE, and optional MUXOUT. It is not limited to
RP2040/2350, Pico, or WeAct boards.

This document describes:

1. Generic wiring requirements (all boards)
2. One **reference setup** used by the maintainer for examples and HIL tests
3. Bring-up checklist

## Generic requirements

| Signal | Role | Notes |
|--------|------|-------|
| SPI SCK, MOSI | Register writes | 32-bit words, MSB first; mode 0 typical |
| LE | Latch enable | GPIO output; rising edge latches each word |
| CE | Chip enable | GPIO output |
| MUXOUT | Lock detect (optional) | GPIO input; needed for `is_locked()` |
| REFIN | Reference clock | Frequency passed as `ref_hz` to synthesizer |

Use [`ADF435xDevice`](../adf435x/device.py) or any duck-typed object with the
same methods. SPI bus index, pin numbers, and baud rate are chosen by the
application — not fixed by the library.

## Reference setup (maintainer)

Examples in [`examples/`](../examples/) and hardware tests in
[`test_device_hw.py`](../tests/test_device_hw.py) assume this wiring. **Adjust
pins and SPI bus for your board.**

- **MCU:** WeAct RP2350B (MicroPython) — one of many compatible boards
- **PLL:** ADF4351 evaluation board
- **Reference:** 10 MHz onboard REFIN
- **Loop filter:** Fixed passive (eval board default)
- **Primary output:** RFOUTA

### Reference pin map (SPI1)

| Signal | GPIO | Notes |
|--------|------|-------|
| SCK | GP10 | SPI1 clock |
| MOSI | GP11 | SPI1 data |
| LE | GP13 | Latch enable |
| CE | GP14 | Chip enable |
| MUXOUT | GP15 | Digital lock detect (input) |

SPI: 1 MHz, mode 0.

## Default synthesizer configuration

Reference examples assume:

- 10 MHz reference (`ref_hz=10_000_000`)
- R counter = 1, doubler off, div-by-2 off
- MUXOUT routed to digital lock detect (default register config)

## Porting to another board

1. Copy `adf435x/` to the MicroPython filesystem.
2. Instantiate `machine.SPI` with your bus and pins (or wrap in a custom device).
3. Pass integer GPIO numbers to `ADF435xDevice` (or implement the duck-typed
   interface for `ADF435xSynthesizer`).
4. Set `ref_hz` and loop-filter-related fields to match your hardware.

Do not hard-code board-specific pins in library modules under `adf435x/`.

## Bring-up checklist

1. Deploy `adf435x/` (see [README](../README.md)).
2. Wire SPI + LE + CE + MUXOUT for your board.
3. Run `power_up()` at golden frequency (2112.6 MHz); confirm lock via MUXOUT.
4. Scope RFOUT; compare to `result.achieved_hz`.
5. Step through a small frequency range via `set_frequency()`.
6. Optional: run `pytest --device` if your board matches the reference pin map.

Analog output verification (spectrum, power) remains manual.

## MUXOUT caveat

Do not leave MUXOUT on the N-divider during band-select (R0) writes if
reconfiguring MUXOUT for debug. Default config uses digital lock detect;
register file write ordering should preserve lock polling during normal
retunes.

## Status

See [STATUS.md](STATUS.md) for hardware bring-up completion state.
