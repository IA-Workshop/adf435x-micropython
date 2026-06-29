# Agent documentation index

Portable, tool-agnostic context for AI agents and human contributors working
on this repository. Cursor-specific rules live in [`.cursor/`](../.cursor/);
start at the repo root [AGENTS.md](../AGENTS.md).

## Documents

| File | Purpose |
|------|---------|
| [GLOSSARY.md](GLOSSARY.md) | Abbreviations and naming/style conventions |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layer stack, data flow, module roles |
| [DATASHEET.md](DATASHEET.md) | Extracted PLL/register facts and figure map |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | Non-negotiable invariants |
| [JOURNAL.md](JOURNAL.md) | Chronological implementation decision log |
| [TESTING.md](TESTING.md) | pytest setup, fixtures, conventions |
| [HARDWARE.md](HARDWARE.md) | Generic wiring, reference pin map, porting |
| [STATUS.md](STATUS.md) | Completed milestones and open work |

Source PDFs: [`datasheets/`](../datasheets/).

## Source of truth

When documentation conflicts with code or tests, trust in this order:

1. Passing tests and `adf435x/` implementation
2. `WORKED_FIELDS` / `WORKED_WORDS` in `tests/conftest.py`
3. [DATASHEET.md](DATASHEET.md) for extracted hardware facts
4. Other agent docs (intent, history, status)

## Maintenance contract

Agent docs describe **intent and invariants**. Code and tests remain the
source of truth for behavior.

| Trigger | Update |
|---------|--------|
| New abbreviation or naming pattern | [GLOSSARY.md](GLOSSARY.md) |
| Datasheet fact used or changed in code | [DATASHEET.md](DATASHEET.md) |
| Non-obvious design choice on a feature branch | [JOURNAL.md](JOURNAL.md) (append) |
| Milestone completed or scope change | [STATUS.md](STATUS.md) |
| New module or layer | [ARCHITECTURE.md](ARCHITECTURE.md) |
| New invariant | [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) |
| Portability / reference pin map change | [HARDWARE.md](HARDWARE.md) |

**Golden vector rule:** `WORKED_FIELDS` and `WORKED_WORDS` are defined once in
[`tests/conftest.py`](../tests/conftest.py). Other docs reference them by name;
do not duplicate hex register words in markdown.
