# Sweeps and frequency tables

To [sweep](glossary.md#sweep) or [hop](glossary.md#hop) between frequencies,
solve all of them once and then play them back. Each hop then sends only the
[registers](glossary.md#register) that change, often a single word.

```python
from adf435x import FrequencyTable

table = FrequencyTable.from_range(synth, 190_000_000, 210_000_000, 2_000_000)
print(len(table), "entries, worst error", table.max_error_hz, "Hz")
synth.play(table, dwell_us=500_000)
```

## Building a table

| Builder | Entries |
|---------|---------|
| `FrequencyTable.from_range(synth, lower_hz, upper_hz, step_hz)` | `lower_hz`, `lower_hz + step_hz`, ... and `upper_hz` itself |
| `FrequencyTable.from_frequencies(synth, [hz, ...])` | Your list, in your order |

Both accept:

- `allow_divider_change=True`, to allow frequencies that need different [RF
  dividers](glossary.md#rf-divider). Without it, a table that crosses a
  [divider boundary](glossary.md#divider-boundary) raises
  `DividerOctaveCrossingError`, and its message suggests ranges that stay on
  one divider.
- `max_error_hz=`, to raise `ValueError` if any entry would be further than
  this from its target.

Building a table does not change the synthesizer or touch the chip, so you
can build tables at start-up and play them later. A table belongs to the
synthesizer it was built with.

### How MOD is chosen

The register that holds [MOD](symbols.md#mod), [R1](symbols.md#rn-and-dbn),
does not need rewriting if MOD stays the same. So the table tries to use one
MOD for every entry that shares an RF divider:

- If one MOD of 4095 or less hits every point exactly, all those entries use
  it. Every point is then exact, and each hop within the band is a single R0
  write. For example, 190 to 210 MHz in 2 MHz steps from a 10 MHz
  [reference](glossary.md#reference) uses MOD 5.
- Otherwise each entry gets its own best MOD. Accuracy is the same as with
  `set_frequency()`, but a hop between different MODs also writes R1.

`table.channel_step_hz` gives the [channel step](glossary.md#channel-step)
when the whole table shares one MOD and one divider, and 0 otherwise. Each
entry has `target_hz`, `achieved_hz`, `error_hz`, `exact`, `rf_divider`,
`fields` and `divider_boundary` (True for the first entry after a divider
change).

## Playing a table

```python
timeouts = synth.play(table, dwell_us=1_000, wait_for_lock=True, cycles=3)
```

| Argument | Default | Meaning |
|----------|---------|---------|
| `dwell_us` | 0 | [Dwell](glossary.md#dwell) after each in-band hop |
| `wait_for_lock` | False | Wait for [lock detect](glossary.md#lock-detect) after each in-band hop |
| `boundary_dwell_us` | 500000 | Dwell after a hop that changes RF divider |
| `require_lock` | False | Raise `LockTimeoutError` if a lock wait times out |
| `cycles` | 1 | Number of passes through the table |

`play()` returns the number of lock waits that timed out. If the chip is
powered down, it raises [CE](glossary.md#ce) first.

To do something at each point, step through the table yourself:

```python
for i in range(len(table)):
    entry = synth.play_step(table, i)
    synth.wait_locked()
    measure(entry.achieved_hz)
```

Each hop compares the entry's register words with what was last written to
the chip, and sends only the differences. That makes it safe to mix
`play_step()` with `set_frequency()`, `mute()` or other calls.

### Settings stay yours

Table entries are encoded from the synthesizer's own settings: output power,
[charge-pump](glossary.md#charge-pump) current, [aux
output](glossary.md#aux-output) and so on. If you change a setting after
building the table (for example with `synth.set_output_power(...)`), the
next hop first re-encodes the table with the new setting.

Tables also turn on [double buffering](glossary.md#double-buffering) of the
RF divider (R2 [DB13](symbols.md#rn-and-dbn)), so a divider change takes
effect at the same moment as the new frequency.

## Divider boundaries

When a hop changes the RF divider, the [VCO](glossary.md#vco) jumps to a
different band and takes longer to settle. `play()` then waits for lock
detect (if [MUXOUT](glossary.md#muxout) is wired) and dwells for
`boundary_dwell_us`. Without MUXOUT it only dwells.

The ADF4351 changes divider at 2200 MHz, 1100 MHz, 550 MHz, 275 MHz, 137.5
MHz and 68.75 MHz; the ADF4350 at the first four of those.

## Speed

On the hop itself the library does very little: for a hop within one band it
compares six words and sends one. Most of the time goes to the
[SPI](glossary.md#spi) write and any dwell. Solving happens when the table
is built, at roughly 70 µs per entry on the [MicroPython Unix
port](glossary.md#micropython); expect several times that on a
microcontroller.
