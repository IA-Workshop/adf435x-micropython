# Development

How to get the library onto a board from a clone, run the host tests, and
check MicroPython compatibility. For contribution rules see
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Deploying with MicroPico (VS Code)

The maintainers use the [MicroPico](https://github.com/paulober/MicroPico)
extension (v4.1 or later). The `.micropico` file at the repository root lets
it detect the project.

Sync from the **repository root** so the board gets an `/adf435x/` package
folder. Do **not** set `micropico.syncFolder` to `"adf435x"`: that copies the
folder's *contents* to the board's root and breaks `import adf435x`.

Put this in your local `.vscode/settings.json` (not committed):

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

Then use **MicroPico → Upload project to Pico**. Only `adf435x/**/*.py` is
copied.

### Running examples

Examples are not copied to the board. Open one on the host, edit its pin
numbers, and use **MicroPico → Run current file**. The library must already
be on the board.

### Other tools

Any tool that copies files works, as long as `adf435x/` lands as a folder at
the board's root (or another directory on `sys.path`).

## Host tests

Everything except the SPI/GPIO driver runs on a PC. Use Python 3.10 or later:

```bash
pip install -e ".[test]"
pytest
```

The tests replace `machine` with a fake, and `FakeChip` in
`tests/conftest.py` models how the chip latches double-buffered registers,
so write ordering is checked without hardware.

## MicroPython compatibility check

CI compiles the library with `mpy-cross` and runs
`tests/micropython_smoke.py` on the MicroPython Unix port. To run it
locally, build the Unix port from the MicroPython repository
(`make -C mpy-cross && make -C ports/unix`), then from the repository root:

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

The Unix port is not an MCU; treat its numbers as relative.
