# Contributing

Thanks for helping. This page covers the checks a change must pass; see
[docs/development.md](docs/development.md) for setting up a board.

## Setup and tests

```bash
pip install -e ".[test]"
pytest
```

All tests run on a PC (CPython 3.10 or later); no hardware is needed. CI
also runs the library on the MicroPython Unix port
([docs/development.md](docs/development.md#micropython-compatibility-check)).

## Rules for library code (`adf435x/`)

- **MicroPython-safe:** no `dataclasses`, `pathlib`, `fractions`, `typing` at
  runtime, or other CPython-only modules. Only `adf435x/device.py` may import
  `machine`, so `import adf435x` works on a PC.
- **No board details:** pin numbers and SPI bus numbers belong in examples
  and user code, never in the library.
- **Whole hertz:** frequencies are integers; do not accept floats.
- **ADF4350 and ADF4351 only:** other ADF435x parts have a different
  register map.
- **Validate at setup, trust at encode:** check values in
  `ADF435xRegisterMapper.validate_config()`; the encoder only masks.
- **Register fields** are described once, in `adf435x/config.py`
  (`FIELDS`). A new field is one row there.

## Tests

- Add or update tests for every behaviour change, next to the layer you
  changed (`tests/test_<module>.py`).
- The data sheet worked example is `WORKED_FIELDS` / `WORKED_WORDS` in
  `tests/conftest.py`; reuse it rather than writing register values out
  again.
- Use `FakeDevice` / `FakeChip` from `tests/conftest.py` instead of writing
  new fakes.
- A known bug that is not fixed yet can be pinned with `@known_bug(...)` in
  `tests/test_regressions.py` (a strict xfail).

## Changes that touch hardware behaviour

Anything that changes what is written to the chip (register values, write
order, timing) should be checked on hardware with
[`examples/validate.py`](examples/validate.py) before release, and the bench
result noted in the pull request.

## Changelog

Add user-visible changes to the "Unreleased" section of
[CHANGELOG.md](CHANGELOG.md).
