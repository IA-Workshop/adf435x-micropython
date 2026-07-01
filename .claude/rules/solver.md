---
paths:
  - "adf435x/solver.py"
  - "tests/test_solver.py"
---

# Solver

- Integer Hz only — no float frequency arguments anywhere in the path.
- `solve()` returns **fields, not register words**; encode only via
  `register_file.configure(**result.fields)`.
- Bounds come from `ADF435xDeviceProfile` + module constants — no `DeviceLimits`.
- MOD search scores `(abs(error_hz), mod)`; gcd-reduce `(FRAC, MOD)` when FRAC > 0.

Full rationale: `.agents/engineering_guidelines.md` (§6, §8), `.agents/datasheet.md`.
