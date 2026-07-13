"""Command-line interface for deterministic research-workflow primitives."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .contracts import available_schemas, validate_contract
from .doctor import run_doctor
from .idea_context import build_idea_context, write_context_manifest
from .identifiers import canonical_paper_id
from .machine_paths import parse_machine_paths
from .profile import project_profile
from .s2check import apply_ready, check_s2
from .sessions import (
    apply_json_patch_object,
    init_session,
    load_patch_argument,
    load_session,
    parse_field_assignments,
    update_session,
)
from .state import RunStore
from .util import ensure_within


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _load_json_argument(value: str | None, *, default: Any) -> Any:
    if value is None:
        return default
    if value.lstrip().startswith(("{", "[")):
        return json.loads(value)
    candidate = Path(value)
    text = candidate.read_text(encoding="utf-8-sig") if candidate.exists() else value
    return json.loads(text)


def _object_argument(value: str | None, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    parsed = _load_json_argument(value, default=default or {})
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object or a path to one")
    return parsed


def _array_argument(value: str | None) -> list[Any]:
    parsed = _load_json_argument(value, default=[])
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON array or a path to one")
    return parsed


def _add_state_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state-root", required=True, type=Path, help="Private runtime state directory")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research-core",
        description="Deterministic contracts and control primitives for the research workflow.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    paths = sub.add_parser("paths", help="Parse the Markdown machine-path configuration")
    paths_sub = paths.add_subparsers(dest="paths_command", required=True)
    paths_show = paths_sub.add_parser("show")
    paths_show.add_argument("--machine-paths", required=True, type=Path)

    paper_id = sub.add_parser("paper-id", help="Normalize identifiers and emit the canonical paper ID")
    for name in ("doi", "openalex", "arxiv", "nber", "url", "title"):
        paper_id.add_argument(f"--{name}")

    contract = sub.add_parser("contract", help="List or validate versioned JSON contracts")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)
    contract_sub.add_parser("list")
    contract_validate = contract_sub.add_parser("validate")
    contract_validate.add_argument("schema")
    contract_validate.add_argument("document", help="JSON text or a JSON file path")

    run = sub.add_parser("run", help="Manage durable, resumable run manifests")
    run_sub = run.add_subparsers(dest="run_command", required=True)
    run_start = run_sub.add_parser("start")
    _add_state_root(run_start)
    run_start.add_argument("--workflow", required=True)
    run_start.add_argument("--run-id")
    run_start.add_argument("--actor", default="human")
    run_start.add_argument("--scope-hash")
    run_start.add_argument("--metadata", help="JSON object or file")
    run_start.add_argument("--step", action="append", default=[], help="Pre-register a pending workflow step")

    run_status = run_sub.add_parser("status")
    _add_state_root(run_status)
    run_status.add_argument("run_id")

    run_complete_step = run_sub.add_parser("step-complete")
    _add_state_root(run_complete_step)
    run_complete_step.add_argument("run_id")
    run_complete_step.add_argument("step")
    run_complete_step.add_argument("--output", help="JSON object or file")
    run_complete_step.add_argument("--artifacts", help="JSON array or file")
    run_complete_step.add_argument("--actor")

    run_start_step = run_sub.add_parser("step-start")
    _add_state_root(run_start_step)
    run_start_step.add_argument("run_id")
    run_start_step.add_argument("step")
    run_start_step.add_argument("--details", help="JSON object or file")
    run_start_step.add_argument("--actor")

    run_wait_step = run_sub.add_parser("step-wait")
    _add_state_root(run_wait_step)
    run_wait_step.add_argument("run_id")
    run_wait_step.add_argument("step")
    run_wait_step.add_argument("--reason", required=True)
    run_wait_step.add_argument("--details", help="JSON object or file")
    run_wait_step.add_argument("--actor")

    run_fail_step = run_sub.add_parser("step-fail")
    _add_state_root(run_fail_step)
    run_fail_step.add_argument("run_id")
    run_fail_step.add_argument("step")
    run_fail_step.add_argument("--error", required=True)
    run_fail_step.add_argument("--details", help="JSON object or file")
    run_fail_step.add_argument("--actor")

    run_resume = run_sub.add_parser("resume")
    _add_state_root(run_resume)
    run_resume.add_argument("run_id")
    run_resume.add_argument("--actor")

    run_complete = run_sub.add_parser("complete")
    _add_state_root(run_complete)
    run_complete.add_argument("run_id")
    run_complete.add_argument("--actor")

    doctor = sub.add_parser("doctor", help="Check paths, text integrity, placeholders, and install drift")
    doctor.add_argument("--machine-paths", type=Path)
    doctor.add_argument("--scan-root", action="append", default=[], type=Path)
    doctor.add_argument("--install-manifest", type=Path)

    profile = sub.add_parser("profile-project", help="Project five provenance-separated profile lanes")
    profile.add_argument("signals", help="JSON array or a JSON file path")
    profile.add_argument("--half-life-days", type=float, default=90.0)

    session = sub.add_parser("idea-session", help="Maintain compact, explicit idea-session state")
    session_sub = session.add_subparsers(dest="session_command", required=True)
    session_init = session_sub.add_parser("init")
    session_init.add_argument("slug")
    session_init.add_argument("--idea-vault", required=True, type=Path)
    session_init.add_argument("--mode", required=True)
    session_init.add_argument("--objective", required=True)
    session_init.add_argument("--scope-hash")
    session_init.add_argument("--overwrite", action="store_true")

    session_show = session_sub.add_parser("show")
    session_show.add_argument("slug")
    session_show.add_argument("--idea-vault", required=True, type=Path)

    session_update = session_sub.add_parser("update")
    session_update.add_argument("slug")
    session_update.add_argument("--idea-vault", required=True, type=Path)
    session_update.add_argument("--field", action="append", default=[], metavar="FIELD=JSON")
    session_update.add_argument("--patch-json", help="Merge object/RFC6902 operations, or a file path")

    context = sub.add_parser("idea-context", help="Build bounded, provenance-bearing idea context")
    context.add_argument("slug")
    context.add_argument("--idea-vault", required=True, type=Path)
    context.add_argument("--pkb-vault", required=True, type=Path)
    context.add_argument("--objective", required=True)
    context.add_argument("--mode", default="general")
    context.add_argument("--max-packets", type=int, default=8)
    context.add_argument("--max-full-sources", type=int, default=3)
    context.add_argument("--write", action="store_true")
    context.add_argument("--workspace", type=Path, help="Must be within ideas/sessions")
    context.add_argument("--format", choices=("json", "markdown"), default="json")
    context.add_argument("--filename")

    s2 = sub.add_parser("s2-check", help="Check an S2 gate and optionally set generated readiness fields")
    s2.add_argument("sidecar", type=Path)
    s2.add_argument("--idea-path", type=Path)
    s2.add_argument("--apply-ready", action="store_true")
    return parser


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "paths":
        _json(parse_machine_paths(args.machine_paths).to_dict())
        return 0

    if args.command == "paper-id":
        values = {name: getattr(args, name) for name in ("doi", "openalex", "arxiv", "nber", "url", "title")}
        _json({"paper_id": canonical_paper_id(values), "inputs": {key: value for key, value in values.items() if value}})
        return 0

    if args.command == "contract":
        if args.contract_command == "list":
            _json({"schemas": available_schemas()})
            return 0
        value = _load_json_argument(args.document, default={})
        errors = validate_contract(args.schema, value)
        _json({"schema": args.schema, "valid": not errors, "errors": errors})
        return 0 if not errors else 1

    if args.command == "run":
        store = RunStore(args.state_root)
        if args.run_command == "start":
            result = store.start(
                args.workflow,
                run_id=args.run_id,
                actor=args.actor,
                scope_hash=args.scope_hash,
                metadata=_object_argument(args.metadata),
                steps=args.step,
            )
        elif args.run_command == "status":
            result = store.load(args.run_id)
        elif args.run_command == "step-complete":
            artifacts = _array_argument(args.artifacts)
            if not all(isinstance(item, dict) for item in artifacts):
                raise ValueError("Every artifact must be a JSON object")
            result = store.complete_step(
                args.run_id,
                args.step,
                output=_object_argument(args.output),
                artifacts=artifacts,
                actor=args.actor,
            )
        elif args.run_command == "step-start":
            result = store.start_step(
                args.run_id,
                args.step,
                details=_object_argument(args.details),
                actor=args.actor,
            )
        elif args.run_command == "step-wait":
            result = store.wait_step(
                args.run_id,
                args.step,
                reason=args.reason,
                details=_object_argument(args.details),
                actor=args.actor,
            )
        elif args.run_command == "step-fail":
            result = store.fail_step(
                args.run_id,
                args.step,
                error=args.error,
                details=_object_argument(args.details),
                actor=args.actor,
            )
        elif args.run_command == "resume":
            result = store.resume(args.run_id, actor=args.actor)
        else:
            result = store.complete_run(args.run_id, actor=args.actor)
        _json(result)
        return 0

    if args.command == "doctor":
        result = run_doctor(
            machine_paths_path=args.machine_paths,
            scan_roots=args.scan_root,
            install_manifest=args.install_manifest,
        )
        _json(result)
        return 0 if result["ok"] else 1

    if args.command == "profile-project":
        signals = _array_argument(args.signals)
        if not all(isinstance(item, dict) for item in signals):
            raise ValueError("Every signal must be a JSON object")
        _json(project_profile(signals, half_life_days=args.half_life_days))
        return 0

    if args.command == "idea-session":
        if args.session_command == "init":
            result = init_session(
                args.idea_vault,
                args.slug,
                mode=args.mode,
                objective=args.objective,
                scope_hash=args.scope_hash,
                overwrite=args.overwrite,
            )
        elif args.session_command == "show":
            result = load_session(args.idea_vault, args.slug)
        else:
            patch = parse_field_assignments(args.field)
            if args.patch_json:
                patch = apply_json_patch_object(patch, load_patch_argument(args.patch_json))
            if not patch:
                raise ValueError("idea-session update requires --field or --patch-json")
            result = update_session(args.idea_vault, args.slug, patch)
        _json(result)
        return 0

    if args.command == "idea-context":
        result = build_idea_context(
            idea_vault=args.idea_vault,
            pkb_vault=args.pkb_vault,
            slug=args.slug,
            objective=args.objective,
            mode=args.mode,
            max_packets=args.max_packets,
            max_full_sources=args.max_full_sources,
        )
        if not args.write:
            _json(result)
            return 0
        session_root = args.idea_vault / "ideas" / "sessions"
        workspace = args.workspace or session_root / "runs" / args.slug
        ensure_within(workspace, session_root)
        path = write_context_manifest(
            result,
            workspace=workspace,
            output_format=args.format,
            filename=args.filename,
            allowed_root=session_root,
        )
        _json({"path": str(path.resolve()), "context_id": result["context_id"], "stats": result["stats"]})
        return 0

    if args.command == "s2-check":
        report = check_s2(args.sidecar, idea_path=args.idea_path)
        if args.apply_ready:
            report = apply_ready(args.sidecar, report)
        _json(report)
        return 0 if report["ready"] else 1

    raise AssertionError(f"Unhandled command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"research-core: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
