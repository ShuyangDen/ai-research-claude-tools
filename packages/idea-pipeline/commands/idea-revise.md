You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline → Vault").
All file paths below are relative to that vault root.
Follow the instructions in `CLAUDE.md` in that vault.

Perform a **REVISE IDEA** operation for the slug provided in the arguments (e.g., `/idea-revise ai-selective-reporting`).

Steps:
1. Read `ideas/<slug>.md` to understand current stage and content
2. Ask the user: "What specifically needs to change?"
3. Re-run the current stage incorporating the user's feedback
4. Update the relevant section(s) of the idea page
5. Set checkpoint_pending: true
6. Update frontmatter: updated date
7. Append to `ideas/log.md`: `[IDEA-REVISE YYYY-MM-DD] slug: <slug> → re-ran stage: <stage>, reason: <brief>`
8. Report what was changed
