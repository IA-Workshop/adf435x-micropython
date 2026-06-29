# Datasheet reference (extracted facts)

Critical PLL and register facts for agent work. Source documents:

- [`datasheets/adf4351.pdf`](../datasheets/adf4351.pdf)
- [`datasheets/ADF4350.pdf`](../datasheets/ADF4350.pdf)
- [`datasheets/ADF4350_ADF4351_Cheat_Sheet_v1_2.pdf`](../datasheets/ADF4350_ADF4351_Cheat_Sheet_v1_2.pdf)

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

- R counter minimum: **1** (`REG2_R_COUNTER_MIN`)
- Eval-board default: R=1, doubler off, div-by-2 off → fPFD = REFIN
- PFD maximum (fractional-N): **32 MHz** (`PFD_MAX_FRAC_HZ`)
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
- **Spur guidance (cheat sheet):** prefer **smaller MOD** when frequency error
  ties — solver MOD search scores `(abs(error_hz), mod)`
- Gcd-reduce (FRAC, MOD) when FRAC > 0; skip for integer-N (keep MOD ≥ mod_min)

## Integer-N vs fractional-N settings

When FRAC = 0, the solver sets (ADF4351):

| Setting | frac-N default | int-N value | Rationale |
|---------|----------------|-------------|-----------|
| LDF | FRAC_N | INT_N | Lock-detect mode |
| ABP | 6 ns | 3 ns | Antibacklash pulse |
| charge_cancel | off | on (4351) | CP spur cancellation |

Fast-hop / sweep mode ([`synthesizer.py`](../adf435x/synthesizer.py)):
`double_buffer=True`, `ldp=6ns` for rapid R0-only hops.

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
- Register words: reference `WORKED_WORDS` by name — **do not duplicate hex
  values in other docs**

## Figure map (code cross-reference)

| Topic | Datasheet | Code |
|-------|-----------|------|
| Double-buffer latching | Figure 23 p.14 | [`register_file.py`](../adf435x/register_file.py) |
| Register 0 | Figure 24 | `register_mapper.register_0` |
| Register 1 | Figure 25 | `register_mapper.register_1` |
| Register 2 | Figure 26 | `register_mapper.register_2` |
| Register 3 | Figure 27 | `register_mapper.register_3` |
| Register 4 | Figure 28 | `register_mapper.register_4` |
| Register 5 | Figure 29 | `register_mapper.register_5` |
| Phase resync default | Figure 25 | [`config.py`](../adf435x/config.py) defaults |
| Serial interface | Timing section | [`device.py`](../adf435x/device.py) |

Bit positions and widths begin at Figure 23 in both ADF4350 and ADF4351
datasheets (see module docstring in [`register_mapper.py`](../adf435x/register_mapper.py)).

## Optional future test vectors

Additional worked examples from the cheat sheet are not yet in the test suite.
See [STATUS.md](STATUS.md) for tracking.
