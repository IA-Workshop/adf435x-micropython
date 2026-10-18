---
paths:
  - "adf435x/config.py"
  - "adf435x/consts.py"
  - "adf435x/profiles.py"
  - "adf435x/register_mapper.py"
  - "adf435x/register_file.py"
---

# Register layer

- A new field is one `_field(...)` row in `config.FIELDS`: register, bit
  position, width, default, kind (`BOOL`, `UINT`, `ENUM`, `DIVIDER`),
  allowed values, error label, and the `ADF435xProfile` capability it
  needs. Encoding and validation both read this table, so no other code
  changes. Keep the `# fmt: off` / `# fmt: on` markers around it.
- A cross-field check is a `_rule_*(profile, config)` function added to
  `register_mapper._RULES` with the fields that trigger it. It raises
  `ValueError` with a message a user can act on.
- Bit positions and codes go in `consts` as `REG{n}_{FIELD}_POS` /
  `_WIDTH` / named codes, with the data sheet figure in a comment.
- Which fields latch on the next R0 write (DBR/DBB) is listed in
  `.agents/datasheet.md`; `register_file._commit_stale_set` and `FakeChip`
  in `tests/conftest.py` must both follow that list.
- Tests: `test_config.py`, `test_register_mapper.py`,
  `test_register_file.py`, `test_validation.py`, `test_fake_chip.py`.
