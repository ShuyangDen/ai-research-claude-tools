---
name: idea-new
description: "Use this skill when the user invokes $idea-new, /idea-new, asks to run idea-new, or asks to capture a new research idea. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-new

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-new.md","source_sha256":"978b02e3305815445a06b92c401f88662911201f5ff3197d02b1110459f662e1","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-new
- /idea-new
- Natural language requests to capture a new research idea

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-new.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

You are managing a research idea pipeline for an economics PhD student.

Step 0: Read `~/.claude/machine_paths.md`; follow `CLAUDE.md` and `AGENTS.md` in the idea vault.

Default behavior: capture only. Run S2 Quick Scan only when the user explicitly asks to explore now.

1. Ask for idea description, domain, priority, and explore now vs capture only.
2. Create `ideas/<slug>.md` from `ideas/_template.md`; preserve the user's Original Idea wording.
3. Capture only: set status=capture, checkpoint_pending=false, s2_review=none, s2_gate_outcome=null; update index and append `[IDEA-NEW YYYY-MM-DD] slug: <slug> → captured`.
4. Explore now: run Quick Scan only: max 5 papers, max 3 candidate openings/tensions/possible deltas. Do not write verified gap, novelty, S3 question, or ADVANCE-S3. Set status=explore, checkpoint_pending=true, s2_review=quick, s2_gate_outcome=pending; update index and append log.
5. Tell the user Full S2 Gate requires `/idea-s2-full <slug> start` before S3.
