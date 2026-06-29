# Project status

Living summary of completed work and open items.

**Host tests:** refresh with `pytest -q` (see [TESTING.md](TESTING.md) for counts).

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
- **Bench validation example** — [`examples/validate.py`](../examples/validate.py)
  (host-run catalog cases; not part of pytest)

## Partially complete

- **Hardware bring-up** — host-run [`validate.py`](../examples/validate.py)
  (scope-tier + PLL edge catalog cases); manual RFOUTA verification per
  [HARDWARE.md](HARDWARE.md) bench table.

## Open work

| Priority | Item | Notes |
|----------|------|-------|
| Medium | Eval board bring-up | Host-run validate.py; scope RFOUT per bench table |
| Low | Cheat-sheet golden vectors | Catalog beyond datasheet golden; see [cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet) |
| Low | MOD search profiling | Exhaustive search fine for single retunes; profile on target MCU if hopping latency matters |
| Low | Export sweep from `__init__.py` | Deferred until sweep API fully stable |
| Low | Remove `HANDOFF_synthesizer.md` stub | Content migrated to `agent/` |

## Package export notes

Exported from package root: synthesizer, solver, register stack, profiles.

Submodule-only (by design): `adf435x.sweep`, `adf435x.device`.

When completing a milestone, update this file and append rationale to
[JOURNAL.md](JOURNAL.md) if non-obvious.
