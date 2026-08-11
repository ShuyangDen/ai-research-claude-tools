---
name: research-state-backfill
description: "Use this skill when the user invokes $research-state-backfill, /research-state-backfill, asks to reconcile legacy completed papers with the queue, repair missing reading feedback, or migrate past paper notes into reviewable taste signals without inventing human preferences."
---
# research-state-backfill

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/ai-education/.claude/commands/research-state-backfill.md","source_sha256":"f4eed7bfc1525dba830bd53b4a3c967b3c01f67907c970c8f63ef79fe72570b7","workflow_version":"3.4.0"} -->

## Trigger Forms

- $research-state-backfill
- /research-state-backfill
- Natural language requests to backfill completed-paper queue state and confirmed reading preferences

## Codex Execution Rules

- Do **not** read `~/.claude/commands/research-state-backfill.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /research-state-backfill

Reconcile legacy completed papers, queue state, and missing taste feedback
without inventing human preferences. This workflow is dry-run and review-first.

## Read

Resolve machine paths, then inspect:

- `<AI_EDUCATION_PATH>\tutor\completed_papers.md`
- `<AI_EDUCATION_PATH>\papers\notes\*.md`
- `<AI_EDUCATION_PATH>\tutor\reading_feedback.jsonl`
- `<PAPER_TRACKER_PATH>\queue_state.jsonl`

## Stage

1. Match completed papers to queue records by canonical paper ID, URL, normalized
   title, then slug. Never rely on slug alone when a stronger identifier exists.
2. Produce a review table with exact match evidence and proposed terminal state.
3. For completed papers lacking feedback, extract only explicit learner language
   from critical reflections, session summaries, and recorded completion
   decisions. Preserve `independently-identified`, `guided`, and `tutor-added`
   origins.
4. Stage proposed feedback with `needs_human_review: true`. Do not label staged
   proposals as actor `human` and do not project them into the researcher profile.

## Apply after confirmation

Ask for one batch confirmation. After confirmation:

- run `papers\queue_sync.py` so matched papers receive terminal queue state;
- run `/record-reading-feedback` once per confirmed proposal, with
  `source=research-state-backfill`, structured reason codes, and only the fields
  the learner confirmed;
- regenerate `paper_preferences.md`;
- run `/update-researcher-profile` and report the exact number of newly confirmed
  signals.

Never infer a positive taste from mere completion, or a negative taste from a
paper being absent. Never overwrite existing feedback; conflicts require review.
