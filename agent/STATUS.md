# Project status

Living summary of completed work and open items. Reconciled against
[`HANDOFF_synthesizer.md`](../HANDOFF_synthesizer.md) (now deprecated) and
current code as of 2026-06-28.

**Host tests:** 301 collected (`pytest --collect-only`).

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
  and skill

## Partially complete

- **Hardware bring-up** — [`test_device_hw.py`](../tests/test_device_hw.py)
  provides digital HIL tests gated by `pytest --device`. Scope/RFOUTA analog
  verification and eval-board lock confirmation remain manual/open.

## Open work

| Priority | Item | Notes |
|----------|------|-------|
| Medium | Eval board bring-up | Golden freq lock, scope RFOUTA, retune sweep on hardware |
| Low | Cheat-sheet golden vectors | Only one worked example in tests; see cheat sheet PDF |
| Low | MOD search profiling | Exhaustive search fine for single retunes; profile on target MCU if hopping latency matters |
| Low | Export sweep from `__init__.py` | Deferred until sweep API fully stable |

## HANDOFF reconciliation notes

Items that were **TODO in HANDOFF** but are **done in code**:

| HANDOFF claim | Current state |
|---------------|---------------|
| `synthesizer.py` — TODO | Implemented |
| `sweep.py` — deferred | Implemented |
| Solver not exported from `__init__.py` | Exported (`solve`, `SolveOptions`, etc.) |
| 258 host tests | 301 tests (synthesizer + sweep suites added) |

Still accurate from HANDOFF:

- Scope limited to ADF4350/ADF4351
- Golden vector in conftest
- `sweep` and `device` remain submodule imports (not package root)

## Known doc/code drift

- [`README.md`](../README.md) previously listed `uv`; aligned to conda/pip in
  agent docs (see [TESTING.md](TESTING.md))
- [`HANDOFF_synthesizer.md`](../HANDOFF_synthesizer.md) deprecated; use `agent/`

When completing a milestone, update this file and append rationale to
[JOURNAL.md](JOURNAL.md) if non-obvious.
