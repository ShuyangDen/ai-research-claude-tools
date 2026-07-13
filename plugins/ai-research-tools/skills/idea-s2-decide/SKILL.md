---
name: idea-s2-decide
description: "Use this skill when the user invokes $idea-s2-decide, /idea-s2-decide, or explicitly asks to record an S2 gate outcome. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-s2-decide

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-s2-decide.md","source_sha256":"91b6d24a000f90bfee4a8c90aa477b8972171f993dd7b983c5935fa64d361863","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-s2-decide
- /idea-s2-decide
- Natural language requests to record an explicit S2 literature-gate outcome

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-s2-decide.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

You are managing a research idea pipeline for an economics PhD student.

Usage: `/idea-s2-decide <slug> <OUTCOME>`
Allowed outcomes: `ADVANCE-S3`, `LOOP-S2`, `RETURN-S1`, `PARK-METHOD`, `PARK-PRIORITY`, `STOP-DUPLICATE`.

Step 0: Read `~/.claude/machine_paths.md`, then read the idea vault `CLAUDE.md` and `AGENTS.md`.

Purpose: record an explicit human S2 gate outcome. This command never writes S3 research questions.

Rules:
- Only run when the user explicitly supplies one allowed outcome.
- The sidecar `ideas/reviews/<slug>-s2-gate.md` is authoritative.
- Idea frontmatter values are generated caches and must be synced from the sidecar.
- Do not change prior Decision / Invalidation History entries.

Procedure:
1. Verify the idea and sidecar exist.
2. Validate the outcome.
3. Require or record a short human rationale, reviewer name if provided, and today's date.
4. If outcome is `ADVANCE-S3`, first verify: `ai_readiness: READY_FOR_HUMAN_DECISION`, gate not dirty, scope hash current, no cache conflict, no unresolved blocking condition.
5. Other outcomes may be recorded before readiness if the human explicitly chooses to loop, return, park, or stop.
6. Update authoritative sidecar frontmatter: `human_decision`, `human_decision_by`, `human_decision_date`, and relevant `gate_status/gate_phase`.
7. Append to `## 17. Decision / Invalidation History`.
8. Sync idea frontmatter cache fields (`s2_review`, `s2_gate_outcome`, `checkpoint_pending`) and update `ideas/index.md`.
9. Append to `ideas/log.md`: `[IDEA-GATE-DECISION YYYY-MM-DD] slug: <slug> → <OUTCOME>; reason: <short reason>`.
10. Stop. Tell the user to run `/idea-next <slug>` only if the outcome is `ADVANCE-S3` and they want to formulate S3.
