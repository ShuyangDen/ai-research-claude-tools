# /sync-reading-queue

Sync the local `papers/reading_queue.md` with the paper tracker repo on GitHub.

## What this command does

1. **Fetch** the latest `reading_queue.md` from the paper tracker GitHub repo
2. **Load** completed papers from `tutor/completed_papers.md`
3. **Merge**: add new papers not yet in the local queue; remove papers already completed
4. **Write** the updated queue back to `papers/reading_queue.md` (Tier 1 first, then Tier 2)
5. **Push** the merged queue back to the paper tracker repo so the other machine stays in sync

---

## Prerequisites

Before running this command, verify:

- `gh` CLI is installed and authenticated: `gh auth status`
- `PAPER_TRACKER_REPO` is configured in `~/.claude/machine_paths.md` (e.g. `yourname/ai-economics-paper-tracker`)
- The authenticated GitHub account has write access to that repo

Read `~/.claude/machine_paths.md` now to find the `PAPER_TRACKER_REPO` value.

---

## Execution Protocol

### Step 1 — Read machine config

Read `~/.claude/machine_paths.md`. Extract the value for `PAPER_TRACKER_REPO`.
If not found, stop and tell the user: "Please add `PAPER_TRACKER_REPO: <owner>/<repo>` to `~/.claude/machine_paths.md` and run again."

### Step 2 — Fetch remote reading_queue.md

Run:
```
gh api repos/<PAPER_TRACKER_REPO>/contents/reading_queue.md --jq '.content' | base64 -d > /tmp/remote_reading_queue.md
```

On Windows (PowerShell):
```powershell
$content = gh api repos/<PAPER_TRACKER_REPO>/contents/reading_queue.md --jq '.content'
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($content)) | Out-File -Encoding utf8 /tmp/remote_reading_queue.md
```

Also capture the file's SHA (needed for the push):
```
gh api repos/<PAPER_TRACKER_REPO>/contents/reading_queue.md --jq '.sha'
```

If the file does not exist yet (404), treat remote as empty (no rows).

### Step 3 — Load local state

Read:
- `papers/reading_queue.md` — local queue (may have user annotations or manual entries)
- `tutor/completed_papers.md` — slugs and URLs of papers already studied

Build a set of **completed URLs** and **completed slugs** from `tutor/completed_papers.md`.

### Step 4 — Merge

Parse all table rows from both the remote queue and the local queue.
A row looks like:
```
| candidate-slug | title | tier | authors | venue | url | added |
```

**Merge rules:**
- Use the **url** column as the unique key for deduplication
- **Remove** any row whose url appears in the completed set
- **Add** rows from remote that are not already in local (by url)
- **Keep** any rows that exist only in local (manual entries the user added)
- **Sort** final list: Tier 1 rows first (sorted by `added` date descending), then Tier 2 (same sort)

### Step 5 — Write local queue

Overwrite `papers/reading_queue.md` with the merged result using this exact header:

```markdown
# Reading Queue

Papers suggested by the paper tracker for potential study sessions.

Tier 1 = priority read (directly targets active research directions).
Tier 2 = for reference (rigorous AI + labor/education, scan abstract).

| candidate-slug | title | tier | authors | venue | url | added |
|----------------|-------|------|---------|-------|-----|-------|
```

Then append all merged rows (Tier 1 first, then Tier 2).

### Step 6 — Push merged queue back to GitHub

Encode the new file content as base64 and PUT it back:

```powershell
$newContent = Get-Content papers/reading_queue.md -Raw -Encoding utf8
$encoded = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($newContent))
$sha = "<SHA from Step 2>"
$body = @{ message = "sync reading queue - $(Get-Date -Format 'yyyy-MM-dd')"; content = $encoded; sha = $sha } | ConvertTo-Json
gh api repos/<PAPER_TRACKER_REPO>/contents/reading_queue.md --method PUT --input - <<< $body
```

Or use gh's native flag:
```
gh api repos/<PAPER_TRACKER_REPO>/contents/reading_queue.md \
  --method PUT \
  -f message="sync reading queue - $(date +%Y-%m-%d)" \
  -f content="$(base64 -w0 papers/reading_queue.md)" \
  -f sha="<SHA>"
```

On Windows, use PowerShell with `Invoke-RestMethod` or `gh api --input -` with a temp JSON file.

### Step 7 — Report to user

Print a summary in Chinese:
```
同步完成。
- 新增论文：N 篇（T1: X 篇，T2: Y 篇）
- 移除已完成：M 篇
- 当前清单：P 篇（T1: Q 篇待读，T2: R 篇待读）
```

---

## Error handling

- If `gh auth status` fails → tell user to run `gh auth login` first
- If the repo returns 403 → token lacks write access; instruct user to add `repo` scope
- If merge produces 0 rows → warn the user before writing (do not silently clear the queue)
- Never delete local-only rows (manual entries) even if they don't exist in the remote
