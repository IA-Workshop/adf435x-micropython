@AGENTS.md

<!--
Claude Code reads AGENTS.md through the import above. Shared policy belongs
in AGENTS.md or .agents/, not here. Block comments like this one are
stripped before the file is loaded, so they cost no context.
-->

## Claude Code

- Rules in `.claude/rules/` load when you read or edit a file that matches
  their `paths`. Each adds the layer-specific conventions for that code.
- Skills in `.claude/skills/`: `adf435x-development` (the change workflow)
  and `docs-style-review` (a writing review pass, run with
  `/docs-style-review`).
- `/context` shows which instruction files are loaded.
