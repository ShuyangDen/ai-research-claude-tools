# Idea Pipeline — Research Idea Management System
**v2.4**

A Claude Code–powered system for managing economics research ideas through a structured pipeline: from raw intuition to data-ready research proposal.

## What it includes

- **JMP Idea vault** — Obsidian vault tracking research ideas through 6 pipeline stages
- **Personal Knowledge Wiki vault** — Obsidian vault ingesting paper exports into concept wiki pages
- **Projects vault** — Obsidian vault tracking ongoing research projects
- **19 global commands** — installed to `~/.claude/commands/` for use in any Claude Code session
- **Config templates** — machine_paths.md, Zotero config, rules

## The 19 commands

| Command | Purpose |
|---------|---------|
| `/idea-help` | **Start here** — shows what you can do right now based on current pipeline state |
| `/idea-new` | Capture a new research idea (default: capture-only, no auto-explore) |
| `/idea-socratic <slug>` | Refine a raw idea through structured 5-layer questioning |
| `/idea-challenge <slug>` | Stress-test an idea with 3-lens critical evaluation |
| `/idea-next <slug>` | Advance an idea one pipeline stage |
| `/idea-revise <slug>` | Re-run the current stage with new feedback |
| `/idea-status` | Refresh the kanban and show all idea statuses |
| `/idea-archive <slug>` | Archive an idea with a reason |
| `/idea-develop <slug>` | Deep-dive an idea with cross-system context |
| `/idea-retrospective <slug>` | Generate a PDF retrospective for a PhD advisor |
| `/idea-zotero-add <slug> <doi>` | Add a paper to an idea's Zotero collection |
| `/wiki-ingest` | Ingest new sources into the personal knowledge wiki |
| `/paper-done <slug>` | Full post-session pipeline: export → wiki → ideas (profile sync separate) |
| `/update-researcher-profile` | Distill idea pipeline into researcher_profile.md (run in fresh session) |
| `/project-init <slug> <path>` | Initialize tracking for a new research project |
| `/project-sync <slug>` | Scan for file changes and update project map |
| `/project-status <slug>` | Interactive project discussion hub |

## Typical workflow

```
New idea → /idea-new
         → /idea-socratic <slug>    (optional, recommended for vague ideas)
         → /idea-next <slug>        (literature exploration)
         → /idea-challenge <slug>   (recommended before data-search)
         → /idea-next <slug>        (research question)
         → /idea-next <slug>        (data search)
         → /idea-next <slug>        (data prep)
         → /idea-next <slug>        (report)

After reading a paper → tell Trevor "我们读完了"
                      → Trevor runs /paper-done <slug> automatically
```

## v2.4 Changes

- **`/idea-socratic`**: Removed role persona (was counterproductive). Replaced with direct behavior constraints. Removed `[Q:TAG]` internal labeling system (no effect on output). Added 15-turn progress checkpoints to prevent context loss in long dialogues.
- **`/idea-challenge`**: Added context-aware next-step guidance after evaluation.
- **`/idea-next`**: Removed raw `curl` of awesome-public-datasets (~400 KB). Replaced with targeted knowledge-based search. Added S1.5 awareness: if Socratic Refinement insights exist, uses them as basis for RQ formulation.
- **`/idea-new`**: Fixed: now defaults to capture-only (was auto-exploring). Added hard cap (max 5 papers / 3 gaps) when explore is chosen.
- **`/paper-done`**: Phase 5 profile sync decoupled — no longer runs automatically in the same context. Suggests running in fresh session. Added natural language trigger documentation.
- **`/idea-help`** (new): State-aware command menu. Reads only the frontmatter cache (~500 tokens). Shows what is actionable right now.
- **`ai-education CLAUDE.md`**: Trevor now states the current actionable item on session start. Trevor recognizes natural language triggers like "我们读完了" and runs `/paper-done` automatically.
- **Vault CLAUDE.md**: Added S1.5 Socratic Refinement and Challenge Panel rules and log tag formats. Fixed awesome-public-datasets curl.
- **`_template.md`**: Added `## S1.5` and `## Challenge Panel Findings` sections.

## Acknowledgements

Parts of v2.4 — specifically the Socratic questioning structure in `/idea-socratic` and the Devil's Advocate challenge pattern in `/idea-challenge` — were inspired by the [academic-research-skills](https://github.com/Imbad0202/academic-research-skills) plugin by Cheng-I Wu ([@Imbad0202](https://github.com/Imbad0202)). The original ARS project implements a full 13-38 agent research-to-publication pipeline with sophisticated multi-agent review panels and Socratic mentoring. We adapted selected patterns (the 5-layer dialogue structure, intent detection, dialogue health check, and Devil's Advocate severity classification) into a lighter, economics-PhD-specific form.

## Installation

Run `INSTALL.md` from the parent `ai-research-claude-tools/` folder.

For standalone installation, see `SETUP.md`.

## Zotero (optional)

The system integrates with Zotero for paper management. You need:
- A free Zotero account at zotero.org
- A Zotero API key (Settings → Feeds/API → Create new private key)
- Your Zotero user ID (visible in your profile URL)

Zotero integration can be skipped — commands that use it will fall back gracefully.
