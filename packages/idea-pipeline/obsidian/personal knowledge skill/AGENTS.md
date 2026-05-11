# Personal Knowledge Wiki — Agent Notes

This vault is a read-mostly knowledge base. The primary operation is `/wiki-ingest`.

## Rules

- Machine-specific paths live in `~/.claude/machine_paths.md`.
- Read `CLAUDE.md` for the wiki page format and ingest protocol.
- Do not delete content from existing wiki pages — only add or cross-link.
- The `sources/` folder is input only — do not modify source files during ingest.

## Operations

- `/wiki-ingest` — ingest new files from `sources/` into the wiki
- `/paper-done <slug>` — triggered from AI Education; exports a paper and automatically calls wiki-ingest logic
