# Agent guide — adf435x-micropython

```bash
pip install -e ".[test]"
pytest
pytest --device    # hardware; maintainer reference pin map — see agent/HARDWARE.md
```

## Scope

- ADF4350/ADF4351 only (not 4355/4356 family)
- MicroPython on any board with SPI + GPIO; pin numbers live in caller /
  examples / tests — never in `adf435x/` library modules
- Host suite: CPython ≥ 3.10, no hardware required

Humans: [agent/README.md](agent/README.md) (doc index). Layer overview:
[agent/ARCHITECTURE.md](agent/ARCHITECTURE.md) (human reference — not required
for implementation tasks).

## Critical gotchas

1. **`WORKED_WORDS[n]` = register Rn**; SPI and `commit_plan()` order is
   **R5→R0**. Compare a full six-register write with `reversed(WORKED_WORDS)`.
   Single source: `tests/conftest.py` — do not duplicate hex values in markdown.

2. **`commit_plan()`** for retunes (minimal stale set).
   **`commit_all_plan()`** only for power-up, divider boundaries, or full
   reprogram.

3. **Integer Hz only** in the solver; no float frequency arguments.

4. **Solver returns fields**, not register words. Encode only via
   `register_file.configure(**result.fields)` (mapper validates at configure).

5. **`import adf435x` must not import `machine`** (host-safe package root).

## Source of truth

1. Passing tests + `adf435x/` code
2. `WORKED_FIELDS` / `WORKED_WORDS` in `tests/conftest.py`
3. [agent/DATASHEET.md](agent/DATASHEET.md)
4. Other agent docs (not authoritative over tests)

## Task routing

| Changing… | Read | Run |
|-----------|------|-----|
| Bit layout / encode | [DATASHEET](agent/DATASHEET.md), [DESIGN_DECISIONS](agent/DESIGN_DECISIONS.md) §1–3, [GLOSSARY](agent/GLOSSARY.md) | `test_register_mapper.py`, `test_register_file.py`, `test_validation.py` |
| Frequency / MOD | [DATASHEET](agent/DATASHEET.md), [GLOSSARY](agent/GLOSSARY.md) | `test_solver.py` |
| Synthesizer / SPI writes | [DESIGN_DECISIONS](agent/DESIGN_DECISIONS.md) §4–5, §11–13; `adf435x/synthesizer.py` | `test_synthesizer.py` |
| Sweep / fast-hop | [DATASHEET](agent/DATASHEET.md) (int-N / fast-hop), [DESIGN_DECISIONS](agent/DESIGN_DECISIONS.md); `adf435x/sweep.py` | `test_sweep.py` |
| Board pins / SPI wiring | [HARDWARE](agent/HARDWARE.md) | `test_device.py`; optional `--device` |
| New public names | [GLOSSARY](agent/GLOSSARY.md) | matching layer tests |
| Test harness / fixtures | [TESTING](agent/TESTING.md) | touched `tests/` files |
| Milestones only | [STATUS](agent/STATUS.md) | — |

Do not open [JOURNAL](agent/JOURNAL.md), [ARCHITECTURE](agent/ARCHITECTURE.md), or
[agent/README](agent/README.md) for implementation work.

## Don't → Do

| Don't | Do instead |
|-------|------------|
| Re-validate ranges in `encode_register()` | `validate_config()` at `configure()`; encode masks widths only |
| Return `(index, word)` or reorder writes in `device` | `commit_plan()` → bare 32-bit words, **R5→R0** |
| Track DBB with a flag separate from encoded R2 | Read `double_buffer` from encoded R2; DBR/DBB logic in `register_file` only |
| Call optimistic `commit()` from the synthesizer | `commit_plan()` → device write → `mark_written()` or `mark_write_failed()` |
| Use float Hz or emit register words from `solve()` | Integer Hz; `solve()` → `configure(**result.fields)` |
| `import machine` at package root | `adf435x.device` submodule only |
| Hard-code board pins in `adf435x/` | Pass SPI/GPIO from caller, examples, or HIL tests |
| Add `SynthPolicy`, `DeviceLimits`, or a second options bag | `SolveOptions` + `ADF435xDeviceProfile` bounds |

Full invariants: [agent/DESIGN_DECISIONS.md](agent/DESIGN_DECISIONS.md).

## Vendor references

- [ADF4350](https://www.analog.com/en/products/adf4350.html) ·
  [ADF4351](https://www.analog.com/en/products/adf4351.html) ·
  [cheat sheet](https://ez.analog.com/rf/w/documents/14697/adf4350-and-adf4351-common-questions-cheat-sheet)
- Extracted PLL/register facts: [agent/DATASHEET.md](agent/DATASHEET.md)

## Definition of done

- [ ] `pytest` exits 0 (**301** collected; **299** pass, **2** skip without
      `--device`)
- [ ] Register / solver / datasheet edit: layer tests updated;
      [DATASHEET.md](agent/DATASHEET.md) updated if an extracted fact changed
- [ ] No new hex register values in markdown (reference `WORKED_*` by name)
- [ ] `import adf435x` does not import `machine`
- [ ] Doc edits follow the task-routing table above (no generic filler)

## Cursor

[`.cursor/rules/`](.cursor/rules/) ·
[`.cursor/skills/adf435x-development/SKILL.md`](.cursor/skills/adf435x-development/SKILL.md)
