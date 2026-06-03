---
name: wiki-ingest
description: Use this skill when the user invokes $wiki-ingest, /wiki-ingest, asks to run wiki-ingest, or asks to ingest source notes into the personal knowledge wiki. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# wiki-ingest
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Personal Knowledge Wiki.
## Trigger Forms
- $wiki-ingest
- /wiki-ingest
- Natural language requests to ingest source notes into the personal knowledge wiki
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\wiki-ingest.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
You are maintaining a personal knowledge wiki in Obsidian.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the wiki vault path (under "Personal Knowledge Wiki 鈫?Vault").
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
     `[INGEST YYYY-MM-DD] source: <filename> 鈫?created: <pages> | updated: <pages>`
5. Report a summary of what was created and updated

If there are no new sources, say so and stop.

