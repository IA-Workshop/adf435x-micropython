---
paths:
  - "adf435x/register_mapper.py"
  - "adf435x/register_file.py"
  - "adf435x/config.py"
---

# Register encode / file

- Validate-at-setup, trust-at-encode: `validate_config()` at configure; encode
  masks widths only.
- `commit_plan()` returns bare 32-bit words; SPI / program order is **R5→R0**.
- Double-buffer state is read from the encoded R2 word — no separate flag.
- `WORKED_WORDS[n]` is register **Rn**. Never duplicate hex in markdown.

Full rationale: `.agents/engineering_guidelines.md` (Don't→Do, Invariant notes),
`.agents/datasheet.md`.
