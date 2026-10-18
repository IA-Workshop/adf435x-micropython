# Frequency planning

This page explains how the library turns a target frequency into
[PLL](glossary.md#pll) settings, and what limits apply. You can try all of
it on a PC, because `solve()` needs no hardware. The letters in the formulas
are defined on the [symbols](symbols.md) page.

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

- The [reference](glossary.md#reference) ([REFIN](symbols.md#refin)) passes
  through the optional doubler, the [R counter](glossary.md#r-counter) and
  the optional divide-by-2 to reach the [PFD](glossary.md#pfd) at
  [fPFD](symbols.md#fpfd).
- The [VCO](glossary.md#vco) runs from 2.2 GHz to 4.4 GHz. The solver picks
  the smallest [RF divider](glossary.md#rf-divider) that puts the VCO in
  that range, so each output frequency has one divider.
- [N](symbols.md#n) is [INT](symbols.md#int) plus the fraction
  [FRAC](symbols.md#frac) / [MOD](symbols.md#mod), with MOD from 2 to 4095.
  FRAC = 0 is [integer-N](glossary.md#integer-n) mode; anything else is
  [fractional-N](glossary.md#fractional-n).
- The output can move in steps of fPFD ÷ MOD ÷ RF divider.

An example, the data sheet's worked example: a 10 MHz reference gives a 10
MHz fPFD. For 2112.6 MHz the solver uses divide-by-2, so the VCO runs at
4225.2 MHz and N = 422.52 = 422 + 13/25.

## Exact and nearest frequencies

The solver uses exact whole-number arithmetic, so the numbers it reports
match the hardware:

- `result.exact` is `True` when the output is exactly the target.
- Otherwise the solver picks the nearest output it can reach. `achieved_hz`
  is that output rounded to the nearest hertz, and `error_hz = target -
  achieved_hz`.
- When several MOD values give the same error, to the nearest hertz, the
  smallest MOD wins. Smaller MOD values usually mean weaker
  [spurs](glossary.md#spur).
- `SolveOptions(exact=True)` makes `solve()` raise `ExactFrequencyError`
  instead of settling for the nearest frequency.

A target is exactly reachable only when N = target × RF divider ÷ fPFD is a
fraction with a denominator of 4095 or less. With a 10 MHz fPFD, for
example, every multiple of 2 kHz below 2.2 GHz (RF divider 2 or more) is
exact, but above 2.2 GHz not all are. Between such points the nearest output
can be more than a kilohertz away at divide-by-1.

## Choosing a channel step

To force a particular [channel step](glossary.md#channel-step) at the
output, pass `channel_step_hz`:

```python
from adf435x import SolveOptions

opts = SolveOptions(channel_step_hz=200_000)
result = solve(2_112_600_000, 10_000_000, ADF4351, options=opts)   # MOD = 25
```

MOD becomes fPFD ÷ (step × RF divider), which must be a whole number from 2
to 4095; otherwise `solve()` raises `ValueError`. The other options are:

| Option | Effect |
|--------|--------|
| `mod=` | Use this MOD as given (never reduced) |
| `rf_divider=` | Use this RF divider instead of choosing one |
| `mod_min=` | Smallest MOD to use (the synthesizer passes 50 in [low-spur mode](glossary.md#low-spur-mode)) |
| `exact=True` | Raise unless the output is exactly the target |

## Choosing the reference path

| Setting | Constructor argument | Range |
|---------|----------------------|-------|
| [Reference doubler](glossary.md#reference-doubler-and-divide-by-2) | `doubler=True` | REFIN must be 30 MHz or less |
| R counter | `r_counter=` | 1 to 1023 |
| Divide-by-2 | `rdiv2=True` | |

fPFD must be at most 32 MHz, the limit for fractional-N mode. A higher fPFD
gives finer output steps for the same MOD, lowers [phase
noise](glossary.md#phase-noise) close to the output frequency, and allows a
wider [loop filter](glossary.md#loop-filter). fPFD does not have to be a
whole number of hertz: a 25 MHz reference with R = 3 (8.333... MHz) works,
and the solver keeps the exact value.

The library also picks the [band-select](glossary.md#band-select) clock: at
most 125 kHz in normal mode, or, on the ADF4351 when fPFD is above 125 kHz,
up to 500 kHz in fast mode. Since the ADF4350 has no fast mode, its fPFD is
limited to 31.875 MHz (125 kHz × 255, the largest divider).

## Integer-N and fractional-N settings

The solver sets the lock-detect and spur-related bits as the data sheet
recommends:

| Mode | [Lock detect](glossary.md#lock-detect) ([LDF, LDP](glossary.md#ldf-and-ldp)) | [ABP](glossary.md#abp) (ADF4351) | [Charge cancel](glossary.md#charge-cancellation) (ADF4351) |
|------|------------------------|---------------|-------------------------|
| Fractional-N (FRAC > 0) | 40 cycles, 10 ns | 6 ns | off |
| Integer-N (FRAC = 0) | 5 cycles, 6 ns | 3 ns | on |

The ADF4350 has a fixed antibacklash pulse and no charge cancellation.

## Prescaler

When the VCO is above 3.6 GHz on the ADF4351 (3.0 GHz on the ADF4350), the
[prescaler](glossary.md#prescaler) must be 8/9, which needs INT ≥ 75. Below
that, the 4/5 prescaler allows INT ≥ 23. The solver handles this for you;
you only need to think about it if you set [registers](glossary.md#register)
by hand.

## Low-spur noise mode

[Low-spur mode](glossary.md#low-spur-mode)
(`noise_mode=consts.REG2_LOW_SPUR`) gives weaker spurs at the cost of more
phase noise, and needs MOD ≥ 50. In that mode the synthesizer asks the
solver for a MOD of at least 50. When you switch to low-spur mode, set MOD
in the same call:

```python
synth.regfile.configure(noise_mode=consts.REG2_LOW_SPUR, mod=50)
synth.set_frequency(synth.frequency)
```
