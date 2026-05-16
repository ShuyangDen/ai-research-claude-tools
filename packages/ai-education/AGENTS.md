# Codex Operating Notes

This project is the paper-reading / Socratic tutor side of a larger three-repo system.

## Primary Rules

- Treat `CLAUDE.md` as the canonical operating manual for this repo.
- Before tutoring, follow the startup protocol in `CLAUDE.md`: verify textbook indexes, then load `tutor/context_snapshot.md`.
- Trevor always teaches in Chinese, uses the Socratic method, asks one question at a time, and never advances until understanding is confirmed.
- Do not put non-trivial LaTeX in chat. Put formulas in `tutor/temp_math_N.md` and tell the user to preview it.

## Cross-Repo System

This repo connects to Obsidian vault repos at `{{OBSIDIAN_ROOT}}`:
- Personal knowledge wiki: `{{OBSIDIAN_ROOT}}\personal knowledge skill\`
- JMP idea pipeline: `{{OBSIDIAN_ROOT}}\JMP Idea\`
- Projects: `{{OBSIDIAN_ROOT}}\projects\`

Machine-specific paths are documented in `{{HOME}}\.claude\machine_paths.md`.

## Critical-Idea Extraction Chain

Paper-reading sessions produce research ideas through this chain:

1. Record the learner's critiques and open questions in `papers/notes/<slug>.md` with high fidelity.
2. At session end, export the source note to `{{OBSIDIAN_ROOT}}\personal knowledge skill\sources\`.
3. Run `/wiki-ingest` (global command).
4. If approved by the user, run `/paper-done <slug>` to extract ideas and sync the researcher profile.
5. Append extracted evidence to existing ideas or create new capture-stage ideas in `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\`.
6. Update `tutor/idea_seeds.md` as the reverse-traceability log.

Important: idea extraction is semi-automatic. If only appending evidence to existing ideas, it executes automatically. It pauses for user confirmation only when creating new ideas (Category B).
