# Personal Knowledge Wiki

This vault is a personal knowledge base built from paper exports, notes, and study sessions.
It uses a wiki pattern: concept pages with cross-links, maintained by `/wiki-ingest`.

---

## Directory Layout

```
/
├── CLAUDE.md          ← this file
├── sources/           ← exported paper summaries and notes (input to wiki)
├── wiki/
│   ├── index.md       ← master list of all wiki pages
│   ├── log.md         ← append-only ingest log
│   └── <Concept>.md   ← one page per concept/method/person
```

---

## Wiki Page Format

```markdown
---
tags: [wiki, <topic>]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <Concept Name>

## Definition
[1–2 sentences: what this is]

## Key Properties
- ...

## When to Use
[Context: which problems, which papers use this]

## Cross-Links
- [[RelatedConcept1]]
- [[RelatedConcept2]]

## Sources
- `sources/<slug>.md` — paper that introduced this concept
```

---

## Ingest Protocol (`/wiki-ingest`)

1. Read `wiki/log.md` to find already-ingested sources
2. List `sources/` — identify new files
3. For each new source: extract concepts → update or create wiki pages → update index → append to log
4. Report what was created and updated

**Rule**: Never remove existing content from wiki pages. Only add or cross-link.

---

## Index Format (`wiki/index.md`)

```markdown
# Wiki Index

| concept | tags | created | updated |
|---------|------|---------|---------|
| [[DifferenceInDifferences]] | causal-inference, econometrics | 2026-01-15 | 2026-03-20 |
```
