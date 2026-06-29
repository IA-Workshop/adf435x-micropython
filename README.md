# adf435x-micropython

MicroPython library for the ADF4350 and ADF4351 wideband PLL synthesizers.
Runs on any MicroPython board with SPI and GPIO; pin wiring is application-specific.

Agent/AI contributors: see [AGENTS.md](AGENTS.md) (Claude Code: [CLAUDE.md](CLAUDE.md)).

## Deployment

There is no on-board installer. Copy the `adf435x/` package directory to the
MicroPython filesystem (via [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html),
Thonny, rshell, or your IDE's upload tool). Copy scripts from `examples/` as
needed and adjust pin assignments for your board. Host files (`tests/`,
`pyproject.toml`) are not required on the device.

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

Hardware-in-the-loop tests are marked `@pytest.mark.device` and are skipped
unless you pass `pytest --device` with a connected ADF435x board.

See [agent/TESTING.md](agent/TESTING.md) for fixtures, conventions, and the
golden vector.

## See Also

### ADF4350

- [Product Page](https://www.analog.com/en/products/adf4350.html)
- [Data Sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)

### ADF4351

- [Product Page](https://www.analog.com/en/products/adf4351.html)
- [Data Sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)
