# adf435x-micropython

MicroPython library for the ADF4350 and ADF4351 wideband PLL synthesizers. Runs on any MicroPython board with SPI and GPIO interfaces.

**Releases:** [GitHub Releases](https://github.com/IA-Workshop/adf435x-micropython/releases)
· [Changelog](CHANGELOG.md)

**Documentation:** [docs/index.md](docs/index.md) · [Quickstart](docs/quickstart.md)

## Installation

### Offline

Download the latest release (`adf435x-X.Y.Z.zip`) from
[Releases](https://github.com/IA-Workshop/adf435x-micropython/releases), unzip,
and copy the `adf435x/` folder to the MicroPython filesystem.

### Online (`mip`)

On the device:

```python
import mip
mip.install("github:IA-Workshop/adf435x-micropython", version="v0.1.0")
```

Or from the host:

```bash
mpremote mip install github:IA-Workshop/adf435x-micropython@v0.1.0
```

### Development

Clone this repo and bulk-sync `adf435x/` to your device. See
[docs/development.md](docs/development.md) for deploy workflow and
[docs/hardware.md](docs/hardware.md) for wiring.

## Quickstart

Full tutorial: [docs/quickstart.md](docs/quickstart.md) ·
[fixed-frequency example](docs/examples/fixed-frequency.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributors

ADF4350/ADF4351 are products of Analog Devices. This library is maintained by
IA-Workshop contributors; see [CHANGELOG.md](CHANGELOG.md) for release history.

## References

### ADF4350

- [Product page](https://www.analog.com/en/products/adf4350.html)
- [Data sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)

### ADF4351

- [Product page](https://www.analog.com/en/products/adf4351.html)
- [Data sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)
