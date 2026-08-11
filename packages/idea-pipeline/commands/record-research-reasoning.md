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
