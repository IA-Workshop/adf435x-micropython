# Project context

Scope, task routing and definition of done. `AGENTS.md` holds the
always-loaded essentials; this file is the depth for planning a change.

## Scope

- ADF4350 and ADF4351 only, not the ADF4355/4356 family.
- MicroPython on any board with SPI and GPIO. Pin numbers live in callers,
  examples and tests, never in `adf435x/`.
- Host suite: CPython 3.10 or later with a fake `machine` module
  (`tests/conftest.py`); no hardware needed.
- On-board bench validation: `examples/validate.py`, run as a single file
  from the host (it is not synced to the board with the library).
- Bench work waiting for hardware is listed in `.agents/status.md`.

## Task routing

Read only the row for your change type. Path-scoped rules in
`.agents/rules/` load on their own when you open matching files.

| Changing | Read | Run |
|----------|------|-----|
| Bit layout / encode | `.agents/datasheet.md`; `.agents/engineering_guidelines.md` (Don't/Do, invariant notes, naming) | `test_config.py`, `test_register_mapper.py`, `test_register_file.py`, `test_validation.py` |
| Frequency / MOD | `.agents/datasheet.md`; naming in `.agents/engineering_guidelines.md` | `test_solver.py`, `bench/bench.py` |
| Synthesizer / SPI writes | `.agents/engineering_guidelines.md` (invariant notes); AGENTS.md invariants 4, 5, 11, 14, 15 | `test_synthesizer.py`, `test_device.py` |
| Sweep / tables | `.agents/datasheet.md` (double buffering); AGENTS.md invariant 14 | `test_sweep.py`, `test_regressions.py` |
| Board pins / SPI wiring | `examples/` for pin conventions; `docs/hardware.md` cites the board wiring | `test_device.py`; `examples/validate.py` on a board |
| New public names | `.agents/engineering_guidelines.md` (naming) | matching layer tests |
| Test harness / fixtures | `.agents/workflow.md` (tests by layer) | touched `tests/` files |
| Human docs, docstrings, comments | `.agents/writing_style.md`; `.agents/workflow.md` (documentation boundary) | `test_docs.py` |
| Version / release | `.agents/workflow.md` (versions and releases) | `test_packaging.py` |
| Agent docs or tool files | `.agents/workflow.md` (tool files) | `test_docs.py` |
| Milestones only | `.agents/status.md` | none |

## Definition of done

- `pytest -q` passes, with tests for the touched layer added or updated.
- `black --check adf435x examples bench tests` passes.
- No 32-bit register words in Markdown; refer to `WORKED_*` by name.
- `import adf435x` does not import `machine`.
- A change based on the data sheet updates `.agents/datasheet.md` and adds
  a test.
- Docs are updated per `.agents/workflow.md`, and human-facing text follows
  `.agents/writing_style.md`.
- A change to what is written to the chip is flagged for a bench check.

The baseline test count lives only in `.agents/status.md`, so adding tests
never makes this checklist wrong.

## Vendor references

- [ADF4350](https://www.analog.com/en/products/adf4350.html),
  [ADF4351](https://www.analog.com/en/products/adf4351.html),
  [common questions cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet)
