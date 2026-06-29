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

## Source of truth (when docs disagree)

1. **Behavior:** code in `adf435x/` and passing tests
2. **Register words:** `WORKED_WORDS` / `WORKED_FIELDS` in `tests/conftest.py`
3. **Extracted PLL facts:** [agent/DATASHEET.md](agent/DATASHEET.md)
4. **Intent and history:** other `agent/` docs and [agent/JOURNAL.md](agent/JOURNAL.md)

Update agent docs when code changes; do not treat docs as authoritative over
tests.

## Task routing

| You are changing… | Read first | Run tests |
|-------------------|------------|-----------|
| Bit layout / encode | DATASHEET, DESIGN_DECISIONS §1–3 | `test_register_mapper`, `test_register_file` |
| Frequency math / MOD | DATASHEET, GLOSSARY | `test_solver` (golden vector) |
| Synthesizer API / writes | ARCHITECTURE, DESIGN_DECISIONS §4, §11 | `test_synthesizer` |
| Sweep / fast-hop | ARCHITECTURE (three-layer), DATASHEET §4 | `test_sweep` |
| Board pins / SPI wiring | HARDWARE (not library modules) | `test_device`, optional `--device` |
| New public names | GLOSSARY | matching layer tests |

## Common mistakes (avoid)

- **`WORKED_WORDS` index vs SPI order:** `WORKED_WORDS[n]` is register **Rn**
  (R0 first). SPI writes and `commit_plan()` return words in **R5→R0** order.
  Compare SPI logs with `reversed(WORKED_WORDS)` when all six registers are
  written.
- **`commit_plan()` vs `commit_all_plan()`:** use `commit_all_plan()` only for
  first power-up, divider boundaries, or full reprogram; use `commit_plan()` for
  frequency retunes (minimal stale set).
- **Solver output:** pass `result.fields` to `configure()` — never encode in
  the solver or skip validation.
- **Board pins:** belong in examples/tests/caller code only — never in `adf435x/`
  library modules.

## Do-not-break (summary)

1. Validate-at-setup, trust-at-encode
2. Commit plans: bare 32-bit words, R5 → R0
3. Double-buffer logic only in register file (read DBB from encoded R2)
4. Plan/mark split at synthesizer boundary
5. Integer-only Hz math in solver
6. Solver produces fields, not register words
7. Host-safe package root (no `machine` import at `import adf435x`)
8. MicroPython-safe, board-agnostic code in `adf435x/` (pins in caller only)

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
