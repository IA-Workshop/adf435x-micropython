---
name: docs-style-review
description: >-
  Review and fix human-facing writing in the adf435x repo (README,
  CONTRIBUTING, CHANGELOG, docs/, docstrings and comments) against the
  project writing rules: American English, hobbyist reader, terms defined
  on first use, short docstrings, no AI-writing patterns.
disable-model-invocation: true
---

# Writing review pass

Apply `.agents/writing_style.md` to the files the user names, or to all
human-facing text if they name none. Change wording, docstrings, comments
and layout only, never behavior.

1. List the files in scope. Agent docs (`AGENTS.md`, `CLAUDE.md`,
   `.agents/`, `.claude/`, `.cursor/`) are out of scope, and
   `.agents/journal.md` is never edited.
2. For each file, check spelling, then the AI-writing patterns, then
   whether each term and symbol is defined on first use.
3. Grep across the scope for British spellings (`our\b`, `ise\b`,
   `isation`, `yse\b`, `tre\b`) and em dashes, and check each hit by hand.
4. Move any agent-oriented content you remove from code into the right
   `.agents/` file, so nothing is lost.
5. Verify: `pytest -q` (the docs tests check links, anchors and the
   register-word ban), `black --check adf435x examples bench tests`.
6. Report what changed per file and any judgment calls, in plain words.
