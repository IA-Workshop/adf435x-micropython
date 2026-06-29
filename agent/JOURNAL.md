# Development journal

Append-only log of implementation decisions. Newest entries at the top.
Permanent invariants go in [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md).

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
