from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from research_workbench.codex_task_queue import CodexTaskQueue, CodexTaskQueueError


def test_queue_targets_visible_task_without_opening_app_or_granting_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout="Queued message 01a06279-0623-7db2-abeb-ba3b5044ec4a for thread 01a06275-e4d4-71a0-b2eb-5be86787f518.\n",
            stderr="",
        )

    monkeypatch.setattr("research_workbench.codex_task_queue.subprocess.run", fake_run)
    queue = CodexTaskQueue(target="论文阅读 · Trevor", cwd=tmp_path, executable="codex-test")
    receipt = queue.enqueue("WORKBENCH_CODEX_HANDOFF_V1")

    command = captured["command"]
    assert command[:6] == [
        "codex-test", "queue", "--thread", "论文阅读 · Trevor", "--message", "WORKBENCH_CODEX_HANDOFF_V1"
    ]
    assert "app" not in command
    assert "--approve-for-me" not in command
    assert "--add-dir" not in command
    assert receipt.message_id == "01a06279-0623-7db2-abeb-ba3b5044ec4a"


def test_queue_reports_missing_target_as_setup_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "research_workbench.codex_task_queue.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="No thread found"),
    )
    queue = CodexTaskQueue(target="论文阅读 · Trevor", cwd=tmp_path, executable="codex-test")
    with pytest.raises(CodexTaskQueueError, match="Create that task once"):
        queue.enqueue("paper")
