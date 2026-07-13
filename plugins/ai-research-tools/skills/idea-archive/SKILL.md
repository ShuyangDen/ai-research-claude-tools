---
name: idea-archive
description: "Use this skill when the user invokes $idea-archive, /idea-archive, asks to run idea-archive, or asks to archive an idea with a reason. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-archive

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-archive.md","source_sha256":"54c02c58fc4e3587ca93c91fd2ddfb4ec557d62871a7cc2e3aaed4c44590a6bd","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-archive
- /idea-archive
- Natural language requests to archive a research idea with a reason

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-archive.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline → Vault").
All file paths below are relative to that vault root.

Perform an **ARCHIVE IDEA** operation for the slug provided in the arguments (e.g., `/idea-archive example-idea`).

Steps:
1. Ask: "Why are you archiving this idea?" (data not available / too similar to existing work / pivoted to different approach / other)
2. Update `ideas/<slug>.md`:
   - Set frontmatter: status=archived, checkpoint_pending=false, updated=today
   - Add to "Decision Log" section: date + reason
3. Update `ideas/index.md`: move from current section to "🗄️ Archived"
4. Append to `ideas/log.md`: `[IDEA-ARCHIVE YYYY-MM-DD] slug: <slug> → reason: <reason>`
5. Confirm to user: idea archived. They can always un-archive by editing the frontmatter manually.
