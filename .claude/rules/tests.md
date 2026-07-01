---
paths:
  - "tests/**"
---

# Tests

- Host CPython ≥ 3.10; fake `machine` in `tests/conftest.py`.
- One assertion per parametrized test; group with `Test*` classes.
- Golden vector is `WORKED_FIELDS` / `WORKED_WORDS` in conftest — never
  re-hardcode hex elsewhere.
- Centralized `FakeDevice` in conftest; no per-file fakes.

Layer→file map: `.agents/rules.md`.
