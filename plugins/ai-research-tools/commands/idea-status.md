You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md` in the idea vault.

Perform a STATUS CHECK.

1. Prefer `ideas/_frontmatter_cache.md` for speed, but include S2 sidecar frontmatter when present.
2. If cache is missing/stale, regenerate by reading only idea frontmatter and S2 sidecar frontmatter.
3. For each idea show slug, title, status, priority, updated, checkpoint, s2_review, s2_gate_outcome, gate_phase, ai_readiness, human_decision, dirty/stale, open blockers if recorded, and next action.
4. If idea cache conflicts with sidecar authoritative fields, show `CACHE-CONFLICT` and mark it as blocking `/idea-next`.
5. Group: Ready for Human Gate Decision, Waiting for Review, In Progress, Captured, Parked, Done, Archived.
6. Update `ideas/index.md` only from cache/sidecar facts; never infer human decisions.
