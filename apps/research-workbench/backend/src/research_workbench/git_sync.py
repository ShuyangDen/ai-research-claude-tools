from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .models import GitRepositoryState, GitSyncOverview, GitSyncRequest, GitSyncResult


ROLE_LABELS = {
    "tools": "AI Research Tools",
    "tracker": "Paper Tracker",
    "ideas": "Ideas",
    "ai-education": "AI Education",
    "knowledge": "Personal Knowledge",
}
SENSITIVE_PATH = re.compile(
    r"(^|/)(\.env($|\.)|machine_paths\.md$|.*(?:secret|credential|password|token).*|.*\.(?:pem|key|p12|pfx)$)",
    re.IGNORECASE,
)


class GitSyncError(RuntimeError):
    pass


@dataclass
class RepositoryTarget:
    repository_id: str
    root: Path
    roles: list[str]


def _creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def _run_git(root: Path, *args: str, timeout: float = 90.0, check: bool = True) -> str:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GCM_INTERACTIVE"] = "Never"
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
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
    """Explicit, allowlisted Git synchronization without automatic commits."""

    def __init__(self, candidates: dict[str, Path]) -> None:
        self.candidates = candidates

    def _targets(self) -> tuple[list[RepositoryTarget], list[GitRepositoryState]]:
        grouped: dict[Path, list[str]] = {}
        missing: list[GitRepositoryState] = []
        for role, configured in self.candidates.items():
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
            targets.append(RepositoryTarget(_repository_id(remote, root), root, sorted(roles)))
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
            return GitRepositoryState(
                repository_id=target.repository_id,
                name=target.root.name,
                roles=target.roles,
                branch=branch,
                remote=remote,
                has_upstream=has_upstream,
                dirty_count=len(changes),
                sensitive_change_count=sensitive,
                ahead=ahead,
                behind=behind,
                last_commit=last_commit[:180],
                state=state,
                detail="有疑似敏感文件改动；同步不会提交这些文件。" if sensitive else "",
            )
        except (GitSyncError, ValueError) as exc:
            return GitRepositoryState(
                repository_id=target.repository_id,
                name=target.root.name,
                roles=target.roles,
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
                "只运行 fetch、pull --ff-only 和 push；不会自动 git add 或 commit。",
                "不会同步 machine paths、登录凭据、Codex thread、私人推荐理由、PDF 或 Workbench 本地状态。",
                "API 不接收任意路径或 shell 命令；仓库范围只来自本机配置。",
            ],
        )

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
            if request.mode in {"pull", "sync"} and before.dirty_count:
                results.append(
                    GitSyncResult(
                        repository_id=repository_id,
                        name=before.name,
                        status="failed",
                        detail=f"有 {before.dirty_count} 个未提交改动；为避免覆盖，本次没有 pull 或 push。请先审核并提交。",
                    )
                )
                continue
            try:
                messages: list[str] = []
                if request.mode in {"fetch", "sync"}:
                    _run_git(target.root, "fetch", "--prune", "origin")
                    messages.append("已获取远端状态")
                refreshed = self._state(target)
                if request.mode == "sync" and refreshed.ahead and refreshed.behind:
                    raise GitSyncError("本地与远端已分叉，需要人工选择合并策略。")
                if request.mode == "pull" or (request.mode == "sync" and refreshed.behind):
                    _run_git(target.root, "pull", "--ff-only")
                    messages.append("已快进拉取")
                refreshed = self._state(target)
                if request.mode == "push" or (request.mode == "sync" and refreshed.ahead):
                    _run_git(target.root, "push")
                    messages.append("已推送已提交内容")
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
            except GitSyncError as exc:
                results.append(
                    GitSyncResult(repository_id=repository_id, name=before.name, status="failed", detail=str(exc)[:500])
                )
        return results, self.overview()
