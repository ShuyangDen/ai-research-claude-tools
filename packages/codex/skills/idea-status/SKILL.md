---
name: idea-status
description: Use this skill when the user invokes $idea-status, /idea-status, or asks for idea pipeline status. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-status

## Trigger Forms
- $idea-status
- /idea-status
- Natural language requests matching this workflow

## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-status.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making gated writes.

## Command Workflow
You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md` in the idea vault.

Perform a STATUS CHECK.

1. Prefer `ideas/_frontmatter_cache.md` for speed, but include S2 sidecar frontmatter when present.
2. If cache is missing/stale, regenerate by reading only idea frontmatter and S2 sidecar frontmatter.
3. For each idea show slug, title, status, priority, updated, checkpoint, s2_review, s2_gate_outcome, gate_phase, ai_readiness, human_decision, dirty/stale, open blockers if recorded, and next action.
4. If idea cache conflicts with sidecar authoritative fields, show `CACHE-CONFLICT` and mark it as blocking `/idea-next`.
5. Group: Ready for Human Gate Decision, Waiting for Review, In Progress, Captured, Parked, Done, Archived.
6. Update `ideas/index.md` only from cache/sidecar facts; never infer human decisions.
