# Project status

Maintainer milestone tracker. Living summary of completed work and open items.

**Host tests:** refresh with `pytest -q` (see [rules.md](rules.md) testing
section for conventions). Baseline 2026-10-17 (after A6): 1154 passed,
1 xfailed (known bugs pinned in `tests/test_regressions.py`).

**Host benchmarks** (`bench/bench.py`, 2026-10-17; relative only, on-target
numbers come from bench step B7):

| Operation | CPython 3.13 | MicroPython 1.24.1 Unix |
|-----------|--------------|-------------------------|
| `solve()` arbitrary target | 8.5 us | 16.9 us |
| `FrequencyTable.from_range`, 71 points | 1.5 ms | 4.8 ms |
| `play_step()` in-band hop (no SPI) | 2.0 us | 7.9 us |
| `set_frequency()` retune (no SPI) | 28.7 us | 69.5 us |

## Completed milestones

- **Foundation stack** — `consts`, `profiles`, `config`, `register_mapper`,
  `register_file`, `device` with layered host tests
- **PLL solver** — [`solver.py`](../adf435x/solver.py): integer Hz math, MOD
  search, golden vector verified; exported from [`__init__.py`](../adf435x/__init__.py)
- **Synthesizer facade** — [`synthesizer.py`](../adf435x/synthesizer.py):
  `ADF435xSynthesizer`, plan/mark writes, lock detect, table playback
- **Sweep support** — [`sweep.py`](../adf435x/sweep.py): `FrequencyTable`
  (words from the synth's settings, one exact MOD per divider band where
  possible); playback via `ADF435xSynthesizer.play()` / `play_step()`
- **Examples** — fixed frequency, solver demo, linear sweep, octave-crossing
  sweep, frequency table builder, raw device/register demos
- **Agent documentation** — consolidated under `.agents/`; human docs in
  `docs/`; path-scoped rules in `.claude/rules/` and `.cursor/rules/`
- **Docs refactor** — content in `docs/`; README slimmed; legacy dotless docs
  tree removed
- **Bench validation example** — [`examples/validate.py`](../examples/validate.py)
  (host-run catalog cases; not part of pytest)
- **Hardware bring-up** — eval-board validation via `validate.py` catalog
  (scope/counter on RFOUTA); see [docs/hardware.md](../docs/hardware.md)
- **v0.1.0 release packaging** — `package.json` for `mip`, GitHub Release zip
  workflow, [CHANGELOG.md](../CHANGELOG.md)
- **Remediation A1: test safety net** — known bugs pinned as strict xfails,
  `FakeChip` latch model, encoder/solver oracles, CI (CPython 3.10–3.13 +
  MicroPython Unix-port smoke); releases gated on CI
- **Remediation A2: register layer** — single `config.FIELDS` table drives
  encode and validation; new datasheet rules (flags, phase < MOD, low-spur
  MOD >= 50, fast band-select divider <= 254, no N-divider on MUXOUT)
- **Remediation A3: register file** — optimistic `commit()` removed;
  `config_version` and `load_prevalidated()` for table playback
- **Remediation A4: solver** — exact rational fPFD, continued-fraction MOD
  search (~280x faster), locked MOD kept, data-sheet lock-detect settings
- **Remediation A5: sweeps** — tables encoded from the synth's settings;
  exact shared MOD per band or per-point fallback; diff-based playback on
  the synthesizer; `ADF435xSweeper` removed
- **Remediation A6: synthesizer** — reference path at construction, solve
  before CE, staged retunes while powered down, lock-detect settle time
- **Remediation A7: host performance** — allocation-free SPI word writes;
  `bench/bench.py` baselines above

## Open work

| Priority | Item | Notes |
|----------|------|-------|
| Low | Docs figure assets | Wiring diagram, probe photos, decision tree |
| High | Remediation A7–A9 | Fix the last pinned xfail (C19); perf, cleanup, docs in `tests/test_regressions.py` (sweep rewrite, solver rewrite, validation, synthesizer, docs) |
| Medium | Remediation B (bench) | Lock-detect policy, DLD settle time (`LOCK_SETTLE_MARGIN_US` is provisional), sweep/SPI checks once the testbench is back |
| Low | Cheat-sheet golden vectors | Catalog beyond datasheet golden; see [cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet) |

## Package export notes

Exported from package root: synthesizer, solver, register stack, profiles.

Submodule-only (by design): `adf435x.sweep`, `adf435x.device`.

When completing a milestone, update this file and append rationale to
[journal.md](journal.md) if non-obvious.
