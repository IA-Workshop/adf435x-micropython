# Changelog

All notable user-facing changes are documented here.

## Unreleased

### Changed (breaking)

- Register fields are described once in `adf435x.config.FIELDS`. Removed:
  `ADF435xRegisterMapper.register_0` … `register_5` (use
  `encode_register(index, config)`), `config.FIELD_WIDTH`,
  `config.FIELD_RANGE_MIN`, `config.FIELD_ENUM_VALUES`, the `consts.*_VALUES`
  tuples, and `consts.DISABLED`, `ENABLED`, `WORD_SIZE_BYTES`, `CONTROL_POS`,
  `CONTROL_WIDTH`.
- `validate_config()` / `configure()` now reject, with `ValueError`:
  on/off fields set to anything other than `True`/`False`/`1`/`0`;
  non-integer values; a phase word not below MOD; low-spur noise mode with
  MOD below 50; a band select clock divider above 254 in fast mode; and
  MUXOUT set to the N-divider output (it stops VCO band select).
- The encoder no longer raises for capability errors (validation already
  rejects them) and masks every field to its width, so a bad flag value can
  no longer spill into a neighbouring bit.

### Known issue

- In low-spur noise mode, `set_frequency()` raises when the solver picks a
  MOD below 50. The solver fix is pending.

## 0.1.0

First release.

- ADF4350/ADF4351 PLL driver: solver, synthesizer, register stack, sweep
- Host-testable on CPython 3.10+ (`pip install -e ".[test]"` then `pytest`)
- Deploy: GitHub Release zip (`adf435x/`) or
  `mip.install("github:IA-Workshop/adf435x-micropython", version="v0.1.0")`
- Bench validation catalog in [`examples/validate.py`](examples/validate.py)
