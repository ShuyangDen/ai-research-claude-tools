---
name: project-status
description: Use this skill when the user invokes $project-status, /project-status, asks to run project-status, or asks to discuss or inspect a tracked research project. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# project-status
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Projects Vault.
## Trigger Forms
- $project-status
- /project-status
- Natural language requests to discuss or inspect a tracked research project
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\project-status.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Main interaction hub for a tracked research project. Lean startup, progressive context loading.

## Usage

`/project-status <slug>`

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- Projects vault (under "Projects 鈫?Vault") 鈫?`<PROJECTS_VAULT>`
- Zotero config path (under "Research Idea Pipeline 鈫?Zotero config") 鈫?`<ZOTERO_CONFIG>`
- Idea vault (under "Research Idea Pipeline 鈫?Vault") 鈫?`<IDEA_VAULT>`

---

## Startup 鈥?load only index.md (< 2 KB)

1. Read `<PROJECTS_VAULT>\<slug>\index.md` ONLY.
2. Show a brief summary in Chinese:
   ```
   椤圭洰锛?title>
   璺緞锛?project-path>
   鐘舵€侊細<status>
   Open Issues锛?N> 鏉?
   鏈€杩戝彉鍔細<recent-change>
   涓婃鍚屾锛?last-sync>
   ```
3. Ask: "鎯宠亰浠€涔堬紵锛坥pen闂銆佹渶杩戞敼鍔ㄣ€佹枃鐚€佹枃浠剁粨鏋勶紝鎴栬€呯洿鎺ヨ锛?

Do NOT preload any other files. Load on demand only.

---

## Progressive loading rules

Load the following files ONLY when the user's message clearly needs them:

| User says | Load |
|-----------|------|
| "open闂" / "娌¤В鍐崇殑" / "杩樻湁浠€涔堣鍋? | `feedback/index.md` |
| 鎻愬埌鏌愪汉锛堝甯堛€乤dvisor銆佹煇浜哄悕锛夌殑鍙嶉 | `feedback/index.md` first, then specific `feedback/<person>-<date>.md` |
| "鏈€杩戞敼浜嗕粈涔? / "杩涘睍" / "sync" | last 5 lines of `changes.md` |
| "鏂囦欢" / "缁撴瀯" / "鏂囦欢澶? | `map.md` |
| "鏂囩尞" / "璁烘枃" / "zotero" | `literature/index.md` |
| 璇㈤棶鏌愭潯鍏蜂綋鎰忚鐨勭粏鑺?| the specific `feedback/<person>-<YYYYMMDD>.md` |
| "鐮旂┒鏂瑰悜" / "idea" / "鍜屾垜鐨勭爺绌舵湁浠€涔堝叧绯? | `## Active Research Directions` section of `<IDEA_VAULT>\researcher_profile.md` (load that section only, not the full file) |

Never preload multiple files at once. Load the most likely one, then load more if the user continues the thread.

---

## Inline operations (handle during conversation, no extra command needed)

### Add a paper

Trigger: user provides a paper title, DOI, or URL and says which direction it belongs to.

Steps:
1. Read `<ZOTERO_CONFIG>`.
2. Find `project_collections.<slug>.directions.<direction>`:
   - If exists: use that collection key
   - If not: create a new sub-collection via Zotero API under `project_collections.<slug>.collection_key`, update config
3. Add the paper to Zotero via API (use DOI lookup via Zotero's translation server if title-only):
   ```
   POST https://api.zotero.org/users/{user_id}/items
   Authorization: Bearer {api_key}
   Content-Type: application/json
   [{"itemType": "journalArticle", "title": "...", "DOI": "...", "collections": ["<collection-key>"]}]
   ```
4. Append to `<PROJECTS_VAULT>\<slug>\literature\index.md`:
   `| <title-short> | <direction> | 鉁?| <YYYY-MM-DD> |`
5. Append to `<PROJECTS_VAULT>\log.md`:
   `[PROJECT-PAPER <YYYY-MM-DD>] slug: <slug> 鈫?added: <title> | direction: <direction> | zotero: 鉁卄
6. Tell user: added to Zotero collection `<direction>` and literature index.

If Zotero API fails: add to literature index with `猬渀 status and note "闇€瑕佹墜鍔ㄦ坊鍔犲埌Zotero".

### Record feedback

Trigger: user pastes a block of text (chat log, email, notes) and mentions who it's from.

Steps:
1. Identify: person name, date (extract from text if possible, else use today), source type (wechat/email/meeting/self-summary).
2. Parse the content and extract individual feedback items (opinions, suggestions, concerns, questions).
3. For each item: propose status `open` by default. If the text clearly says something is done/resolved, propose `resolved-<date>`.
4. **STOP. Show proposal table:**
   ```
   ## Feedback Proposal 鈥?<person>, <date>
   Source: <wechat/email/meeting/self-summary>

   | # | item (original language) | proposed status |
   |---|--------------------------|-----------------|
   | 1 | ... | open |
   | 2 | ... | resolved-2026-05-08 |
   ```
   Say: "纭鎵ц锛熷洖澶?**confirm** 鍏ㄩ儴鎵ц锛屾垨 **revise #N 鈫?open/resolved-鏃ユ湡** 淇敼鏌愭潯锛屾垨 **skip** 鍙栨秷銆?

5. After user confirms:
   - Write `<PROJECTS_VAULT>\<slug>\feedback\<person>-<YYYYMMDD>.md`:
     ```markdown
     ---
     person: <person>
     date: <YYYY-MM-DD>
     source: <wechat/email/meeting/self-summary>
     items: <N>
     open: <count of open items>
     ---
     [numbered list with [open] / [resolved-date] labels]

     ## Raw Source
     [paste original text verbatim here]
     ```
   - Append to `feedback/index.md`:
     `| <person> | <YYYY-MM-DD> | <N> | <open-count> | <one-liner summary> |`
   - Update `<slug>/index.md`: increment open-issues by the number of new open items
   - Update `projects/index.md`: update open-issues for this slug
   - Append to `<PROJECTS_VAULT>\log.md`:
     `[PROJECT-FEEDBACK <YYYY-MM-DD>] slug: <slug> 鈫?from: <person> | <N> items | <open-count> open`

### Mark item resolved

Trigger: user says "绗琗鏉¤В鍐充簡" or "鎶奫鏌愭潯鍐呭]鏍囪涓哄凡瑙ｅ喅".

Steps:
1. If not already loaded, read `feedback/index.md` to find the right feedback file.
2. Read the specific `feedback/<person>-<YYYYMMDD>.md`.
3. Change `[open]` to `[resolved-<today>]` for that item.
4. Decrement `open:` count in the frontmatter.
5. Update `feedback/index.md` open count for that row.
6. Update `<slug>/index.md` open-issues count.
7. Tell user: item marked resolved. N open items remaining.

### Check relevant past feedback

Trigger: user is discussing a topic and asks "鏈夋病鏈夌浉鍏崇殑鎰忚" or similar.

Steps:
1. If not loaded: read `feedback/index.md` (summary table only).
2. Identify rows whose one-liner summary overlaps with the current topic.
3. Load only those specific `feedback/<person>-<date>.md` files.
4. Surface relevant items (both open and resolved) 鈥?note if resolved ones might still be informative.

