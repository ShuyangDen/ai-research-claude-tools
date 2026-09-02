from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class CodexTaskQueueError(RuntimeError):
    """Raised when a Workbench handoff cannot reach the visible Codex task."""


class CodexTaskNotFoundError(CodexTaskQueueError):
    """Raised when the configured visible task does not exist on this machine."""


@dataclass(frozen=True)
class CodexQueueReceipt:
    target: str
    message_id: str
    thread_id: str = ""
    created: bool = False


class CodexTaskQueue:
    """Queue work into an existing, user-visible Codex Desktop task.

    `codex queue` talks to the shared local Codex daemon and does not navigate
    or foreground the desktop app. The target is an exact task name (portable
    across machines) or a thread UUID. Permissions remain those of the target
    task; Workbench never grants approvals or extra writable roots.
    """

    def __init__(
        self,
        *,
        target: str,
        cwd: Path,
        executable: str | None = None,
    ) -> None:
        self.target = target.strip()
        self.cwd = cwd.resolve()
        self.executable = executable or shutil.which("codex") or "codex"

    def enqueue(self, message: str) -> CodexQueueReceipt:
        if not self.target:
            raise CodexTaskQueueError("Codex reading task is not configured.")
        if not message.strip():
            raise ValueError("Codex handoff message cannot be empty.")
        command = [
            self.executable,
            "queue",
            "--thread",
            self.target,
            "--message",
            message,
            "-C",
            str(self.cwd),
        ]
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            result = subprocess.run(
                command,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
                creationflags=creation_flags,
            )
        except FileNotFoundError as exc:
            raise CodexTaskQueueError("Codex CLI was not found. Start Codex Desktop and rerun setup.") from exc
        except subprocess.TimeoutExpired as exc:
            raise CodexTaskQueueError("Codex task handoff timed out before it was accepted.") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "unknown Codex queue error").strip()
            normalized = detail.casefold()
            if any(marker in normalized for marker in ("not found", "no thread", "no active session")):
                raise CodexTaskNotFoundError(
                    f"Codex task '{self.target}' is not active on this machine."
                )
            raise CodexTaskQueueError(f"Codex task handoff failed: {detail}")
        match = re.search(
            r"Queued message\s+([0-9a-f-]+)\s+for thread\s+([0-9a-f-]+)",
            result.stdout,
            re.IGNORECASE,
        )
        return CodexQueueReceipt(
            target=self.target,
            message_id=match.group(1) if match else "",
            thread_id=match.group(2) if match else "",
        )


class FakeCodexTaskQueue:
    def __init__(self, target: str = "论文阅读 · Trevor") -> None:
        self.target = target
        self.messages: list[str] = []

    def enqueue(self, message: str) -> CodexQueueReceipt:
        self.messages.append(message)
        return CodexQueueReceipt(target=self.target, message_id=f"queued-{len(self.messages)}")
