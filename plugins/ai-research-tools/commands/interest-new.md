Create a new current-interest signal through Socratic refinement.

## Usage

`/interest-new`

Use this for rough research questions that are not yet formal idea-pipeline entries.

## Workflow

1. Ask the user for the rough research question in their own words.
2. Run a focused Socratic pass before saving anything:
   - What is the unit of analysis?
   - What is the mechanism?
   - What is the supply-side margin?
   - What is the demand-side margin?
   - What would existing literature likely say?
   - What does the user think existing literature misses?
   - What evidence would make this idea wrong or less interesting?
3. Run a challenge pass:
   - Identify where the assistant may be over-agreeing with the user.
   - Name the strongest counterargument.
   - Check whether the interest is being prematurely framed as a formal research idea.
   - Check whether the mechanism is specific enough to guide paper recommendation.
4. Propose a current-interest entry using this structure:
   ```markdown
   1. **<title>** *(current-interest)*:
      - **Rough question**:
      - **Mechanism**:
      - **Unit / object**:
      - **Supply side**:
      - **Demand side**:
      - **Literature gap**:
      - **Uncertainty / counterpoint**:
   ```
5. Ask for confirmation before writing.
6. After confirmation, append the entry to `## Current Interest Signals` in `researcher_profile.md`.
7. Copy the updated profile to the paper tracker path if configured, but do not create a formal idea file.

## Rules

- Preserve the user's important conceptual distinctions. Do not compress away units, mechanisms, supply-side logic, or demand-side logic.
- A current interest is internal recommendation context, not a public report item.
- Do not include current-interest text in weekly public reports.
