# Bench validation

[`examples/validate.py`](../../examples/validate.py) holds a catalog of bench
checks. Each run programs one case and prints the target, the achieved
frequency, and the lock state; you confirm the output with an instrument.
The script does not decide pass or fail.

## Running it

Set `SELECT` at the top of the script (default `scope_200mhz`), or pass a
case name as the first argument. `list` prints the names. It assumes a
10 MHz reference and the reference pin map in [Hardware](../hardware.md).

## Cases

| Case | Output | Instrument | Checks |
|------|--------|------------|--------|
| `scope_50mhz` … `scope_250mhz` | 50–250 MHz | Oscilloscope | Basic lock across several dividers |
| `cross_part_scope_137p5mhz` | 137.5 MHz | Oscilloscope | Lowest ADF4350 output; integer-N |
| `adf4351_scope_equiv_132p0375mhz` | 132.0375 MHz | Oscilloscope | Data sheet PLL settings at ÷32 |
| `golden_2112p6mhz` | 2112.6 MHz | Counter or spectrum analyzer | Data sheet worked example |
| `adf4351_prescaler_edge_3600mhz` | 3.6 GHz | Counter or spectrum analyzer | Highest VCO with the 4/5 prescaler |
| `adf4351_prescaler_over_3700mhz` | 3.7 GHz | Counter or spectrum analyzer | 8/9 prescaler |
| `narrow_band_sweep` | 140–145 MHz, 1 MHz steps | Oscilloscope | Table playback within one divider band, lock at each step |

## What a pass looks like

- MUXOUT reports high within the timeout.
- The instrument reads the printed `Achieved` frequency, within its
  accuracy and the reference's accuracy.

Lock detect alone is not enough: it shows the loop settled, not that the
frequency is right (for example if `REF_HZ` is wrong).
