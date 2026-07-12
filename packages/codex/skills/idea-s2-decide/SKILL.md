---
name: idea-s2-decide
description: Use this skill when the user invokes $idea-s2-decide, /idea-s2-decide, or explicitly asks to record an S2 gate outcome. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-s2-decide

## Trigger Forms
- $idea-s2-decide
- /idea-s2-decide
- Natural language requests matching this workflow

## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-s2-decide.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making gated writes.

## Command Workflow
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
