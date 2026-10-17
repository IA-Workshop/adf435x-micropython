# Frequency planning

How the library turns a target frequency into PLL settings, and what limits
apply. You can try all of this on a PC: `solve()` needs no hardware.

```python
from adf435x import ADF4351, solve

result = solve(2_112_600_000, 10_000_000, ADF4351)
print(result.fields["int_n"], result.fields["frac"], result.fields["mod"])  # 422 13 25
print(result.achieved_hz, result.error_hz, result.exact)                   # 2112600000 0 True
```

## The signal chain

```text
REFIN --> [x2 doubler] --> [÷R] --> [÷2] --> fPFD
fVCO = fPFD × N,   N = INT + FRAC / MOD
fOUT = fVCO ÷ RF divider   (RF divider = 1, 2, 4, ... 64)
```

- The VCO runs from 2.2 to 4.4 GHz. The solver picks the smallest RF divider
  that puts the VCO in that range, so each output frequency has one divider.
- **N** is INT plus a fraction FRAC/MOD, with MOD from 2 to 4095. FRAC = 0
  is *integer-N* mode; anything else is *fractional-N*.
- The output can move in steps of fPFD ÷ MOD ÷ RF divider.

Example (the data sheet's worked example): a 10 MHz reference gives a
10 MHz fPFD. For 2112.6 MHz the solver uses divide-by-2, so the VCO runs at
4225.2 MHz and N = 422.52 = 422 + 13/25.

## Exact and nearest frequencies

The solver uses exact integer arithmetic, so its reported numbers match the
hardware:

- `result.exact` is `True` when the output is exactly the target.
- Otherwise the solver picks the nearest output it can reach.
  `achieved_hz` is that output rounded to the nearest hertz, and
  `error_hz = target - achieved_hz`.
- When several MOD values give the same error, to the nearest hertz, the
  smallest MOD wins. Smaller MOD values generally mean lower fractional
  spurs.
- `SolveOptions(exact=True)` makes `solve()` raise `ExactFrequencyError`
  instead of settling for the nearest frequency.

A target is exactly reachable only when N = target × divider ÷ fPFD is a
fraction with a denominator of 4095 or less. With a 10 MHz fPFD, for
example, every multiple of 2 kHz below 2.2 GHz (RF divider 2 or more) is
exact, but above 2.2 GHz not all are. Between such points the nearest
output can be more than a kilohertz away at divide-by-1.

## Choosing a channel step

To force a particular channel spacing at the output, pass `channel_step_hz`:

```python
from adf435x import SolveOptions

opts = SolveOptions(channel_step_hz=200_000)
result = solve(2_112_600_000, 10_000_000, ADF4351, options=opts)   # MOD = 25
```

MOD becomes fPFD ÷ (step × RF divider), which must be a whole number from 2
to 4095; otherwise `solve()` raises `ValueError`. Other options:

| Option | Effect |
|--------|--------|
| `mod=` | Use this MOD as given (never reduced) |
| `rf_divider=` | Use this RF divider instead of choosing one |
| `mod_min=` | Smallest MOD to use (the synthesizer passes 50 in low-spur mode) |
| `exact=True` | Raise unless the output is exactly the target |

## Choosing the reference path

| Setting | Constructor argument | Range |
|---------|----------------------|-------|
| Reference doubler | `doubler=True` | REFIN must be ≤ 30 MHz |
| R counter | `r_counter=` | 1 to 1023 |
| Divide-by-2 | `rdiv2=True` | |

fPFD must be at most 32 MHz (the fractional-N limit). A higher fPFD gives
finer output steps for the same MOD, lowers in-band phase noise, and allows
a wider loop filter. It does not have to be a whole number of hertz: a
25 MHz reference with R = 3 (8.333... MHz) works, and the solver keeps the
exact value.

The library also picks the band-select clock: at most 125 kHz in normal
mode, or, on the ADF4351 when fPFD is above 125 kHz, up to 500 kHz in fast
mode. On the ADF4350 this limits fPFD to 31.875 MHz.

## Integer-N and fractional-N settings

The solver sets the lock-detect and spur-related bits as the data sheet
recommends:

| Mode | Lock detect (LDF, LDP) | ABP (ADF4351) | Charge cancel (ADF4351) |
|------|------------------------|---------------|-------------------------|
| Fractional-N (FRAC > 0) | 40 cycles, 10 ns | 6 ns | off |
| Integer-N (FRAC = 0) | 5 cycles, 6 ns | 3 ns | on |

The ADF4350 has a fixed antibacklash pulse and no charge cancellation.

## Prescaler

Above 3.6 GHz VCO on the ADF4351 (3.0 GHz on the ADF4350) the prescaler
must be 8/9, which needs INT ≥ 75; below that the 4/5 prescaler allows
INT ≥ 23. The solver handles this; it only matters if you set registers by
hand.

## Low-spur noise mode

Low-spur mode (`noise_mode=consts.REG2_LOW_SPUR`) trades phase noise for
lower spurs and needs MOD ≥ 50. The synthesizer asks the solver for at least
50 automatically in that mode. When you switch to low-spur mode, set MOD in
the same call:

```python
synth.regfile.configure(noise_mode=consts.REG2_LOW_SPUR, mod=50)
synth.set_frequency(synth.frequency)
```
