# Datasheet reference (extracted facts)

> Canonical agent PLL/register reference. User-facing explanations:
> [docs/reference/pll-primer.md](../docs/reference/pll-primer.md).

Critical PLL and register facts for agent work. Primary sources (Analog Devices):

- [ADF4351 product page](https://www.analog.com/en/products/adf4351.html) —
  [data sheet PDF](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)
- [ADF4350 product page](https://www.analog.com/en/products/adf4350.html) —
  [data sheet PDF](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)
- [ADF4350/ADF4351 common questions cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet)
  (EngineerZone; spur/MOD guidance)

Extracted facts below are maintained in-repo so agents need not rely on local
PDF copies.

**Agent rule:** datasheet-sensitive edits must update this file if they change
an extracted fact, and add or update a test.

## PLL frequency relationships

```text
fPFD = REFIN × (1 + doubler) / (R × rdiv2_factor)   # rdiv2_factor = 2 if div-by-2
N = INT + FRAC/MOD
fVCO = fPFD × N
fOUT = fVCO / RF_divider                         # RF_divider is power of 2
channel_step ≈ fPFD / MOD
```

- VCO operating band: **2.2 GHz – 4.4 GHz** (`VCO_MIN_HZ` / `VCO_MAX_HZ` in
  [`solver.py`](../adf435x/solver.py))
- RF divider: powers of 2; R4 encodes **log2(divider)**, not the divider value
- Feedback: always fundamental (`REG4_FEEDBACK_FUNDAMENTAL`) in this library

## Reference path and PFD

- R counter minimum: **1** (`REG2_R_COUNTER_MIN`); maximum **1023** (10-bit field)
- Eval-board default: R=1, doubler off, div-by-2 off → fPFD = REFIN
- **REFIN rated range (Table 1):** **10 MHz – 250 MHz** on both ADF4350 and ADF4351
- Below 10 MHz REFIN: permitted with **slew rate > 21 V/µs** (footnote, not a
  separate rated band)
- **REFIN maximum with doubler enabled:** **30 MHz** (`REF_MAX_DOUBLER_HZ`)
- PFD maximum (fractional-N): **32 MHz** (`PFD_MAX_FRAC_HZ`)
- ADF4351 integer-N PFD maxima (45 / 90 MHz) are out of scope for the frac-N
  solver path
- Band-select clock: ≤ **125 kHz** normal; ADF4351 fast mode ≤ **500 kHz**
  when fPFD > 125 kHz

Implemented in `_pick_band_clk` in [`solver.py`](../adf435x/solver.py).

## INT, MOD, and prescaler limits

| Parameter | 4/5 prescaler | 8/9 prescaler |
|-----------|---------------|---------------|
| INT minimum (NMIN) | 23 | 75 |
| INT maximum | 65535 | 65535 |
| MOD range | 2 – 4095 | 2 – 4095 |

- Prescaler 4/5 below profile threshold (3.0 GHz ADF4350 / 3.6 GHz ADF4351),
  else 8/9
- **Spur guidance (cheat sheet):** reduce FRAC/MOD where possible — the solver
  prefers the **smallest MOD** among candidates whose error rounds to the same
  whole hertz (repo policy), so results are already in lowest terms
- A fixed MOD (`SolveOptions.mod`, or `channel_step_hz` = RF-output step, giving
  MOD = fPFD / (step × RF divider); data sheet p.21 example) is never reduced
- Low-spur noise mode needs **MOD ≥ 50** (p.23); the synthesizer passes
  `mod_min=50` to the solver in that mode

## Integer-N vs fractional-N settings

The solver sets these from FRAC (data sheet p.19–20):

| Setting | frac-N (FRAC > 0) | int-N (FRAC = 0) | Notes |
|---------|-------------------|------------------|-------|
| LDF | FRAC_N (40 cycles) | INT_N (5 cycles) | Lock-detect cycle count |
| LDP | 10 ns | 6 ns | Lock-detect comparison window; p.19 recommends DB8:DB7 = 00 / 11 |
| ABP | 6 ns (4351) / fixed 3 ns (4350) | 3 ns | ADF4350 ABP not programmable |
| charge_cancel | off | on | ADF4351 only |

Frequency tables ([`sweep.py`](../adf435x/sweep.py)) add only
`double_buffer=True` (R4 divider latches with the R0 write). Lock-detect
settings follow the table's PLL mode: a locked-MOD band with any fractional
channel keeps fractional-N settings for all its entries (valid at FRAC = 0
too), so integer channels do not rewrite R2/R3 mid-sweep.

## Double-buffer latching (Figure 23, p. 14)

- **DBR:** R1 and R2 changes require a trailing **R0 write** to take effect
- **DBB:** R4 RF divider latches on R0 only when R2 bit 13 (`double_buffer`)
  is set
- DBB state is read from the **encoded R2 word**, not a separate flag
- Enforced in `register_file._commit_stale_set`; tested in
  [`test_register_file.py`](../tests/test_register_file.py)

## SPI programming order

- Write order: **R5 → R0** (register address in DB2:DB0 of each 32-bit word)
- LE: low during shift, rising edge latches, return low
- First power-up: full six-register write; retunes: minimal stale set only

See [`device.py`](../adf435x/device.py) and
[`register_file.py`](../adf435x/register_file.py).

## ADF4350 vs ADF4351 feature matrix

| Feature | ADF4350 | ADF4351 |
|---------|---------|---------|
| RF divider max | 16 | 64 |
| Phase adjust (R1) | no | yes |
| Fast band-select (R3) | no | yes |
| Programmable ABP (R3) | fixed 3 ns | 6/3 ns |
| Charge cancel (R3) | no | yes |
| prescaler 4/5 max VCO | 3.0 GHz | 3.6 GHz |

Profile gates in `register_mapper.validate_config`; do not bypass in encode.

## Golden vector

Defined in [`tests/conftest.py`](../tests/conftest.py):

- Target: 2112.6 MHz, ADF4351, 10 MHz ref, RF divide-by-2
- Fields: INT=422, FRAC=13, MOD=25, prescaler 8/9, fast band-select,
  `band_clk_div=20`
- Words: `WORKED_WORDS[0]` … `WORKED_WORDS[5]` are registers R0 … R5
- SPI / `commit_plan()` order is R5→R0 — use `reversed(WORKED_WORDS)` for a
  full six-register sequence
- **Do not duplicate hex values in other docs** — reference `WORKED_WORDS` by name

Config field names map to registers via `FIELD_REGISTER` (derived from
`FIELDS`) in [`config.py`](../adf435x/config.py).

## Figure map (code cross-reference)

| Topic | Datasheet | Code |
|-------|-----------|------|
| Double-buffer latching | Figure 23 p.14 | [`register_file.py`](../adf435x/register_file.py) |
| Registers 0–5 (bit layout) | Figures 24–29 | `config.FIELDS` (one row per field, grouped by register) |
| Encode / validate | Figures 24–29 | `register_mapper.encode_register`, `validate_config` |
| Phase resync default | Figure 25 | [`config.py`](../adf435x/config.py) defaults |
| Serial interface | Timing section | [`device.py`](../adf435x/device.py) |

Bit positions and widths begin at Figure 23 in both ADF4350 and ADF4351
datasheets (see module docstring in [`register_mapper.py`](../adf435x/register_mapper.py)).

## Optional future test vectors

Additional worked examples from the
[cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet)
are not yet in the test suite. See [status.md](status.md) for tracking.
