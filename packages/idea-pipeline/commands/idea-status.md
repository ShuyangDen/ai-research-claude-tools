You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline → Vault").
All file paths below are relative to that vault root.

Perform a **STATUS CHECK** operation:

1. List all `.md` files in `ideas/` directory (exclude: index.md, log.md, _template.md)
2. Read the frontmatter of each file
3. Output a formatted status table grouped by:
   - 🔴 Waiting for Review (checkpoint_pending: true) — list these first with emphasis
   - 🟡 In Progress (checkpoint_pending: false, status not done/archived)
   - ✅ Done
   - 🗄️ Archived
4. For each idea show: slug, title (# heading), current status/stage, priority, last updated date
5. Also update `ideas/index.md` to match the current state
