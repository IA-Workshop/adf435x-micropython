# Glossary

Words and abbreviations used in these docs, in alphabetical order. Letters
used in formulas, such as fPFD, N and MOD, are on the [symbols
page](symbols.md).

## ABP

Antibacklash pulse. A short pulse the phase frequency detector always sends,
so the charge pump reacts even to tiny phase errors. The ADF4351 uses 6 ns
for fractional-N and 3 ns for integer-N; the ADF4350's is fixed. Library
field: `abp`.

## Aux output

The second RF output, RFOUTB. It is off by default. Library fields:
`aux_enable`, `aux_power`, `aux_select`.

## Band select

Every time R0 is written, the chip picks which of its VCO's many frequency
bands to use. This takes 10 cycles of the band-select clock, which must run
at 125 kHz or less (or up to 500 kHz in the ADF4351's fast mode). The
library sets the clock for you. Library fields: `band_clk_div`,
`band_clk_mode`.

## CE

Chip enable, a pin. High powers the chip up. Low powers it down, and the
chip keeps its register contents. Library: `power_up()`, `power_down()`.

## Channel step

The spacing between neighboring output frequencies in a sweep or channel
plan, such as 25 kHz. See [output step](symbols.md#output-step).

## Charge cancellation

An ADF4351 feature that reduces spurs in integer-N mode. Library field:
`charge_cancel`.

## Charge pump

The part of the PLL that pushes small pulses of current into the loop filter
to raise or lower the VCO's control voltage. The size of the pulses, the CP
current, must suit the loop filter. Library field: `cp_current_code` (0 to
15; 7 suits the evaluation board).

## Counter

Short for frequency counter: an instrument that measures a signal's
frequency directly.

## CPython

The standard Python interpreter that runs on a PC. The library's tests run
on it.

## dBm

Power compared with one milliwatt: 0 dBm is 1 mW, +5 dBm is about 3.2 mW and
−4 dBm is about 0.4 mW.

## Divider boundary

A frequency where the RF divider changes, such as 2200 MHz on both parts.
Each RF divider covers one octave (a factor of two in frequency).

## Double buffering

Some register fields do not take effect when written. They wait for the next
write to R0, so several changes land at the same moment. These are the phase
and MOD (R1); the doubler, divide-by-2, R counter and CP current (R2); and
the RF divider (R4), but only when the `double_buffer` field is on (data
sheet p.12).

## Dwell

How long a sweep stays on one frequency before moving to the next.

## Evaluation board

The Analog Devices test board for the chip. The examples assume its 10 MHz
reference oscillator and its loop filter.

## Exact

A result is exact when the output frequency equals the target exactly, with
no error at all. Library: `result.exact`.

## Fractional-N

The mode where FRAC is not 0, so N has a fractional part. It gives fine
frequency steps but can add spurs. Compare [integer-N](#integer-n).

## Frequency table

A list of frequencies the library has solved in advance, so a sweep can jump
between them quickly. Library: `FrequencyTable`.

## GPIO

General-purpose input/output: a microcontroller pin that a program can set
high or low, or read.

## Hop

One move from one frequency to the next in a sweep.

## Integer-N

The mode where FRAC is 0, so N is a whole number. It usually has fewer spurs
than fractional-N, but the VCO can then only move in steps of a whole fPFD.

## LD pin

A lock-detect output pin, separate from MUXOUT. The library reads MUXOUT
instead; R5 sets the LD pin's mode (library field `lock_pin`).

## LDF and LDP

The lock-detect settings. LDF is the count: lock is reported after 40
(fractional-N) or 5 (integer-N) phase comparisons in a row that line up. LDP
is how closely they must line up: 10 ns or 6 ns. The library picks both.
Library fields: `ldf`, `ldp`.

## LE

Load enable, a pin. While LE is low, the chip shifts in data bits; a rising
edge on LE then copies the 32 bits into the register that the low three bits
name.

## Lock

The PLL is locked when the divided-down VCO matches the reference in
frequency and phase, so the output stays at the programmed frequency.

## Lock detect

A signal from the chip that says the PLL is locked. The library reads the
digital lock detect signal on MUXOUT. Library: `is_locked()`,
`wait_locked()`.

## Loop filter

The resistors and capacitors on the board between the charge pump and the
VCO's tuning input. They turn the charge pump's pulses into an even voltage.
Their values decide how fast the PLL locks and how clean the output is.

## Low-spur mode

A noise mode that gives fewer spurs and more phase noise. It needs MOD to be
at least 50. The default is low-noise mode. Library field: `noise_mode`.

## MCU

Microcontroller unit: the small computer on your MicroPython board.

## MicroPython

A version of Python for microcontrollers. The Unix port is a build of
MicroPython that runs on a PC, used here for testing.

## mip

MicroPython's package installer. A board with a network connection can use
it to download the library.

## MOSI and SCK

The two SPI lines the library uses: MOSI (data from the board to the chip,
wired to DATA) and SCK (the clock, wired to CLK).

## MSB

Most significant bit: the highest bit of a word. "MSB first" means that bit
is sent first.

## MUXOUT

A chip output pin that can show one of several internal signals. The library
uses it for digital lock detect. Library field: `muxout`.

## Octave

A factor of two in frequency, such as 1100 MHz to 2200 MHz.

## Phase

A 12-bit R1 field that sets the output's phase offset. It must be less than
MOD and is 1 by default. Library field: `phase`.

## Phase noise

Small random wobbles in the timing of the output signal. On a spectrum
analyzer it shows as a skirt of noise around the output frequency.

## PFD

Phase frequency detector. It compares the reference (after the R counter)
with the divided-down VCO and drives the charge pump to correct any
difference. It runs at [fPFD](symbols.md#fpfd).

## PLL

Phase-locked loop. A circuit that holds an oscillator at an exact multiple
of a reference clock. It divides the oscillator's output down, compares it
with the reference, and steers the oscillator until the two match.

## Prescaler

A fast divider at the start of the feedback divider, set to divide by 4/5 or
8/9. The 8/9 setting is needed when the VCO is above 3.6 GHz (ADF4351) or
3.0 GHz (ADF4350), and it raises the smallest legal INT from 23 to 75.
Library field: `prescaler`.

## R counter

The reference divider: it divides the reference by [R](symbols.md#r), from 1
to 1023, before the PFD. Library field: `r_counter`.

## Reference

The clock the chip compares its VCO against, fed to the REFIN pin. It is
usually a crystal oscillator. The output is only as accurate as the
reference. Library: `ref_hz`.

## Reference doubler and divide-by-2

Two optional stages around the R counter: the doubler multiplies the
reference by 2 before it, and divide-by-2 halves the signal after it.
Library fields: `doubler`, `rdiv2`.

## Register

One of the chip's six 32-bit settings stores, R0 to R5. The library always
writes a whole register at once, as one 32-bit word.

## Register file

The library's copy of the six register words: the ones it wants on the chip,
and the ones it last wrote. Library: `ADF435xRegisterFile`.

## RF divider

The output divider after the VCO. Dividing by 1, 2, 4 and so on up to 64 (16
on the ADF4350) reaches frequencies below the VCO's 2.2 GHz. Library field:
`rf_divider`.

## RFOUTA

The chip's main RF output. RFOUTB is the [aux output](#aux-output).

## Solver

The library code that turns a target frequency into PLL settings. Library:
`solve()`.

## Spectrum analyzer

An instrument that shows signal power against frequency. It can show the
output, its spurs and its phase noise.

## SPI

Serial peripheral interface: a way to send data one bit at a time on a data
line, timed by a clock line. The chip uses mode 0: the clock rests low and
data is read on its rising edge.

## Spur

A small unwanted signal at a frequency near the output. Fractional-N mode
tends to produce more of them.

## Stale register

A register whose wanted word differs from the word last written to the chip.
Only stale registers are written.

## Sweep

Stepping the output through a list of frequencies, one after another.

## VCO

Voltage-controlled oscillator: an oscillator whose frequency follows a
control voltage. The ADF4350 and ADF4351 have one built in that covers 2.2
GHz to 4.4 GHz, split into many smaller bands.
