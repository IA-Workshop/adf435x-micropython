# adf435x documentation

adf435x is a [MicroPython](glossary.md#micropython) library for the Analog
Devices ADF4350 and ADF4351. These chips are [PLL](glossary.md#pll)
synthesizers: from a fixed [reference](glossary.md#reference) clock they
make an output at a frequency you choose, from 34.375 MHz (137.5 MHz on the
ADF4350) up to 4.4 GHz.

New words are explained in the [glossary](glossary.md), and the letters used
in formulas (fPFD, N, MOD and so on) on the [symbols](symbols.md) page.

## Start here

1. [Quickstart](quickstart.md): wire the board, set one frequency, check for
   [lock](glossary.md#lock).
2. [Hardware](hardware.md): the signals, [SPI](glossary.md#spi) settings,
   timing and a reference pin map.
3. [API guide](api-guide.md): which class to use, and how each one behaves.

## Guides

- [Frequency planning](frequency-planning.md): how a frequency becomes PLL
  settings, what "exact" means, and how to choose a reference.
- [Sweeps and frequency tables](sweeps.md): fast hopping between
  frequencies, divider boundaries and lock waits.
- [Troubleshooting](troubleshooting.md): no lock, the wrong frequency, and
  error messages.
- [Development](development.md): putting the library on a board, and running
  the tests.

## Reference

- [Examples](examples/index.md): what each script in `examples/` shows.
- [Bench validation](examples/validation.md): the test cases in
  `validate.py`.
- [Glossary](glossary.md): words and abbreviations.
- [Symbols](symbols.md): the letters used in formulas.
- [Changelog](../CHANGELOG.md)
