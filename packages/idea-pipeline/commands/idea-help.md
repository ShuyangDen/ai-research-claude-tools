Show what actions are available right now, based on the current state of the idea pipeline.

**Step 0: Read machine config**
Read `~/.claude/machine_paths.md` → vault path (under "Research Idea Pipeline → Vault").

**Step 1: Read cache only (do NOT open individual idea files)**
Read `ideas/_frontmatter_cache.md`. If missing or empty, read only the frontmatter blocks from each idea file to rebuild it.

**Step 2: Compute current state**
From the cache, identify:
- Ideas with `checkpoint_pending: true` (waiting for your action)
- Ideas by status: capture / explore / question / data-search / data-prep / report
- Count of archived and done ideas

**Step 3: Output a context-aware action menu**

Format the output as follows — only show sections that have something in them:

---

## 当前可操作

**⏳ 等待你的审查（checkpoint_pending = true）**
| Slug | Status | 推荐下一步 |
|------|--------|----------|
| <slug> | explore | `/idea-next <slug>` 推进到研究问题，或 `/idea-socratic <slug>` 先精炼 |
| <slug> | question | `/idea-challenge <slug>` 压力测试，或 `/idea-next <slug>` 进入数据搜索 |

**📝 进行中（可随时操作）**
| Slug | Status | 可用命令 |
|------|--------|---------|
| <slug> | capture | `/idea-socratic <slug>` / `/idea-next <slug>` |
| <slug> | data-search | `/idea-next <slug>` 下载数据 |

**全局命令（任何时候都可以用）**
- `/idea-new` — 记录一个新研究想法
- `/idea-status` — 刷新看板视图
- `/idea-develop <slug>` — 跨论文深度发展某个想法
- `/idea-help` — 再次查看本菜单

**论文相关**
- `/paper-done <slug>` — 完成论文阅读后的完整导出流程（也可以告诉 Trevor"我们读完了"自动触发）
- `/wiki-ingest` — 将新来源摄入知识维基
- `/update-researcher-profile` — 同步研究者画像（建议在新会话中单独运行）

---

**Token 成本说明**：本命令只读 frontmatter cache，不读任何想法全文，token 消耗极低（约 500-1000 tokens）。

Keep the output concise — no preamble, just the table and command list.
