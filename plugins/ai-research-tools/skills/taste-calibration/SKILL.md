---
name: taste-calibration
description: "Use this skill when the user invokes $taste-calibration, /taste-calibration, asks whether AI has learned their research taste, wants to compare AI and human paper rankings, or wants a held-out monthly recommendation calibration."
---
# taste-calibration

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/ai-education/.claude/commands/taste-calibration.md","source_sha256":"a87e51cbb7a7d49a206516ccb00db4d23943a4529cd38c7ad8b90d7c03b8c631","workflow_version":"3.3.0"} -->

## Trigger Forms

- $taste-calibration
- /taste-calibration
- Natural language requests to evaluate how well the recommendation profile predicts the researcher's paper ranking

## Codex Execution Rules

- Do **not** read `~/.claude/commands/taste-calibration.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

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
