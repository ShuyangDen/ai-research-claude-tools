---
name: sync-reading-queue
description: "Use this skill when the user invokes $sync-reading-queue, /sync-reading-queue, or asks to sync AI Education reading state with the paper tracker queue. This is the Codex adapter for the canonical AI Research Tools command."
---
# sync-reading-queue

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/ai-education/.claude/commands/sync-reading-queue.md","source_sha256":"6430def47f635cdf5a589f4f3274ad62dc3708c1634a7b5dc74d89fc98853fc0","workflow_version":"3.0.0"} -->

## Trigger Forms

- $sync-reading-queue
- /sync-reading-queue
- Natural language requests to synchronize the reading queue and terminal reading states

## Codex Execution Rules

- Do **not** read `~/.claude/commands/sync-reading-queue.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

# /sync-reading-queue

Sync local reading state with the paper tracker GitHub repo. The canonical file
is `queue_state.jsonl`; `reading_queue.md` is a generated compatibility view.

## What this command does

1. Fetch `queue_state.jsonl` and `reading_queue.md` from the tracker repo.
2. Load completed papers from `tutor/completed_papers.md`.
3. Load terminal full/selective/rough/skip events from
   `tutor/reading_feedback.jsonl` when present.
4. Deterministically merge canonical, legacy, and local-only rows with
   `papers/queue_sync.py`.
5. Persist terminal status in `papers/queue_state.jsonl`, regenerate local
   `papers/reading_queue.md`, and push both files (state first).

## Prerequisites

- `gh` CLI is installed and authenticated: `gh auth status`.
- `PAPER_TRACKER_REPO` is configured in `~/.claude/machine_paths.md`.
- The authenticated GitHub account has write access to that repo.

## Execution Protocol

### Step 1 - Read machine config

Read `~/.claude/machine_paths.md` and extract `PAPER_TRACKER_REPO`.
If missing, stop and tell the user to add `PAPER_TRACKER_REPO: <owner>/<repo>`.

### Step 2 - Fetch remote state/views and SHAs

Use the GitHub Contents API for both:
- `repos/<PAPER_TRACKER_REPO>/contents/queue_state.jsonl`
- `repos/<PAPER_TRACKER_REPO>/contents/reading_queue.md`

Decode each `.content` from base64 as UTF-8 into separate temporary files and
capture each `.sha`. A 404 state file is a supported one-time migration: create
an empty temporary state file and let the helper migrate the legacy Markdown.
A 404 for both files means an empty remote queue.

### Step 3 - Load local state

Read:
- `papers/reading_queue.md`
- `tutor/completed_papers.md`
- `tutor/reading_feedback.jsonl` (optional)

Do not edit or infer JSONL records manually. The helper reads completed slugs,
URLs when present, and feedback terminal states.

### Step 4 - Deterministic merge

Run from the AI Education project root:

```powershell
python papers\queue_sync.py `
  --state <downloaded-state-temp> `
  --remote-markdown <downloaded-markdown-temp> `
  --local-markdown papers\reading_queue.md `
  --completed tutor\completed_papers.md `
  --feedback tutor\reading_feedback.jsonl `
  --output-state papers\queue_state.jsonl `
  --output-markdown papers\reading_queue.md
```

The helper preserves tracker metadata (`paper_id`, lane, matched signal, score),
keeps local-only manual entries, deduplicates by stable ID/URL/title/slug, marks
full/selective/rough reads `completed`, marks skipped reads `skipped`, and hides
terminal records only from the Markdown view. An empty active view is valid when
all records have a documented terminal state; canonical history must remain.

### Step 5 - Write local queue

The helper writes `papers/reading_queue.md` with this canonical header:

```markdown
# Reading Queue

Derived compatibility view. Canonical state: `queue_state.jsonl`.

Tier 1 = priority read. Tier 2 = adjacent/general fit. Tier 3 = methodology.

| candidate-slug | title | tier | authors | venue | url | added |
|----------------|-------|------|---------|-------|-----|-------|
```

Never hand-edit the generated header or reconstruct state from Markdown when a
valid canonical state file exists.

### Step 6 - Push canonical state, then derived view

Upload `papers/queue_state.jsonl` first, using its captured SHA when it existed.
Only after that succeeds, upload `papers/reading_queue.md` using its own SHA.
Skip a PUT when content is unchanged. On Windows, avoid shell heredocs and BOM
issues; for each file use a temp JSON body written as UTF-8 without BOM:

```powershell
$newContent = Get-Content -LiteralPath $localPath -Raw -Encoding utf8
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($newContent))
$payload = @{ message = "sync canonical reading queue - $(Get-Date -Format 'yyyy-MM-dd')"; content = $encoded }
if ($sha) { $payload.sha = $sha }
$body = $payload | ConvertTo-Json -Compress
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tmp, $body, $utf8NoBom)
gh api "repos/$repo/contents/$remotePath" --method PUT --input $tmp
```

### Step 7 - Report

Report in Chinese:
- new rows added by tier
- rows newly marked completed/skipped
- current queue counts by tier
- canonical-state and Markdown commit SHAs, if pushed

## Error handling

- If `gh auth status` fails, tell the user to run `gh auth login`.
- If GitHub returns 403, the token lacks write access.
- If either remote file changed between fetch and PUT, refetch both, rerun the
  helper, and retry once.
- If canonical-state upload fails, do not upload Markdown.
- If state succeeds but Markdown fails, report a degraded sync; do not roll back
  state. The next tracker run can regenerate the view safely.
- Never delete canonical records. Terminal records change status and disappear
  only from the derived active view.
