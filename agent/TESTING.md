# Testing

Host-side tests run under CPython with pytest. No board or `machine` module is
required for the default suite.

## Environment setup

### Primary local workflow (this repo)

```bash
conda activate general
pip install -e ".[test]"    # once, or when deps change
pytest
```

### Portable setup (any developer)

```bash
# Any Python 3.10+ venv or conda environment
pip install -e ".[test]"
pytest
```

Requirements: CPython ≥ 3.10 and pytest (declared in
[`pyproject.toml`](../pyproject.toml)). Environment name is not prescribed;
`general` is the maintainer's local conda env.

Hardware-in-the-loop tests:

```bash
pytest --device
```

Requires a connected ADF435x eval board. Tests marked `@pytest.mark.device`
are skipped unless `--device` is passed.

## Golden vector chain

Primary integration regression (datasheet worked example):

```text
solve(2_112_600_000, 10_000_000, ADF4351)
  → configure(**result.fields)
  → encode → commit_plan()
  → compare to WORKED_WORDS
```

Defined in [`tests/conftest.py`](../tests/conftest.py):

- `WORKED_FIELDS` — PLL field dict
- `WORKED_WORDS` — expected R5→R0 register words

Do not duplicate hex values in agent docs; reference these names.

## Fixtures

| Fixture | Purpose |
|---------|---------|
| `mapper` | ADF4351 register mapper |
| `worked_config` | Config for golden vector |
| `worked_regfile` | Register file configured to golden vector |
| `make_config(**fields)` | Build config with overrides |
| `FakeDevice` | Record SPI writes; simulate CE/MUXOUT |
| `synth` | Synthesizer + FakeDevice (conftest) |
| `mock_machine` | Fake `machine` module for device tests |

`FakeDevice` lives only in conftest. Do not duplicate in test files.

## Test style

- Group tests in `Test{FeatureArea}` classes
- Use `@pytest.mark.parametrize` for profile and edge coverage
- One behavioral assertion per concern where practical
- Import private solver helpers (e.g. `_compute_f_pfd`) for focused unit tests

## Layered test map

| Test file | Module under test |
|-----------|-------------------|
| `test_consts.py` | Bit layout, DBR indices |
| `test_profile.py` | ADF4350 vs ADF4351 capabilities |
| `test_config.py` | Field schema, transactional configure |
| `test_validation.py` | Mapper validation rules |
| `test_register_mapper.py` | Encode, golden vector, profile gates |
| `test_register_file.py` | Staleness, DBR/DBB ordering, plan/mark |
| `test_solver.py` | Frequency math, MOD search, band edges |
| `test_synthesizer.py` | End-to-end with FakeDevice |
| `test_sweep.py` | Table building, single-R0 hop invariant |
| `test_device.py` | SPI byte order, LE sequence |
| `test_device_hw.py` | Hardware lock detect (`--device`) |

## Key invariants to preserve in tests

- **Golden vector:** solver fields and encoded words match `WORKED_*`
- **Double-buffer:** R1/R2 changes force trailing R0 write
- **Fast-hop:** in-band sweep hops are single R0 word (`test_int_frac_only_hops_are_single_r0`)
- **Plan/mark:** SPI failure calls `mark_write_failed`; cache unchanged until success
- **Divider crossing:** `DividerOctaveCrossingError` unless explicitly allowed

## After code changes

Always run:

```bash
pytest
```

For register, solver, or datasheet-sensitive edits, add or update tests in the
matching layer file before finishing.
