# Personal Knowledge Base — Agent Notes

- Read `~/.claude/machine_paths.md` as UTF-8 before crossing project boundaries.
- Treat `sources/` as canonical and read-only during wiki ingest.
- Treat `wiki/` as a derived, provenance-preserving view.
- Use stable claim IDs and locators; distinguish results, author interpretation, researcher reflection, and agent inference.
- Retrieval workers never write the vault. One orchestrator/single writer applies validated changes atomically.
- Never overwrite `## Human Notes` or human verification fields.
- Use source-content hashes so updated sources are re-ingested.
- `/idea-chat` retrieves bounded claim cards; `/paper-done` owns source creation; `/wiki-ingest` owns concept projection.
