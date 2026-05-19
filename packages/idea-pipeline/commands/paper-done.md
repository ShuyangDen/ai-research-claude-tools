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

### 1b. Load active research directions (partial read only)

Read **only the `## Active Research Directions` section** from `<IDEA_VAULT>\researcher_profile.md`. Do NOT load the full file. Extract the numbered direction list (typically < 500 tokens). Store in memory for use in 1c.

### 1c. Write export to wiki sources

Transform the notes into the export format below and write to `<WIKI_VAULT>\sources\<slug>.md`. Keep the in-memory export content for Phase 2 (no disk re-read needed).

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
- If critique connects to an active research direction, add: "Active direction: <direction number and name>"]

## 对 Idea Pipeline 的相关性
[Which research directions does this paper connect to? Name direction number and slug. Be specific: evidence for, against, methodology to borrow, or data source.]

## 开放问题
[All open questions from the notes file, preserved verbatim]
```

Topic tags: choose 2–4 from `labor-economics`, `education`, `ai-economics`, `information-frictions`, `causal-inference`, `field-experiment`, `structural-model`, `signaling`, `behavioral`, `automation`, `human-capital`, `science-of-science`

### 1d. Update AI_education state files

1. Update `<AI_EDUCATION_PATH>\papers\index.md`: find the row with slug `<slug>`, change status to `exported`.
2. Update `<AI_EDUCATION_PATH>\tutor\context_snapshot.md`: remove any pending action line referencing this paper's export.
3. Append to `<AI_EDUCATION_PATH>\tutor\idea_seeds.md`:
   ```
   [YYYY-MM-DD] paper: <title> | source: <slug>.md
     → exported to: <WIKI_VAULT>/sources/<slug>.md
     → status: pending idea extraction
   ```

---

## Phase 2 — Wiki Ingest (automatic, single-source mode)

Use the export content already in memory from Phase 1 — do NOT re-read `sources/<slug>.md` from disk.

1. Read `<WIKI_VAULT>\wiki\log.md` to confirm this source hasn't been ingested yet. If it already appears in the log, skip Phase 2.
2. Using the in-memory export content from Phase 1, extract key concepts, methods, and people.
3. For each concept, check if a wiki page exists in `<WIKI_VAULT>\wiki\`:
   - **New concept** (no existing page): create a new wiki page.
   - **Existing concept with genuinely new content**: update the page only if this paper adds something substantively new — a new method variant, a contradicting finding, an important caveat, or a concrete application not yet covered. Do NOT update if the paper only provides a redundant example of an already-covered concept.
   - **Existing concept, no new content**: skip — leave the page untouched.
4. Update `<WIKI_VAULT>\wiki\index.md` only if new pages were created.
5. Append to `<WIKI_VAULT>\wiki\log.md` regardless of outcome:
   `[INGEST YYYY-MM-DD] source: <slug>.md → created: <pages or "none"> | updated: <pages or "none"> | skipped: <N concepts already covered>`

Note: Do NOT enumerate the `sources/` directory or process other files. This is a targeted single-source ingest. Use `/wiki-ingest` separately if you want to batch-process all pending sources.

---

## Phase 3 — Idea Extraction (auto or one stop)

Use the in-memory export content from Phase 1. Extract all content from:
- `## 批判性反思（独立识别）` — numbered critiques
- `## 开放问题` — open questions
- `## 对 Idea Pipeline 的相关性` — existing idea slug links

### Load idea descriptions from cache (do NOT read full idea files yet)

Read `<IDEA_VAULT>\ideas\_profile_cache.json`. For each idea slug mentioned in "对 Idea Pipeline 的相关性", look up its `title` and `description` from the cache. This is sufficient to score relevance and classify candidates. Do NOT open individual idea files at this stage.

For each candidate, classify:

**Category A — Append to existing idea**: candidate is explicitly linked to a slug in "对 Idea Pipeline 的相关性", AND the cache description confirms relevance. Do NOT read the full idea file yet — defer to Phase 4 execution.

**Category B — Create new idea (status: capture)**: NOT linked to existing slug, AND names a specific causal mechanism or channel (not vague "AI affects X"). Enforced standard: must have a concrete, researchable question.

**Category C — Skip**: purely methodological, no research question, or too vague.

**Decision — stop or auto-execute:**

- **If NO Category B candidates**: auto-execute all Category A and C actions immediately without stopping. Skip the proposal table. Tell the user inline what was done.
- **If at least one Category B candidate exists**: present the proposal table and STOP, waiting for user confirmation before writing any files.

Proposal table format (only shown when Category B exists):

```
## Idea Extraction Proposal — <slug>.md
Paper: <title>

| # | Type | Original text (shortened) | Proposed action | Target |
|---|------|--------------------------|-----------------|--------|
| ... | ... | ... | A/B/C: ... | slug or — |
```

Say (in Chinese): "以上是提取方案。回复 **confirm** 执行全部，或 **revise #N → [新分类]** 调整某条，或 **skip** 取消提取。"

**DO NOT write any files until user confirms (only applies when Category B candidates exist).**

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

### Researcher profile sync — conditional

6. Before syncing, read **only the first 5 lines** of `<IDEA_VAULT>\researcher_profile.md` to extract the `Last updated:` date. Do NOT load the full file.

   Check two conditions:
   - **Condition A** — any Category B ideas were created in Phase 4 (new ideas added to Active Research Directions)
   - **Condition B** — `Last updated` date is more than 7 days before today

   **If either condition is true**: run the full `/update-researcher-profile` logic (re-read changed idea files, update researcher_profile.md, sync to paper_tracker repo, git push).

   **If neither condition is true**: skip the sync entirely. Tell the user (in Chinese): "researcher_profile.md 跳过同步（无新 idea，上次同步在 N 天前）"

---

## Phase 5 — Final Report

Tell the user (in Chinese):
- Export written to: `sources/<slug>.md`
- Wiki pages created/updated/skipped: <summary>
- Ideas appended: <slugs or none>
- New ideas created: <slugs or none>; run `/idea-next <slug>` when ready to develop them
- researcher_profile.md: synced and pushed to paper_tracker, OR skipped (reason)
