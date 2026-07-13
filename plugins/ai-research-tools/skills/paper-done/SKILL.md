---
name: paper-done
description: "Use this skill when the user invokes $paper-done, /paper-done, says a paper reading is complete, or asks to export notes and run the post-session paper pipeline. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# paper-done

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/paper-done.md","source_sha256":"34abd062963c5e111550e02e3f7c063caa187726093cb4002cad377d821c51ca","workflow_version":"3.0.0"} -->

## Trigger Forms

- $paper-done
- /paper-done
- Natural language signals that a paper reading is complete and should enter the post-session pipeline

## Codex Execution Rules

- Do **not** read `~/.claude/commands/paper-done.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /paper-done

Complete a full paper-reading session through a durable, resumable workflow. The run coordinates four stores, but each artifact has one owner and one writer.

## Usage

`/paper-done <slug>`

Use `/paper-rough-done <slug>` when the session intentionally covered only selected modules.

## Paths and runtime

Read `~/.claude/machine_paths.md` as UTF-8 and resolve:

- `<TOOLS_ROOT>` from `AI Research Tools → Source root`
- `<AI_EDUCATION_PATH>` from `AI Education Project → Project root`
- `<WIKI_VAULT>` from `Personal Knowledge Wiki → Vault`
- `<IDEA_VAULT>` from `Research Idea Pipeline → Vault`
- `<PAPER_TRACKER_PATH>` and `<PAPER_TRACKER_REPO>` from Paper Tracker
- `<STATE_ROOT>` from `Workflow State → Root`, defaulting to `~/.codex/ai-research-tools/state`

Invoke the deterministic runtime as `python "<TOOLS_ROOT>\scripts\research_core.py" ...`; no global package install is required. Use it for stable IDs, run state, hashes, atomic writes, validation, and profile projection. Use `<AI_EDUCATION_PATH>\tutor\reading_feedback.py` for the feedback event log/view. If either runtime is missing, stop before cross-vault writes and report how to repair the installation; do not fall back to an unlogged multi-file transaction.

## Transaction contract

Start or resume a workflow run with `research_core.py run ... --state-root "<STATE_ROOT>"` for `paper-done`. Derive a filesystem-safe deterministic run ID from the canonical `paper_id` plus input-note SHA-256; never put a raw DOI slash in the run ID. On first start, pre-register the complete plan so future steps are durable `pending` entries:

```powershell
python "<TOOLS_ROOT>\scripts\research_core.py" run start `
  --state-root "<STATE_ROOT>" --workflow paper-done --run-id "<safe-run-id>" `
  --step validate_note --step export_source --step ingest_wiki `
  --step record_feedback --step propose_idea_delta --step apply_confirmed_delta `
  --step update_reading_state --step project_profile
```

The run manifest must persist:

- run ID, workflow/schema versions, paper ID and aliases
- input/output paths and content hashes
- each step's `pending|waiting_human|running|completed|failed` state
- attempts, error, and next exact action

Completed steps with matching output hashes are not repeated. A mismatched output is a conflict to review, not permission to overwrite. Every file write is UTF-8 without BOM, validated in a temporary file, then atomically replaced.

Run steps:

1. `validate_note`
2. `export_source`
3. `ingest_wiki`
4. `record_feedback`
5. `propose_idea_delta`
6. `apply_confirmed_delta`
7. `update_reading_state`
8. `project_profile`

On failure, mark the current step failed and report the resume command. Never infer overall completion from the existence of `Idea Extraction Record` alone.

## Step 1 — Validate note and identity

Read `<AI_EDUCATION_PATH>\papers\notes\<slug>.md` and the corresponding paper catalog/queue record when present.

Resolve stable identity in this order: DOI, arXiv ID, OpenAlex work ID, NBER paper ID, then normalized canonical URL, and only then a title/year fingerprint. Store the human slug as an alias, never as the sole identity when a stable identifier exists.

Validate that the note distinguishes:

- what was actually read and understood
- reported results versus authors' interpretation
- learner/researcher reflections and their origin labels
- identification/design, data, locators, and unresolved questions

If the note is selective, route to `/paper-rough-done`. Do not fill unread results from model memory.

## Step 2 — Export source schema v2

Create or upgrade `<WIKI_VAULT>\sources\<slug>.md` using `sources/_template.md`.

Required metadata:

- `schema_version: 2`, canonical `paper_id`, and available identifiers
- title, authors, year, venue, version, URL
- `reading_status`, `read_depth`, and explicit `coverage`
- source note path and SHA-256

Required content:

- Core Contribution
- Claims and Evidence
- Identification and Threats
- Data
- Learner Reflections
- Open Questions
- Idea Relationships
- Processing State

Each claim receives a stable `<paper_id>#cNNN` ID, one allowed claim type, a source locator, confidence, human-verification state, and status. Preserve learner wording under Learner Reflections. Do not copy tutoring dialogue or invent unobserved estimates.

Validate the staged source before replacing an existing file. When upgrading legacy content, preserve all human reflections and existing extraction history; map old sections into v2 rather than dropping them.

## Step 3 — Hash-based wiki ingest

Run a targeted `/wiki-ingest <slug>.md` for this source hash.

- Source records remain read-only in this step.
- Wiki assertions refer to claim IDs and source locators.
- Conflicts remain explicit; outdated assertions are marked superseded.
- Human Notes are preserved.
- A changed source is re-ingested even if its filename already appears in the log.

Record created, updated, and superseded assertions plus the source hash in the run manifest.

## Step 4 — Record reading feedback

Prepare one compact `ReadingFeedback` record and ask the user to confirm or edit only fields not already explicit in the session:

```yaml
paper_id:
slug:
read_depth: full
rating: high-value | useful | low-fit
usefulness: evidence | method | data | mechanism | citation | compact combination
surprise:
belief_changed:
idea_affected: [idea slugs or none]
reason:
```

Append the confirmed record through `python "<AI_EDUCATION_PATH>\tutor\reading_feedback.py" record --paper-id "<paper_id>" --slug "<slug>" ... --run-id "<safe-run-id>"`; the recorder generates `schema_version`, `feedback_id`, `recorded_at`, `outcome`, actor, and provenance. It updates `<AI_EDUCATION_PATH>\tutor\reading_feedback.jsonl` and regenerates `paper_preferences.md`. Do not write duplicate feedback for the same paper/run.

## Step 5 — Stage an idea delta

Build candidates from `researcher_reflection` claims, Open Questions, and explicit Idea Relationships. Classify each:

- **A — Link to an existing idea**: there is a specific relationship and target slug.
- **B — Propose a new capture**: a concrete researchable question and causal/mechanistic channel exist.
- **C — Keep in knowledge only**: methodological/general/too vague.

Present a compact proposal table with candidate claim ID, relationship, action, target, and one-sentence rationale. Persist it with `research_core.py run step-wait ... propose_idea_delta --reason "confirm candidate actions" --details <candidate-json>`, then stop. No idea/index/log write occurs before explicit confirmation. After confirmation, run `research_core.py run resume ...` and complete the step with the accepted/revised IDs.

## Step 6 — Apply only confirmed deltas

After confirmation, the single writer:

- adds a compact row to the target idea's `## Evidence from Readings`: claim ID, relationship, how it changes the idea, and source path
- or creates a new idea from `_template.md` with `status: capture`, original user/reflection wording, and claim-ID source link
- updates idea index and append-only log once
- records accepted/skipped candidate IDs in source Processing State and the run manifest

Do not copy a long reflection into both source and idea. If new evidence can change an active Full S2 Gate, set generated dirty fields and append one dirty-history/log event; do not change any human decision.

## Step 7 — Update reading lifecycle

Idempotently:

- mark the paper exported/completed in AI Education index and completed records
- remove it from the active reading queue by canonical paper ID and aliases
- update context snapshot and idea seed link without duplicating entries
- regenerate the Markdown queue from structured queue state
- request the normal queue sync only after the local transaction commits

## Step 8 — Project the profile

Run the deterministic profile projector from approved idea state and confirmed reading feedback. It must preserve human-declared profile sections and write separate `declared`, `portfolio`, `inferred`, `speculative`, and `negative` signals with provenance, confidence, and recency.

Copy the validated profile projection to the local paper-tracker project and emit `profile.snapshot.published`. Do not silently `git push`; report whether the remote tracker still needs a push/sync.

## Final report

Report the run ID, completed/waiting/failed steps, written artifacts, feedback result, confirmed idea deltas, gates marked dirty, queue state, profile snapshot hash, and exact resume command. Keep the report under one screen unless a failure needs details.
