---
paths:
  - "adf435x/solver.py"
  - "tests/test_solver.py"
---

# Solver

- fPFD is kept as an exact fraction (`pfd_num`, `pfd_den`). Never round it
  or use floats; `exact` is true only when the residual is zero.
- MOD search uses continued fractions (`_farey_neighbors`,
  `_simplest_between`). Among results whose error rounds to the same hertz,
  the smallest MOD wins.
- A fixed MOD (`SolveOptions.mod` or `channel_step_hz`) is used as given,
  never reduced.
- Lock-detect and spur bits for integer-N vs fractional-N come from
  `pll_mode_fields()`; their data sheet basis is in `.agents/datasheet.md`.
- The baseline speed is in `.agents/status.md`; rerun `bench/bench.py`
  after changing the search.
