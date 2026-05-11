You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline → Vault").
All file paths below are relative to that vault root.

Perform an **ARCHIVE IDEA** operation for the slug provided in the arguments (e.g., `/idea-archive ai-selective-reporting`).

Steps:
1. Ask: "Why are you archiving this idea?" (data not available / too similar to existing work / pivoted to different approach / other)
2. Update `ideas/<slug>.md`:
   - Set frontmatter: status=archived, checkpoint_pending=false, updated=today
   - Add to "Decision Log" section: date + reason
3. Update `ideas/index.md`: move from current section to "🗄️ Archived"
4. Append to `ideas/log.md`: `[IDEA-ARCHIVE YYYY-MM-DD] slug: <slug> → reason: <reason>`
5. Confirm to user: idea archived. They can always un-archive by editing the frontmatter manually.
