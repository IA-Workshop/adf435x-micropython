# Datasheet reference (extracted facts)

> Canonical agent PLL/register reference. User-facing explanations:
> [docs/frequency-planning.md](../docs/frequency-planning.md) and
> [docs/hardware.md](../docs/hardware.md).

Primary sources (Analog Devices). Page numbers below are from ADF4351 Rev. A
(28 pp.) and ADF4350 Rev. B (34 pp.); "CS" is the ADF4350/ADF4351 common
questions cheat sheet v1.2. Local PDF copies go in `datasheets/`
(gitignored).

- [ADF4351 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)
- [ADF4350 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)
- [Cheat sheet (EngineerZone)](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet)

**Agent rule:** datasheet-sensitive edits must update this file if they change
an extracted fact, and add or update a test. Label repo policy as policy, not
as a data sheet fact.

## PLL frequency relationships

```text
fPFD = REFIN × (1 + D) / (R × (1 + T))       # D = doubler, T = divide-by-2
N = INT + FRAC/MOD
fVCO = fPFD × N                              # fundamental feedback (R4 DB23 = 1)
fOUT = fVCO / RF_divider                     # RF_divider = 2^k
VCO step = fPFD / MOD;  RF output step = fPFD / (MOD × RF_divider)
```

- VCO 2.2–4.4 GHz on both parts (Table 1, p.3; `VCO_MIN_HZ` / `VCO_MAX_HZ`).
- Output: ADF4351 34.375 MHz (÷64) – 4.4 GHz; ADF4350 137.5 MHz (÷16) –
  4.4 GHz (Table 1, p.3). R4 encodes **log2(divider)** (Fig 28, p.17).
- Feedback: always fundamental in this library.
- Worked example (p.21): 2112.6 MHz from 10 MHz REFIN, 200 kHz RF-output
  resolution, ÷2 → VCO resolution 400 kHz → MOD = 25, INT = 422, FRAC = 13.
  The resolution in MOD = fPFD / fRES is VCO-level (the p.18 R1 text calls it
  "RF output", which conflicts with the example). `SolveOptions.
  channel_step_hz` is the RF-output step: MOD = fPFD / (step × RF divider).

## Reference path and PFD

- R counter 1–1023 (10-bit; `REG2_R_COUNTER_MIN`).
- REFIN 10–250 MHz on both parts; below 10 MHz the Table 1 test condition
  requires slew rate > 21 V/µs (p.3).
- REFIN ≤ 30 MHz with the doubler (p.19, both parts; `REF_MAX_DOUBLER_HZ`).
- PFD maximum. ADF4351: 32 MHz fractional-N; 45 MHz integer-N with band
  select enabled (needs DB23 = 1, p.24); 90 MHz integer-N with band select
  disabled (phase adjust DB28 = 1, ABP 3 ns; p.3, p.11, p.24). ADF4350:
  32 MHz in all modes (p.3, p.21). The solver uses 32 MHz
  (`PFD_MAX_FRAC_HZ`) for both.

## Band select

- Clock = fPFD / band_clk_div (R4 DB19:DB12, 1–255).
- Normal mode (R3 DB23 = 0): clock ≤ 125 kHz (p.12–13, p.20); recommended
  when fPFD < 125 kHz (p.19).
- ADF4351 fast mode (DB23 = 1): clock ≤ 500 kHz and **divider ≤ 254**
  (p.19). CS: "set DB23 to 1 unless the fPFD ≤ 125 kHz". ADF4350 has no
  DB23 (reserved), so its fPFD is limited to 125 kHz × 255 = 31.875 MHz.
- Duration: 10 band-select clock cycles (p.12): 80 µs at 125 kHz, 20 µs at
  500 kHz (p.13). VTUNE is disconnected from the loop filter meanwhile.
- **The N-counter output on MUXOUT must be off** for band select to work
  (p.18; CS). `validate_config` rejects `REG2_MUX_NDIVIDER`.
- Implemented in `solver._pick_band_clk`; the fast-mode divider limit is
  also a `register_mapper` rule.

## INT, MOD, prescaler, phase

| Parameter | 4/5 prescaler | 8/9 prescaler |
|-----------|---------------|---------------|
| INT minimum (NMIN) | 23 | 75 |
| INT maximum | 65535 | 65535 |
| MOD range | 2 – 4095 | 2 – 4095 |

- Prescaler 8/9 is required above 3.6 GHz (ADF4351) / 3.0 GHz (ADF4350) at
  the prescaler input (p.18); with fundamental feedback that is the VCO (CS).
- The phase word must be **less than MOD**; use 1 when phase resync and spur
  optimization are unused (p.18, Fig 25). Enforced by a mapper rule.
- Low-spur noise mode needs **MOD ≥ 50** (ADF4351 p.23; CS). Enforced by a
  mapper rule; the synthesizer passes `mod_min=50` to the solver.
- Phase adjust (R1 DB28, ADF4351 only) disables band select and resync on R0
  writes; intended for fixed frequencies or changes under 1 MHz (p.18).
- CS: reduce FRAC/MOD where possible. **Repo policy:** among MOD values whose
  error rounds to the same hertz the smallest wins, so results are in lowest
  terms; a fixed MOD (`SolveOptions.mod`, `channel_step_hz`) is never reduced.

## Integer-N vs fractional-N settings

| Setting | Fractional-N | Integer-N | Source |
|---------|--------------|-----------|--------|
| LDF (R2 DB8) | 0: 40 PFD cycles | 1: 5 cycles | p.19; integer-N needs FRAC = 0 and LDF = 1 (p.11) |
| LDP (R2 DB7) | 0: 10 ns window | 1: 6 ns window | p.19 recommends DB8:DB7 = 00 / 11 |
| ABP (R3 DB22, ADF4351) | 0: 6 ns | 1: 3 ns | p.19 (3 ns "not recommended" for frac-N) |
| Charge cancel (R3 DB21, ADF4351) | 0 | 1 | p.20 |

- LDP is a **comparison window**, not a pulse width: lock detect goes high
  after n consecutive PFD cycles inside the window, n from LDF. A 6 ns window
  with the 40-cycle count may never assert in fractional-N.
- ADF4350: R3 DB31:DB19 are reserved (0); ABP is fixed, "typically 3 ns"
  (p.11). Its p.19 integer-N LDP prose contradicts its Fig 26 (likely a
  typo); the Fig 26 encodings match the ADF4351.
- Implemented in `solver.pll_mode_fields`. Frequency tables keep
  fractional-N settings for a whole locked-MOD band that has any fractional
  channel (valid at FRAC = 0), so integer channels do not rewrite R2/R3.

## Double-buffer latching (p.12, Figure 23 p.14)

- **DBR, wait for the next R0 write:** R1 phase (DB26:15) and MOD (DB14:3);
  R2 doubler (DB25), divide-by-2 (DB24), R counter (DB23:14), CP current
  (DB12:9).
- **Immediate:** everything else, including the R1 prescaler and phase
  adjust, and R2 noise mode, MUXOUT, DB13, LDF, LDP, PD polarity,
  power-down, CP three-state, counter reset.
- **DBB:** R4 RF divider (DB22:20) waits for R0 only while R2 DB13 is set.
- The register file adds an R0 write whenever R1 or R2 changes (always
  safe), and for R4 when DB13 is set in the encoded R2 word. `FakeChip`
  (`tests/conftest.py`) models exactly this list.

## SPI programming

- Data is clocked on the CLK rising edge, MSB first; the interface example
  uses an SPI master with CPHA = 0, i.e. mode 0 (p.26). Maximum SPI clock
  20 MHz (CS; t4 = t5 = 25 ns minimum, Table 2 p.5).
- LE latches on its rising edge: t1 LE setup 20 ns, t7 LE pulse 20 ns, t6
  CLK-to-LE 10 ns, t2/t3 data setup/hold 10 ns (Table 2, p.5; ADF4350 p.4).
  If more than 32 bits are shifted, the last 32 latch (CS).
- Power-up: R5, R4, R3, R2, R1, R0 after the supplies are up (p.20; ADF4350
  p.21). No delay between writes or after CE is specified, and no double
  write. With AVDD at 0 V the SPI pins must be at 0 V (CS).
- Retune: [R4], [R1], R0, with R4 only if the divider changed and R1 only if
  MOD changed (CS). The diff-based plan produces this.
- CE low powers down and three-states the charge pump (p.7). CE low and
  software power-down both **retain register contents** (CS). Writes while
  CE is low are not documented, so the synthesizer stages them instead.
- Lock detect right after an R0 write is **not documented** (it may read
  stale-high). The synthesizer waits band select + the LDF cycle count +
  `LOCK_SETTLE_MARGIN_US` before polling; the margin is provisional until
  bench step B3.

## R5

- DB20:DB19 = 11 (reserved ones), DB21 = 0, other reserved bits 0 (Fig 29,
  p.17). LD pin DB23:22: 00 low, 01 digital lock detect, 10 low, 11 high.
- CS anomaly: its phase-adjust box says "if FRAC = 0, R5 DB[18:15] must be
  0b0100". That conflicts with Fig 29 and appears in neither data sheet; the
  library does not adopt it.

## ADF4350 vs ADF4351

| Feature | ADF4350 | ADF4351 |
|---------|---------|---------|
| RF divider max | 16 | 64 |
| Phase adjust (R1 DB28) | reserved | yes |
| Fast band select (R3 DB23) | reserved | yes |
| ABP (R3 DB22) | fixed ~3 ns, reserved | 6 / 3 ns |
| Charge cancel (R3 DB21) | reserved | yes |
| 4/5 prescaler max | 3.0 GHz | 3.6 GHz |
| PFD max | 32 MHz | 32 / 45 / 90 MHz (see above) |

- ADF4350 cold drift: below 0 °C with a fundamental VCO under 2.95 GHz, R0
  must be reprogrammed (p.13). The library does not handle this.
- Capability flags live in `profiles.py`. Checks run in
  `register_mapper.validate_config` (from the capability column of
  `config.FIELDS`); encode never checks.

## Golden vector

Defined in [`tests/conftest.py`](../tests/conftest.py):

- Target 2112.6 MHz, ADF4351, 10 MHz reference, RF divide-by-2.
- Fields: INT = 422, FRAC = 13, MOD = 25, prescaler 8/9. Fast band select
  with `band_clk_div = 20` (10 MHz / 20 = 500 kHz) is a repo choice that
  follows p.19; it is not part of the data sheet example.
- `WORKED_WORDS[0]` … `WORKED_WORDS[5]` are registers R0 … R5. SPI order is
  R5→R0, so use `reversed(WORKED_WORDS)` for a full sequence.
- **Do not duplicate hex values in other docs** (checked by
  `tests/test_docs.py`).

Field names map to registers via `FIELD_REGISTER` (derived from `FIELDS`) in
[`config.py`](../adf435x/config.py).

## Figure map

| Topic | Data sheet (both parts) | Code |
|-------|-------------------------|------|
| Register map, DBR/DBB marks | Fig 23, p.14 | `config.FIELDS`, `register_file._commit_stale_set` |
| R0, R1 | Figs 24–25, p.15 | `config.FIELDS` |
| R2, R3 | Figs 26–27, p.16 | `config.FIELDS` |
| R4, R5 | Figs 28–29, p.17 | `config.FIELDS` |
| Phase word default (1) | Fig 25 | `config.FIELDS` (`phase`) |
| Phase resync (clock divider mode 10) | Fig 27, p.24 | `clockdiv_mode` (not used by the solver) |
| Serial interface timing | Table 2 | [`device.py`](../adf435x/device.py) |

## Open questions for the bench

- How quickly digital lock detect reflects a retune (step B3).
- Whether registers accept writes while CE is low (step B8).
- Whether a 6 ns LDP window ever asserts in fractional-N (step B2).

## Optional future test vectors

Additional worked examples from the cheat sheet are not yet in the test
suite. See [status.md](status.md) for tracking.
