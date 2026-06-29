# Agent guide — adf435x-micropython

Entry point for AI agents and contributors. Read this before making changes.

## Scope

- **Devices:** ADF4350 and ADF4351 only (not 4355/4356 family)
- **Target runtime:** MicroPython on any supported board (not tied to a specific
  MCU family — RP2040/2350, STM32, ESP32, etc.)
- **Host testing:** CPython ≥ 3.10 + pytest (no hardware required)

## Read order

1. [agent/GLOSSARY.md](agent/GLOSSARY.md) — abbreviations and naming (read before new types/fields)
2. [agent/ARCHITECTURE.md](agent/ARCHITECTURE.md) — layer stack and data flow
3. [agent/DESIGN_DECISIONS.md](agent/DESIGN_DECISIONS.md) — non-negotiable invariants
4. Task-specific:
   - Register/encode work → [agent/DATASHEET.md](agent/DATASHEET.md)
   - Tests → [agent/TESTING.md](agent/TESTING.md)
   - Board/pins → [agent/HARDWARE.md](agent/HARDWARE.md)
   - History → [agent/JOURNAL.md](agent/JOURNAL.md)
   - Current status → [agent/STATUS.md](agent/STATUS.md)

Full index: [agent/README.md](agent/README.md).

## Do-not-break (summary)

1. Validate-at-setup, trust-at-encode
2. Commit plans: bare 32-bit words, R5 → R0
3. Double-buffer logic only in register file (read DBB from encoded R2)
4. Plan/mark split at synthesizer boundary
5. Integer-only Hz math in solver
6. Solver produces fields, not register words
7. Host-safe package root (no `machine` import at `import adf435x`)
8. MicroPython-safe, board-agnostic code in `adf435x/` (no board-specific pins in library modules)

Details: [agent/DESIGN_DECISIONS.md](agent/DESIGN_DECISIONS.md).

## Golden vector

Datasheet worked example (2112.6 MHz, ADF4351, 10 MHz ref):

- Fields: `WORKED_FIELDS` in [`tests/conftest.py`](tests/conftest.py)
- Words: `WORKED_WORDS` in the same file

Do not duplicate hex register values in docs.

## Run tests

```bash
conda activate general          # maintainer local env; any 3.10+ env works
pip install -e ".[test]"
pytest
```

Hardware: `pytest --device`. See [agent/TESTING.md](agent/TESTING.md).

## Datasheets

PDFs in [`datasheets/`](datasheets/). Extracted facts for agents:
[agent/DATASHEET.md](agent/DATASHEET.md).

## Cursor integration

Project rules: [`.cursor/rules/`](.cursor/rules/). Development skill:
[`.cursor/skills/adf435x-development/SKILL.md`](.cursor/skills/adf435x-development/SKILL.md).
