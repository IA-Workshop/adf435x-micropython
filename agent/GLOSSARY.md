# Glossary and naming conventions

Consult this file before introducing new types, fields, or abbreviations.

## Device and RF terms

| Term | Meaning | Code / config name | Notes |
|------|---------|-------------------|-------|
| PLL | Phase-locked loop | — | |
| VCO | Voltage-controlled oscillator (2.2–4.4 GHz) | `vco_hz` in `SolveResult` | |
| PFD | Phase-frequency detector input | `f_pfd_hz` | Max 32 MHz for frac-N |
| REFIN | Reference clock input | `ref_hz` | Synth/solver argument |
| RFOUT | RF output port | — | Examples use RFOUTA |
| INT | Integer part of N divider | `int_n` | Config field |
| FRAC | Fractional numerator | `frac` | Config field |
| MOD | Fractional modulus | `mod` | Channel step ≈ fPFD/MOD |
| N | Feedback divider: INT + FRAC/MOD | — | fVCO = fPFD × N |
| prescaler | Dual-modulus 4/5 or 8/9 | `prescaler` | Selected from VCO freq |
| RF divider | Output divide-by (power of 2) | `rf_divider` | R4 encodes log2(divider) |
| frac-N / int-N | Fractional vs integer-N mode | `frac == 0` | int-N sets LDF/ABP extras |
| band-select | VCO sub-band calibration clock | `band_clk_div`, `band_clk_mode` | |

## Register and SPI terms

| Term | Meaning | Code / config name | Notes |
|------|---------|-------------------|-------|
| DBR | Double-buffered register | `DBR_REGISTER_INDICES` | R1, R2 latch on R0 write |
| DBB | R4 RF divider double-buffer | `double_buffer` | Active when R2 DB13 set |
| LE | Latch enable (GPIO) | `device.py` | Rising edge latches word |
| CE | Chip enable | `chip_enable` / `chip_disable` | |
| MUXOUT | Multiplexed status pin | `read_muxout`, `REG2_MUX_*` | Digital lock default |
| CP | Charge pump | `cp_current` | Must match loop filter |
| LDF | Lock-detect precision | `ldf` | FRAC_N vs INT_N |
| LDP | Lock-detect pulse width | `ldp` | 10 ns or 6 ns |
| ABP | Antibacklash pulse | `abp` | 6 ns frac-N, 3 ns int-N |
| MTLD | Mute till lock detect | `mtld` | |
| CSR | Cycle-slip reduction | `csr` | |

## Library terms

| Term | Meaning | Type / module |
|------|---------|---------------|
| regfile | Register file state manager | `ADF435xRegisterFile` |
| device | SPI/GPIO transport (board-specific wiring) | `ADF435xDevice` or duck-typed |
| mapper | Field encoder/validator | `ADF435xRegisterMapper` |
| profile | Part capability descriptor | `ADF4350`, `ADF4351` |
| golden vector | Datasheet worked example | `WORKED_FIELDS`, `WORKED_WORDS` |
| plan/mark | Split commit from cache update | `commit_plan` + `mark_written` |
| fast-hop | Sweep mode with DBB + short LDP | `_enable_fast_hop_mode` |

## Naming conventions

### Classes

`ADF435x` prefix + PascalCase role noun: `ADF435xSynthesizer`, `FrequencyTable`,
`SolveResult`.

Do not use: `SynthPolicy`, `DeviceLimits`, or generic `Manager` suffixes.

### Config fields

snake_case, match datasheet concept: `int_n`, `frac`, `mod`, `rf_divider`,
`double_buffer`.

Do not alias: `n`, `N`, `integer`.

### Constants

`REG{n}_{FIELD}_{SUFFIX}`: `REG0_INT_POS`, `REG2_MUX_DIGITALLOCK`.

Suffixes: `_POS`, `_WIDTH`, `_MIN`, `_VALUES`.

### Private helpers

Leading underscore, verb-first: `_pick_rf_divider`, `_write_prebuilt_plan`,
`_normalize_frac_mod`.

### Write-path verbs

Use explicit names, not vague `_program`:

- `_write_stale_registers` — diff-based commit from regfile
- `_write_prebuilt_plan` — play a pre-encoded word list (sweep)

### Tests

`Test{FeatureArea}` classes. Shared fixtures in [`tests/conftest.py`](../tests/conftest.py)
(`FakeDevice`); do not duplicate per test file.

### Errors

`{Condition}Error`: `FrequencyOutOfRangeError`, `DividerOctaveCrossingError`.

## Do not introduce

- Parallel option-bag types duplicating `SolveOptions`
- Separate dirty flags on the register file
- Limits classes duplicating [`profiles.py`](../adf435x/profiles.py)
- CPython-only stdlib in [`adf435x/`](../adf435x/)
- Duplicate `FakeDevice` fixtures outside conftest
