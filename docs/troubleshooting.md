# Troubleshooting

Words such as [lock](glossary.md#lock), [MUXOUT](glossary.md#muxout) and
[fPFD](symbols.md#fpfd) are explained in the [glossary](glossary.md) and on
the [symbols](symbols.md) page.

## No output, or never locks

Work through these in order.

1. Check the wiring with MUXOUT. Run
   [`examples/device_handler.py`](../examples/device_handler.py), which sets
   MUXOUT high and then low without needing lock. If MUXOUT does not follow,
   the [SPI](glossary.md#spi) wiring, [LE](glossary.md#le) or the MUXOUT
   input is wrong. Check that SPI is in mode 0, and that LE is wired to the
   pin you passed as `le_pin`.
2. Check the [reference](glossary.md#reference). `ref_hz` must equal the
   real [REFIN](symbols.md#refin) frequency, and REFIN must be from 10 MHz
   to 250 MHz (30 MHz at most with the doubler on).
3. Check [CE](glossary.md#ce). `synth.is_powered` should be `True`; with CE
   low the chip is powered down.
4. Check the [charge-pump](glossary.md#charge-pump) current. It must suit
   your [loop filter](glossary.md#loop-filter). The default, code 7, suits
   the [evaluation board](glossary.md#evaluation-board)
   ([Hardware](hardware.md#loop-filter-and-charge-pump-current)).
5. Give it time. After a large jump, especially one that changes the [RF
   divider](glossary.md#rf-divider), lock can take hundreds of microseconds.
   Use `wait_locked()` rather than a single `is_locked()` read.

## Locked, but the wrong frequency

- `ref_hz` does not match the real reference. The [PLL](glossary.md#pll)
  locks just as well to the wrong value.
- Look at `synth.achieved_hz` and `result.error_hz`: the target may not be
  exactly reachable ([Frequency
  planning](frequency-planning.md#exact-and-nearest-frequencies)).

## `wait_locked()` returns False

- MUXOUT is not wired, or `muxout` was changed from digital lock detect. In
  both cases `is_locked()` raises `RuntimeError`.
- The loop is not locking; see the first section.

## Errors when setting a frequency

| The message mentions | Meaning |
|----------------------|---------|
| `outside [...]` (`FrequencyOutOfRangeError`) | Below 34.375 MHz (ADF4351) or 137.5 MHz (ADF4350), or above 4.4 GHz |
| `f_pfd=... exceeds` (`NoSolutionError`) | fPFD is over 32 MHz: raise `r_counter`, or turn off the doubler |
| `must be an integer` (`TypeError`) | A float such as `433.92e6`; write `433_920_000` |
| `low-spur noise mode needs MOD >= 50` | Set `mod=50` in the same `configure()` call that turns on [low-spur mode](glossary.md#low-spur-mode) |
| `phase=... must be less than MOD` | A [phase](glossary.md#phase) you set is too large for the new [MOD](symbols.md#mod) |
| `power_up() needs frequency_hz` | Pass `frequency_hz=` the first time |

## Sweeps

`DividerCrossingError` means the range needs more than one RF divider.
Narrow it as the message suggests, or pass `allow_divider_change=True`.

If [hops](glossary.md#hop) are slower than expected, check
`table.channel_step_hz`. If it is 0, the entries use different MODs and each
hop also writes [R1](symbols.md#rn-and-dbn). Choose a step that divides
evenly ([Sweeps](sweeps.md#how-mod-is-chosen)).

If `max_error_hz` is exceeded, some targets cannot be reached that closely
with your reference. Change the step or the reference path.
