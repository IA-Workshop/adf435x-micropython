# adf435x-micropython

MicroPython library for the ADF4350 and ADF4351 wideband PLL synthesizers.
Runs on any MicroPython board with SPI and GPIO; pin wiring is application-specific.

**Releases:** [GitHub Releases](https://github.com/IA-Workshop/adf435x-micropython/releases)
· [Changelog](CHANGELOG.md)

Agent/AI contributors: see [AGENTS.md](AGENTS.md) (Claude Code: [CLAUDE.md](CLAUDE.md)).

## Install

**Offline (release zip):** download `adf435x-X.Y.Z.zip` from
[Releases](https://github.com/IA-Workshop/adf435x-micropython/releases), unzip,
and copy the `adf435x/` folder to the MicroPython filesystem.

**Online (networked board):**

```python
import mip
mip.install("github:IA-Workshop/adf435x-micropython", version="v0.1.0")
```

Or from the host: `mpremote mip install github:IA-Workshop/adf435x-micropython@v0.1.0`

**Development:** clone this repo and bulk-sync `adf435x/` with
[MicroPico](https://github.com/paulober/MicroPico) or
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html).
See [agent/HARDWARE.md](agent/HARDWARE.md) for the maintainer reference pin map.
Copy scripts from `examples/` as needed. Host files (`tests/`, `pyproject.toml`)
are not required on the device.

## Quick start

Adjust SPI bus and GPIO numbers for your board (reference wiring in
[agent/HARDWARE.md](agent/HARDWARE.md)):

```python
from machine import Pin, SPI

from adf435x.device import ADF435xDevice
from adf435x.profiles import ADF4351
from adf435x.synthesizer import ADF435xSynthesizer

spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(10), mosi=Pin(11))
device = ADF435xDevice(
    spi,
    load_enable_pin=13,
    chip_enable_pin=14,
    muxout_pin=9,
)
synth = ADF435xSynthesizer(device, ADF4351, ref_hz=10_000_000)
synth.power_up(frequency_hz=200_000_000)
synth.wait_locked()
print(synth.achieved_hz)
```

## API levels

1. **`ADF435xSynthesizer`** — set one frequency, lock detect, output power
   (`adf435x` package root).
2. **`FrequencyTable` / `ADF435xSweeper`** — precomputed hop sequences
   (`import adf435x.sweep`).
3. **Register file + solver** — lower-level field and Hz planning
   (`ADF435xRegisterFile`, `solve`).

Layer overview: [agent/ARCHITECTURE.md](agent/ARCHITECTURE.md).

## Testing

Host-side tests run under CPython with pytest. No board or `machine` module is
required; `tests/conftest.py` installs a fake `machine` for device-handler
checks.

```bash
conda activate general    # local convention; any Python 3.10+ env works
pip install -e ".[test]"
pytest
```

Or with a virtual environment:

```bash
pip install -e ".[test]"
pytest
```

On-board bench validation (scope/counter checks):
[`examples/validate.py`](examples/validate.py).
Run from the host (**Run current file**); bulk-sync deploys `adf435x/` only.
See [agent/HARDWARE.md](agent/HARDWARE.md).

See [agent/TESTING.md](agent/TESTING.md) for fixtures, conventions, and the
golden vector.

## See Also

### ADF4350

- [Product Page](https://www.analog.com/en/products/adf4350.html)
- [Data Sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)

### ADF4351

- [Product Page](https://www.analog.com/en/products/adf4351.html)
- [Data Sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)

Extracted PLL/register facts for contributors: [agent/DATASHEET.md](agent/DATASHEET.md).
