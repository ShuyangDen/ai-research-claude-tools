---
name: idea-develop
description: Use this skill when the user invokes $idea-develop, /idea-develop, asks to run idea-develop, or asks to deep-dive on an idea with cross-system context. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-develop
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-develop
- /idea-develop
- Natural language requests to deep-dive on an idea with cross-system context
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-develop.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Develop a research idea with targeted context drawn from the three-system knowledge base. Reads only lean indexes first, scores relevance, then loads only the relevant full files 鈥?not everything.

## Usage

`/idea-develop <slug>`

Where `<slug>` is an idea file name without `.md` (e.g. `ai-human-capital`, `ai-selective-reporting`).

---

## Step 0 鈥?Read machine paths

Read `~/.claude/machine_paths.md` to get:
- AI Education path (under "AI Education Project 鈫?Project root")
- Idea vault path (under "Research Idea Pipeline 鈫?Vault")

---

## Step 1 鈥?Load Layer 0 (indexes only)

Read these three files in parallel. Total size < 12 KB.

- `{{AI_EDUCATION_PATH}}\papers\index.md` 鈥?all studied papers with topics and one-liners
- `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\index.md` 鈥?all research ideas with status
- `{{OBSIDIAN_ROOT}}\JMP Idea\researcher_profile.md` 鈥?active research directions and methodology standards

*(Replace `{{AI_EDUCATION_PATH}}` and `{{OBSIDIAN_ROOT}}` with the paths read from machine_paths.md)*

If `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\<slug>.md` does not exist, stop and tell the user: "No idea file found at ideas/<slug>.md."

---

## Step 2 鈥?Score relevance

From the indexes, score each item for relevance to the target idea `<slug>`. Do this in one pass, not as separate API calls.

**Score each studied paper** (from papers/index.md) on:
- Topic overlap with the idea's research direction
- Methodological relevance (does it use methods the idea requires?)
- Whether it provides evidence for, against, or context for the idea's mechanism

**Score each other idea** (from ideas/index.md, excluding the target slug) on:
- Whether it shares the same underlying mechanism or data requirement
- Whether it has a complementary or conflicting research question

Load everything that scores "relevant" 鈥?no hard cap on count. Typically 3鈥? papers and 0鈥? related ideas. If a paper is clearly unrelated (e.g., sovereign debt paper for an AI-education idea), skip it.

---

## Step 3 鈥?Load Layer 2 (two sub-layers)

### Step 3a 鈥?Load compressed sources first (default)

For each relevant paper identified in Step 2:
- Check if `<WIKI_VAULT>\sources\<paper-slug>.md` exists
- **If yes**: load `sources/<paper-slug>.md` (compressed export, ~1 KB) 鈥?this is the default
- **If no**: fall back to `{{AI_EDUCATION_PATH}}\papers\notes\<paper-slug>.md` (full tutor notes)

Always load:
- `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\<slug>.md` 鈥?the target idea
- `{{OBSIDIAN_ROOT}}\JMP Idea\ideas\<related-slug>.md` 鈥?for each related idea (if any)

Do NOT load full-text paper markdowns from `papers/text/`.

### Step 3b 鈥?Load full notes on demand only

Load `papers/notes/<paper-slug>.md` ONLY when:
- The user explicitly asks about math prerequisites, proof details, or specific Phase 1/2 tutor content
- The sources file marks a method as "not covered" and the user is asking about that method

Announce to the user when falling back to full notes: "姝ｅ湪鍔犺浇 <slug> 鐨勫畬鏁寸瑪璁帮紙鍘熷鐗堬級浠ヨ幏鍙栨洿澶氱粏鑺傘€?

---

## Step 4 鈥?Report context loaded

Tell the user (in Chinese):
- Which idea is being developed
- Which papers were loaded (by title) and why each is relevant
- Which related ideas were loaded (if any)
- Total approximate context size

Then ask: "浣犳兂浠庡摢涓搴﹀垏鍏ワ紵锛堟満鍒惰璁°€佹暟鎹瓥鐣ャ€佹枃鐚患杩般€佽繕鏄壒鍒ゆ€у弽鎬濓紵锛?

---

## Step 5 鈥?Develop the idea

Work through whatever the user chooses. Draw explicitly on the loaded paper notes and researcher_profile when making connections. When you identify a new critique or research question, note it explicitly for the user to save to the idea file.

At the end of the session, remind the user to run `/idea-revise <slug>` to save any updates to the idea file.

