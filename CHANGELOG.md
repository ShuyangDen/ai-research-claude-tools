# Changelog

## 2.4.0 (2026-05-20)

### New commands
- **`/idea-socratic <slug>`** — 5-layer Socratic dialogue to refine a raw idea before formalizing the RQ. Behavior-constraint driven (no role persona). Saves output to `## S1.5: Socratic Refinement` in the idea file.
- **`/idea-challenge <slug>`** — 3-lens single-pass critical evaluation (Lens A: Methodology/ID, Lens B: Literature/Contribution, Lens C: Devil's Advocate). Context-aware next-step guidance after evaluation.
- **`/idea-help`** — State-aware command menu. Reads only `_frontmatter_cache.md` (~500 tokens). Shows what is actionable right now based on current pipeline state.

### LLM engineering fixes
- **`/idea-socratic`**: Removed role persona ("You are a senior economics professor...") — was counterproductive, competed with behavioral constraints. Replaced with direct behavior constraints. Removed `[Q:CLARIFY]`/`[Q:PROBE]`/`[Q:CHALLENGE]` internal labeling system (marked "internal, never show to user" but had no constraint effect on generation — decorative tokens). Added 15-turn progress checkpoints to prevent context loss in long dialogues.
- **`/idea-next`**: Removed raw `curl` of awesome-public-datasets README (~400 KB, causing severe attention dilution in data-search stage). Replaced with targeted knowledge-based recall. Added S1.5 awareness: if Socratic Refinement insights exist, uses them as basis for RQ formulation instead of re-deriving from scratch.
- **`/idea-new`**: Fixed: was auto-running S2 literature exploration by default. Now defaults to capture-only. User must explicitly choose explore. Added hard cap (max 5 papers / 3 gaps) when explore is chosen.
- **`/paper-done`**: Added next-step guidance block in Chinese (Phase 5). Added natural language trigger note for Trevor integration.

### Discoverability
- Every command now shows next-step guidance in Chinese after completing, so users know what to run next without memorizing the command list.
- Trevor (`ai-education/CLAUDE.md`) now states the current actionable item after greeting (mid-paper / finished but not exported / no paper in progress).
- Trevor recognizes natural language triggers like "我们读完了", "今天就到这里", "paper done" and runs `/paper-done <slug>` automatically — users never need to type the exact slash command.

### Template & vault updates
- **`_template.md`**: Added `## S1.5: Socratic Refinement` and `## Challenge Panel Findings` placeholder sections.
- **Vault `CLAUDE.md`**: Added S1.5 and Challenge Panel operation rules. Added new log tag formats: `[IDEA-SOCRATIC]`, `[IDEA-CHALLENGE]`, `[IDEA-EXTRACT]`. Fixed awesome-public-datasets curl instruction.

### Acknowledgements
Parts of v2.4 — specifically the Socratic questioning structure in `/idea-socratic` and the Devil's Advocate challenge pattern in `/idea-challenge` — were inspired by the [academic-research-skills](https://github.com/Imbad0202/academic-research-skills) plugin by Cheng-I Wu ([@Imbad0202](https://github.com/Imbad0202)).

### Migration (v2.3 → v2.4) — handled automatically by INSTALL.md
- 3 new commands copied to `HOME\.claude\commands\`: `idea-socratic.md`, `idea-challenge.md`, `idea-help.md`
- `idea-new.md`, `idea-next.md`, `paper-done.md` overwritten (system files)
- `ai-education/CLAUDE.md` overwritten (system file)

---

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
