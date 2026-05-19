# Changelog

## 2.3.0 (2026-05-19)

### Performance: progressive disclosure overhaul

**`/paper-done` — 显著提速，减少无效 token 消耗**
- Phase 1b：不再加载完整 `researcher_profile.md`，改为只读 `## Active Research Directions` 单节（从全文 ~3 KB 降至 ~300 token）
- Phase 2 (wiki ingest)：改为定向单篇模式——直接使用 Phase 1 的内存内容，不重新读磁盘，不枚举 `sources/` 目录；沿用 v2.2 的 skip-aware 逻辑（仅在有新内容时更新 wiki 页面）
- Phase 3 (idea extraction)：使用 `ideas/_profile_cache.json` 做初步评分，只有确认执行的 Category A idea 才读其完整文件，延迟到 Phase 4；沿用 v2.2 的 auto-execute（无 Category B 时无需用户确认）
- Phase 4 (researcher profile sync)：条件触发，仅在以下任一条件满足时运行：① Phase 4 创建了新 idea（Category B）；② `researcher_profile.md` 上次更新超过 7 天。其余情况跳过并告知用户

**`/idea-develop` — 大幅减少 paper notes 加载量**
- Step 3 改为两层加载：默认优先加载 `sources/<slug>.md`（压缩导出版，~1 KB），回退到 `papers/notes/<slug>.md` 需用户明确触发（询问数学推导、Phase 1/2 细节等）
- 典型会话从加载 10–30 KB 原始笔记降至 3–6 KB 压缩版

### Architecture: raw vs. compressed separation

- `papers/notes/<slug>.md`（原始 tutor 笔记）与 `sources/<slug>.md`（压缩导出版）的分离原则现已贯穿所有命令：`/paper-done` 和 `/idea-develop` 均优先使用压缩版，原始文件按需加载

### Migration (v2.2 → v2.3) — handled automatically by INSTALL.md
- `paper-done.md` and `idea-develop.md` in `HOME\.claude\commands\` are overwritten (system files)

---

## 2.2.0 (2026-05-16)

### New features
- **Skip-aware `/paper-done` pipeline** — phases 2, 3, and 4 now check necessity before acting:
  - Phase 2 (wiki ingest): skips updating existing wiki pages if this paper adds no genuinely new content; still logs the ingest
  - Phase 3 (idea extraction): auto-executes without pausing when all candidates are Category A or C (append/skip); only stops for user confirmation when at least one Category B (new idea) is proposed
  - Phase 4 (researcher profile sync): skips `update-researcher-profile` if only evidence bullets were appended — no new ideas created, no status changes
- **Skip-aware `/update-researcher-profile`** — new Step 3b: after reading changed files, checks if `title`, `status`, or `description` changed; if only `updated:` frontmatter changed, skips the paper_tracker copy and git push entirely

### Migration (v2.1 → v2.2) — handled automatically by INSTALL.md
- `paper-done.md` and `update-researcher-profile.md` in `HOME\.claude\commands\` are overwritten (system files)

---

## 2.1.0 (2026-05-15)

### New features
- **Reading queue sync** — paper-tracker now writes `reading_queue.md` to its GitHub repo after every weekly run; AI_education can pull and merge this list via `/sync-reading-queue`
- `/sync-reading-queue` — new slash command in AI_education: fetches the latest reading queue from the paper-tracker GitHub repo, removes already-completed papers, merges new ones (Tier 1 first), writes back to both local `papers/reading_queue.md` and the remote repo so both machines stay in sync
- **Abstract translation fix** — Chinese digest email now correctly translates abstract text inside blockquotes (previously left in English)

### Setup changes
- `gh` CLI required for `/sync-reading-queue`; INSTALL.md Step 5e now auto-configures `PAPER_TRACKER_REPO` in `machine_paths.md` and installs the command into AI_education

### Migration (v2.0 → v2.1) — handled automatically by INSTALL.md
- `/sync-reading-queue` command copied to `AI_EDUCATION_PATH\.claude\commands\`
- `PAPER_TRACKER_REPO` line added to `machine_paths.md` (existing content untouched)
- Requires `gh auth login` on each machine

---

## 2.0.0 (2026-05-11)

### New features
- **Projects system** — third Obsidian vault (`projects/`) for tracking ongoing research projects
- `/project-init` — initialize tracking for a project folder (file map, change log, Zotero collection, feedback recording)
- `/project-sync` — detect file changes, update project map and change log
- `/project-status` — progressive context loading for project discussion; handles feedback recording and paper-to-Zotero inline
- `/paper-done` — full post-session pipeline: export notes → wiki ingest → idea extraction → researcher profile sync (replaces 4 separate manual steps)
- `/idea-develop` — load targeted cross-system context (relevant papers + related ideas + researcher profile) for deep idea work
- `/idea-retrospective` — generate a LaTeX/PDF retrospective document of an idea's intellectual journey for a PhD advisor

### Researcher profile improvements
- `## Active Projects` section added — auto-updated by `/project-sync` after each sync
- Active Research Directions now include pipeline stage annotations
- Incremental mtime-based cache in `/update-researcher-profile` — only re-reads modified idea files

### System improvements
- `tutor/paper_notes.md` is now an index file; per-paper notes live in `papers/notes/<slug>.md`
- `tutor/context_snapshot.md` no longer contains the full completed papers list — moved to `tutor/completed_papers.md`
- `tutor/idea_seeds.md` cleanup — no more raw candidate accumulation
- Bug fix: `tutor/system.md` Phase 3 Critical Thinking protocol now correctly references `papers/notes/<slug>.md` (not `tutor/paper_notes.md`)

### Migration (v1 → v2) — handled automatically by INSTALL.md
- `tutor/paper_notes.md` auto-split into per-paper files in `papers/notes/` (with user confirmation and .bak backup)
- `machine_paths.md` gets new `## Paper Tracker` and `## Projects` sections appended
- `zotero/config.json` gets `project_collections: {}` field appended (api_key and idea_collections preserved)
- `researcher_profile.md` gets `## Active Projects` section appended (existing content untouched)

---

## 1.0.0 (2026-02-05)

Initial release. Three systems:
- ai-education: Socratic paper tutor with Trevor/Mira personas
- idea-pipeline: Research idea pipeline (6 stages) + personal knowledge wiki + 8 global commands
- paper-tracker: Automated weekly economics paper digest via GitHub Actions

### v1 command set (8 commands)
`/idea-new`, `/idea-next`, `/idea-revise`, `/idea-status`, `/idea-archive`, `/idea-zotero-add`, `/wiki-ingest`, `/update-researcher-profile`
