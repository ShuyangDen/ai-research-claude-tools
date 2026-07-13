# Idea Pipeline — Research Idea Management System

**v3.0**

A source-grounded research-idea workflow for economics: capture an intuition, build an audited literature view, sharpen a question, find data, and preserve decisions without losing provenance.

## What it includes

- **JMP Idea vault** — ideas, resumable S2 gates, compact chat sessions, and decisions
- **Personal Knowledge Base** — canonical paper source records plus rebuildable concept views
- **Projects vault** — ongoing research-project maps
- **Global workflow commands** — Claude commands and generated Codex skill adapters from one release manifest
- **Private machine config** — installed from public `.example` files; real paths and credentials stay outside this repository

## Main commands

| Command | Purpose |
|---------|---------|
| `/idea-help` | Show the next valid actions |
| `/idea-new` | Capture a new idea without forced auto-exploration |
| `/idea-chat <slug> [mode]` | Default bounded conversation: clarify, literature, mechanism, identification, data, challenge, or decision |
| `/idea-socratic <slug>` | Optional concise Socratic mode of idea-chat |
| `/idea-challenge <slug>` | Stage a single-agent, evidence-bounded stress test |
| `/idea-next <slug>` | Advance through guarded checkpoints |
| `/idea-s2-full <slug> start\|resume\|status\|check` | Run or inspect the audited Full S2 Literature Gate |
| `/idea-s2-decide <slug> <OUTCOME>` | Record an explicit human gate decision |
| `/idea-revise <slug>` | Revise the current stage while preserving gate rules |
| `/idea-status` | Refresh and inspect idea status |
| `/idea-archive <slug>` | Archive with a reason |
| `/idea-develop <slug>` | Compatibility alias for `/idea-chat <slug> auto` |
| `/idea-extract-from-source <source.md>` | Stage claim-linked idea deltas for confirmation |
| `/idea-retrospective <slug>` | Generate an advisor-facing retrospective |
| `/idea-zotero-add <slug> <doi>` | Add a paper to an idea's Zotero collection |
| `/wiki-ingest [source.md]` | Hash-based source-to-concept projection |
| `/paper-done <slug>` | Resumable full-read completion transaction |
| `/paper-rough-done <slug>` | Resumable selective-read completion transaction |
| `/update-researcher-profile` | Project approved idea and reading signals to Paper Tracker |
| `/project-init`, `/project-sync`, `/project-status` | Track ongoing research projects |

## Typical workflow

```text
New idea → /idea-new
         → /idea-chat <slug> clarify        (or optional Socratic mode)
         → /idea-s2-full <slug> start
         → human scope approval + high-threat reading
         → /idea-s2-full <slug> resume
         → /idea-s2-decide <slug> ADVANCE-S3
         → /idea-next <slug>
         → /idea-chat <slug> identification|data|decision

Finished paper → /paper-done <slug>
               → canonical source claims + hash-based wiki projection
               → confirmed reading feedback + staged idea delta
               → local profile projection for the next tracker run
```

## v3.0 changes

- Adds target-first `/idea-chat` with hard retrieval caps, claim provenance, compact answers, and staged session deltas.
- Makes develop, Socratic, and challenge behaviors bounded modes rather than independent context protocols.
- Adds source schema v2 with stable paper/claim IDs, locators, read coverage, and hash-based wiki ingest.
- Converts paper completion into a durable run with resume/repair semantics and one writer per artifact.
- Closes the loop with structured ReadingFeedback and a versioned recommendation-profile projection.
- Keeps ordinary chat single-agent. S2/Challenge sub-agents and single-vs-multi A/B evaluation remain disabled until a later evaluation phase.

## Acknowledgements

Earlier Socratic and Devil's Advocate patterns were inspired by the [academic-research-skills](https://github.com/Imbad0202/academic-research-skills) project by Cheng-I Wu. This package keeps those modes optional and lightweight; reliable state, provenance, and retrieval boundaries take priority over agent count.

## Installation

Use the repository-level `INSTALL.md`. For standalone setup, see `SETUP.md`.

Zotero integration is optional. Copy the public config example to the private machine path, then add your own API key and user ID.
