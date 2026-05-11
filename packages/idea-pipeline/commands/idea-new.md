You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get the vault path (under "Research Idea Pipeline → Vault").
All file paths below are relative to that vault root.
Follow the instructions in `CLAUDE.md` in that vault.

Perform a **CREATE NEW IDEA** operation:

**Step 1: Gather idea details**
Ask the user for:
- (a) idea description (can be rough/one sentence)
- (b) research domain (default: economics)
- (c) priority: low / medium / high

**Step 2: Create idea page**
- Generate a URL-safe slug from the title (e.g., "ai-selective-reporting")
- Create `ideas/<slug>.md` based on `ideas/_template.md`
- Fill in the "Original Idea" section

**Step 3: Auto-run S2 (Literature Exploration)**
Using your own knowledge, find:
- Key existing papers on this topic (with authors, year, journal, brief description)
- Research gaps this idea could fill
- Similar research questions already studied (and what's different about this one)
- Relevant datasets that might be useful (brief mention, full search comes in S4)
- Always note: "⚠️ Based on Claude's knowledge (cutoff ~Aug 2025). Verify recent work on Google Scholar."

Fill in the "Literature Exploration" section.

**Step 4: Finalize**
- Set frontmatter: status=explore, checkpoint_pending=true, created/updated=today
- Update `ideas/index.md` — add to "🔴 Waiting for Review" section
- Append to `ideas/log.md`: `[IDEA-NEW YYYY-MM-DD] slug: <slug> → created, auto-explored`

**Step 5: Report to Claude Code session**
- Which page was created
- Summary of literature found (3-5 bullet points)
- Tell user to review and run `/idea-next <slug>` to continue
