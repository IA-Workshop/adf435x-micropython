# Project context

Scope, task routing, and definition of done. Always-loaded essentials (source of
truth, invariants, gotchas) live in `AGENTS.md`; this file is the on-demand depth
for planning a change.

## Scope

- ADF4350/ADF4351 only — not the 4355/4356 family.
- MicroPython on any board with SPI + GPIO. Pin numbers live in callers,
  examples, and tests — never in `adf435x/` library modules.
- Host suite: CPython ≥ 3.10 with a fake `machine` (`tests/conftest.py`); no
  hardware required.
- On-board bench validation: `examples/validate.py` (host **Run current file**,
  not bulk-synced). Wiring: `docs/hardware.md`.
- Human documentation: `docs/index.md`.

## Task routing

Read only the row for your change type.

| Changing… | Read | Run |
|-----------|------|-----|
| Bit layout / encode | `.agents/datasheet.md`, `.agents/engineering_guidelines.md` (Don't→Do, Invariant notes, Naming) | `test_register_mapper.py`, `test_register_file.py`, `test_validation.py` |
| Frequency / MOD | `.agents/datasheet.md`, naming in `.agents/engineering_guidelines.md` | `test_solver.py` |
| Synthesizer / SPI writes | `.agents/engineering_guidelines.md` (Invariant notes); AGENTS.md invariants 4–5, 11, 14–15; `adf435x/synthesizer.py` | `test_synthesizer.py` |
| Sweep / tables | `.agents/datasheet.md`, AGENTS.md invariant 14; `adf435x/sweep.py` | `test_sweep.py`, `test_regressions.py` |
| Board pins / SPI wiring | `docs/hardware.md` | `test_device.py`; `examples/validate.py` on board |
| New public names | `.agents/engineering_guidelines.md` naming | matching layer tests |
| Test harness / fixtures | `.agents/rules.md` testing section | touched `tests/` files |
| Human docs | `.agents/rules.md` (Documentation boundary) | `test_docs.py` |
| Version / release | `CONTRIBUTING.md` (Releasing) | `test_packaging.py` |
| Milestones only | `.agents/status.md` | — |

## Definition of done

- [ ] `pytest` exits 0; tests for the touched layer added or updated.
- [ ] No new hex register values in markdown (reference `WORKED_*` by name).
- [ ] `import adf435x` does not import `machine`.
- [ ] Datasheet-derived change → `.agents/datasheet.md` updated, plus a test.
- [ ] Docs updated per `.agents/rules.md`.

Baseline test count is tracked in `.agents/status.md` only — do not hardcode it
in prose, so adding tests never invalidates a checklist.

## Vendor references

- [ADF4350](https://www.analog.com/en/products/adf4350.html) ·
  [ADF4351](https://www.analog.com/en/products/adf4351.html) ·
  [cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet)
