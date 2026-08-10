# /taste-calibration

Run a held-out monthly check of whether the current recommendation profile
predicts the researcher's paper ranking.

## Protocol

1. Resolve `<AI_EDUCATION_PATH>` and `<PAPER_TRACKER_PATH>` from machine paths.
2. Select 8-10 recent eligible paper cards that were not used to create the
   current profile projection and have no recorded human triage decision.
3. Using only `recommendation_profile.json`, rank their paper IDs and freeze the
   predicted array before showing the cards to the researcher.
4. Ask the researcher for one ordered list, allowing ties only by expanding them
   into explicit pairwise indifference notes outside the metric input.
5. Run:

```powershell
python tutor\taste_calibration.py `
  --predicted '<JSON_ARRAY>' `
  --human '<JSON_ARRAY>' `
  --batch-id '<calibration-id>' `
  --profile-hash '<projection-hash>' `
  --log tutor\taste_calibration.jsonl
```

Report top-3 precision and pairwise agreement. Do not claim that AI has learned
the researcher's taste from anecdotal agreement. Show the trailing three
calibrations when available. If agreement deteriorates, inspect topic,
mechanism, identification, data, and time-cost reason codes before changing the
profile.
