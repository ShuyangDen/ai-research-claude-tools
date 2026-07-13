---
name: idea-challenge
description: "Use this skill when the user invokes $idea-challenge, /idea-challenge, or asks to stress-test a research idea. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-challenge

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-challenge.md","source_sha256":"40fa58c851b49fe48cbc0ed30b30237f9e07d0c729a5cac3fedec322ae985a4c","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-challenge
- /idea-challenge
- Natural language requests to stress-test a research idea

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-challenge.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-challenge

Run a bounded, single-agent stress test. This version deliberately does not start Challenge sub-agents; multi-agent behavior will be evaluated separately.

## Usage

`/idea-challenge <slug>`

Run `/idea-chat <slug> challenge`, then evaluate three lenses:

1. **Mechanism and identification** — estimand, counterfactual, plausible variation, measurement, and strongest alternative explanation.
2. **Literature and contribution** — only from the authoritative S2 sidecar and retrieved claim cards.
3. **Feasibility and falsification** — data availability, observability, scope, and evidence that would overturn the idea.

For each finding record:

```text
finding_id, lens, severity (critical|major|minor), claim, evidence_claim_ids, fix_or_test
```

Rules:

- Read the target and sidecar before retrieval; use the same context caps as `/idea-chat`.
- A literature finding with no current evidence is `UNVERIFIED`, not `OK`, `MAJOR`, or `CRITICAL`.
- Do not certify novelty or replace the Full S2 Gate.
- Distinguish a fatal contradiction from missing evidence. Missing evidence is normally a test/blocker, not proof the idea is wrong.
- Present the strongest 3 findings first; put additional minor findings in a collapsed/optional note rather than expanding the answer.
- Stage the result in the idea session and ask for one explicit confirmation or revision. Do not write the canonical idea on the first pass.

After confirmation, replace `## Challenge Panel Findings` with a compact table, append one log entry, and preserve evidence claim IDs. A `critical` finding creates a HOLD until the Decision Log records a resolution or explicit override. Never modify S2 human-only fields.
