You are managing a research idea pipeline for an economics PhD student.

This command is a transition guard: it checks checkpoint and S2 Gate state before advancing, and it must not create or complete a Full Gate ad hoc.

Step 0: Read `~/.claude/machine_paths.md` to get the vault path and Zotero config path. Follow `CLAUDE.md` and `AGENTS.md` in the vault.

Perform an ADVANCE IDEA operation for the provided slug. If no slug is provided, list actionable ideas and ask which one to advance.

`capture → explore`:
- Run S2 Quick Scan only: max 5 representative or suspiciously close papers, max 3 candidate openings/tensions/possible deltas.
- Do not write `gap verified`, `novel`, formal S3 research question, or `ADVANCE-S3`.
- Set status=explore, checkpoint_pending=true, s2_review=quick, s2_gate_outcome=pending.
- Update index and append log.

`explore → question`:
1. Read `ideas/<slug>.md` and `ideas/reviews/<slug>-s2-gate.md`.
2. If the sidecar is missing, stop and tell the user to run `/idea-s2-full <slug> start`.
3. If the sidecar is incomplete, dirty, stale, not ready, has unresolved high-threat papers, has incomplete required routes, has version/provenance conflicts, or conflicts with idea frontmatter cache, stop and list blockers. Do not create or complete Full Gate here.
4. If `ai_readiness` is not `READY_FOR_HUMAN_DECISION`, stop and tell the user to run `/idea-s2-full <slug> resume` or `check` as appropriate.
5. If `human_decision` is pending, stop and tell the user to run `/idea-s2-decide <slug> <OUTCOME>`.
6. If the authoritative decision is `LOOP-S2`, `RETURN-S1`, `PARK-METHOD`, `PARK-PRIORITY`, or `STOP-DUPLICATE`, do not advance. Summarize the current outcome.
7. If and only if the authoritative sidecar has a dated `human_decision: ADVANCE-S3`, the gate is current, and cache is consistent, formulate exactly 1 main research question, max 3 sub-questions, hypotheses, 1 candidate identification strategy, Frontier Position, and S2 Conditions Carried Forward.
8. If S3 changes the Scope Card's core axes, invalidate the gate and return to LOOP-S2 instead.
9. Set status=question, checkpoint_pending=true, update index and append log.

`question → data-search`:
- Run dataset search as specified in `CLAUDE.md`.
- Prefer credible exogenous shocks, discontinuities, policy/platform changes, staggered rollouts, or other quasi-experimental variation before forcing a causal design.
- S4 validates access/variables/sample and may download data; S2 researchability does not.

Later transitions follow `CLAUDE.md`.
