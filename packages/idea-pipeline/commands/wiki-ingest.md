You are maintaining a personal knowledge wiki in Obsidian.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the wiki vault path (under "Personal Knowledge Wiki → Vault").
If the path says "not set up on this machine", tell the user and stop.

Follow the instructions in `CLAUDE.md` in that vault. Now perform an **INGEST** operation:

1. Read `wiki/log.md` to see which sources have already been ingested
2. List all files in `sources/`
3. Identify files NOT yet mentioned in the log
4. For each new source:
   - Read its content carefully
   - Extract key concepts, people, tools, techniques, and ideas
   - For each concept: check if a wiki page already exists in `wiki/`
     - If yes: update it with new information and cross-links
     - If no: create a new page at `wiki/<ConceptName>.md` with proper frontmatter
   - Update `wiki/index.md` with any new pages
   - Append to `wiki/log.md` (at the bottom):
     `[INGEST YYYY-MM-DD] source: <filename> → created: <pages> | updated: <pages>`
5. Report a summary of what was created and updated

If there are no new sources, say so and stop.
