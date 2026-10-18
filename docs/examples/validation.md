# Bench validation

[`examples/validate.py`](../../examples/validate.py) holds a set of bench
checks. Each run programs one case and prints the target, the achieved
frequency and the [lock](../glossary.md#lock) state. You confirm the output
with an instrument; the script does not decide pass or fail.

## Running it

Set `SELECT` at the top of the script (default `scope_200mhz`), or pass a
case name as the first argument. `list` prints the names. The script assumes
a 10 MHz [reference](../glossary.md#reference) and the reference pin map in
[Hardware](../hardware.md#reference-setup).

## Cases

| Case | Output | Instrument | Checks |
|------|--------|------------|--------|
| `scope_50mhz` to `scope_250mhz` | 50 to 250 MHz | Oscilloscope | Basic lock with several [RF dividers](../glossary.md#rf-divider) |
| `cross_part_scope_137p5mhz` | 137.5 MHz | Oscilloscope | Lowest ADF4350 output; [integer-N](../glossary.md#integer-n) |
| `adf4351_scope_equiv_132p0375mhz` | 132.0375 MHz | Oscilloscope | Data sheet [PLL](../glossary.md#pll) settings at ÷32 |
| `golden_2112p6mhz` | 2112.6 MHz | [Counter](../glossary.md#counter) or [spectrum analyzer](../glossary.md#spectrum-analyzer) | Data sheet worked example |
| `adf4351_prescaler_edge_3600mhz` | 3.6 GHz | Counter or spectrum analyzer | Highest [VCO](../glossary.md#vco) frequency with the 4/5 [prescaler](../glossary.md#prescaler) |
| `adf4351_prescaler_over_3700mhz` | 3.7 GHz | Counter or spectrum analyzer | 8/9 prescaler |
| `narrow_band_sweep` | 140 to 145 MHz, 1 MHz steps | Oscilloscope | Table playback within one divider band, with lock at each step |

## What a pass looks like

- [MUXOUT](../glossary.md#muxout) reports high within the timeout.
- The instrument reads the printed `Achieved` frequency, within its own
  accuracy and the reference's accuracy.

Lock detect alone is not enough. It shows the loop settled, not that the
frequency is right; for example, the loop still locks if `REF_HZ` is wrong.
