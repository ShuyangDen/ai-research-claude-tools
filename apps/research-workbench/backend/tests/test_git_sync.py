from __future__ import annotations

import subprocess
from pathlib import Path

from research_workbench.git_sync import GitSyncService
from research_workbench.models import GitSyncRequest


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return completed.stdout.strip()


def test_sync_is_allowlisted_fast_forward_only_and_never_commits_dirty_files(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    first = tmp_path / "first"
    second = tmp_path / "second"
    subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, check=True)
    subprocess.run(["git", "init", "-b", "main", str(first)], capture_output=True, check=True)
    git(first, "config", "user.email", "fixture@example.test")
    git(first, "config", "user.name", "Fixture")
    (first / "README.md").write_text("one\n", encoding="utf-8")
    git(first, "add", "README.md")
    git(first, "commit", "-m", "initial")
    git(first, "remote", "add", "origin", str(remote))
    git(first, "push", "-u", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    subprocess.run(["git", "clone", str(remote), str(second)], capture_output=True, check=True)

    (first / "README.md").write_text("two\n", encoding="utf-8")
    git(first, "add", "README.md")
    git(first, "commit", "-m", "update")
    git(first, "push")

    service = GitSyncService({"tools": second, "tracker": second})
    targets, missing = service._targets()
    assert not missing
    assert len(targets) == 1
    repository_id = targets[0].repository_id
    fetched, _ = service.sync(GitSyncRequest(mode="fetch", repository_ids=[repository_id]))
    assert fetched[0].status == "succeeded"
    assert service.overview().repositories[0].behind == 1
    synced, overview = service.sync(GitSyncRequest(mode="sync", repository_ids=[repository_id]))
    assert synced[0].status == "succeeded", synced[0].detail
    assert overview.repositories[0].state == "clean"
    assert (second / "README.md").read_text(encoding="utf-8") == "two\n"

    head_before = git(second, "rev-parse", "HEAD")
    (second / "README.md").write_text("local draft\n", encoding="utf-8")
    with_local_edits, overview = service.sync(GitSyncRequest(mode="sync", repository_ids=[repository_id]))
    assert with_local_edits[0].status == "succeeded"
    assert "未提交改动（未上传）" in with_local_edits[0].detail
    assert git(second, "rev-parse", "HEAD") == head_before
    assert overview.repositories[0].dirty_count == 1
    (second / "README.md").write_text("two\n", encoding="utf-8")

    (second / ".env").write_text("DO_NOT_UPLOAD=fixture\n", encoding="utf-8")
    blocked, overview = service.sync(GitSyncRequest(mode="sync", repository_ids=[repository_id]))
    assert blocked[0].status == "failed"
    assert overview.repositories[0].dirty_count == 1
    assert overview.repositories[0].sensitive_change_count == 1
    assert ".env" not in blocked[0].detail


def test_missing_configured_directory_is_reported_without_local_path(tmp_path: Path) -> None:
    missing = tmp_path / "private-machine-path"
    overview = GitSyncService({"ideas": missing}).overview()
    assert overview.repositories[0].available is False
    assert overview.repositories[0].name == "Ideas"
    assert str(tmp_path) not in overview.model_dump_json()


def test_manual_sync_commits_and_pushes_dedicated_private_state(tmp_path: Path) -> None:
    remote = tmp_path / "private-state.git"
    seed = tmp_path / "seed"
    local = tmp_path / "local"
    receiver = tmp_path / "receiver"
    subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, check=True)
    subprocess.run(["git", "init", "-b", "main", str(seed)], capture_output=True, check=True)
    git(seed, "config", "user.email", "fixture@example.test")
    git(seed, "config", "user.name", "Fixture")
    (seed / "README.md").write_text("private state\n", encoding="utf-8")
    git(seed, "add", "README.md")
    git(seed, "commit", "-m", "initial")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    subprocess.run(["git", "clone", str(remote), str(local)], capture_output=True, check=True)
    git(local, "config", "user.email", "fixture@example.test")
    git(local, "config", "user.name", "Fixture")
    slate = local / "workbench" / "weeks" / "2026-W36" / "slate.json"
    slate.parent.mkdir(parents=True)
    slate.write_text('{"ranking_version": 3}\n', encoding="utf-8")

    service = GitSyncService({"workbench-state": local})
    target = service._targets()[0][0]
    results, overview = service.sync(GitSyncRequest(mode="sync", repository_ids=[target.repository_id]))
    assert results[0].status == "succeeded", results[0].detail
    assert "已提交本机私有状态" in results[0].detail
    assert overview.repositories[0].state == "clean"

    subprocess.run(["git", "clone", str(remote), str(receiver)], capture_output=True, check=True)
    assert (receiver / "workbench" / "weeks" / "2026-W36" / "slate.json").exists()
