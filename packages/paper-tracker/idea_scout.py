#!/usr/bin/env python3
"""CLI for public discovery and staged idea-scout run manifests."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from scout_core import build_manifest, source_plan
from scout_discovery import discover_openalex


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Scout input must be a JSON object")
    return value


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _atomic_write(path: Path, value: dict, *, allowed_root: Path) -> None:
    if not _within(path, allowed_root):
        raise ValueError(f"Scout output escapes state root: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public, privacy-bounded economics idea scouting")
    sub = parser.add_subparsers(dest="command", required=True)
    packs = sub.add_parser("source-plan")
    packs.add_argument("--scope", action="append")
    packs.add_argument("--as-of")

    discover = sub.add_parser("discover-openalex")
    discover.add_argument("run_id")
    discover.add_argument(
        "--scope",
        action="append",
        choices=("labor", "education", "econometrics", "meta_analysis", "metascience"),
        required=True,
    )
    discover.add_argument("--as-of")
    discover.add_argument("--state-root", required=True, type=Path)
    discover.add_argument("--per-query", type=int, default=25)

    validate = sub.add_parser("validate")
    validate.add_argument("input", type=Path)

    materialize = sub.add_parser("materialize")
    materialize.add_argument("input", type=Path)
    materialize.add_argument("--state-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path: Path | None = None
    if args.command == "source-plan":
        result = source_plan(args.scope, as_of=args.as_of)
    elif args.command == "discover-openalex":
        if not args.run_id.startswith("scout-"):
            raise ValueError("Scout run_id must start with 'scout-'")
        result = discover_openalex(args.scope, as_of=args.as_of, per_query=args.per_query)
        output_path = args.state_root / "runs" / args.run_id / "openalex.json"
        _atomic_write(output_path, result, allowed_root=args.state_root)
    else:
        result = build_manifest(_load(args.input))
        if args.command == "materialize":
            output_path = args.state_root / "runs" / result["run_id"] / "manifest.json"
            _atomic_write(output_path, result, allowed_root=args.state_root)
    response = dict(result)
    if output_path is not None:
        response["output_path"] = str(output_path.resolve())
    print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
