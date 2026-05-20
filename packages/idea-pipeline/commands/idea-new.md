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
- (d) explore now or capture only? (default: **capture only**)

**Step 2: Create idea page**
- Generate a URL-safe slug from the title (e.g., "ai-selective-reporting")
- Create `ideas/<slug>.md` based on `ideas/_template.md`
- Fill in the "Original Idea" section

**Step 3: Capture only (default)**
- Set frontmatter: status=capture, checkpoint_pending=false, created/updated=today
- Update `ideas/index.md` — add to "Captured" section
- Append to `ideas/log.md`: `[IDEA-NEW YYYY-MM-DD] slug: <slug> → captured`
- Tell user:
  - "Idea captured as `<slug>`. Run `/idea-next <slug>` to run literature exploration."
  - "Or run `/idea-socratic <slug>` first to refine the idea through structured questions before exploring."

**Step 3 (alt): Explore now (only if user explicitly chose this)**
- Run S2 literature exploration with **hard cap: max 5 papers, max 3 gaps**
- Using your own knowledge, find:
  - Key existing papers on this topic (max 5 — with authors, year, journal, brief description)
  - Research gaps this idea could fill (max 3)
  - Similar research questions already studied (and what's different about this one)
  - Relevant datasets that might be useful (brief mention, full search comes in S4)
  - Always note: "⚠️ Based on Claude's knowledge (cutoff ~Aug 2025). Verify recent work on Google Scholar."
- Fill in the "S2: Literature Exploration" section
- Set frontmatter: status=explore, checkpoint_pending=true, created/updated=today
- Update `ideas/index.md` — add to "🔴 Waiting for Review" section
- Append to `ideas/log.md`: `[IDEA-NEW YYYY-MM-DD] slug: <slug> → created, auto-explored`
- Report summary to user (3-5 bullet points from literature found)
- Tell user to review and run `/idea-next <slug>` to continue
