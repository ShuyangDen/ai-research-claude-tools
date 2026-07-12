# Changelog

## 2.7.0 (2026-07-12)

### Stateful S2 literature review gate
- Added `/idea-s2-full` as the resumable Full S2 Gate workflow entry point.
- Added `/idea-s2-decide` for explicit human gate decisions before S3.
- Changed `/idea-next` into a transition guard: it no longer creates Full Gates ad hoc, and it only allows S3 after an authoritative `ADVANCE-S3` decision.
- Preserved `/idea-new` as capture-first with optional Quick Scan only; Quick Scan cannot certify novelty or write an S3 question.

### Literature-review capability foundations
- Upgraded the S2 sidecar template to schema v2 with gate phase, PKB-A/B passes, local retrieval manifest, known-item recall, relationship ledger, synthesis claim ledger, stopping certificate, and decision history.
- Added `system/literature_sources.yml` as a starter economics source registry for journal, working-paper, and field-specific frontier checks.
- Added safety addenda for `/paper-done`, `/wiki-ingest`, `/idea-socratic`, and `/idea-challenge` so new verified evidence marks linked active S2 gates dirty instead of silently changing decisions.

### Codex support
- Added Codex skills for `idea-s2-full` and `idea-s2-decide`.
- Synced updated Codex skills for `idea-new`, `idea-next`, `idea-revise`, `idea-status`, `paper-done`, `wiki-ingest`, `idea-socratic`, and `idea-challenge`.

### Security and packaging
- Removed literal personal identifiers from the installer security-scan example and replaced them with generic sensitive-pattern checks.
- Bumped package versions from 2.6.0 to 2.7.0.

### Migration from 2.6.x
- Copy the two new S2 commands and Codex skills during installation.
- Existing ideas, gates, researcher profiles, and source notes are not migrated in bulk; old gates should be upgraded lazily when they are resumed.

---
## 2.6.0 (2026-07-09)

### Selective rough-read archive
- Added **`/paper-rough-done <slug>`** for papers that were intentionally read only in selected modules.
- Rough-read archives preserve the selective focus, skipped sections, learner critiques, open questions, and a lightweight paper map without pretending the whole paper was mastered.
- Rough-read exports mark `reading_status: rough-read / selective read` and `idea_extraction: skipped` by default.
- `/paper-done` now routes rough-read/selective-read notes through the lightweight archive path while preserving the existing full paper pipeline for complete reads.
- Trevor and Codex paper-reading tutor now recognize Chinese natural-language rough-read archive triggers.

### Reading queue sync fixes
- `/sync-reading-queue` now formally supports Tier 1, Tier 2, and Tier 3.
- Completed rough-read papers are removed from the local and remote reading queue by slug as well as URL.
- GitHub API upload now uses UTF-8 no-BOM JSON on Windows to avoid JSON parse failures.
- Merge safety check now refuses to clear the queue if the merged result is empty.

### Codex support
- Added Codex-native `$paper-rough-done` skill.
- Updated `$paper-done`, `$paper-reading-tutor`, and `$sync-reading-queue` skills to match the v2.6 workflow.

### Migration (v2.5 -> v2.6)
- Install copies the new `paper-rough-done.md` command and Codex skill.
- AI Education local protocol files are overwritten as system files; user notes, exports, completed records, and reading history are preserved.

---
## 2.5.0 (2026-06-02)

### Codex support
- Added **one-command-one-skill Codex support** under `packages/codex/skills/`.
- Every AI Research Tools slash command now has a Codex skill copy, so Codex can run `$paper-done <slug>`, `$wiki-ingest`, `$idea-next <slug>`, and related workflows without reading `~/.claude/commands/` at runtime.
- Claude Code commands are preserved unchanged; Codex receives copied workflow skills.
- Added a Codex-native paper-reading-tutor skill for AI Education sessions, enforcing concept-first, paper-anchored Phase 1 reading with self-contained paper context before original-paper examples.

### Command packaging
- Formalized **`/idea-extract-from-source`** into `packages/idea-pipeline/commands/` and included it in the Codex command set.
- Added Codex versions of AI Education local commands: `ai-education-export` and `sync-reading-queue`.

### Installer updates
- INSTALL now installs Codex skills to `~/.codex/skills/` after Claude command installation.
- Generated usage guide now documents both Claude Code slash commands and Codex `$command` skill usage.
- Security scan coverage includes the new `packages/codex/` templates.

---

## 2.4.0 (2026-05-20)

### New commands
- **`/idea-socratic <slug>`** 鈥?5-layer Socratic dialogue to refine a raw idea before formalizing the RQ. Behavior-constraint driven (no role persona). Saves output to `## S1.5: Socratic Refinement` in the idea file.
- **`/idea-challenge <slug>`** 鈥?3-lens single-pass critical evaluation (Lens A: Methodology/ID, Lens B: Literature/Contribution, Lens C: Devil's Advocate). Context-aware next-step guidance after evaluation.
- **`/idea-help`** 鈥?State-aware command menu. Reads only `_frontmatter_cache.md` (~500 tokens). Shows what is actionable right now based on current pipeline state.

### LLM engineering fixes
- **`/idea-socratic`**: Removed role persona ("You are a senior economics professor...") 鈥?was counterproductive, competed with behavioral constraints. Replaced with direct behavior constraints. Removed `[Q:CLARIFY]`/`[Q:PROBE]`/`[Q:CHALLENGE]` internal labeling system (marked "internal, never show to user" but had no constraint effect on generation 鈥?decorative tokens). Added 15-turn progress checkpoints to prevent context loss in long dialogues.
- **`/idea-next`**: Removed raw `curl` of awesome-public-datasets README (~400 KB, causing severe attention dilution in data-search stage). Replaced with targeted knowledge-based recall. Added S1.5 awareness: if Socratic Refinement insights exist, uses them as basis for RQ formulation instead of re-deriving from scratch.
- **`/idea-new`**: Fixed: was auto-running S2 literature exploration by default. Now defaults to capture-only. User must explicitly choose explore. Added hard cap (max 5 papers / 3 gaps) when explore is chosen.
- **`/paper-done`**: Added next-step guidance block in Chinese (Phase 5). Added natural language trigger note for Trevor integration.

### Discoverability
- Every command now shows next-step guidance in Chinese after completing, so users know what to run next without memorizing the command list.
- Trevor (`ai-education/CLAUDE.md`) now states the current actionable item after greeting (mid-paper / finished but not exported / no paper in progress).
- Trevor recognizes natural language triggers like "鎴戜滑璇诲畬浜?, "浠婂ぉ灏卞埌杩欓噷", "paper done" and runs `/paper-done <slug>` automatically 鈥?users never need to type the exact slash command.

### Template & vault updates
- **`_template.md`**: Added `## S1.5: Socratic Refinement` and `## Challenge Panel Findings` placeholder sections.
- **Vault `CLAUDE.md`**: Added S1.5 and Challenge Panel operation rules. Added new log tag formats: `[IDEA-SOCRATIC]`, `[IDEA-CHALLENGE]`, `[IDEA-EXTRACT]`. Fixed awesome-public-datasets curl instruction.

### Acknowledgements
Parts of v2.4 鈥?specifically the Socratic questioning structure in `/idea-socratic` and the Devil's Advocate challenge pattern in `/idea-challenge` 鈥?were inspired by the [academic-research-skills](https://github.com/Imbad0202/academic-research-skills) plugin by Cheng-I Wu ([@Imbad0202](https://github.com/Imbad0202)).

### Migration (v2.3 鈫?v2.4) 鈥?handled automatically by INSTALL.md
- 3 new commands copied to `HOME\.claude\commands\`: `idea-socratic.md`, `idea-challenge.md`, `idea-help.md`
- `idea-new.md`, `idea-next.md`, `paper-done.md` overwritten (system files)
- `ai-education/CLAUDE.md` overwritten (system file)

---

## 2.3.0 (2026-05-19)

### Performance: progressive disclosure overhaul

**`/paper-done` 鈥?鏄捐憲鎻愰€燂紝鍑忓皯鏃犳晥 token 娑堣€?*
- Phase 1b锛氫笉鍐嶅姞杞藉畬鏁?`researcher_profile.md`锛屾敼涓哄彧璇?`## Active Research Directions` 鍗曡妭锛堜粠鍏ㄦ枃 ~3 KB 闄嶈嚦 ~300 token锛?
- Phase 2 (wiki ingest)锛氭敼涓哄畾鍚戝崟绡囨ā寮忊€斺€旂洿鎺ヤ娇鐢?Phase 1 鐨勫唴瀛樺唴瀹癸紝涓嶉噸鏂拌纾佺洏锛屼笉鏋氫妇 `sources/` 鐩綍锛涙部鐢?v2.2 鐨?skip-aware 閫昏緫锛堜粎鍦ㄦ湁鏂板唴瀹规椂鏇存柊 wiki 椤甸潰锛?
- Phase 3 (idea extraction)锛氫娇鐢?`ideas/_profile_cache.json` 鍋氬垵姝ヨ瘎鍒嗭紝鍙湁纭鎵ц鐨?Category A idea 鎵嶈鍏跺畬鏁存枃浠讹紝寤惰繜鍒?Phase 4锛涙部鐢?v2.2 鐨?auto-execute锛堟棤 Category B 鏃舵棤闇€鐢ㄦ埛纭锛?
- Phase 4 (researcher profile sync)锛氭潯浠惰Е鍙戯紝浠呭湪浠ヤ笅浠讳竴鏉′欢婊¤冻鏃惰繍琛岋細鈶?Phase 4 鍒涘缓浜嗘柊 idea锛圕ategory B锛夛紱鈶?`researcher_profile.md` 涓婃鏇存柊瓒呰繃 7 澶┿€傚叾浣欐儏鍐佃烦杩囧苟鍛婄煡鐢ㄦ埛

**`/idea-develop` 鈥?澶у箙鍑忓皯 paper notes 鍔犺浇閲?*
- Step 3 鏀逛负涓ゅ眰鍔犺浇锛氶粯璁や紭鍏堝姞杞?`sources/<slug>.md`锛堝帇缂╁鍑虹増锛寏1 KB锛夛紝鍥為€€鍒?`papers/notes/<slug>.md` 闇€鐢ㄦ埛鏄庣‘瑙﹀彂锛堣闂暟瀛︽帹瀵笺€丳hase 1/2 缁嗚妭绛夛級
- 鍏稿瀷浼氳瘽浠庡姞杞?10鈥?0 KB 鍘熷绗旇闄嶈嚦 3鈥? KB 鍘嬬缉鐗?

### Architecture: raw vs. compressed separation

- `papers/notes/<slug>.md`锛堝師濮?tutor 绗旇锛変笌 `sources/<slug>.md`锛堝帇缂╁鍑虹増锛夌殑鍒嗙鍘熷垯鐜板凡璐┛鎵€鏈夊懡浠わ細`/paper-done` 鍜?`/idea-develop` 鍧囦紭鍏堜娇鐢ㄥ帇缂╃増锛屽師濮嬫枃浠舵寜闇€鍔犺浇

### Migration (v2.2 鈫?v2.3) 鈥?handled automatically by INSTALL.md
- `paper-done.md` and `idea-develop.md` in `HOME\.claude\commands\` are overwritten (system files)

---

## 2.2.0 (2026-05-16)

### New features
- **Skip-aware `/paper-done` pipeline** 鈥?phases 2, 3, and 4 now check necessity before acting:
  - Phase 2 (wiki ingest): skips updating existing wiki pages if this paper adds no genuinely new content; still logs the ingest
  - Phase 3 (idea extraction): auto-executes without pausing when all candidates are Category A or C (append/skip); only stops for user confirmation when at least one Category B (new idea) is proposed
  - Phase 4 (researcher profile sync): skips `update-researcher-profile` if only evidence bullets were appended 鈥?no new ideas created, no status changes
- **Skip-aware `/update-researcher-profile`** 鈥?new Step 3b: after reading changed files, checks if `title`, `status`, or `description` changed; if only `updated:` frontmatter changed, skips the paper_tracker copy and git push entirely

### Migration (v2.1 鈫?v2.2) 鈥?handled automatically by INSTALL.md
- `paper-done.md` and `update-researcher-profile.md` in `HOME\.claude\commands\` are overwritten (system files)

---

## 2.1.0 (2026-05-15)

### New features
- **Reading queue sync** 鈥?paper-tracker now writes `reading_queue.md` to its GitHub repo after every weekly run; AI_education can pull and merge this list via `/sync-reading-queue`
- `/sync-reading-queue` 鈥?new slash command in AI_education: fetches the latest reading queue from the paper-tracker GitHub repo, removes already-completed papers, merges new ones (Tier 1 first), writes back to both local `papers/reading_queue.md` and the remote repo so both machines stay in sync
- **Abstract translation fix** 鈥?Chinese digest email now correctly translates abstract text inside blockquotes (previously left in English)

### Setup changes
- `gh` CLI required for `/sync-reading-queue`; INSTALL.md Step 5e now auto-configures `PAPER_TRACKER_REPO` in `machine_paths.md` and installs the command into AI_education

### Migration (v2.0 鈫?v2.1) 鈥?handled automatically by INSTALL.md
- `/sync-reading-queue` command copied to `AI_EDUCATION_PATH\.claude\commands\`
- `PAPER_TRACKER_REPO` line added to `machine_paths.md` (existing content untouched)
- Requires `gh auth login` on each machine

---

## 2.0.0 (2026-05-11)

### New features
- **Projects system** 鈥?third Obsidian vault (`projects/`) for tracking ongoing research projects
- `/project-init` 鈥?initialize tracking for a project folder (file map, change log, Zotero collection, feedback recording)
- `/project-sync` 鈥?detect file changes, update project map and change log
- `/project-status` 鈥?progressive context loading for project discussion; handles feedback recording and paper-to-Zotero inline
- `/paper-done` 鈥?full post-session pipeline: export notes 鈫?wiki ingest 鈫?idea extraction 鈫?researcher profile sync (replaces 4 separate manual steps)
- `/idea-develop` 鈥?load targeted cross-system context (relevant papers + related ideas + researcher profile) for deep idea work
- `/idea-retrospective` 鈥?generate a LaTeX/PDF retrospective document of an idea's intellectual journey for a PhD advisor

### Researcher profile improvements
- `## Active Projects` section added 鈥?auto-updated by `/project-sync` after each sync
- Active Research Directions now include pipeline stage annotations
- Incremental mtime-based cache in `/update-researcher-profile` 鈥?only re-reads modified idea files

### System improvements
- `tutor/paper_notes.md` is now an index file; per-paper notes live in `papers/notes/<slug>.md`
- `tutor/context_snapshot.md` no longer contains the full completed papers list 鈥?moved to `tutor/completed_papers.md`
- `tutor/idea_seeds.md` cleanup 鈥?no more raw candidate accumulation
- Bug fix: `tutor/system.md` Phase 3 Critical Thinking protocol now correctly references `papers/notes/<slug>.md` (not `tutor/paper_notes.md`)

### Migration (v1 鈫?v2) 鈥?handled automatically by INSTALL.md
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
