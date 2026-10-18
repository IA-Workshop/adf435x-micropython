# Changelog

All notable user-facing changes are documented here. Terms such as MOD and
fPFD are explained in the [glossary](docs/glossary.md) and on the
[symbols](docs/symbols.md) page.

## Unreleased

### Changed (breaking)

- Renamed for brevity (old name, then new): `ADF435xDeviceProfile` to
  `ADF435xProfile`; `DividerOctaveCrossingError` to `DividerCrossingError`;
  `max_hz_for_rf_divider()` to `divider_max_hz()`;
  `SolveResult.f_pfd_hz` to `pfd_hz`;
  `ADF435xRegisterFile.commit_all_plan()` to `full_plan()`; and the
  `ADF435xDevice` arguments and attributes `load_enable_pin` and
  `chip_enable_pin` to `le_pin` and `ce_pin`.
- Register fields are described once in `adf435x.config.FIELDS`. Removed:
  `ADF435xRegisterMapper.register_0` to `register_5` (use
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
  no longer spill into a neighboring bit.
- `ADF435xRegisterFile`: removed `commit()`, `commit_all()` and the
  `invalidate` alias. Use `commit_plan()` / `full_plan()`, write the
  words, then `mark_written()` or `mark_write_failed()`.
- Solver: `achieved_hz` and `vco_hz` are rounded to the nearest hertz (were
  floored) and `error_hz` is `target_hz - achieved_hz`.
- Solver: `SolveOptions.channel_spacing_hz` is replaced by `channel_step_hz`,
  the step at the RF output (MOD = fPFD / (step × RF divider), which must
  be a whole number).
- Solver: an explicit MOD (`SolveOptions.mod`) is used as given, no longer
  reduced by a common factor.
- Solver: among MOD values whose error rounds to the same hertz, the smallest
  wins (fewer spurs); the choice can differ from v0.1.0 by under a hertz.
- Solver: sets the lock-detect window (`ldp`) as the data sheet recommends,
  10 ns for fractional-N and 6 ns for integer-N.
- Solver: non-integer frequencies raise `TypeError`; `ref_hz <= 0`, an
  out-of-range MOD, and an illegal `rf_divider` raise `ValueError` up front.

- Sweeps: `ADF435xSweeper` is removed. Build a `FrequencyTable`, then call
  `synth.play(table, ...)` or `synth.play_step(table, index)`.
  `FrequencyEntry.plan` is replaced by `words` (all six registers); playback
  writes only what differs from the last write. `build_frequency_table()`
  and its helpers are removed from `adf435x.solver`, and
  `DividerCrossingError` moved to `adf435x.sweep` (still exported from
  the package root).
- Tables: `from_range` targets exactly `lower_hz, lower_hz + step_hz, ...`
  plus `upper_hz`; each RF-divider band shares one MOD that hits every point
  exactly when one fits (<= 4095), else each point gets its own best MOD.

- Synthesizer: `power_up()` needs `frequency_hz` unless a frequency was
  already set, and solves before raising CE. `set_frequency()` while powered
  down stores the settings without SPI writes; `power_up()` writes them.
- Synthesizer: `is_locked()` raises `RuntimeError` when MUXOUT is not routed
  to digital lock detect, and `wait_locked()` first waits out VCO band
  select plus the lock-detect count after a write (`lock_settle_us()`).

### Added

- `ADF435xRegisterFile.config_version` (counts successful `configure()`
  calls) and `load_words(fields, words)` for precomputed state.
- `SolveResult.exact`: true only when the output is exactly the target;
  `SolveOptions(exact=True)` uses it.
- `SolveOptions.mod_min` and `SolveOptions.copy(**overrides)` (replaces
  `with_locked_pll`, which is removed).
- `ADF435xSynthesizer.solve()`, `play()`, `play_step()`, `solve_options`,
  `mod_min`, `has_lock_detect`, and `LockTimeoutError`
  (`play(..., require_lock=True)`); `play()` returns the number of lock
  timeouts.
- `ADF435xSynthesizer.lock_settle_us()`, `synthesizer.LOCK_SETTLE_MARGIN_US`
  (provisional), and `solver.reference_fields()`.
- `FrequencyTable.max_error_hz`, the `max_error_hz=` limit when building,
  and `FrequencyEntry.target_hz`, `exact`, `rf_divider`. `FrequencyTable` is
  exported from the package root.
- `FrequencyOutOfRangeError`, `NoSolutionError` and `ExactFrequencyError`
  are exported from the package root.
- The release workflow fails unless the tag matches the version in both
  `pyproject.toml` and `package.json`. The in-development version is
  `0.2.0.dev0`.

### Documentation

- New user guides in `docs/`: quickstart, hardware, API guide, frequency
  planning, sweeps, troubleshooting, development, examples, a glossary of
  terms and a page of symbols; new `CONTRIBUTING.md`. The README has a
  quickstart again, and its links work.

### Fixed

- Solver: fPFD is kept as an exact fraction, so a non-integer fPFD (for
  example 25 MHz / R=3) no longer reports phantom errors, and `exact=True`
  no longer accepts outputs that are off by a fraction of a hertz.
- ADF4351: PFD frequencies between 31.875 and 32 MHz are accepted (fast
  band-select mode).
- Low-spur noise mode: the synthesizer asks the solver for MOD >= 50.
- Sweeps keep the synthesizer's settings (output power, charge-pump
  current, aux output, ...) instead of writing defaults, and the register
  cache always matches the chip, including after `set_frequency()` between
  steps.
- `from_range` returns every requested point instead of a coarser grid, and
  never ends short of or beyond `upper_hz`; `from_frequencies` no longer
  loses accuracy to a MOD locked from the first entry.
- Divider-crossing sweeps run on boards without MUXOUT (boundary hops dwell
  instead of waiting for lock), and the crossing error suggests ranges that
  stay on one divider.
- Table hops no longer force a 6 ns lock-detect window in fractional-N.
- The synthesizer applies its reference path (R counter, doubler, divide-by-2)
  and band-select clock at construction, so no write can carry placeholder
  values (R=1, a band-select clock far above 500 kHz).
- An invalid `power_up()` frequency leaves CE low.
- `examples/registers.py` expected 131.9125 MHz; the output is 132.0375 MHz.
  All examples pass SPI pins as `machine.Pin` objects.

### Performance

- The MOD search is about 280x faster: 16 us per solve on the MicroPython
  Unix port, was 4.6 ms.
- `ADF435xDevice.write_register()` reuses one 4-byte buffer instead of
  allocating per word.
- Table building no longer enumerates every grid point (a full-octave table
  at MOD 4095 needed ~5.6 MB on MicroPython), and playback no longer
  validates and re-encodes on every hop.

## 0.1.0

First release.

- ADF4350/ADF4351 PLL driver: solver, synthesizer, register stack, sweep
- Host-testable on CPython 3.10+ (`pip install -e ".[test]"` then `pytest`)
- Deploy: GitHub Release zip (`adf435x/`) or
  `mip.install("github:IA-Workshop/adf435x-micropython", version="v0.1.0")`
- Bench validation catalog in [`examples/validate.py`](examples/validate.py)
