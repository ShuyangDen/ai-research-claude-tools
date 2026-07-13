---
name: paper-rough-done
description: "Use this skill when the user invokes $paper-rough-done, /paper-rough-done, or says a paper was selectively read and should be archived as a rough-read record. This is the Codex adapter for the canonical lightweight post-paper workflow."
---
# paper-rough-done

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/paper-rough-done.md","source_sha256":"f283df39e15e295ee0c579c0b390c2edc01343c07960c9a10fdc08b9b62e683f","workflow_version":"3.0.0"} -->

## Trigger Forms

- $paper-rough-done
- /paper-rough-done
- Natural language signals that a selectively read paper should be archived as a rough-read record

## Codex Execution Rules

- Do **not** read `~/.claude/commands/paper-rough-done.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /paper-rough-done

Complete an intentional selective/rough reading through the same durable transaction as `/paper-done`, with narrower export and no default idea creation.

## Usage

`/paper-rough-done <slug>`

Resolve paths and use `python "<TOOLS_ROOT>\scripts\research_core.py" run ... --state-root "<STATE_ROOT>"` exactly as `/paper-done`. Use workflow `paper-rough-done` and these steps:

1. `validate_note`
2. `export_source`
3. `ingest_wiki`
4. `record_feedback`
5. `update_reading_state`
6. `project_profile`

## Selective-reading contract

The note and source must state:

- `reading_status: selective`
- `read_depth: rough` or `selective`
- modules/sections actually covered
- details deliberately deferred or not covered
- learner reflections and open questions grounded in the covered material

Use source schema v2 and stable paper/claim IDs. Never summarize full-paper results, appendices, mechanisms, or estimates that were not read. `coverage` is a boundary, not a completeness score.

Run targeted hash-based wiki ingest. Only project useful assertions from covered material.

## Reading feedback

Confirm and append the same `ReadingFeedback` schema as `/paper-done`, with the actual rough/selective depth. A selective read may still be `high-value`; do not equate depth with usefulness. Record surprise, belief change, and affected ideas.

## Idea extraction

Default: no idea write. Preserve reflections in the source and set `idea_extraction: skipped_by_default` in Processing State. If the user explicitly requests extraction, stage claim-ID candidates through `/idea-extract-from-source`; still require confirmation before writing ideas.

## Reading lifecycle and profile

Mark the queue item completed with its actual read depth, update AI Education index/completed/context state idempotently, regenerate the queue view, and run the profile projector. Do not silently push git remotes.

Report the run ID, coverage, source/wiki changes, feedback, local/remote queue status, profile snapshot, and resume command if incomplete.
