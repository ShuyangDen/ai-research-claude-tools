Run the complete post-session pipeline for a finished paper: export notes → wiki ingest → idea extraction (one confirmation) → researcher profile sync.

## Usage

`/paper-done <slug>`

Where `<slug>` is the paper slug (e.g. `w33941`, `qjae044`).

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- AI Education root (under "AI Education Project → Project root") → `<AI_EDUCATION_PATH>`
- Wiki vault (under "Personal Knowledge Wiki → Vault") → `<WIKI_VAULT>`
- Idea vault (under "Research Idea Pipeline → Vault") → `<IDEA_VAULT>`

---

## Phase 1 — Export (automatic, no confirmation needed)

### 1a. Read source notes

Read `<AI_EDUCATION_PATH>\papers\notes\<slug>.md`.

If not found: stop and tell user "No notes file at papers/notes/<slug>.md."

Check if `## Idea Extraction Record` already exists at the bottom of `<WIKI_VAULT>\sources\<slug>.md`. If it does, this paper was already fully processed — tell the user and stop.

### 1b. Write export to wiki sources

Transform the notes into the export format below and write to `<WIKI_VAULT>\sources\<slug>.md`.

Export format:

```markdown
---
tags: [paper, <topic-tags>]
created: <YYYY-MM-DD today>
source: AI_education tutor session
paper: <Full title and authors, from the # heading in the notes file>
---

# <Paper Title> — Export Summary

## 论文核心贡献
[1–3 sentences: what the paper does and what problem it solves]

## 核心方法（已掌握）
[Method name, intuition, key mathematical tools — only what the learner genuinely mastered, drawn from Phase 2 checkboxes]

## 数学工具
[Mathematical tools used, with mastery level: complete / partial / not covered]

## 批判性反思（独立识别）
[ALL critical reflections — one numbered entry per critique. For each:
- Label: independently-identified / guided / tutor-added
- Preserve original language verbatim
- If entry contains implicit research question, add: "Implicit research question: ..."
- If critique connects to an active research direction from researcher_profile.md, add: "Active direction: <direction number and name>"]

## 对 Idea Pipeline 的相关性
[Which research directions from <IDEA_VAULT>\researcher_profile.md does this paper connect to? Name direction number and slug. Be specific: evidence for, against, methodology to borrow, or data source.]

## 开放问题
[All open questions from the notes file, preserved verbatim]
```

Topic tags: choose 2–4 from `labor-economics`, `education`, `ai-economics`, `information-frictions`, `causal-inference`, `field-experiment`, `structural-model`, `signaling`, `behavioral`, `automation`, `human-capital`, `science-of-science`

### 1c. Update AI_education state files

1. Update `<AI_EDUCATION_PATH>\papers\index.md`: find the row with slug `<slug>`, change status to `exported`.
2. Update `<AI_EDUCATION_PATH>\tutor\context_snapshot.md`: remove any pending action line referencing this paper's export.
3. Append to `<AI_EDUCATION_PATH>\tutor\idea_seeds.md`:
   ```
   [YYYY-MM-DD] paper: <title> | source: <slug>.md
     → exported to: <WIKI_VAULT>/sources/<slug>.md
     → status: pending idea extraction
   ```

---

## Phase 2 — Wiki Ingest (automatic)

1. Read `<WIKI_VAULT>\wiki\log.md` to confirm this source hasn't been ingested yet.
2. Read `<WIKI_VAULT>\sources\<slug>.md`.
3. Extract key concepts, methods, and people from the export.
4. For each concept: check if a wiki page exists in `<WIKI_VAULT>\wiki\`. Update if exists, create if not.
5. Update `<WIKI_VAULT>\wiki\index.md` with any new pages.
6. Append to `<WIKI_VAULT>\wiki\log.md`:
   `[INGEST YYYY-MM-DD] source: <slug>.md → created: <pages> | updated: <pages>`

---

## Phase 3 — Idea Extraction Proposal (ONE STOP — wait for user)

Read the exported source file. Extract all content from:
- `## 批判性反思（独立识别）` — numbered critiques
- `## 开放问题` — open questions
- `## 对 Idea Pipeline 的相关性` — existing idea slug links

For each candidate, classify:

**Category A — Append to existing idea**: candidate is explicitly linked to a slug in "对 Idea Pipeline 的相关性". Read the idea file to confirm, then append to `## Evidence from Readings`.

**Category B — Create new idea (status: capture)**: NOT linked to existing slug, AND names a specific causal mechanism or channel (not vague "AI affects X"). Enforced standard: must have a concrete, researchable question.

**Category C — Skip**: purely methodological, no research question, or too vague.

Present this table, then STOP and wait:

```
## Idea Extraction Proposal — <slug>.md
Paper: <title>

| # | Type | Original text (shortened) | Proposed action | Target |
|---|------|--------------------------|-----------------|--------|
| ... | ... | ... | A/B/C: ... | slug or — |
```

Say (in Chinese): "以上是提取方案。回复 **confirm** 执行全部，或 **revise #N → [新分类]** 调整某条，或 **skip** 取消提取。"

**DO NOT write any files until user confirms.**

---

## Phase 4 — Execute (after user confirms)

### Category A — Append to existing idea

1. Read `<IDEA_VAULT>\ideas\<slug>.md`
2. If `## Evidence from Readings` exists: append bullet. If not: add section before `## Decision Log`.
3. Bullet format:
   ```
   - **<Author-year>** (`sources/<slug>.md`): <critique text, original language> — origin: independently-identified / guided / tutor-added
   ```
4. Update `updated:` in frontmatter.
5. Append to `<IDEA_VAULT>\ideas\log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <slug>.md → appended to: <idea-slug>`

### Category B — Create new idea

1. Create `<IDEA_VAULT>\ideas\<new-slug>.md` from `ideas/_template.md`:
   - `status: capture`, `checkpoint_pending: true`
   - Fill `## Original Idea` with the critique/question (original language)
   - Add `## Source` section after Original Idea:
     ```
     ## Source
     - Paper: `sources/<slug>.md`
     - Origin: <Critique N / Open Question N> — <independently-identified / guided / tutor-added>
     - Extracted: YYYY-MM-DD
     ```
2. Add to `<IDEA_VAULT>\ideas\index.md` under "🔴 Waiting for Review".
3. Append to `<IDEA_VAULT>\ideas\log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <slug>.md → created: <new-slug>`

### After all writes

4. Append `## Idea Extraction Record` to the source file:
   ```markdown
   ## Idea Extraction Record
   - Extracted: YYYY-MM-DD
   - Appended to: <slugs or "none">
   - Created: <slugs or "none">
   - Skipped: <N> items
   ```
5. Update `<AI_EDUCATION_PATH>\tutor\idea_seeds.md` — update the line added in Phase 1 to reflect actual extraction results.

### Researcher profile sync

6. Run the full `/update-researcher-profile` logic (re-read changed idea files, update researcher_profile.md, sync to paper_tracker repo, git push).

---

## Phase 5 — Final Report

Tell the user (in Chinese):
- Export written to: `sources/<slug>.md`
- Wiki pages created/updated: <list>
- Ideas appended: <slugs or none>
- New ideas created: <slugs or none>; run `/idea-next <slug>` when ready to develop them
- researcher_profile.md synced and pushed to paper_tracker
