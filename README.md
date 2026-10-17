# adf435x-micropython

MicroPython library for the Analog Devices ADF4350 and ADF4351 wideband PLL
synthesizers. Ask for a frequency in hertz; the library works out the PLL
settings and programs the chip over SPI. Runs on any MicroPython board with
SPI and a few GPIO pins, and is fully testable on a PC with CPython.

**Releases:** [GitHub Releases](https://github.com/IA-Workshop/adf435x-micropython/releases)
· [Changelog](CHANGELOG.md) · **Documentation:** [docs/index.md](docs/index.md)

> These docs describe the code on this branch, which has breaking changes
> since v0.1.0 (see the "Unreleased" section of the [changelog](CHANGELOG.md)).
> For v0.1.0 itself, read the README at the `v0.1.0` tag.

## Installation

**Release zip:** download `adf435x-X.Y.Z.zip` from
[Releases](https://github.com/IA-Workshop/adf435x-micropython/releases),
unzip, and copy the `adf435x/` folder to the board's filesystem.

**`mip`** (on a networked board):

```python
import mip
mip.install("github:IA-Workshop/adf435x-micropython", version="v0.1.0")
```

**From a clone:** copy or sync `adf435x/` to the board; see
[docs/development.md](docs/development.md).

## Quickstart

Wire SPI (SCK, MOSI), LE, CE and optionally MUXOUT
([docs/hardware.md](docs/hardware.md)), change the pin numbers below to
match your board, and run:

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

Walkthrough: [docs/quickstart.md](docs/quickstart.md).

## What you can do

| Goal | Use | Guide |
|------|-----|-------|
| One frequency, retunes, mute, output power, lock detect | `ADF435xSynthesizer` | [API guide](docs/api-guide.md) |
| Fast sweeps and frequency hopping | `FrequencyTable` + `synth.play()` | [Sweeps](docs/sweeps.md) |
| Plan frequencies without hardware | `solve()`, `FrequencyTable` | [Frequency planning](docs/frequency-planning.md) |
| Set individual register fields | `ADF435xRegisterFile` | [API guide](docs/api-guide.md#register-level-control) |

Examples for each are in [`examples/`](examples/) and described in
[docs/examples/index.md](docs/examples/index.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and references

ADF4350/ADF4351 are products of Analog Devices. This library is maintained by
IA-Workshop contributors; see [CHANGELOG.md](CHANGELOG.md) for release
history.

- ADF4350: [product page](https://www.analog.com/en/products/adf4350.html) ·
  [data sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)
- ADF4351: [product page](https://www.analog.com/en/products/adf4351.html) ·
  [data sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)
