# Idea Pipeline — Research Idea Management System
**v2.7**

A Claude Code–powered system for managing economics research ideas through a structured pipeline: from raw intuition to data-ready research proposal.

## What it includes

- **JMP Idea vault** — Obsidian vault tracking research ideas through 6 pipeline stages
- **Personal Knowledge Wiki vault** — Obsidian vault ingesting paper exports into concept wiki pages
- **Projects vault** — Obsidian vault tracking ongoing research projects
- **21+ global commands** — installed to `~/.claude/commands/` for use in any Claude Code session
- **Config templates** — machine_paths.md, Zotero config, rules

## The 21+ commands

| Command | Purpose |
|---------|---------|
| `/idea-help` | **Start here** — shows what you can do right now based on current pipeline state |
| `/idea-new` | Capture a new research idea (default: capture-only, no auto-explore) |
| `/idea-socratic <slug>` | Refine a raw idea through structured 5-layer questioning |
| `/idea-challenge <slug>` | Stress-test an idea with 3-lens critical evaluation |
| `/idea-next <slug>` | Transition guard for checkpoint-safe advancement; S3 requires a completed Full S2 Gate and explicit human `ADVANCE-S3` decision |
| `/idea-s2-full <slug> start\|resume\|status\|check` | Create, resume, inspect, or validate the stateful Full S2 Literature Gate sidecar |
| `/idea-s2-decide <slug> <OUTCOME>` | Record an explicit human gate outcome such as `ADVANCE-S3`, `LOOP-S2`, `PARK-PRIORITY`, or `STOP-DUPLICATE` |
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
         → /idea-socratic <slug>       (optional, recommended for vague ideas)
         → /idea-s2-full <slug> start  (Full S2 Gate; PKB-first literature review)
         → human scope approval + reading of high-threat papers
         → /idea-s2-full <slug> resume
         → /idea-s2-decide <slug> ADVANCE-S3
         → /idea-next <slug>           (formal research question)
         → /idea-challenge <slug>      (recommended before data-search)
         → /idea-next <slug>           (data search)
         → /idea-next <slug>           (data prep)
         → /idea-next <slug>           (report)

After reading a paper → tell Trevor "我们读完了"
                      → Trevor runs /paper-done <slug> automatically
```

## v2.7 Changes

- Adds a stateful S2 Full Literature Gate before S3 for economics JMP idea development.
- Splits S2 into lightweight Quick Scan and audited Full Gate: Quick Scan can surface leads, but cannot certify novelty or generate a formal S3 question.
- Makes the personal knowledge base the first retrieval layer through PKB-A context recall and PKB-B scope-constrained evidence search.
- Adds `/idea-s2-full` and `/idea-s2-decide` commands plus matching Codex skills.
- Converts `/idea-next` into a transition guard that blocks S3 when gates are missing, dirty, stale, abstract-only, cache-conflicted, or awaiting human decision.
- Adds `ideas/_s2_gate_template.md` schema v2 and `system/literature_sources.yml`.
- Preserves existing ideas and notes; no bulk migration is required.

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
