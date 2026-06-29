# Project status

Living summary of completed work and open items.

**Host tests:** 301 collected; 299 pass, 2 skipped without `--device`.

## Completed milestones

- **Foundation stack** — `consts`, `profiles`, `config`, `register_mapper`,
  `register_file`, `device` with layered host tests
- **PLL solver** — [`solver.py`](../adf435x/solver.py): integer Hz math, MOD
  search, golden vector verified; exported from [`__init__.py`](../adf435x/__init__.py)
- **Synthesizer facade** — [`synthesizer.py`](../adf435x/synthesizer.py):
  `ADF435xSynthesizer`, plan/mark writes, lock detect, fast-hop mode helper
- **Sweep support** — [`sweep.py`](../adf435x/sweep.py): `FrequencyTable`,
  `ADF435xSweeper`, divider-boundary handling, MOD lock per band
- **Examples** — fixed frequency, solver demo, linear sweep, octave-crossing
  sweep, frequency table builder, raw device/register demos
- **Agent documentation** — `agent/` directory, `AGENTS.md`, `.cursor/` rules
  and skill; board-agnostic portability documented

## Partially complete

- **Hardware bring-up** — [`test_device_hw.py`](../tests/test_device_hw.py)
  provides digital HIL tests gated by `pytest --device` on the reference pin
  map. Scope/RFOUTA analog verification remains manual.

## Open work

| Priority | Item | Notes |
|----------|------|-------|
| Medium | Eval board bring-up | Golden freq lock, scope RFOUTA, retune sweep on hardware |
| Low | Cheat-sheet golden vectors | Only one worked example in tests; see [cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet) |
| Low | MOD search profiling | Exhaustive search fine for single retunes; profile on target MCU if hopping latency matters |
| Low | Export sweep from `__init__.py` | Deferred until sweep API fully stable |
| Low | Remove `HANDOFF_synthesizer.md` stub | Content migrated to `agent/` |

## Package export notes

Exported from package root: synthesizer, solver, register stack, profiles.

Submodule-only (by design): `adf435x.sweep`, `adf435x.device`.

When completing a milestone, update this file and append rationale to
[JOURNAL.md](JOURNAL.md) if non-obvious.
