# Session Snapshot
Last updated: {{INSTALL_DATE}}

## Current State
**No active paper.** Awaiting first paper from user.

response_mode: compact

## Learner Profile (compressed)
*(Filled in by Trevor after first session based on user's background and learning style.)*

## Pending Actions
*(None)*

## Completed Papers
0 total. Full list in `tutor/completed_papers.md`.

## When New Paper Arrives
1. Read `tutor/system.md` and preserve the strict order: Phase 0 orientation/read-depth decision -> Phase 1 math-necessity gate (waive known foundations) -> Phase 2 complete story map
2. Convert PDF: `python -m markitdown "pdfs/<paper.pdf>" -o "text/<slug>.md"` (use markitdown, not pdftotext)
3. Check `textbooks/index/<slug>/paper_relevance.md` for each textbook
4. Update this snapshot with new paper info before session ends
5. On full/selective/rough/skip completion, record `tutor/reading_feedback.jsonl`
