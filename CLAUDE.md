@AGENTS.md

<!--
Claude Code reads AGENTS.md through the import above. Shared policy belongs
in AGENTS.md or .agents/, not here. Block comments like this one are
stripped before the file is loaded, so they cost no context.
-->

## Claude Code

- `.claude/rules` and `.claude/skills/*` are symlinks into `.agents/`
  (layout in AGENTS.md). A rule loads when you read or edit a file that
  matches its `paths`. Edit the files under `.agents/`, not the links.
- Skills: `adf435x-development` (the change workflow) and
  `docs-style-review` (a writing review pass, run with
  `/docs-style-review`).
- `/context` shows which instruction files are loaded.
