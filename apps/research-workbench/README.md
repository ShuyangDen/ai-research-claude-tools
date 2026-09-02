# AI Research Workbench v1

本地优先的论文、阅读、Ideas、进行中项目与研究流程工作台。浏览器只连接本机 FastAPI
代理；论文阅读对话不嵌入网页，而是排入 Codex Desktop 的可见 Trevor 任务。现有 Markdown、
JSONL、Obsidian 文件和 Research Core 状态仍是唯一真相。

## Windows 启动

首次安装：

```powershell
powershell -ExecutionPolicy Bypass -File apps/research-workbench/setup.ps1
```

之后启动：

```powershell
powershell -ExecutionPolicy Bypass -File apps/research-workbench/start.ps1
```

打开 <http://127.0.0.1:8765>。服务默认拒绝局域网地址。

首次使用 Codex 功能前运行下面的脚本，选择 ChatGPT 登录；它会自动发现 Codex
Desktop 内置的 CLI，因此不要求 `codex` 已经在 PATH 中，也不需要 API key。

```powershell
powershell -ExecutionPolicy Bypass -File apps/research-workbench/login.ps1
```

`start.ps1` 也会自动执行相同的登录检查。

### 一次性建立 Trevor 交接任务

在 Codex Desktop 的 AI Education 项目中建立一个任务，并把标题设为
`论文阅读 · Trevor`。安装或跨电脑接收工作由 Codex 执行时，安装代理应完成这一步；
工作台本身不会为了建任务而弹出 Codex。需要使用别的任务名时，可设置本机环境变量
`RESEARCH_WORKBENCH_READING_THREAD`。

阅读室点击“感兴趣 · 精读”“感兴趣 · 定向粗读”或“不感兴趣”后，只使用
`codex queue` 把消息排入这个可见任务，不导航、不前置 Codex 窗口，也不代替用户扩大
权限。精读/粗读由 AI Education 的 `paper-reading-tutor` 先取得合法 PDF、经 MarkItDown
解析后再进入正文；不感兴趣先在 Codex 问原因，回答后才记录 reading feedback 和同步队列。

## 在另一台电脑安装

另一台电脑已经有本仓库时，先拉取最新代码，再运行统一安装器；它会同步三个研究包，
并自动建立 Workbench Python 环境、安装前端依赖和编译前端：

```powershell
git pull --ff-only
python scripts\sync_local_install.py --apply
powershell -ExecutionPolicy Bypass -File apps/research-workbench/start.ps1
```

首次使用 Codex 功能时，根据 `login.ps1` 的提示用同一个 ChatGPT 账户登录，并在该机
AI Education 项目建立同名 `论文阅读 · Trevor` 任务。Python
虚拟环境、前端构建产物、登录凭据与本机路径不会从 GitHub 下载；它们会在每台电脑上
单独建立。

如果 Paper Tracker、Idea vault、Projects vault、AI Education 或 Personal Knowledge 位于仓库之外，
每台电脑仍需保留自己的 `machine_paths.md`。这个文件只负责本机路径解析，已被 Git
忽略，不应上传。

## 两台电脑同步

打开“运行记录”里的 **GitHub Sync**，可以同步所有已配置研究仓库，也可以只同步一个：

- 同步会先 `fetch`，只做 `pull --ff-only`，然后推送已经存在的本地提交。
- 普通研究仓库不会自动 `git add` 或 `git commit`。即使存在未提交改动，按钮仍可点击：
  工作台会保留这些改动，只同步已经提交的历史；只有 Git 无法安全快进时才停止并提示人工合并。
- 专用的 **Workbench Private State** 仓库是唯一例外：用户手动点击同步即明确授权工作台
  提交该仓库中的状态，然后 fetch、必要时 rebase、push。这个 GitHub remote 必须保持 Private。
- 本地与远端分叉时会停止并提示人工处理，不会自行 merge 或 rebase。
- API 只接受工作台从本机配置解析出的仓库 ID，不接受任意路径或 shell 命令。

### 私有 Workbench 状态仓库

建立一个单独的 private repository（推荐名 `ai-research-workbench-state`），在每台电脑克隆
到任意本机路径，并在各自的 `~/.claude/machine_paths.md` 中配置：

```markdown
## Research Workbench
- **Private state repo**: `E:\path\on\this\computer\ai-research-workbench-state`
```

路径不需要在两台电脑上一样。状态里的 AI Education、Tracker、Idea vault、Projects vault
和 Tools 路径会保存为逻辑占位符，并在读取时按该机的 `machine_paths.md` 还原。

Projects vault 中的工作台、笔记和状态由 Obsidian 私有仓库同步。实际研究目录可以在每台
电脑放到不同位置，并用项目 slug 覆盖共享文件中的路径：

```markdown
## Project Paths
- **welfare**: `E:\path\on\this\computer\welfare`
- **major**: `E:\path\on\this\computer\major`
```

项目原始数据不复制到 Workbench 状态仓库。Welfare 和 Major 这类含大量原始数据的目录，
应把代码、文稿和小型派生结果放入各自的 private Git repository；受许可限制的数据、PDF、
缓存和可重建输出保留在本机。这样无需占用有限的 Google Drive 空间。

完整摘要、每周候选池快照、ranking/Top 5、私人理由、周计划、clusters、摘要解释、运行记录
和可恢复会话状态会写入这个私有仓库。打开另一台电脑后，到“运行记录 → GitHub Sync”同步
**Workbench Private State**，现有结果会直接恢复，不会重新请求摘要或重复 ranking。PDF 正文、
登录凭据、依赖缓存和临时文件不进入该仓库。

## 数据边界

- 只读聚合：Paper Tracker archives/queue、Idea vault、AI Education、已安装 skills。
- 项目页：读取并更新 `machine_paths.md` 指向的 Projects vault；共享状态通过该 vault 的
  private Git repository 同步，并可通过 `Project Paths` 为每台电脑重映射真实项目目录。它只登记已有项目目录，
  不会改写项目目录本身。每个项目的自适应看板、耐久笔记和复用模块保存在 Projects
  vault；手写图像只保存在本机的 Workbench 状态目录。新增项目会建立
  project-status/project-sync 兼容的索引骨架。
- Workbench 私有状态：优先读取 `machine_paths.md` 的 `Research Workbench / Private state repo`；
  未配置时才回退到 `apps/research-workbench/.workbench-state/`。也可用
  `RESEARCH_WORKBENCH_STATE_ROOT` 临时覆盖。
- Tracker 公开归档：`<paper_tracker_root>/archives/<ISO-week>/<run-id>/`。
- PDF cache：`<paper_tracker_root>/pdf_cache/`，不会提交 Git。
- 所有写接口均为固定动作并要求 CSRF；没有 shell 或任意路径 API。
- Git 同步只覆盖预先配置的仓库；普通仓库不自动提交，但有本地改动时仍可安全同步已提交历史；
  专用私有状态仓库仅在用户手动同步时提交。
- 排名和项目辅助继续使用受控的本地 Codex 调用。论文阅读不在工作台显示聊天或审批；
  它继承目标 Trevor 任务本身的权限，所需 PDF 下载和研究记录写入在 Codex 中按原流程确认。
- 本周推荐有不可绕过的摘要门槛：摘要缺失、只有标题或只是短元数据片段时不显示推荐；
  只有完整摘要逐字传给本地 Codex、并为全部候选返回摘要依据后的 ranking v3 才能进入推荐区。
- 论文列表、阅读室和本周推荐都使用同一份完整摘要；单篇详情缺摘要时会从公开学术元数据源
  补全并记录来源，而不会用标题代替摘要。

## 开发

```powershell
apps/research-workbench/.venv/Scripts/python -m pytest apps/research-workbench/backend/tests
cd apps/research-workbench/frontend
npm run build
```
