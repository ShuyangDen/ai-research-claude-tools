---
name: idea-next
description: Use this skill when the user invokes $idea-next, /idea-next, asks to run idea-next, or asks to advance an idea to the next pipeline stage. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-next
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-next
- /idea-next
- Natural language requests to advance an idea to the next pipeline stage
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-next.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get:
- Vault path (under "Research Idea Pipeline 鈫?Vault")
- Zotero config path (under "Research Idea Pipeline 鈫?Zotero config")

All file paths below are relative to that vault root.
Follow the instructions in `CLAUDE.md` in that vault.

Perform an **ADVANCE IDEA** operation for the idea slug provided in the arguments (e.g., `/idea-next ai-selective-reporting`).

If no slug is provided, list all ideas with `checkpoint_pending: true` and ask which one to advance.

Steps:
1. Read `ideas/<slug>.md` and check the current `status` in frontmatter
2. Based on current status, execute the next stage as defined in CLAUDE.md:

   **explore 鈫?question:**
   - Check if `## S1.5: Socratic Refinement` section exists and contains insights in the "Complete INSIGHT List"
     - If S1.5 insights exist: use them as the basis for the RQ, sub-questions, hypotheses, and identification strategy 鈥?do NOT re-derive from scratch. Acknowledge this in the section: "Formulated from S1.5 Socratic Refinement insights."
     - If no S1.5 section: derive from the literature in S2 + any user feedback
   - Formulate 1 main research question + 2-3 sub-questions + hypotheses
   - Suggest a plausible identification strategy
   - Fill "Research Questions" section
   - Set status=question, checkpoint_pending=true
   - **Zotero sync for S2 papers:** Read the Zotero config path from machine_paths.md. For each key paper already listed in the Literature Exploration section that has a DOI:
     1. Check Unpaywall `https://api.unpaywall.org/v2/{doi}?email=<YOUR_EMAIL>` for OA status
     2. Fetch metadata from Crossref `https://api.crossref.org/works/{doi}` and construct a Zotero item JSON
     3. POST to `https://api.zotero.org/users/{user_id}/items` with the API key to add it
     4. Add to the idea's collection from config `idea_collections[slug]`
     5. Mark 鉁?next to papers successfully added, 猬?for ones that need manual download
   - After syncing, show a summary: "Added X papers to Zotero. Y need manual PDF download: [list titles]"

   **question 鈫?data-search:**
   - Run THREE-SOURCE dataset search:
     1. Your own knowledge: recommend known public datasets
     2. Use the `/paper-lookup` K-Dense skill to search for relevant papers and datasets via OpenAlex API
     3. Do NOT fetch the raw awesome-public-datasets README (it is ~400 KB and degrades attention). Instead, apply your knowledge of that list to surface relevant entries by topic.
     4. Check economics-specific databases listed in CLAUDE.md (IPUMS, BLS, PSID, O*NET, etc.)
   - Fill "Datasets" table: name, source, URL, size, relevance (1-5), notes
   - Set status=data-search, checkpoint_pending=true

   **data-search 鈫?data-prep:**
   - Download and clean the user-approved dataset(s) into `ideas/data/<slug>/`
   - Document all cleaning steps in the idea page
   - Set status=data-prep, checkpoint_pending=false

   **data-prep 鈫?report:**
   - Generate preliminary analysis report at `ideas/reports/<slug>-report.md`
   - Include: descriptive stats, key distributions, preliminary correlations, data quality assessment, suggested next steps
   - Set status=report, checkpoint_pending=false

3. Update frontmatter: new status, updated=today, checkpoint_pending as above
4. Update `ideas/index.md` to reflect new status
5. Append to `ideas/log.md`: `[IDEA-NEXT YYYY-MM-DD] slug: <slug> 鈫?advanced: <old>鈫?new>`
6. Report summary to user in the Claude Code session

