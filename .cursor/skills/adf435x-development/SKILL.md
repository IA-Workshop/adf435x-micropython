---
name: adf435x-development
description: >-
  Develop the ADF435x MicroPython PLL library. Use when changing adf435x/,
  tests/, examples/, or agent docs.
---

# ADF435x development workflow

## 1. Orient

Read [AGENTS.md](../../AGENTS.md) — use the **task-routing table** only. Open
the listed docs for your change type; do not read JOURNAL, ARCHITECTURE, or
agent/README for implementation.

## 2. Implement

- Follow [agent/GLOSSARY.md](../../agent/GLOSSARY.md) for new names
- MicroPython-safe `adf435x/` (no dataclasses, pathlib, etc.)
- Board pins in caller/examples/tests only
- Minimal diff

## 3. Test

```bash
pip install -e ".[test]"
pytest
```

| Change | Tests |
|--------|-------|
| Register / encode | `test_register_mapper.py`, `test_register_file.py`, `test_validation.py` |
| Solver | `test_solver.py` |
| Synthesizer | `test_synthesizer.py` |
| Sweep | `test_sweep.py` |
| Device SPI | `test_device.py` |

## 4. Update docs (when needed)

| Change | Doc |
|--------|-----|
| Datasheet fact | `agent/DATASHEET.md` |
| New name/abbrev | `agent/GLOSSARY.md` |
| New invariant | `agent/DESIGN_DECISIONS.md` |
| Milestone | `agent/STATUS.md` |
| Non-obvious merge rationale | `agent/JOURNAL.md` (human; append only) |
| Layer structure (humans) | `agent/ARCHITECTURE.md` |

## Definition of done

See [AGENTS.md](../../AGENTS.md) § Definition of done.
