Initialize tracking for a new research project. Run once per project.

## Usage

`/project-init <slug> <project-path>`

- `<slug>`: short identifier, lowercase, hyphens ok (e.g. `thesis-ch2`, `jmp-draft`)
- `<project-path>`: absolute path to the project folder (e.g. `<absolute-project-path>`)

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- Projects vault (under "Projects → Vault") → `<PROJECTS_VAULT>`
- Zotero config path (under "Research Idea Pipeline → Zotero config") → `<ZOTERO_CONFIG>`

---

## Step 1 — Validate

1. Read `~/.claude/machine_paths.md` to confirm the projects vault path.
2. Verify `<project-path>` exists on disk. If not: stop and tell user.
3. Read `<PROJECTS_VAULT>\index.md`. If a row with `<slug>` already exists: stop and tell user "Project already initialized. Run /project-sync <slug> instead."

---

## Step 2 — Create Zotero collection

Read `<ZOTERO_CONFIG>`. Using the Zotero Web API:

```
POST https://api.zotero.org/users/{user_id}/collections
Authorization: Bearer {api_key}
Content-Type: application/json

[{"name": "<slug>", "parentCollection": false}]
```

Extract the new collection key from the response (`successful["0"].key`). If the API call fails: tell user, continue without Zotero (set collection key to `"pending"`).

---

## Step 3 — Create folder structure

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

[Ask user for 1–2 sentence project description and insert here]

Open Issues: 0 items
Recent change: —
```

**`snapshot.json`**: `{}`  (empty — will be populated in Step 4)

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

## Step 4 — Initial folder scan

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

For `map.md`: add one row per subfolder (not individual files, unless the folder has < 5 files total). For small folders, list individual files. Generate a brief purpose description from the folder/file name. Do NOT read file contents at this stage — infer purpose from names only.

---

## Step 5 — Update global files

1. Append to `<PROJECTS_VAULT>\index.md`:
   `| <slug> | [title from description] | <project-path> | active | 0 | <YYYY-MM-DD> |`

2. Update `<ZOTERO_CONFIG>` — add to `project_collections`:
   ```json
   "<slug>": {"collection_key": "<key>", "directions": {}}
   ```

3. Append to `<PROJECTS_VAULT>\log.md`:
   `[PROJECT-INIT <YYYY-MM-DD>] slug: <slug> → path: <project-path> | zotero: <key>`

---

## Step 6 — Report

Tell user (in Chinese):
- Project `<slug>` initialized at `projects/<slug>/`
- Zotero collection created (or pending if API failed)
- Folder map: X subfolders recorded in map.md
- Next steps: run `/project-sync <slug>` after making changes; use `/project-status <slug>` to discuss the project
