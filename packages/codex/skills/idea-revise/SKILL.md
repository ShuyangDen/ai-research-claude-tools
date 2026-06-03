---
name: idea-revise
description: Use this skill when the user invokes $idea-revise, /idea-revise, asks to run idea-revise, or asks to revise or rerun the current stage of an idea. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-revise
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-revise
- /idea-revise
- Natural language requests to revise or rerun the current stage of an idea
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-revise.md at runtime. This skill is the copied command source for Codex.
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
Follow the instructions in `CLAUDE.md` in that vault.

Perform a **REVISE IDEA** operation for the slug provided in the arguments (e.g., `/idea-revise ai-selective-reporting`).

Steps:
1. Read `ideas/<slug>.md` to understand current stage and content
2. Ask the user: "What specifically needs to change?"
3. Re-run the current stage incorporating the user's feedback
4. Update the relevant section(s) of the idea page
5. Set checkpoint_pending: true
6. Update frontmatter: updated date
7. Append to `ideas/log.md`: `[IDEA-REVISE YYYY-MM-DD] slug: <slug> 鈫?re-ran stage: <stage>, reason: <brief>`
8. Report what was changed

