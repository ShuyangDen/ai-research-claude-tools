---
name: idea-extract-from-source
description: "Use this skill when the user invokes $idea-extract-from-source, /idea-extract-from-source, asks to run idea-extract-from-source, or asks to extract research ideas from an exported source note. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-extract-from-source

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-extract-from-source.md","source_sha256":"6713e24f56edd848ceb79890869fe3a222fa3a4352d953455c027077373d3aba","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-extract-from-source
- /idea-extract-from-source
- Natural language requests to extract research ideas from an exported source note

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-extract-from-source.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-extract-from-source

Stage provenance-preserving idea deltas from one personal-knowledge source record.

## Usage

`/idea-extract-from-source <source-file>`

Read machine paths as UTF-8, then read the source record, target idea metadata, and existing extraction/run state. Source schema v2 is preferred; legacy sections may be mapped without rewriting the source during proposal.

## Candidate construction

Use only:

- `researcher_reflection` claims
- explicit Open Questions
- explicit Idea Relationships

Every candidate needs a stable claim ID. For a legacy source, assign deterministic provisional IDs from paper ID/source hash and item order; label them provisional until the source is upgraded.

Classify:

- **A — Link existing**: a specific target idea and support/contradict/refine/method/data relationship exist.
- **B — New capture**: the source contains a concrete researchable question and named mechanism/channel.
- **C — Knowledge only**: useful knowledge but not a sufficiently specific idea delta.

Do not use general paper findings as if they were the researcher's new idea. Deduplicate by `(source hash, claim ID, target, action)` rather than by prose similarity alone.

## Human checkpoint

Present:

| # | Claim ID | Type | Proposed action | Target | Why |
|---|----------|------|-----------------|--------|-----|

Use the research-core run store with a filesystem-safe run ID derived from source hash. Pre-register `propose_idea_delta` and `apply_confirmed_delta`, persist the proposal with `run step-wait ... --reason "confirm candidate actions" --details <candidate-json>`, then stop. Accept `confirm`, `revise #N ...`, or `skip`; resume the same run before applying. Do not write idea/index/log files before confirmation.

## Confirmed write

The single writer applies only confirmed items:

- Existing idea: add one row under `## Evidence from Readings` with claim ID, relationship, one sentence explaining the idea delta, and source path.
- New capture: create from `_template.md`, preserve the original reflection/question, and link its source claim ID. Do not auto-run S2.
- Update idea index/log once and append accepted/skipped candidate IDs to source Processing State through the paper workflow writer.

Never copy a long source passage into multiple idea files. If a confirmed delta changes an approved S2 scope or frontier synthesis, mark the gate dirty without changing human fields.

Report accepted/skipped candidates, exact files changed, and any gate made dirty.
