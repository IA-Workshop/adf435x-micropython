---
name: adf435x-development
description: >-
  Develop the ADF435x MicroPython PLL library. Use when changing adf435x/,
  tests/, examples/, or agent docs.
---

# ADF435x development workflow

## 1. Orient

Read [AGENTS.md](../../AGENTS.md) for scope, invariants, and gotchas. For
task-specific depth, open the row in
[.agents/context.md](../../.agents/context.md) — do not read
`.agents/journal.md` for implementation.

## 2. Implement

- Follow [.agents/engineering_guidelines.md](../../.agents/engineering_guidelines.md)
  for new names
- MicroPython-safe `adf435x/` (no dataclasses, pathlib, etc.)
- Board pins in caller/examples/tests only
- Minimal diff

**Step complete:** run pytest for touched layers → append
[.agents/journal.md](../../.agents/journal.md) when non-obvious → update docs
per [.agents/rules.md](../../.agents/rules.md).

## 3. Test

```bash
pip install -e ".[test]"
pytest
```

See [.agents/rules.md](../../.agents/rules.md) for tests-by-layer map.

## Definition of done

See [.agents/context.md](../../.agents/context.md) § Definition of done.
