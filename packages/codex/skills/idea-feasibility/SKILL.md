---
name: idea-feasibility
description: "Use this skill when the user invokes $idea-feasibility, /idea-feasibility, asks to test whether a research idea is empirically feasible, wants a two-week data/identification sprint, or wants a continue/pivot/kill feasibility decision before a full literature gate."
---
# idea-feasibility

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-feasibility.md","source_sha256":"86c106608ee49534492133a527e71b827ad1d8a471f03a7fd3717638dd4d1aa1","workflow_version":"3.3.0"} -->

## Trigger Forms

- $idea-feasibility
- /idea-feasibility
- Natural language requests to test an idea's data, identification, minimum artifact, and nearest-paper feasibility

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-feasibility.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-feasibility

Run a two-week empirical feasibility sprint before committing an idea to a
costly Full S2 literature gate. Use for a promising mechanism that still needs a
real dataset, exogenous margin, minimum analysis artifact, or nearest-paper test.

## Usage

`/idea-feasibility <slug> start|update|status|decide`

Read `~/.claude/machine_paths.md` and resolve `<TOOLS_ROOT>` and `<IDEA_VAULT>`.
The authoritative sidecar is:

`<IDEA_VAULT>\ideas\feasibility\<slug>-feasibility.md`

## Start

Read the target idea first. Copy
`<IDEA_VAULT>\ideas\_feasibility_gate_template.md` to the authoritative
sidecar, set the slug, today's date, and a deadline exactly 14 days later. Keep
`human_decision: pending`. Starting the sprint does not advance the idea.

Build the initial sprint around:

- one-sentence estimand;
- named exogenous variation;
- named obtainable data and acquisition route;
- one minimum artifact: sample extract, first stage, descriptive figure, power
  calculation, replication, or simulation;
- three nearest papers and the remaining economic wedge;
- a day-by-day deliverable plan.

## Update and status

Update only evidence-backed fields and artifact paths. Then run:

Use an absolute `minimum_artifact_path` when practical. A relative artifact
path is resolved from the feasibility sidecar's directory.

```powershell
python "<TOOLS_ROOT>\scripts\research_core.py" feasibility-check `
  "<IDEA_VAULT>\ideas\feasibility\<slug>-feasibility.md"
```

Use `--apply-ready` only when the read-only check is ready. That option may set
generated readiness fields but must not set a human decision.

## Decide

Only the researcher may choose `continue`, `pivot`, or `kill`. Record actor,
date, reason, next action, and what evidence would reverse the decision.

- `continue`: the idea may enter Full S2 or become the dashboard primary/backup.
- `pivot`: freeze the failed estimand/data route and start a new scoped sprint.
- `kill`: retain the sidecar and failure reason as negative taste/feasibility
  evidence; do not delete the idea history.

An attractive literature gap without an acquired/tested sample and minimum
artifact is not ready.
