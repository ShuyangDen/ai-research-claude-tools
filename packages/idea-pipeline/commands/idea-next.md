You are managing a research idea pipeline for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get:
- Vault path (under "Research Idea Pipeline → Vault")
- Zotero config path (under "Research Idea Pipeline → Zotero config")

All file paths below are relative to that vault root.
Follow the instructions in `CLAUDE.md` in that vault.

Perform an **ADVANCE IDEA** operation for the idea slug provided in the arguments (e.g., `/idea-next ai-selective-reporting`).

If no slug is provided, list all ideas with `checkpoint_pending: true` and ask which one to advance.

Steps:
1. Read `ideas/<slug>.md` and check the current `status` in frontmatter
2. Based on current status, execute the next stage as defined in CLAUDE.md:

   **explore → question:**
   - Based on literature + any user feedback, formulate 1 main research question + 2-3 sub-questions + hypotheses
   - Suggest a plausible identification strategy
   - Fill "Research Questions" section
   - Set status=question, checkpoint_pending=true
   - **Zotero sync for S2 papers:** Read the Zotero config path from machine_paths.md. For each key paper already listed in the Literature Exploration section that has a DOI:
     1. Check Unpaywall `https://api.unpaywall.org/v2/{doi}?email=<YOUR_EMAIL>` for OA status
     2. Fetch metadata from Crossref `https://api.crossref.org/works/{doi}` and construct a Zotero item JSON
     3. POST to `https://api.zotero.org/users/{user_id}/items` with the API key to add it
     4. Add to the idea's collection from config `idea_collections[slug]`
     5. Mark ✅ next to papers successfully added, ⬜ for ones that need manual download
   - After syncing, show a summary: "Added X papers to Zotero. Y need manual PDF download: [list titles]"

   **question → data-search:**
   - Run THREE-SOURCE dataset search:
     1. Your own knowledge: recommend known public datasets
     2. Use the `/paper-lookup` K-Dense skill to search for relevant papers and datasets via OpenAlex API
     3. Fetch awesome-public-datasets: `curl -s https://raw.githubusercontent.com/awesomedata/awesome-public-datasets/master/README.rst` and search for matches
     4. Check economics-specific databases listed in CLAUDE.md (IPUMS, BLS, PSID, O*NET, etc.)
   - Fill "Datasets" table: name, source, URL, size, relevance (1-5), notes
   - Set status=data-search, checkpoint_pending=true

   **data-search → data-prep:**
   - Download and clean the user-approved dataset(s) into `ideas/data/<slug>/`
   - Document all cleaning steps in the idea page
   - Set status=data-prep, checkpoint_pending=false

   **data-prep → report:**
   - Generate preliminary analysis report at `ideas/reports/<slug>-report.md`
   - Include: descriptive stats, key distributions, preliminary correlations, data quality assessment, suggested next steps
   - Set status=report, checkpoint_pending=false

3. Update frontmatter: new status, updated=today, checkpoint_pending as above
4. Update `ideas/index.md` to reflect new status
5. Append to `ideas/log.md`: `[IDEA-NEXT YYYY-MM-DD] slug: <slug> → advanced: <old>→<new>`
6. Report summary to user in the Claude Code session
