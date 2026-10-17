# Fixed-frequency example

[`examples/fixed_frequency.py`](../../examples/fixed_frequency.py) programs
one frequency, waits for lock, and prints what to expect on the output.

## Before you run it

- Library on the board ([Development](../development.md)).
- Wiring as in [Hardware](../hardware.md#reference-setup), or edit `PINS`.
- `REF_HZ` set to your reference frequency (10 MHz on the evaluation board).
- `TARGET_FREQ_HZ` set to the frequency you want (default 200 MHz, which a
  200 MHz oscilloscope can show).

## What it does

```python
synth = ADF435xSynthesizer(device, ADF4351, ref_hz=REF_HZ)
synth.power_up(frequency_hz=TARGET_FREQ_HZ)
locked = synth.wait_locked(timeout_us=500_000)
```

`power_up()` solves the PLL settings and writes all six registers;
`wait_locked()` polls MUXOUT for up to half a second.

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

## Variations

- `TARGET_FREQ_HZ = 137_500_000`: the lowest ADF4350 output, integer-N, on
  both parts.
- `TARGET_FREQ_HZ = 2_112_600_000`: the data sheet's worked example (needs a
  counter or spectrum analyzer).
