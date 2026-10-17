# adf435x documentation

A MicroPython library for the ADF4350 and ADF4351 PLL synthesizers.

## Start here

1. [Quickstart](quickstart.md): wire the board, set one frequency, check lock.
2. [Hardware](hardware.md): signals, SPI settings, timing, and a reference
   pin map.
3. [API guide](api-guide.md): which class to use, and how each behaves.

## Guides

- [Frequency planning](frequency-planning.md): how a frequency becomes PLL
  settings, what "exact" means, and choosing a reference.
- [Sweeps and frequency tables](sweeps.md): fast hopping, divider
  boundaries, lock waits.
- [Troubleshooting](troubleshooting.md): no lock, wrong frequency, errors.
- [Development](development.md): deploying to a board, running tests.

## Reference

- [Examples](examples/index.md): what each script in `examples/` shows.
- [Bench validation](examples/validation.md): the `validate.py` test catalog.
- [Glossary](glossary.md): PLL and register terms.
- [Changelog](../CHANGELOG.md)
