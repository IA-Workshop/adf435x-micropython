---
paths:
  - "tests/**"
---

# Tests

- Use the shared fakes in `tests/conftest.py`: `FakeDevice`, `FakeChip`
  (models register latching), and the fixtures `fake_chip`, `chip_synth`
  and `no_sleep`. Do not write new fakes in test files.
- Group tests in `Test*` classes, one assertion per parametrized case.
- A known bug that is not fixed yet is a strict xfail with `known_bug(...)`
  in `test_regressions.py`. Fixing it makes the test pass unexpectedly,
  which fails the run, so remove the marker in the same change.
- `test_docs.py` checks Markdown links and anchors, the register-word ban,
  and that the README and quickstart code runs.
- Which test file covers which layer: `.agents/workflow.md`.
