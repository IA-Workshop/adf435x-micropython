# Examples

The scripts in [`examples/`](../../examples/) run on the board once the
library is installed. Each has its pin numbers at the top; change them to
match your wiring ([Hardware](../hardware.md)). Run them from the PC
([Development](../development.md#running-examples)).

| Script | What it shows | Level |
|--------|---------------|-------|
| [`device_handler.py`](../../examples/device_handler.py) | Raw [register](../glossary.md#register) writes; toggles [MUXOUT](../glossary.md#muxout) high and low to prove the wiring | Device |
| [`fixed_frequency.py`](../../examples/fixed_frequency.py) | One frequency and a [lock](../glossary.md#lock) check ([walkthrough](fixed-frequency.md)) | Synthesizer |
| [`frequency_sweep.py`](../../examples/frequency_sweep.py) | A [sweep](../glossary.md#sweep) in even steps with `FrequencyTable` and `play()` | Synthesizer |
| [`frequency_sweep_octave.py`](../../examples/frequency_sweep_octave.py) | A sweep across two [RF divider](../glossary.md#rf-divider) boundaries | Synthesizer |
| [`frequency_table_solver.py`](../../examples/frequency_table_solver.py) | Plan and print a table, then step through it | Planning |
| [`fixed_frequency_solver.py`](../../examples/fixed_frequency_solver.py) | `solve()` with a register file and device, without the synthesizer | Registers |
| [`registers.py`](../../examples/registers.py) | Set register fields by hand: the data sheet example, at ÷32 so a scope can show it | Registers |
| [`validate.py`](../../examples/validate.py) | Bench test cases ([details](validation.md)) | Synthesizer |

All the examples assume a 10 MHz [reference](../glossary.md#reference) and
the ADF4351. For the ADF4350, import `ADF4350` instead and keep frequencies
at or above 137.5 MHz.
