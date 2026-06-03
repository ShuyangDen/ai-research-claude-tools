You are extracting potential research ideas from a paper source note in the personal knowledge wiki.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get:
- AI Education project path
- Wiki vault path (under "Personal Knowledge Wiki → Vault")
- Idea pipeline vault path (under "Research Idea Pipeline → Vault")

If either path says "not set up on this machine", tell the user and stop.

---

## Input

The user will provide a source filename (e.g. `ide-talamas2025-ai-knowledge-economy.md`).
Read `<wiki-vault>/sources/<filename>` carefully.

---

## Step 1: Parse Critical Content

From the source file, extract all content from these three sections:

1. **`## 批判性反思`** (or `## 批判性反思（独立识别）`, i.e. "Critical Reflections") — numbered critiques
2. **`## 开放问题`** (i.e. "Open Questions") — numbered open questions
3. **`## 对 Idea Pipeline 的相关性`** (i.e. "Relevance to Idea Pipeline") — existing idea slug links (e.g. `ai-human-capital`, `ai-better-questions`)

Build a combined list of all critiques + open questions as candidate seeds.

---

## Step 2: Classify Each Candidate

For each candidate, classify it into one of three categories:

### Category A — Append to existing idea
Condition: The critique/question is **explicitly mentioned** in `## 对 Idea Pipeline 的相关性` (Relevance to Idea Pipeline) as related to a specific slug.
- Read the existing idea page at `<idea-vault>/ideas/<slug>.md` to confirm the connection makes sense.
- Disposition: append critique as a bullet under `## Evidence from Readings` in that idea page.

### Category B — Create new idea (status: capture)
Condition: The critique/question is NOT linked to an existing slug, AND it contains a specific, researchable question with a plausible causal channel (not just "AI affects X" vaguely).
- **Enforced standard (from user memory):** The candidate MUST name a specific causal mechanism or channel. Vague "AI causes X" framings do not qualify — they must be sharpened first.
- Disposition: create new `ideas/<slug>.md` at `status: capture`.

### Category C — Skip
Condition: The candidate is purely methodological, has no clear research question, or is too vague even after sharpening.
- Disposition: note only, no file written.

---

## Step 3: Present Proposal Table (SEMI-AUTOMATIC — STOP HERE)

Present the user with a table listing every candidate and its proposed classification:

```
## Idea Extraction Proposal — <source filename>
Paper: <paper title from frontmatter>

| # | Type | Original Text (shortened) | Proposed Action | Target |
|---|------|--------------------------|-----------------|--------|
| Critique 1 | critique | Unlimited demand assumption... | B: New idea | `infinite-demand-assumption` |
| Critique 2 | critique | Two-layer org structure... | C: Skip (methodological) | — |
| Critique 4 | critique | 1D knowledge breaks PAM... | B: New idea | `multidim-knowledge-pam-breakdown` |
| Open Q 1 | open question | Equilibrium org under multi-dim knowledge... | A: Append | `ai-human-capital` |
| Open Q 3 | open question | How to empirically distinguish... | B: New idea | `coworker-vs-copilot-identification` |
```

Then say (communicate with user in Chinese as usual, but the table above stays in English):
> Above is the proposal. Please confirm or revise:
> - Reply **confirm** to execute all actions
> - Reply **revise #N → [new classification]** to adjust individual entries
> - Reply **skip** to cancel the entire extraction

**DO NOT write any files until the user confirms.**

---

## Step 4: Execute (after user confirms)

### For Category A items (Append to existing idea):

1. Read `<idea-vault>/ideas/<slug>.md`
2. Check if a `## Evidence from Readings` section already exists:
   - If yes: append a new bullet under it
   - If no: add the section before `## Decision Log`
3. Append this bullet format:
   ```
   - **<Paper author-year>** (<source filename>): <critique text, preserved in original language> — origin: independently-identified / guided / tutor-added
   ```
4. Update the `updated:` date in frontmatter
5. Append to `<idea-vault>/ideas/log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <filename> → appended to: <slug>`

### For Category B items (Create new idea):

1. Generate a URL-safe slug from the research question (lowercase, hyphens, max 5 words)
2. Check `<idea-vault>/ideas/` — if slug already exists, append `-<paper-short-name>` suffix
3. Create `<idea-vault>/ideas/<slug>.md` based on `ideas/_template.md` with:
   - `status: capture`
   - `checkpoint_pending: true`
   - Fill `## Original Idea` with the critique/question text (preserve original language)
   - Add a `## Source` section (after Original Idea, before S2):
     ```markdown
     ## Source
     - Paper: [[<wiki-page-name>]] (`sources/<filename>`)
     - Origin: <Critique N / Open Question N> — <independently-identified / guided / tutor-added>
     - Extracted: YYYY-MM-DD
     ```
   - Leave `## S2: Literature Exploration` as `*Status: pending*` — **do NOT auto-run S2**
4. Add to `<idea-vault>/ideas/index.md` under "🔴 Waiting for Review"
5. Append to `<idea-vault>/ideas/log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <filename> → created new idea: <slug>`

### After all writes:

6. Update `<wiki-vault>/sources/<filename>` — add a line at the bottom:
   ```markdown
   ## Idea Extraction Record
   - Extracted: YYYY-MM-DD
   - Appended to: <slugs or "none">
   - Created: <slugs or "none">
   - Skipped: <count> items
   ```
   This prevents duplicate extraction on re-runs (check for this section before starting Step 1).

7. Also update `<ai-education-path>/tutor/idea_seeds.md`:
   - If file doesn't exist, create it with a header
   - Append:
     ```
     [YYYY-MM-DD] paper: <paper title> | source: <filename>
       → appended to: <slugs or "none">
       → created: <slugs or "none">
       → skipped: <N> items
     ```

8. Report to user:
   - What was appended, to which slugs
   - What new ideas were created (with slugs)
   - Remind: run `/idea-next <slug>` on any new capture ideas to advance to S2 when ready

---

## Idempotency Check

At the START of Step 1, before parsing:
- Check if `## Idea Extraction Record` already exists at the bottom of the source file
- If yes: tell the user "Already extracted on <date>. Ideas created: <slugs>. To re-extract, delete the `## Idea Extraction Record` section from the source file first." and stop.
