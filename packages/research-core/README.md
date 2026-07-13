# Research Workflow Core

`research-core` is the deterministic control layer for the three-part research
workflow. It deliberately does **not** contain an autonomous research agent. It
provides contracts, durable run state, deterministic context retrieval, and
diagnostics that Claude/Codex skills can call.

The package never stores personal data in this repository. Runtime manifests,
events, and idea-session sidecars are written to paths selected by the user.

## Main commands

```powershell
# Resolve the Markdown machine config into a typed JSON model
research-core paths show --machine-paths "$HOME\.claude\machine_paths.md"

# Create and inspect durable workflow runs
research-core run start --state-root D:\private-workflow-state --workflow paper-done `
  --step validate_note --step propose_idea_delta --step apply_confirmed_delta
research-core run status --state-root D:\private-workflow-state <run-id>
research-core run step-start --state-root D:\private-workflow-state <run-id> validate_note
research-core run step-complete --state-root D:\private-workflow-state <run-id> export
research-core run step-wait --state-root D:\private-workflow-state <run-id> propose_idea_delta `
  --reason "confirm candidate actions" --details candidates.json
research-core run step-fail --state-root D:\private-workflow-state <run-id> ingest --error "..."
research-core run resume --state-root D:\private-workflow-state <run-id>

# Maintain a compact, non-canonical idea conversation sidecar
research-core idea-session init demo --idea-vault D:\Obsidian\...\JMP-Idea `
  --mode literature --objective "Clarify the nearest literature"
research-core idea-session update demo --idea-vault D:\Obsidian\...\JMP-Idea `
  --field 'open_questions=["What evidence would reverse the claim?"]'

# Build a bounded, provenance-bearing context manifest. This never edits the idea.
research-core idea-context demo --idea-vault D:\...\JMP-Idea `
  --pkb-vault D:\...\personal-knowledge --mode literature `
  --objective "Find the closest contradictory evidence" --max-packets 8 --write

# Check paths, encoding, placeholders, and an optional install hash manifest
research-core doctor --machine-paths "$HOME\.claude\machine_paths.md" `
  --scan-root "$HOME\.codex\skills" --install-manifest install-manifest.json

# Read-only S2 readiness check; mutation is opt-in and AI-owned fields only
research-core s2-check D:\...\ideas\reviews\demo-s2-gate.md
research-core s2-check D:\...\ideas\reviews\demo-s2-gate.md --apply-ready
```

## Runtime state layout

```text
<state-root>/
  events/events.jsonl
  runs/<run-id>/manifest.json
```

Writes use UTF-8 without a BOM, a same-directory temporary file, `fsync`, and
`os.replace`. A per-file lock prevents two local writers from replacing the same
aggregate concurrently.

## Architectural boundary

- The orchestrator owns run receipts, not research conclusions.
- A paper tracker owns discovery/ranking; a tutor owns reading sessions; the
  PKB/idea system owns knowledge and idea state.
- Research sub-agents may be recorded through `actor` and `scope_hash`, but this
  package does not spawn them.
- `doctor` understands both portable `files` manifests, local-sync
  `artifacts` with `destination`, and repository `path`/`sha256` artifacts.
- `idea-context` reads in this order: target idea, authoritative S2 gate, latest
  session sidecar, explicit objective/mode, PKB index/pages/sources, related ideas.
  It never reads `researcher_profile.md` to guess the target.
