# AI Research Claude Tools

A suite of Claude Code鈥損owered tools for economics PhD research. Install everything with one command.

## Packages

| Package | What it does |
|---------|-------------|
| **ai-education** | Socratic paper tutor. Two AI personas (Trevor/Mira) guide you through economics papers using the Socratic method. Exports notes to your knowledge base automatically. |
| **idea-pipeline** | Research idea management. 20 global commands + 3 Obsidian vaults. From raw intuition 鈫?literature review 鈫?research questions 鈫?data 鈫?report. |
| **paper-tracker** | Weekly paper digest. GitHub Actions workflow searches OpenAlex, arXiv, NBER, IZA and emails you a filtered digest of relevant papers every Monday. |

## Installation

1. Clone or download this repo:
   ```bash
   git clone https://github.com/<username>/ai-research-claude-tools.git
   ```
   Or download and unzip.

2. Open Claude Code in this folder:
   ```bash
   cd ai-research-claude-tools
   claude
   ```

3. Claude automatically reads `INSTALL.md` and walks you through the setup interactively.

The installer:
- Detects if you're a fresh install, v1 user, or upgrading from v2+
- Asks for your folder paths interactively
- Migrates v1 data automatically (paper_notes.md split, config merging)
- Generates a personalized `USAGE.md` with your actual paths filled in
- Runs a security scan before writing any files

## Requirements

- Claude Code (claude.ai/code)
- Python 3.9+ (for PDF tools)
- `pip install pdfplumber markitdown` (for ai-education)
- A Zotero account (optional, for reference management)
- A GitHub account (for paper-tracker automation)

## Upgrading

```bash
git pull
claude   # Claude reads INSTALL.md and runs upgrade mode
```

Your idea files, paper notes, and learner profile are never touched during upgrades.

## What's new in v2.7.0

- Stateful S2 literature review gate with `/idea-s2-full` and explicit `/idea-s2-decide` human decisions.
- `/idea-next` is now a transition guard: Full Gates are not created ad hoc, Quick Scan cannot advance to S3, and S3 requires an authoritative `ADVANCE-S3` decision.
- S2 Gate schema v2 adds PKB-A/B passes, local retrieval manifests, known-item recall, relationship ledgers, synthesis claim ledgers, stopping certificates, and decision history.
- Added `system/literature_sources.yml` as a starter economics frontier-search registry.
- Installer security-scan examples now use generic sensitive-pattern checks instead of literal personal identifiers.

## License

MIT. Customize freely for your research.
