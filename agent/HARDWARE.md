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

Examples in [`examples/`](../examples/) assume this wiring.
**Adjust pins and SPI bus for your board.**

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
| MUXOUT | GP9 | Digital lock detect (input) |

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

## Deploy to board (MicroPico)

The maintainer uses the [MicroPico](https://github.com/paulober/MicroPico)
extension (v4.1+). A repo-root [`.micropico`](../.micropico) marker enables
project auto-detection.

### Preserve `import adf435x`

**Do not** set `micropico.syncFolder` to `"adf435x"`. That uploads the
*contents* of `adf435x/` to the board filesystem root (`/register_file.py`, …)
and breaks `import adf435x`.

Sync from the **repository root** and exclude non-library trees with
`pyIgnore` so `/adf435x/` lands on flash as a package directory.

Add to **local** [`.vscode/settings.json`](../.vscode/settings.json)
(`.vscode/` is gitignored — copy this block per machine):

```jsonc
{
  "micropico.syncFolder": "",
  "micropico.syncFileTypes": ["py"],
  "micropico.pyIgnore": [
    "tests", "examples", "agent", "conftest.py",
    "**/.git", "**/__pycache__", "**/.pytest_cache"
  ]
}
```

- `syncFolder: ""` — repo root; only `adf435x/**/*.py` bulk-syncs to flash.
- `pyIgnore` — excludes all of `examples/` (demos and validation scripts).

### Run examples from the host

Examples and [`validate.py`](../examples/validate.py) are **not**
bulk-synced. With `adf435x/` on flash, open a script on the host and use
**MicroPico → Run current file** (or `mpremote connect run path/to/script.py`).

Validation scripts must not `import tests.*` on the Pico.

## Bring-up checklist

1. Bulk-sync `adf435x/` per [Deploy to board (MicroPico)](#deploy-to-board-micropico).
2. Wire SPI + LE + CE + MUXOUT for your board.
3. Run [`fixed_frequency.py`](../examples/fixed_frequency.py) or
   [`validate.py`](../examples/validate.py) with default
   ``scope_200mhz`` (**Run current file**); scope RFOUTA at ~200 MHz.
4. Try other catalog slugs via ``validate.py`` (``SELECT`` or ``list``).
5. Optional GHz checks: ``golden_2112p6mhz`` (counter/spectrum).
6. Wide scope sweeps: [`frequency_sweep.py`](../examples/frequency_sweep.py).

Analog output verification (spectrum, power) remains manual.

## Validation vector bench table

Bench cases live in [`validate.py`](../examples/validate.py) ``CASES`` (10 MHz
REFIN). Other examples reference slugs in comments only.

| Slug | Output (Hz) | Profile | Bench instrument |
|------|-------------|---------|----------------|
| `scope_50mhz` | 50_000_000 | ADF4351 | Oscilloscope |
| `scope_75mhz` | 75_000_000 | ADF4351 | Oscilloscope |
| `scope_100mhz` | 100_000_000 | ADF4351 | Oscilloscope |
| `scope_150mhz` | 150_000_000 | ADF4351 | Oscilloscope |
| `scope_200mhz` | 200_000_000 | ADF4351 | Oscilloscope |
| `scope_250mhz` | 250_000_000 | ADF4351 | Oscilloscope |
| `golden_2112p6mhz` | 2_112_600_000 | ADF4351 | RF counter / spectrum |
| `cross_part_scope_137p5mhz` | 137_500_000 | both | Oscilloscope (≤150 MHz) |
| `adf4351_scope_equiv_132p0375mhz` | 132_037_500 | ADF4351 | Oscilloscope |
| `adf4351_prescaler_edge_3600mhz` | 3_600_000_000 | ADF4351 | RF counter / spectrum |
| `adf4351_prescaler_over_3700mhz` | 3_700_000_000 | ADF4351 | RF counter / spectrum |

Host-run [`validate.py`](../examples/validate.py) programs one
catalog case per run (``SELECT`` or ``sys.argv[1]``; ``list`` for names).

## Lock detect vs frequency proof

Digital lock detect (MUXOUT) confirms the PLL acquired and VCO band-select
succeeded. It does **not** prove the absolute RF output frequency. Confirm
output with a scope or counter on RFOUTA; ``validate.py`` prints target and
achieved Hz for that purpose.

## MUXOUT caveat

Do not leave MUXOUT on the N-divider during band-select (R0) writes if
reconfiguring MUXOUT for debug. Default config uses digital lock detect;
register file write ordering should preserve lock polling during normal
retunes.

## Status

See [STATUS.md](STATUS.md) for hardware bring-up completion state.
