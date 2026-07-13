# Personal Knowledge Base

This vault stores source-grounded paper knowledge for idea development. Paper source records are canonical; concept wiki pages and search indexes are rebuildable projections.

## Ownership

- `sources/<slug>.md`: canonical paper/source record, written by the paper completion workflow.
- `wiki/<Concept>.md`: derived concept view, written only by wiki ingest.
- `wiki/index.md`: derived navigation index.
- `wiki/log.md`: append-only ingest events with input content hashes.
- Human-authored text under `## Human Notes` is never overwritten by a projector.

Only one writer may update an artifact in a run. Retrieval/chat workers are read-only.

## Source schema v2

Create new source records from `sources/_template.md`. Required metadata includes a stable `paper_id`, available DOI/OpenAlex/arXiv/Zotero identifiers, read depth, coverage, source-note path, and source-note SHA-256.

Claims use stable IDs and one of four types:

- `reported_result`: a result explicitly reported by the paper
- `author_interpretation`: the authors' explanation or framing
- `researcher_reflection`: the learner/researcher's critique or connection
- `agent_inference`: a new inference that is not stated by the source

Every consequential claim needs a source locator. Unknown provenance must be recorded as unknown, not invented. Never silently convert an inference into a paper result.

## Wiki page format

```markdown
---
schema_version: 2
tags: [wiki, <topic>]
created: YYYY-MM-DD
updated: YYYY-MM-DD
derived: true
---

# <Concept Name>

## Definition

## Assertions
| Assertion ID | Statement | Claim ID | Relationship | Source | Locator | Status |
|--------------|-----------|----------|--------------|--------|---------|--------|

## Conflicts and Boundaries

## Cross-Links

## Human Notes
```

Do not merge conflicting claims into one smooth paragraph. Preserve both, label their relationship, and identify scope/version differences. Mark outdated assertions `superseded`; do not erase their provenance.

## Hash-based ingest

Ingest state is keyed by the SHA-256 of source content, not by filename alone. A changed source must be reconsidered even if it already appears in `wiki/log.md`.

For each changed source:

1. Validate source metadata and claim locators.
2. Update or create concept assertions with claim IDs.
3. Preserve Human Notes and unresolved conflicts.
4. Update `wiki/index.md` if navigation changed.
5. Append `[INGEST ...] source: <file> | sha256: <hash> | created: ... | updated: ... | superseded: ...`.

The wiki is read through claim IDs during idea chat. Full source records are loaded only for the highest-ranked claims or when verification is needed.
