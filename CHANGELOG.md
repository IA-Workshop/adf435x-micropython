# Changelog

All notable user-facing changes are documented here.

## 0.1.0

First release.

- ADF4350/ADF4351 PLL driver: solver, synthesizer, register stack, sweep
- Host-testable on CPython 3.10+ (`pip install -e ".[test]"` then `pytest`)
- Deploy: GitHub Release zip (`adf435x/`) or
  `mip.install("github:IA-Workshop/adf435x-micropython", version="v0.1.0")`
- Bench validation catalog in [`examples/validate.py`](examples/validate.py)

**Before tagging:** run `pytest` locally (not enforced by CI for v0.1.0).
