# Development journal

**Human reference only** — never on the agent implementation read path. Append
after non-obvious merges; permanent rules belong in
[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md).

Append-only log of implementation decisions. Newest entries at the top.

## Entry format

```markdown
## YYYY-MM-DD — Short title (branch/topic)

**Context:** one sentence
**Decision:** what we chose
**Alternatives rejected:** brief
**Files affected:** list
**Follow-ups:** if any
```

---

## 2026-06-29 — v0.1.0 release packaging

**Context:** Library feature-complete; ship ``adf435x/`` via GitHub Releases and
``mip`` without CI or local datasheet PDFs.

**Decision:** ``package.json`` (10 modules), tag-triggered release workflow
(zip only, no pytest gate), README install/quick-start, ``CHANGELOG.md``,
``datasheets/`` gitignored and removed locally; facts remain in
``agent/DATASHEET.md``.

**Alternatives rejected:** PyPI, micropython-lib upstream, ``.mpy`` builds,
GitHub Actions CI for v0.1.0, bundling ``examples/`` in release zip.

**Files affected:** ``package.json``, ``.github/workflows/release.yml``,
``README.md``, ``CHANGELOG.md``, ``.gitignore``, ``agent/STATUS.md``

**Follow-ups:** CI on push/PR when release cadence warrants it.

---

## 2026-06-29 — Bench validation in examples only

**Context:** Pre-PR review; host ``tests/vectors/`` duplicated
``examples/validate.py`` and could not run on hardware anyway.

**Decision:** Remove ``tests/vectors/``, ``TestCatalog``, and sync catalog tests;
``examples/validate.py`` ``CASES`` is the single bench registry. Sweep case calls
``power_up()`` before table playback; ``fixed_frequency.py`` matches validate
output style.

**Alternatives rejected:** Host sync test between catalog and example; keeping
``ValidationVector`` types in tests.

**Files affected:** ``tests/vectors/`` (deleted), ``tests/test_solver.py``,
``tests/test_validation_examples_sync.py`` (deleted),
``tests/test_vectors_catalog.py`` (deleted), ``examples/validate.py``,
``examples/fixed_frequency.py``, ``examples/frequency_table_solver.py``,
agent docs

**Follow-ups:** Shared pin module for examples (optional).

---

## 2026-06-29 — Scope-tier bench validation (host-run)

**Context:** Code review: missing 50–250 MHz scope points, validation should not
bulk-sync; run from host like other examples.

**Decision:** Six ``scope_*`` ``device=True`` rows in ``ref_10mhz.py``;
``validate.py`` single ``CASES`` registry (default ``scope_200mhz``), ``list``
case, per-step sweep print, ``ValueError`` on unknown; blanket ``examples`` in
MicroPico ``pyIgnore``; scope-first bring-up in HARDWARE.

**Alternatives rejected:** Bulk-sync ``validation_tests/``; PASS/FAIL bench
verdicts without analog instruments.

**Files affected:** ``examples/validate.py``,
``tests/test_validation_examples_sync.py`` (later removed), ``examples/fixed_frequency.py``,
``agent/HARDWARE.md``, ``agent/TESTING.md``, ``agent/GLOSSARY.md``,
``agent/STATUS.md``, ``AGENTS.md``, ``README.md``

**Follow-ups:** Shared pin module for examples (optional dedupe).

---

## 2026-06-29 — On-board validation_tests (pytest hardware removal)

**Context:** Host `pytest --device` could not run HIL tests (`machine` missing on
CPython); bench validation belongs on the Pico.

**Decision:** Move lock-detect and narrow-band sweep to
`examples/validation_tests/` (`_bench.py`, runners); delete
`test_device_hw.py` and `--device` pytest hooks; add
`test_validation_examples_sync.py` to guard catalog drift; MicroPico `pyIgnore`
syncs `validation_tests/` while excluding demo examples.

**Alternatives rejected:** Host mpremote pytest wrapper; importing `tests.vectors`
on the board.

**Files affected:** `examples/validation_tests/*`, `tests/test_device_hw.py`
(deleted), `tests/conftest.py`, `tests/test_validation_examples_sync.py`,
`tests/vectors/_types.py`, `pyproject.toml`, `agent/TESTING.md`,
`agent/HARDWARE.md`, `agent/STATUS.md`, `agent/ARCHITECTURE.md`, `AGENTS.md`,
`README.md`, `.cursor/rules/adf435x-tests.mdc`

**Follow-ups:** mpremote host runner for validation_tests (optional).

---

## 2026-06-29 — Hardware validation milestone (steps 3–6)

**Context:** Plan to expand host catalog tests, device HIL, examples, and agent
doc hooks after MicroPico deploy and `tests/vectors/` (steps 1–2).

**Decision:** `TestCatalog` in `test_solver.py`; parametrized lock-detect over
five ADF4351 catalog rows in `test_device_hw.py`; 140–145 MHz device sweep;
example catalog comments; HARDWARE bench table; TESTING catalog section;
`adf435x-agent-docs.mdc` + SKILL step-complete hook.

**Alternatives rejected:** Duplicate golden-only device test; importing
`tests.vectors` on Pico; `syncFolder: adf435x` flatten deploy.

**Files affected:** `tests/test_solver.py`, `tests/test_device_hw.py`,
`tests/test_vectors_catalog.py`, `examples/fixed_frequency.py`,
`examples/registers.py`, `agent/HARDWARE.md`, `agent/TESTING.md`,
`agent/STATUS.md`, `.cursor/rules/adf435x-agent-docs.mdc`,
`.cursor/skills/adf435x-development/SKILL.md`

**Follow-ups:** Optional `--device` CI; alternate `ref_*` bundles when HW exists.

---

## 2026-06-29 — ValidationVector catalog (step 2)

**Context:** Hardware validation needed a host-side catalog of integer-Hz solve
targets with part flags and reference-bundle extensibility.

**Decision:** Add `tests/vectors/` package (`ValidationVector`, `RefCatalog`,
`ref_10mhz.py` with six rows); validate REFIN/fPFD limits on import; host
`test_vectors_catalog.py` asserts each row matches `solve()`.

**Alternatives rejected:** `adf435x/vectors.py` on board; `HilVector` naming;
flattened `syncFolder: adf435x` catalog deploy.

**Files affected:** `tests/vectors/`, `tests/test_vectors_catalog.py`,
`agent/GLOSSARY.md`, `agent/DATASHEET.md`

**Follow-ups:** `TestCatalog` in `test_device_hw.py` HIL parametrization (steps
3–4).

---

## 2026-06-29 — MicroPico deploy documentation (step 1)

**Context:** Board upload needed a documented MicroPico layout so `adf435x/` ships
as an importable package, not flattened to the filesystem root.

**Decision:** Track an empty repo-root `.micropico` marker; document root
`syncFolder` plus `pyIgnore` in `HARDWARE.md` (`.vscode/settings.json` stays
local/gitignored).

**Alternatives rejected:** `syncFolder: "adf435x"` (breaks package imports);
committing `.vscode/settings.json` (machine-specific).

**Files affected:** `.micropico`, `.gitignore`, `agent/HARDWARE.md`

**Follow-ups:** ValidationVector catalog (`tests/vectors/`), HIL expansion.

---

## 2026-06-28 — Board-agnostic portability (docs)

**Context:** Agent docs implied the library targets WeAct RP2350B / Pico family only.

**Decision:** Document library as MicroPython board-agnostic; WeAct + eval board
pin map is a maintainer reference example only. Pin/SPI wiring stays in
examples, tests, and caller code — not in `adf435x/` modules.

**Alternatives rejected:** Hard-coding RP2040/2350 assumptions in library code or docs.

**Files affected:** `AGENTS.md`, `agent/ARCHITECTURE.md`, `agent/HARDWARE.md`,
`agent/DESIGN_DECISIONS.md`, `examples/fixed_frequency.py`

**Follow-ups:** None.

---

## 2026-06-28 — Agent documentation directory

**Context:** Multiple agent sessions produced design knowledge scattered across
handoff docs and chat history.

**Decision:** Create portable `agent/` knowledge base plus thin `.cursor/`
rules and skill; migrate [`HANDOFF_synthesizer.md`](../HANDOFF_synthesizer.md).

**Alternatives rejected:** Cursor-only `.cursor/` docs (not portable); single
monolithic handoff file (stale quickly).

**Files affected:** `agent/*`, `AGENTS.md`, `.cursor/rules/`, `.cursor/skills/`

**Follow-ups:** Append entries when completing feature-branch work.

---

## 2026-06 — Test infrastructure consolidation

**Context:** Synthesizer tests initially duplicated a local `FakeDevice`.

**Decision:** Centralize `FakeDevice` in [`tests/conftest.py`](../tests/conftest.py);
synthesizer tests use it without requiring `mock_machine` where possible.

**Alternatives rejected:** Per-file fake devices; always requiring `mock_machine`.

**Files affected:** `tests/conftest.py`, `tests/test_synthesizer.py`

**Follow-ups:** None.

---

## 2026-06 — MicroPython portability requirement

**Context:** Synthesizer and sweep modules must run on MicroPython boards, not
just CPython.

**Decision:** All new `adf435x/` code uses portable MicroPython-safe patterns
(`const` shim, `time.ticks_us` / `ticks_ms` fallbacks, custom `_gcd` and
`_log2`). No dependency on a specific MCU family.

**Alternatives rejected:** CPython-only features (`dataclasses`, `bit_length`).

**Files affected:** `adf435x/synthesizer.py`, `adf435x/sweep.py`, `adf435x/consts.py`

**Follow-ups:** Profile solve latency on device if MOD search becomes bottleneck.

---

## 2026-06 — Sweep module design

**Context:** Fast frequency hopping needs pre-encoded plans, not per-hop solving.

**Decision:** `FrequencyTable` precomputes SPI plans; `ADF435xSweeper` plays
them. MOD locked per divider band; full R5→R0 at divider boundaries;
`DividerOctaveCrossingError` by default for multi-octave spans; in-band hops
target single R0 writes.

**Alternatives rejected:** Re-solving on every hop; silent divider changes across
octaves.

**Files affected:** `adf435x/sweep.py`, `tests/test_sweep.py`,
`examples/frequency_sweep.py`, `examples/frequency_sweep_octave.py`

**Follow-ups:** Hardware validation of fast-hop timing on eval board.

---

## 2026-06 — API simplification (synthesizer + sweep)

**Context:** Early synthesizer plan had redundant accessors and setup steps.

**Decision:** Drop `SynthPolicy`; table builders take ref/profile from
synthesizer context; sweeper auto-enables fast-hop internally (no user
`prepare()` step); remove redundant `last_result` / duplicate frequency setter.

**Alternatives rejected:** `SynthPolicy` + `SolveOptions` parallel bags;
explicit `prepare()` before `run()`.

**Files affected:** `adf435x/synthesizer.py`, `adf435x/sweep.py`

**Follow-ups:** None.

---

## 2026-06 — Synthesizer facade (three-layer API)

**Context:** Users need frequency-first API separate from sweep playback.

**Decision:** Three layers: `ADF435xSynthesizer` (single frequency),
`FrequencyTable` (precomputed plans), `ADF435xSweeper` (playback). Explicit
write verbs: `_write_stale_registers`, `_write_prebuilt_plan`. Plan/mark split
with lock detect via MUXOUT.

**Alternatives rejected:** Single monolith class combining set-frequency and
sweep; vague `_program()` naming.

**Files affected:** `adf435x/synthesizer.py`, `tests/test_synthesizer.py`,
`adf435x/__init__.py`

**Follow-ups:** Export sweep from `__init__.py` only if API stabilizes further.

---

## 2026-06 — Solver rewrite

**Context:** No code could compute golden-vector fields from a target frequency.

**Decision:** Pure `solver.py`: integer-only Hz math; bounds from
`ADF435xDeviceProfile` + module constants (no `DeviceLimits` class); exhaustive
MOD search scoring `(abs(error_hz), mod)` with gcd reduction when frac > 0.

**Alternatives rejected:** Early stub with `DeviceLimits` / `limits_for_profile`;
float frequency math.

**Files affected:** `adf435x/solver.py`, `tests/test_solver.py`

**Follow-ups:** Optional cheat-sheet golden vectors; MOD search optimization.

---

## 2026-06 — Foundation register stack

**Context:** Need host-testable register pipeline before frequency solving.

**Decision:** Six layers (consts → device): validate-at-setup/trust-at-encode;
plan/mark split; staleness by word diff; double-buffer in register file;
golden vector in conftest; host-safe package root.

**Alternatives rejected:** Hand-kept dirty flags; encoding in config layer;
importing `machine` at package root.

**Files affected:** `adf435x/consts.py` through `adf435x/device.py`,
`tests/conftest.py`, layered test files

**Follow-ups:** None (foundation complete).
