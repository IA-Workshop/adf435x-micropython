---
name: adf435x-development
description: >-
  Workflow for changing the adf435x ADF4350/ADF4351 MicroPython library:
  solver, register fields, synthesizer, frequency tables, examples or
  tests. Use when planning or making a code change in adf435x/, tests/,
  examples/ or bench/, and before handing the change back.
---

# Changing the adf435x library

## 1. Orient

`AGENTS.md` is already loaded. Open the row for your kind of change in
[.agents/context.md](../../../.agents/context.md#task-routing) and read only
the files it lists. If the change depends on a data sheet fact, check
[.agents/datasheet.md](../../../.agents/datasheet.md) and cite the page.

## 2. Change

- Keep the diff to what the task needs.
- `adf435x/` must still run on MicroPython: no CPython-only stdlib, no
  board pins.
- A new public name follows
  [.agents/engineering_guidelines.md](../../../.agents/engineering_guidelines.md#naming)
  and gets a changelog entry.
- Docstrings, comments and docs follow
  [.agents/writing_style.md](../../../.agents/writing_style.md).

## 3. Verify

```bash
pytest -q
black --check adf435x examples bench tests
```

If the change could affect MicroPython, also compile with `mpy-cross` and
run `micropython tests/micropython_smoke.py` (CI runs both). If it changes
what is written to the chip, say so in the handoff: it needs a bench check
with `examples/validate.py` before release.

## 4. Record

Update the docs listed in
[.agents/rules.md](../../../.agents/rules.md#documentation-update-obligations)
for your change. Append a dated entry to `.agents/journal.md` only for a
decision that is not obvious from the code and tests.

Done means every item in
[.agents/context.md](../../../.agents/context.md#definition-of-done) is true.
