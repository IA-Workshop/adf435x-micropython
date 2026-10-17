# Agent workflow and maintenance rules

What to run, what to update, and how the tool files fit together.

## Implementation workflow

1. Read the `.agents/context.md` task-routing row for your change type.
2. Read `.agents/engineering_guidelines.md` when touching names, the solver,
   the register file or the synthesizer.
3. Make the smallest diff that does the job; `adf435x/` stays
   MicroPython-safe.
4. Run `pytest -q` and `black --check adf435x examples bench tests`.
5. Update docs per the table below.
6. Append to `.agents/journal.md` only for a decision that is not obvious
   from the code and tests. Do not read it to learn the current design; it
   describes past states.

## Tests by layer

| Change | Tests |
|--------|-------|
| Register / encode | `test_config.py`, `test_register_mapper.py`, `test_register_file.py`, `test_validation.py`, `test_fake_chip.py` |
| Solver | `test_solver.py` |
| Synthesizer | `test_synthesizer.py` |
| Sweep | `test_sweep.py` |
| Device SPI | `test_device.py` |
| Docs | `test_docs.py` |
| Version / `package.json` | `test_packaging.py` |
| Any fixed bug | `test_regressions.py` |

Conventions for writing tests are in `.claude/rules/tests.md`. Record the
current test count in `.agents/status.md` when it changes at a milestone;
do not repeat it elsewhere. Bench validation is not pytest:
`examples/validate.py`, described in `docs/examples/validation.md`.

- Known bugs are strict xfails in `tests/test_regressions.py`, made with
  `known_bug(finding, why)`. A fix makes the test pass unexpectedly, which
  fails the run, so remove the marker in the same change. Do not add a
  normal test that asserts current buggy behavior.
- Review finding IDs, from the code review of 2026-10-15 (all fixed in
  remediation steps A2 to A8), map to `tests/test_regressions.py` classes.
  Use the ID as the first argument of `known_bug(...)` if a finding
  reopens. Keep IDs out of test docstrings and comments.

  | ID | Defect | Test class |
  |----|--------|------------|
  | C1 | Sweep plans encoded from defaults, not the synth config | `TestSweepUsesSynthConfig` |
  | C2 | Range tables far coarser than requested | `TestRangeTableCoverage` |
  | C3 | Explicit frequency lists silently lose accuracy | `TestFrequencyListAccuracy` |
  | C4 | "Locked" MOD not locked | `TestLockedMod` |
  | C5, C6 | PFD truncation; floored achieved frequency | `TestExactArithmetic` |
  | C7, C17, C21, C8 | Validation gaps (C8: fast-mode divider limit) | `TestValidationGaps` |
  | C21 (solver side) | Low-spur MOD minimum ignored by the solver | `TestLowSpurSolve` |
  | C8 | Valid ADF4351 PFD range rejected | `TestBandSelectRange` |
  | C9 | Lock-detect settings | `TestLockDetectSettings` |
  | C10, C16 | Power-up and unpowered writes | `TestPowerUp` |
  | C11 | Divider-boundary sweeps without MUXOUT | `TestSweepWithoutMuxout` |
  | C12 | Lock polling before band select can finish | `TestLockSettle` |
  | C13 | Divider-crossing error suggestions | `TestCrossingSuggestions` |
  | C14 | Solver input validation | `TestSolverInputs` |
  | C15 | Playback after interleaved writes | `TestInterleavedPlayback` |
  | C19 | Example arithmetic | `TestExampleConstants` |
  | Q6 | Public error classes | `TestPublicErrors` |

- `FakeChip` (conftest) models register latching (DBR/DBB, data sheet
  p.12). Use it to check that `last_written` matches what the chip holds.
- The refactor oracles (frozen v0.1.0 encoder output and solver) checked
  the A2 and A4 rewrites and were removed in A8. Recover them from commit
  `ecf5a78` if a future rewrite needs them.
- Benchmarks: `python bench/bench.py` or `micropython bench/bench.py`;
  record notable changes in `.agents/status.md`.

## Documentation update obligations

| Change | Update |
|--------|--------|
| Public API or behavior | `docs/api-guide.md`, plus `docs/sweeps.md` or `docs/frequency-planning.md` as relevant |
| New term or symbol in human docs | `docs/glossary.md` or `docs/symbols.md` |
| Board deploy or wiring | `docs/hardware.md` |
| User-visible change | `CHANGELOG.md` "Unreleased" |
| New names | `.agents/engineering_guidelines.md` |
| Data sheet fact | `.agents/datasheet.md`, plus a test |
| Permanent invariant | `AGENTS.md` and `.agents/engineering_guidelines.md` |
| Test conventions | `.claude/rules/tests.md` and this file |
| Writing rules | `.agents/writing_style.md` |
| Milestone | `.agents/status.md` |
| Non-obvious decision | `.agents/journal.md` (append only) |

## Versions and releases

- Between releases `pyproject.toml` and `package.json` carry the same
  development version (`X.Y.Z.devN`); `test_packaging.py` checks that they
  agree and that `package.json` lists every `adf435x/*.py` module.
- The release workflow runs on a `vX.Y.Z` tag and fails unless the tag
  matches both files. Do not tag a release before the bench checks listed
  in `.agents/status.md` have passed; the maintainer tags releases.

## Tool files

- `AGENTS.md` is the shared entry point. Codex and Cursor read it directly;
  `CLAUDE.md` imports it with `@AGENTS.md` and adds Claude Code notes. Keep
  shared policy out of `CLAUDE.md`.
- `.claude/rules/*.md` hold the conventions for one area of code, loaded
  when Claude reads or edits a file matching their `paths`. They add detail
  to `AGENTS.md` and do not repeat it.
- `.cursor/rules/*.mdc` have the same globs and only point to the matching
  `.claude/rules/` file, so each convention has one copy.
- `.claude/skills/` holds the skills; Cursor reads that directory too. Keep
  skill frontmatter to `name`, `description` and, for user-only skills,
  `disable-model-invocation`.
- When you rename or move a file these name, update every pointer. The
  docs tests check that links resolve.

## Documentation boundary

Human docs (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/**`) and
agent docs (`AGENTS.md`, `CLAUDE.md`, `.agents/**`, `.claude/**`,
`.cursor/**`) serve different readers and purposes.

- Either side may cite the other, for example a human page linking the
  data sheet fact list as a source.
- Neither relies on the other. A user must not need an agent doc to
  understand or use the library, and an agent must not need a human page
  to learn a rule or invariant.
- New agent fact: `.agents/`. New explanation for users: `docs/`. If both
  readers need it, write it for each, in that reader's terms.
