"""Durable, resumable workflow-run manifests and an append-only event stream."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Iterable

from .util import (
    SCHEMA_VERSION,
    append_jsonl_atomic,
    atomic_write_json,
    file_lock,
    read_json,
    slug_is_safe,
    stable_hash,
    utc_now,
)


class RunStateError(RuntimeError):
    pass


class RunStore:
    def __init__(self, state_root: str | Path):
        self.root = Path(state_root)
        self.runs_root = self.root / "runs"
        self.events_path = self.root / "events" / "events.jsonl"

    def manifest_path(self, run_id: str) -> Path:
        if not slug_is_safe(run_id):
            raise ValueError(f"Unsafe run_id: {run_id!r}")
        return self.runs_root / run_id / "manifest.json"

    def _event(
        self,
        *,
        run: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
        actor: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "occurred_at": utc_now(),
            "actor": actor or run["actor"],
            "aggregate_type": "workflow_run",
            "aggregate_id": run["run_id"],
            "run_id": run["run_id"],
            "scope_hash": run.get("scope_hash"),
            "correlation_id": run["run_id"],
            "causation_id": run.get("last_event_id"),
            "payload": payload,
        }
        append_jsonl_atomic(self.events_path, event)
        return event

    def start(
        self,
        workflow: str,
        *,
        run_id: str | None = None,
        actor: str = "human",
        scope_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
        steps: Iterable[str] = (),
    ) -> dict[str, Any]:
        run_id = run_id or str(uuid.uuid4())
        path = self.manifest_path(run_id)
        if path.exists():
            raise RunStateError(f"Run already exists: {run_id}")
        now = utc_now()
        planned_steps = list(dict.fromkeys(str(step).strip() for step in steps))
        if any(not step for step in planned_steps):
            raise ValueError("Planned step names cannot be empty")
        manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "workflow": workflow,
            "status": "running",
            "actor": actor,
            "scope_hash": scope_hash,
            "created_at": now,
            "updated_at": now,
            "resume_count": 0,
            "current_step": None,
            "steps": [
                {"name": step, "status": "pending", "attempt": 1}
                for step in planned_steps
            ],
            "metadata": metadata or {},
            "artifacts": [],
        }
        event = self._event(run=manifest, event_type="run.started", payload={"workflow": workflow})
        manifest["last_event_id"] = event["event_id"]
        manifest["manifest_hash"] = self._manifest_hash(manifest)
        atomic_write_json(path, manifest)
        return manifest

    @staticmethod
    def _manifest_hash(manifest: dict[str, Any]) -> str:
        hashable = {key: value for key, value in manifest.items() if key != "manifest_hash"}
        return stable_hash(hashable)

    def load(self, run_id: str) -> dict[str, Any]:
        path = self.manifest_path(run_id)
        if not path.exists():
            raise RunStateError(f"Unknown run: {run_id}")
        manifest = read_json(path)
        expected = manifest.get("manifest_hash")
        if expected and expected != self._manifest_hash(manifest):
            raise RunStateError(f"Manifest hash mismatch for {run_id}")
        return manifest

    def _save(self, manifest: dict[str, Any]) -> None:
        manifest["updated_at"] = utc_now()
        manifest["manifest_hash"] = self._manifest_hash(manifest)
        atomic_write_json(self.manifest_path(manifest["run_id"]), manifest)

    @staticmethod
    def _find_step(manifest: dict[str, Any], step_name: str) -> dict[str, Any] | None:
        return next((step for step in manifest["steps"] if step["name"] == step_name), None)

    @staticmethod
    def _assert_step_transition_allowed(manifest: dict[str, Any], step_name: str) -> None:
        waiting = [step["name"] for step in manifest["steps"] if step.get("status") == "waiting_human"]
        if manifest["status"] == "completed":
            raise RunStateError("Cannot transition a step in a completed run")
        if manifest["status"] in {"failed", "paused"}:
            raise RunStateError(f"Run is {manifest['status']}; resume it before transitioning steps")
        if manifest["status"] == "waiting_human":
            raise RunStateError(
                f"Run is waiting for human input at {manifest.get('current_step')!r}; resume it first"
            )
        if waiting and step_name not in waiting:
            raise RunStateError(
                f"Resolve waiting step {waiting[0]!r} before transitioning {step_name!r}"
            )

    def complete_step(
        self,
        run_id: str,
        step_name: str,
        *,
        output: dict[str, Any] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        path = self.manifest_path(run_id)
        with file_lock(path):
            manifest = self.load(run_id)
            if manifest["status"] == "completed":
                raise RunStateError("Cannot add a step to a completed run")
            self._assert_step_transition_allowed(manifest, step_name)
            step = self._find_step(manifest, step_name)
            canonical_output = output or {}
            if step and step["status"] == "completed":
                if step.get("output", {}) == canonical_output:
                    return manifest
                raise RunStateError(f"Step {step_name!r} already completed with different output")
            now = utc_now()
            if step is None:
                step = {"name": step_name, "attempt": 1, "started_at": now}
                manifest["steps"].append(step)
            elif step["status"] == "failed":
                step["attempt"] = int(step.get("attempt", 1)) + 1
            step.setdefault("started_at", now)
            step.update(
                {
                    "status": "completed",
                    "completed_at": now,
                    "output": canonical_output,
                    "error": None,
                    "waiting_since": None,
                    "wait_reason": None,
                }
            )
            manifest["status"] = "running"
            manifest["current_step"] = step_name
            if artifacts:
                known = {stable_hash(item) for item in manifest["artifacts"]}
                for artifact in artifacts:
                    if stable_hash(artifact) not in known:
                        manifest["artifacts"].append(artifact)
            event = self._event(
                run=manifest,
                event_type="run.step_completed",
                payload={"step": step_name, "attempt": step["attempt"], "output": canonical_output},
                actor=actor,
            )
            manifest["last_event_id"] = event["event_id"]
            self._save(manifest)
            return manifest

    def start_step(
        self,
        run_id: str,
        step_name: str,
        *,
        details: dict[str, Any] | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        """Mark a step running; repeated calls while running are idempotent."""

        path = self.manifest_path(run_id)
        with file_lock(path):
            manifest = self.load(run_id)
            if manifest["status"] == "completed":
                raise RunStateError("Cannot start a step in a completed run")
            self._assert_step_transition_allowed(manifest, step_name)
            step = self._find_step(manifest, step_name)
            now = utc_now()
            if step is None:
                step = {"name": step_name, "attempt": 1, "started_at": now}
                manifest["steps"].append(step)
            elif step.get("status") == "completed":
                raise RunStateError(f"Step {step_name!r} is already completed")
            elif step.get("status") == "running":
                return manifest
            elif step.get("status") == "failed":
                step["attempt"] = int(step.get("attempt", 1)) + 1
                step["started_at"] = now
            step.setdefault("started_at", now)
            step.update(
                {
                    "status": "running",
                    "details": details or {},
                    "error": None,
                    "waiting_since": None,
                    "wait_reason": None,
                }
            )
            manifest["status"] = "running"
            manifest["current_step"] = step_name
            event = self._event(
                run=manifest,
                event_type="run.step_started",
                payload={"step": step_name, "attempt": step["attempt"], "details": details or {}},
                actor=actor,
            )
            manifest["last_event_id"] = event["event_id"]
            self._save(manifest)
            return manifest

    def wait_step(
        self,
        run_id: str,
        step_name: str,
        *,
        reason: str,
        details: dict[str, Any] | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        """Persist a human decision boundary without treating it as failure."""

        path = self.manifest_path(run_id)
        with file_lock(path):
            manifest = self.load(run_id)
            if manifest["status"] == "completed":
                raise RunStateError("Cannot wait in a completed run")
            step = self._find_step(manifest, step_name)
            now = utc_now()
            if step is None:
                step = {"name": step_name, "attempt": 1, "started_at": now}
                manifest["steps"].append(step)
            elif step.get("status") == "completed":
                raise RunStateError(f"Cannot wait on completed step {step_name!r}")
            canonical_details = details or {}
            step.setdefault("started_at", now)
            if (
                manifest["status"] == "waiting_human"
                and manifest.get("current_step") == step_name
                and step.get("status") == "waiting_human"
                and step.get("wait_reason") == reason
                and step.get("details", {}) == canonical_details
            ):
                return manifest
            self._assert_step_transition_allowed(manifest, step_name)
            step.update(
                {
                    "status": "waiting_human",
                    "waiting_since": now,
                    "wait_reason": reason,
                    "details": canonical_details,
                    "error": None,
                }
            )
            manifest["status"] = "waiting_human"
            manifest["current_step"] = step_name
            event = self._event(
                run=manifest,
                event_type="run.step_waiting_human",
                payload={"step": step_name, "attempt": step["attempt"], "reason": reason, "details": canonical_details},
                actor=actor,
            )
            manifest["last_event_id"] = event["event_id"]
            self._save(manifest)
            return manifest

    def fail_step(
        self,
        run_id: str,
        step_name: str,
        *,
        error: str,
        details: dict[str, Any] | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        path = self.manifest_path(run_id)
        with file_lock(path):
            manifest = self.load(run_id)
            self._assert_step_transition_allowed(manifest, step_name)
            step = self._find_step(manifest, step_name)
            now = utc_now()
            if step is None:
                step = {"name": step_name, "attempt": 1, "started_at": now}
                manifest["steps"].append(step)
            elif step.get("status") == "failed" and manifest["status"] == "running":
                step["attempt"] = int(step.get("attempt", 1)) + 1
                step["started_at"] = now
            if step.get("status") == "completed":
                raise RunStateError(f"Cannot fail completed step {step_name!r}")
            step.setdefault("started_at", now)
            step.update(
                {
                    "status": "failed",
                    "failed_at": now,
                    "error": error,
                    "details": details or {},
                    "waiting_since": None,
                    "wait_reason": None,
                }
            )
            manifest["status"] = "failed"
            manifest["current_step"] = step_name
            event = self._event(
                run=manifest,
                event_type="run.step_failed",
                payload={"step": step_name, "attempt": step["attempt"], "error": error, "details": details or {}},
                actor=actor,
            )
            manifest["last_event_id"] = event["event_id"]
            self._save(manifest)
            return manifest

    def resume(self, run_id: str, *, actor: str | None = None) -> dict[str, Any]:
        path = self.manifest_path(run_id)
        with file_lock(path):
            manifest = self.load(run_id)
            if manifest["status"] not in {"failed", "paused", "waiting_human"}:
                raise RunStateError(f"Run {run_id} is {manifest['status']}, not resumable")
            previous = manifest["status"]
            manifest["status"] = "running"
            manifest["resume_count"] = int(manifest.get("resume_count", 0)) + 1
            event = self._event(
                run=manifest,
                event_type="run.resumed",
                payload={"previous_status": previous, "resume_count": manifest["resume_count"]},
                actor=actor,
            )
            manifest["last_event_id"] = event["event_id"]
            self._save(manifest)
            return manifest

    def complete_run(self, run_id: str, *, actor: str | None = None) -> dict[str, Any]:
        path = self.manifest_path(run_id)
        with file_lock(path):
            manifest = self.load(run_id)
            if manifest["status"] == "completed":
                return manifest
            incomplete = [step["name"] for step in manifest["steps"] if step["status"] != "completed"]
            if incomplete:
                raise RunStateError(f"Cannot complete a run with incomplete steps: {', '.join(incomplete)}")
            manifest["status"] = "completed"
            event = self._event(run=manifest, event_type="run.completed", payload={}, actor=actor)
            manifest["last_event_id"] = event["event_id"]
            self._save(manifest)
            return manifest
