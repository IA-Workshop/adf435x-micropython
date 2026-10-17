# Symbols

The letters and names used in formulas on these pages. They follow the
ADF4350 and ADF4351 data sheets. For words such as PLL or VCO, see the
[glossary](glossary.md).

The whole chain, from reference to output:

```text
fPFD = REFIN × (1 + D) ÷ (R × (1 + T))
N    = INT + FRAC ÷ MOD
fVCO = fPFD × N
fOUT = fVCO ÷ RF divider
```

## REFIN

The reference frequency: the clock fed into the chip's REFIN pin, 10 MHz to
250 MHz (at most 30 MHz with the doubler on). REFIN is also the pin's name.
In the library it is `ref_hz`.

## D

The reference doubler bit: 1 doubles REFIN before the R counter, 0 leaves it
alone. In the library it is `doubler`.

## R

The R counter value: the reference is divided by R, a whole number from 1 to
1023. In the library it is `r_counter`.

## T

The reference divide-by-2 bit: 1 halves the signal after the R counter, 0
leaves it alone. In the library it is `rdiv2`.

## fPFD

The phase frequency detector frequency: how many times per second the chip
compares its divided-down VCO with the reference. fPFD = REFIN × (1 + D) ÷
(R × (1 + T)). The library keeps it at or below 32 MHz, the limit for
fractional-N mode. In the library it is `f_pfd_hz`.

## N

The feedback divide ratio: the VCO frequency divided by fPFD. N = INT + FRAC
÷ MOD, so N can be a fraction such as 422.52.

## INT

The whole-number part of N. Its smallest legal value depends on the
prescaler: 23 with the 4/5 prescaler, 75 with 8/9. The largest is 65535. In
the library it is `int_n`.

## FRAC

The numerator of the fractional part of N, from 0 to MOD − 1. FRAC = 0 means
integer-N mode. In the library it is `frac`.

## MOD

The modulus: the denominator of the fractional part of N, from 2 to 4095. A
larger MOD allows finer frequency steps. In the library it is `mod`.

## fVCO

The VCO frequency: fVCO = fPFD × N. It is always from 2.2 GHz to 4.4 GHz. In
the library it is `vco_hz`.

## RF divider

The output divider after the VCO: 1, 2, 4, 8, 16, 32 or 64 (the ADF4350
stops at 16). In formulas it stands for the divider's value. In the library
it is `rf_divider`.

## fOUT

The output frequency: fOUT = fVCO ÷ RF divider. The data sheets call it
RFOUT. In the library it is `achieved_hz`.

## Output step

The smallest change in fOUT for a given MOD: fPFD ÷ (MOD × RF divider). In
the library, `channel_step_hz` sets it.

## Rn and DBn

R0 to R5 are the chip's six registers. DBn is bit n of a register word, from
DB0 (lowest) to DB31, so "R2 DB13" is bit 13 of register R2.
