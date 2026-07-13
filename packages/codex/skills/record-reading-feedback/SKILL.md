---
name: record-reading-feedback
description: "Use this skill when the user invokes $record-reading-feedback, /record-reading-feedback, finishes or skips a paper, or asks to record durable reading feedback. This is the Codex adapter for the canonical AI Research Tools command."
---
# record-reading-feedback

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/ai-education/.claude/commands/record-reading-feedback.md","source_sha256":"b6516bdb90990f48b8c93dcc915e5cc20c53d7faba727f35b266aae6be81ee4d","workflow_version":"3.0.0"} -->

## Trigger Forms

- $record-reading-feedback
- /record-reading-feedback
- Natural language signals that a paper reached a terminal reading state and feedback should enter the recommendation loop

## Codex Execution Rules

- Do **not** read `~/.claude/commands/record-reading-feedback.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /record-reading-feedback

Record one durable feedback event after a paper is fully read, selectively
read, roughly triaged, or skipped.

## Usage

`/record-reading-feedback <slug>`

Read `~/.claude/machine_paths.md`, resolve `<AI_EDUCATION_PATH>` and `<TOOLS_ROOT>`, and obtain the paper's canonical `paper_id` from queue/catalog metadata. If it is absent, derive it with `python "<TOOLS_ROOT>\scripts\research_core.py" paper-id ...`; do not use the slug when a DOI, arXiv, OpenAlex, canonical URL, or title fingerprint can be resolved.

## Compact collection protocol

Infer values already stated in the conversation. Ask at most one compact
question for missing fields; do not run a survey.

Required fields:

- `read_depth`: `full`, `selective`, `rough`, or `skipped`
- `rating`: `high-value`, `useful`, or `low-fit`
- `usefulness`: what was useful; use `none` for a low-fit skip
- `surprise`: unexpected evidence or mechanism; may be `none`
- `belief_changed`: what changed; may be `none`
- `idea_affected`: zero or more idea slugs

If the user already stated enough information, write directly. If one material
field is genuinely uncertain, show one compact inferred line as the single
follow-up question; do not add a separate generic confirmation.

## Write

Run from the AI Education project:

```powershell
python "<AI_EDUCATION_PATH>\tutor\reading_feedback.py" record `
  --paper-id "<canonical-paper-id>" `
  --slug "<slug>" `
  --read-depth "<full|selective|rough|skipped>" `
  --rating "<high-value|useful|low-fit>" `
  --usefulness "<compact text>" `
  --surprise "<compact text or none>" `
  --belief-changed "<compact text or none>" `
  --idea-affected "<slug-if-any>" `
  --reason "<compact reason if skipped>" `
  --run-id "<workflow-run-id-if-any>"
```

Omit optional fields when absent. Repeat `--idea-affected` for multiple ideas.
The script writes canonical `tutor/reading_feedback.jsonl` and
regenerates `tutor/paper_preferences.md`. It is idempotent for identical
same-paper, same-run, same-day feedback. Legacy slug-only rows remain readable,
but every new event should carry a canonical `paper_id`.
