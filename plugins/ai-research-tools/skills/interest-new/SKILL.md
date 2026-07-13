---
name: interest-new
description: "Use this skill when the user invokes $interest-new, /interest-new, or asks to add a rough current research interest through Socratic questioning before it becomes a formal idea. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# interest-new

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/interest-new.md","source_sha256":"6b0d17e71d23fa3cfb6c83d72fc2c3b981f48a36b371acebb16732e5d4351dba","workflow_version":"3.0.0"} -->

## Trigger Forms

- $interest-new
- /interest-new
- Natural language requests to capture and refine a rough current research interest

## Codex Execution Rules

- Do **not** read `~/.claude/commands/interest-new.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

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
