from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator


@dataclass
class CodexDiagnostic:
    installed: bool
    logged_in: bool
    auth_detail: str
    cli_path: str
    gh_installed: bool
    gh_detail: str


@dataclass
class PromptResult:
    thread_id: str
    text: str
    events: list[dict[str, Any]] = field(default_factory=list)


class CodexUnavailable(RuntimeError):
    pass


def find_codex_cli() -> str:
    """Resolve a PATH-installed CLI or the CLI bundled with Codex Desktop."""
    resolved = shutil.which("codex")
    if resolved:
        return resolved
    if os.name != "nt":
        return ""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        return ""
    bundled_root = Path(local_app_data) / "OpenAI" / "Codex" / "bin"
    if not bundled_root.exists():
        return ""
    candidates = list(bundled_root.glob("*/codex.exe"))
    if not candidates:
        candidates = list(bundled_root.rglob("codex.exe"))
    if not candidates:
        return ""
    return str(max(candidates, key=lambda path: path.stat().st_mtime).resolve())


class CodexSdkRunner:
    """Official Python SDK runner for bounded, non-interactive workflows."""

    def __init__(self, *, cwd: Path) -> None:
        self.cwd = cwd.resolve()

    async def run_prompt(
        self,
        prompt: str,
        *,
        thread_id: str = "",
        model: str = "gpt-5.6-terra",
        skill: tuple[str, Path] | None = None,
        image_paths: tuple[Path, ...] = (),
        timeout: float = 300.0,
    ) -> PromptResult:
        try:
            from openai_codex import ApprovalMode, AsyncCodex, CodexConfig, LocalImageInput, Sandbox, SkillInput, TextInput
        except ImportError as exc:  # pragma: no cover - dependency is part of production install
            raise CodexUnavailable("Official openai-codex Python SDK is not installed") from exc
        inputs: list[Any] = [TextInput(text=prompt)]
        inputs.extend(LocalImageInput(path=str(path.resolve())) for path in image_paths)
        if skill:
            name, path = skill
            inputs.append(SkillInput(name=name, path=str(path.resolve())))
        config = CodexConfig(
            cwd=str(self.cwd),
            client_name="ai_research_workbench",
            client_title="AI Research Workbench",
            client_version="0.1.0",
        )

        async def execute() -> PromptResult:
            async with AsyncCodex(config) as client:
                thread = (
                    await client.thread_resume(
                        thread_id,
                        approval_mode=ApprovalMode.deny_all,
                        sandbox=Sandbox.read_only,
                    )
                    if thread_id
                    else await client.thread_start(
                        approval_mode=ApprovalMode.deny_all,
                        cwd=str(self.cwd),
                        model=model,
                        sandbox=Sandbox.read_only,
                        service_name="ai_research_workbench",
                    )
                )
                result = await thread.run(
                    inputs,
                    approval_mode=ApprovalMode.deny_all,
                    effort="medium",
                    model=model,
                    sandbox=Sandbox.read_only,
                )
                if result.error:
                    raise CodexUnavailable(str(result.error))
                return PromptResult(thread_id=thread.id, text=result.final_response or "")

        try:
            return await asyncio.wait_for(execute(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise CodexUnavailable("Codex SDK workflow timed out") from exc


def _probe(command: list[str], timeout: float = 8.0) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        detail = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
        return completed.returncode, detail
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def diagnose_codex() -> CodexDiagnostic:
    codex_path = find_codex_cli()
    gh_path = shutil.which("gh") or ""
    login_code, login_detail = _probe([codex_path, "login", "status"]) if codex_path else (127, "Codex CLI not found")
    gh_code, gh_detail = _probe([gh_path, "--version"]) if gh_path else (127, "GitHub CLI not found")
    normalized = login_detail.casefold()
    logged_in = login_code == 0 and "not logged in" not in normalized
    return CodexDiagnostic(
        installed=bool(codex_path),
        logged_in=logged_in,
        auth_detail=login_detail or ("Logged in" if logged_in else "Not logged in"),
        cli_path=codex_path,
        gh_installed=gh_code == 0,
        gh_detail=gh_detail,
    )


class EventHub:
    def __init__(self, history_size: int = 300) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=history_size))

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        self._history[channel].append(event)
        for queue in tuple(self._subscribers[channel]):
            await queue.put(event)

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        for event in self._history.get(channel, ()):
            await queue.put(event)
        self._subscribers[channel].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[channel].discard(queue)


class CodexAppServer:
    """Minimal official app-server JSON-RPC client kept behind the local backend.

    The browser never receives the app-server transport. Server-initiated
    approvals are converted into Workbench events and must be answered through
    the allowlisted approval endpoint.
    """

    def __init__(self, *, cwd: Path, event_hub: EventHub | None = None) -> None:
        self.cwd = cwd.resolve()
        self.events = event_hub or EventHub()
        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._turn_done: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._text: dict[str, list[str]] = defaultdict(list)
        self._event_log: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._approvals: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    @property
    def pending_approvals(self) -> list[dict[str, Any]]:
        return list(self._approvals.values())

    async def start(self) -> None:
        async with self._lock:
            if self.running:
                return
            executable = find_codex_cli()
            if not executable:
                raise CodexUnavailable(
                    "Codex CLI 未安装；请按官方说明安装，或运行 Workbench 的 `login.ps1` 自动发现 Codex Desktop CLI"
                )
            self._process = await asyncio.create_subprocess_exec(
                executable,
                "app-server",
                cwd=str(self.cwd),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._reader_task = asyncio.create_task(self._reader_loop())
            await self.request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "ai_research_workbench",
                        "title": "AI Research Workbench",
                        "version": "0.1.0",
                    }
                },
            )
            await self.notify("initialized", {})

    async def close(self) -> None:
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
        if self._reader_task:
            self._reader_task.cancel()
        self._process = None

    async def _send(self, payload: dict[str, Any]) -> None:
        if not self._process or not self._process.stdin:
            raise CodexUnavailable("Codex App Server 未运行")
        self._process.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        await self._process.stdin.drain()

    async def request(self, method: str, params: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
        await self.start() if not self.running and method != "initialize" else None
        request_id = self._next_id
        self._next_id += 1
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        await self._send({"method": method, "id": request_id, "params": params})
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(request_id, None)
        if "error" in response:
            raise CodexUnavailable(f"App Server {method} failed: {response['error']}")
        return response.get("result", {})

    async def notify(self, method: str, params: dict[str, Any]) -> None:
        await self._send({"method": method, "params": params})

    async def _reader_loop(self) -> None:
        assert self._process and self._process.stdout
        while True:
            line = await self._process.stdout.readline()
            if not line:
                error = "Codex App Server closed unexpectedly"
                for future in tuple(self._pending.values()):
                    if not future.done():
                        future.set_exception(CodexUnavailable(error))
                return
            try:
                message = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            request_id = message.get("id")
            if request_id in self._pending and ("result" in message or "error" in message):
                future = self._pending[request_id]
                if not future.done():
                    future.set_result(message)
                continue
            method = str(message.get("method", ""))
            params = message.get("params") or {}
            thread_id = str(params.get("threadId") or params.get("thread", {}).get("id") or "system")
            event = {"method": method, "params": params}
            self._event_log[thread_id].append(event)
            if method == "item/agentMessage/delta":
                delta = params.get("delta")
                if isinstance(delta, str):
                    self._text[thread_id].append(delta)
            if method == "turn/completed":
                future = self._turn_done.get(thread_id)
                if future and not future.done():
                    future.set_result(params)
            if method == "serverRequest/resolved":
                resolved_request_id = str(params.get("requestId", ""))
                for approval_id, approval in tuple(self._approvals.items()):
                    if str(approval.get("rpc_id", "")) == resolved_request_id:
                        self._approvals.pop(approval_id, None)
            if request_id is not None and method in {
                "item/commandExecution/requestApproval",
                "item/fileChange/requestApproval",
                "tool/requestUserInput",
            }:
                approval_id = str(uuid.uuid4())
                approval = {
                    "approval_id": approval_id,
                    "rpc_id": request_id,
                    "thread_id": thread_id,
                    "method": method,
                    "params": params,
                }
                self._approvals[approval_id] = approval
                event = {"method": "workbench/approval-required", "params": approval}
            await self.events.publish(thread_id, event)

    async def account(self) -> dict[str, Any]:
        return await self.request("account/read", {"refreshToken": False})

    async def start_thread(self, *, model: str = "gpt-5.6-terra", thread_id: str = "") -> str:
        if thread_id:
            result = await self.request("thread/resume", {"threadId": thread_id})
        else:
            result = await self.request(
                "thread/start",
                {
                    "model": model,
                    "cwd": str(self.cwd),
                    # A new thread starts read-only. Individual writable turns
                    # override this with the guarded policy below.
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "serviceName": "ai_research_workbench",
                },
            )
        resolved = str(result.get("thread", {}).get("id", ""))
        if not resolved:
            raise CodexUnavailable("App Server did not return a thread id")
        return resolved

    async def run_prompt(
        self,
        prompt: str,
        *,
        thread_id: str = "",
        model: str = "gpt-5.6-terra",
        skill: tuple[str, Path] | None = None,
        image_paths: tuple[Path, ...] = (),
        writable_roots: tuple[Path, ...] = (),
        timeout: float = 300.0,
    ) -> PromptResult:
        resolved_thread = await self.start_thread(model=model, thread_id=thread_id)
        self._text[resolved_thread].clear()
        self._event_log[resolved_thread].clear()
        done: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._turn_done[resolved_thread] = done
        inputs: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        inputs.extend({"type": "localImage", "path": str(path.resolve())} for path in image_paths)
        if skill:
            name, path = skill
            inputs.append({"type": "skill", "name": name, "path": str(path.resolve())})
        sandbox_policy: dict[str, Any]
        if writable_roots:
            sandbox_policy = {
                "type": "workspaceWrite",
                "writableRoots": [str(path.resolve()) for path in writable_roots],
                "networkAccess": False,
            }
        else:
            sandbox_policy = {"type": "readOnly"}
        approval_policy = "untrusted" if writable_roots else "never"
        await self.request(
            "turn/start",
            {
                "threadId": resolved_thread,
                "input": inputs,
                "cwd": str(self.cwd),
                # Paper reading and discussion are read-only and must not stop
                # for routine local reads. Only explicit write workflows ask.
                "approvalPolicy": approval_policy,
                "sandboxPolicy": sandbox_policy,
                "model": model,
                "effort": "medium",
            },
        )
        try:
            await asyncio.wait_for(done, timeout=timeout)
        finally:
            self._turn_done.pop(resolved_thread, None)
        return PromptResult(
            thread_id=resolved_thread,
            text="".join(self._text.pop(resolved_thread, [])),
            events=self._event_log.pop(resolved_thread, []),
        )

    async def answer_approval(self, approval_id: str, decision: str) -> None:
        allowed = {"accept", "acceptForSession", "decline", "cancel"}
        if decision not in allowed:
            raise ValueError(f"Unsupported approval decision: {decision}")
        approval = self._approvals.pop(approval_id, None)
        if not approval:
            raise KeyError(approval_id)
        await self._send({"id": approval["rpc_id"], "result": {"decision": decision}})
        await self.events.publish(
            approval["thread_id"],
            {"method": "workbench/approval-answered", "params": {"approval_id": approval_id, "decision": decision}},
        )


class FakeCodexAppServer(CodexAppServer):
    """Deterministic test double that never starts a process."""

    def __init__(self, *, cwd: Path, responses: list[str] | None = None) -> None:
        super().__init__(cwd=cwd)
        self.responses = deque(responses or ["{}"])
        self.prompts: list[str] = []

    @property
    def running(self) -> bool:
        return True

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def account(self) -> dict[str, Any]:
        return {"account": {"type": "chatgpt", "planType": "plus"}}

    async def start_thread(self, *, model: str = "gpt-5.6-terra", thread_id: str = "") -> str:
        return thread_id or f"thr_test_{len(self.prompts) + 1}"

    async def run_prompt(self, prompt: str, **kwargs: Any) -> PromptResult:
        self.prompts.append(prompt)
        thread_id = str(kwargs.get("thread_id") or f"thr_test_{len(self.prompts)}")
        text = self.responses.popleft() if self.responses else "{}"
        await self.events.publish(thread_id, {"method": "item/agentMessage/delta", "params": {"threadId": thread_id, "delta": text}})
        await self.events.publish(thread_id, {"method": "turn/completed", "params": {"threadId": thread_id, "status": "completed"}})
        return PromptResult(thread_id=thread_id, text=text)
