---
name: paper-batch-triage
description: "Use this skill when the user invokes $paper-batch-triage, /paper-batch-triage, has too many recommended papers, receives a weekly paper digest, asks which papers are actually worth reading, or wants to classify a batch into deep, targeted, cluster-only, skip, and backlog actions."
---
# paper-batch-triage

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/ai-education/.claude/commands/paper-batch-triage.md","source_sha256":"4304310743c60f8a2f3e38b3aeeb8a1cbfc49a414f5ac066a9bafb04e009b1ce","workflow_version":"3.4.0"} -->

## Trigger Forms

- $paper-batch-triage
- /paper-batch-triage
- Natural language requests to triage a weekly or overloaded reading queue as one bounded batch

## Codex Execution Rules

- Do **not** read `~/.claude/commands/paper-batch-triage.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /paper-batch-triage

Triage a capacity-bounded batch of papers before opening any one-paper tutor
session. Use this workflow when the reading queue feels large, the weekly digest
arrives, or the learner asks what is actually worth reading.

## Paths and inputs

Read `~/.claude/machine_paths.md` and resolve `<AI_EDUCATION_PATH>` and
`<PAPER_TRACKER_PATH>`. Prefer `<AI_EDUCATION_PATH>\papers\queue_state.jsonl`
when it is fresh; otherwise use `<PAPER_TRACKER_PATH>\queue_state.jsonl`.

Run from AI Education:

```powershell
python papers\batch_triage.py prepare `
  --queue-state "<QUEUE_STATE>" `
  --output-dir papers\batch_triage `
  --max-papers 10
```

The helper selects at most ten active papers. Do not bypass the active queue to
inflate the batch.

## Build source-grounded paper cards

For every selected paper, retrieve the best accessible abstract and inspect the
introduction/design/main-result information only as needed. Mark coverage as
`metadata`, `abstract`, `selected sections`, or `full text`; never imply that the
learner read the paper.

Each card contains:

1. research question;
2. setting/data;
3. design or model;
4. main claim;
5. direct connection to the primary/backup JMP question, if any;
6. strongest reason to spend learner time;
7. strongest credibility, duplication, or feasibility threat;
8. recommended action: `deep`, `targeted`, `cluster-only`, `skip`, or `backlog`;
9. selected sections when recommending `targeted`;
10. one or more reason codes: `importance`, `mechanism`, `identification`,
   `data`, `measurement`, `surprise`, `feasibility`, `contradiction`,
   `duplicate`, `low-fit`, or `time-cost`.

Group cards by research question or mechanism. Present one compact batch table,
not ten sequential mini-sessions. Ask one question for the entire decision set.
If two papers compete for the same attention slot, ask for or infer only from an
explicit answer which wins and why; record that pairwise comparison.

## Apply confirmed decisions

After the learner confirms the batch, write one temporary JSON object:

```json
{
  "decisions": [
    {
      "paper_id": "...",
      "candidate_slug": "...",
      "action": "targeted",
      "reason_codes": ["mechanism", "identification"],
      "rationale": "...",
      "would_build_on": true,
      "predicted_value": 4,
      "selected_sections": ["identification", "main table"],
      "cluster_id": "..."
    }
  ],
  "comparisons": [
    {
      "winner_paper_id": "...",
      "loser_paper_id": "...",
      "reason_codes": ["feasibility"],
      "rationale": "..."
    }
  ]
}
```

Then run:

```powershell
python papers\batch_triage.py apply `
  --batch "papers\batch_triage\<batch-id>.json" `
  --decisions "<TEMP_DECISIONS_JSON>" `
  --queue-state "<QUEUE_STATE>" `
  --triage-log tutor\triage_feedback.jsonl `
  --comparison-log tutor\taste_comparisons.jsonl
```

For each confirmed `skip`, also run `/record-reading-feedback` with
`read_depth=skipped`, `rating=low-fit`, `usefulness=none`, the confirmed reason
codes, and the learner's compact rationale. A skip is taste evidence, not a read.

Do not create full paper notes, wiki source notes, or research ideas for
`cluster-only`, `skip`, or `backlog`. Run `/sync-reading-queue` after decisions
so canonical remote state receives the human actions.

## Handoff

- `deep` enters Trevor at Phase 0 and may proceed through the normal protocol.
- `targeted` enters Trevor with explicit selected modules and may finish through
  `/paper-rough-done`.
- a cluster with at least three papers may enter `/paper-cluster-synthesis`.

When the learner explains why one paper outranks another, why a paper is not
worth the time, or what kind of evidence they seek, also call
`/record-research-reasoning`. Preserve the pairwise comparison as the paper
choice and the reasoning event as the reusable decision rule. Do not turn a
single unexplained skip into a durable preference.
