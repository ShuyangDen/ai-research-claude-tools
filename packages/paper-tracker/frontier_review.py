#!/usr/bin/env python3
"""CLI for incremental, Obsidian-backed economics frontier reviews."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from frontier_core import (
    DEFAULT_WINDOW_MONTHS,
    build_update_plan,
)
from frontier_render import (
    extract_human_notes,
    paper_filename,
    render_cluster_note,
    render_index,
    render_paper_note,
    render_run_report,
)
from frontier_state import build_frontier_state
from scout_core import source_plan


APPLIED_SECONDARY_SOURCES = (
    "American Economic Journal: Applied Economics",
    "American Economic Journal: Economic Policy",
    "Review of Economics and Statistics",
    "Journal of Public Economics",
)


def frontier_source_plan(
    scopes: list[str] | None = None, *, as_of: str | None = None, months: int = DEFAULT_WINDOW_MONTHS
) -> dict[str, Any]:
    """Narrow idea-scout's broad source plan to labor/education field synthesis."""

    selected_scopes = list(dict.fromkeys(scopes or ["labor", "education"]))
    plan = source_plan(
        selected_scopes,
        as_of=as_of,
        journal_months=months,
        working_paper_months=months,
    )
    packs = ["econ_top5"]
    if "labor" in selected_scopes:
        packs.append("labor_field")
    if "education" in selected_scopes:
        packs.append("education_field")
    packs.extend(("applied_secondary", "frontier_working_papers"))
    sources = {
        pack: plan["sources"][pack]
        for pack in packs
        if pack in plan["sources"]
    }
    sources["applied_secondary"] = list(APPLIED_SECONDARY_SOURCES)
    sources = {pack: sources[pack] for pack in packs}
    plan["source_packs"] = packs
    plan["sources"] = sources
    share = round(1 / len(selected_scopes), 4)
    plan["topic_budget"] = {scope: share for scope in selected_scopes}
    plan["frontier_review_policy"] = {
        "incremental": True,
        "default_token_mode": "standard",
        "abstract_first": True,
        "working_paper_targeted_sections_only": True,
        "unrequested_methods_and_meta_packs": "excluded",
    }
    return plan


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Frontier input must be a JSON object: {path}")
    return value


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _atomic_write(path: Path, data: bytes, *, allowed_root: Path) -> None:
    if not _within(path, allowed_root):
        raise ValueError(f"Frontier output escapes state root: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _text_bytes(value: str) -> bytes:
    return value.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _load_state(root: Path) -> dict[str, Any]:
    path = root / "state.json"
    return _load(path) if path.exists() else {}


def _committed_run_ids(state: dict[str, Any]) -> set[str]:
    values = {str(item) for item in state.get("committed_run_ids", [])}
    if state.get("last_run_id"):
        values.add(str(state["last_run_id"]))
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Incremental, source-grounded economics frontier review state"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sources = sub.add_parser("source-plan")
    sources.add_argument("--scope", action="append", choices=("labor", "education"))
    sources.add_argument("--as-of")
    sources.add_argument("--months", type=int, default=DEFAULT_WINDOW_MONTHS)

    plan = sub.add_parser("plan")
    plan.add_argument("input", type=Path)
    plan.add_argument("--state-root", required=True, type=Path)
    plan.add_argument("--write", action="store_true")

    validate = sub.add_parser("validate")
    validate.add_argument("input", type=Path)
    validate.add_argument("--state-root", required=True, type=Path)

    materialize = sub.add_parser("materialize")
    materialize.add_argument("input", type=Path)
    materialize.add_argument("--state-root", required=True, type=Path)

    status = sub.add_parser("status")
    status.add_argument("--state-root", required=True, type=Path)
    return parser


def _materialize_unlocked(
    payload: dict[str, Any],
    root: Path,
    *,
    require_materialization_hash: bool = True,
) -> dict[str, Any]:
    previous = _load_state(root)
    run_id = str(payload.get("run_id", ""))
    run_root = root / "runs" / run_id
    if run_id in _committed_run_ids(previous):
        raise ValueError(f"Frontier run_id is already committed: {run_id}")
    plan = build_update_plan(payload, previous)
    state, manifest = build_frontier_state(
        payload,
        previous,
        require_materialization_hash=require_materialization_hash,
    )
    run_root = root / "runs" / manifest["run_id"]

    # Projections first, canonical state last.  An interrupted run therefore
    # cannot make partial projections authoritative.
    for paper_id, paper in state["papers"].items():
        path = root / "papers" / paper_filename(paper_id)
        _atomic_write(path, _text_bytes(render_paper_note(paper)), allowed_root=root)
    for cluster_id, cluster in state["clusters"].items():
        path = root / "clusters" / f"{cluster_id}.md"
        human_notes = extract_human_notes(path.read_text(encoding="utf-8-sig")) if path.exists() else ""
        _atomic_write(
            path,
            _text_bytes(render_cluster_note(cluster, state["papers"], human_notes=human_notes)),
            allowed_root=root,
        )
    _atomic_write(run_root / "plan.json", _json_bytes(plan), allowed_root=root)
    _atomic_write(run_root / "manifest.json", _json_bytes(manifest), allowed_root=root)
    _atomic_write(
        run_root / "report.md", _text_bytes(render_run_report(manifest, state)), allowed_root=root
    )
    _atomic_write(root / "index.md", _text_bytes(render_index(state)), allowed_root=root)
    _atomic_write(root / "state.json", _json_bytes(state), allowed_root=root)
    return {
        "run_id": manifest["run_id"],
        "state_root": str(root.resolve()),
        "state_hash": state["state_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "materialization_hash": manifest["materialization_hash"],
        "report_path": str((run_root / "report.md").resolve()),
        "updated_cluster_ids": manifest["updated_cluster_ids"],
    }


def _materialize(
    payload: dict[str, Any],
    root: Path,
    *,
    require_materialization_hash: bool = True,
) -> dict[str, Any]:
    with _state_lock(root):
        return _materialize_unlocked(
            payload,
            root,
            require_materialization_hash=require_materialization_hash,
        )


@contextlib.contextmanager
def _state_lock(root: Path):
    """Hold an OS-managed nonblocking lock that is released on process exit."""

    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".materialize.lock"
    with lock_path.open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError(
                    f"Another frontier materialization holds the state lock: {lock_path}"
                ) from exc
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError(
                    f"Another frontier materialization holds the state lock: {lock_path}"
                ) from exc
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _coverage_warnings(source_health: Any) -> list[str]:
    warnings: list[str] = []
    if not isinstance(source_health, dict) or not source_health:
        return ["No source-health record is available for the latest run."]

    def visit(prefix: str, value: Any) -> None:
        if isinstance(value, dict) and "status" not in value:
            for key, child in value.items():
                visit(f"{prefix}/{key}" if prefix else str(key), child)
            return
        if isinstance(value, dict):
            status = str(value.get("status", "unknown")).casefold()
        else:
            status = str(value).casefold() if prefix == "status" else "unknown"
        if status not in {"ok", "healthy", "active"}:
            warnings.append(f"{prefix}: {status}")

    for source, value in source_health.items():
        visit(str(source), value)
    return warnings


def _next_reconciliation_at(state: dict[str, Any]) -> str | None:
    value = str(state.get("last_reconciled_at", "") or "")
    if not value:
        return None
    try:
        moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (moment + dt.timedelta(days=90)).isoformat()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "source-plan":
        result = frontier_source_plan(args.scope, as_of=args.as_of, months=args.months)
    elif args.command == "status":
        state = _load_state(args.state_root)
        latest = state.get("last_run_summary", {}) if state else {}
        result = {
            "exists": bool(state),
            "state_root": str(args.state_root.resolve()),
            "last_run_id": state.get("last_run_id"),
            "updated_at": state.get("updated_at"),
            "paper_count": len(state.get("papers", {})),
            "active_paper_count": sum(
                row.get("frontier_status", "active") == "active"
                for row in state.get("papers", {}).values()
                if isinstance(row, dict)
            ),
            "cluster_count": len(state.get("clusters", {})),
            "state_hash": state.get("state_hash"),
            "last_reconciled_at": state.get("last_reconciled_at"),
            "next_reconciliation_at": _next_reconciliation_at(state),
            "source_health": latest.get("source_health", {}),
            "coverage_warnings": _coverage_warnings(latest.get("source_health", {})),
            "last_inventory": latest.get("inventory", {}),
        }
    elif args.command == "plan":
        payload = _load(args.input)
        if args.write:
            with _state_lock(args.state_root):
                current_state = _load_state(args.state_root)
                result = build_update_plan(payload, current_state)
                path = args.state_root / "runs" / result["run_id"] / "plan.json"
                if result["run_id"] in _committed_run_ids(current_state):
                    raise ValueError(
                        f"Frontier run_id is already committed: {result['run_id']}"
                    )
                _atomic_write(path, _json_bytes(result), allowed_root=args.state_root)
                result = {**result, "plan_path": str(path.resolve())}
        else:
            result = build_update_plan(payload, _load_state(args.state_root))
    elif args.command == "validate":
        state, manifest = build_frontier_state(_load(args.input), _load_state(args.state_root))
        result = {
            "valid": True,
            "run_id": manifest["run_id"],
            "state_hash": state["state_hash"],
            "manifest_hash": manifest["manifest_hash"],
            "materialization_hash": manifest["materialization_hash"],
        }
    else:
        result = _materialize(_load(args.input), args.state_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
