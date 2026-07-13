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
