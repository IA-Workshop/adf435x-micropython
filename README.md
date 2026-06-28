# adf435x-micropython

MicroPython library for the ADF4350 and ADF4351 wideband PLL synthesizers.

## Deployment

There is no on-board installer. Copy the `adf435x/` package directory to the
MicroPython filesystem (via [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html),
Thonny, rshell, or your IDE’s upload tool). Copy scripts from `examples/` as
needed and adjust pin assignments for your board. Host files (`tests/`,
`pyproject.toml`) are not required on the device.

## See Also

### ADF4350

- [Product Page](https://www.analog.com/en/products/adf4350.html)
- [Data Sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4350.pdf)

### ADF4351

- [Product Page](https://www.analog.com/en/products/adf4351.html)
- [Data Sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4351.pdf)
