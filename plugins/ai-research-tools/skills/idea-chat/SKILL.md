---
name: idea-chat
description: "Use this skill when the user invokes $idea-chat, /idea-chat, or asks for a bounded, source-grounded conversation about one research idea. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-chat

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-chat.md","source_sha256":"6ecea1810250ab2e9e78589306bacfd51a756f6e936823bfb15290a2bf841d1a","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-chat
- /idea-chat
- Natural language requests to discuss one research idea with bounded, source-grounded context

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-chat.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /idea-chat

Develop one research idea with a bounded, source-grounded conversation. This is the default entry point for ordinary idea discussion; it uses one agent and deterministic local retrieval.

## Usage

`/idea-chat <slug> [auto|clarify|literature|mechanism|identification|data|challenge|decision]`

If no mode is supplied, infer it from the user's immediate request and state the inferred mode in one short line. Do not start S2/Challenge sub-agents in this workflow.

## Step 0 — Resolve paths

Read `~/.claude/machine_paths.md` as UTF-8 and resolve:

- `<TOOLS_ROOT>` from `AI Research Tools → Source root`
- `<AI_EDUCATION_PATH>` from `AI Education Project → Project root`
- `<IDEA_VAULT>` from `Research Idea Pipeline → Vault`
- `<WIKI_VAULT>` from `Personal Knowledge Wiki → Vault`

If `AI Research Tools → Source root` is missing, continue with the manual retrieval fallback below and tell the user once that deterministic retrieval is unavailable. Never guess a personal path.

## Step 1 — Read the target before searching

Read, in this order:

1. `<IDEA_VAULT>\ideas\<slug>.md`: frontmatter, Current Brief if present, Original Idea, current-stage section, and latest Decision Log entries.
2. `<IDEA_VAULT>\ideas\reviews\<slug>-s2-gate.md`, if present: frontmatter and Gate Brief/current synthesis only. This sidecar is authoritative for S2 state.
3. `<IDEA_VAULT>\ideas\sessions\<slug>-session.json`, if present.

Stop if the idea does not exist. If idea frontmatter conflicts with the S2 sidecar, report `STATE-CONFLICT`; use the sidecar for S2 facts and do not advance the idea.

Before retrieval, define internally:

- `objective`: the concrete question to answer this turn
- `mode`
- `scope_hash`: from the approved Scope Card when available, otherwise a hash of the current compact scope
- `decision_needed`: the one decision this conversation should clarify, if any

Open the response with no more than three short lines:

```text
本轮目标：...
当前边界：...
需要决定：...   # omit when no decision is needed
```

## Step 2 — Retrieve bounded evidence

Preferred path: invoke the repo-local runtime (no global install required):

```powershell
python "<TOOLS_ROOT>\scripts\research_core.py" idea-context <slug> --idea-vault "<IDEA_VAULT>" --pkb-vault "<WIKI_VAULT>" --mode <mode> --objective <objective> --max-packets 8 --max-full-sources 3 --write
```

Retrieval rules:

- Return at most 8 claim cards total.
- Load at most 3 full source notes and at most 1 related idea.
- Prefer, in order: current S2 Gate Brief/nearest-neighbor evidence, concept wiki assertions, paper source claims, then AI Education notes only when a requested detail is absent upstream.
- Include a useful mix when available: support, contradiction, nearest prior work, mechanism, method/identification, and data.
- Every card must include `claim_id`, `claim_type`, `source_path`, and `locator`. Allowed claim types are `reported_result`, `author_interpretation`, `researcher_reflection`, and `agent_inference`.
- Treat wiki pages as derived views. For consequential claims, follow their source link back to a paper source note.
- Do not load full paper text unless the user explicitly asks for a detail that cannot be answered from notes.

Manual fallback: search only after reading the target. Query `wiki/index.md`, concept pages, `sources/`, and related-idea metadata using the target mechanism, population/exposure/outcome, method, and objective. Apply the same caps. Never preload the full researcher profile or every relevant note.

## Step 3 — Answer compactly

Answer the user's question first. Do not narrate file-loading steps or recite the workflow.

Use this compact shape when the turn involves research judgment:

```markdown
**当前判断** — 2–3 sentences.

**最相关证据**
- Up to 3 claim cards with claim ID and source.

**最大冲突或不确定性** — one short paragraph, or “暂无关键冲突”.

**这会怎样改变 idea** — one proposed delta, or “本轮不需要改动”.

**下一步** — at most one question, only when an answer from the user is needed.
```

For a simple direct question, use an even shorter answer. Never refuse a direct answer merely to preserve a Socratic format. In `clarify` mode, ask one diagnostic question at a time only when it will change the answer.

Grounding rules:

- Separate paper findings, authors' interpretation, the researcher's reflection, and your inference.
- If a literature/contribution claim lacks a current source or gate evidence, label it `UNVERIFIED` instead of judging novelty from model memory.
- A normal chat may interpret an existing Full S2 Gate but cannot certify novelty, change human-only gate fields, or record `ADVANCE-S3`.
- Do not repeat the same evidence or background in consecutive turns unless the user asks.

## Step 4 — Persist only a working delta

After a substantive turn, atomically update `<IDEA_VAULT>\ideas\sessions\<slug>-session.json` through `python "<TOOLS_ROOT>\scripts\research_core.py" idea-session update ...`. Initialize it first with `idea-session init` when absent. Store only:

- mode, objective, and scope_hash
- agreed and contested points
- open questions
- claim IDs used
- one `candidate_delta`
- one `next_decision`

Do not copy long evidence passages into the session or idea page. Do not modify the canonical idea, index, profile, or S2 human fields during ordinary chat.

When the user explicitly confirms a proposed delta, merge only that delta into the relevant idea section, append one Decision Log entry, and clear the staged delta. If the accepted change alters an approved S2 scope axis, mark the gate dirty and require `/idea-s2-full <slug> resume`.
