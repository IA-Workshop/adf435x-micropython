# API guide

The library has three levels. Most programs only need the first.

| Level | Class | Use it to |
|-------|-------|-----------|
| Synthesizer | `ADF435xSynthesizer` | Set frequencies in hertz, mute, set output power, check [lock](glossary.md#lock), play [sweeps](glossary.md#sweep) |
| Planning | `solve()`, `FrequencyTable` | Work out [PLL](glossary.md#pll) settings or a sweep without touching hardware |
| Registers | `ADF435xRegisterFile` | Set individual [register](glossary.md#register) fields directly |

Everything can be imported from `adf435x` except the [SPI](glossary.md#spi)
and [GPIO](glossary.md#gpio) driver, `adf435x.device.ADF435xDevice`. That is
the only module that imports [MicroPython](glossary.md#micropython)'s
`machine` module, so the rest also runs on a PC.

## The synthesizer

```python
synth = ADF435xSynthesizer(device, ADF4351, ref_hz=10_000_000,
                           r_counter=1, doubler=False, rdiv2=False)
```

`r_counter`, `doubler` and `rdiv2` set the
[reference](glossary.md#reference) path: the [R
counter](glossary.md#r-counter) and the [doubler and
divide-by-2](glossary.md#reference-doubler-and-divide-by-2) (see [Frequency
planning](frequency-planning.md#choosing-the-reference-path)). They are
applied straight away, and an illegal combination raises an error here.

### Powering up and retuning

| Call | Effect |
|------|--------|
| `power_up(frequency_hz=...)` | Solve, raise [CE](glossary.md#ce), and write all six registers. The frequency is required the first time. An illegal frequency raises an error before CE goes high. |
| `set_frequency(hz)` | Solve and write the registers that changed. Returns a `SolveResult`. While powered down it only stores the settings, and the next `power_up()` writes them. |
| `power_down()` | CE low. The chip keeps its register contents. |
| `mute()`, `unmute()` | RF output off or on; the PLL keeps running. |
| `set_output_power(code)` | One of `consts.REG4_POWER_MINUS_4DBM`, `..._MINUS_1DBM`, `..._PLUS_2DBM`, `..._PLUS_5DBM` (power in [dBm](glossary.md#dbm)). |

Properties: `frequency` (the last target), `achieved_hz`, `is_powered`,
`last_write_us`, `profile`, `ref_hz`, `regfile`, `solve_options`.

### Lock detect

| Call | Effect |
|------|--------|
| `is_locked()` | Read [MUXOUT](glossary.md#muxout) once. Raises `RuntimeError` if MUXOUT is not wired, or is not set to digital lock detect. |
| `wait_locked(timeout_us=100_000)` | Poll until locked or timed out, and return `True` or `False`. Right after a write it first waits `lock_settle_us()`, the time for [band select](glossary.md#band-select) plus the [lock-detect count](glossary.md#ldf-and-ldp), so a "locked" reading left over from the old frequency is not mistaken for lock at the new one. |
| `has_lock_detect` | `True` if the device can read MUXOUT. |

### What the solver controls

Every `set_frequency()` sets the PLL fields: `int_n`, `frac`, `mod`
([INT](symbols.md#int), [FRAC](symbols.md#frac) and [MOD](symbols.md#mod)),
the [prescaler](glossary.md#prescaler), the
[`rf_divider`](glossary.md#rf-divider), `feedback`, the reference path, the
band-select clock (`band_clk_div`, `band_clk_mode`), and the lock-detect and
[spur](glossary.md#spur)-related settings `ldf`, `ldp`,
[`abp`](glossary.md#abp) and
[`charge_cancel`](glossary.md#charge-cancellation). These last four follow
the data sheet's recommendations for [integer-N](glossary.md#integer-n) and
[fractional-N](glossary.md#fractional-n) modes. Everything else (output
power, [charge-pump](glossary.md#charge-pump) current, MUXOUT, noise mode,
the [aux output](glossary.md#aux-output) and so on) stays as you set it.

### Solving without applying

`synth.solve(hz)` returns the `SolveResult` that `set_frequency(hz)` would
use, without changing anything. See [Frequency
planning](frequency-planning.md).

## Frequency tables

`FrequencyTable.from_range(synth, lower_hz, upper_hz, step_hz)` and
`FrequencyTable.from_frequencies(synth, [hz, ...])` solve a list of
frequencies in advance, and `synth.play(table)` and `synth.play_step(table,
i)` program them. See [Sweeps](sweeps.md).

## Register-level control

`synth.regfile` is the synthesizer's [register
file](glossary.md#register-file), an `ADF435xRegisterFile`. Its config
fields are named after the data sheet (`cp_current_code`, `muxout`,
`noise_mode`, `aux_enable`, `mtld` and so on):

```python
from adf435x import consts

synth.regfile.configure(aux_enable=True, aux_power=consts.REG4_POWER_PLUS_2DBM)
synth.set_frequency(synth.frequency)   # writes the changed registers
```

`configure()` checks every value, and every rule that involves it. For
example, the [phase](glossary.md#phase) must be below MOD, and [low-spur
mode](glossary.md#low-spur-mode) needs MOD of at least 50. If anything is
illegal it raises `ValueError` and changes nothing.

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
`mark_written()`. It adds an R0 write ([R0 to R5](symbols.md#rn-and-dbn) are
the six registers) when a [double-buffered](glossary.md#double-buffering)
register (R1, R2, or the R4 divider with double buffering on) needs one to
take effect. Words are always in R5-to-R0 order, as the chip requires.

## Errors

| Error | Raised when |
|-------|-------------|
| `FrequencyOutOfRangeError` | The target is outside the part's output range |
| `NoSolutionError` | No legal PLL settings exist (for example, [fPFD](symbols.md#fpfd) is too high) |
| `ExactFrequencyError` | `SolveOptions(exact=True)` is set and the target is not exactly reachable |
| `DividerOctaveCrossingError` | A table needs more than one RF divider and `allow_divider_change` is False |
| `LockTimeoutError` | `play(..., require_lock=True)` is used and lock did not happen in time |
| `ValueError` | A field value or option is illegal |
| `TypeError` | A frequency is not a whole number of hertz (floats are rejected) |

The first four are subclasses of `ValueError`; `LockTimeoutError` is a
`RuntimeError`.
