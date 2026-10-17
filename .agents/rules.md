# Agent workflow and maintenance rules

What to run, what to update, and where wrappers point.

## Implementation workflow

1. Read the `.agents/context.md` task-routing row for your change type.
2. Read `.agents/engineering_guidelines.md` when touching names, the solver, the
   register file, or the synthesizer.
3. Implement a minimal diff in `adf435x/` (MicroPython-safe).
4. Run `pytest` for the touched layers before handoff.
5. Update docs per the table below.
6. Append `.agents/journal.md` only for a non-obvious decision (write-only during
   work — never read it for orientation).

```bash
pip install -e ".[test]"
pytest
```

## Tests by layer

| Change | Tests |
|--------|-------|
| Register / encode | `test_register_mapper.py`, `test_register_file.py`, `test_validation.py` |
| Solver | `test_solver.py` |
| Synthesizer | `test_synthesizer.py` |
| Sweep | `test_sweep.py` |
| Device SPI | `test_device.py` |

Host CPython ≥ 3.10; fake `machine` in `tests/conftest.py`. Golden vector is
`WORKED_FIELDS` / `WORKED_WORDS` in conftest — do not re-hardcode hex elsewhere.
One assertion per parametrized test; group with `Test*` classes. Centralized
`FakeDevice` in conftest; no per-file fakes. Current baseline count: refresh with
`pytest -q` and record in `.agents/status.md`. Bench validation (not pytest):
`examples/validate.py` → `docs/examples/validation.md`.

- **Known bugs** are strict xfails in `tests/test_regressions.py`, tagged with
  a review ID. A fix makes the test XPASS, which fails the run: remove the
  `known_bug` marker in the same change. Never add a normal test that asserts
  current buggy behaviour.
- **`FakeChip`** (conftest) models register latching (DBR/DBB, data sheet p.12);
  use it to assert `last_written` matches what the chip holds.
- **Refactor oracles** (frozen v0.1.0 encoder output and solver) proved the
  A2 and A4 rewrites and were removed in A8; recover them from git history
  (commit ecf5a78) if a future rewrite needs them.
- **Benchmarks:** `python bench/bench.py` or `micropython bench/bench.py`;
  record notable changes in `.agents/status.md`.
- **MicroPython:** CI compiles `adf435x/` with `mpy-cross` and runs
  `micropython tests/micropython_smoke.py` on the Unix port. Run it locally
  before changing anything that might not be MicroPython-safe.

## Documentation update obligations

After each implementation step:

| Change | Update |
|--------|--------|
| Board deploy / wiring | `docs/hardware.md` |
| New names / catalog | `.agents/engineering_guidelines.md` |
| Datasheet fact | `.agents/datasheet.md` (+ a test) |
| Tests / HIL conventions | this file, testing section |
| Milestone | `.agents/status.md` |
| Permanent invariant | `AGENTS.md` + `.agents/engineering_guidelines.md` |
| Human layer overview | `docs/architecture.md` |
| Non-obvious merge rationale | `.agents/journal.md` (append only) |

## Wrapper policy

- **Source of truth:** the `.agents/` directory.
- **Thin entry points:** `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/`, `.claude/rules/`
  point here and carry no routing tables of their own.
- `CLAUDE.md` is `@AGENTS.md` plus Claude-only notes. Cursor and Codex read
  `AGENTS.md` directly.
- `.claude/rules/*.md` and `.cursor/rules/*.mdc` are path-scoped pointers into
  `.agents/`; they trigger on matching file edits and never restate content.

## Documentation boundary

- Human docs (`docs/**`, and the human body of `README.md`) link only to
  `docs/**`, source, tests, or external URLs. They **never** reference
  `.agents/**`, `AGENTS.md`, or `CLAUDE.md`.
- Agent docs (`.agents/**`, `AGENTS.md`, `CLAUDE.md`) **may** link to `docs/**`,
  source, tests, and external URLs.
- New agent fact → `.agents/`. New human explanation → `docs/`. Never cross the
  boundary in the human→agent direction.
