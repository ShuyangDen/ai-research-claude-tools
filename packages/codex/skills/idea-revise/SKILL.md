---
name: idea-revise
description: Use this skill when the user invokes $idea-revise, /idea-revise, asks to revise an idea, or asks to rerun part of an idea workflow. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-revise

## Trigger Forms
- $idea-revise
- /idea-revise
- Natural language requests matching this workflow

## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-revise.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making gated writes.

## Command Workflow
You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md`.

Perform REVISE IDEA for the provided slug.

1. Read the idea and any S2 sidecar.
2. If revision changes population, treatment/exposure, outcome, mechanism, claim type, candidate contribution, or closest literature family: increment/suggest scope_version, recompute/suggest scope_hash, mark gate_dirty=true, ai_readiness=NOT_READY, human_decision=pending, and append Decision / Invalidation History. Return to the earliest affected phase, usually `pkb_evidence` or earlier.
3. If revision only adds readings/searches/clarifications: append Search Log or Evidence; mark synthesis dirty; do not change scope version.
4. Never delete old search/evidence/history or overwrite human fields.
5. Update index/cache and append `[IDEA-REVISE YYYY-MM-DD] slug: <slug> → re-ran stage: <stage>`.
