Export a completed paper's session notes from the AI_education tutor to the Obsidian personal knowledge wiki.

## Usage

`/ai-education-export <slug>`

Where `<slug>` is the paper slug (e.g. `freelance_jmp_latest`, `w33941`, `qjae044`).

---

## Step 1 — Read source notes

Read `{{AI_EDUCATION_PATH}}\papers\notes\<slug>.md`.

If the file does not exist, stop and tell the user: "No notes file found at papers/notes/<slug>.md. Check the slug in tutor/paper_notes.md for the correct name."

---

## Step 2 — Transform to export format

The export is a transformation, not a copy. Paper notes record the learning process; the export records final understanding only.

Write to: `{{OBSIDIAN_ROOT}}\personal knowledge skill\sources\<slug>.md`

Use this format:

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
[ALL critical reflections from Phase 3 / Critical Reflections section — one numbered entry per critique. For each:
- Label: independently-identified / guided / tutor-added
- Preserve original language verbatim (Chinese or English)
- If the entry contains an implicit research question, add: "Implicit research question: ..."
- If the critique connects to an active research direction from researcher_profile.md, add: "Active direction: <direction number and name>"]

## 对 Idea Pipeline 的相关性
[Which research directions from {{OBSIDIAN_ROOT}}\JMP Idea\researcher_profile.md does this paper connect to? Name the direction number and slug. Be specific about what the paper contributes — evidence for, evidence against, methodology to borrow, or data source.]

## 开放问题
[All open questions from the notes file, preserved verbatim]
```

**Topic tags**: choose 2–4 from: `labor-economics`, `education`, `ai-economics`, `information-frictions`, `causal-inference`, `field-experiment`, `structural-model`, `signaling`, `behavioral`, `automation`, `human-capital`, `science-of-science`

---

## Step 3 — Update idea_seeds.md

Append to `{{AI_EDUCATION_PATH}}\tutor\idea_seeds.md`:

```
[YYYY-MM-DD] paper: <paper title> | source: <slug>.md
  → exported to: {{OBSIDIAN_ROOT}}/personal knowledge skill/sources/<slug>.md
  → status: pending /idea-extract-from-source
```

---

## Step 4 — Update context_snapshot.md

Read `{{AI_EDUCATION_PATH}}\tutor\context_snapshot.md`. In the Pending Actions section, find and remove the line referencing this paper's export (e.g. "Export <paper> session notes to Obsidian"). Write the updated file.

---

## Step 5 — Update papers/index.md

Read `{{AI_EDUCATION_PATH}}\papers\index.md`. Find the row with slug `<slug>` and change its status field to `exported`. Write the updated file.

---

## Step 6 — Report

Tell the user (in Chinese, as Trevor):
- Export written to: `{{OBSIDIAN_ROOT}}/personal knowledge skill/sources/<slug>.md`
- Pending actions updated (item removed from context_snapshot.md)
- papers/index.md updated: status set to `exported`
- Next step: run `/wiki-ingest` in `{{OBSIDIAN_ROOT}}/personal knowledge skill/` to index the new source
- After that: run `/idea-extract-from-source <slug>.md` in `{{OBSIDIAN_ROOT}}/JMP Idea/` to extract research ideas
