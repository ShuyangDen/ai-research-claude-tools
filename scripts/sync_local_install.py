#!/usr/bin/env python3
"""Safely compare or install AI Research Tools system files.

The default mode is a read-only dry run.  ``--check`` is also read-only and
returns a non-zero status when installed files drift.  Only ``--apply`` writes,
and every replaced file is backed up before an atomic UTF-8/no-BOM replace.
Personal research data is rejected independently of the mapping manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MAPPING = "packages/codex/local-install-files.json"
MAPPING_SCHEMA = "ai-research-tools.local-install-files"
STATE_SCHEMA = "ai-research-tools.local-install-state"
UTF8_BOM = b"\xef\xbb\xbf"
PATH_TOKEN_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")
SOURCE_TOKEN_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
MACHINE_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
MACHINE_VALUE_RE = re.compile(r"^-\s+\*\*(.+?)\*\*\s*:\s*(.*?)\s*$")


class InstallError(RuntimeError):
    """Raised when an install plan is unsafe or invalid."""


@dataclass(frozen=True)
class InstallItem:
    scope: str
    source: Path
    destination: Path
    source_sha256: str
    installed_sha256: str
    data: bytes
    status: str
    previous_sha256: str | None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def decode_utf8(data: bytes, path: Path) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InstallError(f"not valid UTF-8: {path}: {exc}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def atomic_write(path: Path, data: bytes, *, allow_bom: bool = False) -> None:
    if data.startswith(UTF8_BOM) and not allow_bom:
        raise InstallError(f"refusing to write a UTF-8 BOM: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def repo_path(repo_root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise InstallError(f"source path must be repo-relative: {relative}")
    resolved = (repo_root / candidate).resolve()
    if not is_within(resolved, repo_root):
        raise InstallError(f"source path escapes the repository: {relative}")
    return resolved


def repo_relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def parse_machine_paths_text(text: str) -> dict[tuple[str, str], str]:
    """Parse ``## Section`` and ``- **Key**: `value``` entries."""
    section = ""
    values: dict[tuple[str, str], str] = {}
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        heading = MACHINE_HEADING_RE.match(raw_line.strip())
        if heading:
            section = heading.group(1).strip().casefold()
            continue
        value_match = MACHINE_VALUE_RE.match(raw_line.strip())
        if not value_match or not section:
            continue
        key = value_match.group(1).strip().casefold()
        value = value_match.group(2).strip()
        if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
            value = value[1:-1].strip()
        values[(section, key)] = value
    return values


def first_machine_value(
    values: dict[tuple[str, str], str], candidates: Iterable[tuple[str, str]]
) -> str | None:
    for section, key in candidates:
        value = values.get((section.casefold(), key.casefold()))
        if value:
            return value
    return None


def concrete_path(value: str | None, label: str) -> Path:
    if not value:
        raise InstallError(f"machine_paths.md is missing {label}")
    if "{{" in value or "}}" in value:
        raise InstallError(f"machine_paths.md still has a placeholder for {label}")
    expanded = os.path.expandvars(os.path.expanduser(value.rstrip("\\/")))
    path = Path(expanded)
    if not path.is_absolute():
        raise InstallError(f"machine path for {label} is not absolute: {value}")
    return path.resolve()


def resolve_variables(machine_paths: Path, repo_root: Path, home: Path) -> dict[str, Path | str]:
    if not machine_paths.exists():
        raise InstallError(f"machine paths file is missing: {machine_paths}")
    text = decode_utf8(machine_paths.read_bytes(), machine_paths)
    parsed = parse_machine_paths_text(text)
    idea_vault = concrete_path(
        first_machine_value(
            parsed,
            (("Research Idea Pipeline", "Vault"), ("Idea Pipeline", "Vault")),
        ),
        "Research Idea Pipeline / Vault",
    )
    wiki_vault = concrete_path(
        first_machine_value(
            parsed,
            (("Personal Knowledge Wiki", "Vault"), ("Personal Knowledge", "Vault")),
        ),
        "Personal Knowledge Wiki / Vault",
    )
    ai_education = concrete_path(
        first_machine_value(
            parsed,
            (
                ("AI Education Project", "Project root"),
                ("AI Education Project", "Path"),
                ("AI Education", "Project root"),
            ),
        ),
        "AI Education Project / Project root",
    )
    paper_tracker = concrete_path(
        first_machine_value(
            parsed,
            (
                ("Paper Tracker", "Project root"),
                ("Paper Tracker", "Path"),
            ),
        ),
        "Paper Tracker / Project root",
    )

    if idea_vault.parent.resolve() == wiki_vault.parent.resolve():
        obsidian_root = idea_vault.parent.resolve()
    else:
        try:
            obsidian_root = Path(os.path.commonpath([idea_vault, wiki_vault])).resolve()
        except ValueError:
            obsidian_root = idea_vault.parent.resolve()

    return {
        "HOME": home.resolve(),
        "TOOLS_ROOT": repo_root.resolve(),
        "IDEA_VAULT": idea_vault,
        "WIKI_VAULT": wiki_vault,
        "OBSIDIAN_ROOT": obsidian_root,
        "AI_EDUCATION_PATH": ai_education,
        "PAPER_TRACKER_PATH": paper_tracker,
        "INSTALL_DATE": datetime.now(timezone.utc).date().isoformat(),
    }


def load_mapping(repo_root: Path, mapping_path: Path) -> dict[str, Any]:
    if not mapping_path.exists():
        raise InstallError(f"mapping manifest is missing: {mapping_path}")
    raw = mapping_path.read_bytes()
    if raw.startswith(UTF8_BOM):
        raise InstallError(f"mapping manifest must be UTF-8 without BOM: {mapping_path}")
    try:
        mapping = json.loads(decode_utf8(raw, mapping_path))
    except json.JSONDecodeError as exc:
        raise InstallError(f"invalid mapping manifest: {mapping_path}: {exc}") from exc
    if mapping.get("schema") != MAPPING_SCHEMA or mapping.get("schema_version") != 1:
        raise InstallError("unsupported local-install mapping schema")
    version = mapping.get("installer_version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise InstallError("installer_version must be strict semver")
    for key in ("files", "trees"):
        if not isinstance(mapping.get(key), list):
            raise InstallError(f"mapping manifest needs a {key} list")
    repo_path(repo_root, mapping["release_version_file"])
    return mapping


def available_scopes(mapping: dict[str, Any]) -> tuple[str, ...]:
    scopes = {
        item.get("scope")
        for key in ("trees", "files")
        for item in mapping[key]
        if isinstance(item, dict)
    }
    if None in scopes or not all(isinstance(scope, str) and scope for scope in scopes):
        raise InstallError("every install mapping needs a non-empty scope")
    return tuple(sorted(scopes))


def select_scopes(mapping: dict[str, Any], requested: list[str] | None) -> set[str]:
    available = set(available_scopes(mapping))
    if not requested:
        return available
    selected = {
        value.strip()
        for entry in requested
        for value in entry.split(",")
        if value.strip()
    }
    if "all" in selected:
        if len(selected) != 1:
            raise InstallError("--scope all cannot be combined with another scope")
        return available
    if not selected:
        raise InstallError("--scope did not select any scope")
    unknown = sorted(selected - available)
    if unknown:
        raise InstallError(
            f"unknown scope(s): {', '.join(unknown)}; available: {', '.join(sorted(available))}"
        )
    return selected


def expand_destination(template: str, variables: dict[str, Path | str]) -> Path:
    root_match = re.match(r"^\{([A-Z][A-Z0-9_]*)\}(?:[/\\]|$)", template)
    if not root_match:
        raise InstallError(f"destination must begin with a named root token: {template}")
    root_name = root_match.group(1)
    root_value = variables.get(root_name)
    if not isinstance(root_value, Path):
        raise InstallError(f"destination uses an unavailable path token: {root_name}")

    def replace(match: re.Match[str]) -> str:
        value = variables.get(match.group(1))
        if not isinstance(value, Path):
            raise InstallError(f"destination uses an unavailable path token: {match.group(1)}")
        return str(value)

    expanded = PATH_TOKEN_RE.sub(replace, template)
    destination = Path(expanded).resolve()
    if not is_within(destination, root_value):
        raise InstallError(f"destination escapes {root_name}: {template}")
    return destination


def protected_reason(destination: Path, variables: dict[str, Path | str]) -> str | None:
    """Return why a destination is personal data, regardless of the manifest."""
    idea_root = variables["IDEA_VAULT"]
    wiki_root = variables["WIKI_VAULT"]
    ai_root = variables["AI_EDUCATION_PATH"]
    tracker_root = variables["PAPER_TRACKER_PATH"]
    assert all(isinstance(value, Path) for value in (idea_root, wiki_root, ai_root, tracker_root))

    if is_within(destination, idea_root):
        relative = destination.resolve().relative_to(idea_root.resolve())
        parts = tuple(part.casefold() for part in relative.parts)
        if parts in {("researcher_profile.md",), ("recommendation_profile.json",)}:
            return "idea researcher or recommendation profile"
        if parts and parts[0] == "ideas":
            allowed = {("ideas", "_template.md"), ("ideas", "_s2_gate_template.md")}
            if parts not in allowed:
                return "idea content (only template files are installable)"

    if is_within(destination, wiki_root):
        relative = destination.resolve().relative_to(wiki_root.resolve())
        parts = tuple(part.casefold() for part in relative.parts)
        if parts and parts[0] == "wiki":
            return "personal wiki content"
        if parts and parts[0] == "sources" and parts != ("sources", "_template.md"):
            return "personal source notes (only sources/_template.md is installable)"

    if is_within(destination, ai_root):
        relative = destination.resolve().relative_to(ai_root.resolve())
        parts = tuple(part.casefold() for part in relative.parts)
        if parts and parts[0] == "papers" and parts != ("papers", "queue_sync.py"):
            return "paper queue, notes, PDFs, or reading data"
        protected_tutor_prefixes = (
            "context_snapshot",
            "completed_papers",
            "idea_seeds",
            "paper_notes",
            "progress",
            "math_gaps",
            "learner_profile",
            "paper_preferences",
            "reading_feedback",
            "feedback",
        )
        if len(parts) >= 2 and parts[0] == "tutor":
            name = parts[1]
            if name != "reading_feedback.py" and name.startswith(protected_tutor_prefixes):
                return "AI Education notes, profile, preferences, progress, or feedback"

    if is_within(destination, tracker_root):
        relative = destination.resolve().relative_to(tracker_root.resolve())
        if relative.parts:
            name = relative.parts[0].casefold()
            if name == "recommendation_profile.example.json":
                return None
            protected_prefixes = (
                "researcher_profile",
                "recommendation_profile",
                "reading_queue",
                "feedback",
            )
            if name.startswith(protected_prefixes):
                return "Paper Tracker profile, feedback, or queue data"
    return None


def render_source(source: Path, variables: dict[str, Path | str]) -> tuple[bytes, str]:
    raw = source.read_bytes()
    text = decode_utf8(raw, source)
    if not text.strip():
        raise InstallError(f"refusing to install an empty source file: {source}")

    def replace(match: re.Match[str]) -> str:
        value = variables.get(match.group(1))
        return str(value) if value is not None else match.group(0)

    rendered = SOURCE_TOKEN_RE.sub(replace, text).encode("utf-8")
    if rendered.startswith(UTF8_BOM) or not rendered.strip():
        raise InstallError(f"refusing unsafe rendered content from: {source}")
    return rendered, sha256_bytes(raw)


def iter_mapping_entries(
    repo_root: Path, mapping: dict[str, Any], selected: set[str]
) -> Iterable[tuple[str, Path, str]]:
    for tree in mapping["trees"]:
        if not isinstance(tree, dict) or tree.get("scope") not in selected:
            continue
        for field in ("source_glob", "source_base", "destination_root"):
            if not isinstance(tree.get(field), str):
                raise InstallError(f"tree mapping is missing {field}: {tree}")
        base = repo_path(repo_root, tree["source_base"])
        matches = sorted(repo_root.glob(tree["source_glob"]), key=lambda path: str(path).casefold())
        if not matches:
            raise InstallError(f"source glob matched no files: {tree['source_glob']}")
        for source in matches:
            source = source.resolve()
            if not source.is_file() or not is_within(source, base):
                raise InstallError(f"unsafe tree source: {source}")
            relative = source.relative_to(base).as_posix()
            destination = f"{tree['destination_root'].rstrip('/\\')}/{relative}"
            yield tree["scope"], source, destination

    for entry in mapping["files"]:
        if not isinstance(entry, dict) or entry.get("scope") not in selected:
            continue
        if not isinstance(entry.get("source"), str) or not isinstance(
            entry.get("destination"), str
        ):
            raise InstallError(f"invalid file mapping: {entry}")
        yield entry["scope"], repo_path(repo_root, entry["source"]), entry["destination"]


def build_plan(
    repo_root: Path,
    mapping: dict[str, Any],
    variables: dict[str, Path | str],
    selected: set[str],
) -> list[InstallItem]:
    plan: list[InstallItem] = []
    destinations: set[str] = set()
    for scope, source, destination_template in iter_mapping_entries(repo_root, mapping, selected):
        if not source.exists():
            raise InstallError(f"required system source is missing: {source}")
        destination = expand_destination(destination_template, variables)
        reason = protected_reason(destination, variables)
        if reason:
            raise InstallError(f"refusing protected destination ({reason}): {destination}")
        key = os.path.normcase(str(destination.resolve()))
        if key in destinations:
            raise InstallError(f"duplicate install destination: {destination}")
        destinations.add(key)
        data, source_hash = render_source(source, variables)
        installed_hash = sha256_bytes(data)
        if destination.exists():
            if not destination.is_file():
                raise InstallError(f"destination is not a regular file: {destination}")
            previous = destination.read_bytes()
            previous_hash = sha256_bytes(previous)
            status = "current" if previous == data else "update"
        else:
            previous_hash = None
            status = "create"
        plan.append(
            InstallItem(
                scope=scope,
                source=source,
                destination=destination,
                source_sha256=source_hash,
                installed_sha256=installed_hash,
                data=data,
                status=status,
                previous_sha256=previous_hash,
            )
        )
    return sorted(plan, key=lambda item: (item.scope, str(item.destination).casefold()))


def backup_path_for(destination: Path, backup_root: Path) -> Path:
    resolved = destination.resolve()
    drive = resolved.drive.rstrip(":\\/") or "root"
    parts = [part for part in resolved.parts if part not in (resolved.anchor, "\\", "/")]
    return backup_root / drive / Path(*parts)


def backup_existing(path: Path, backup_root: Path) -> Path | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise InstallError(f"cannot back up a non-file destination: {path}")
    backup = backup_path_for(path, backup_root)
    atomic_write(backup, path.read_bytes(), allow_bom=True)
    return backup


def expand_config_path(template: str, variables: dict[str, Path | str]) -> Path:
    return expand_destination(template, variables)


def apply_plan(
    repo_root: Path,
    mapping_path: Path,
    mapping: dict[str, Any],
    machine_paths: Path,
    variables: dict[str, Path | str],
    selected: set[str],
    plan: list[InstallItem],
    state_manifest: Path,
    backup_base: Path,
) -> int:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_root = backup_base / timestamp
    records: list[dict[str, Any]] = []
    changed = 0
    for item in plan:
        backup: Path | None = None
        if item.status != "current":
            backup = backup_existing(item.destination, backup_root)
            atomic_write(item.destination, item.data)
            changed += 1
        records.append(
            {
                "scope": item.scope,
                "source": repo_relative(repo_root, item.source),
                "destination": str(item.destination),
                "source_sha256": item.source_sha256,
                "installed_sha256": item.installed_sha256,
                "previous_sha256": item.previous_sha256,
                "backup": str(backup) if backup else None,
                "status": item.status,
                "workflow_version": decode_utf8(
                    repo_path(repo_root, mapping["release_version_file"]).read_bytes(),
                    repo_path(repo_root, mapping["release_version_file"]),
                ).strip(),
            }
        )

    state = {
        "schema": STATE_SCHEMA,
        "schema_version": 1,
        "installer_version": mapping["installer_version"],
        "workflow_version": records[0]["workflow_version"] if records else None,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "source_repository": str(repo_root.resolve()),
        "mapping_manifest": repo_relative(repo_root, mapping_path),
        "mapping_sha256": sha256_bytes(mapping_path.read_bytes()),
        "machine_paths": str(machine_paths.resolve()),
        "scopes": sorted(selected),
        "backup_root": str(backup_root),
        "artifacts": records,
    }
    previous_state_backup = backup_existing(state_manifest, backup_root)
    if previous_state_backup:
        state["previous_state_manifest_backup"] = str(previous_state_backup)
    atomic_write(state_manifest, json_bytes(state))
    print(f"apply complete: {changed} file(s) changed; state: {state_manifest}")
    if changed:
        print(f"backups: {backup_root}")
    return 0


def report_plan(plan: list[InstallItem]) -> tuple[int, int]:
    changed = 0
    for item in plan:
        print(f"{item.status:7} [{item.scope}] {item.destination}")
        if item.status != "current":
            changed += 1
    current = len(plan) - changed
    print(f"summary: {current} current, {changed} create/update, {len(plan)} total")
    return current, changed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely check or install system-only AI Research Tools files. "
            "With no action flag, performs a read-only dry run."
        )
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Read-only drift check; exit 1 on drift.")
    action.add_argument("--dry-run", action="store_true", help="Read-only preview (the default).")
    action.add_argument("--apply", action="store_true", help="Back up and atomically apply changes.")
    parser.add_argument(
        "--scope",
        action="append",
        help="Limit to a scope; repeat or comma-separate values. Use 'all' for every scope.",
    )
    parser.add_argument(
        "--machine-paths",
        type=Path,
        default=Path.home() / ".claude" / "machine_paths.md",
        help="Path to the private machine_paths.md file.",
    )
    parser.add_argument(
        "--mapping",
        default=DEFAULT_MAPPING,
        help=f"Repo-relative mapping manifest (default: {DEFAULT_MAPPING}).",
    )
    parser.add_argument(
        "--state-manifest",
        type=Path,
        help="Override the local installation-state manifest path.",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        help="Override the root directory used for timestamped backups.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        mapping_path = repo_path(repo_root, args.mapping)
        mapping = load_mapping(repo_root, mapping_path)
        selected = select_scopes(mapping, args.scope)
        variables = resolve_variables(args.machine_paths, repo_root, Path.home())
        plan = build_plan(repo_root, mapping, variables, selected)
        _, changed = report_plan(plan)
        if args.apply:
            state_manifest = (
                args.state_manifest.resolve()
                if args.state_manifest
                else expand_config_path(mapping["default_state_manifest"], variables)
            )
            backup_base = (
                args.backup_root.resolve()
                if args.backup_root
                else expand_config_path(mapping["default_backup_root"], variables)
            )
            return apply_plan(
                repo_root,
                mapping_path,
                mapping,
                args.machine_paths,
                variables,
                selected,
                plan,
                state_manifest,
                backup_base,
            )
        if args.check and changed:
            return 1
        return 0
    except InstallError as exc:
        print(f"local install error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
