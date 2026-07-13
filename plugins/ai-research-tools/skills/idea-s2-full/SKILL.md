---
name: idea-s2-full
description: "Use this skill when the user invokes $idea-s2-full, /idea-s2-full, asks to start, resume, or check a Full S2 Literature Gate, or asks to run the stateful S2 literature-review workflow. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-s2-full

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-s2-full.md","source_sha256":"61139558c049792423acf16b0105870d91f94ed563a9c84ad3b461b1f48eb99c","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-s2-full
- /idea-s2-full
- Natural language requests to start, resume, inspect, or check a Full S2 Literature Gate

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-s2-full.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

You are managing a research idea pipeline for an economics PhD student.

Usage: `/idea-s2-full <slug> start|resume|status|check`

Step 0: Read `~/.claude/machine_paths.md`, then read the idea vault `CLAUDE.md` and `AGENTS.md`. All idea-vault paths below are relative to the vault root.

Purpose: perform or resume a Full S2 Literature Gate. This is a stateful literature-review workflow, not a one-shot document generation call. AI may prepare evidence and mark `READY_FOR_HUMAN_DECISION`; AI must never set human read status, human verification, human gap status, human decision, `ADVANCE-S3`, or `status: question`.

General rules:
- Do not bulk migrate old ideas or source notes.
- Do not overwrite S1 original text, human scope approval, human screening overrides, human verification, human decision/rationale, Search Log, or Decision / Invalidation History.
- The authoritative gate state is `ideas/reviews/<slug>-s2-gate.md` frontmatter. Idea frontmatter values are generated caches only.
- If sidecar and idea cache conflict, stop and report `CACHE-CONFLICT` before transition.
- If an existing gate is schema v1, lazily upgrade by preserving old sections and appending missing schema v2 sections; set `ai_readiness: NOT_READY` until check passes.

Actions:

`start`
1. Verify `ideas/<slug>.md` exists and status is `capture` or `explore`.
2. If sidecar missing, create `ideas/reviews/<slug>-s2-gate.md` from `ideas/_s2_gate_template.md`.
3. If sidecar exists, preserve all content and add missing schema/frontmatter fields only.
4. Set gate frontmatter: `gate_status: active`, `gate_phase: pkb_context`, `ai_readiness: NOT_READY`, `human_decision: pending`, unless protected human fields already exist.
5. Run PKB-A Context Recall from frozen S1 wording: machine paths, researcher profile, idea map/index, related ideas, parked/rejected/archived decisions, prior extraction records, source-note Critical Reflections/Open Questions/Idea-Pipeline Relevance/Idea Extraction Record.
6. Fill only generated PKB-A sections and Context Brief.
7. Stop at `scope_approval` and ask the human to approve one searchable Scope Card. Do not run external search and do not write S3.

`resume`
1. Read authoritative sidecar frontmatter and body.
2. Check dirty reasons, cache conflict, scope hash mismatch, stale/freshness flags, and missing schema sections.
3. Resume at the first incomplete phase.
4. PKB-B local evidence search can begin only after human Scope Card approval.
5. PKB-B must produce Local Retrieval Manifest, Known-Item Recall Test, Local Candidate Ledger, and `What External Search Must Clarify`.
6. If Known-Item Recall fails, stop and require query/path repair before external search.
7. External search must use the Search Protocol and `system/literature_sources.yml` where applicable. Record zero-result, paywall, unavailable, and incomplete routes.
8. Stop at human decision points: scope approval, screening override, human reading, nearest-paper selection, gate decision.
9. Rebuild generated synthesis sections from source-grounded claims and source notes; do not update by copying old AI summaries.

`status`
Read only. Report gate status/phase, dirty/stale state, scope version/hash, missing required routes, open must-reads/high threats/version conflicts, latest search/synthesis dates, current blockers, cache consistency, and next exact action.

`check`
Run the readiness linter against the Stopping and Readiness Certificate. Block readiness if any required item fails, including unread high-threat papers, abstract-only decisive claims, unresolved version conflicts, incomplete required routes, failed known-item recall, dirty gate, stale scope, or cache conflict. If all pass, set only `ai_readiness: READY_FOR_HUMAN_DECISION`, `gate_status: ready_for_human_decision`, and `gate_phase: adjudication`. Do not write human-only fields.
