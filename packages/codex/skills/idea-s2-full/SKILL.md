---
name: idea-s2-full
description: Use this skill when the user invokes $idea-s2-full, /idea-s2-full, asks to start/resume/check a Full S2 Literature Gate, or asks to run the stateful S2 literature review workflow. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-s2-full

## Trigger Forms
- $idea-s2-full
- /idea-s2-full
- Natural language requests matching this workflow

## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-s2-full.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making gated writes.

## Command Workflow
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
