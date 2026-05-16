Update the researcher profile by distilling the current state of the idea pipeline and syncing to the paper tracker.
Uses an incremental cache so only modified idea files are re-read.

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- Idea pipeline vault (under "Research Idea Pipeline → Vault") → call this `<IDEA_VAULT>`
- Paper tracker path (under "Paper Tracker → Path") → call this `<PAPER_TRACKER_PATH>`

Derived paths:
- Ideas folder: `<IDEA_VAULT>\ideas\`
- Cache file: `<IDEA_VAULT>\ideas\_profile_cache.json`
- Source researcher_profile: `<IDEA_VAULT>\researcher_profile.md`
- Paper tracker copy: `<PAPER_TRACKER_PATH>\researcher_profile.md`
- Paper tracker git dir: `<PAPER_TRACKER_PATH>\`

---

## Step 1 — Load cache

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

## Step 2 — Detect changed files

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

## Step 3 — Read only changed files

For each file marked **Needs reading**, read its frontmatter and body. Extract:

- `title`: from the `# ` heading
- `status`: from frontmatter `status:` field
- `description`: one-line core mechanism from the "Original Idea" section
- `archived_reason`: if `status: archived`, extract the failure reason from "## Decision Log"; otherwise `null`

Classify:
- **Active**: status is one of `capture`, `explore`, `question`, `data-search`, `data-prep`, `report`, `done`
- **Archived**: status is `archived`

For files using cached data, read `title`, `status`, `description`, `archived_reason` directly from the cache — do NOT re-read the file.

---

## Step 3b — Check if profile-relevant fields changed

Compare each re-read file's extracted fields against its cached values:
- Did `title` change? → profile-relevant
- Did `status` change? → profile-relevant (e.g., `explore` → `archived`)
- Did `description` change? → profile-relevant

**If NO re-read file has a profile-relevant change** (only `updated:` in frontmatter changed, e.g., from evidence bullets appended): skip Steps 5–7 entirely. Proceed to Step 4 (update cache) then Step 8 (report with skip notice). Do NOT rewrite researcher_profile.md, do NOT copy to paper_tracker, do NOT git push.

---

## Step 4 — Update cache

Write the updated cache back to `<IDEA_VAULT>\ideas\_profile_cache.json`.

For every idea file (changed or unchanged), write its current mtime and extracted fields. Remove entries for files that no longer exist.

---

## Step 5 — Read current researcher_profile.md

Read `<IDEA_VAULT>\researcher_profile.md` in full. You will rewrite only two sections; keep everything else verbatim.

---

## Step 6 — Rewrite the profile

Update the following sections. Do NOT touch any other section.

### Section to replace: `## Active Research Directions`

Rewrite based on all active ideas (from cache + newly read). Format:

```
## Active Research Directions

Papers touching these directions are most likely to generate interest:

1. **[Idea title]** *(stage)*: [One sentence: core mechanism + what makes it interesting]
2. ...
```

Order by priority (high → medium → low), then by pipeline stage (earlier = more speculative).

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

## Step 7 — Save and sync

1. Write the updated content to `<IDEA_VAULT>\researcher_profile.md`
2. Copy the same content to `<PAPER_TRACKER_PATH>\researcher_profile.md`
3. In the paper tracker git directory, run:
   ```
   git add researcher_profile.md
   git commit -m "chore: sync researcher_profile from idea pipeline update"
   git push origin main
   ```

---

## Step 8 — Report

Tell the user:
- How many files were re-read vs served from cache
- Total active ideas (list titles + stages) and archived ideas
- If Steps 5–7 ran: confirm both files were updated and git push succeeded; if git push failed, show the error and ask the user to push manually
- If Steps 5–7 were skipped: note "No profile-relevant changes (title/status/description unchanged) — researcher_profile.md and paper_tracker not updated"
- **Reminder** (only when git push ran): researcher_profile.md has been pushed to paper_tracker repo. If you also changed paperextract.py or any other code in the paper tracker, manually push those changes too.
