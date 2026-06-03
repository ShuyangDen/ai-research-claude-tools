---
name: idea-extract-from-source
description: Use this skill when the user invokes $idea-extract-from-source, /idea-extract-from-source, asks to run idea-extract-from-source, or asks to extract research ideas from an exported source note. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-extract-from-source
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-extract-from-source
- /idea-extract-from-source
- Natural language requests to extract research ideas from an exported source note
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-extract-from-source.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
You are extracting potential research ideas from a paper source note in the personal knowledge wiki.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get:
- AI Education project path
- Wiki vault path (under "Personal Knowledge Wiki 鈫?Vault")
- Idea pipeline vault path (under "Research Idea Pipeline 鈫?Vault")

If either path says "not set up on this machine", tell the user and stop.

---

## Input

The user will provide a source filename (e.g. `ide-talamas2025-ai-knowledge-economy.md`).
Read `<wiki-vault>/sources/<filename>` carefully.

---

## Step 1: Parse Critical Content

From the source file, extract all content from these three sections:

1. **`## 鎵瑰垽鎬у弽鎬漙** (or `## 鎵瑰垽鎬у弽鎬濓紙鐙珛璇嗗埆锛塦, i.e. "Critical Reflections") 鈥?numbered critiques
2. **`## 寮€鏀鹃棶棰榒** (i.e. "Open Questions") 鈥?numbered open questions
3. **`## 瀵?Idea Pipeline 鐨勭浉鍏虫€** (i.e. "Relevance to Idea Pipeline") 鈥?existing idea slug links (e.g. `ai-human-capital`, `ai-better-questions`)

Build a combined list of all critiques + open questions as candidate seeds.

---

## Step 2: Classify Each Candidate

For each candidate, classify it into one of three categories:

### Category A 鈥?Append to existing idea
Condition: The critique/question is **explicitly mentioned** in `## 瀵?Idea Pipeline 鐨勭浉鍏虫€ (Relevance to Idea Pipeline) as related to a specific slug.
- Read the existing idea page at `<idea-vault>/ideas/<slug>.md` to confirm the connection makes sense.
- Disposition: append critique as a bullet under `## Evidence from Readings` in that idea page.

### Category B 鈥?Create new idea (status: capture)
Condition: The critique/question is NOT linked to an existing slug, AND it contains a specific, researchable question with a plausible causal channel (not just "AI affects X" vaguely).
- **Enforced standard (from user memory):** The candidate MUST name a specific causal mechanism or channel. Vague "AI causes X" framings do not qualify 鈥?they must be sharpened first.
- Disposition: create new `ideas/<slug>.md` at `status: capture`.

### Category C 鈥?Skip
Condition: The candidate is purely methodological, has no clear research question, or is too vague even after sharpening.
- Disposition: note only, no file written.

---

## Step 3: Present Proposal Table (SEMI-AUTOMATIC 鈥?STOP HERE)

Present the user with a table listing every candidate and its proposed classification:

```
## Idea Extraction Proposal 鈥?<source filename>
Paper: <paper title from frontmatter>

| # | Type | Original Text (shortened) | Proposed Action | Target |
|---|------|--------------------------|-----------------|--------|
| Critique 1 | critique | Unlimited demand assumption... | B: New idea | `infinite-demand-assumption` |
| Critique 2 | critique | Two-layer org structure... | C: Skip (methodological) | 鈥?|
| Critique 4 | critique | 1D knowledge breaks PAM... | B: New idea | `multidim-knowledge-pam-breakdown` |
| Open Q 1 | open question | Equilibrium org under multi-dim knowledge... | A: Append | `ai-human-capital` |
| Open Q 3 | open question | How to empirically distinguish... | B: New idea | `coworker-vs-copilot-identification` |
```

Then say (communicate with user in Chinese as usual, but the table above stays in English):
> Above is the proposal. Please confirm or revise:
> - Reply **confirm** to execute all actions
> - Reply **revise #N 鈫?[new classification]** to adjust individual entries
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
   - **<Paper author-year>** (<source filename>): <critique text, preserved in original language> 鈥?origin: independently-identified / guided / tutor-added
   ```
4. Update the `updated:` date in frontmatter
5. Append to `<idea-vault>/ideas/log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <filename> 鈫?appended to: <slug>`

### For Category B items (Create new idea):

1. Generate a URL-safe slug from the research question (lowercase, hyphens, max 5 words)
2. Check `<idea-vault>/ideas/` 鈥?if slug already exists, append `-<paper-short-name>` suffix
3. Create `<idea-vault>/ideas/<slug>.md` based on `ideas/_template.md` with:
   - `status: capture`
   - `checkpoint_pending: true`
   - Fill `## Original Idea` with the critique/question text (preserve original language)
   - Add a `## Source` section (after Original Idea, before S2):
     ```markdown
     ## Source
     - Paper: [[<wiki-page-name>]] (`sources/<filename>`)
     - Origin: <Critique N / Open Question N> 鈥?<independently-identified / guided / tutor-added>
     - Extracted: YYYY-MM-DD
     ```
   - Leave `## S2: Literature Exploration` as `*Status: pending*` 鈥?**do NOT auto-run S2**
4. Add to `<idea-vault>/ideas/index.md` under "馃敶 Waiting for Review"
5. Append to `<idea-vault>/ideas/log.md`:
   `[IDEA-EXTRACT YYYY-MM-DD] source: <filename> 鈫?created new idea: <slug>`

### After all writes:

6. Update `<wiki-vault>/sources/<filename>` 鈥?add a line at the bottom:
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
       鈫?appended to: <slugs or "none">
       鈫?created: <slugs or "none">
       鈫?skipped: <N> items
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

