---
paths:
  - "adf435x/solver.py"
  - "tests/test_solver.py"
---

# Solver

- Integer Hz only — no float frequency arguments anywhere in the path.
- `solve()` returns **fields, not register words**; encode only via
  `register_file.configure(**result.fields)`.
- Bounds come from `ADF435xProfile` + module constants — no `DeviceLimits`.
- Exact integer math: fPFD is a fraction (`pfd_num / pfd_den`), never rounded.
- MOD search: continued fractions; among errors that round to the same
  hertz, the smallest MOD wins (results are already in lowest terms).
- A fixed MOD (`SolveOptions.mod`, `channel_step_hz`) is never reduced.

Full rationale: `.agents/engineering_guidelines.md` (Don't→Do), `.agents/datasheet.md`.
