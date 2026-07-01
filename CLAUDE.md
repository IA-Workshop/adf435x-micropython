@AGENTS.md

<!--
Claude Code loads AGENTS.md via the @import above (markdown links do not load
files — only `@path` does). Cursor, Codex, and other agents read AGENTS.md
directly. Keep shared policy in AGENTS.md / .agents/ — not here. This comment is
stripped before injection, so it costs no context.
-->

## Claude Code specifics

- Path-scoped rules in `.claude/rules/` load automatically when you edit matching
  files; each one points into `.agents/` for the full rationale.
- Load on demand for deep work: `.agents/engineering_guidelines.md`,
  `.agents/rules.md`, `.agents/datasheet.md`.
