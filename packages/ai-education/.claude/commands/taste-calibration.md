# /taste-calibration

Run a held-out monthly check of whether the current recommendation profile and
Researcher Pattern Card predict the researcher's paper or idea ranking.

## Protocol

1. Resolve `<AI_EDUCATION_PATH>`, `<PAPER_TRACKER_PATH>`, and `<IDEA_VAULT>` from machine paths.
2. Choose `papers` or `ideas`; report the two calibration histories separately.
3. For `papers`, select 8-10 recent eligible paper cards that were not used to create the
   current profile projection and have no recorded human triage decision.
4. For `ideas`, select 6-8 candidates from a frozen scout run that did not build
   the current Pattern Card. Do not create or advance those ideas.
5. Using only the frozen profile/Pattern Card, rank IDs and save the predicted
   array plus profile/style hashes before showing the cards to the researcher.
6. Ask the researcher for one ordered list, allowing ties only by expanding them
   into explicit pairwise indifference notes outside the metric input.
7. Run:

```powershell
python tutor\taste_calibration.py `
  --predicted '<JSON_ARRAY>' `
  --human '<JSON_ARRAY>' `
  --batch-id '<calibration-id>' `
  --profile-hash '<projection-hash>' `
  --item-type '<paper|idea>' `
  --log tutor\taste_calibration.jsonl
```

Report top-3 precision and pairwise agreement separately by item type. Do not claim that AI has learned
the researcher's taste from anecdotal agreement. Show the trailing three
calibrations when available. If agreement deteriorates, inspect topic,
mechanism, identification, data, and time-cost reason codes before changing the
profile. For idea calibration, inspect which axis failed: intrinsic taste,
mechanism, importance/novelty, identification, data feasibility,
time-to-signal/salvage value, or JMP/advisor fit.
