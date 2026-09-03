from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .models import GitRepositoryState, GitSyncOverview, GitSyncRequest, GitSyncResult
from .tracker_queue_sync import atomic_write_text, merge_queue_text, refresh_queue_view


ROLE_LABELS = {
    "tools": "AI Research Cloud Tools",
    "tracker": "Paper Tracker",
    "ideas": "Ideas",
    "ai-education": "AI Education",
    "knowledge": "Personal Knowledge",
    "projects": "Projects",
    "workbench-state": "Workbench Private State",
}
ROLE_SCOPE = {
    "tools": ["Workbench 前后端与安装包|||Workbench frontend, backend, and installer", "三个 agent/skill 适配器及研究工作流|||Three agent/skill adapters and research workflows", "版本、测试和同步脚本|||Version, tests, and sync scripts"],
    "tracker": ["论文队列与历史状态|||Paper queue and history", "推荐/研究者 profile|||Recommendations and researcher profile", "抓取、周报、frontier 代码与测试|||Collection, weekly digest, frontier code, and tests"],
    "ai-education": ["论文阅读笔记与索引|||Paper reading notes and indexes", "Trevor 会话状态和 reading feedback|||Trevor session state and reading feedback", "教材索引、研究来源、报告源文件与技能|||Textbook indexes, research sources, report sources, and skills"],
    "ideas": ["JMP Idea 想法、gate、研究 profile 与审计数据|||JMP ideas, gates, research profile, and audit data"],
    "knowledge": ["Personal Knowledge 来源笔记、frontier 卡片与知识索引|||Personal Knowledge source notes, frontier cards, and indexes"],
    "projects": ["Projects 项目索引、专属工作台、变更记录与导师反馈|||Project indexes, adaptive workspaces, change logs, and advisor feedback"],
    "workbench-state": ["完整摘要与候选池快照|||Complete abstracts and candidate-pool snapshots", "Ranking、Top 5、私人理由与周计划|||Rankings, Top 5, private reasons, and weekly plans", "Clusters、解释、运行记录与可恢复会话状态|||Clusters, explanations, run receipts, and resumable session state"],
}
ROLE_EXCLUDES = {
    "tools": ["本机 Workbench 状态、Codex thread、依赖缓存与构建产物|||Machine-local Workbench state, Codex threads, dependency caches, and build artifacts"],
    "tracker": ["本地 PDF、邮件凭据、缓存和临时生成文件|||Local PDFs, email credentials, caches, and temporary generated files"],
    "ai-education": ["论文/教材 PDF、全文转换、缓存、LaTeX 构建产物和 queue 镜像|||Paper/textbook PDFs, full-text conversions, caches, LaTeX builds, and queue mirrors"],
    "ideas": ["密钥、Zotero 本机配置、锁文件、缓存和论文 PDF|||Secrets, local Zotero settings, lock files, caches, and paper PDFs"],
    "knowledge": ["密钥、机器路径、临时 frontier 工作目录、缓存和论文 PDF|||Secrets, machine paths, temporary frontier workspaces, caches, and paper PDFs"],
    "projects": ["项目原始数据与 PDF；这里只同步 Projects vault 中的耐久状态|||Raw project data and PDFs; only durable Projects-vault state is synced"],
    "workbench-state": ["PDF 正文、登录凭据、依赖缓存和临时文件|||PDF full text, login credentials, dependency caches, and temporary files"],
}
SENSITIVE_PATH = re.compile(
    r"(^|/)(\.env($|\.)|machine_paths\.md$|"
    r"(?:secrets?|credentials?|passwords?|tokens?|api[_-]?keys?|access[_-]?tokens?|"
    r"refresh[_-]?tokens?|client[_-]?secrets?)(?:[._-]|$)|.*\.(?:pem|key|p12|pfx)$)",
    re.IGNORECASE,
)
SENSITIVE_CONTENT = re.compile(
    r"(?ix)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret)"
    r"[\"']?\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']|"
    r"bearer\s+[a-z0-9._~+/=-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
TEXT_STATE_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".toml", ".txt", ".yaml", ".yml"}
AI_EDUCATION_STATE_PATHS = (
    "papers/notes",
    "papers/exports",
    "tutor/context_snapshot.md",
    "tutor/reading_feedback.jsonl",
)


class GitSyncError(RuntimeError):
    pass


@dataclass
class RepositoryTarget:
    repository_id: str
    root: Path
    roles: list[str]
    display_name: str
    included_scope: list[str]
    excluded_scope: list[str]


def _creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def _run_git(root: Path, *args: str, timeout: float = 90.0, check: bool = True) -> str:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GCM_INTERACTIVE"] = "Never"
    try:
        completed = subprocess.run(
            ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env=environment,
            creationflags=_creation_flags(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitSyncError(str(exc)) from exc
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if check and completed.returncode != 0:
        output = "\n".join(part for part in (stdout, stderr) if part)
        raise GitSyncError(output or f"git {' '.join(args)} failed ({completed.returncode})")
    # Git for Windows can emit harmless configuration warnings on stderr even
    # when a command succeeds.  State readers (especially `status --porcelain`)
    # must only consume the machine-readable stdout or those warnings look like
    # repository changes.
    return stdout


def _safe_remote(value: str) -> str:
    remote = value.strip()
    if not remote:
        return ""
    if remote.startswith("git@") and ":" in remote:
        host, path = remote.split(":", 1)
        return f"{host.removeprefix('git@')}/{path.removesuffix('.git')}"
    parsed = urlsplit(remote)
    if parsed.scheme and parsed.netloc:
        host = parsed.hostname or parsed.netloc.rsplit("@", 1)[-1]
        if parsed.port:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path.removesuffix(".git"), "", ""))
    return Path(remote).name.removesuffix(".git")


def _repository_id(remote: str, root: Path) -> str:
    stable = _safe_remote(remote).casefold() or root.name.casefold()
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:12]


class GitSyncService:
    """Explicit, allowlisted Git synchronization.

    Ordinary research repositories are never committed automatically. Their
    committed history can still be fetched, fast-forwarded, and pushed while
    unrelated local edits remain in place. A dedicated ``workbench-state``
    repository is different: pressing Sync is the user's explicit request to
    snapshot and transfer that private state. Paper Tracker also receives
    special handling: only its canonical queue files are auto-committed, then
    local reading progress and remote discoveries are merged by paper identity.
    """

    def __init__(self, candidates: dict[str, Path | None]) -> None:
        self.candidates = candidates

    def _targets(self) -> tuple[list[RepositoryTarget], list[GitRepositoryState]]:
        grouped: dict[Path, list[str]] = {}
        missing: list[GitRepositoryState] = []
        for role, configured in self.candidates.items():
            if configured is None:
                missing.append(
                    GitRepositoryState(
                        repository_id=f"missing-{role}",
                        name=ROLE_LABELS.get(role, role),
                        roles=[role],
                        available=False,
                        state="unavailable",
                        detail=(
                            "尚未在 machine_paths.md 配置独立私有状态仓库。"
                            if role == "workbench-state"
                            else "此电脑尚未配置该数据目录。"
                        ),
                    )
                )
                continue
            path = configured.resolve()
            if not path.exists():
                missing.append(
                    GitRepositoryState(
                        repository_id=f"missing-{role}",
                        name=ROLE_LABELS.get(role, role),
                        roles=[role],
                        available=False,
                        state="unavailable",
                        detail="此电脑尚未配置该数据目录。",
                    )
                )
                continue
            try:
                root_text = _run_git(path, "rev-parse", "--show-toplevel", timeout=10)
                root = Path(root_text.splitlines()[0]).resolve()
            except GitSyncError:
                missing.append(
                    GitRepositoryState(
                        repository_id=f"not-git-{role}",
                        name=ROLE_LABELS.get(role, role),
                        roles=[role],
                        available=False,
                        state="unavailable",
                        detail="目录存在，但不是 Git 仓库。",
                    )
                )
                continue
            grouped.setdefault(root, []).append(role)

        targets: list[RepositoryTarget] = []
        for root, roles in grouped.items():
            remote = _run_git(root, "remote", "get-url", "origin", timeout=10, check=False)
            sorted_roles = sorted(roles)
            if "tools" in roles:
                display_name = "AI Research Cloud Tools"
            elif "workbench-state" in roles:
                display_name = ROLE_LABELS["workbench-state"]
            elif "tracker" in roles:
                display_name = "Paper Tracker"
            elif "ai-education" in roles:
                display_name = "AI Education"
            elif any(role in roles for role in ("ideas", "knowledge", "projects")):
                display_name = "Obsidian Research Vault"
            else:
                display_name = root.name
            included = [item for role in sorted_roles for item in ROLE_SCOPE.get(role, [])]
            excluded = [item for role in sorted_roles for item in ROLE_EXCLUDES.get(role, [])]
            targets.append(RepositoryTarget(_repository_id(remote, root), root, sorted_roles, display_name, included, excluded))
        return targets, missing

    def _state(self, target: RepositoryTarget) -> GitRepositoryState:
        try:
            branch = _run_git(target.root, "branch", "--show-current", timeout=10)
            if not branch:
                branch = _run_git(target.root, "rev-parse", "--short", "HEAD", timeout=10)
            raw_remote = _run_git(target.root, "remote", "get-url", "origin", timeout=10, check=False)
            remote = _safe_remote(raw_remote)
            changes = [line for line in _run_git(target.root, "status", "--porcelain=v1", timeout=20).splitlines() if line]
            changed_paths = [line[3:].replace("\\", "/") if len(line) > 3 else "" for line in changes]
            sensitive = sum(1 for path in changed_paths if SENSITIVE_PATH.search(path))
            upstream = _run_git(
                target.root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", timeout=10, check=False
            )
            has_upstream = bool(upstream and "fatal:" not in upstream.casefold())
            ahead = behind = 0
            if has_upstream:
                counts = _run_git(target.root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}", timeout=15)
                parts = counts.split()
                if len(parts) >= 2:
                    ahead, behind = int(parts[0]), int(parts[1])
            if changes:
                state = "dirty"
            elif ahead and behind:
                state = "diverged"
            elif ahead:
                state = "ahead"
            elif behind:
                state = "behind"
            else:
                state = "clean"
            last_commit = _run_git(target.root, "log", "-1", "--format=%h %cs %s", timeout=10, check=False)
            tracked = [line for line in _run_git(target.root, "ls-files", timeout=30).splitlines() if line]
            untracked = [line for line in _run_git(target.root, "ls-files", "--others", "--exclude-standard", timeout=30).splitlines() if line]
            return GitRepositoryState(
                repository_id=target.repository_id,
                name=target.display_name,
                roles=target.roles,
                branch=branch,
                remote=remote,
                has_upstream=has_upstream,
                dirty_count=len(changes),
                sensitive_change_count=sensitive,
                ahead=ahead,
                behind=behind,
                last_commit=last_commit[:180],
                tracked_count=len(tracked),
                tracked_pdf_count=sum(1 for path in tracked if path.casefold().endswith(".pdf")),
                untracked_count=len(untracked),
                ignored_count=None,
                included_scope=target.included_scope,
                excluded_scope=target.excluded_scope,
                state=state,
                detail="有疑似敏感文件改动；同步不会提交这些文件。" if sensitive else "",
            )
        except (GitSyncError, ValueError) as exc:
            return GitRepositoryState(
                repository_id=target.repository_id,
                name=target.display_name,
                roles=target.roles,
                included_scope=target.included_scope,
                excluded_scope=target.excluded_scope,
                state="error",
                detail=str(exc)[:500],
            )

    def overview(self) -> GitSyncOverview:
        targets, missing = self._targets()
        repositories = [self._state(target) for target in targets] + missing
        repositories.sort(key=lambda item: (not item.available, item.name.casefold()))
        return GitSyncOverview(
            repositories=repositories,
            privacy=[
                "普通研究仓库只同步已提交历史；AI Education 仅自动提交论文笔记、阅读反馈和导出状态。",
                "即使仓库有本地改动也可以点击同步；远端更新只在 Git 能安全快进时拉取。",
                "Paper Tracker 会按论文 ID 合并队列：保留本机阅读进度，并接收云端新推荐，不会整文件覆盖。",
                "Workbench Private State 仅在手动点击同步时自动提交；该 remote 必须保持 Private。",
                "不会同步 machine paths、登录凭据、PDF 正文、依赖缓存或临时文件。",
                "API 不接收任意路径或 shell 命令；仓库范围只来自本机配置。",
            ],
        )

    @staticmethod
    def _is_portable_state(target: RepositoryTarget) -> bool:
        return target.roles == ["workbench-state"]

    @staticmethod
    def _is_tracker_queue(target: RepositoryTarget) -> bool:
        return target.roles == ["tracker"] and (target.root / "queue_state.jsonl").exists()

    @staticmethod
    def _is_ai_education(target: RepositoryTarget) -> bool:
        return target.roles == ["ai-education"]

    @staticmethod
    def _changed_paths(target: RepositoryTarget, pathspecs: tuple[str, ...] = ()) -> set[str]:
        separator = ("--", *pathspecs) if pathspecs else ()
        tracked = _run_git(target.root, "diff", "HEAD", "--name-only", *separator, timeout=30, check=False)
        untracked = _run_git(
            target.root,
            "ls-files",
            "--others",
            "--exclude-standard",
            *separator,
            timeout=30,
            check=False,
        )
        return {
            line.replace("\\", "/")
            for line in (*tracked.splitlines(), *untracked.splitlines())
            if line.strip()
        }

    @staticmethod
    def _assert_safe_content(target: RepositoryTarget, paths: set[str]) -> None:
        for relative in sorted(paths):
            normalized = relative.replace("\\", "/")
            if SENSITIVE_PATH.search(normalized):
                raise GitSyncError("检测到疑似凭据文件名；没有暂存或上传任何内容。")
            path = target.root / relative
            if not path.is_file() or path.suffix.casefold() not in TEXT_STATE_SUFFIXES:
                continue
            if path.stat().st_size > 5 * 1024 * 1024:
                raise GitSyncError("待同步文本状态超过 5 MB；请先人工检查后再同步。")
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if SENSITIVE_CONTENT.search(text):
                raise GitSyncError("待同步状态中检测到疑似凭据内容；没有暂存或上传任何内容。")

    @staticmethod
    def _assert_private_remote(target: RepositoryTarget) -> None:
        raw_remote = _run_git(target.root, "remote", "get-url", "origin", timeout=10, check=False)
        safe_remote = _safe_remote(raw_remote)
        github_match = re.search(
            r"github\.com[/:](?P<slug>[^/]+/[^/]+?)(?:\.git)?$",
            safe_remote,
            re.IGNORECASE,
        )
        if github_match is None:
            raw = raw_remote.strip()
            is_network_remote = bool(
                re.match(r"^(?!file:)[a-z][a-z0-9+.-]*://", raw, re.IGNORECASE)
                or re.match(r"^[^/@:]+@[^:]+:", raw)
            )
            if is_network_remote:
                raise GitSyncError(
                    "Workbench State 使用了无法验证隐私的远端；为避免泄露，本次同步已停止。"
                )
            return
        slug = github_match.group("slug")
        try:
            completed = subprocess.run(
                ["gh", "repo", "view", slug, "--json", "isPrivate", "--jq", ".isPrivate"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
                env={**os.environ, "GH_PROMPT_DISABLED": "1"},
                creationflags=_creation_flags(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitSyncError("无法调用 GitHub CLI 验证 Workbench State 远端隐私。") from exc
        if completed.returncode != 0 or completed.stdout.strip().casefold() != "true":
            raise GitSyncError("无法确认 Workbench State 远端为 Private；为避免泄露，本次同步已停止。")

    @staticmethod
    def _active_ai_education_paths(target: RepositoryTarget) -> tuple[str, ...]:
        active = []
        for relative in AI_EDUCATION_STATE_PATHS:
            if (target.root / relative).exists() or _run_git(
                target.root, "ls-files", "--", relative, timeout=10, check=False
            ):
                active.append(relative)
        return tuple(active)

    def _commit_portable_state(self, target: RepositoryTarget) -> bool:
        changed_paths = self._changed_paths(target)
        if not changed_paths:
            return False
        self._assert_private_remote(target)
        self._assert_safe_content(target, changed_paths)
        _run_git(target.root, "add", "-A", "--", ".", timeout=30)
        staged = _run_git(target.root, "diff", "--cached", "--name-only", timeout=30)
        if not staged:
            return False
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        _run_git(target.root, "commit", "-m", f"chore(workbench): sync private state {stamp}", timeout=60)
        return True

    def _commit_ai_education_state(self, target: RepositoryTarget) -> bool:
        pathspecs = self._active_ai_education_paths(target)
        if not pathspecs:
            return False
        changed_paths = self._changed_paths(target, pathspecs)
        if not changed_paths:
            return False
        self._assert_safe_content(target, changed_paths)
        _run_git(target.root, "add", "-A", "--", *pathspecs, timeout=30)
        raw_modes = _run_git(target.root, "diff", "--cached", "--raw", "--", *pathspecs, timeout=30)
        if re.search(r"^:\d{6} 160000 ", raw_modes, re.MULTILINE):
            _run_git(target.root, "reset", "-q", "HEAD", "--", *pathspecs, timeout=30, check=False)
            raise GitSyncError("AI Education 笔记目录中检测到嵌套 Git checkout；没有提交或上传。")
        staged = _run_git(target.root, "diff", "--cached", "--name-only", "--", *pathspecs, timeout=30)
        if not staged:
            return False
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        _run_git(
            target.root,
            "commit",
            "--only",
            "-m",
            f"chore(ai-education): sync reading notes {stamp}",
            "--",
            *pathspecs,
            timeout=60,
        )
        return True

    def _commit_tracker_queue(self, target: RepositoryTarget) -> tuple[bool, int]:
        count = refresh_queue_view(target.root)
        changes = _run_git(
            target.root,
            "status",
            "--porcelain=v1",
            "--",
            "queue_state.jsonl",
            "reading_queue.md",
            timeout=30,
        )
        if not changes:
            return False, count
        self._assert_safe_content(target, {"queue_state.jsonl", "reading_queue.md"})
        _run_git(
            target.root,
            "add",
            "--",
            "queue_state.jsonl",
            "reading_queue.md",
            timeout=30,
        )
        staged = _run_git(
            target.root,
            "diff",
            "--cached",
            "--name-only",
            "--",
            "queue_state.jsonl",
            "reading_queue.md",
            timeout=30,
        )
        if not staged:
            return False, count
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        _run_git(
            target.root,
            "commit",
            "--only",
            "-m",
            f"chore(queue): sync reading progress {stamp}",
            "--",
            "queue_state.jsonl",
            "reading_queue.md",
            timeout=60,
        )
        return True, count

    def _tracker_dirty_remote_overlap(self, target: RepositoryTarget) -> list[str]:
        dirty = self._changed_paths(target) - {"queue_state.jsonl", "reading_queue.md"}
        if not dirty:
            return []
        remote_changed = {
            line.replace("\\", "/")
            for line in _run_git(
                target.root,
                "diff",
                "--name-only",
                "HEAD..@{upstream}",
                timeout=30,
                check=False,
            ).splitlines()
            if line.strip()
        }
        return sorted(dirty & remote_changed)

    def _merge_tracker_history(self, target: RepositoryTarget) -> int:
        state_path = target.root / "queue_state.jsonl"
        local_text = state_path.read_text(encoding="utf-8-sig") if state_path.exists() else ""
        remote_text = _run_git(
            target.root,
            "show",
            "@{upstream}:queue_state.jsonl",
            timeout=30,
            check=False,
        )
        merged_state, merged_markdown, count = merge_queue_text(local_text, remote_text)

        _run_git(target.root, "merge", "--no-commit", "--no-ff", "@{upstream}", timeout=90, check=False)
        merge_head = _run_git(target.root, "rev-parse", "--verify", "MERGE_HEAD", timeout=10, check=False)
        if not merge_head:
            raise GitSyncError(
                "无法启动 Paper Tracker 安全合并；本地文件保持不变，请先处理非队列改动。"
            )
        conflicts = {
            line.replace("\\", "/")
            for line in _run_git(
                target.root, "diff", "--name-only", "--diff-filter=U", timeout=30, check=False
            ).splitlines()
            if line
        }
        allowed = {"queue_state.jsonl", "reading_queue.md"}
        unexpected = sorted(conflicts - allowed)
        if unexpected:
            _run_git(target.root, "merge", "--abort", timeout=30, check=False)
            raise GitSyncError(
                "Paper Tracker 除队列外还有代码冲突，已安全停止：" + ", ".join(unexpected[:8])
            )
        atomic_write_text(state_path, merged_state)
        atomic_write_text(target.root / "reading_queue.md", merged_markdown)
        _run_git(target.root, "add", "--", "queue_state.jsonl", "reading_queue.md", timeout=30)
        remaining = _run_git(
            target.root, "diff", "--name-only", "--diff-filter=U", timeout=30, check=False
        )
        if remaining:
            _run_git(target.root, "merge", "--abort", timeout=30, check=False)
            raise GitSyncError("Paper Tracker 队列合并后仍有未解决冲突，已恢复合并前状态。")
        _run_git(
            target.root,
            "commit",
            "-m",
            "merge(queue): preserve reading progress and remote recommendations",
            timeout=60,
        )
        return count

    def sync(self, request: GitSyncRequest) -> tuple[list[GitSyncResult], GitSyncOverview]:
        targets, _ = self._targets()
        by_id = {target.repository_id: target for target in targets}
        selected = request.repository_ids or list(by_id)
        unknown = [repository_id for repository_id in selected if repository_id not in by_id]
        if unknown:
            raise ValueError("Unknown or unavailable repository selection")
        results: list[GitSyncResult] = []
        for repository_id in selected:
            target = by_id[repository_id]
            before = self._state(target)
            if not before.remote:
                results.append(GitSyncResult(repository_id=repository_id, name=before.name, status="skipped", detail="没有 origin remote。"))
                continue
            if request.mode != "fetch" and not before.has_upstream:
                results.append(
                    GitSyncResult(
                        repository_id=repository_id,
                        name=before.name,
                        status="failed",
                        detail="当前分支没有 upstream；请先在 Git 中配置跟踪分支。",
                    )
                )
                continue
            portable_state = self._is_portable_state(target)
            tracker_queue = self._is_tracker_queue(target)
            ai_education = self._is_ai_education(target)
            committed_state = False
            committed_queue = False
            committed_ai_state = False
            queue_count = 0
            try:
                messages: list[str] = []
                if request.mode in {"fetch", "sync"}:
                    _run_git(target.root, "fetch", "--prune", "origin")
                    messages.append("已获取远端状态")
                    before = self._state(target)
                if before.sensitive_change_count:
                    raise GitSyncError("检测到疑似凭据文件改动；为避免意外传输，本次同步已停止。")
                if tracker_queue and request.mode in {"push", "sync"} and before.behind:
                    overlap = self._tracker_dirty_remote_overlap(target)
                    if overlap:
                        raise GitSyncError(
                            "Paper Tracker 的本地代码改动与远端更新重叠；尚未创建队列提交，请先人工合并："
                            + ", ".join(overlap[:8])
                        )
                if portable_state and request.mode in {"push", "sync"}:
                    committed_state = self._commit_portable_state(target)
                if tracker_queue and request.mode in {"push", "sync"}:
                    committed_queue, queue_count = self._commit_tracker_queue(target)
                if ai_education and request.mode in {"push", "sync"}:
                    committed_ai_state = self._commit_ai_education_state(target)
                if committed_state:
                    messages.append("已提交本机私有状态")
                if committed_queue:
                    messages.append(f"已提交本机阅读进度（队列共 {queue_count} 篇）")
                if committed_ai_state:
                    messages.append("已提交 AI Education 论文笔记与阅读反馈")
                refreshed = self._state(target)
                if request.mode == "sync" and refreshed.ahead and refreshed.behind:
                    if portable_state:
                        try:
                            _run_git(target.root, "pull", "--rebase")
                        except GitSyncError:
                            _run_git(target.root, "rebase", "--abort", check=False)
                            raise GitSyncError("两台电脑同时修改了同一份私有状态；已安全停止，需要人工选择保留版本。")
                        messages.append("已在远端私有状态之上重放本机更新")
                        refreshed = self._state(target)
                    elif tracker_queue:
                        queue_count = self._merge_tracker_history(target)
                        messages.append(f"已按论文 ID 合并本机阅读进度与云端新推荐（共 {queue_count} 篇）")
                        refreshed = self._state(target)
                    else:
                        raise GitSyncError("本地与远端已分叉，需要人工选择合并策略。")
                if request.mode == "pull" or (request.mode == "sync" and refreshed.behind):
                    try:
                        _run_git(target.root, "pull", "--ff-only")
                    except GitSyncError as exc:
                        if refreshed.dirty_count:
                            raise GitSyncError(
                                f"已获取远端状态，但 {refreshed.dirty_count} 个本地未提交改动与拉取不兼容；"
                                "Git 没有覆盖这些改动，请先提交或人工合并。"
                            ) from exc
                        raise
                    messages.append("已安全快进拉取")
                refreshed = self._state(target)
                if request.mode == "push" or (request.mode == "sync" and refreshed.ahead):
                    _run_git(target.root, "push")
                    messages.append("已推送已提交内容")
                refreshed = self._state(target)
                if not portable_state and refreshed.dirty_count:
                    messages.append(f"保留 {refreshed.dirty_count} 个本地未提交改动（未上传）")
                if not messages:
                    messages.append("本地与远端已经一致")
                results.append(
                    GitSyncResult(
                        repository_id=repository_id,
                        name=before.name,
                        status="succeeded",
                        detail="；".join(messages),
                    )
                )
            except (GitSyncError, ValueError) as exc:
                preserved = []
                if committed_state:
                    preserved.append("本机私有状态提交已保留但尚未完成同步")
                if committed_queue:
                    preserved.append("本机阅读队列提交已保留但尚未完成同步")
                if committed_ai_state:
                    preserved.append("本机 AI Education 笔记提交已保留但尚未完成同步")
                detail = "；".join([*preserved, str(exc)])
                results.append(
                    GitSyncResult(repository_id=repository_id, name=before.name, status="failed", detail=detail[:500])
                )
        return results, self.overview()
