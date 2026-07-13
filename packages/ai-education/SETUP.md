# AI Education — Standalone Setup Guide

This guide installs the AI Education Socratic Tutor package. If you're using the master INSTALL.md from `ai-research-claude-tools/`, you don't need this file — the master installer handles everything.

## Prerequisites

- Claude Code installed
- Python 3.10+ (for PDF text extraction and structured feedback/queue helpers)
- `pip install pdfplumber markitdown` (for textbook indexing and PDF conversion)

## Step 1 — Choose your installation folder

Pick an empty folder for the AI Education project. Example:
- Windows: `C:\Users\<you>\AI_education`
- Mac/Linux: `~/AI_education`

Copy all files from this `packages/ai-education/` folder into that location.

## Step 2 — Configure machine_paths.md

Open `~/.claude/machine_paths.md` (create it if it doesn't exist). Add or update:

```markdown
## AI Education Project
- **Project root**: `<YOUR_AI_EDUCATION_PATH>`
- **Papers**: `<YOUR_AI_EDUCATION_PATH>\papers\`
- **Textbooks**: `<YOUR_AI_EDUCATION_PATH>\textbooks\`
```

Also add the Obsidian wiki path if you're using the personal knowledge wiki:

```markdown
## Personal Knowledge Wiki
- **Vault**: `<YOUR_OBSIDIAN_ROOT>\personal knowledge skill`
```

## Step 3 — Connect to idea pipeline (optional)

In `CLAUDE.md`, update the researcher_profile path:
- Find: `{{OBSIDIAN_ROOT}}\JMP Idea\researcher_profile.md`
- Replace with your actual JMP Idea vault path

## Step 4 — Open with Claude Code

```bash
cd <YOUR_AI_EDUCATION_PATH>
claude
```

Claude automatically reads `CLAUDE.md` and enters Trevor mode.

## Step 5 — Add your first textbook (optional)

1. Put a textbook PDF in `textbooks/`
2. Claude Code will prompt you to run `/index-textbook <filename.pdf>` if the index is missing
3. The index is built once and reused across sessions

## Folder structure

```
AI_education/
├── CLAUDE.md           ← session bootloader (auto-loaded)
├── AGENTS.md           ← agent configuration
├── papers/
│   ├── pdfs/           ← place paper PDFs here
│   ├── text/           ← converted markdown (auto-generated)
│   ├── notes/          ← per-paper study notes
│   ├── index.md        ← paper status table
│   ├── reading_queue.md  ← generated active compatibility view
│   ├── queue_state.jsonl ← local canonical queue copy (created on sync)
│   └── queue_sync.py     ← deterministic tracker/local merge helper
├── textbooks/
│   ├── scripts/        ← extract_toc.py, read_pages.py
│   └── (index/ folder auto-created when indexed)
└── tutor/
    ├── system.md       ← full protocol reference (loaded on-demand)
    ├── trevor.md       ← Trevor persona
    ├── mira.md         ← Mira persona
    ├── context_snapshot.md  ← session state (updated each session)
    ├── reading_feedback.py    ← canonical feedback recorder/view renderer
    ├── reading_feedback.jsonl ← personal event log (created on first record)
    └── (other tracking files)
```

## Reading feedback and queue sync

Terminal full/selective/rough/skip decisions are recorded with
`/record-reading-feedback <slug>`. Run `/sync-reading-queue` to merge local
manual rows and terminal decisions into the paper tracker's canonical
`queue_state.jsonl`; `reading_queue.md` is regenerated and should not be pushed
by itself.
