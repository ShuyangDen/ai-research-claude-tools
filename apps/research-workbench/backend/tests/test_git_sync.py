from __future__ import annotations

import subprocess
from pathlib import Path

from research_workbench.git_sync import GitSyncService
from research_workbench.models import GitSyncRequest
from research_workbench.tracker_queue_sync import parse_queue_jsonl, render_reading_queue, serialize_queue


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


def test_domain_token_module_name_is_not_mistaken_for_a_secret(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], capture_output=True, check=True)
    git(tmp_path, "config", "user.email", "fixture@example.test")
    git(tmp_path, "config", "user.name", "Fixture")
    (tmp_path / "frontier_tokens.py").write_text("TOKEN_BUDGET = 1000\n", encoding="utf-8")

    state = GitSyncService({"tools": tmp_path}).overview().repositories[0]

    assert state.dirty_count == 1
    assert state.sensitive_change_count == 0


def test_unconfigured_private_state_is_reported_without_falling_back_to_tools(tmp_path: Path) -> None:
    overview = GitSyncService({"tools": tmp_path, "workbench-state": None}).overview()
    state = next(item for item in overview.repositories if item.roles == ["workbench-state"])
    assert state.available is False
    assert "machine_paths.md" in state.detail


def test_private_state_rejects_a_network_remote_whose_privacy_cannot_be_verified(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], capture_output=True, check=True)
    git(tmp_path, "config", "user.email", "fixture@example.test")
    git(tmp_path, "config", "user.name", "Fixture")
    (tmp_path / "README.md").write_text("private state\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-m", "initial")
    git(tmp_path, "remote", "add", "origin", "https://gitlab.example.test/owner/state.git")
    (tmp_path / "workbench.json").write_text("{}\n", encoding="utf-8")

    service = GitSyncService({"workbench-state": tmp_path})
    target = service._targets()[0][0]
    try:
        service._commit_portable_state(target)
    except RuntimeError as exc:
        assert "无法验证隐私" in str(exc)
    else:
        raise AssertionError("unverifiable network remote should be rejected")


def test_ai_education_sync_commits_only_durable_reading_state(tmp_path: Path) -> None:
    remote = tmp_path / "ai-education.git"
    seed = tmp_path / "seed"
    local = tmp_path / "local"
    receiver = tmp_path / "receiver"
    subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, check=True)
    subprocess.run(["git", "init", "-b", "main", str(seed)], capture_output=True, check=True)
    git(seed, "config", "user.email", "fixture@example.test")
    git(seed, "config", "user.name", "Fixture")
    (seed / "tutor").mkdir()
    (seed / "tutor" / "reading_feedback.jsonl").write_text('{"paper_id":"one"}\n', encoding="utf-8")
    (seed / "README.md").write_text("original\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "initial")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    subprocess.run(["git", "clone", str(remote), str(local)], capture_output=True, check=True)
    git(local, "config", "user.email", "fixture@example.test")
    git(local, "config", "user.name", "Fixture")
    (local / "tutor" / "reading_feedback.jsonl").write_text(
        '{"paper_id":"one"}\n{"paper_id":"two"}\n', encoding="utf-8"
    )
    (local / "README.md").write_text("local draft\n", encoding="utf-8")

    service = GitSyncService({"ai-education": local})
    target = service._targets()[0][0]
    results, overview = service.sync(GitSyncRequest(mode="sync", repository_ids=[target.repository_id]))

    assert results[0].status == "succeeded", results[0].detail
    assert "已提交 AI Education" in results[0].detail
    assert overview.repositories[0].dirty_count == 1
    assert (local / "README.md").read_text(encoding="utf-8") == "local draft\n"
    subprocess.run(["git", "clone", str(remote), str(receiver)], capture_output=True, check=True)
    assert '"paper_id":"two"' in (receiver / "tutor" / "reading_feedback.jsonl").read_text(encoding="utf-8")
    assert (receiver / "README.md").read_text(encoding="utf-8") == "original\n"


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

    head_before = git(local, "rev-parse", "HEAD")
    unsafe = local / "workbench" / "settings.json"
    unsafe.write_text('{"api_key":"fixture-value-that-must-not-upload"}\n', encoding="utf-8")
    blocked, _ = service.sync(GitSyncRequest(mode="sync", repository_ids=[target.repository_id]))
    assert blocked[0].status == "failed"
    assert "疑似凭据内容" in blocked[0].detail
    assert git(local, "rev-parse", "HEAD") == head_before
    assert unsafe.exists()


def test_tracker_sync_semantically_merges_progress_and_new_recommendations(tmp_path: Path) -> None:
    remote = tmp_path / "tracker.git"
    seed = tmp_path / "seed"
    local = tmp_path / "local"
    cloud_runner = tmp_path / "cloud-runner"
    receiver = tmp_path / "receiver"
    subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, check=True)
    subprocess.run(["git", "init", "-b", "main", str(seed)], capture_output=True, check=True)
    git(seed, "config", "user.email", "fixture@example.test")
    git(seed, "config", "user.name", "Fixture")

    def queue_record(paper_id: str, **updates):  # type: ignore[no-untyped-def]
        value = {
            "paper_id": paper_id,
            "candidate_slug": paper_id.replace(":", "-"),
            "title": f"Distinctive economics paper title {paper_id}",
            "tier": 2,
            "lane": "adjacent",
            "matched_signal": "",
            "authors": "A. Author",
            "venue": "Working Paper",
            "url": f"https://example.test/{paper_id}",
            "published": "2026-08-01",
            "added": "2026-08-10",
            "last_seen": "2026-08-10",
            "status": "queued",
            "score": 70.0,
            "triage_action": "",
            "pinned": False,
            "identifiers": {},
            "schema_version": "1.1",
        }
        value.update(updates)
        return value

    initial = [queue_record("doi:one")]
    (seed / "queue_state.jsonl").write_text(serialize_queue(initial), encoding="utf-8")
    (seed / "reading_queue.md").write_text(render_reading_queue(initial), encoding="utf-8")
    (seed / "README.md").write_text("private tracker\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "initial")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    subprocess.run(["git", "clone", str(remote), str(local)], capture_output=True, check=True)
    subprocess.run(["git", "clone", str(remote), str(cloud_runner)], capture_output=True, check=True)
    for root in (local, cloud_runner):
        git(root, "config", "user.email", "fixture@example.test")
        git(root, "config", "user.name", "Fixture")

    local_rows = [queue_record(
        "doi:one",
        status="completed",
        triage_action="complete-full",
        user_updated_at="2026-09-02T12:00:00Z",
    )]
    (local / "queue_state.jsonl").write_text(serialize_queue(local_rows), encoding="utf-8")
    (local / "local-notes.txt").write_text("uncommitted draft\n", encoding="utf-8")

    cloud_rows = [
        queue_record("doi:one", last_seen="2026-09-03", score=97.0),
        queue_record("doi:two", last_seen="2026-09-03", score=96.0),
    ]
    (cloud_runner / "queue_state.jsonl").write_text(serialize_queue(cloud_rows), encoding="utf-8")
    (cloud_runner / "reading_queue.md").write_text(render_reading_queue(cloud_rows), encoding="utf-8")
    git(cloud_runner, "add", "queue_state.jsonl", "reading_queue.md")
    git(cloud_runner, "commit", "-m", "weekly recommendations")
    git(cloud_runner, "push")

    service = GitSyncService({"tracker": local})
    target = service._targets()[0][0]
    results, overview = service.sync(GitSyncRequest(mode="sync", repository_ids=[target.repository_id]))

    assert results[0].status == "succeeded", results[0].detail
    assert "按论文 ID 合并" in results[0].detail
    assert (local / "local-notes.txt").read_text(encoding="utf-8") == "uncommitted draft\n"
    assert "local-notes.txt" not in git(local, "ls-files")
    assert overview.repositories[0].dirty_count == 1

    subprocess.run(["git", "clone", str(remote), str(receiver)], capture_output=True, check=True)
    merged = parse_queue_jsonl((receiver / "queue_state.jsonl").read_text(encoding="utf-8"), source="receiver")
    assert {item["paper_id"] for item in merged} == {"doi:one", "doi:two"}
    first = next(item for item in merged if item["paper_id"] == "doi:one")
    assert first["status"] == "completed"
    assert first["score"] == 97.0
    assert "doi-two" in (receiver / "reading_queue.md").read_text(encoding="utf-8")
    assert "doi-one" not in (receiver / "reading_queue.md").read_text(encoding="utf-8")

    git(cloud_runner, "pull", "--ff-only")
    (cloud_runner / "README.md").write_text("remote code update\n", encoding="utf-8")
    git(cloud_runner, "add", "README.md")
    git(cloud_runner, "commit", "-m", "remote code update")
    git(cloud_runner, "push")
    head_before = git(local, "rev-parse", "HEAD")
    (local / "README.md").write_text("local code draft\n", encoding="utf-8")
    local_queue = parse_queue_jsonl(
        (local / "queue_state.jsonl").read_text(encoding="utf-8"), source="local"
    )
    local_queue[0]["status"] = "in_progress"
    (local / "queue_state.jsonl").write_text(serialize_queue(local_queue), encoding="utf-8")

    blocked, _ = service.sync(GitSyncRequest(mode="sync", repository_ids=[target.repository_id]))

    assert blocked[0].status == "failed"
    assert "README.md" in blocked[0].detail
    assert git(local, "rev-parse", "HEAD") == head_before
    assert "queue_state.jsonl" in git(local, "status", "--short")
