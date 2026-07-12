# {{title}} — S2 Full Literature Gate

```yaml
---
gate_schema_version: 2
idea_slug: {{slug}}

gate_status: draft             # draft / active / ready_for_human_decision / closed
gate_phase: pkb_context        # pkb_context / scope_approval / pkb_evidence / search_protocol / external_search / screening / human_reading / synthesis / adversarial_search / researchability / adjudication / closed
gate_dirty: false
dirty_reasons: []

scope_version: 1
scope_hash:
scope_approved_by:
scope_approved_date:

search_as_of:
refresh_due:

ai_readiness: NOT_READY        # NOT_READY / READY_FOR_HUMAN_DECISION
readiness_checked_at:

# Human-only fields. AI must never populate these without explicit user decision.
human_gap_status: unreviewed   # unreviewed / supported_by_search / contested / refuted / unresolved
human_decision: pending        # pending / ADVANCE-S3 / LOOP-S2 / RETURN-S1 / PARK-METHOD / PARK-PRIORITY / STOP-DUPLICATE
human_decision_by:
human_decision_date:
---
```

## 0. Frozen S1 Original

- Original idea text:
- Idea page:
- S1 preserved without rewrite: yes/no

## 1. PKB-A Context Recall

This phase starts from the frozen S1 wording before the human approves a searchable scope.

### Source Availability

| Source | Path / collection | Available? | Notes |
|---|---|---|---|
| Machine paths | `~/.claude/machine_paths.md` |  |  |
| Researcher profile |  |  |  |
| Idea map / index |  |  |  |
| Existing active ideas |  |  |  |
| Parked / rejected / archived ideas |  |  |  |
| Prior idea extraction records |  |  |  |
| Personal source notes |  |  |  |
| Zotero / annotations |  |  |  |
| Local full texts / PDFs |  |  |  |

### Related Ideas and Prior Decisions

| Idea | Status / decision | Relationship | What to reuse / avoid |
|---|---|---|---|

### Prior Extraction Records

| Source note | Extracted idea / record | Relevance | Follow-up |
|---|---|---|---|

### Critical Reflections and Open Questions

| Source note | Reflection / open question | Mechanism / data / ID signal | Relevance |
|---|---|---|---|

### Known Seeds / Mechanisms / Data / Identification

- Known seed papers:
- Recurring mechanisms:
- Known datasets / settings:
- Known shocks / assignment rules:
- Preferred or distrusted identification patterns:
- Scope questions for the human:

### Context Brief

- Candidate interpretations:
- Incompatible interpretations:
- Known prior failures / parked variants:
- What the researcher already knows:
- What must not be inferred from local preference alone:

## 2. Human-Approved Scope Card

AI may draft options, but the human chooses the active searchable scope.

- Unit / population:
- Setting:
- Exposure / object:
- Outcome:
- Mechanism:
- Claim type:
- Candidate contribution:
- Exclusions / out of scope:
- Closest literature families:
- Scope approved by:
- Scope approved date:
- Scope hash:

## 3. PKB-B Local Evidence Search

This phase starts only after scope approval.

### Local Retrieval Manifest

| Run ID | Date | Local layer | Exact query / action | Scope axes | Hits inspected | Items linked | Zero / unavailable / stale | Next action |
|---|---|---|---|---|---:|---|---|---|

### Known-Item Recall Test

- Expected known items:
- Recovered:
- Missed:
- Query repair performed:
- Human recall check: pass / fail / waived with reason

If a high-signal known item is missed, repair query/path and rerun the affected local search before external search.

### Local Candidate Ledger

| Work / note / idea | Local source | Scope axes matched | Threat / support | Source level | Next action |
|---|---|---|---|---|---|

### What External Search Must Clarify

-

## 4. Search Protocol and Coverage Matrix

Use `system/literature_sources.yml` as a starter registry. Human-approved scope decides which sources are active.

| Route | Source / profile | Query family | Window / filters | Required? | Status | Waiver / notes |
|---|---|---|---|---|---|---|
| PKB-A | local |  |  | yes |  |  |
| PKB-B | local |  |  | yes |  |  |
| NBER / working papers |  |  |  | yes |  |  |
| Top economics journals |  |  |  | yes |  |  |
| Field journals |  |  |  | scope-dependent |  |  |
| Exact / lexical route |  |  |  | yes |  |  |
| Broad / semantic / index route |  |  |  | yes |  |  |
| Citation / author expansion |  |  |  | yes for nearest seeds |  |  |
| Learned-terminology rerun |  |  |  | yes |  |  |
| Review / survey / handbook |  |  |  | mature-field |  |  |
| Already-Done targeted search |  |  |  | yes |  |  |

## 5. Append-Only Search Log

Do not overwrite earlier runs. Record zero-result, paywall, unavailable, and incomplete routes.

| Date | Source | Exact query / action | Filters / window | Results inspected | Added candidates | New must/maybe | Learned terms | Failure / zero result | Next action |
|---|---|---|---|---:|---|---|---|---|---|

## 6. Candidate, Version, and Screening Ledger

### Candidate and Screening Ledger

| Work / manifestation | Found via | Shared axes | AI label / reason | Human label / reason | Source level | Full-text action |
|---|---|---|---|---|---|---|

Allowed labels: `must-read`, `maybe`, `irrelevant`, `pending-full-text`, `version-conflict`.

### Work Family / Manifestation Ledger

| Work family ID | Manifestation | DOI / ID | Status | Read manifestation? | Merge basis | Human confirmation |
|---|---|---|---|---|---|---|

Auto-merge only exact DOI/stable ID/explicit version relations. Fuzzy working-paper/journal matches require human confirmation.

## 7. Human Reading Queue and Evidence Table

### Human Reading Queue

| Work | Why must read | Decisive fields | Current read status | Needed action |
|---|---|---|---|---|

### Field-Level Evidence Table

| Claim ID | Work / manifestation | Field | Value | Evidence state | Source level | Locator | Extracted by | Human verified | Date |
|---|---|---|---|---|---|---|---|---|---|

Evidence states: `reported`, `author_interpretation`, `reviewer_inference`, `NR/unknown`.
Source levels: `metadata`, `abstract`, `introduction`, `targeted_full_text`, `table/appendix`, `full_text`.

## 8. Typed Relationship Ledger

| Edge ID | From | Relation | To | Axis / value | Basis | Source / locator | Evidence state | Confirmation | Relevant idea |
|---|---|---|---|---|---|---|---|---|---|

Minimum relation vocabulary:

- Identity / citation: `HAS_MANIFESTATION`, `SAME_WORK_FAMILY`, `CITES`, `CITED_BY`
- Contribution: `ASKS_SAME_QUESTION`, `EXTENDS`, `REPLICATES`, `THREATENS_IDEA`
- Mechanism: `TESTS_SAME_MECHANISM`, `EXTENDS_MECHANISM`, `ALTERNATIVE_MECHANISM`, `CONTRADICTS_MECHANISM`
- Data: `USES_SAME_DATASET`, `USES_LINKABLE_DATA`, `USES_SAME_SETTING`
- Identification: `USES_SAME_SHOCK`, `USES_SAME_ASSIGNMENT_RULE`, `USES_SAME_DESIGN_FAMILY`
- Idea history: `INSPIRED`, `BRANCHED_FROM`, `REJECTED_FOR`, `PARKED_FOR`

Confirmations: `metadata-observed`, `ai-proposed`, `human-confirmed`.

## 9. Synthesis Claim Ledger

| Synthesis claim | Supporting claims / sources | Contradicting or qualifying claims | Evidence strength | Remaining uncertainty | Human disposition |
|---|---|---|---|---|---|

## 10. Integrated Literature Review

Build this from source-grounded claims and human-read source notes. Do not synthesize decisive claims from abstracts only.

### Literature Architecture

### What Is Established

### Disagreements and Nulls

### Saturated Mechanisms / Designs

### Open Questions Surviving Full-Text Review

### Researcher Critical Reflections

Mark these as researcher interpretation, not paper facts.

### How Reading Changed the Idea

### Provisional Frontier / Watchlist

Use this for abstract-only or unresolved records.

## 11. Nearest-Neighbor Matrix

True nearest papers should be human-selected or human-confirmed.

| Axis | Paper 1 | Paper 2 | Paper 3 | This idea | Decisive difference | Verification status |
|---|---|---|---|---|---|---|
| Population / unit |  |  |  |  |  |  |
| Exposure / treatment |  |  |  |  |  |  |
| Mechanism |  |  |  |  |  |  |
| Outcome |  |  |  |  |  |  |
| Data / setting |  |  |  |  |  |  |
| Identification |  |  |  |  |  |  |
| Contribution |  |  |  |  |  |  |

## 12. Already-Done Memo and Targeted Rerun

- Strongest sourced case that the idea is already done:
- Best counterexample paper:
- Remaining difference:
- Why the difference may or may not matter economically:
- New aliases / learned terms:
- Targeted rerun query/actions:
- Rerun outcome:

## 13. Candidate Wedges

These are not formal S3 research questions. AI may propose; the human chooses.

| Candidate wedge | Evidence basis | Closest threat | Material difference | Possible research path | Main unresolved risk | Human status |
|---|---|---|---|---|---|---|

## 14. Researchability / Exogenous-Shock / Data-Path Triage

S2 only does low-cost feasibility reconnaissance. S4 validates data access and construction.

| Shock / data lead | Found in | Assignment / timing logic | Unit / outcomes | Candidate data | Prior use | Access evidence | Main threats | Human verdict |
|---|---|---|---|---|---|---|---|---|

Access status: `concept_only`, `event_verified`, `data_metadata_verified`, `access_verified`.

### Measurement or Theory Alternative

- Measurement path:
- Theory/model path:
- Why this remains worth S3 without a current empirical shock:

## 15. Stopping and Readiness Certificate

- [ ] S1 original is frozen.
- [ ] Scope Card is human-approved and current.
- [ ] PKB-A is complete.
- [ ] PKB-B manifest is complete.
- [ ] Known-item recall passed or has a human waiver.
- [ ] Every required external route is complete or has a human waiver.
- [ ] All Scope Card axes and adversarial query families were searched.
- [ ] Work families and relevant manifestations are resolved.
- [ ] Open must-read count is zero.
- [ ] No high-overlap maybe or pending-full-text item can reverse the decision.
- [ ] No unresolved version conflict can reverse the decision.
- [ ] True nearest papers were selected or confirmed by the human.
- [ ] Decisive nearest-paper fields have locators and human verification.
- [ ] Decisive unsupported claims equal zero.
- [ ] Citation/author expansion produced no unresolved material change.
- [ ] Learned-terminology/adversarial rerun produced no unresolved material change.
- [ ] Already-Done targeted search produced no new unresolved high-severity threat.
- [ ] Integrated Review is current relative to all linked source notes.
- [ ] Researchability reconnaissance is complete.
- [ ] Search freshness is acceptable for this field.
- [ ] Gate is not dirty and scope hash matches.

Only when all required items pass may AI set `ai_readiness: READY_FOR_HUMAN_DECISION`.

## 16. Human Gate Decision

Authoritative decision is read from frontmatter. This section is human-readable rationale only.

### Human Rationale

### Primary Wedge, If Any

### Closest Paper and Material Difference

### Conditions Carried Forward

## 17. Decision / Invalidation History

Append only.

| Date | Actor | Event | Previous state | New state | Reason | Scope version |
|---|---|---|---|---|---|---|
