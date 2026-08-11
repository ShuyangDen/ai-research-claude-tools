# Idea Pipeline — Research Idea Management System

**v3.4**

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
| `/idea-scout [scope]` | Scan recent labor/education economics with secondary econometrics/meta-analysis lanes, fresh abstract-access checks, Tianjin/SUFE tier priors, NBER/IZA/CEPR, and separate attention/crowding signals |
| `/weekly-research-loop` | Turn the current digest, bounded reading, cluster synthesis, and confirmed reasoning memory into 3-4 reviewable weekly candidates |
| `/record-research-reasoning` | Preserve compact, provenance-aware reasoning and idea-feedback events without storing raw chain-of-thought |
| `/idea-feasibility <slug> start\|update\|status\|decide` | Run a two-week data, identification, minimum-artifact, and nearest-paper sprint before Full S2 |
| `/jmp-dashboard` | Keep exactly one primary JMP idea, at most one backup, and one observable next artifact |
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

Recent literature → /idea-scout labor|education|econometrics|meta_analysis|metascience
                  → human candidate selection
                  → /idea-new with immutable AI provenance
                  → optional bounded Quick Scan and human checkpoint

Promising candidate → /idea-feasibility <slug> start
                    → acquire/test data + build one minimum artifact
                    → human continue|pivot|kill
                    → only then Full S2 or primary/backup portfolio role
Weekly cycle → /weekly-research-loop
             → one deep + up to two targeted reads; cluster-only for the rest
             → confirmed reasoning memory + frozen AI ranking
             → 3-4 idea candidates with early-signal, salvage, and kill tests
             → human keep|modify|hold|reject checkpoint
```

## v3.4 changes

- Adds provenance-aware research reasoning and idea-feedback memory with strict separation among taste, feasibility, advisor fit, and candidate outcomes.
- Adds a capacity-bounded weekly research loop that turns digest evidence and paper clusters into three to four human-reviewed candidates.
- Strengthens feasibility gates with time to first informative signal, up-front effort, stopping rules, salvage artifacts, and null-result interpretation.
- Extends held-out taste calibration from paper rankings to idea rankings.

## v3.3 changes

- Adds a pre-S2 empirical feasibility gate and a JMP dashboard with one primary and at most one backup.
- Links active portfolio roles to a human `continue` decision and a tracked execution project.
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
