# adf435x-micropython

A [MicroPython](docs/glossary.md#micropython) library for the Analog Devices
ADF4350 and ADF4351 wideband [PLL](docs/glossary.md#pll) synthesizers. You
ask for a frequency in hertz; the library works out the PLL settings and
sends them to the chip over [SPI](docs/glossary.md#spi). It runs on any
MicroPython board with SPI and a few [GPIO](docs/glossary.md#gpio) pins, and
its tests run on a PC with [CPython](docs/glossary.md#cpython).

[Releases](https://github.com/IA-Workshop/adf435x-micropython/releases) ·
[Changelog](CHANGELOG.md) · [Documentation](docs/index.md)

> These docs describe the code on this branch, which has breaking changes
> since v0.1.0 (see the "Unreleased" section of the [changelog](CHANGELOG.md)).
> For v0.1.0 itself, read the README at the `v0.1.0` tag.

## Installation

Pick one of these:

- From a release: download `adf435x-X.Y.Z.zip` from
  [Releases](https://github.com/IA-Workshop/adf435x-micropython/releases),
  unzip it, and copy the `adf435x/` folder to the board's filesystem.
- With [`mip`](docs/glossary.md#mip), on a board with a network connection:

  ```python
  import mip
  mip.install("github:IA-Workshop/adf435x-micropython", version="vX.Y.Z")
  ```

  Replace `vX.Y.Z` with a release tag. v0.1.0 has the older API; read the
  README at that tag if you install it.
- From a clone of this repository: copy `adf435x/` to the board, as
  described in [docs/development.md](docs/development.md).

## Quickstart

Wire SPI ([SCK and MOSI](docs/glossary.md#mosi-and-sck)),
[LE](docs/glossary.md#le), [CE](docs/glossary.md#ce) and, if you can,
[MUXOUT](docs/glossary.md#muxout); [docs/hardware.md](docs/hardware.md)
explains each signal. Change the pin numbers below to match your board, and
run:

```python
from machine import Pin, SPI

from adf435x import ADF4351, ADF435xSynthesizer
from adf435x.device import ADF435xDevice

spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11))
device = ADF435xDevice(spi, load_enable_pin=13, chip_enable_pin=14, muxout_pin=9)

synth = ADF435xSynthesizer(device, ADF4351, ref_hz=10_000_000)
synth.power_up(frequency_hz=200_000_000)
print("locked:", synth.wait_locked(), "output:", synth.achieved_hz, "Hz")
```

`ref_hz` is the frequency of the [reference](docs/glossary.md#reference)
clock on your board, and `wait_locked()` waits for the PLL to
[lock](docs/glossary.md#lock). For a step-by-step walkthrough, see
[docs/quickstart.md](docs/quickstart.md).

## What you can do

| Goal | Use | Guide |
|------|-----|-------|
| Set one frequency, retune, mute, set output power, check lock | `ADF435xSynthesizer` | [API guide](docs/api-guide.md) |
| [Sweep](docs/glossary.md#sweep) or jump between frequencies quickly | `FrequencyTable` and `synth.play()` | [Sweeps](docs/sweeps.md) |
| Plan frequencies without hardware | `solve()`, `FrequencyTable` | [Frequency planning](docs/frequency-planning.md) |
| Set individual [register](docs/glossary.md#register) fields | `ADF435xRegisterFile` | [API guide](docs/api-guide.md#register-level-control) |

The scripts in [`examples/`](examples/) show each of these;
[docs/examples/index.md](docs/examples/index.md) describes them.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and references

The ADF4350 and ADF4351 are Analog Devices products. IA-Workshop
contributors maintain this library; [CHANGELOG.md](CHANGELOG.md) has the
release history.

- ADF4350: [product page](https://www.analog.com/en/products/adf4350.html) ·
  [data sheet
  (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)
- ADF4351: [product page](https://www.analog.com/en/products/adf4351.html) ·
  [data sheet
  (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)
