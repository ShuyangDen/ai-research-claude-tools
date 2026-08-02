Convert a current-interest signal into a formal idea-pipeline entry.

## Usage

`/interest-to-idea <interest-slug-or-title>`

## Workflow

1. Read `researcher_profile.md`.
2. Locate the requested entry under `## Current Interest Signals`.
3. Review related context:
   - `## Active Research Directions`
   - `## Reading Preference Signals`
   - relevant source notes if explicitly named in the current-interest entry
4. Produce a conversion proposal:
   - Proposed title and slug
   - Research question
   - Mechanism
   - Literature gap
   - Related current ideas and overlap risk
   - Possible data or theory path
   - Main identification or feasibility concern
   - Proposed immutable `idea_origin`: use `human` when the current-interest core question/mechanism came from the user, `hybrid` when AI materially supplied it, and `ai_generated` only when the interest itself came from an AI proposal
5. Stop for user confirmation.
6. Only after confirmation:
   - Create `ideas/<slug>.md` from `ideas/_template.md`
   - Set `status: capture`
   - Fill `## Original Idea` with the refined current-interest content
   - Complete `## Origin & Provenance`; never default an AI-proposed current interest to human
   - Add a `## Source` section noting that it came from `Current Interest Signals`
   - Update `ideas/index.md`
   - Append to `ideas/log.md`

## Rules

- Never convert a current interest into a formal idea without explicit user confirmation.
- Never change an existing origin during conversion or later refinement.
- If the current interest lacks a mechanism, data/theory path, or literature gap, recommend more reading instead of creating an idea.
