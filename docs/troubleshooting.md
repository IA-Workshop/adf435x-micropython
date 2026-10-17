# Troubleshooting

## No output, or never locks

1. **Check wiring with MUXOUT.** Run
   [`examples/device_handler.py`](../examples/device_handler.py). It sets
   MUXOUT high, then low, without needing lock. If MUXOUT does not follow,
   SPI, LE or the MUXOUT input is wrong (check SPI mode 0 and that LE is the
   pin you passed as `load_enable_pin`).
2. **Check the reference.** `ref_hz` must equal the real REFIN frequency,
   and REFIN must be within 10–250 MHz (≤ 30 MHz with the doubler).
3. **Check CE.** `synth.is_powered` should be `True`; CE low powers the chip
   down.
4. **Check the charge-pump current.** It must suit your loop filter; the
   default (code 7) matches the evaluation board
   ([Hardware](hardware.md#loop-filter-and-charge-pump-current)).
5. **Give it time.** Lock after a large jump (especially a divider change)
   can take hundreds of microseconds; use `wait_locked()` rather than one
   `is_locked()` read.

## Locked, but the wrong frequency

- `ref_hz` does not match the real reference. The PLL locks happily to the
  wrong value.
- Look at `synth.achieved_hz` and `result.error_hz`: the target may not be
  exactly reachable ([Frequency planning](frequency-planning.md#exact-and-nearest-frequencies)).

## `wait_locked()` returns False

- MUXOUT is not wired, or `muxout` was changed from digital lock detect
  (`is_locked()` raises `RuntimeError` in both cases).
- The loop really is not locking; see the first section.

## Errors when setting a frequency

| Message mentions | Meaning |
|------------------|---------|
| `outside [...]` (`FrequencyOutOfRangeError`) | Below 34.375 MHz (ADF4351) / 137.5 MHz (ADF4350), or above 4.4 GHz |
| `f_pfd=... exceeds` (`NoSolutionError`) | fPFD over 32 MHz: raise `r_counter`, or turn off the doubler |
| `must be an integer` (`TypeError`) | A float such as `433.92e6`; write `433_920_000` |
| `low-spur noise mode needs MOD >= 50` | Set `mod=50` in the same `configure()` call that turns on low-spur mode |
| `phase=... must be less than MOD` | A phase word you set is too large for the new MOD |
| `power_up() needs frequency_hz` | Pass `frequency_hz=` the first time |

## Sweeps

- **`DividerOctaveCrossingError`:** the range needs several RF dividers.
  Narrow it as the message suggests, or pass `allow_divider_change=True`.
- **Hops slower than expected:** if `table.channel_step_hz` is 0, entries
  use different MODs and each hop also writes R1. Choose a step that divides
  evenly ([Sweeps](sweeps.md#how-mod-is-chosen)).
- **`max_error_hz` exceeded:** some targets are not reachable that closely
  with your reference; change the step or the reference path.
