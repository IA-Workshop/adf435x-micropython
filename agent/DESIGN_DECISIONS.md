# Design decisions (invariants)

Permanent rules agents must preserve. Historical rationale for each choice
lives in [JOURNAL.md](JOURNAL.md). Naming rules in [GLOSSARY.md](GLOSSARY.md).

Each entry: **Decision → Rationale → Enforced in → Do not**.

---

## 1. Validate-at-setup, trust-at-encode

**Decision:** Validation runs in `validate_config()` at configure time; encode
masks widths but does not re-check ranges.

**Rationale:** Keeps the hot encode path branch-light; solver output is
rejected at the register-file boundary.

**Enforced in:** [`register_mapper.py`](../adf435x/register_mapper.py),
[`register_file.configure()`](../adf435x/register_file.py)

**Do not:** Add range checks inside `encode_register` or bypass validation in
the synthesizer.

---

## 2. Commit plans are bare words, R5 → R0

**Decision:** `commit_plan()` returns a list of 32-bit integers (register
address in DB2:DB0), ordered R5 down to R0.

**Rationale:** Matches datasheet SPI programming order; device handler writes
caller-supplied order.

**Enforced in:** [`register_file.py`](../adf435x/register_file.py),
[`device.py`](../adf435x/device.py)

**Do not:** Return `(index, word)` pairs or change write order at the device
layer.

---

## 3. Double-buffer logic stays in the register file

**Decision:** DBR/DBB latch ordering is computed from the encoded word diff.
DBB state is read from the encoded R2 word (`double_buffer` bit).

**Rationale:** Prevents drift between a separate flag and the diffed words.

**Enforced in:** [`register_file._commit_stale_set`](../adf435x/register_file.py)

**Do not:** Reintroduce a separate double-buffer flag outside the encoded R2
word.

---

## 4. Plan/mark split at the synthesizer boundary

**Decision:** Register file emits plans without updating cache; synthesizer
calls `mark_written()` or `mark_write_failed()` after device I/O.

**Rationale:** Enables failure recovery and timestamp stamping without making
the register file time-aware.

**Enforced in:** [`synthesizer._write_prebuilt_plan`](../adf435x/synthesizer.py)

**Do not:** Use optimistic `commit()` in the synthesizer write path.

---

## 5. Timestamps at synth level; freshness at regfile level

**Decision:** `_last_write_us` lives on the synthesizer. `commit_count` on the
register file is the pure freshness signal.

**Rationale:** Register file stays timeless and host-testable.

**Enforced in:** [`synthesizer.py`](../adf435x/synthesizer.py),
[`register_file.dump()`](../adf435x/register_file.py)

**Do not:** Add wall-clock fields to the register file.

---

## 6. Integer-only Hz math in the solver

**Decision:** All frequency planning uses integer hertz with explicit
remainders (`_round_div`, `_ceil_div`, `_gcd`).

**Rationale:** MicroPython doubles give ~256 Hz resolution near 4 GHz.

**Enforced in:** [`solver.py`](../adf435x/solver.py)

**Do not:** Use float Hz in the solver or accept float frequency arguments.

---

## 7. Scope is ADF4350/ADF4351 only

**Decision:** No support for ADF4355/4356/5355/5356 (different register map).

**Rationale:** Shared register layout in `consts` assumes 4350/4351 family.

**Enforced in:** [`profiles.py`](../adf435x/profiles.py) module docstring

**Do not:** Add profiles or register fields for other families without a
separate design pass.

---

## 8. Solver produces fields, not words

**Decision:** `solve()` returns a `SolveResult` with a field dict. Encoding is
always `register_file.configure()` + mapper.

**Rationale:** Single validation and encode gate; solver stays pure.

**Enforced in:** [`solver.py`](../adf435x/solver.py)

**Do not:** Encode register words inside the solver.

---

## 9. Host-safe package root

**Decision:** Importing `adf435x` does not import `machine`. Device access is
via `adf435x.device`.

**Rationale:** Full pytest suite runs on CPython without hardware.

**Enforced in:** [`__init__.py`](../adf435x/__init__.py)

**Do not:** Import `machine` from any module re-exported at package root.

---

## 10. No duplicate option bags

**Decision:** Reference path options live in `SolveOptions` only. No `SynthPolicy`
or parallel configuration types.

**Rationale:** Avoids overlapping APIs and repeated constructor arguments.

**Enforced in:** [`synthesizer.py`](../adf435x/synthesizer.py),
[`solver.py`](../adf435x/solver.py)

**Do not:** Introduce a second options class for the synthesizer.

---

## 11. Explicit write-path verb names

**Decision:** Use `_write_stale_registers` and `_write_prebuilt_plan`, not
vague names like `_program`.

**Rationale:** Clarifies diff-based vs pre-built plan paths (sweep).

**Enforced in:** [`synthesizer.py`](../adf435x/synthesizer.py),
[`sweep.py`](../adf435x/sweep.py)

**Do not:** Add generic `_program()` wrappers.

---

## 12. MicroPython-safe new code

**Decision:** All code in `adf435x/` must run on MicroPython across board
ports (not a single MCU family). Use `time.ticks_us` / `time.ticks_ms` shims;
avoid CPython-only stdlib.

**Rationale:** Host tests use CPython; deployed code runs on diverse
MicroPython boards with varying `machine` implementations.

**Enforced in:** [`consts.py`](../adf435x/consts.py) (`const` shim),
[`synthesizer.py`](../adf435x/synthesizer.py), [`sweep.py`](../adf435x/sweep.py)

**Do not:** Use `dataclasses`, `pathlib`, or other unavailable stdlib on target.

---

## 13. Board-agnostic library modules

**Decision:** Pin numbers, SPI bus index, and baud rate live in caller code,
examples, and hardware tests — not in `adf435x/` library modules.

**Rationale:** The library targets any MicroPython board with SPI and GPIO;
hard-coded pins would break portability.

**Enforced in:** [`device.py`](../adf435x/device.py) (accepts injected SPI/pins),
[`synthesizer.py`](../adf435x/synthesizer.py) (duck-typed device)

**Do not:** Add board-specific constants or `machine` pin assignments under
`adf435x/` except in `device.py`'s constructor arguments from the caller.
