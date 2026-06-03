---
name: idea-status
description: Use this skill when the user invokes $idea-status, /idea-status, asks to run idea-status, or asks to show all ideas by current pipeline status. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-status
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-status
- /idea-status
- Natural language requests to show all ideas by current pipeline status
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-status.md at runtime. This skill is the copied command source for Codex.
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

Perform a **STATUS CHECK** operation:

1. List all `.md` files in `ideas/` directory (exclude: index.md, log.md, _template.md)
2. Read the frontmatter of each file
3. Output a formatted status table grouped by:
   - 馃敶 Waiting for Review (checkpoint_pending: true) 鈥?list these first with emphasis
   - 馃煛 In Progress (checkpoint_pending: false, status not done/archived)
   - 鉁?Done
   - 馃梽锔?Archived
4. For each idea show: slug, title (# heading), current status/stage, priority, last updated date
5. Also update `ideas/index.md` to match the current state

