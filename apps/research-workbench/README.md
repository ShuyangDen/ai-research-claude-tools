# AI Research Workbench v1

本地优先的论文、阅读、Ideas、进行中项目与研究流程工作台。浏览器只连接本机 FastAPI
代理；Codex App Server、文件权限与审批不会暴露给前端。现有 Markdown、
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

## 在另一台电脑安装

另一台电脑已经有本仓库时，先拉取最新代码，再运行统一安装器；它会同步三个研究包，
并自动建立 Workbench Python 环境、安装前端依赖和编译前端：

```powershell
git pull --ff-only
python scripts\sync_local_install.py --apply
powershell -ExecutionPolicy Bypass -File apps/research-workbench/start.ps1
```

首次使用 Codex 功能时，根据 `login.ps1` 的提示用同一个 ChatGPT 账户登录。Python
虚拟环境、前端构建产物、登录凭据与本机路径不会从 GitHub 下载；它们会在每台电脑上
单独建立。

如果 Paper Tracker、Idea vault、Projects vault、AI Education 或 Personal Knowledge 位于仓库之外，
每台电脑仍需保留自己的 `machine_paths.md`。这个文件只负责本机路径解析，已被 Git
忽略，不应上传。

## 两台电脑同步

打开“运行记录”里的 **GitHub Sync**，可以同步所有已配置研究仓库，也可以只同步一个：

- 同步会先 `fetch`，只做 `pull --ff-only`，然后推送已经存在的本地提交。
- 工作台不会运行 `git add` 或 `git commit`；存在未提交改动时会停止该仓库的同步，
  避免覆盖工作。
- 本地与远端分叉时会停止并提示人工处理，不会自行 merge 或 rebase。
- API 只接受工作台从本机配置解析出的仓库 ID，不接受任意路径或 shell 命令。

因此跨电脑的推荐、论文状态、Ideas 和研究档案需要先由对应现有流程写入其 Git 仓库并
提交，之后点击“同步”即可带到另一台电脑。PDF、Codex thread、私人推荐理由和 Workbench
本地状态刻意保持仅本机，不经 GitHub 传播。

## 数据边界

- 只读聚合：Paper Tracker archives/queue、Idea vault、AI Education、已安装 skills。
- 项目页：读取并更新 `machine_paths.md` 指向的 Projects vault；只登记已有项目目录，
  不会改写项目目录本身。新增项目会建立 project-status/project-sync 兼容的索引骨架。
- Workbench 私有状态：默认 `apps/research-workbench/.workbench-state/workbench/`；可用
  `RESEARCH_WORKBENCH_STATE_ROOT` 覆盖。
- Tracker 公开归档：`<paper_tracker_root>/archives/<ISO-week>/<run-id>/`。
- PDF cache：`<paper_tracker_root>/pdf_cache/`，不会提交 Git。
- 所有写接口均为固定动作并要求 CSRF；没有 shell 或任意路径 API。
- Git 同步只覆盖预先配置的仓库，只传输已经提交的内容；不会自动生成提交。
- 排名、解释和普通对话使用只读 Codex sandbox；只有明确触发“完成/粗读归档”或
  `idea-next` 时，才向 App Server 提供配置过的数据根目录，网络仍关闭且审批会回到工作台。
- 本周推荐有不可绕过的摘要门槛：摘要缺失、只有标题或只是短元数据片段时不显示推荐；
  只有完整摘要逐字传给本地 Codex、并为全部候选返回摘要依据后的 ranking v3 才能进入推荐区。

## 开发

```powershell
apps/research-workbench/.venv/Scripts/python -m pytest apps/research-workbench/backend/tests
cd apps/research-workbench/frontend
npm run build
```
