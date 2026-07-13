You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md`.

Perform REVISE IDEA for the provided slug.

1. Read the idea and any S2 sidecar.
2. If revision changes population, treatment/exposure, outcome, mechanism, claim type, candidate contribution, or closest literature family: increment/suggest scope_version, recompute/suggest scope_hash, mark gate_dirty=true, ai_readiness=NOT_READY, human_decision=pending, and append Decision / Invalidation History. Return to the earliest affected phase, usually `pkb_evidence` or earlier.
3. If revision only adds readings/searches/clarifications: append Search Log or Evidence; mark synthesis dirty; do not change scope version.
4. Never delete old search/evidence/history or overwrite human fields.
5. Update index/cache and append `[IDEA-REVISE YYYY-MM-DD] slug: <slug> → re-ran stage: <stage>`.
