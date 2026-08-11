---
name: paper-cluster-synthesis
description: "Use this skill when the user invokes $paper-cluster-synthesis, /paper-cluster-synthesis, asks to synthesize several papers around one question, wants a claim or identification matrix, or wants to decide which single paper in a literature cluster deserves human deep reading."
---
# paper-cluster-synthesis

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/ai-education/.claude/commands/paper-cluster-synthesis.md","source_sha256":"74cc9ecf6b4c28d2589ad77d67cda50f6b01c9d1b3b8325f4bf0fb72d3fb1c99","workflow_version":"3.4.0"} -->

## Trigger Forms

- $paper-cluster-synthesis
- /paper-cluster-synthesis
- Natural language requests to synthesize three to eight related papers and identify the frontier delta

## Codex Execution Rules

- Do **not** read `~/.claude/commands/paper-cluster-synthesis.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /paper-cluster-synthesis

Synthesize three to eight papers around one research question, mechanism, or
empirical wedge. This is the default bridge between broad AI reading and one
pivotal human deep read.

## Protocol

1. Read `~/.claude/machine_paths.md` and resolve `<AI_EDUCATION_PATH>`,
   `<IDEA_VAULT>`, and `<WIKI_VAULT>`.
2. Require an explicit cluster ID plus three to eight paper IDs from a confirmed
   batch-triage manifest. Do not silently widen the cluster.
3. Read existing source/notes first. Retrieve external text only for claims not
   already covered locally.
4. Label every claim's coverage as `metadata`, `abstract`, `selected sections`,
   or `full text`, and attach source locators when available.
5. Write `<AI_EDUCATION_PATH>\papers\clusters\<cluster-id>.md` atomically.

## Required output

- Common research object and why it matters economically
- Claim matrix: paper, unit, treatment/exposure, outcome, design, claim, coverage
- Identification comparison
- Contradictions, nulls, and boundary conditions
- Data and institutional-setting opportunities
- Nearest-paper / already-done threat
- Frontier delta: what remains genuinely unresolved
- Relevance to the current primary/backup JMP idea
- Reading decision: one pivotal `deep`, up to two `targeted`, or no human read
- One cheapest empirical falsification or feasibility test

Do not create a new idea automatically. If the cluster reveals a candidate,
stage it for explicit human selection and send it to `/idea-feasibility` before
a Full S2 gate. Do not inflate cluster synthesis into claims that the learner
personally mastered every paper.

If the learner identifies the decisive contradiction, missing mechanism,
measurement replacement, or cheapest falsification, persist that observable
move through `/record-research-reasoning`. The cluster file stores evidence;
reasoning memory stores the learner's reusable transformation rule.
