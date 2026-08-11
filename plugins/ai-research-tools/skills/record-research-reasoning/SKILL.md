---
name: record-research-reasoning
description: "Use this skill whenever the researcher explains why a paper or idea is interesting, weak, modified, stopped, or rejected; reports advisor feedback; identifies a recurring thinking habit; or asks AI to remember how they reason. It records compact, provenance-aware research reasoning and idea feedback without storing raw chain-of-thought or conflating taste with feasibility and advisor fit."
---
# record-research-reasoning

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/record-research-reasoning.md","source_sha256":"a0ef1fa07be13bfa9a97c649bb6330271b8f384cadf3b5da4def2ca8e3443bec","workflow_version":"3.4.0"} -->

## Trigger Forms

- $record-research-reasoning
- /record-research-reasoning
- Natural language research conversations containing durable critique, idea-choice, feasibility, stopping, preference, or advisor-feedback signals

## Codex Execution Rules

- Do **not** read `~/.claude/commands/record-research-reasoning.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /record-research-reasoning

Persist compact, observable evidence about how the researcher evaluates papers,
forms ideas, revises mechanisms, responds to feasibility constraints, and uses
advisor feedback. The objective is to learn reusable research judgment without
storing raw transcripts or pretending to capture hidden chain-of-thought.

## Trigger

Run this workflow when the researcher:

- explicitly says why a paper or idea is interesting, weak, surprising, or not worth the time;
- endorses another researcher's question-forming move and explains why that
  externally authored idea pattern is worth learning or reusing;
- catches an assumption, measurement, identification, equilibrium, or external-validity problem;
- transforms an initial question into a sharper mechanism or estimand;
- compares two papers or ideas and explains the preference;
- reports advisor support, skepticism, rejection, or a requested pivot;
- identifies a repeated project constraint such as data cost, time to first signal, reversibility, or JMP timing;
- asks the AI to remember a research-thinking habit.

Do not record routine logistics, assistant-only speculation, raw private
conversation, or a preference inferred from silence.

## Paths

Read `~/.claude/machine_paths.md` and resolve `<TOOLS_ROOT>` and `<IDEA_VAULT>`.
Runtime memory is private and append-only:

```text
<IDEA_VAULT>\ideas\memory\reasoning-events.jsonl
<IDEA_VAULT>\ideas\memory\idea-feedback.jsonl
```

## Two distinct records

### 1. Reasoning event

Use a reasoning event for an observable intellectual move. Store:

- the trigger: fact, anomaly, institutional detail, paper claim, or decision problem;
- one or more public `thinking_moves`, such as measurement reframing,
  mechanism decomposition, heterogeneity, equilibrium reasoning,
  identification diagnostic, data feasibility, time cost, or option value;
- a concise rationale summarizing what the researcher said;
- the decision or candidate delta;
- alternatives explicitly rejected;
- a reusable transfer rule only when the researcher stated it or confirmed it;
- `durability`: `candidate_specific`, `repeated_pattern`, or `declared_constraint`;
- actor and actor basis.

This is a compact decision rationale, not private chain-of-thought.

### Endorsed external idea pattern

When the learner likes an idea or question-forming move that originated in a
paper, preserve two authorships rather than collapsing them:

- `intellectual_origin: external_exemplar` for a source-authored move, or
  `hybrid_synthesis` when the learner materially transforms it;
- `source_pattern`: what the paper's author did when forming the question;
- `endorsement_rationale`: why the learner likes that move;
- `transferable_element`: the abstract move that future ideation may reuse;
- `transfer_boundary`: what must not be copied or attributed to the learner;
- a stable paper/claim reference in `source_refs`.

The author's idea is not learner-original. The learner's selection, explanation,
and transformation are valid taste and reasoning evidence when directly stated.

### 2. Idea feedback

Use idea feedback whenever a generated or human idea is kept, modified,
advanced, held, parked, rejected, or deleted. Evaluate these axes separately:

- intrinsic interest;
- importance;
- mechanism;
- novelty;
- identification;
- data feasibility;
- time to first informative signal;
- salvage value if the project fails;
- JMP fit;
- advisor fit.

Unknown stays `unknown`. Never fill a missing reason with a plausible guess.

## Provenance and learning rules

- Direct researcher statements may become `profile_eligible` reasoning when
  `human_confirmed: true`.
- A directly endorsed external exemplar may teach idea-generation style, but
  must retain paper authorship. Project the learner's endorsement/transfer rule,
  never a false claim that the learner originated the source idea.
- Researcher-reported advisor feedback uses actor/rater `advisor` plus basis
  `researcher_reported`. It informs feasibility and portfolio constraints, not
  the researcher's intrinsic taste.
- An AI-generated candidate remains quarantined as a topic until authoritative
  `ADVANCE-S3`. The researcher's separately stated mechanism-level rationale
  may still become a human reasoning event.
- Assistant inference is stored only when useful as a proposal, with
  `actor_basis: inferred`, `human_confirmed: false`, and
  `profile_eligible: false`.
- A null or contrary result is not automatically a failure. Record whether it
  would be well powered, interpretable, and economically informative. The risk
  to penalize is large irreversible effort before any useful signal, especially
  when failed work has little salvage value.

## Record commands

Stage each JSON object locally, validate it, then append through the deterministic CLI:

```powershell
python "<TOOLS_ROOT>\scripts\research_core.py" memory record-reasoning `
  <reasoning-event.json> --idea-vault "<IDEA_VAULT>"

python "<TOOLS_ROOT>\scripts\research_core.py" memory record-idea-feedback `
  <idea-feedback.json> --idea-vault "<IDEA_VAULT>"
```

The commands are idempotent. A conflicting duplicate ID is an error.

## Interaction policy

- If the researcher explicitly supplied the relevant rationale, persist it
  without forcing another questionnaire.
- Ask at most one compact follow-up when the missing distinction would change
  learning materially, such as taste versus feasibility or researcher versus
  advisor judgment.
- Do not interrupt every substantive turn. Accumulate a bounded session delta
  and persist at a terminal paper state, an idea decision, an advisor update, or
  the end of a substantive work session.
- Briefly confirm what was recorded and which fields remain unknown.

## Profile handoff

`/update-researcher-profile` reads both logs. Promote only repeated or declared,
direct, human-confirmed transfer rules. Candidate-specific and advisor outcomes
remain visible to feasibility, deduplication, and portfolio ranking without
silently becoming taste.
