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
