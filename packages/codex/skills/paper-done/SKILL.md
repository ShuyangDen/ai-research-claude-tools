---
name: paper-done
description: Use this skill when the user invokes $paper-done, /paper-done, asks to run paper-done, or asks to run the full post-paper pipeline: export, wiki ingest, idea extraction. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# paper-done
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for AI Education + Idea Pipeline.
## Trigger Forms
- $paper-done
- /paper-done
- Natural language requests to run the full post-paper pipeline: export, wiki ingest, idea extraction
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\paper-done.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Run the complete post-session pipeline for a finished paper: export notes 鈫?wiki ingest 鈫?idea extraction (one confirmation) 鈫?researcher profile sync.

## Usage

`/paper-done <slug>`

Where `<slug>` is the paper slug (e.g. `w33941`, `qjae044`).

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- AI Education root (under "AI Education Project 鈫?Project root") 鈫?`<AI_EDUCATION_PATH>`
- Wiki vault (under "Personal Knowledge Wiki 鈫?Vault") 鈫?`<WIKI_VAULT>`
- Idea vault (under "Research Idea Pipeline 鈫?Vault") 鈫?`<IDEA_VAULT>`

---

## Phase 1 鈥?Export (automatic, no confirmation needed)

### 1a. Read source notes

Read `<AI_EDUCATION_PATH>\papers\notes\<slug>.md`.

If not found: stop and tell user "No notes file at papers/notes/<slug>.md."

Check if `## Idea Extraction Record` already exists at the bottom of `<WIKI_VAULT>\sources\<slug>.md`. If it does, this paper was already fully processed 鈥?tell the user and stop.

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

# <Paper Title> 鈥?Export Summary

## 璁烘枃鏍稿績璐＄尞
[1鈥? sentences: what the paper does and what problem it solves]

## 鏍稿績鏂规硶锛堝凡鎺屾彙锛?[Method name, intuition, key mathematical tools 鈥?only what the learner genuinely mastered, drawn from Phase 2 checkboxes]

## 鏁板宸ュ叿
[Mathematical tools used, with mastery level: complete / partial / not covered]

## 鎵瑰垽鎬у弽鎬濓紙鐙珛璇嗗埆锛?[ALL critical reflections 鈥?one numbered entry per critique. For each:
- Label: independently-identified / guided / tutor-added
- Preserve original language verbatim
- If entry contains implicit research question, add: "Implicit research question: ..."
- If critique connects to an active research direction, add: "Active direction: <direction number and name>"]

## 瀵?Idea Pipeline 鐨勭浉鍏虫€?[Which research directions does this paper connect to? Name direction number and slug. Be specific: evidence for, against, methodology to borrow, or data source.]

## 寮€鏀鹃棶棰?[All open questions from the notes file, preserved verbatim]
```

Topic tags: choose 2鈥? from `labor-economics`, `education`, `ai-economics`, `information-frictions`, `causal-inference`, `field-experiment`, `structural-model`, `signaling`, `behavioral`, `automation`, `human-capital`, `science-of-science`

### 1d. Update AI_education state files

1. Update `<AI_EDUCATION_PATH>\papers\index.md`: find the row with slug `<slug>`, change status to `exported`.
2. Update `<AI_EDUCATION_PATH>\tutor\context_snapshot.md`: remove any pending action line referencing this paper's export.
3. Append to `<AI_EDUCATION_PATH>\tutor\idea_seeds.md`:
   ```
   [YYYY-MM-DD] paper: <title> | source: <slug>.md
     鈫?exported to: <WIKI_VAULT>/sources/<slug>.md
     鈫?status: pending idea extraction
   ```

---

## Phase 2 鈥?Wiki Ingest (automatic, single-source mode)

Use the export content already in memory from Phase 1 鈥?do NOT re-read `sources/<slug>.md` from disk.

1. Read `<WIKI_VAULT>\wiki\log.md` to confirm this source hasn't been ingested yet. If it already appears in the log, skip Phase 2.
2. Using the in-memory export content from Phase 1, extract key concepts, methods, and people.
3. For each concept, check if a wiki page exists in `<WIKI_VAULT>\wiki\`:
   - **New concept** (no existing page): create a new wiki page.
   - **Existing concept with genuinely new content**: update the page only if this paper adds something substantively new 鈥?a new method variant, a contradicting finding, an important caveat, or a concrete application not yet covered. Do NOT update if the paper only provides a redundant example of an already-covered concept.
   - **Existing concept, no new content**: skip 鈥?leave the page untouched.
4. Update `<WIKI_VAULT>\wiki\index.md` only if new pages were created.
5. Append to `<WIKI_VAULT>\wiki\log.md` regardless of outcome:
   `[INGEST YYYY-MM-DD] source: <slug>.md 鈫?created: <pages or "none"> | updated: <pages or "none"> | skipped: <N concepts already covered>`

Note: Do NOT enumerate the `sources/` directory or process other files. This is a targeted single-source ingest. Use `/wiki-ingest` separately if you want to batch-process all pending sources.

---

## Phase 3 鈥?Idea Extraction (auto or one stop)

Use the in-memory export content from Phase 1. Extract all content from:
- `## 鎵瑰垽鎬у弽鎬濓紙鐙珛璇嗗埆锛塦 鈥?numbered critiques
- `## 寮€鏀鹃棶棰榒 鈥?open questions
- `## 瀵?Idea Pipeline 鐨勭浉鍏虫€ 鈥?existing idea slug links

### Load idea descriptions from cache (do NOT read full idea files yet)

Read `<IDEA_VAULT>\ideas\_profile_cache.json`. For each idea slug mentioned in "瀵?Idea Pipeline 鐨勭浉鍏虫€?, look up its `title` and `description` from the cache. This is sufficient to score relevance and classify candidates. Do NOT open individual idea files at this stage.

For each candidate, classify:

**Category A 鈥?Append to existing idea**: candidate is explicitly linked to a slug in "瀵?Idea Pipeline 鐨勭浉鍏虫€?, AND the cache description confirms relevance. Do NOT read the full idea file yet 鈥?defer to Phase 4 execution.

**Category B 鈥?Create new idea (status: capture)**: NOT linked to existing slug, AND names a specific causal mechanism or channel (not vague "AI affects X"). Enforced standard: must have a concrete, researchable question.

**Category C 鈥?Skip**: purely methodological, no research question, or too vague.

**Decision 鈥?stop or auto-execute:**

- **If NO Category B candidates**: auto-execute all Category A and C actions immediately without stopping. Skip the proposal table. Tell the user inline what was done.
- **If at least one Category B candidate exists**: present the proposal table and STOP, waiting for user confirmation before writing any files.

Proposal table format (only shown when Category B exists):

```
## Idea Extraction Proposal 鈥?<slug>.md
Paper: <title>

| # | Type | Original text (shortened) | Proposed action | Target |
|---|------|--------------------------|-----------------|--------|
| ... | ... | ... | A/B/C: ... | slug or 鈥?|
```

Say (in Chinese): "浠ヤ笂鏄彁鍙栨柟妗堛€傚洖澶?**confirm** 鎵ц鍏ㄩ儴锛屾垨 **revise #N 鈫?[鏂板垎绫籡** 璋冩暣鏌愭潯锛屾垨 **skip** 鍙栨秷鎻愬彇銆?

**DO NOT write any files until user confirms (only applies when Category B candidates exist).**

---

## Phase 4 鈥?Execute (after user confirms)

### Category A 鈥?Append to existing idea

1. Read `<IDEA_VAULT>\ideas\<slug>.md`
2. If `## Evidence from Readings` exists: append bullet. If not: add section before `## Decision Log`.
3. Bullet format:
   ```
   - **<Author-year>** (`sources/<slug>.md`): <critique text, original language> 鈥?origin: independently-identified / guided / tutor-added
   ```
4. Update `updated:` in frontmatter.
5. Append to `<IDEA_VAULT>\ideas\log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <slug>.md 鈫?appended to: <idea-slug>`

### Category B 鈥?Create new idea

1. Create `<IDEA_VAULT>\ideas\<new-slug>.md` from `ideas/_template.md`:
   - `status: capture`, `checkpoint_pending: true`
   - Fill `## Original Idea` with the critique/question (original language)
   - Add `## Source` section after Original Idea:
     ```
     ## Source
     - Paper: `sources/<slug>.md`
     - Origin: <Critique N / Open Question N> 鈥?<independently-identified / guided / tutor-added>
     - Extracted: YYYY-MM-DD
     ```
2. Add to `<IDEA_VAULT>\ideas\index.md` under "馃敶 Waiting for Review".
3. Append to `<IDEA_VAULT>\ideas\log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <slug>.md 鈫?created: <new-slug>`

### After all writes

4. Append `## Idea Extraction Record` to the source file:
   ```markdown
   ## Idea Extraction Record
   - Extracted: YYYY-MM-DD
   - Appended to: <slugs or "none">
   - Created: <slugs or "none">
   - Skipped: <N> items
   ```
5. Update `<AI_EDUCATION_PATH>\tutor\idea_seeds.md` 鈥?update the line added in Phase 1 to reflect actual extraction results.

### Researcher profile sync 鈥?conditional

6. Before syncing, read **only the first 5 lines** of `<IDEA_VAULT>\researcher_profile.md` to extract the `Last updated:` date. Do NOT load the full file.

   Check two conditions:
   - **Condition A** 鈥?any Category B ideas were created in Phase 4 (new ideas added to Active Research Directions)
   - **Condition B** 鈥?`Last updated` date is more than 7 days before today

   **If either condition is true**: run the full `/update-researcher-profile` logic (re-read changed idea files, update researcher_profile.md, sync to paper_tracker repo, git push).

   **If neither condition is true**: skip the sync entirely. Tell the user (in Chinese): "researcher_profile.md 璺宠繃鍚屾锛堟棤鏂?idea锛屼笂娆″悓姝ュ湪 N 澶╁墠锛?

---

## Phase 5 鈥?Final Report

Tell the user (in Chinese):
- Export written to: `sources/<slug>.md`
- Wiki pages created/updated/skipped: <summary>
- Ideas appended: <slugs or none>
- New ideas created: <slugs or none>; run `/idea-next <slug>` when ready to develop them
- researcher_profile.md: synced and pushed to paper_tracker, OR skipped (reason)

