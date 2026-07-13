# Codex Operating Notes

This vault is the JMP idea pipeline for an economics PhD student.

## Primary Rules

- Treat `CLAUDE.md` as the canonical pipeline specification.
- Machine-specific paths live in `~/.claude/machine_paths.md`; read that file before running any workflow that touches another vault.
- Do not advance an idea past a checkpoint without explicit user approval.
- Keep `ideas/log.md` append-only.
- A Full S2 Gate is a resumable literature-review workflow, not a single document-generation call.
- The Personal Knowledge Base Pass has two stages: context recall before human scope approval, then scope-constrained local evidence retrieval before external search.
- The local pass must record sources searched, exact actions/queries, hits, misses, unavailable paths, and a known-item recall check.
- AI must not set human read status, human verification, human gap status, a gate decision, or an S3 stage.
- An unread high-threat paper, incomplete required route, unresolved decisive provenance, stale scope, dirty gate, or cache conflict blocks READY FOR HUMAN DECISION and blocks S3.
- `/idea-next` is a transition guard. `/idea-s2-full` performs and resumes the Full Gate.
- `/paper-done` must mark linked active S2 gates dirty when newly verified evidence can change their synthesis or frontier position.
- The S2 gate sidecar is authoritative for gate state and human decision; idea frontmatter values are generated caches.
- Ordinary idea discussion uses `/idea-chat`: read the target and authoritative sidecar first, retrieve bounded claim cards, and stage a session delta before canonical writes.
- Retrieval and review workers are read-only. A single orchestrator/writer applies validated changes.

## Key Workflows

- `/idea-new`: capture a new idea by default; run the quick S2 scan only when explicitly requested.
- `/idea-next`: advance an idea one stage, respecting checkpoints.
- `/idea-s2-full`: start, resume, check, or inspect a Full S2 Literature Gate.
- `/idea-s2-decide`: record an explicit human S2 gate outcome.
- `/idea-socratic`: refine a raw idea through 5-layer Socratic dialogue.
- `/idea-chat`: bounded default conversation for clarification, literature, mechanism, identification, data, challenge, and decisions.
- `/idea-socratic`: optional Socratic mode of `/idea-chat`.
- `/idea-challenge`: stress-test an idea with 3-lens critical evaluation.
- `/idea-help`: show what is actionable right now.
- `/idea-status`: refresh the idea kanban.
- `/wiki-ingest`: ingest new source notes in the personal knowledge wiki.
- `/paper-done`: full post-session pipeline for a finished paper.

When using Codex, use the installed Codex skill with the same name. Do not read `~/.claude/commands/` as an alternate runtime source; the install manifest and source hash must identify the generated adapter version.

## Idea Extraction Contract

`/paper-done` includes idea extraction:

- First parse the source note's critical reflections, open questions, and idea-pipeline relevance sections.
- Then present a proposal table to the user.
- Do not write idea files until the user confirms.
- After confirmation, update idea pages, `ideas/index.md`, `ideas/log.md`, and the source note's `Idea Extraction Record`.

Quality bar: new ideas must name a specific causal mechanism or channel. Vague "AI affects X" framings should be skipped or sharpened before creation.
