# Engineering guidelines

Don't→Do corrections, expanded invariant rationale, and the naming catalog. The
canonical numbered invariant list lives in `AGENTS.md`; this file is the
actionable and reference form.

## Don't → Do

| Don't | Do instead |
|-------|------------|
| Re-validate ranges in `encode_register()` | `validate_config()` at `configure()`; encode masks widths only |
| Add per-register encode code, defaults, or value sets | Add one row to `config.FIELDS`; cross-field checks go in `register_mapper._RULES` |
| Return `(index, word)` or reorder writes in `device` | `commit_plan()` → bare 32-bit words, **R5→R0** |
| Track DBB with a flag separate from encoded R2 | Read `double_buffer` from encoded R2; DBR/DBB logic in `register_file` only |
| Mark registers written before the device write succeeds | `commit_plan()` → device write → `mark_written()` or `mark_write_failed()` (no optimistic `commit()`; removed in A3) |
| Use float Hz or emit register words from `solve()` | Integer Hz; `solve()` → `configure(**result.fields)` |
| `import machine` at package root | `adf435x.device` submodule only |
| Hard-code board pins in `adf435x/` | Pass SPI/GPIO from caller or examples |
| Add `SynthPolicy`, `DeviceLimits`, or a second options bag | `SolveOptions` + `ADF435xDeviceProfile` bounds |
| Precompute delta write plans for a sweep | Store all six words per entry; `play_step()` diffs against `last_written` |
| Write SPI while CE is low | Stage in the register file; `power_up()` writes |
| Round fPFD or use float math in the solver | Integer fractions (`pfd_num / pfd_den`); `exact` only when the residual is zero |

## Invariant notes (beyond the one-liners in AGENTS.md)

- **Validate-at-setup, trust-at-encode** — the mapper validates at `configure`;
  encoding assumes valid input and masks field widths only. No defensive
  re-checks downstream.
- **Plan/mark split** — the register file is pure: it emits a plan and never
  performs I/O. The synthesizer owns the device write and the post-I/O state
  transition (`mark_written` / `mark_write_failed`).
- **Freshness signals** — `commit_count` (monotonic, on the register file) marks
  write freshness and `config_version` counts successful `configure()` calls
  (frequency tables re-encode when it changes); wall-clock `_last_write_us`
  belongs on the synthesizer to keep the register file portable and clock-free.
- **Solver bounds** — come from `ADF435xDeviceProfile` plus module constants. Do
  not reintroduce a `DeviceLimits` / `limits_for_profile` layer.

## Naming

Consult before introducing new types, fields, or abbreviations.

### Classes
`ADF435x` prefix + PascalCase: `ADF435xSynthesizer`, `FrequencyTable`,
`SolveResult`. No `SynthPolicy`, `DeviceLimits`, or `Manager` suffixes.

### Config fields
snake_case: `int_n`, `frac`, `mod`, `rf_divider`, `double_buffer`. Do not alias
`n`, `N`, `integer`.

### Constants
`REG{n}_{FIELD}_{SUFFIX}` with `_POS`, `_WIDTH`, `_MIN`. Legal-value sets,
defaults and labels live in the `config.FIELDS` table, not in `consts`.

`consts` wraps values in `micropython.const()` (an identity stand-in on
CPython). Other modules read them as attributes (`consts.X`), so MicroPython
does not fold them across modules; do not rely on cross-module folding for
speed.

### Golden vector indexing
- `WORKED_WORDS[i]` is register **Ri**.
- SPI / `commit_plan()` order is **R5→R0** — reverse when comparing to
  `WORKED_WORDS`.

### Errors
`{Condition}Error`: `FrequencyOutOfRangeError`, `DividerOctaveCrossingError`.

## Do not introduce

- Parallel option-bag types duplicating `SolveOptions`
- Separate dirty flags on the register file
- Limits classes duplicating `profiles.py`
- CPython-only stdlib in `adf435x/`
- Duplicate `FakeDevice` outside `tests/conftest.py`

When a name or invariant changes, update this file and `AGENTS.md`'s invariant
list together.
