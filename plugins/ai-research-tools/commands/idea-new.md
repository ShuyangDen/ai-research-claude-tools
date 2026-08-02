You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md` in the idea vault.

Default behavior: capture only. Run S2 Quick Scan only when the user explicitly asks to explore now.

1. Ask for idea description, domain, priority, explore now vs capture only, and origin when it is not evident.
2. Classify `idea_origin` as `human`, `hybrid`, or `ai_generated`. Human means the user supplied the core question/mechanism even if AI structures or searches it; hybrid means AI materially supplied the core mechanism to a user seed; AI-generated means the central proposal originated from `/idea-scout` or another AI proposal. If ambiguous, state the proposed classification and ask. Never silently label AI prose as human-authored.
3. Create `ideas/<slug>.md` from `ideas/_template.md`; preserve the original proposer wording in `Original Idea` and complete `Origin & Provenance`. For scout candidates, require `origin_run_id` and `origin_candidate_id`. Origin is immutable after creation. A missing origin on an old file is read as `legacy_unclassified`, never guessed or bulk-migrated.
4. Capture only: set status=capture, checkpoint_pending=false, s2_review=none, s2_gate_outcome=null; update index and append `[IDEA-NEW YYYY-MM-DD] slug: <slug> -> captured; origin: <idea_origin>; run: <origin_run_id|null>; candidate: <origin_candidate_id|null>`.
5. Explore now: run Quick Scan only: max 5 papers, max 3 candidate openings/tensions/possible deltas. Do not write verified gap, novelty, S3 question, or ADVANCE-S3. Set status=explore, checkpoint_pending=true, s2_review=quick, s2_gate_outcome=pending; update index and append the provenance-bearing log event.
6. Tell the user Full S2 Gate requires `/idea-s2-full <slug> start` before S3. An AI-generated idea remains excluded from preference projection until the authoritative S2 outcome is `ADVANCE-S3`.
