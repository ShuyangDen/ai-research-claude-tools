# Codex Operating Notes

This vault is the JMP idea pipeline for an economics PhD student.

## Primary Rules

- Treat `CLAUDE.md` as the canonical pipeline specification.
- Machine-specific paths live in `~/.claude/machine_paths.md`; read that file before running any workflow that touches another vault.
- Do not advance an idea past a checkpoint without explicit user approval.
- Keep `ideas/log.md` append-only.

## Key Workflows

- `/idea-new`: create a new idea and auto-run S2 explore.
- `/idea-next`: advance an idea one stage, respecting checkpoints.
- `/idea-status`: refresh the idea kanban.
- `/wiki-ingest`: ingest new source notes in the personal knowledge wiki.
- `/paper-done`: full post-session pipeline for a finished paper.

When using Codex, emulate a slash command by reading the corresponding file in `~/.claude/commands/` and following it exactly.

## Idea Extraction Contract

`/paper-done` includes idea extraction:

- First parse the source note's critical reflections, open questions, and idea-pipeline relevance sections.
- Then present a proposal table to the user.
- Do not write idea files until the user confirms.
- After confirmation, update idea pages, `ideas/index.md`, `ideas/log.md`, and the source note's `Idea Extraction Record`.

Quality bar: new ideas must name a specific causal mechanism or channel. Vague "AI affects X" framings should be skipped or sharpened before creation.
