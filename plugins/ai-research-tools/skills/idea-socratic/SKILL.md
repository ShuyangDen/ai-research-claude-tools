---
name: idea-socratic
description: "Use this skill when the user invokes $idea-socratic, /idea-socratic, or asks to refine a research idea through Socratic dialogue. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-socratic

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-socratic.md","source_sha256":"c48aa4d3520bc7c26104ba356ec6808d29ad3ba72f7adca7cdd185355e0bb2b6","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-socratic
- /idea-socratic
- Natural language requests to refine an idea through Socratic dialogue

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-socratic.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-socratic

Optional Socratic mode for `/idea-chat`; use it when the user wants to discover or sharpen their own reasoning, not as the default way to answer every idea question.

## Usage

`/idea-socratic <slug>`

Run `/idea-chat <slug> clarify` with these additions:

- Start from the target idea, authoritative S2 sidecar, and current session; do not start from the whole profile.
- Ask at most one question per turn and keep the response under 180 Chinese characters unless the user asks for an explanation.
- Answer direct questions directly. A concise answer may be followed by one diagnostic question.
- Tag a genuinely new, specific statement as `[INSIGHT: ...]`; do not tag paraphrases or generic preferences.
- Choose the next useful dimension from problem, mechanism, falsification, identification, evidence/data, and contribution. Do not force all dimensions or a minimum number of exchanges.
- Do not push causal methods before the estimand and mechanism are clear.
- Do not hint at literature from memory. Use retrieved claim cards or label the point `UNVERIFIED`.
- End when the user asks, a concrete decision is reached, or further questioning has low information value.

At a natural stopping point, stage a compact candidate delta in the idea session:

```markdown
### Socratic delta
- Question or estimand clarified:
- Mechanism clarified:
- Evidence that would change the belief:
- Main unresolved issue:
```

Merge it into `## S1.5: Socratic Refinement` only after explicit confirmation. If it changes an approved S2 scope axis, mark the gate dirty; never change a human gate decision.
