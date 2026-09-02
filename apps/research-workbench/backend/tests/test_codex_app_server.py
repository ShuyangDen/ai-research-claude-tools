from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import research_workbench.codex_app_server as codex_module
from research_workbench.codex_app_server import CodexAppServer, CodexUnavailable, diagnose_codex


class ProbeAppServer(CodexAppServer):
    def __init__(self, *, cwd: Path) -> None:
        super().__init__(cwd=cwd)
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.sent: list[dict[str, Any]] = []

    @property
    def running(self) -> bool:
        return True

    async def request(self, method: str, params: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
        self.requests.append((method, params))
        if method == "thread/start":
            return {"thread": {"id": "thr-new"}}
        if method == "thread/resume":
            return {"thread": {"id": params["threadId"]}}
        if method == "thread/list":
            return {"data": []}
        if method == "thread/name/set":
            return {}
        if method == "turn/start":
            thread_id = params["threadId"]
            self._text[thread_id].append("streamed answer")
            self._event_log[thread_id].append({"method": "item/agentMessage/delta"})
            if thread_id in self._turn_done:
                self._turn_done[thread_id].set_result({"status": "completed"})
            return {"turn": {"status": "inProgress"}}
        return {}

    async def _send(self, payload: dict[str, Any]) -> None:
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_app_server_start_resume_stream_and_scoped_write_sandbox(tmp_path: Path) -> None:
    server = ProbeAppServer(cwd=tmp_path)
    ai_education = tmp_path / "AI Education"
    readonly = await server.run_prompt("read", thread_id="thr-existing", cwd=ai_education)
    assert readonly.thread_id == "thr-existing"
    assert readonly.text == "streamed answer"
    assert [method for method, _ in server.requests[:2]] == ["thread/resume", "turn/start"]
    assert server.requests[1][1]["approvalPolicy"] == "never"
    assert server.requests[1][1]["sandboxPolicy"] == {"type": "readOnly"}
    assert server.requests[1][1]["cwd"] == str(ai_education.resolve())

    vault = tmp_path / "vault"
    writable = await server.run_prompt("write", writable_roots=(vault,), cwd=ai_education)
    assert writable.thread_id == "thr-new"
    thread = next(params for method, params in reversed(server.requests) if method == "thread/start")
    assert thread["approvalPolicy"] == "never"
    assert thread["sandbox"] == "read-only"
    assert thread["cwd"] == str(ai_education.resolve())
    turn = next(params for method, params in reversed(server.requests) if method == "turn/start")
    assert turn["approvalPolicy"] == "untrusted"
    assert turn["sandboxPolicy"] == {
        "type": "workspaceWrite",
        "writableRoots": [str(vault.resolve())],
        "networkAccess": False,
    }


@pytest.mark.asyncio
async def test_named_handoff_creates_titles_and_queues_visible_task(tmp_path: Path) -> None:
    server = ProbeAppServer(cwd=tmp_path)
    ai_education = tmp_path / "AI Education"

    thread_id, turn_id, created = await server.queue_named_prompt(
        "论文阅读 · Trevor", "read this paper", cwd=ai_education
    )

    assert thread_id == "thr-new"
    assert turn_id == ""
    assert created is True
    assert [method for method, _ in server.requests] == [
        "thread/list", "thread/start", "thread/name/set", "turn/start"
    ]
    assert server.requests[2][1] == {"threadId": "thr-new", "name": "论文阅读 · Trevor"}
    turn = server.requests[3][1]
    assert turn["cwd"] == str(ai_education.resolve())
    assert turn["sandboxPolicy"] == {"type": "readOnly"}


@pytest.mark.asyncio
async def test_named_handoff_does_not_reuse_same_title_from_another_project(tmp_path: Path) -> None:
    class OtherProjectProbe(ProbeAppServer):
        async def request(self, method: str, params: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
            self.requests.append((method, params))
            if method == "thread/list":
                return {
                    "data": [
                        {
                            "id": "thr-other",
                            "name": "论文阅读 · Trevor",
                            "cwd": str((tmp_path / "other-project").resolve()),
                        }
                    ]
                }
            if method == "thread/start":
                return {"thread": {"id": "thr-new"}}
            return {}

    server = OtherProjectProbe(cwd=tmp_path)
    thread_id, _, created = await server.queue_named_prompt(
        "论文阅读 · Trevor", "read this paper", cwd=tmp_path / "AI Education"
    )

    assert thread_id == "thr-new"
    assert created is True
    assert "thread/resume" not in [method for method, _ in server.requests]
    assert [method for method, _ in server.requests] == [
        "thread/list", "thread/start", "thread/name/set", "turn/start"
    ]


@pytest.mark.asyncio
async def test_app_server_approval_response_is_allowlisted(tmp_path: Path) -> None:
    server = ProbeAppServer(cwd=tmp_path)
    server._approvals["approval-1"] = {
        "approval_id": "approval-1",
        "rpc_id": 17,
        "thread_id": "thr-1",
        "method": "item/fileChange/requestApproval",
        "params": {},
    }
    await server.answer_approval("approval-1", "accept")
    assert server.sent == [{"id": 17, "result": {"decision": "accept"}}]
    assert server.pending_approvals == []
    with pytest.raises(ValueError):
        await server.answer_approval("missing", "always-allow")


@pytest.mark.asyncio
async def test_stale_rollout_is_replaced_with_a_fresh_thread(tmp_path: Path) -> None:
    class StaleProbe(ProbeAppServer):
        async def request(self, method: str, params: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
            self.requests.append((method, params))
            if method == "thread/resume":
                raise CodexUnavailable(
                    "App Server thread/resume failed: no rollout found for thread id stale-thread"
                )
            if method == "thread/start":
                return {"thread": {"id": "thr-recovered"}}
            return {}

    server = StaleProbe(cwd=tmp_path)
    recovered = await server.start_thread(thread_id="stale-thread")
    assert recovered == "thr-recovered"
    assert [method for method, _ in server.requests] == ["thread/resume", "thread/start"]


def test_login_diagnostic_rejects_explicit_not_logged_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_module, "find_codex_cli", lambda: "codex.exe")
    monkeypatch.setattr(codex_module.shutil, "which", lambda name: f"{name}.exe" if name == "gh" else None)

    def probe(command: list[str], timeout: float = 8.0) -> tuple[int, str]:
        if command[0] == "codex.exe":
            return 0, "Not logged in"
        return 0, "gh version fixture"

    monkeypatch.setattr(codex_module, "_probe", probe)
    diagnostic = diagnose_codex()
    assert diagnostic.installed is True
    assert diagnostic.logged_in is False
    assert diagnostic.gh_installed is True


def test_desktop_bundled_codex_is_discovered_without_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundled = tmp_path / "OpenAI" / "Codex" / "bin" / "version-id" / "codex.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"fixture")
    monkeypatch.setattr(codex_module.os, "name", "nt")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(codex_module.shutil, "which", lambda _: None)
    assert codex_module.find_codex_cli() == str(bundled.resolve())
