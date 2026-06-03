---
name: project-init
description: Use this skill when the user invokes $project-init, /project-init, asks to run project-init, or asks to initialize tracking for a research project. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# project-init
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Projects Vault.
## Trigger Forms
- $project-init
- /project-init
- Natural language requests to initialize tracking for a research project
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\project-init.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Initialize tracking for a new research project. Run once per project.

## Usage

`/project-init <slug> <project-path>`

- `<slug>`: short identifier, lowercase, hyphens ok (e.g. `thesis-ch2`, `jmp-draft`)
- `<project-path>`: absolute path to the project folder (e.g. `C:\path\to\project`)

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- Projects vault (under "Projects 鈫?Vault") 鈫?`<PROJECTS_VAULT>`
- Zotero config path (under "Research Idea Pipeline 鈫?Zotero config") 鈫?`<ZOTERO_CONFIG>`

---

## Step 1 鈥?Validate

1. Read `~/.claude/machine_paths.md` to confirm the projects vault path.
2. Verify `<project-path>` exists on disk. If not: stop and tell user.
3. Read `<PROJECTS_VAULT>\index.md`. If a row with `<slug>` already exists: stop and tell user "Project already initialized. Run /project-sync <slug> instead."

---

## Step 2 鈥?Create Zotero collection

Read `<ZOTERO_CONFIG>`. Using the Zotero Web API:

```
POST https://api.zotero.org/users/{user_id}/collections
Authorization: Bearer {api_key}
Content-Type: application/json

[{"name": "<slug>", "parentCollection": false}]
```

Extract the new collection key from the response (`successful["0"].key`). If the API call fails: tell user, continue without Zotero (set collection key to `"pending"`).

---

## Step 3 鈥?Create folder structure

Create the following files at `<PROJECTS_VAULT>\<slug>\`:

**`index.md`**:
```markdown
---
slug: <slug>
project-path: <project-path>
status: active
last-sync: <YYYY-MM-DD today>
zotero-collection: <collection-key>
---

[Ask user for 1鈥? sentence project description and insert here]

Open Issues: 0 items
Recent change: 鈥?
```

**`snapshot.json`**: `{}`  (empty 鈥?will be populated in Step 4)

**`map.md`**:
```markdown
# Project Map: <project-path>

Last updated: <YYYY-MM-DD>

| path | purpose | last-changed |
|------|---------|-------------|
```

**`changes.md`**:
```markdown
# Change Log

```

**`literature/index.md`**:
```markdown
# Literature

| title | direction | zotero | date-added |
|-------|-----------|--------|------------|
```

**`feedback/index.md`**:
```markdown
# Feedback Index

| person | date | items | open | summary |
|--------|------|-------|------|---------|
```

---

## Step 4 鈥?Initial folder scan

Walk `<project-path>` using this Python command:

```bash
python -c "
import os, json
root = r'<project-path>'
result = {}
for dirpath, dirnames, filenames in os.walk(root):
    # skip hidden folders
    dirnames[:] = [d for d in dirnames if not d.startswith('.')]
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

For directories (not files), also add folder entries with the most recent mtime among their children.

Write the result to `snapshot.json`.

For `map.md`: add one row per subfolder (not individual files, unless the folder has < 5 files total). For small folders, list individual files. Generate a brief purpose description from the folder/file name. Do NOT read file contents at this stage 鈥?infer purpose from names only.

---

## Step 5 鈥?Update global files

1. Append to `<PROJECTS_VAULT>\index.md`:
   `| <slug> | [title from description] | <project-path> | active | 0 | <YYYY-MM-DD> |`

2. Update `<ZOTERO_CONFIG>` 鈥?add to `project_collections`:
   ```json
   "<slug>": {"collection_key": "<key>", "directions": {}}
   ```

3. Append to `<PROJECTS_VAULT>\log.md`:
   `[PROJECT-INIT <YYYY-MM-DD>] slug: <slug> 鈫?path: <project-path> | zotero: <key>`

---

## Step 6 鈥?Report

Tell user (in Chinese):
- Project `<slug>` initialized at `projects/<slug>/`
- Zotero collection created (or pending if API failed)
- Folder map: X subfolders recorded in map.md
- Next steps: run `/project-sync <slug>` after making changes; use `/project-status <slug>` to discuss the project

