# Fixed-frequency example

[`examples/fixed_frequency.py`](../../examples/fixed_frequency.py) programs
one frequency, waits for [lock](../glossary.md#lock), and prints what to
expect on the output.

## Before you run it

- Put the library on the board ([Development](../development.md)).
- Wire the board as in the [reference
  setup](../hardware.md#reference-setup), or edit `PINS`.
- Set `REF_HZ` to your [reference](../glossary.md#reference) frequency (10
  MHz on the [evaluation board](../glossary.md#evaluation-board)).
- Set `TARGET_FREQ_HZ` to the frequency you want. The default, 200 MHz, is
  low enough for a 200 MHz oscilloscope to show.

## What it does

```python
synth = ADF435xSynthesizer(device, ADF4351, ref_hz=REF_HZ)
synth.power_up(frequency_hz=TARGET_FREQ_HZ)
locked = synth.wait_locked(timeout_us=500_000)
```

`power_up()` works out the [PLL](../glossary.md#pll) settings and writes all
six [registers](../glossary.md#register). `wait_locked()` then watches
[MUXOUT](../glossary.md#muxout) for up to half a second.

## Expected output

```text
Powering up at 200.000000 MHz
Target:    200000000 Hz (200.000000 MHz)
Achieved:  200000000 Hz (200.000000 MHz)
MUXOUT:    high
Probe RFOUTA with scope or counter.
```

If `MUXOUT` reports `not high within timeout`, see
[Troubleshooting](../troubleshooting.md#no-output-or-never-locks).

## Other targets to try

- `TARGET_FREQ_HZ = 137_500_000`: the lowest output of the ADF4350. It is
  [integer-N](../glossary.md#integer-n) on both parts.
- `TARGET_FREQ_HZ = 2_112_600_000`: the data sheet's worked example. You
  need a frequency [counter](../glossary.md#counter) or [spectrum
  analyzer](../glossary.md#spectrum-analyzer) to see it.
