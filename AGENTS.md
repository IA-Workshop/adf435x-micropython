# adf435x-micropython agent guide

MicroPython library for the ADF4350/ADF4351 wideband PLL synthesizers.
Host-testable on CPython; runs on any MicroPython board with SPI and GPIO.

## Commands

```bash
pip install -e ".[dev]"          # pytest + black
pytest -q                        # host suite, no hardware needed
black adf435x examples bench tests
python -m compileall -q adf435x examples bench tests
```

CI also compiles `adf435x/` with `mpy-cross` and runs
`micropython tests/micropython_smoke.py` on the MicroPython Unix port. Run
that locally when a change might not be MicroPython-safe.

## Source of truth, in order

1. Passing tests and the `adf435x/` code.
2. `WORKED_FIELDS` / `WORKED_WORDS` in `tests/conftest.py` (the data sheet
   worked example).
3. `.agents/datasheet.md` for PLL and register facts.
4. Other docs, which never override tests.

## Invariants

Each one is covered by tests. Changing one means changing those tests and
`.agents/engineering_guidelines.md`, which has the rationale.

1. **Validate at setup, trust at encode.** `validate_config()` runs in
   `configure()`; encoding only masks field widths.
2. **Plans are bare words.** `commit_plan()` returns 32-bit ints; SPI order
   is R5 to R0.
3. **Double-buffer state comes from the encoded R2 word**, not a flag.
4. **Plan/mark split.** The register file emits a plan and does no I/O; the
   synthesizer writes, then calls `mark_written()` or `mark_write_failed()`.
5. **Clocks live on the synthesizer** (`_last_write_us`); the register file
   keeps `commit_count` and `config_version`.
6. **Integer hertz only** in the solver. Floats raise `TypeError`.
7. **ADF4350/ADF4351 only.** No ADF4355/4356 register map.
8. **The solver returns fields, not words.** Encode through
   `register_file.configure(**result.fields)`.
9. **Host-safe package root.** `import adf435x` must not import `machine`;
   only `adf435x.device` does.
10. **One option bag:** `SolveOptions`. Bounds come from `ADF435xProfile`.
11. **Explicit write verbs:** `_write_stale_registers`,
    `_write_prebuilt_plan`. No generic `_program()`.
12. **MicroPython-safe `adf435x/`.** No `dataclasses`, `pathlib`, `typing`
    or other CPython-only stdlib.
13. **Board-agnostic library.** Pin numbers live in examples, tests and
    callers.
14. **Tables store words; playback diffs.** `FrequencyTable` entries hold
    all six words; `play_step()` calls `load_words()` and writes what
    differs from `last_written`.
15. **No SPI while powered down.** `set_frequency()` and output controls
    stage settings; `power_up()` solves, raises CE, then writes.

## Gotchas

- `WORKED_WORDS[n]` is register Rn. A full write is R5 first, so compare it
  with `reversed(WORKED_WORDS)`.
- Use `commit_plan()` for every retune and table hop, divider changes
  included. `full_plan()` is for power-up or a full reprogram.
- The prescaler must be 8/9 above 3.6 GHz (ADF4351) or 3.0 GHz (ADF4350).
  R4 stores log2 of the RF divider, not the divider.
- Register words appear in exactly one place, `tests/conftest.py`.
  `tests/test_docs.py` fails if a 32-bit hex word shows up in any Markdown
  file, so refer to `WORKED_*` by name.
- Register fields are defined once in `config.FIELDS`; cross-field checks
  live in `register_mapper._RULES`.
- `.agents/journal.md` records past decisions and the states they replaced.
  Append a dated entry for a non-obvious decision, but do not read it to
  learn how the code works now; it describes code that may no longer exist.

## Writing

Human-facing text (docs, README, changelog, docstrings, comments) follows
`.agents/writing_style.md`: American English, a hobbyist reader, terms
defined on first use, short docstrings, and no AI-writing patterns.

Human docs (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/**`) and
agent docs (this file, `CLAUDE.md`, `.agents/`, `.claude/`, `.cursor/`)
serve different readers. Either may cite the other, but each must be
complete on its own: never leave a fact a user needs only in agent docs, or
a rule an agent needs only in human docs.

## Read on demand

- `.agents/context.md`: scope, which files to read and tests to run for each
  kind of change, definition of done.
- `.agents/engineering_guidelines.md`: Don't/Do table, invariant rationale,
  naming.
- `.agents/rules.md`: workflow, test conventions, which docs to update.
- `.agents/datasheet.md`: PLL relationships, register facts with data
  sheet pages.
- `.agents/writing_style.md`: the writing rules above in full.
- `.agents/status.md`: milestones, test baseline, open work.

## Tool files

- Claude Code: `CLAUDE.md` imports this file; path-scoped rules in
  `.claude/rules/`; skills in `.claude/skills/`.
- Cursor: `.cursor/rules/*.mdc` point to the matching `.claude/rules/`
  file. Cursor also reads `.claude/skills/`.
- Codex and other tools read this file directly.
