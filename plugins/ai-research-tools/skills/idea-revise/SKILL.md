---
name: idea-revise
description: "Use this skill when the user invokes $idea-revise, /idea-revise, asks to revise an idea, or asks to rerun part of an idea workflow. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-revise

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-revise.md","source_sha256":"056603d6b45e1d66153e6cff671184d1019d91a1d07d110a2a64447667010e45","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-revise
- /idea-revise
- Natural language requests to revise an idea or rerun its current stage

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-revise.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md`.

Perform REVISE IDEA for the provided slug.

1. Read the idea and any S2 sidecar.
2. If revision changes population, treatment/exposure, outcome, mechanism, claim type, candidate contribution, or closest literature family: increment/suggest scope_version, recompute/suggest scope_hash, mark gate_dirty=true, ai_readiness=NOT_READY, human_decision=pending, and append Decision / Invalidation History. Return to the earliest affected phase, usually `pkb_evidence` or earlier.
3. If revision only adds readings/searches/clarifications: append Search Log or Evidence; mark synthesis dirty; do not change scope version.
4. Never delete old search/evidence/history or overwrite human fields.
5. Update index/cache and append `[IDEA-REVISE YYYY-MM-DD] slug: <slug> → re-ran stage: <stage>`.
