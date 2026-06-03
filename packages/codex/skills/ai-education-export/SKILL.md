---
name: ai-education-export
description: Use this skill when the user invokes $ai-education-export, /ai-education-export, asks to run ai-education-export, or asks to export completed AI Education paper notes to the knowledge wiki. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# ai-education-export
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for AI Education.
## Trigger Forms
- $ai-education-export
- /ai-education-export
- Natural language requests to export completed AI Education paper notes to the knowledge wiki
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\ai-education-export.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Export a completed paper's session notes from the AI_education tutor to the Obsidian personal knowledge wiki.

## Usage

`/ai-education-export <slug>`

Where `<slug>` is the paper slug (e.g. `freelance_jmp_latest`, `w33941`, `qjae044`).

---

## Step 1 鈥?Read source notes

Read `{{AI_EDUCATION_PATH}}\papers\notes\<slug>.md`.

If the file does not exist, stop and tell the user: "No notes file found at papers/notes/<slug>.md. Check the slug in tutor/paper_notes.md for the correct name."

---

## Step 2 鈥?Transform to export format

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

# <Paper Title> 鈥?Export Summary

## 璁烘枃鏍稿績璐＄尞
[1鈥? sentences: what the paper does and what problem it solves]

## 鏍稿績鏂规硶锛堝凡鎺屾彙锛?
[Method name, intuition, key mathematical tools 鈥?only what the learner genuinely mastered, drawn from Phase 2 checkboxes]

## 鏁板宸ュ叿
[Mathematical tools used, with mastery level: complete / partial / not covered]

## 鎵瑰垽鎬у弽鎬濓紙鐙珛璇嗗埆锛?
[ALL critical reflections from Phase 3 / Critical Reflections section 鈥?one numbered entry per critique. For each:
- Label: independently-identified / guided / tutor-added
- Preserve original language verbatim (Chinese or English)
- If the entry contains an implicit research question, add: "Implicit research question: ..."
- If the critique connects to an active research direction from researcher_profile.md, add: "Active direction: <direction number and name>"]

## 瀵?Idea Pipeline 鐨勭浉鍏虫€?
[Which research directions from {{OBSIDIAN_ROOT}}\JMP Idea\researcher_profile.md does this paper connect to? Name the direction number and slug. Be specific about what the paper contributes 鈥?evidence for, evidence against, methodology to borrow, or data source.]

## 寮€鏀鹃棶棰?
[All open questions from the notes file, preserved verbatim]
```

**Topic tags**: choose 2鈥? from: `labor-economics`, `education`, `ai-economics`, `information-frictions`, `causal-inference`, `field-experiment`, `structural-model`, `signaling`, `behavioral`, `automation`, `human-capital`, `science-of-science`

---

## Step 3 鈥?Update idea_seeds.md

Append to `{{AI_EDUCATION_PATH}}\tutor\idea_seeds.md`:

```
[YYYY-MM-DD] paper: <paper title> | source: <slug>.md
  鈫?exported to: {{OBSIDIAN_ROOT}}/personal knowledge skill/sources/<slug>.md
  鈫?status: pending /idea-extract-from-source
```

---

## Step 4 鈥?Update context_snapshot.md

Read `{{AI_EDUCATION_PATH}}\tutor\context_snapshot.md`. In the Pending Actions section, find and remove the line referencing this paper's export (e.g. "Export <paper> session notes to Obsidian"). Write the updated file.

---

## Step 5 鈥?Update papers/index.md

Read `{{AI_EDUCATION_PATH}}\papers\index.md`. Find the row with slug `<slug>` and change its status field to `exported`. Write the updated file.

---

## Step 6 鈥?Report

Tell the user (in Chinese, as Trevor):
- Export written to: `{{OBSIDIAN_ROOT}}/personal knowledge skill/sources/<slug>.md`
- Pending actions updated (item removed from context_snapshot.md)
- papers/index.md updated: status set to `exported`
- Next step: run `/wiki-ingest` in `{{OBSIDIAN_ROOT}}/personal knowledge skill/` to index the new source
- After that: run `/idea-extract-from-source <slug>.md` in `{{OBSIDIAN_ROOT}}/JMP Idea/` to extract research ideas

