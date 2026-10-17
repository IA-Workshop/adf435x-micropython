# API guide

The library has three levels. Most programs only need the first.

| Level | Class | Use it to |
|-------|-------|-----------|
| Synthesizer | `ADF435xSynthesizer` | Set frequencies in hertz, mute, set output power, check lock, play sweeps |
| Planning | `solve()`, `FrequencyTable` | Work out PLL settings or a sweep without touching hardware |
| Registers | `ADF435xRegisterFile` | Control individual register fields directly |

Everything is importable from `adf435x` except the SPI/GPIO driver, which is
`adf435x.device.ADF435xDevice` (it is the only module that imports
`machine`, so the rest also runs on a PC).

## The synthesizer

```python
synth = ADF435xSynthesizer(device, ADF4351, ref_hz=10_000_000,
                           r_counter=1, doubler=False, rdiv2=False)
```

`r_counter`, `doubler` and `rdiv2` set the reference path (see
[Frequency planning](frequency-planning.md#choosing-the-reference-path)).
They are applied immediately, and invalid combinations raise here.

### Powering up and retuning

| Call | Effect |
|------|--------|
| `power_up(frequency_hz=...)` | Solve, raise CE, write all six registers. The frequency is required the first time. An invalid frequency raises before CE goes high. |
| `set_frequency(hz)` | Solve and write the registers that changed. Returns a `SolveResult`. While powered down it only stores the settings; the next `power_up()` writes them. |
| `power_down()` | CE low. The chip keeps its register contents. |
| `mute()`, `unmute()` | RF output off or on; the PLL keeps running. |
| `set_output_power(code)` | One of `consts.REG4_POWER_MINUS_4DBM`, `..._MINUS_1DBM`, `..._PLUS_2DBM`, `..._PLUS_5DBM`. |

Properties: `frequency` (last target), `achieved_hz`, `is_powered`,
`last_write_us`, `profile`, `ref_hz`, `regfile`, `solve_options`.

### Lock detect

| Call | Effect |
|------|--------|
| `is_locked()` | Read MUXOUT once. Raises `RuntimeError` if MUXOUT is not wired, or not routed to digital lock detect. |
| `wait_locked(timeout_us=100_000)` | Poll until locked or timed out; returns `True` or `False`. Right after a write it first waits `lock_settle_us()` (VCO band select plus the lock-detect count), so an old "locked" reading is not mistaken for the new frequency. |
| `has_lock_detect` | `True` if the device can read MUXOUT. |

### What the solver controls

Every `set_frequency()` sets the PLL fields: `int_n`, `frac`, `mod`,
`prescaler`, `rf_divider`, `feedback`, the reference path, the band-select
clock (`band_clk_div`, `band_clk_mode`), and the lock-detect and
spur-related settings `ldf`, `ldp`, `abp` and `charge_cancel`, which follow
the data sheet's integer-N and fractional-N recommendations. Everything else
(output power, charge-pump current, MUXOUT, noise mode, aux output, ...)
stays as you set it.

### Solving without applying

`synth.solve(hz)` returns the `SolveResult` that `set_frequency(hz)` would
use, without changing anything. See
[Frequency planning](frequency-planning.md).

## Frequency tables

`FrequencyTable.from_range(synth, lower_hz, upper_hz, step_hz)` and
`FrequencyTable.from_frequencies(synth, [hz, ...])` solve a list of
frequencies in advance; `synth.play(table)` and `synth.play_step(table, i)`
program them. See [Sweeps](sweeps.md).

## Register-level control

`synth.regfile` is the synthesizer's `ADF435xRegisterFile`. Its config fields
are named after the data sheet (`cp_current_code`, `muxout`, `noise_mode`,
`aux_enable`, `mtld`, ...):

```python
from adf435x import consts

synth.regfile.configure(aux_enable=True, aux_power=consts.REG4_POWER_PLUS_2DBM)
synth.set_frequency(synth.frequency)   # writes the changed registers
```

`configure()` checks every value and every rule that involves it (for
example the phase word must be below MOD, and low-spur noise mode needs MOD
of at least 50). If anything is invalid it raises `ValueError` and changes
nothing.

You can also use a register file on its own, without a synthesizer, and
write the words yourself:

```python
from adf435x import ADF4351, ADF435xRegisterFile, consts

regfile = ADF435xRegisterFile(ADF4351)
regfile.configure(int_n=422, frac=13, mod=25, rf_divider=2, band_clk_div=20,
                  band_clk_mode=consts.REG3_BAND_CLK_HIGH)
words = regfile.commit_all_plan()   # R5..R0, ready to send
device.write_registers(words)
regfile.mark_written()              # or regfile.mark_write_failed() on error
```

`commit_plan()` returns only the registers that changed since the last
`mark_written()`, plus an R0 write when a double-buffered register (R1, R2,
or the R4 divider with double buffering on) needs latching. Words are always
in R5-to-R0 order, as the chip requires.

## Errors

| Error | Raised when |
|-------|-------------|
| `FrequencyOutOfRangeError` | The target is outside the part's output range |
| `NoSolutionError` | No legal PLL settings exist (for example fPFD too high) |
| `ExactFrequencyError` | `SolveOptions(exact=True)` and the target is not exactly reachable |
| `DividerOctaveCrossingError` | A table needs several RF dividers and `allow_divider_change` is False |
| `LockTimeoutError` | `play(..., require_lock=True)` and lock did not assert |
| `ValueError` | An invalid field value or option |
| `TypeError` | A frequency that is not a whole number of hertz (floats are rejected) |

The first four are subclasses of `ValueError`; `LockTimeoutError` is a
`RuntimeError`.
