from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import research_workbench.codex_app_server as codex_module
from research_workbench.codex_app_server import CodexAppServer, diagnose_codex


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
        if method == "turn/start":
            thread_id = params["threadId"]
            self._text[thread_id].append("streamed answer")
            self._event_log[thread_id].append({"method": "item/agentMessage/delta"})
            self._turn_done[thread_id].set_result({"status": "completed"})
            return {"turn": {"status": "inProgress"}}
        return {}

    async def _send(self, payload: dict[str, Any]) -> None:
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_app_server_start_resume_stream_and_scoped_write_sandbox(tmp_path: Path) -> None:
    server = ProbeAppServer(cwd=tmp_path)
    readonly = await server.run_prompt("read", thread_id="thr-existing")
    assert readonly.thread_id == "thr-existing"
    assert readonly.text == "streamed answer"
    assert [method for method, _ in server.requests[:2]] == ["thread/resume", "turn/start"]
    assert server.requests[1][1]["approvalPolicy"] == "never"
    assert server.requests[1][1]["sandboxPolicy"] == {"type": "readOnly"}

    vault = tmp_path / "vault"
    writable = await server.run_prompt("write", writable_roots=(vault,))
    assert writable.thread_id == "thr-new"
    thread = next(params for method, params in reversed(server.requests) if method == "thread/start")
    assert thread["approvalPolicy"] == "never"
    assert thread["sandbox"] == "read-only"
    turn = next(params for method, params in reversed(server.requests) if method == "turn/start")
    assert turn["approvalPolicy"] == "untrusted"
    assert turn["sandboxPolicy"] == {
        "type": "workspaceWrite",
        "writableRoots": [str(vault.resolve())],
        "networkAccess": False,
    }


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
