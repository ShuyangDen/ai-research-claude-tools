---
name: project-sync
description: "Use this skill when the user invokes $project-sync, /project-sync, asks to run project-sync, or asks to sync changes from a tracked research project. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# project-sync

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/project-sync.md","source_sha256":"5ca20b16972f74a26497bea51db3acce3dcd41ab6f7181b1a6ffb10cc1170856","workflow_version":"3.0.0"} -->

## Trigger Forms

- $project-sync
- /project-sync
- Natural language requests to sync changes from a tracked research project

## Codex Execution Rules

- Do **not** read `~/.claude/commands/project-sync.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

Scan a tracked project folder for file changes and update the project map and change log.

## Usage

`/project-sync <slug>`

Run periodically after making progress on a project.

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- Projects vault (under "Projects → Vault") → `<PROJECTS_VAULT>`
- Idea vault (under "Research Idea Pipeline → Vault") → `<IDEA_VAULT>`
- Paper tracker path (under "Paper Tracker → Path") → `<PAPER_TRACKER_PATH>`

---

## Step 1 — Load project state

1. Read `<PROJECTS_VAULT>\<slug>\index.md` — get `project-path`.
2. Read `<PROJECTS_VAULT>\<slug>\snapshot.json` — get last-known mtime for every file.

If `<slug>` folder does not exist: stop and tell user "Project not found. Run /project-init <slug> <path> first."

---

## Step 2 — Detect changed files

Run this Python command to get current mtimes for all files in `<project-path>`:

```bash
python -c "
import os, json, sys
root = r'<project-path>'
result = {}
skip_dirs = {'.git', '__pycache__', '.ipynb_checkpoints', 'node_modules', '.obsidian'}
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith('.')]
    for fname in filenames:
        if fname.startswith('.'): continue
        fpath = os.path.join(dirpath, fname)
        rel = os.path.relpath(fpath, root)
        try:
            result[rel] = os.path.getmtime(fpath)
        except: pass
print(json.dumps(result))
"
```

Compare each file's mtime to `snapshot.json`:
- **Changed/new**: current mtime > cached mtime, OR file not in cache
- **Deleted**: in cache but no longer exists on disk
- **Unchanged**: mtime matches — skip entirely

---

## Step 3 — Read and summarize changed files

For each changed/new file (skip binary files: .pdf, .png, .jpg, .xlsx, .docx, .zip):
- Read up to the first 80 lines
- Generate a one-line purpose description based on filename + content

For binary files: record that they exist and their size, but do not read contents.

If more than 20 files changed, process the 20 most recently modified and note the total count.

---

## Step 4 — Update map.md

Read `<PROJECTS_VAULT>\<slug>\map.md`.

For each changed/new file:
- If a row for this path already exists: update `purpose` and `last-changed`
- If it's a new file: add a new row

For deleted files: remove their rows.

Group by directory — files in the same folder appear together. Folders with more than 8 files are summarized as a folder row instead of per-file rows.

Write the updated file.

---

## Step 5 — Append to changes.md

Append to `<PROJECTS_VAULT>\<slug>\changes.md`:

```
[SYNC YYYY-MM-DD] changed: <comma-separated filenames> | <one-sentence AI summary of what changed>
```

Keep each entry to one line. If many files changed, summarize the theme ("revised 5 analysis scripts", "added 3 new data files").

---

## Step 6 — Update snapshot.json

Write the full current mtime dict (all files, not just changed ones) to `snapshot.json`.

---

## Step 7 — Update index files

1. Update `<PROJECTS_VAULT>\<slug>\index.md`:
   - Set `last-sync: <YYYY-MM-DD today>`
   - Set `Recent change: <YYYY-MM-DD> — <brief summary of this sync>`

2. Update `<PROJECTS_VAULT>\index.md`: find the row for `<slug>`, update `last-sync` column.

3. Append to `<PROJECTS_VAULT>\log.md`:
   `[PROJECT-SYNC <YYYY-MM-DD>] slug: <slug> → <N> files changed: <filenames>`

4. Update `<IDEA_VAULT>\researcher_profile.md` → `## Active Projects` section:
   - Read `<PROJECTS_VAULT>\index.md` (the full table)
   - Rewrite the section body as one line per active project:
     `**<slug>** (<status>): <title> — open issues: <N>, last sync: <date>`
   - Sync the updated researcher_profile.md to the paper tracker copy at
     `<PAPER_TRACKER_PATH>\researcher_profile.md`
   - Do NOT git push here (leave that to /update-researcher-profile)

---

## Step 8 — Report

Tell user (in Chinese):
- X files changed since last sync (list them with their one-line description)
- If 0 changes: "没有文件变动。"
- map.md updated
- Run `/project-status <slug>` to discuss the project
