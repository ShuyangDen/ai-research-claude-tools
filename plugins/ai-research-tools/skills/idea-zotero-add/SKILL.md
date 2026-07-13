---
name: idea-zotero-add
description: "Use this skill when the user invokes $idea-zotero-add, /idea-zotero-add, asks to run idea-zotero-add, or asks to add a paper to an idea's Zotero collection. This is the Codex adapter for the canonical AI Research Tools Claude command."
---
# idea-zotero-add

<!-- workflow-adapter: {"generator_version":"1.0.0","schema":"ai-research-tools.codex-skill-adapter","schema_version":1,"source_path":"packages/idea-pipeline/commands/idea-zotero-add.md","source_sha256":"e156ceada01866c728103e4259b25c2902f78597c1665dbbc8dda7afbaa8761d","workflow_version":"3.0.0"} -->

## Trigger Forms

- $idea-zotero-add
- /idea-zotero-add
- Natural language requests to add a paper to an idea's Zotero collection

## Codex Execution Rules

- Do **not** read `~/.claude/commands/idea-zotero-add.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

You are managing the Zotero library for an economics PhD student.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` to get:
- Vault path (under "Research Idea Pipeline → Vault")
- Zotero config path (under "Research Idea Pipeline → Zotero config")

Read the Zotero config file to get `api_key`, `user_id`, and optional `unpaywall_email`.
Zotero Web API base: `https://api.zotero.org/users/{user_id}`

Usage: `/idea-zotero-add <slug> <doi-or-url>`

**Step 1: Read config**
Read the Zotero config file (path from machine_paths.md) to get:
- api_key
- user_id
- unpaywall_email (optional; used only for Unpaywall OA lookup)
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
- If `unpaywall_email` is configured, check Open Access via `https://api.unpaywall.org/v2/{doi}?email={url_encoded_unpaywall_email}`. Never log or invent the email.
- If it is absent, skip Unpaywall lookup and report that automatic OA attachment was not attempted; do not send a placeholder address.
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
