---
name: idea-help
description: Use this skill when the user invokes $idea-help, /idea-help, asks to run idea-help, or asks to show a state-aware action menu for idea work. This is the Codex-native copy of the AI Research Tools workflow; do not read Claude command files at runtime.
---
# idea-help
This is the Codex-native version of the AI Research Tools command $(System.Collections.Hashtable.Name) for Research Idea Pipeline.
## Trigger Forms
- $idea-help
- /idea-help
- Natural language requests to show a state-aware action menu for idea work
## Codex Execution Rules
- Do **not** read {{HOME}}\.claude\commands\idea-help.md at runtime. This skill is the copied command source for Codex.
- Read {{HOME}}\.claude\machine_paths.md first whenever the workflow needs project or vault paths.
- Preserve Claude Code commands; never delete or overwrite files in {{HOME}}\.claude\commands\.
- Follow Codex filesystem rules: use apply_patch for repo edits when possible; request escalated permission before writing outside the current writable root; use native PowerShell cmdlets with -LiteralPath for Obsidian vault appends or copies.
- Do not take destructive actions unless the user explicitly requested them.
- Preserve user data. Do not overwrite idea files, source notes, paper notes, wiki pages, or project files unless this command explicitly says to update them.
- If the command contains a confirmation checkpoint, stop and wait for explicit user approval before making the gated writes.
## Command Workflow
Show what actions are available right now, based on the current state of the idea pipeline.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` 鈫?vault path (under "Research Idea Pipeline 鈫?Vault").

**Step 1: Read cache only (do NOT open individual idea files)**
Read `ideas/_frontmatter_cache.md`. If missing or empty, read only the frontmatter blocks from each idea file to rebuild it.

**Step 2: Compute current state**
From the cache, identify:
- Ideas with `checkpoint_pending: true` (waiting for your action)
- Ideas by status: capture / explore / question / data-search / data-prep / report
- Count of archived and done ideas

**Step 3: Output a context-aware action menu**

Format the output as follows 鈥?only show sections that have something in them:

---

## 褰撳墠鍙搷浣?
**鈴?绛夊緟浣犵殑瀹℃煡锛坈heckpoint_pending = true锛?*
| Slug | Status | 鎺ㄨ崘涓嬩竴姝?|
|------|--------|----------|
| <slug> | explore | `/idea-next <slug>` 鎺ㄨ繘鍒扮爺绌堕棶棰橈紝鎴?`/idea-socratic <slug>` 鍏堢簿鐐?|
| <slug> | question | `/idea-challenge <slug>` 鍘嬪姏娴嬭瘯锛屾垨 `/idea-next <slug>` 杩涘叆鏁版嵁鎼滅储 |

**馃摑 杩涜涓紙鍙殢鏃舵搷浣滐級**
| Slug | Status | 鍙敤鍛戒护 |
|------|--------|---------|
| <slug> | capture | `/idea-socratic <slug>` / `/idea-next <slug>` |
| <slug> | data-search | `/idea-next <slug>` 涓嬭浇鏁版嵁 |

**鍏ㄥ眬鍛戒护锛堜换浣曟椂鍊欓兘鍙互鐢級**
- `/idea-new` 鈥?璁板綍涓€涓柊鐮旂┒鎯虫硶
- `/idea-status` 鈥?鍒锋柊鐪嬫澘瑙嗗浘
- `/idea-develop <slug>` 鈥?璺ㄨ鏂囨繁搴﹀彂灞曟煇涓兂娉?- `/idea-help` 鈥?鍐嶆鏌ョ湅鏈彍鍗?
**璁烘枃鐩稿叧**
- `/paper-done <slug>` 鈥?瀹屾垚璁烘枃闃呰鍚庣殑瀹屾暣瀵煎嚭娴佺▼锛堜篃鍙互鍛婅瘔 Trevor"鎴戜滑璇诲畬浜?鑷姩瑙﹀彂锛?- `/wiki-ingest` 鈥?灏嗘柊鏉ユ簮鎽勫叆鐭ヨ瘑缁村熀
- `/update-researcher-profile` 鈥?鍚屾鐮旂┒鑰呯敾鍍忥紙寤鸿鍦ㄦ柊浼氳瘽涓崟鐙繍琛岋級

---

**Token 鎴愭湰璇存槑**锛氭湰鍛戒护鍙 frontmatter cache锛屼笉璇讳换浣曟兂娉曞叏鏂囷紝token 娑堣€楁瀬浣庯紙绾?500-1000 tokens锛夈€?
Keep the output concise 鈥?no preamble, just the table and command list.

