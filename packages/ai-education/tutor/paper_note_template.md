# Paper Note Template

Use this template for `papers/notes/<slug>.md`. Existing notes do not need to be migrated unless they are reopened for a new reading session.

## Phase 0 Triage

| Field | Notes |
|---|---|
| Broad research question | <what the paper asks> |
| Plain-language story preview | <2-4 connected sentences: who faces what problem, what the authors do, and what they claim> |
| Setting / data / model | <empirical setting, model setting, or data source> |
| Core design / comparison | <main identification strategy, model comparison, or argument structure> |
| Main claim | <central contribution or result family> |
| Relevance to learner agenda | high / medium / low, with one-line reason |
| Strongest reason to read | <why it may be useful> |
| Strongest reason to skip | <why it may not be worth deep reading> |
| Triage decision | 精读 / 定向粗读或略读（store as targeted/selective/rough） / 跳过 |
| Recommended deep-read modules | <1-3 modules only, or none> |

## Phase 1 Math Necessity Gate

| Field | Notes |
|---|---|
| Gate outcome | waived / quick-check / teaching-required |
| Mastery evidence used | <direct learner statement, prior alignment, math-gaps record, or genuinely uncertain> |
| Foundations waived | <named objects such as DiD or SVD; do not add explanations here> |
| Blocking foundations to teach | <only unfamiliar objects required for the chosen scope, or none> |
| Gate decision | <why the tutor proceeds directly to the story or pauses for one focused lesson> |

## Phase 1 Alignment Status

| Concept | Necessity | Learner status | Group | Paper anchor | Paper context aligned? | Last check | Needs visualization? |
|---|---|---|---|---|---|---|---|
| <concept> | blocking / previously aligned / new but optional / paper detail, defer | known-waived / simple-waived / uncertain-quick-check / teaching-required / understood / shaky / gap / deferred | core identification / supporting estimation / paper-specific term | <one-line original-paper anchor, or none> | yes / no / not used | <evidence or checkpoint result; "direct statement" is valid> | yes / no |

Rules:

- Phase 1 always makes a gate decision, but teaching occurs only for `blocking + teaching-required` items.
- `known-waived` and `simple-waived` receive no definition, toy example, derivation, or teach-back unless the learner asks.
- `previously aligned` means a quick reminder is enough unless the learner is shaky.
- `new but optional` means teach only if the learner chooses that deep-read module.
- `paper detail, defer` means do not teach in Phase 1; handle in Phase 2 only if needed.
- If `Paper anchor` is not `none`, Trevor must complete the Paper Context Mini-Gate before asking the learner to reason about that anchor.
- `Paper context aligned?` is `yes` only if outcome, treatment/key variable, comparison/baseline, and reason for the method were all made explicit.
- `Status` should not be marked `understood` unless the learner explained a taught concept back in their own words.
- A direct learner statement plus consistent prior evidence is sufficient for `known-waived`; do not relabel it `understood` merely to force a test.

## Phase Transition Log

| Transition | Confirmed by learner? | Notes |
|---|---|---|
| Phase 1 -> Phase 2 | yes / no | <what was still shaky, if anything> |
| Phase 2 -> Phase 3 | yes / no | <what paper argument was completed> |

## Selective Read Scope

Use this section when the paper is intentionally archived as a rough read or selective read.

| Field | Notes |
|---|---|
| Reading status | full read / rough-read complete / selective read / skipped |
| Selective focus actually read | <dataset construction, identification issue, mechanism, result family, etc.> |
| Why this focus was enough | <learner's reason> |
| Skipped or deferred details | <methods, results, appendices, robustness, mechanisms not read> |
| Full idea extraction requested? | yes / no |

## Tutor Mistakes / Learner Corrections

Record process corrections with high fidelity. These are framework-learning signals, not ordinary paper notes.

| Moment | Learner correction | Protocol implication |
|---|---|---|
| <where it happened> | <verbatim correction if possible> | <e.g., "background was not aligned before using paper anchor"> |

## Phase 2 Complete Story Map

### Setting and Actors

### Economic Puzzle / Core Question

### Unit, Timing, Treatment or Key Variable, Comparison, and Outcome

### Mechanism Chain

### Identification / Model Counterfactual

### Headline Findings and Magnitudes

### Interpretation, Contribution, and Limits

### Selected Deep-Read Modules

## Skipped / Deferred Details

Record intentionally skipped methods, proofs, robustness checks, appendix details, or measurement construction. Include the reason: low relevance, not blocking, learner not interested, or deferred until needed.

## Critical Reflections (Phase 3)

Record every critique, doubt, and open question with origin labels:

- `independently-identified`
- `guided`
- `tutor-added`

Preserve the learner's original wording whenever possible.

## Endorsed External Idea Patterns

Use this only when the learner explicitly likes a research question or
idea-forming move that originated with the paper's authors.

| Source paper / claim | Author's idea-forming move | Why learner likes it | Transferable element | Transfer boundary |
|---|---|---|---|---|
| <stable paper/claim reference> | <what the authors did> | <learner's stated reason> | <abstract move to reuse> | <what not to copy or claim as learner-original> |

Label these `author-origin / learner-endorsed`. Do not merge them with
`independently-identified` critiques or learner-original research questions.

## Open Questions
