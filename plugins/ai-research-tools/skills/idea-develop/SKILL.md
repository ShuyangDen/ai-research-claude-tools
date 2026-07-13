---
name: idea-develop
description: "Use this skill when the user invokes $idea-develop, /idea-develop, asks to run idea-develop, or asks to deep-dive on an idea with cross-system context. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-develop

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-develop.md","source_sha256":"aa86287cd7e68bc979675edb3eefc5f0e349c54d669455043c7a18ef60297127","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-develop
- /idea-develop
- Natural language requests to deep-dive on an idea with cross-system context

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-develop.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-develop

Compatibility alias for the bounded idea conversation workflow.

## Usage

`/idea-develop <slug>`

Run `/idea-chat <slug> auto` and follow `idea-chat.md` exactly. Do not use the retired index-first/full-note-loading workflow.

For an explicit request, map naturally:

- 文献综述 / nearest papers → `literature`
- 机制 → `mechanism`
- 识别 / empirical strategy → `identification`
- 数据 → `data`
- 批判 / stress test → `challenge`
- 要不要推进 / compare options → `decision`

Tell the user once that `/idea-chat` is the preferred name; otherwise keep the interaction identical.
