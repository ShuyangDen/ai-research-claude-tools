---
name: idea-scout
description: "Use this skill when the user invokes $idea-scout or /idea-scout, asks what recent Top-5 or ranked field economics papers are studying, wants labor/education/econometrics/meta-analysis hotspots, wants personalized research ideas from this week's reading, or asks AI to generate source-grounded research ideas in the researcher's style. It uses provenance-aware reasoning memory, separates attention from crowding and taste from feasibility, stages candidates, and waits for confirmation before creating ideas."
---
# idea-scout

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-scout.md","source_sha256":"c0fe1ff5c969f50440582f1dd74f0f13ab586ae55c71b6d7e74758f41d328176","workflow_version":"3.4.0"} -->

## Trigger Forms

- $idea-scout
- /idea-scout
- Natural language requests to scan recent economics research and generate personalized, source-grounded idea candidates

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-scout.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-scout [scope|weekly]

Find current economics research clusters and propose personalized, source-grounded research ideas without silently turning AI output into the researcher's own preferences.

Use this workflow when the user asks to scan recent Top-5 or field-journal work, identify current labor/education/metascience topics, broaden beyond AI, or generate new ideas in the researcher's style. For a literature review of one existing idea, use `/idea-chat` or `/idea-s2-full`; for paper recommendations without idea generation, use the Paper Tracker.

## Step 0: Paths and boundaries

Read `~/.claude/machine_paths.md`, then the idea-vault `CLAUDE.md` and `AGENTS.md`.

Resolve `<TOOLS_ROOT>`, `<IDEA_VAULT>`, `<PKB_VAULT>`, and `<PAPER_TRACKER_PATH>` from the machine config. This is an on-demand workflow. Do not create an automation or change the weekly AI digest. Retrieval/review workers are read-only; one orchestrator writes staged scout artifacts and confirmed ideas.

## Step 1: Fix scope and windows

Default substantive scope: labor economics and economics of education, with econometrics and meta-analysis/evidence synthesis as secondary expansion lanes. Use a default topical budget of roughly 35% labor, 35% education, 15% econometrics, and 15% meta-analysis; economics metascience remains available when explicitly requested or strongly matched. Default windows:

- journals and online-first articles: most recent 24 months;
- working-paper frontier: most recent 12 months.

Use the deterministic source plan:

```text
python "<TOOLS_ROOT>\packages\paper-tracker\idea_scout.py" source-plan --scope labor --scope education
```

Use the approved `labor_education_default` source profile. Allocate roughly 80% of retrieval effort to official Top-5 economics journals, leading labor and education journals, NBER, and IZA. Use AEJ Applied/Policy, ReStat, Journal of Public Economics, and CEPR as strong secondary routes. Long-tail repositories and discovery indexes receive at most 20% of the retrieval budget. Public AEA RCT/OSF registry routes activate only when metascience is in scope. Record every attempted route, exact public query, retrieval date, hit count, zero result, and unavailable route.

Read `system/economics_journal_catalogs.yml`. It records the public Tianjin University Ma Yinchu and SUFE economics journal tiers, their catalog/retrieval dates, normalized weights, field tags, and the latest abstract-access audit. Treat these tiers as transparent retrieval and research-attention priors, not as paper-level quality or novelty judgments. Journals elsewhere in either public catalog may be added on demand only after recording their catalog tier and passing the same abstract-access probe.

Before activating a journal, require a fresh `verified_primary`, `verified_fallback`, or `verified_version_abstract` route that exposed an actual recent abstract. A successful connection, table of contents, title, or metadata-only response is insufficient. Use official publisher/Crossref routes first; a working-paper version, RePEc/institutional mirror, Semantic Scholar, or OpenAlex may bridge abstract access only after DOI/ISSN/canonical-venue verification and explicit version provenance. If no route exposes an abstract, mark the journal blocked rather than inferring findings from titles.

## Step 2: Build or verify the Researcher Pattern Card

Personalize locally from provenance-separated evidence:

1. manually declared research interests and constraints;
2. human/hybrid ideas;
3. AI-generated ideas only after an authoritative `ADVANCE-S3` S2 decision;
4. confirmed reading feedback, archive/HOLD reasons, and negative preferences;
5. recurring preferences about mechanisms, dynamic outcomes, identification, data access, and pilots.

Also read the private memory summary built from
`ideas/memory/reasoning-events.jsonl` and `idea-feedback.jsonl`. Keep four
objects separate during ranking:

1. intrinsic researcher taste;
2. scientific importance/novelty;
3. empirical feasibility, time to first signal, and salvage value;
4. JMP/advisor fit.

Direct human-confirmed reasoning may inform taste. Researcher-reported advisor
outcomes inform feasibility and portfolio constraints but cannot overwrite
intrinsic taste. Unknown reasons remain unknown.

Source-authored idea patterns that the researcher explicitly endorsed during
paper reading are attributed exemplars. Reuse the abstract question-forming
move, not the paper's topic, result, or originality claim. Keep the author's
move, the researcher's reason for liking it, the transferable element, and the
transfer boundary visible in local ranking provenance.

If `ideas/scouting/researcher-pattern-card.md` is missing or not human-approved, present a compact draft and stop for approval before using it to rank candidates. Do not infer approval from silence. Preserve a SHA-256 `style_hash` for each run.

Every scout response, including a first-use response that stops at Pattern Card approval, must state the profile quarantine rule explicitly: an `ai_generated` candidate or idea contributes zero researcher-profile interest/retrieval signal until the authoritative S2 sidecar records the human outcome `ADVANCE-S3`; its origin label remains AI-generated afterward.

The full Pattern Card and private profile prose stay local. External search tools receive only public topic/venue/method terms. Never place local paths, email addresses, profile text, idea prose, or private signal text in external queries.

## Step 3: Retrieve and normalize evidence

Search current public sources. Prefer primary/official journal, working-paper, registry, DOI, and author pages. Merge exact DOI/stable-ID/explicit version relations automatically; fuzzy working-paper/journal matches require a relationship note rather than silent merge.

Source quality is attached to the verified canonical venue, not the discovery service:

- OpenAlex is a discovery/metadata index only. An OpenAlex-discovered QJE or JOLE paper inherits the verified journal tier; an unverified OpenAlex record supplies no quality or source-breadth credit.
- arXiv, SSRN/RePEc, and unverified author manuscripts are supplemental. They may reveal an emerging lead, but they cannot establish a hotspot and cannot support a candidate without curated economics anchors.
- Across candidate nearest-paper links, at least 70% must come from the primary/secondary economics routes, and each candidate must have at least 50% curated-source support. Report the achieved source mix in the manifest and report.
- Attach the harmonized journal-rank weight and catalog provenance to journal evidence. NBER/CEPR/IZA receive explicit frontier-working-paper priors, not journal-tier labels.

For each paper record:

- title, authors, date, venue/status, public URL;
- DOI/OpenAlex/NBER/arXiv identity when available;
- source family and candidate cluster;
- evidence level: `title_only`, `metadata`, `abstract`, or `targeted_full_text`;
- a bounded abstract-supported statement, not an inferred result from the title.

Use `packages/paper-tracker/scout_core.py` to validate queries, normalize paper IDs, deduplicate records, audit the candidate source mix, and classify clusters. A cluster is a `hotspot` only with at least 3 recent eligible papers, source/venue breadth of at least 2, and tier/evidence-weighted attention of at least 1.6. Discovery-only records do not count toward this threshold unless their canonical economics venue is verified. Otherwise call it an `emerging signal`. Missing core sources block a strong hotspot claim but do not erase the run; report degraded coverage.

Do not equate attention with attractiveness. Report at least two axes: `tier_weighted_attention` and `crowding_risk`. Use the strongest two to three high-ranked signals for frontier strength so publication volume cannot raise the score without bound. A dense cluster may be difficult to enter; candidate opportunity still requires semantic nearest-neighbor review, a credible identification/data path, and a mechanism-specific wedge.

## Step 4: Generate and screen candidates

Generate 6 candidates by default, never more than 8. At least half must be non-AI topics, and no cluster may supply more than 2 candidates.

For `weekly` mode, seed generation from the current digest/queue, completed or
rough-read notes, and this week's cluster syntheses. Generate 3-4 candidates
instead of six, then use recent frontier sources only to test and sharpen the
nearest-neighbor position. Weekly mode must not rerun or email the paper digest.

Every candidate needs:

- an explicit causal mechanism or behavioral channel;
- unit/population, exposure/treatment, outcomes, and a falsifiable comparison;
- 2-5 nearest paper IDs from this run;
- a plausible data and identification path;
- why the question is timely;
- overlap with active, parked, archived, and sibling ideas;
- crowding risk and why the proposal may still be enterable despite the nearest literature;
- the largest feasibility or identification risk;
- estimated time to first informative signal and the cheapest test that could
  kill the candidate;
- the reusable artifact or knowledge that survives a null/failed pilot;
- a compact observable-fit explanation naming the triggering evidence,
  `thinking_moves`, and matched Pattern Card IDs; this is not hidden
  chain-of-thought;
- `idea_origin: ai_generated`.

Render these as explicit candidate-level fields. In particular, every row/card must contain separate `Why now` and `Overlap` entries; cluster-level prose, a nearest-paper list, or a risk note does not substitute for either field. Before presenting the table, run a completeness check and reject or repair any candidate missing one of the required fields.

Reject generic “X affects Y,” descriptive keyword-counting without an estimand, unobservable outcomes without a measurement plan, and any assertion that an opening is already established as new. Score source evidence separately from subjective researcher fit, and never reward raw paper count as candidate opportunity.

## Step 5: Stage an auditable run

Write only scout staging artifacts under:

```text
<IDEA_VAULT>\ideas\scouting\runs\<run_id>\manifest.json
<IDEA_VAULT>\ideas\scouting\runs\<run_id>\report.md
```

The manifest stores scope, windows, public queries, source health, source policy, catalog/rank provenance, abstract-access status, achieved candidate source mix, tier-weighted attention, crowding risk, stable paper records, cluster labels, candidate records, `style_hash`, the recommendation-profile hash, a bounded list of reasoning-event IDs used, the frozen AI ranking, and `manifest_hash`; it must not store Pattern Card text or raw private rationale. Materialize it with:

```text
python "<TOOLS_ROOT>\packages\paper-tracker\idea_scout.py" materialize <manifest-input.json> --state-root "<IDEA_VAULT>\ideas\scouting"
```

Present a proposal table with candidate ID, origin, mechanism, nearest papers, data/ID path, overlap, and largest risk. Do not create or edit `ideas/<slug>.md`, `ideas/index.md`, or `ideas/log.md` yet.

## Step 6: Human selection and handoff

Wait for the user to select candidate IDs and choose either `capture only` or `capture + Quick Scan`.

Before showing the candidates, freeze the AI ranking and profile/style hashes.
After review, record one `/record-research-reasoning` idea-feedback event per
candidate, keeping intrinsic interest, mechanism, importance, novelty,
identification, data feasibility, time to signal, salvage value, JMP fit, and
advisor fit separate. Record modifications as before/after candidate deltas.
Do not infer a missing rejection rationale.

After explicit selection, invoke `/idea-new` with:

```yaml
idea_origin: ai_generated
origin_run_id: <run_id>
origin_candidate_id: <candidate_id>
```

Preserve the AI-authored seed wording and state visibly that the user approved exploration but did not originate the proposal. The origin is immutable. Append the confirmed creation event to `ideas/log.md`.

For Quick Scan, enforce the existing hard caps: at most 5 papers and at most 3 candidate openings/tensions. Set `status: explore`, `checkpoint_pending: true`, `s2_review: quick`, and `s2_gate_outcome: pending`; do not write S3, `ADVANCE-S3`, or certify an opening as a demonstrated contribution. Stop at the human checkpoint.

## Output

Return source and abstract-access coverage, degraded/blocked routes, a tier-weighted attention plus crowding table, the candidate proposal table, overlap warnings, the staged run path, and the exact next human decision.
