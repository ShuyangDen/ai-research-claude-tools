---
name: idea-status
description: "Use this skill when the user invokes $idea-status, /idea-status, or asks for idea-pipeline status. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-status

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-status.md","source_sha256":"57d6af11f40f40066cce8a90b72743674d5eaac16673dde001bb8f655a382d19","workflow_version":"3.2.0"} -->

## Trigger Forms

- $idea-status
- /idea-status
- Natural language requests for current idea-pipeline status

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-status.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md` in the idea vault.

Perform a STATUS CHECK.

1. Prefer `ideas/_frontmatter_cache.md` for speed, but include S2 sidecar frontmatter when present.
2. If cache is missing/stale, regenerate by reading only idea frontmatter and S2 sidecar frontmatter.
3. For each idea show slug, title, `idea_origin`, status, priority, updated, checkpoint, s2_review, s2_gate_outcome, gate_phase, ai_readiness, human_decision, dirty/stale, open blockers if recorded, and next action. Missing origin is displayed as `legacy_unclassified`; do not infer it.
4. If idea cache conflicts with sidecar authoritative fields, show `CACHE-CONFLICT` and mark it as blocking `/idea-next`.
5. Keep the stage groups, and add a dedicated `AI-Generated Candidates` view containing every `idea_origin: ai_generated` item with its current stage/checkpoint. Do not duplicate AI items into a user-authored label.
6. Update `ideas/index.md` only from cache/sidecar facts; never infer human decisions.
