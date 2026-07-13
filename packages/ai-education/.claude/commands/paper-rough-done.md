# /paper-rough-done

Lightweight archive for a paper that was intentionally read selectively.

## Usage

`/paper-rough-done <slug>`

Use this when the learner says the paper is done as a rough read, selective read, partial read, or "只读这一部分就归档". This command is not a failed full `/paper-done`; it is the correct completion path for papers where only selected modules were read.

## Paths

Read `~/.claude/machine_paths.md` to resolve:
- `<AI_EDUCATION_PATH>` from AI Education Project / Project root
- `<WIKI_VAULT>` from Personal Knowledge Wiki / Vault
- `<PAPER_TRACKER_REPO>` from Paper Tracker / PAPER_TRACKER_REPO

## Phase 0 - Confirm scope

Before writing, confirm from the current notes or the conversation:
- paper slug
- selective focus actually read
- details intentionally skipped/deferred
- whether the learner explicitly asked to run full idea extraction

If selective focus or learner critiques are missing from `papers/notes/<slug>.md`, update the note first from the session context. Do not invent unread results.

### Phase 0b - Record recommendation feedback

Run `/record-reading-feedback <slug>` before archive. Use `read_depth=selective`
when a chosen module was read, otherwise `read_depth=rough`. Infer the other
fields from the conversation and ask at most one compact question. This feedback
event is required even when full idea extraction is skipped.

## Phase 1 - Lightweight notes check

Read `<AI_EDUCATION_PATH>\papers\notes\<slug>.md`.

The note must clearly contain:
- `Status: rough-read complete / selective read` or equivalent
- selective focus / triage focus
- paper understanding for only the read modules
- skipped or deferred details
- learner critiques and open questions

If the note is missing, create it from the session transcript and PDF/text context, but keep it limited to the read modules. If the note exists but is too broad, narrow the export rather than expanding the paper note.

## Phase 2 - Export source

Write `<WIKI_VAULT>\sources\<slug>.md` as a transformation, not a raw copy.

Required frontmatter:
```markdown
---
tags: [paper, <topic-tags>]
created: <YYYY-MM-DD today>
source: AI_education tutor session
paper: <title and authors>
reading_status: rough-read / selective read
idea_extraction: skipped
---
```

Required sections:
- `# <Paper Title> - Export Summary`
- `## 论文核心贡献` - 1-2 sentences, framed as what was retained from the selective read
- `## 核心方法（已掌握）` - only methods actually discussed; otherwise say not covered in detail
- `## 数学工具` - mark deferred/not covered where appropriate
- `## 批判性反思（独立识别）` - preserve learner critiques verbatim and add implicit research questions when useful
- `## 对 Idea Pipeline 的相关性` - explain why retained or why idea extraction is skipped
- `## 开放问题`

Do not include full-paper results, appendix claims, or mechanisms that were not actually read.

## Phase 3 - Single-source wiki ingest

Run a targeted ingest for only `<slug>.md`.

1. Read `<WIKI_VAULT>\wiki\log.md`; if `<slug>.md` already appears, skip this phase.
2. Extract only concepts that are genuinely useful from the lightweight export.
3. Create or update wiki pages only for those concepts.
4. Update `wiki/index.md` only if a page is created.
5. Append one log line:
   `[INGEST YYYY-MM-DD] source: <slug>.md -> created: <pages or none> | updated: <pages or none> | skipped: <N>`

Never enumerate all `sources/` and never batch-ingest unrelated files.

## Phase 4 - AI Education state updates

Update local state:
1. `<AI_EDUCATION_PATH>\tutor\completed_papers.md`: append a numbered row with `(rough-read record)`.
2. `<AI_EDUCATION_PATH>\papers\index.md`: add/update row with status `exported` and one-liner beginning `Rough-read record:`.
3. `<AI_EDUCATION_PATH>\tutor\idea_seeds.md`: append an entry with `reading status: rough-read / selective read`, `appended to: none`, `created: none`, and `skipped: full idea extraction` unless the learner explicitly asked otherwise.
4. `<AI_EDUCATION_PATH>\tutor\context_snapshot.md`: prepend a short current-state summary, session summary, critical reflection status, and math gaps/deferred details.
5. `<AI_EDUCATION_PATH>\papers\reading_queue.md`: remove the paper row by slug if present.

## Phase 5 - Reading queue remote sync

Run `/sync-reading-queue`. It must persist the `completed`/`skipped` status to
the tracker's canonical `queue_state.jsonl` before updating the derived
`reading_queue.md`. Do not push Markdown alone; doing so would allow a later
tracker run to resurrect the paper from canonical state.

If `gh` is unavailable or unauthenticated, leave local queue updated and tell the learner remote sync was skipped.

## Phase 6 - Idea extraction default

Do not run full idea extraction by default. If the learner explicitly asks to extract ideas, run `/paper-done <slug>` full extraction phase or `/idea-extract-from-source <slug>.md` after this lightweight archive.

## Final report

Report in Chinese:
- note path
- source path
- wiki pages created/updated/skipped
- completed/index/context/idea_seeds updated
- reading queue local/remote status
- idea extraction skipped unless explicitly requested
