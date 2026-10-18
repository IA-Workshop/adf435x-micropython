---
paths:
  - "adf435x/synthesizer.py"
  - "adf435x/sweep.py"
  - "adf435x/device.py"
---

# Synthesizer, sweeps and device

- Every SPI write follows plan, write, mark: get words from the register
  file, send them with `device.write_registers()`, then call
  `mark_written()`, or `mark_write_failed()` if the write raised.
- Table entries are encoded from a copy of the synthesizer's settings with
  `double_buffer=True`. `FrequencyTable.sync()` re-encodes them when the
  register file's `config_version` changes.
- The settle wait before lock polling uses `LOCK_SETTLE_MARGIN_US`, which is
  provisional until bench step B3 (see `.agents/status.md`).
- `device.py` is the only module that imports `machine`. Keep the hot path
  (`write_registers`) free of allocation.
- Tests: `test_synthesizer.py`, `test_sweep.py`, `test_device.py`,
  `test_regressions.py`.
