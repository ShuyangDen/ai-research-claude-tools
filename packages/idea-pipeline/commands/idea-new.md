You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md` in the idea vault.

Default behavior: capture only. Run S2 Quick Scan only when the user explicitly asks to explore now.

1. Ask for idea description, domain, priority, and explore now vs capture only.
2. Create `ideas/<slug>.md` from `ideas/_template.md`; preserve the user's Original Idea wording.
3. Capture only: set status=capture, checkpoint_pending=false, s2_review=none, s2_gate_outcome=null; update index and append `[IDEA-NEW YYYY-MM-DD] slug: <slug> → captured`.
4. Explore now: run Quick Scan only: max 5 papers, max 3 candidate openings/tensions/possible deltas. Do not write verified gap, novelty, S3 question, or ADVANCE-S3. Set status=explore, checkpoint_pending=true, s2_review=quick, s2_gate_outcome=pending; update index and append log.
5. Tell the user Full S2 Gate requires `/idea-s2-full <slug> start` before S3.
