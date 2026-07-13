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
