# AI Research Tools — Master Installer

You are Claude Code running an installation script. Follow these steps carefully and interactively. Do not skip steps, do not preload all files at once — work through each step sequentially.

---

## Step 0 — Security Scan (BLOCKING — do this before anything else)

Search all `.md` and `.json` files under `packages/` for personal information that should have been removed. Run this grep:

```bash
grep -rn --include="*.md" --include="*.json" \
  -e "Binghamton" -e "Deng Shuyang" -e "dengshuyang" \
  -e "Pi9n5fNt7eHE5WQ03Eq7dCJ0" \
  -e "dengshuyang125@gmail" \
  -e "9851109" \
  -e "E:\\\\obsidian" \
  packages/
```

Also check for non-placeholder Windows user paths:
```bash
grep -rn --include="*.md" --include="*.json" -P "(?<!\{)[A-Z]:\\\\Users\\\\[^<{]" packages/
```

**If any matches are found**: List the file paths and line numbers. Stop installation and tell the user: "Personal information detected in template files — please review before sharing." Do NOT continue until the user explicitly says to proceed.

**If no matches**: Report "Security scan passed." and continue to Step 1.

---

## Step 1 — Detect Installation State

Check in order, take the first matching case:

### Case A — v2+ user (has version marker)
Check if `~/.claude/.ai-tools-version` exists. If yes: read it, extract version number, proceed to **Step 1A**.

### Case B — v1 user (old install, no version marker)
Check all three conditions:
1. `~/.claude/commands/idea-new.md` exists
2. `~/.claude/commands/paper-done.md` does NOT exist
3. `~/.claude/machine_paths.md` exists

If all three true: this is a v1 user. Proceed to **Step 1B**.

### Case C — Fresh install
Neither A nor B. Proceed to **Step 1C**.

---

### Step 1A — v2+ Migration

Tell user: "Detected existing v2.x installation. Current version: [version]. Upgrading to 2.0.0."

Read `CHANGELOG.md` and show the relevant upgrade notes. Ask user to confirm before proceeding to Step 2.

### Step 1B — v1 Migration

Tell user (in Chinese if the user appears to be Chinese-speaking, English otherwise):

"检测到 v1 安装（无版本标记）。将进行 v1→v2 迁移：
- 系统文件（commands、CLAUDE.md、system.md）将被覆盖（这些是纯代码文件，不含你的内容）
- 用户数据（你的想法文件、paper notes、learner profile）完全保留
- 新增：projects 系统、/paper-done 命令、/idea-develop 命令
请确认继续（输入 yes）"

Wait for confirmation. Do not proceed until user confirms.

### Step 1C — Fresh Install

Tell user: "No previous installation detected. Will perform fresh install of all three packages:
1. ai-education (Socratic paper tutor)
2. idea-pipeline (research idea management + 14 commands + 3 Obsidian vaults)
3. paper-tracker (weekly paper digest via GitHub Actions)

Each package can be used independently. Confirm to continue."

Wait for confirmation.

---

## Step 2 — Collect Paths (Interactive)

### For Fresh Install — ask all paths:

Ask the user for each path one at a time. Use their answers verbatim — do not guess or infer:

1. **Obsidian root folder** (parent of all 3 vaults):
   "Where should the 3 Obsidian vaults be created? (e.g., C:\Users\you\obsidian or D:\research\obsidian)"
   → Store as `OBSIDIAN_ROOT`

2. **AI Education project folder** (new or existing):
   "Where should the AI Education tutor project live? (e.g., C:\Users\you\AI_education)"
   → Store as `AI_EDUCATION_PATH`

3. **Paper tracker folder** (where to clone/put the paper tracker):
   "Where should the paper tracker live? (e.g., C:\Users\you\paper-tracker)"
   → Store as `PAPER_TRACKER_PATH`

4. **Zotero credentials** (optional — user can skip):
   "Do you use Zotero for reference management? (yes/no/skip)"
   If yes: ask for API key → `ZOTERO_API_KEY` and user ID → `ZOTERO_USER_ID`
   If skip: use placeholder values `<YOUR_ZOTERO_API_KEY>` and `<YOUR_ZOTERO_USER_ID>`

5. **Home directory** — detect automatically:
   Run `python -c "import os; print(os.path.expanduser('~'))"` and store as `HOME`

### For v1/v2 Migration — read existing paths first:

1. Read `~/.claude/machine_paths.md` — extract existing paths (Obsidian root, AI Education path)
2. Show user: "I found these existing paths: [list them]. Are these still correct? (yes/no)"
3. If yes: reuse them
4. If no: ask for corrections
5. Ask only for NEW paths: "Projects vault is new in v2. Where should it be? Under [OBSIDIAN_ROOT]\projects? (yes/no, or enter a different path)"

After collecting all paths, show a summary table and ask: "Proceed with these paths? (yes/no)"

---

## Step 3 — Install idea-pipeline (install this first; other packages depend on it)

### 3a. Create Obsidian vault directories

Check if each directory exists. If not, create it:
- `OBSIDIAN_ROOT\JMP Idea\`
- `OBSIDIAN_ROOT\JMP Idea\ideas\`
- `OBSIDIAN_ROOT\personal knowledge skill\`
- `OBSIDIAN_ROOT\personal knowledge skill\sources\`
- `OBSIDIAN_ROOT\personal knowledge skill\wiki\`
- `OBSIDIAN_ROOT\projects\`

### 3b. Copy vault template files

**For each file, replace `{{OBSIDIAN_ROOT}}`, `{{AI_EDUCATION_PATH}}`, `{{HOME}}`, `{{PAPER_TRACKER_PATH}}`, `{{INSTALL_DATE}}` with the actual collected values before writing.**

Copy these files (system files — always overwrite for v1/v2 migration):
- `packages/idea-pipeline/obsidian/JMP Idea/CLAUDE.md` → `OBSIDIAN_ROOT\JMP Idea\CLAUDE.md`
- `packages/idea-pipeline/obsidian/JMP Idea/AGENTS.md` → `OBSIDIAN_ROOT\JMP Idea\AGENTS.md`
- `packages/idea-pipeline/obsidian/personal knowledge skill/CLAUDE.md` → `OBSIDIAN_ROOT\personal knowledge skill\CLAUDE.md`
- `packages/idea-pipeline/obsidian/personal knowledge skill/AGENTS.md` → `OBSIDIAN_ROOT\personal knowledge skill\AGENTS.md`

Copy these skeleton files (create only if not already present — never overwrite for migration):
- `packages/idea-pipeline/obsidian/JMP Idea/ideas/index.md` → `OBSIDIAN_ROOT\JMP Idea\ideas\index.md`
- `packages/idea-pipeline/obsidian/JMP Idea/ideas/log.md` → `OBSIDIAN_ROOT\JMP Idea\ideas\log.md`
- `packages/idea-pipeline/obsidian/JMP Idea/ideas/_template.md` → `OBSIDIAN_ROOT\JMP Idea\ideas\_template.md` (overwrite: template is a system file)
- `packages/idea-pipeline/obsidian/JMP Idea/ideas/_frontmatter_cache.md` → `OBSIDIAN_ROOT\JMP Idea\ideas\_frontmatter_cache.md` (create only)
- `packages/idea-pipeline/obsidian/personal knowledge skill/wiki/index.md` → create only
- `packages/idea-pipeline/obsidian/personal knowledge skill/wiki/log.md` → create only
- `packages/idea-pipeline/obsidian/projects/index.md` → create only
- `packages/idea-pipeline/obsidian/projects/log.md` → create only

**researcher_profile.md — special handling:**
Check if `OBSIDIAN_ROOT\JMP Idea\researcher_profile.md` exists:
- If it does NOT exist: copy template, replace `{{INSTALL_DATE}}` with today's date
- If it DOES exist: check if `## Active Projects` section is present
  - If missing: append the `## Active Projects` section from the template between Active Research Directions and What This Researcher Does NOT Care About
  - If present: leave researcher_profile.md completely untouched

### 3c. Install global commands

Copy all 15 files from `packages/idea-pipeline/commands/` to `HOME\.claude\commands\` (always overwrite — these are pure system files):
- idea-archive.md, idea-develop.md, idea-new.md, idea-next.md
- idea-retrospective.md, idea-revise.md, idea-status.md, idea-zotero-add.md
- wiki-ingest.md, update-researcher-profile.md, paper-done.md
- project-init.md, project-sync.md, project-status.md
- research-present.md

**Before writing each command file**: replace `{{AI_EDUCATION_PATH}}` and `{{OBSIDIAN_ROOT}}` with actual values.

### 3d. Install rules

Copy all files from `packages/idea-pipeline/config/rules/` to `HOME\.claude\rules\` (always overwrite).

### 3e. Install machine_paths.md

Read `packages/idea-pipeline/config/machine_paths.md`. Replace all `{{VARIABLE}}` placeholders with actual values. Write to `HOME\.claude\machine_paths.md`.

**For v1/v2 migration**: If `HOME\.claude\machine_paths.md` already exists, merge:
1. Read the existing file
2. Check which sections are present
3. Only add sections that are missing (e.g., add `## Paper Tracker` if not present)
4. Do NOT overwrite sections that already have real paths

### 3f. Install Zotero config

**Fresh install**: Copy `packages/idea-pipeline/config/zotero/config.json` to `HOME\.claude\zotero\config.json`. Replace `<YOUR_ZOTERO_API_KEY>` and `<YOUR_ZOTERO_USER_ID>` with collected values (or placeholders if user skipped).

**v1/v2 migration**: If config already exists:
1. Read existing config — preserve api_key, user_id, idea_collections
2. Add `"project_collections": {}` if that field is missing
3. Write merged result back

---

## Step 4 — Install ai-education

### 4a. Check/create AI Education directory

If `AI_EDUCATION_PATH` does not exist: create it.

Create subdirectories if missing:
- `papers\`, `papers\notes\`, `papers\pdfs\`, `papers\text\`
- `textbooks\`, `textbooks\scripts\`
- `tutor\`

### 4b. Copy system files (always overwrite)

**Before writing**: replace `{{OBSIDIAN_ROOT}}` and `{{HOME}}` in each file.

- `packages/ai-education/CLAUDE.md` → `AI_EDUCATION_PATH\CLAUDE.md`
- `packages/ai-education/AGENTS.md` → `AI_EDUCATION_PATH\AGENTS.md`
- `packages/ai-education/tutor/system.md` → `AI_EDUCATION_PATH\tutor\system.md`
- `packages/ai-education/tutor/trevor.md` → `AI_EDUCATION_PATH\tutor\trevor.md`
- `packages/ai-education/tutor/mira.md` → `AI_EDUCATION_PATH\tutor\mira.md`

### 4c. Copy scripts (always overwrite — no personal info)

- `packages/ai-education/textbooks/scripts/extract_toc.py` → `AI_EDUCATION_PATH\textbooks\scripts\extract_toc.py`
- `packages/ai-education/textbooks/scripts/read_pages.py` → `AI_EDUCATION_PATH\textbooks\scripts\read_pages.py`
- `packages/ai-education/textbooks/README.md` → `AI_EDUCATION_PATH\textbooks\README.md` (create only)

### 4d. Copy skeleton files (create only — never overwrite)

- `packages/ai-education/papers/index.md` → `AI_EDUCATION_PATH\papers\index.md`
- `packages/ai-education/papers/reading_queue.md` → `AI_EDUCATION_PATH\papers\reading_queue.md`
- `packages/ai-education/tutor/context_snapshot.md` → `AI_EDUCATION_PATH\tutor\context_snapshot.md`
- `packages/ai-education/tutor/completed_papers.md` → `AI_EDUCATION_PATH\tutor\completed_papers.md`
- `packages/ai-education/tutor/idea_seeds.md` → `AI_EDUCATION_PATH\tutor\idea_seeds.md`
- `packages/ai-education/tutor/paper_notes.md` → `AI_EDUCATION_PATH\tutor\paper_notes.md`
- `packages/ai-education/tutor/progress.md` → `AI_EDUCATION_PATH\tutor\progress.md`
- `packages/ai-education/tutor/math_gaps.md` → `AI_EDUCATION_PATH\tutor\math_gaps.md`
- `packages/ai-education/tutor/learner_profile.md` → `AI_EDUCATION_PATH\tutor\learner_profile.md` (create only — user data)

### 4e — v1 Migration: paper_notes.md Split

**Only for v1 migration.** Check if `AI_EDUCATION_PATH\tutor\paper_notes.md` exists and has more than 50 lines of actual content (not just the index header).

If the file is a monolithic notes file (not the index format), auto-split it:

1. Read `AI_EDUCATION_PATH\tutor\paper_notes.md`
2. Parse into sections by `## ` or `# ` heading (each heading = one paper)
3. For each section:
   - Generate a candidate slug from the heading (lowercase, spaces → hyphens, remove special chars)
   - Check if `AI_EDUCATION_PATH\papers\notes\<slug>.md` already exists
4. Show a proposal table and STOP — wait for user:
   ```
   ## paper_notes.md Split Proposal
   
   | Paper heading | Candidate slug | Action |
   |---------------|----------------|--------|
   | Automation and Polarization | automation-polarization | Create papers/notes/automation-polarization.md |
   | Faridani 2025 | faridani-2025 | Skip (papers/notes/faridani-2025.md already exists) |
   ```
   Say: "I found [N] paper sections in paper_notes.md. Reply **confirm** to split them, **revise** to change a slug (e.g., 'revise #2 → new-slug'), or **skip** to leave paper_notes.md as-is."

5. After confirmation:
   - For each "Create" action: write the section content to `papers/notes/<slug>.md`
   - Backup original: rename `paper_notes.md` to `paper_notes.md.bak`
   - Overwrite `paper_notes.md` with the index template from `packages/ai-education/tutor/paper_notes.md`
   - Report: "Split complete. [N] notes files created. Original backed up as paper_notes.md.bak."

6. If user chose "skip": leave paper_notes.md as-is. Tell user they can run this migration manually later.

---

## Step 5 — Install paper-tracker

### 5a. Create paper tracker directory

If `PAPER_TRACKER_PATH` does not exist: create it.

### 5b. Copy paper tracker files (overwrite all — these are system files)

Copy all files from `packages/paper-tracker/` to `PAPER_TRACKER_PATH\`:
- All Python scripts (paperextract.py, paperextract_cn.py, utils_pdf_email.py, run_weekly_digest.py)
- requirements.txt
- .github/workflows/weekly_paper_digest.yml
- README.md, SETUP.md, and all documentation .md files

### 5c. Install researcher_profile.md (create only)

If `PAPER_TRACKER_PATH\researcher_profile.md` does NOT exist: copy from template (replace `{{INSTALL_DATE}}`).
If it DOES exist: leave it untouched.

### 5d. Initialize git repo

If `PAPER_TRACKER_PATH` is not already a git repo:
```bash
cd <PAPER_TRACKER_PATH>
git init
git add .
git commit -m "feat: initial paper tracker setup"
```

Tell user: "Now push this to a GitHub repo and configure 4 GitHub Secrets. See PAPER_TRACKER_PATH\SETUP.md for full instructions."

### 5e. Configure GitHub CLI for /sync-reading-queue

This step enables the `/sync-reading-queue` command in AI_education, which syncs the paper tracker's reading queue to the local project. It requires `gh` CLI.

**Check if gh is installed:**
```bash
gh --version
```

If the command is not found, tell the user:
"GitHub CLI (`gh`) is not installed. Please install it from https://cli.github.com, then run `gh auth login`. After that, re-open Claude Code here to continue — or skip this step and do it later."

Wait for the user to confirm gh is installed before continuing.

**Check if gh is authenticated:**
```bash
gh auth status
```

If not authenticated, tell the user to run `gh auth login` and wait for confirmation.

**Add PAPER_TRACKER_REPO to machine_paths.md:**

Read `HOME\.claude\machine_paths.md`. If a `PAPER_TRACKER_REPO` line is not already present under `## Paper Tracker`, add it:

```markdown
- **PAPER_TRACKER_REPO**: `<GITHUB_USERNAME>/ai-economics-paper-tracker`
```

To find `GITHUB_USERNAME`, run:
```bash
gh api user --jq '.login'
```

Use the result as the GitHub username. The repo name is always `ai-economics-paper-tracker` (or whatever the user named it when pushing in step 5d).

**Install the /sync-reading-queue command into AI_education:**

Copy `packages/ai-education/commands/sync-reading-queue.md` → `AI_EDUCATION_PATH\.claude\commands\sync-reading-queue.md` (always overwrite — this is a system file).

Tell user: "`/sync-reading-queue` is now available in your AI_education project. Run it after each weekly digest to pull new papers into your reading queue."

---

## Step 6 — Generate USAGE.md

Write `HOME\.claude\USAGE.md` with the user's actual paths filled in:

```markdown
# AI Research Tools — Usage Guide

Installed: <today's date> | Version: 2.0.0

## System Architecture

```
AI Research Tools
├── ai-education (Socratic Tutor)  →  <AI_EDUCATION_PATH>
├── idea-pipeline (3 Obsidian vaults + 14 commands)
│   ├── JMP Idea vault             →  <OBSIDIAN_ROOT>\JMP Idea
│   ├── Personal Knowledge Wiki    →  <OBSIDIAN_ROOT>\personal knowledge skill
│   └── Projects vault             →  <OBSIDIAN_ROOT>\projects
└── paper-tracker (weekly digest)  →  <PAPER_TRACKER_PATH>

Global commands: <HOME>\.claude\commands\ (15 commands)
Machine config:  <HOME>\.claude\machine_paths.md
Zotero config:   <HOME>\.claude\zotero\config.json (if using Zotero)
```

## Quick Start Workflows

### Read a paper (ai-education)
1. Put PDF in `<AI_EDUCATION_PATH>\papers\pdfs\`
2. `cd <AI_EDUCATION_PATH>` then open Claude Code
3. Say: "我们来读这篇 [paper name]"
4. When done: `/paper-done <slug>` (exports + idea extraction + sync)

### Create a research idea (idea-pipeline)
1. Open Claude Code anywhere
2. `/idea-new` — describe your idea, Claude does literature review
3. `/idea-next <slug>` — advance through pipeline stages
4. `/idea-status` — see all ideas and their stages

### Develop an idea with full context (idea-pipeline)
1. `/idea-develop <slug>` — loads relevant papers + related ideas + researcher profile
2. Discuss mechanisms, data strategies, critiques
3. `/idea-revise <slug>` to save updates

### Manage a research project (idea-pipeline)
1. `/project-init <slug> <path>` — initialize tracking for a project folder
2. `/project-sync <slug>` — after making progress, scan for changes
3. `/project-status <slug>` — discuss the project, record feedback

### Sync researcher profile (idea-pipeline)
- `/update-researcher-profile` — auto-updates from idea pipeline, pushes to paper tracker

## All 14 Commands

| Command | What it does |
|---------|-------------|
| `/idea-new` | Create a new research idea |
| `/idea-next <slug>` | Advance idea to next pipeline stage |
| `/idea-revise <slug>` | Re-run current stage with new input |
| `/idea-status` | Show all ideas by status |
| `/idea-archive <slug>` | Archive an idea with reason |
| `/idea-develop <slug>` | Deep-dive with cross-system context |
| `/idea-retrospective <slug>` | Generate PDF retrospective for advisor |
| `/idea-zotero-add <slug> <doi>` | Add paper to Zotero collection |
| `/wiki-ingest` | Ingest sources into knowledge wiki |
| `/paper-done <slug>` | Full post-paper pipeline |
| `/update-researcher-profile` | Sync profile to paper tracker |
| `/project-init <slug> <path>` | Start tracking a project |
| `/project-sync <slug>` | Scan project for changes |
| `/project-status <slug>` | Project discussion hub |
| `/research-present` | Socratic design + build for research HTML/slides |

## Key File Paths

| File | Purpose |
|------|---------|
| `<HOME>\.claude\machine_paths.md` | Machine-specific paths (read by all commands) |
| `<OBSIDIAN_ROOT>\JMP Idea\researcher_profile.md` | Your research identity (auto-updated) |
| `<AI_EDUCATION_PATH>\tutor\context_snapshot.md` | Current tutor session state |
| `<AI_EDUCATION_PATH>\papers\index.md` | All papers and their status |
| `<OBSIDIAN_ROOT>\JMP Idea\ideas\index.md` | All research ideas |
| `<OBSIDIAN_ROOT>\projects\index.md` | All tracked projects |

## Upgrading

When a new version is available:
1. `git pull` (if you cloned from GitHub) or download new zip
2. Open Claude Code in the `ai-research-claude-tools/` folder
3. Claude reads INSTALL.md and runs upgrade mode automatically
```

---

## Step 7 — Write Version Marker

Write `HOME\.claude\.ai-tools-version`:
```json
{"version": "2.0.0", "installed": "<YYYY-MM-DD today>", "packages": ["ai-education", "idea-pipeline", "paper-tracker"]}
```

---

## Step 8 — Final Report

Tell the user (in Chinese if they appear Chinese-speaking):

"安装完成！

**已安装：**
- ai-education → `<AI_EDUCATION_PATH>`
- JMP Idea vault → `<OBSIDIAN_ROOT>\JMP Idea`
- Personal Knowledge Wiki → `<OBSIDIAN_ROOT>\personal knowledge skill`
- Projects vault → `<OBSIDIAN_ROOT>\projects`
- 14 个全局命令 → `<HOME>\.claude\commands\`
- Paper Tracker → `<PAPER_TRACKER_PATH>` [需要推送到 GitHub]

**使用指南已生成：** `<HOME>\.claude\USAGE.md`

**下一步：**
1. 在 Obsidian 中打开三个 vault，确认文件已创建
2. 编辑 `researcher_profile.md`，填写你的研究方向
3. 按照 `<PAPER_TRACKER_PATH>\SETUP.md` 的指引，将 paper tracker 推送到 GitHub 并配置 4 个 GitHub Secrets
4. 在 `<AI_EDUCATION_PATH>` 中打开 Claude Code，开始使用 Trevor tutor

有问题？在 `USAGE.md` 中查看完整使用指南。"
