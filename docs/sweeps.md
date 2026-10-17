# Sweeps and frequency tables

For sweeps and frequency hopping, solve all the frequencies once and then
play them back. Each hop then only sends the registers that change, often a
single word.

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

- `allow_divider_change=True` to allow frequencies that need different RF
  dividers. Without it, a table that crosses a divider boundary raises
  `DividerOctaveCrossingError`, whose message suggests ranges that stay on
  one divider.
- `max_error_hz=` to raise `ValueError` if any entry would be further than
  this from its target.

Building a table does not change the synthesizer or touch the chip, so you
can build tables at start-up and play them later. A table belongs to the
synthesizer it was built with.

### How MOD is chosen

The register that holds MOD (R1) does not need rewriting if MOD stays the
same, so the table tries to use one MOD for every entry that shares an RF
divider:

- If one MOD of 4095 or less hits every point exactly, all those entries use
  it. Every point is then exact and each in-band hop is a single R0 write.
  For example, 190–210 MHz in 2 MHz steps from a 10 MHz reference uses
  MOD 5.
- Otherwise each entry gets its own best MOD. Accuracy is the same as
  `set_frequency()`, but a hop between different MODs also writes R1.

`table.channel_step_hz` gives the channel spacing when the whole table
shares one MOD and divider, and 0 otherwise. Each entry has `target_hz`,
`achieved_hz`, `error_hz`, `exact`, `rf_divider`, `fields` and
`divider_boundary` (True for the first entry after a divider change).

## Playing a table

```python
timeouts = synth.play(table, dwell_us=1_000, wait_for_lock=True, cycles=3)
```

| Argument | Default | Meaning |
|----------|---------|---------|
| `dwell_us` | 0 | Wait after each in-band hop |
| `wait_for_lock` | False | Wait for lock detect after each in-band hop |
| `boundary_dwell_us` | 500000 | Wait after a hop that changes RF divider |
| `require_lock` | False | Raise `LockTimeoutError` if a lock wait times out |
| `cycles` | 1 | Passes through the table |

`play()` returns the number of lock waits that timed out. It raises CE first
if the chip is powered down.

To do something at each point, step through the table yourself:

```python
for i in range(len(table)):
    entry = synth.play_step(table, i)
    synth.wait_locked()
    measure(entry.achieved_hz)
```

Each hop compares the entry's register words with what was last written to
the chip and sends only the differences. That means mixing `play_step()`
with `set_frequency()`, `mute()` or other calls is safe.

### Settings stay yours

Table entries are encoded from the synthesizer's own settings: output
power, charge-pump current, aux output and so on. If you change a setting
after building the table (for example `synth.set_output_power(...)`), the
next hop re-encodes the table with the new setting first.

Tables also turn on double buffering of the RF divider (R2 DB13), so a
divider change takes effect together with the new frequency.

## Divider boundaries

When a hop changes the RF divider, the VCO jumps to a different band and
takes longer to settle. `play()` then waits for lock detect (if MUXOUT is
wired) and dwells for `boundary_dwell_us`. Without MUXOUT it just dwells.

The ADF4351 changes divider at 2200 MHz, 1100 MHz, 550 MHz, 275 MHz,
137.5 MHz and 68.75 MHz; the ADF4350 at the first four of those.

## Speed

On the hop itself the library does very little work: for an in-band hop,
comparing six words and sending one. Most of the time is the SPI write and
any dwell. Solving happens when the table is built, at roughly 70 µs per
entry on the MicroPython Unix port; expect several times that on a
microcontroller.
