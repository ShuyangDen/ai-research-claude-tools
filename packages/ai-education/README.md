# AI Education — Socratic Paper Tutor

A Claude Code–powered Socratic tutor for reading economics papers. Uses two AI personas (Trevor and Mira), a prerequisites alignment protocol, and a visualization system to guide deep paper understanding.

## What it does

- **Adaptive Reading Order**: Starts with a plain-language orientation and `精读` / `定向粗读` / `跳过` decision, runs a math-necessity gate that waives already-mastered foundations, then gives a complete paper story before selective technical deep dives.
- **Socratic Method**: Never gives answers before asking questions. Guides you to rediscover key intuitions step by step.
- **Critical Reflection (Phase 3)**: Records all critiques and open questions with origin labels (independently-identified / guided / tutor-added). These feed directly into your research idea pipeline.
- **Knowledge Base Export**: `/paper-done <slug>` exports notes to your Obsidian wiki and extracts new research ideas automatically.
- **Recommendation Feedback Loop**: terminal full/selective/rough/skip decisions are recorded in `tutor/reading_feedback.jsonl`; `paper_preferences.md` is a generated view for researcher-profile sync.
- **Canonical Queue Sync**: `papers/queue_sync.py` updates tracker `queue_state.jsonl` first, then regenerates the Markdown view, so completed or skipped papers are not resurrected.
- **Response Modes**: `compact` (default), `default`, and learner-requested `deep` modes keep Socratic tutoring focused; the initial orientation and complete story map are protected from destructive over-compression.
- **Capacity-Bounded Batch Triage**: `/paper-batch-triage` compares at most ten paper cards in one decision, then routes only confirmed `deep` or `targeted` papers into Trevor.
- **Cluster Synthesis**: `/paper-cluster-synthesis` compares claims, identification, contradictions, and the frontier delta across three to eight papers without pretending the learner read all of them.
- **Taste Calibration**: structured reason codes, pairwise choices, predicted-versus-realized value, and held-out ranking checks measure whether recommendations are actually learning the researcher's taste.
- **Research Reasoning Memory**: compact, provenance-aware records preserve the learner's observable measurement, mechanism, identification, comparison, and stopping moves without storing raw chain-of-thought.

## Installation

Run `INSTALL.md` from the parent `ai-research-claude-tools/` folder — it handles all setup including this package.

For standalone installation of this package only, see `SETUP.md`.

## Usage

1. Put paper PDFs in `papers/pdfs/`
2. Open Claude Code in this project folder
3. Claude enters Trevor mode automatically (reads `CLAUDE.md`)
4. When done: `/paper-done <slug>` to export and sync everything
5. Run `/sync-reading-queue` after a terminal queue decision if the finish command could not reach GitHub
