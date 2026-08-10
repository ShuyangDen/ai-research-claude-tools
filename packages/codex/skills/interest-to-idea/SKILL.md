---
name: interest-to-idea
description: "Use this skill when the user invokes $interest-to-idea, /interest-to-idea, or asks to convert a current interest into a formal research idea. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# interest-to-idea

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/interest-to-idea.md","source_sha256":"ffba87df3d2ee4adb11ff50d98a62f34e56cd7ff4f27e8f4f59169502048025b","workflow_version":"3.3.0"} -->

## Trigger Forms

- $interest-to-idea
- /interest-to-idea
- Natural language requests to convert a current interest into a formal research idea

## Codex Execution Rules

- Do **not** read `~/.claude/commands/interest-to-idea.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

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
