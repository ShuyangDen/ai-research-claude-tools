---
name: idea-archive
description: Use this skill when the user invokes $idea-archive, /idea-archive, asks to run idea-archive, or asks to archive an idea with a reason. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-archive
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-archive
- /idea-archive
- Natural language requests to archive an idea with a reason
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-archive.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline 鈫?Vault").
All file paths below are relative to that vault root.

Perform an **ARCHIVE IDEA** operation for the slug provided in the arguments (e.g., `/idea-archive ai-selective-reporting`).

Steps:
1. Ask: "Why are you archiving this idea?" (data not available / too similar to existing work / pivoted to different approach / other)
2. Update `ideas/<slug>.md`:
   - Set frontmatter: status=archived, checkpoint_pending=false, updated=today
   - Add to "Decision Log" section: date + reason
3. Update `ideas/index.md`: move from current section to "馃梽锔?Archived"
4. Append to `ideas/log.md`: `[IDEA-ARCHIVE YYYY-MM-DD] slug: <slug> 鈫?reason: <reason>`
5. Confirm to user: idea archived. They can always un-archive by editing the frontmatter manually.

