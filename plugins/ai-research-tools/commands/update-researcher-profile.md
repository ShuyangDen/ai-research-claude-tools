# /update-researcher-profile

Project approved idea state and confirmed reading feedback into a compact, versioned recommendation profile, then sync the validated local copy to Paper Tracker.

## Paths

Read `~/.claude/machine_paths.md` as UTF-8 and resolve:

- `<TOOLS_ROOT>` from `AI Research Tools → Source root`
- `<IDEA_VAULT>` from `Research Idea Pipeline → Vault`
- `<AI_EDUCATION_PATH>` from `AI Education Project → Project root`
- `<PAPER_TRACKER_PATH>` from `Paper Tracker → Project root`

Inputs:

- `<IDEA_VAULT>\researcher_profile.md`
- `<IDEA_VAULT>\ideas\*.md` plus authoritative S2 sidecars
- `<IDEA_VAULT>\ideas\_profile_cache.json`
- `<AI_EDUCATION_PATH>\tutor\reading_feedback.jsonl`

Outputs:

- `<IDEA_VAULT>\recommendation_profile.json`
- `<IDEA_VAULT>\researcher_profile.md`
- `<PAPER_TRACKER_PATH>\recommendation_profile.json`
- `<PAPER_TRACKER_PATH>\researcher_profile.md`

Use `python "<TOOLS_ROOT>\scripts\research_core.py" profile-project ...` plus atomic UTF-8 writes. Never synthesize the profile by sending the full personal history once per paper.

## Change detection

Cache SHA-256 content hashes, schema version, and extracted fields; do not rely on `mtime` ordering. For every idea cache:

- title, status, priority, Current Brief objective/scope/next decision
- compact mechanism/estimand from the current approved state
- S2 scope hash, human outcome, nearest-paper/wedge summary, and dirty state
- accepted Evidence-from-Readings claim IDs
- archived/parked reason

Also hash reading feedback and human-maintained profile sections. Reproject when any relevant hash changes, including new evidence, S3 narrowing, S2 state, preference feedback, negative evidence, or interest conversion. A title/status unchanged check is not sufficient.

## Signal model

Keep five distinct classes; do not collapse them into generic prose:

1. `declared`: manually maintained long-run interests and hard constraints. Preserve verbatim unless the user edits them.
2. `portfolio`: approved active ideas with current scope and stage.
3. `speculative`: capture/explore hypotheses; lower weight and never equivalent to an approved direction.
4. `inferred`: confirmed reading feedback with provenance, confidence, and time decay.
5. `negative`: low-fit readings, abandoned directions, contradictions, and archived failure modes.

Deduplicate a Current Interest after it becomes a formal idea. Preserve the provenance link rather than counting it twice. Never infer a durable preference from one ambiguous interaction.

For each machine-readable signal store:

```json
{
  "schema_version": "1.0",
  "signal_id": "...",
  "signal_type": "declared|portfolio|speculative|inferred|negative",
  "status": "active|paused|archived",
  "title": "...",
  "mechanism": "...",
  "retrieval_terms": [],
  "confidence": 0.0,
  "priority": "low|medium|high",
  "source_refs": [],
  "human_approved": false,
  "observed_at": "...",
  "updated_at": "...",
  "expires_at": null
}
```

The projector adds `projection_score` and `tier_1_eligible`. Only human-approved `declared` and `portfolio` signals may enter Tier 1. Every projected signal must validate against the versioned `profile-signal` contract before publication.

## Recommendation lanes

The JSON projection declares `recommendation_lane_weights` with a diversified default allocation:

- 55% portfolio fit
- 20% adjacent mechanisms/data/domains
- 15% contradiction/null/adversarial evidence
- 10% methodology watch

These map to Tracker's `exploit`, `adjacent`, `contradiction`, and `methodology` lanes. An explicit `PAPER_TRACKER_LANE_MIX` environment setting may override them, but the actual allocation used must be recorded. `retrieval_terms` extend candidate retrieval; signals must not be used only after a hard-coded search.

## Rendered Markdown

Preserve manually maintained sections verbatim, especially Core Research Focus, Natural Thinking Patterns, Current Interest Signals, and explicit exclusions. Rebuild only marked generated sections:

- Active Research Directions — approved/active portfolio first; speculative ideas clearly labeled
- Reading Preference Signals — durable, aggregate patterns from confirmed feedback; include useful rough reads and low-fit patterns
- Current Interest Conversion Candidates — proposals only, never automatic idea creation
- Negative Evidence / Abandoned Directions
- Recurring Failure Modes
- Recommendation Retrieval Terms and Exploration Budget

Do not copy private feedback rows, private idea text, or rationales into public paper reports. Tracker receives compact signal IDs/terms, not the full profile text per candidate.

## Validate and sync

Before replacing outputs, validate schemas, signal IDs, projection scores, provenance, duplicate conversion, and UTF-8. `recommendation_profile.json` is the projector's structured five-lane output; Paper Tracker consumes that lane shape directly and derives its compact prompt without a second hand-maintained schema. Stage all four outputs; replace the local files only when validation passes. If tracker copies diverged due a concurrent personal edit, stop with a three-way diff instead of overwriting.

Emit `profile.snapshot.published` with input/output hashes. Do not silently commit or push git remotes; report the local sync and whether a remote update remains.

## Report

Show changed input classes, active/speculative/negative counts, feedback records incorporated, signals added/expired/deduplicated, output hashes, local tracker sync, and any blocker. Keep personal signal text out of logs unless the user asks to inspect it.
