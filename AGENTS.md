# adf435x-micropython — agent guide

MicroPython library for ADF4350/ADF4351 wideband PLL synthesizers. Host-testable
on CPython; runs on any MicroPython board with SPI + GPIO. Pin numbers live in
callers/examples/tests, never in `adf435x/`.

```bash
pip install -e ".[test]"
pytest
```

## Source of truth (in order)

1. Passing tests + `adf435x/` code
2. `WORKED_FIELDS` / `WORKED_WORDS` in `tests/conftest.py`
3. `.agents/datasheet.md` — PLL / register facts
4. Other docs — not authoritative over tests

## Invariants

Canonical list. Full rationale and the Don't→Do table: `.agents/engineering_guidelines.md`.
Do not violate without updating tests.

1. **Validate-at-setup, trust-at-encode** — `validate_config()` at configure; encode masks widths only.
2. **Commit plans are bare words** — `commit_plan()` returns 32-bit ints in caller order; SPI/program order is **R5→R0**.
3. **Double-buffer state from encoded R2** — no separate flag.
4. **Plan/mark split** — regfile emits the plan; synthesizer calls `mark_written()` / `mark_write_failed()` after I/O.
5. **Timestamps on synthesizer** (`_last_write_us`); `commit_count` and `config_version` on regfile for freshness.
6. **Integer Hz only** in the solver — no float frequency arguments.
7. **ADF4350/ADF4351 only** — no 4355/4356 register map.
8. **Solver returns fields, not words** — encode only via `register_file.configure(**result.fields)`.
9. **Host-safe root** — `import adf435x` must not import `machine`.
10. **One option bag** — `SolveOptions` only; no `SynthPolicy` / `DeviceLimits`.
11. **Explicit write verbs** — `_write_stale_registers`, `_write_prebuilt_plan`; no `_program()`.
12. **MicroPython-safe `adf435x/`** — no `dataclasses`, `pathlib`, CPython-only stdlib.
13. **Board-agnostic library** — pins in callers/examples/tests only.
14. **Tables store words; playback diffs** — `FrequencyTable` entries hold all six words; `play_step()` uses `load_prevalidated()` then writes what differs from `last_written`. No precomputed delta plans.
15. **No SPI while powered down** — `set_frequency()` / output controls stage settings; `power_up()` writes them. `power_up()` solves before raising CE.

## Critical gotchas

- `WORKED_WORDS[n]` is register **Rn**. Compare a full six-register write with `reversed(WORKED_WORDS)`.
- `commit_plan()` for every retune and table hop, divider changes included (minimal stale set + latch R0); `commit_all_plan()` only for power-up or full reprogram.
- Prescaler threshold **3.6 GHz** (4351) / **3.0 GHz** (4350). R4 encodes **log2(divider)**, not the divider value.
- Never duplicate hex register values in markdown — reference `WORKED_*` by name (single source: `tests/conftest.py`; enforced by `tests/test_docs.py`).
- Register fields are defined once in `config.FIELDS`; cross-field checks live in `register_mapper._RULES`.
- `.agents/journal.md` is human append-only history — **never** on the implementation read path.

## Going deeper (read on demand)

- `.agents/engineering_guidelines.md` — Don't→Do table, expanded invariants, naming catalog
- `.agents/rules.md` — workflow, tests-by-layer, doc-update obligations
- `.agents/context.md` — scope, task-routing table, definition of done
- `.agents/datasheet.md` — PLL relationships, register/figure map

## Tool wrappers

- **Cursor:** `.cursor/rules/*.mdc`, `.cursor/skills/adf435x-development/SKILL.md`.
- **Claude Code:** path-scoped rules in `.claude/rules/` load automatically when you edit matching files.

Human docs (`docs/**`) never reference agent docs; the reverse is allowed.

Wrappers point here; they do not duplicate this content.
