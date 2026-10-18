# Contributing

Thanks for helping. This page covers the checks a change must pass. To set
up a board, see [docs/development.md](docs/development.md).

## Setup and tests

```bash
pip install -e ".[dev]"
pytest
black adf435x examples bench tests
```

Code is formatted with [black](https://black.readthedocs.io/) at 88
columns; CI fails if `black --check` would change anything.

All tests run on a PC ([CPython](docs/glossary.md#cpython) 3.10 or later),
with no hardware. CI also runs the library on the [MicroPython Unix
port](docs/glossary.md#micropython)
([docs/development.md](docs/development.md#micropython-compatibility-check)).

## Rules for library code (`adf435x/`)

- Keep it MicroPython-safe: no `dataclasses`, `pathlib`, `fractions`,
  `typing` at run time, or other modules that only CPython has. Only
  `adf435x/device.py` may import `machine`, so that `import adf435x` works
  on a PC.
- Keep board details out. Pin numbers and [SPI](docs/glossary.md#spi) bus
  numbers belong in examples and user code, never in the library.
- Frequencies are whole numbers of hertz. Do not accept floats.
- Support the ADF4350 and ADF4351 only. Other ADF435x parts have a different
  [register](docs/glossary.md#register) map.
- Check values when they are set, in
  `ADF435xRegisterMapper.validate_config()`. The encoder trusts its input
  and only masks each field to its width.
- Describe each register field once, in `FIELDS` in `adf435x/config.py`. A
  new field is one new row there.

## Tests

- Add or update tests for every change in behavior, in the file for the
  layer you changed (`tests/test_<module>.py`).
- The data sheet worked example is `WORKED_FIELDS` and `WORKED_WORDS` in
  `tests/conftest.py`. Reuse it rather than writing register values out
  again.
- Use `FakeDevice` and `FakeChip` from `tests/conftest.py` instead of
  writing new fakes.
- A known bug that is not fixed yet can be pinned with `@known_bug(...)` in
  `tests/test_regressions.py`, which marks the test as a strict expected
  failure.

## Changes that touch hardware behavior

Anything that changes what is written to the chip (register values, write
order or timing) should be checked on hardware with
[`examples/validate.py`](examples/validate.py) before release. Note the
bench result in the pull request.

## Changelog

Add user-visible changes to the "Unreleased" section of
[CHANGELOG.md](CHANGELOG.md).

## Releasing

Between releases the version is a development version such as `0.2.0.dev0`,
in both `pyproject.toml` and `package.json` (a test checks that they agree).
To release `X.Y.Z`:

1. Set the version to `X.Y.Z` in both files.
2. Rename the changelog's "Unreleased" heading to `X.Y.Z`, and update the
   README's install note if the API changed.
3. Merge to `main` and push the tag `vX.Y.Z`. The release workflow runs CI,
   checks that the tag matches both files, and publishes the zip.
4. Bump both files to the next `.dev0` version on `develop`.
