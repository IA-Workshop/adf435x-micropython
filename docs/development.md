# Development

How to put the library on a board from a clone of the repository, run the
tests on a PC, and check that the code still runs on
[MicroPython](glossary.md#micropython). For the rules a change must follow,
see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Deploying with MicroPico (VS Code)

The maintainers use the [MicroPico](https://github.com/paulober/MicroPico)
extension for VS Code (v4.1 or later), which copies files to a MicroPython
board and runs scripts on it. The `.micropico` file at the repository root
lets it find the project.

Sync from the repository root, so the board gets an `/adf435x/` package
folder. Do not set `micropico.syncFolder` to `"adf435x"`: that copies the
folder's contents, not the folder, to the board's root, and `import adf435x`
then fails.

Put this in your local `.vscode/settings.json` (it is not committed):

```jsonc
{
  "micropico.syncFolder": "",
  "micropico.syncFileTypes": ["py"],
  "micropico.pyIgnore": [
    "tests", "examples", "bench", "docs", "datasheets", ".agents",
    "**/.git", "**/__pycache__", "**/.pytest_cache"
  ]
}
```

Then run the "MicroPico: Upload project to Pico" command. Only
`adf435x/**/*.py` is copied.

### Running examples

Examples are not copied to the board. Open one on the PC, edit its pin
numbers, and run the "MicroPico: Run current file" command. The library must
already be on the board.

### Other tools

Any tool that copies files works, as long as `adf435x/` ends up as a folder
at the board's root (or in another directory on `sys.path`).

## Host tests

Everything except the [SPI](glossary.md#spi) and [GPIO](glossary.md#gpio)
driver runs on a PC with [CPython](glossary.md#cpython) 3.10 or later:

```bash
pip install -e ".[test]"
pytest
```

The tests replace MicroPython's `machine` module with a fake. `FakeChip` in
`tests/conftest.py` models how the chip delays
[double-buffered](glossary.md#double-buffering) fields, so the order of
[register](glossary.md#register) writes is checked without hardware.

## MicroPython compatibility check

CI (the automatic checks GitHub runs on every push and pull request)
compiles the library with `mpy-cross`, MicroPython's compiler, and runs
`tests/micropython_smoke.py` on the MicroPython Unix port. To run it
yourself, build the Unix port from the MicroPython repository (`make -C
mpy-cross && make -C ports/unix`), then from this repository's root:

```bash
/path/to/micropython tests/micropython_smoke.py   # prints SMOKE OK
```

## Benchmarks

`bench/bench.py` times solving, table building and playback on CPython or
the Unix port:

```bash
python bench/bench.py
/path/to/micropython bench/bench.py
```

The Unix port runs on a PC, not a microcontroller, so compare its numbers
with each other rather than with a board.
