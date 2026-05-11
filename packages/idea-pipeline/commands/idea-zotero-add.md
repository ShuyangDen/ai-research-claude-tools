You are managing the Zotero library for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get:
- Vault path (under "Research Idea Pipeline → Vault")
- Zotero config path (under "Research Idea Pipeline → Zotero config")

Read the Zotero config file to get `api_key` and `user_id`.
Zotero Web API base: `https://api.zotero.org/users/{user_id}`

Usage: `/idea-zotero-add <slug> <doi-or-url>`

**Step 1: Read config**
Read the Zotero config file (path from machine_paths.md) to get:
- api_key
- user_id  
- idea_collections map (slug → collection key)

If the slug is not in idea_collections, ask the user if they want to create a new collection for it.

**Step 2: Resolve the paper**
From the DOI or URL provided:
- If it's a DOI (starts with `10.` or `doi.org`): use Zotero's translation server via the Web API
- If it's a URL: pass directly to Zotero translator

Try to add via Zotero Web API using the "items/new" endpoint with identifier lookup:
```
POST https://api.zotero.org/users/{user_id}/items
```

Use this approach to resolve metadata:
1. First try: `https://api.zotero.org/users/{user_id}/items` with a search for existing items matching the DOI
2. If not found: use `https://www.zotero.org/utils/doi?doi={doi}` or the Crossref API to fetch metadata
3. Construct a Zotero item JSON with the metadata and POST it

**Step 3: Add to correct collection**
After creating the item, add it to the idea's collection:
```
PATCH https://api.zotero.org/users/{user_id}/items/{item_key}
```
with `collections: [collection_key]`

**Step 4: Try to attach PDF**
- Check if the paper is Open Access via Unpaywall: `https://api.unpaywall.org/v2/{doi}?email=<YOUR_EMAIL>`
- If OA PDF available: download it and attach to the Zotero item via:
  ```
  POST https://api.zotero.org/users/{user_id}/items/{item_key}/file
  ```
- If not OA: tell the user "PDF not freely available. You can manually attach via Zotero desktop."

**Step 5: Update idea page**
- Read `ideas/<slug>.md` from the vault path
- In the Literature Exploration section, find the paper and add a ✅ Zotero marker next to it
- If the paper wasn't in the list yet, add it to a "## Added to Zotero" subsection
- Append to `ideas/log.md`: `[ZOTERO-ADD YYYY-MM-DD] slug: <slug> → added: <paper title>`

**Step 6: Report**
Tell the user:
- Paper title and authors
- Whether PDF was attached automatically or needs manual download
- Zotero collection it was added to
