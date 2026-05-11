# Idea Pipeline — Research Idea Management System

A Claude Code–powered system for managing economics research ideas through a structured pipeline: from raw intuition to data-ready research proposal.

## What it includes

- **JMP Idea vault** — Obsidian vault tracking research ideas through 6 pipeline stages
- **Personal Knowledge Wiki vault** — Obsidian vault ingesting paper exports into concept wiki pages
- **Projects vault** — Obsidian vault tracking ongoing research projects
- **14 global commands** — installed to `~/.claude/commands/` for use in any Claude Code session
- **Config templates** — machine_paths.md, Zotero config, rules

## The 14 commands

| Command | Purpose |
|---------|---------|
| `/idea-new` | Create a new research idea with auto-literature review |
| `/idea-next <slug>` | Advance an idea one pipeline stage |
| `/idea-revise <slug>` | Re-run the current stage with new feedback |
| `/idea-status` | Refresh the kanban and show all idea statuses |
| `/idea-archive <slug>` | Archive an idea with a reason |
| `/idea-develop <slug>` | Deep-dive an idea with cross-system context |
| `/idea-retrospective <slug>` | Generate a PDF retrospective for a PhD advisor |
| `/idea-zotero-add <slug> <doi>` | Add a paper to an idea's Zotero collection |
| `/wiki-ingest` | Ingest new sources into the personal knowledge wiki |
| `/paper-done <slug>` | Full post-session pipeline: export → wiki → ideas → sync |
| `/update-researcher-profile` | Distill idea pipeline into researcher_profile.md |
| `/project-init <slug> <path>` | Initialize tracking for a new research project |
| `/project-sync <slug>` | Scan for file changes and update project map |
| `/project-status <slug>` | Interactive project discussion hub |

## Installation

Run `INSTALL.md` from the parent `ai-research-claude-tools/` folder.

For standalone installation, see `SETUP.md`.

## Zotero (optional)

The system integrates with Zotero for paper management. You need:
- A free Zotero account at zotero.org
- A Zotero API key (Settings → Feeds/API → Create new private key)
- Your Zotero user ID (visible in your profile URL)

Zotero integration can be skipped — commands that use it will fall back gracefully.
