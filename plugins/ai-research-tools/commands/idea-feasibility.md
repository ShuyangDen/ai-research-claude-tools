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
- estimated up-front hours, whether costly collection is required, and a first
  informative signal obtainable within 14 days;
- one explicit early stopping rule tied to access, merge quality, treatment
  variation, first stage, power, or outcome observability;
- a salvage artifact that remains useful if the candidate is killed;
- whether a well-powered null or contrary result would still answer an
  economically meaningful question;
- three nearest papers and the remaining economic wedge;
- a day-by-day deliverable plan.

## Update and status

Update only evidence-backed fields and artifact paths. Then run:

If an existing sidecar uses `gate_schema_version: 1`, upgrade it in place to
version 2 before checking: preserve all human decision and evidence fields,
add the new investment/early-signal/salvage/null fields and sections, and keep a
backup. Do not replace a populated sidecar wholesale with the blank template.

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

Do not treat "the estimate may be zero" as a reason by itself. The relevant JMP
risk is large irreversible effort before any informative signal, especially
when a failed data build has little reuse value or the null would be
underpowered/uninterpretable. Record the resulting reasoning and idea-feedback
events through `/record-research-reasoning`.
