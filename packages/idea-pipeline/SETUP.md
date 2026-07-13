# Idea Pipeline — Standalone Setup Guide

If you're using the master INSTALL.md from `ai-research-claude-tools/`, skip this file — the master installer handles everything.

## Prerequisites

- Claude Code installed
- A free Zotero account (optional but recommended): zotero.org
- An Obsidian installation for the vaults (optional but recommended): obsidian.md

## Step 1 — Decide on your Obsidian root folder

The system creates 3 vaults under one root folder. Example:
- Windows: `C:\Users\<you>\obsidian\`
- Mac: `~/obsidian/`

Inside that root, the installer creates:
- `<root>\JMP Idea\` — research idea pipeline vault
- `<root>\personal knowledge skill\` — knowledge wiki vault
- `<root>\projects\` — project tracking vault

## Step 2 — Copy vault files

Copy each subfolder from `packages/idea-pipeline/obsidian/` to your chosen Obsidian root.

On upgrades, copy only system files (`CLAUDE.md`, `AGENTS.md`, templates) and create missing directories. Never replace personal ideas, source records, wiki pages, profiles, logs, or sessions with package skeletons.

```
packages/idea-pipeline/obsidian/JMP Idea/     → <root>\JMP Idea\
packages/idea-pipeline/obsidian/personal knowledge skill/ → <root>\personal knowledge skill\
packages/idea-pipeline/obsidian/projects/     → <root>\projects\
```

## Step 3 — Install global commands

Copy all `.md` files from `packages/idea-pipeline/commands/` to `~/.claude/commands/`, or use the repository sync tool so hashes and backups are recorded.

On Windows: `C:\Users\<you>\.claude\commands\`
On Mac/Linux: `~/.claude/commands/`

## Step 4 — Install rules

Copy all files from `packages/idea-pipeline/config/rules/` to `~/.claude/rules/`.

## Step 5 — Configure machine_paths.md

Copy `packages/idea-pipeline/config/machine_paths.example.md` to `~/.claude/machine_paths.md`.

Edit the file and replace all `{{PLACEHOLDER}}` values with your actual paths:

```markdown
## AI Research Tools
- **Source root**: `<path to this ai-research-claude-tools clone>`

## Personal Knowledge Wiki
- **Vault**: `C:\Users\<you>\obsidian\personal knowledge skill`

## Research Idea Pipeline
- **Vault**: `C:\Users\<you>\obsidian\JMP Idea`
- **Zotero config**: `C:\Users\<you>\.claude\zotero\config.json`

## AI Education Project
- **Project root**: `<path to your AI Education folder>`
- ...

## Projects
- **Vault**: `C:\Users\<you>\obsidian\projects`

## Paper Tracker
- **Project root**: `<path to your paper tracker repo folder>`
```

## Step 6 — Configure Zotero (optional)

Copy `packages/idea-pipeline/config/zotero/config.example.json` to `~/.claude/zotero/config.json`.

Get your Zotero API key:
1. Log in at zotero.org → Settings → Feeds/API
2. Click "Create new private key"
3. Enable library read/write access

Get your user ID:
1. Go to zotero.org/settings/keys
2. Your user ID is shown as "Your userID for use in API calls: XXXXXXX"

Edit `config.json`:
```json
{
  "api_key": "your-api-key-here",
  "user_id": "your-user-id-here",
  "unpaywall_email": "optional-email-for-oa-lookup@example.org",
  "idea_collections": {},
  "project_collections": {}
}
```

`unpaywall_email` is optional. Leave it empty to skip automatic Unpaywall PDF lookup; the workflow never sends a placeholder email.

## Step 7 — Open JMP Idea vault with Claude Code

```bash
cd "<root>\JMP Idea"
claude
```

Run `/idea-new` to create your first research idea.

Use `/idea-chat <slug>` for ordinary idea discussion. `/idea-develop` remains a compatibility alias.

## Step 8 — Customize researcher_profile.md

Edit `<root>\JMP Idea\researcher_profile.md`:
- Fill in your Core Research Focus
- Set your Methodology Requirements (what methods you require/exclude)
- Add your "What This Researcher Does NOT Care About" list

After adding your first few ideas, run `/update-researcher-profile` to auto-populate Active Research Directions.
