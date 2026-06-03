---
name: update-researcher-profile
description: Use this skill when the user invokes $update-researcher-profile, /update-researcher-profile, asks to run update-researcher-profile, or asks to sync the researcher profile from idea files. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# update-researcher-profile
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $update-researcher-profile
- /update-researcher-profile
- Natural language requests to sync the researcher profile from idea files
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\update-researcher-profile.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Update the researcher profile by distilling the current state of the idea pipeline and syncing to the paper tracker.
Uses an incremental cache so only modified idea files are re-read.

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- Idea pipeline vault (under "Research Idea Pipeline 鈫?Vault") 鈫?call this `<IDEA_VAULT>`
- Paper tracker path (under "Paper Tracker 鈫?Path") 鈫?call this `<PAPER_TRACKER_PATH>`

Derived paths:
- Ideas folder: `<IDEA_VAULT>\ideas\`
- Cache file: `<IDEA_VAULT>\ideas\_profile_cache.json`
- Source researcher_profile: `<IDEA_VAULT>\researcher_profile.md`
- Paper tracker copy: `<PAPER_TRACKER_PATH>\researcher_profile.md`
- Paper tracker git dir: `<PAPER_TRACKER_PATH>\`

---

## Step 1 鈥?Load cache

Read `<IDEA_VAULT>\ideas\_profile_cache.json`.

If it does not exist, treat cache as `{}` (all files will be read fresh).

Cache format:
```json
{
  "ai-selective-reporting.md": {
    "mtime": 1715430600.0,
    "title": "AI and Selective Reporting",
    "status": "explore",
    "description": "One-line mechanism description",
    "archived_reason": null
  }
}
```

---

## Step 2 鈥?Detect changed files

Run this Python command to get the current mtime of every idea file (excluding skipped ones):

```bash
python -c "
import os, json
skip = {'index.md', 'log.md', '_template.md', '_frontmatter_cache.md', '_profile_cache.json'}
d = r'<IDEA_VAULT>\ideas'
for f in sorted(os.listdir(d)):
    if f.endswith('.md') and f not in skip:
        print(f + '\t' + str(os.path.getmtime(os.path.join(d, f))))
"
```

Compare each file's current mtime to its cached mtime.

- **Needs reading**: file is not in cache, OR current mtime > cached mtime
- **Use cache**: current mtime == cached mtime (data is still valid)

---

## Step 3 鈥?Read only changed files

For each file marked **Needs reading**, read its frontmatter and body. Extract:

- `title`: from the `# ` heading
- `status`: from frontmatter `status:` field
- `description`: one-line core mechanism from the "Original Idea" section
- `archived_reason`: if `status: archived`, extract the failure reason from "## Decision Log"; otherwise `null`

Classify:
- **Active**: status is one of `capture`, `explore`, `question`, `data-search`, `data-prep`, `report`, `done`
- **Archived**: status is `archived`

For files using cached data, read `title`, `status`, `description`, `archived_reason` directly from the cache 鈥?do NOT re-read the file.

---

## Step 3b 鈥?Check if profile-relevant fields changed

Compare each re-read file's extracted fields against its cached values:
- Did `title` change? 鈫?profile-relevant
- Did `status` change? 鈫?profile-relevant (e.g., `explore` 鈫?`archived`)
- Did `description` change? 鈫?profile-relevant

**If NO re-read file has a profile-relevant change** (only `updated:` in frontmatter changed, e.g., from evidence bullets appended): skip Steps 5鈥? entirely. Proceed to Step 4 (update cache) then Step 8 (report with skip notice). Do NOT rewrite researcher_profile.md, do NOT copy to paper_tracker, do NOT git push.

---

## Step 4 鈥?Update cache

Write the updated cache back to `<IDEA_VAULT>\ideas\_profile_cache.json`.

For every idea file (changed or unchanged), write its current mtime and extracted fields. Remove entries for files that no longer exist.

---

## Step 5 鈥?Read current researcher_profile.md

Read `<IDEA_VAULT>\researcher_profile.md` in full. You will rewrite only two sections; keep everything else verbatim.

---

## Step 6 鈥?Rewrite the profile

Update the following sections. Do NOT touch any other section.

### Section to replace: `## Active Research Directions`

Rewrite based on all active ideas (from cache + newly read). Format:

```
## Active Research Directions

Papers touching these directions are most likely to generate interest:

1. **[Idea title]** *(stage)*: [One sentence: core mechanism + what makes it interesting]
2. ...
```

Order by priority (high 鈫?medium 鈫?low), then by pipeline stage (earlier = more speculative).

### Section to replace: `## Recurring Failure Modes` (inside "Research Quality Bar for New Ideas")

If any ideas are archived, add or update:

```
**Recurring failure modes** (from archived ideas):
- `[slug]`: [One line: why it was archived]
```

If no ideas are archived, leave this subsection unchanged.

### Update the header

Change `Last updated:` to today's date.
Update the source line to reflect current active/archived counts.

---

## Step 7 鈥?Save and sync

1. Write the updated content to `<IDEA_VAULT>\researcher_profile.md`
2. Copy the same content to `<PAPER_TRACKER_PATH>\researcher_profile.md`
3. In the paper tracker git directory, run:
   ```
   git add researcher_profile.md
   git commit -m "chore: sync researcher_profile from idea pipeline update"
   git push origin main
   ```

---

## Step 8 鈥?Report

Tell the user:
- How many files were re-read vs served from cache
- Total active ideas (list titles + stages) and archived ideas
- If Steps 5鈥? ran: confirm both files were updated and git push succeeded; if git push failed, show the error and ask the user to push manually
- If Steps 5鈥? were skipped: note "No profile-relevant changes (title/status/description unchanged) 鈥?researcher_profile.md and paper_tracker not updated"
- **Reminder** (only when git push ran): researcher_profile.md has been pushed to paper_tracker repo. If you also changed paperextract.py or any other code in the paper tracker, manually push those changes too.

