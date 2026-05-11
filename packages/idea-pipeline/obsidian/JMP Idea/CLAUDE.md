# Research Idea Pipeline — JMP Idea Vault

This vault tracks research ideas for an economics PhD student.
It uses an LLM-assisted pipeline to move from raw intuitions to data-ready research proposals.

---

## Directory Layout

```
/
├── CLAUDE.md               ← this file (schema & pipeline rules)
├── sources/                ← slides, papers, notes related to ideas (READ ONLY)
├── ideas/
│   ├── index.md            ← kanban of all ideas by status
│   ├── log.md              ← append-only operation log
│   ├── _template.md        ← template for new ideas
│   ├── _frontmatter_cache.md  ← cache for fast status checks
│   ├── _profile_cache.json ← mtime cache for update-researcher-profile
│   ├── data/               ← downloaded datasets, organized by idea slug
│   ├── reports/            ← preliminary analysis reports
│   └── <slug>.md           ← one page per idea
```

---

## Pipeline Stages

Each idea moves through these stages in order:

| Stage | Name | Description |
|-------|------|-------------|
| S1 | **capture** | Idea submitted and structured |
| S2 | **explore** | Literature review + similar research found |
| S3 | **question** | Research questions and hypotheses refined |
| S4 | **data-search** | Datasets discovered and evaluated |
| S5 | **data-prep** | Data downloaded and cleaned |
| S6 | **report** | Preliminary analysis report generated |
| — | **done** | User decided to proceed with full project |
| — | **archived** | User decided not to pursue |

**Human checkpoints** (Claude pauses and waits for user review):
- After S2 (explore) — user reviews literature findings
- After S3 (question) — user confirms research questions
- After S4 (data-search) — user selects datasets to download

---

## Idea Page Format

Every idea page uses this frontmatter:

```yaml
---
tags: [idea]
status: capture
created: YYYY-MM-DD
updated: YYYY-MM-DD
priority: medium          # low / medium / high
domain: economics         # research field
checkpoint_pending: false  # true = waiting for user review
---
```

Cross-linking: use `[[PageName]]` for Obsidian wiki links.
At the bottom of each page, maintain a `## Related` section.

---

## Operations

### CREATE NEW IDEA (`/idea-new`)

Default behavior: **capture only** (no S2). Only run S2 if user explicitly requests it.

1. Ask user for: idea description, domain, priority, and whether to explore now or capture only
2. Create `ideas/<slug>.md` from `_template.md`; fill "Original Idea" section
3. If capture only: set status=capture, checkpoint_pending=false; tell user to run `/idea-next <slug>` when ready
4. If explore now: run S2 with **hard cap — max 5 papers, max 3 gaps**; set status=explore, checkpoint_pending=true
5. Update `ideas/index.md` and `ideas/log.md`

### ADVANCE IDEA (`/idea-next <slug>`)

Read the current `status` from the idea's frontmatter, then:

**capture → explore:**
- S2 literature review with **hard cap: max 5 papers, max 3 gaps**
- Set status=explore, checkpoint_pending=true

**explore → question:**
- Formulate **exactly 1 main research question + max 3 sub-questions** + hypotheses + 1 ID strategy
- Fill "Research Questions" section
- Set status=question, checkpoint_pending=true

**question → data-search:**
- Three-source dataset search; present **top 5 datasets only**:
  1. Claude's knowledge: known public datasets
  2. Fetch awesome-public-datasets README: `curl -s https://raw.githubusercontent.com/awesomedata/awesome-public-datasets/master/README.rst`
  3. Economics-specific sources (IPUMS, BLS, Census, PSID, etc.)
- Fill "Datasets" table: name, source, URL, size, relevance (1-5), notes
- Set status=data-search, checkpoint_pending=true

**data-search → data-prep:**
- Download and clean the user-approved dataset(s) into `ideas/data/<slug>/`
- Document cleaning steps in the idea page
- Set status to `data-prep`

**data-prep → report:**
- Generate a preliminary analysis report at `ideas/reports/<slug>-report.md`
- Report should include: descriptive stats, key distributions, preliminary correlations, data quality notes, suggested next steps
- Set status to `report`, checkpoint_pending: false
- Tell user: "Report complete. Review [[slug-report]] and decide: proceed / archive."

### REVISE IDEA (`/idea-revise <slug>`)

1. Ask user: what needs to change?
2. Re-run the current stage with the user's feedback incorporated
3. Set checkpoint_pending: true again

### STATUS CHECK (`/idea-status`)

1. Read `ideas/_frontmatter_cache.md` — do NOT open individual idea files
2. If cache is missing or stale, regenerate it by reading only the frontmatter blocks of each idea file
3. Output grouped table: Waiting for review → In Progress → Captured → Done → Archived

### ARCHIVE IDEA (`/idea-archive <slug>`)

1. Ask: reason for archiving?
2. Update status to `archived`, record reason in "Decision Log"
3. Update index and log

---

## Index Format (`ideas/index.md`)

```markdown
## Waiting for Review 🔴
- [[slug]] — title — Stage: explore — Priority: high

## In Progress
- [[slug2]] — title — Stage: data-prep

## Done ✅
## Archived
```

---

## Log Format (`ideas/log.md`)

Append-only. Never edit existing entries. Add new entries at the bottom.

```
[IDEA-NEW YYYY-MM-DD] slug: <slug> → created, auto-explored
[IDEA-NEXT YYYY-MM-DD] slug: <slug> → advanced: explore→question
[IDEA-REVISE YYYY-MM-DD] slug: <slug> → re-ran stage: question
[IDEA-ARCHIVE YYYY-MM-DD] slug: <slug> → reason: <reason>
```

---

## Economics-Specific Dataset Sources

When doing S4 (data-search) for economics research, always check:

**Labor / Human Capital:**
- IPUMS CPS, APS (ipums.org) — occupation, wages, hours, education
- BLS Occupational Employment Statistics — wage distributions by occupation
- PSID (Panel Study of Income Dynamics) — longitudinal household
- O*NET — occupation task content, AI exposure measures
- Felten et al. AI exposure index — AI substitutability by occupation

**Academic Research / Science of Science:**
- OpenAlex (openalex.org) — 250M+ scholarly works, free API
- Semantic Scholar — papers, citations, author info
- Web of Science / Scopus — p-values, statistical significance in papers
- NBER Working Papers — economics preprints with metadata
- AEA RCT Registry — registered experiments

**Education / Students:**
- PISA, TIMSS — international student assessments
- IPEDS — US higher education data
- Common Core of Data — K-12

**General:**
- World Bank Open Data
- FRED (Federal Reserve Economic Data)
- OECD.Stat

---

## Zotero Integration

Zotero config path: read from `~/.claude/machine_paths.md` → "Research Idea Pipeline → Zotero config"
Read `api_key` and `user_id` from that config file. Idea collection keys are stored in `idea_collections` map.

**When adding a new idea**, create a new sub-collection via:
```
POST https://api.zotero.org/users/{user_id}/collections
[{"name": "<slug>", "parentCollection": false}]
```
Then save the new key to the config file under `idea_collections.<slug>`.

**Adding papers to Zotero:**
- `/idea-zotero-add <slug> <doi-or-url>` — add a single paper (user-triggered)
- During `explore → question` transition: auto-sync all DOI papers from S2 literature section
- Use Unpaywall API to check OA status before attempting PDF attachment
- Mark papers in idea page: ✅ = in Zotero, ⬜ = needs manual download

**Paper item format for Zotero API:**
```json
{
  "itemType": "journalArticle",
  "title": "...",
  "creators": [{"creatorType": "author", "firstName": "...", "lastName": "..."}],
  "DOI": "...",
  "publicationTitle": "...",
  "volume": "...", "issue": "...", "pages": "...",
  "date": "YYYY",
  "collections": ["<collection_key>"]
}
```
