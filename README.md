# AI Research Tools

A local-first research workflow for finding papers, reading them, preserving source-grounded knowledge, and developing research ideas without mixing personal data into the public tools repository.

## Components

| Component | Responsibility |
|-----------|----------------|
| **Paper Tracker** | Candidate discovery, source health, stable IDs, diversified ranking lanes, and structured queue suggestions |
| **AI Education** | Paper triage/reading, canonical notes, completion depth, and confirmed reading feedback |
| **Idea Pipeline + Personal Knowledge** | Source claims, concept projections, idea conversations, S2 gates, and human decisions |
| **Research Core** | Shared schemas, hashes, durable runs/events, validators, retrieval, profile projection, and doctor |
| **Adapters / plugin** | Generated Claude commands and Codex skills with source hashes and install manifests |

The repository contains tools, schemas, templates, synthetic fixtures, and packaging metadata only. Personal ideas, paper notes, profiles, queues, feedback, source records, and credentials remain in the machine paths configured by the user.

## Closed loop

```text
profile snapshot
  → Paper Tracker discovery/ranking
  → structured reading queue
  → AI Education reading + feedback
  → source claim record + knowledge projection
  → bounded /idea-chat + confirmed idea delta
  → profile projection
  → next tracker run
```

Deterministic state, hashes, retries, and writes belong to Research Core. LLM workflows interpret research content but do not own transaction state. Ordinary idea chat remains single-agent; multi-agent S2/Challenge behavior is reserved for a later A/B evaluation.

## Installation and upgrade

Clone the repository, then follow `INSTALL.md`. The installer/sync tool reads a private `~/.claude/machine_paths.md`, backs up system targets, protects personal-data paths, and records source/destination hashes.

```bash
git clone https://github.com/<username>/ai-research-claude-tools.git
cd ai-research-claude-tools
```

Run doctor and sync in check/dry-run mode before applying an upgrade. Never copy package skeleton data over a personal vault.

```powershell
python scripts\sync_local_install.py --dry-run
python scripts\sync_local_install.py --apply
python scripts\sync_local_install.py --check
```

## Requirements

- Python 3.9+
- Claude Code and/or Codex
- Package-specific Python requirements for PDF/email/tracker features
- Zotero and GitHub are optional integrations

## v3.0 highlights

- Target-first, bounded `/idea-chat` with claim provenance and staged session deltas
- One canonical paper-ID algorithm across discovery, queue sync, reading feedback, and knowledge export
- Queue lifecycle, ReadingFeedback, source schema v2, and five provenance-separated profile signal classes
- Durable, resumable paper completion with planned steps and non-bypassable human checkpoints
- Source-health/degraded-run reporting and diversified recommendation lanes
- 29 generated/validated workflow adapters, a dual-surface repo-local plugin, hashes, backup-aware sync, and install drift checks

See `CHANGELOG.md` for migration details.

## License

MIT.
