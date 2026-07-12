# Research Idea Pipeline — JMP Idea Vault

This vault tracks research ideas for an economics PhD student.
It uses an LLM-assisted pipeline to move from raw intuitions to data-ready research proposals.

---

## Directory Layout

```
/
├── CLAUDE.md               ← this file (schema & pipeline rules)
├── sources/                ← slides, papers, notes related to ideas (READ ONLY)
├── system/
│   └── literature_sources.yml ← editable Level-1 source registry for S2 gates
├── ideas/
│   ├── index.md            ← kanban of all ideas by status
│   ├── log.md              ← append-only operation log
│   ├── _template.md        ← template for new ideas
│   ├── _frontmatter_cache.md  ← cache for fast status checks
│   ├── _profile_cache.json ← mtime cache for update-researcher-profile
│   ├── data/               ← downloaded datasets, organized by idea slug
│   ├── reports/            ← preliminary analysis reports
│   ├── reviews/            ← S2 literature gate sidecars and review memos
│   ├── _s2_gate_template.md ← template for full S2 literature gates
│   └── <slug>.md           ← one page per idea
```

---

## Pipeline Stages

Each idea moves through these stages in order:

| Stage | Name | Description |
|-------|------|-------------|
| S1 | **capture** | Idea submitted and structured |
| S2 | **explore** | Quick scan +, when needed, full literature review gate before S3 |
| S3 | **question** | Research questions and hypotheses refined |
| S4 | **data-search** | Datasets discovered and evaluated |
| S5 | **data-prep** | Data downloaded and cleaned |
| S6 | **report** | Preliminary analysis report generated |
| — | **done** | User decided to proceed with full project |
| — | **archived** | User decided not to pursue |

**Human checkpoints** (Claude pauses and waits for user review):
- After S2 (explore) — user reviews the full literature gate and explicitly chooses ADVANCE-S3 / LOOP-S2 / RETURN-S1 / PARK-METHOD / PARK-PRIORITY / STOP-DUPLICATE
- After S3 (question) — user confirms research questions
- After S4 (data-search) — user selects datasets to download

---

## Idea Page Format

Every idea page uses this frontmatter:

```yaml
---
tags: [idea]
status: capture
created: YYYY-MM-DD
updated: YYYY-MM-DD
priority: medium          # low / medium / high
domain: economics         # research field
checkpoint_pending: false  # true = waiting for user review
s2_review: none            # none / quick / full
s2_gate_outcome: null      # pending / ADVANCE-S3 / LOOP-S2 / RETURN-S1 / PARK-METHOD / PARK-PRIORITY / STOP-DUPLICATE
---
```

Older idea files may omit `s2_review` and `s2_gate_outcome`; treat missing values as `none` and `null`. Do not bulk-migrate old ideas unless they are being actively advanced.
These two fields are generated caches for status/index display. The authoritative S2 gate state and human decision live in `ideas/reviews/<slug>-s2-gate.md` frontmatter. If the idea cache and sidecar disagree, block transition and regenerate/sync cache before proceeding.

Cross-linking: use `[[PageName]]` for Obsidian wiki links.
At the bottom of each page, maintain a `## Related` section.

---

## S2 Literature Review Gate

S2 has two levels:

1. **S2 Quick Scan**: a lightweight initial scan for newly captured ideas. This replaces the old "max 5 papers / max 3 gaps" exploration. It should report candidate openings, tensions, or possible deltas, not verified gaps. It is useful for triage, but it is not enough to enter S3.
2. **S2 Full Literature Gate**: required before any idea can move from `explore` to `question`.

The full gate is normally written as `ideas/reviews/<slug>-s2-gate.md` using `ideas/_s2_gate_template.md`. Do not advance to S3 unless the user has explicitly reviewed the gate and recorded a dated `ADVANCE-S3` decision.

Required components of a full S2 gate:

1. **Personal Knowledge Base Pass**: this is the first layer of every Full Gate, before external search. Search the local researcher profile, idea map, existing idea files, source notes, prior extraction records, Zotero or annotation records when available, and relevant full-text papers in the personal knowledge vault. Summarize what the researcher already knows, including recurring mechanisms, data/identification preferences, prior rejected or parked directions, and citation/mechanism/data relationships among already-read papers.
2. **Scope Card**: state unit/population, setting, exposure/object, outcome, mechanism, claim type, candidate contribution, exclusions, and closest economics literatures. A substantive change to these axes invalidates the old gate and returns the idea to S2.
3. **Search Protocol and Search Log**: external search starts only after the Personal Knowledge Base Pass states what external search must clarify. Document sources searched, search terms, dates, and inclusion/exclusion decisions. Include top economics journals, NBER working papers, field journals, and credible recent working papers where relevant.
4. **Screening Table and Evidence Table**: separate broad hits from must-read papers; record what each paper studies, its data, method, mechanism, and threat to novelty. Decisive claims must distinguish `reported`, `author interpretation`, `reviewer inference`, and `unknown`.
5. **Integrated Literature Review**: after the user has read the must-read papers, synthesize the literature using local source notes and downloaded full texts, not only abstracts. Read introductions, related-work sections, data/method sections, and conclusions when available. The review should explain what the literature already knows, where papers disagree, which mechanisms are saturated, and how the candidate idea changes after reading.
6. **Researchability and Exogenous-Shock Triage**: before proposing a final research question, first search for credible exogenous shocks, discontinuities, policy changes, platform changes, staggered rollouts, or other quasi-experimental variation. For each candidate, evaluate data availability, identification threats, and whether outcomes are observable. If no plausible public or obtainable data path exists, default to LOOP-S2 or PARK rather than forcing S3.
7. **Theory/Model Alternative**: only after the exogenous-shock/data pass, consider whether the idea has a theory/model route. This should be grounded in the researcher's existing toolkit and preferences from the local knowledge base.
8. **Nearest-Neighbor Matrix and Already-Done Memo**: identify the closest papers and state whether the idea is already done, needs sharpening, should be parked, or is ready for human decision.
9. **Human Gate Decision**: the agent may mark READY FOR HUMAN DECISION, but only the user can choose `ADVANCE-S3`, `LOOP-S2`, `RETURN-S1`, `PARK-METHOD`, `PARK-PRIORITY`, or `STOP-DUPLICATE`.

If an idea fails because the literature is promising but no credible data or shock exists, keep the review as a reusable memo and park the idea until a better empirical setting appears.

---

## Stateful S2 Gate Contract

The Full S2 Gate is a resumable state machine, not a one-shot AI summary. It is executed by `/idea-s2-full <slug> start|resume|status|check`; `/idea-next` is only a transition guard.

### Authoritative State

`ideas/reviews/<slug>-s2-gate.md` frontmatter is authoritative for:

- `gate_schema_version`
- `gate_status`
- `gate_phase`
- `gate_dirty`
- `dirty_reasons`
- `scope_version`
- `scope_hash`
- `ai_readiness`
- `human_gap_status`
- `human_decision`
- `human_decision_by`
- `human_decision_date`

Idea frontmatter values such as `s2_review` and `s2_gate_outcome` are generated caches. If cache values conflict with the sidecar, block `/idea-next` and regenerate/sync cache. AI must never populate human-only fields: human read status, human verification, human gap status, human decision, or S3 stage.

### Gate Phases

Use these gate phases:

```text
pkb_context
scope_approval
pkb_evidence
search_protocol
external_search
screening
human_reading
synthesis
adversarial_search
researchability
adjudication
closed
```

Do not infer completion from phase names alone. Readiness requires the Stopping and Readiness Certificate in the sidecar.

### Two-Stage Personal Knowledge Base Pass

**PKB-A context recall** starts from the frozen S1 wording. It reads `~/.claude/machine_paths.md`, `researcher_profile.md`, idea map/index, related active ideas, parked/rejected/archived ideas and decision reasons, prior extraction records, and source-note sections such as Critical Reflections, Open Questions, Idea-Pipeline Relevance, and Idea Extraction Record. It outputs a Context Brief and questions the human must resolve in the Scope Card. It must not choose the scope or certify a gap.

**Human Scope Card approval** selects one searchable interpretation: unit/population, setting, exposure/object, outcome, mechanism, claim type, candidate contribution, exclusions, and closest literature families. If an idea mixes measurement, causal, and theory projects, return to S1 or split rather than letting AI choose.

**PKB-B scope-constrained local evidence search** happens only after scope approval. It searches source notes, critical reflections, open questions, idea extraction records, backlinks, Zotero/annotations when available, and high-signal local full text. It must produce a Local Retrieval Manifest, Known-Item Recall Test, local candidate ledger, and `What External Search Must Clarify`.

External search cannot begin until PKB-B is complete or the human records a waiver.

### Evidence, Relationships, and Versions

S2 gates must distinguish:

- machine accessed vs human read vs human verified for this idea;
- metadata, abstract, introduction, targeted full text, table/appendix, and full-text evidence;
- reported claim, author interpretation, reviewer inference, and unknown/NR;
- work family vs manifestation, including NBER/SSRN/author/journal versions.

Auto-merge only exact DOI/stable ID/explicit version relations. Fuzzy working-paper/journal matches require human confirmation. A version conflict that can change a nearest-neighbor judgment blocks readiness.

### Paper-Done Dirty Loop

When `/paper-done` processes a paper that is linked to an active S2 gate, it must not change the gate decision. It should mark the gate dirty and append a log event if newly verified evidence can change the Evidence Table, literature cluster, nearest-neighbor cell, Already-Done Memo, candidate wedge, or shock/data feasibility. Readiness returns to `NOT_READY` until `/idea-s2-full <slug> resume` rebuilds affected generated sections from canonical source notes.

### Stopping Rule

Never use a fixed paper count as the pass condition. `READY_FOR_HUMAN_DECISION` requires stable scope, required route coverage, known-item recall, nearest-neighbor resolution, threat closure, evidence closure, marginal/adversarial saturation, synthesis stability, researchability reconnaissance, freshness, and a clean/non-dirty gate. Sparse literatures need an explicit human waiver.

---

## Operations

### CREATE NEW IDEA (`/idea-new`)

Default behavior: **capture only** (no S2). Only run S2 if user explicitly requests it.

1. Ask user for: idea description, domain, priority, and whether to explore now or capture only
2. Create `ideas/<slug>.md` from `_template.md`; fill "Original Idea" section
3. If capture only: set status=capture, checkpoint_pending=false; tell user to run `/idea-next <slug>` when ready
4. If explore now: run S2 Quick Scan with **hard cap — max 5 papers, max 3 candidate openings/tensions/possible deltas**; set status=explore, checkpoint_pending=true, s2_review=quick, s2_gate_outcome=pending
5. Update `ideas/index.md` and `ideas/log.md`

### SOCRATIC REFINEMENT (`/idea-socratic <slug>`)

5-layer Socratic dialogue to refine a raw idea before formalizing the research question.
- Only available for ideas in status=capture or status=explore
- Saves output to `## S1.5: Socratic Refinement` section in the idea file
- The `explore → question` transition in `/idea-next` will use S1.5 insights if present
- If Socratic refinement changes a human-approved Scope Card's core axes, the existing S2 gate outcome becomes invalid and the idea must return to LOOP-S2.

### CHALLENGE PANEL (`/idea-challenge <slug>`)

3-lens single-pass critical evaluation (Methodology, Literature, Devil's Advocate).
- Recommended before advancing from question → data-search
- Saves output to `## Challenge Panel Findings` section in the idea file
- HOLD verdict blocks `/idea-next` until Decision Log records resolution or explicit override
- The Literature lens does not replace the S2 Full Literature Gate and must not certify novelty.

### ADVANCE IDEA (`/idea-next <slug>`)

Read the current `status` from the idea's frontmatter, then:

**capture → explore:**
- Run S2 Quick Scan with **hard cap: max 5 papers, max 3 candidate openings/tensions/possible deltas**
- Do not write `gap verified`, `novel`, a formal S3 research question, or `ADVANCE-S3`
- Set status=explore, checkpoint_pending=true, s2_review=quick, s2_gate_outcome=pending

**explore → question:**
- If `ideas/reviews/<slug>-s2-gate.md` is missing, stop and tell the user to run `/idea-s2-full <slug> start`. Do not create or complete the Full Gate inside `/idea-next`.
- If the sidecar is incomplete, dirty, stale, not ready, has unresolved high-threat papers, has incomplete required routes, has version/provenance conflicts, or conflicts with idea frontmatter cache, stop and list blockers. Do not formulate S3.
- If the sidecar is ready but `human_decision: pending`, stop and tell the user to run `/idea-s2-decide <slug> <OUTCOME>`.
- If the authoritative sidecar decision is `LOOP-S2`, `RETURN-S1`, `PARK-METHOD`, `PARK-PRIORITY`, or `STOP-DUPLICATE`, do not advance. Summarize the current outcome.
- If and only if the authoritative sidecar has a dated `human_decision: ADVANCE-S3`, the gate is current, and the cache is consistent, proceed:
- Check if `## S1.5: Socratic Refinement` section exists with insights — if yes, use as basis for RQ
- Formulate **exactly 1 main research question + max 3 sub-questions** + hypotheses + 1 ID strategy
- Include `Frontier Position`: what the question changes relative to named nearest papers
- Include `S2 Conditions Carried Forward`: unresolved data, identification, scope, or literature risks that S3/S4 must resolve
- Fill "Research Questions" section
- Set status=question, checkpoint_pending=true

**question → data-search:**
- Three-source dataset search; present **top 5 datasets only**:
  1. Claude's knowledge: known public datasets
  2. Do NOT fetch the raw awesome-public-datasets README (it is ~400 KB and degrades attention). Apply your knowledge of that list to surface relevant entries by topic.
  3. Economics-specific sources (IPUMS, BLS, Census, PSID, etc.)
- Fill "Datasets" table: name, source, URL, size, relevance (1-5), notes
- Set status=data-search, checkpoint_pending=true

**data-search → data-prep:**
- Download and clean the user-approved dataset(s) into `ideas/data/<slug>/`
- Document cleaning steps in the idea page
- Set status to `data-prep`

**data-prep → report:**
- Generate a preliminary analysis report at `ideas/reports/<slug>-report.md`
- Report should include: descriptive stats, key distributions, preliminary correlations, data quality notes, suggested next steps
- Set status to `report`, checkpoint_pending: false
- Tell user: "Report complete. Review [[slug-report]] and decide: proceed / archive."

### REVISE IDEA (`/idea-revise <slug>`)

1. Ask user: what needs to change?
2. Re-run the current stage with the user's feedback incorporated
3. Set checkpoint_pending: true again
4. If the revision substantively changes population, treatment/exposure, outcome, mechanism, claim type, or candidate contribution, invalidate the old S2 gate outcome and return to LOOP-S2. If it only adds search/readings, append to the existing Search Log instead of overwriting it.

### FULL S2 GATE (`/idea-s2-full <slug> start|resume|status|check`)

- `start`: create or schema-upgrade `ideas/reviews/<slug>-s2-gate.md`, set gate active at `pkb_context`, run PKB-A context recall, then stop for human Scope Card approval.
- `resume`: read the authoritative sidecar, handle dirty/cache/scope conflicts, resume at the first incomplete phase, and stop at any human decision point: scope approval, screening override, human reading, nearest-paper selection, or gate decision.
- `status`: read-only summary of phase/status, dirty/stale state, missing routes, open must-reads/high threats/version conflicts, latest search/synthesis dates, blockers, and next action.
- `check`: run the readiness linter. If all required checks pass, set only `ai_readiness: READY_FOR_HUMAN_DECISION`, `gate_status: ready_for_human_decision`, and `gate_phase: adjudication`. Do not write human-only fields.

### S2 GATE DECISION (`/idea-s2-decide <slug> <OUTCOME>`)

Allowed outcomes: `ADVANCE-S3`, `LOOP-S2`, `RETURN-S1`, `PARK-METHOD`, `PARK-PRIORITY`, `STOP-DUPLICATE`.

This command only records an explicit human outcome. For `ADVANCE-S3`, it must verify `ai_readiness: READY_FOR_HUMAN_DECISION`, clean/non-dirty sidecar, current scope hash, and no cache conflict. Other outcomes may be recorded before readiness if the human chooses to stop, loop, return, park, or stop as duplicate. The command updates authoritative sidecar frontmatter, appends Decision / Invalidation History, syncs idea cache/index/log, and never generates S3.

### STATUS CHECK (`/idea-status`)

1. Read `ideas/_frontmatter_cache.md` — do NOT open individual idea files
2. If cache is missing or stale, regenerate it by reading only the frontmatter blocks of each idea file and S2 sidecar frontmatter
3. Surface gate phase, AI readiness, human decision, dirty/stale flag, open must-read/high-threat count when available, freshness, and next action
4. If cache and sidecar disagree, show `CACHE-CONFLICT` and block advance
5. Output grouped table: Ready for Human Gate Decision → Waiting for Review → In Progress → Captured → Parked → Done → Archived

### ARCHIVE IDEA (`/idea-archive <slug>`)

1. Ask: reason for archiving?
2. Update status to `archived`, record reason in "Decision Log"
3. Update index and log

---

## Index Format (`ideas/index.md`)

```markdown
## Waiting for Review 🔴
- [[slug]] — title — Stage: explore — Priority: high

## Ready for Human Gate Decision
- [[slug]] — title — S2 Full Gate ready — Outcome: pending

## In Progress
- [[slug2]] — title — Stage: data-prep

## Parked
- [[slug3]] — title — Reason: PARK-METHOD / PARK-PRIORITY

## Done ✅
## Archived
```

---

## Log Format (`ideas/log.md`)

Append-only. Never edit existing entries. Add new entries at the bottom.

```
[IDEA-NEW YYYY-MM-DD] slug: <slug> → captured
[IDEA-NEW YYYY-MM-DD] slug: <slug> → created, auto-explored
[IDEA-NEXT YYYY-MM-DD] slug: <slug> → advanced: explore→question
[IDEA-REVISE YYYY-MM-DD] slug: <slug> → re-ran stage: question
[IDEA-ARCHIVE YYYY-MM-DD] slug: <slug> → reason: <reason>
[IDEA-SOCRATIC YYYY-MM-DD] slug: <slug> → N insights, mode: exploratory/goal-oriented
[IDEA-CHALLENGE YYYY-MM-DD] slug: <slug> → Lens A: ok/major/critical, Lens B: ok/major/critical, Lens C: highest severity
[IDEA-EXTRACT YYYY-MM-DD] source: <slug>.md → appended to: <idea-slug>
[IDEA-EXTRACT YYYY-MM-DD] source: <slug>.md → created: <new-slug>
[IDEA-S2-GATE YYYY-MM-DD] slug: <slug> → full review ready for human decision
[IDEA-GATE-DECISION YYYY-MM-DD] slug: <slug> → <OUTCOME>; reason: <short reason>
```

---

## Economics-Specific Dataset Sources

When doing S4 (data-search) for economics research, always check:

**Labor / Human Capital:**
- IPUMS CPS, APS (ipums.org) — occupation, wages, hours, education
- BLS Occupational Employment Statistics — wage distributions by occupation
- PSID (Panel Study of Income Dynamics) — longitudinal household
- O*NET — occupation task content, AI exposure measures
- Felten et al. AI exposure index — AI substitutability by occupation

**Academic Research / Science of Science:**
- OpenAlex (openalex.org) — 250M+ scholarly works, free API
- Semantic Scholar — papers, citations, author info
- Web of Science / Scopus — p-values, statistical significance in papers
- NBER Working Papers — economics preprints with metadata
- AEA RCT Registry — registered experiments

**Education / Students:**
- PISA, TIMSS — international student assessments
- IPEDS — US higher education data
- Common Core of Data — K-12

**General:**
- World Bank Open Data
- FRED (Federal Reserve Economic Data)
- OECD.Stat

---

## Zotero Integration

Zotero config path: read from `~/.claude/machine_paths.md` → "Research Idea Pipeline → Zotero config"
Read `api_key` and `user_id` from that config file. Idea collection keys are stored in `idea_collections` map.

**When adding a new idea**, create a new sub-collection via:
```
POST https://api.zotero.org/users/{user_id}/collections
[{"name": "<slug>", "parentCollection": false}]
```
Then save the new key to the config file under `idea_collections.<slug>`.

**Adding papers to Zotero:**
- `/idea-zotero-add <slug> <doi-or-url>` — add a single paper (user-triggered)
- Quick Scan does not automatically sync all results.
- After a Full S2 Gate, sync only included/core/nearest papers from the Evidence Table. Non-DOI working papers may be saved manually or by metadata lookup; excluded records stay in the Screening/Search Log.
- Use Unpaywall API to check OA status before attempting PDF attachment
- Mark papers in idea page: ✅ = in Zotero, ⬜ = needs manual download

**Paper item format for Zotero API:**
```json
{
  "itemType": "journalArticle",
  "title": "...",
  "creators": [{"creatorType": "author", "firstName": "...", "lastName": "..."}],
  "DOI": "...",
  "publicationTitle": "...",
  "volume": "...", "issue": "...", "pages": "...",
  "date": "YYYY",
  "collections": ["<collection_key>"]
}
```
