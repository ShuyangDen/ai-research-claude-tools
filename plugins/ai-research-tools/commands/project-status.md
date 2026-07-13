Main interaction hub for a tracked research project. Lean startup, progressive context loading.

## Usage

`/project-status <slug>`

## Paths (read from machine_paths.md)

Read `~/.claude/machine_paths.md` to get:
- Projects vault (under "Projects → Vault") → `<PROJECTS_VAULT>`
- Zotero config path (under "Research Idea Pipeline → Zotero config") → `<ZOTERO_CONFIG>`
- Idea vault (under "Research Idea Pipeline → Vault") → `<IDEA_VAULT>`

---

## Startup — load only index.md (< 2 KB)

1. Read `<PROJECTS_VAULT>\<slug>\index.md` ONLY.
2. Show a brief summary in Chinese:
   ```
   项目：<title>
   路径：<project-path>
   状态：<status>
   Open Issues：<N> 条
   最近变动：<recent-change>
   上次同步：<last-sync>
   ```
3. Ask: "想聊什么？（open问题、最近改动、文献、文件结构，或者直接说）"

Do NOT preload any other files. Load on demand only.

---

## Progressive loading rules

Load the following files ONLY when the user's message clearly needs them:

| User says | Load |
|-----------|------|
| "open问题" / "没解决的" / "还有什么要做" | `feedback/index.md` |
| 提到某人（导师、advisor、某人名）的反馈 | `feedback/index.md` first, then specific `feedback/<person>-<date>.md` |
| "最近改了什么" / "进展" / "sync" | last 5 lines of `changes.md` |
| "文件" / "结构" / "文件夹" | `map.md` |
| "文献" / "论文" / "zotero" | `literature/index.md` |
| 询问某条具体意见的细节 | the specific `feedback/<person>-<YYYYMMDD>.md` |
| "研究方向" / "idea" / "和我的研究有什么关系" | `## Active Research Directions` section of `<IDEA_VAULT>\researcher_profile.md` (load that section only, not the full file) |

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
   `| <title-short> | <direction> | ✅ | <YYYY-MM-DD> |`
5. Append to `<PROJECTS_VAULT>\log.md`:
   `[PROJECT-PAPER <YYYY-MM-DD>] slug: <slug> → added: <title> | direction: <direction> | zotero: ✅`
6. Tell user: added to Zotero collection `<direction>` and literature index.

If Zotero API fails: add to literature index with `⬜` status and note "需要手动添加到Zotero".

### Record feedback

Trigger: user pastes a block of text (chat log, email, notes) and mentions who it's from.

Steps:
1. Identify: person name, date (extract from text if possible, else use today), source type (wechat/email/meeting/self-summary).
2. Parse the content and extract individual feedback items (opinions, suggestions, concerns, questions).
3. For each item: propose status `open` by default. If the text clearly says something is done/resolved, propose `resolved-<date>`.
4. **STOP. Show proposal table:**
   ```
   ## Feedback Proposal — <person>, <date>
   Source: <wechat/email/meeting/self-summary>

   | # | item (original language) | proposed status |
   |---|--------------------------|-----------------|
   | 1 | ... | open |
   | 2 | ... | resolved-2026-05-08 |
   ```
   Say: "确认执行？回复 **confirm** 全部执行，或 **revise #N → open/resolved-日期** 修改某条，或 **skip** 取消。"

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
     `[PROJECT-FEEDBACK <YYYY-MM-DD>] slug: <slug> → from: <person> | <N> items | <open-count> open`

### Mark item resolved

Trigger: user says "第X条解决了" or "把[某条内容]标记为已解决".

Steps:
1. If not already loaded, read `feedback/index.md` to find the right feedback file.
2. Read the specific `feedback/<person>-<YYYYMMDD>.md`.
3. Change `[open]` to `[resolved-<today>]` for that item.
4. Decrement `open:` count in the frontmatter.
5. Update `feedback/index.md` open count for that row.
6. Update `<slug>/index.md` open-issues count.
7. Tell user: item marked resolved. N open items remaining.

### Check relevant past feedback

Trigger: user is discussing a topic and asks "有没有相关的意见" or similar.

Steps:
1. If not loaded: read `feedback/index.md` (summary table only).
2. Identify rows whose one-liner summary overlaps with the current topic.
3. Load only those specific `feedback/<person>-<date>.md` files.
4. Surface relevant items (both open and resolved) — note if resolved ones might still be informative.
