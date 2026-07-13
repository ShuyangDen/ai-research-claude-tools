#!/usr/bin/env python3
"""Build and verify Codex workflow adapters and the repo-local plugin.

Claude command markdown is canonical for ``generated`` adapters.  Hand-written
Codex-only workflows are declared as ``passthrough`` and are never rewritten in
``packages/codex``; they are only mirrored into the plugin.
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
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = "packages/codex/workflow-adapters.json"
ADAPTER_SCHEMA = "ai-research-tools.workflow-adapters"
SKILL_SCHEMA = "ai-research-tools.codex-skill-adapter"
INSTALL_SCHEMA = "ai-research-tools.install-manifest"
PLUGIN_INSTALL_SCHEMA = "ai-research-tools.plugin-install-manifest"
CLAUDE_COMMAND_SCHEMA = "ai-research-tools.claude-command"
UTF8_BOM = b"\xef\xbb\xbf"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
FORBIDDEN_TEXT = (
    "$(System.Collections.Hashtable.Name)",
    "\ufffd",
    "\u9225\u65ba",
    "\u922b\u6265",
    "\u59dd\uff45\u6e6a",
    "\u6d63\u72b3\u5142",
    "?" * 4,
)


class AdapterError(RuntimeError):
    """Raised when an adapter manifest or source is unsafe or inconsistent."""


@dataclass(frozen=True)
class BuildPlan:
    expected_files: dict[Path, bytes]
    generated_package_paths: frozenset[Path]
    active_plugin_skill_paths: frozenset[Path]
    active_plugin_command_paths: frozenset[Path]
    active_names: tuple[str, ...]
    planned_names: tuple[str, ...]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    return text.encode("utf-8")


def decode_utf8(data: bytes, path: Path) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AdapterError(f"not valid UTF-8: {path}: {exc}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalized_utf8(data: bytes, path: Path) -> bytes:
    text = decode_utf8(data, path)
    return text.encode("utf-8")


def assert_clean_text(text: str, path: Path) -> None:
    found = [marker for marker in FORBIDDEN_TEXT if marker in text]
    if found:
        markers = ", ".join(repr(marker) for marker in found)
        raise AdapterError(f"forbidden mojibake/generator marker in {path}: {markers}")
    match = re.search(r"<YOUR_[A-Z0-9_]+>", text)
    if match:
        raise AdapterError(f"unresolved setup placeholder in runtime workflow {path}: {match.group(0)}")


def resolve_repo_path(repo_root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise AdapterError(f"manifest path must be repo-relative: {relative}")
    root = repo_root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AdapterError(f"manifest path escapes repository: {relative}") from exc
    return resolved


def repo_relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def read_required(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise AdapterError(f"required file is missing: {path}") from exc


def load_manifest(repo_root: Path, manifest_path: Path) -> tuple[dict[str, Any], bytes]:
    raw = read_required(manifest_path)
    text = decode_utf8(raw, manifest_path)
    if raw.startswith(UTF8_BOM):
        raise AdapterError(f"adapter manifest must be UTF-8 without BOM: {manifest_path}")
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"invalid adapter manifest JSON: {manifest_path}: {exc}") from exc
    if manifest.get("schema") != ADAPTER_SCHEMA or manifest.get("schema_version") != 1:
        raise AdapterError("unsupported workflow adapter schema")
    adapters = manifest.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        raise AdapterError("workflow adapter manifest must contain a non-empty adapters list")
    expected_default = resolve_repo_path(repo_root, DEFAULT_MANIFEST)
    if manifest_path.resolve() != expected_default and not manifest_path.exists():
        raise AdapterError(f"manifest does not exist: {manifest_path}")
    return manifest, raw


def load_plugin_manifest(path: Path, workflow_version: str) -> tuple[dict[str, Any], bytes]:
    raw = read_required(path)
    if raw.startswith(UTF8_BOM):
        raise AdapterError(f"plugin manifest must be UTF-8 without BOM: {path}")
    text = decode_utf8(raw, path)
    if "[TODO:" in text:
        raise AdapterError(f"plugin manifest contains TODO placeholder: {path}")
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"invalid plugin manifest JSON: {path}: {exc}") from exc
    if manifest.get("name") != "ai-research-tools":
        raise AdapterError(f"unexpected plugin name in {path}")
    if manifest.get("version") != workflow_version:
        raise AdapterError(
            f"plugin version in {path} must match {workflow_version}, "
            f"got {manifest.get('version')!r}"
        )
    forbidden_keys = {"token", "secret", "password", "api_key", "apikey"}
    if any(key.casefold() in forbidden_keys for key in manifest):
        raise AdapterError(f"plugin manifest contains a credential field: {path}")
    if re.search(r"(?<![A-Za-z])(?:[A-Za-z]:[\\/]|/(?:Users|home)/)", text):
        raise AdapterError(f"plugin manifest contains a machine-specific path: {path}")
    return manifest, raw


def render_skill(
    adapter: dict[str, Any],
    source_text: str,
    source_sha256: str,
    workflow_version: str,
    generator_version: str,
) -> bytes:
    name = adapter["name"]
    description = adapter.get("description")
    natural_trigger = adapter.get("natural_trigger")
    if not isinstance(description, str) or not description.strip():
        raise AdapterError(f"generated adapter {name} needs a non-empty description")
    if not isinstance(natural_trigger, str) or not natural_trigger.strip():
        raise AdapterError(f"generated adapter {name} needs a non-empty natural_trigger")

    metadata = {
        "generator_version": generator_version,
        "schema": SKILL_SCHEMA,
        "schema_version": 1,
        "source_path": adapter["canonical_source_path"],
        "source_sha256": source_sha256,
        "workflow_version": workflow_version,
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    canonical = source_text.rstrip("\n")
    rendered = f"""---
name: {name}
description: {json.dumps(description, ensure_ascii=False)}
---
# {name}

<!-- workflow-adapter: {metadata_json} -->

## Trigger Forms

- ${name}
- /{name}
- {natural_trigger}

## Codex Execution Rules

- Do **not** read `~/.claude/commands/{name}.md` at runtime; the canonical Claude command is embedded below.
- Read `~/.claude/machine_paths.md` before resolving project or vault paths.
- Preserve Claude command files and unrelated user data.
- Follow Codex filesystem and approval rules for writes outside the current workspace.
- Do not take destructive actions unless the user explicitly requests them.
- Stop at every confirmation checkpoint in the canonical workflow and wait for explicit user approval.

## Canonical Workflow

{canonical}
"""
    assert_clean_text(rendered, Path(adapter["package_path"]))
    data = rendered.encode("utf-8")
    if data.startswith(UTF8_BOM) or b"\r" in data:
        raise AdapterError(f"generator produced non-normalized UTF-8 for {name}")
    return data


def validate_manifest_entries(repo_root: Path, adapters: list[dict[str, Any]]) -> None:
    names: set[str] = set()
    package_paths: set[Path] = set()
    for index, adapter in enumerate(adapters):
        if not isinstance(adapter, dict):
            raise AdapterError(f"adapter #{index} is not an object")
        name = adapter.get("name")
        mode = adapter.get("mode")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise AdapterError(f"invalid adapter name at index {index}: {name!r}")
        if name in names:
            raise AdapterError(f"duplicate adapter name: {name}")
        names.add(name)
        if mode not in {"generated", "passthrough", "planned"}:
            raise AdapterError(f"invalid adapter mode for {name}: {mode!r}")
        for field in ("canonical_source_path", "package_path"):
            if not isinstance(adapter.get(field), str):
                raise AdapterError(f"adapter {name} is missing {field}")
            resolve_repo_path(repo_root, adapter[field])
        package_path = resolve_repo_path(repo_root, adapter["package_path"])
        if package_path in package_paths:
            raise AdapterError(f"duplicate package_path: {adapter['package_path']}")
        package_paths.add(package_path)
        expected_suffix = Path("packages") / "codex" / "skills" / name / "SKILL.md"
        if Path(adapter["package_path"]) != expected_suffix:
            raise AdapterError(f"adapter {name} must target {expected_suffix.as_posix()}")
        if mode == "planned" and adapter.get("required", True) is not False:
            raise AdapterError(f"planned adapter {name} must set required=false")

    actual = {
        path.resolve()
        for path in (repo_root / "packages" / "codex" / "skills").glob("*/SKILL.md")
    }
    declared = {
        resolve_repo_path(repo_root, adapter["package_path"])
        for adapter in adapters
        if adapter["mode"] != "planned"
    }
    unmanaged = sorted(repo_relative(repo_root, path) for path in actual - declared)
    if unmanaged:
        raise AdapterError(f"package skills missing from adapter manifest: {', '.join(unmanaged)}")


def build_plan(repo_root: Path, manifest_path: Path) -> BuildPlan:
    manifest, manifest_raw = load_manifest(repo_root, manifest_path)
    adapters: list[dict[str, Any]] = manifest["adapters"]
    validate_manifest_entries(repo_root, adapters)

    generator_version = manifest.get("generator_version")
    if not isinstance(generator_version, str) or not SEMVER_RE.fullmatch(generator_version):
        raise AdapterError("generator_version must be strict semver")

    version_path = resolve_repo_path(repo_root, manifest["release_version_file"])
    version_raw = read_required(version_path)
    workflow_version = decode_utf8(version_raw, version_path).strip()
    if not SEMVER_RE.fullmatch(workflow_version):
        raise AdapterError(f"invalid workflow version in {version_path}: {workflow_version!r}")

    plugin_root = resolve_repo_path(repo_root, manifest["plugin_root"])
    codex_plugin_manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    _, codex_plugin_manifest_raw = load_plugin_manifest(
        codex_plugin_manifest_path, workflow_version
    )
    claude_plugin_manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    _, claude_plugin_manifest_raw = load_plugin_manifest(
        claude_plugin_manifest_path, workflow_version
    )

    expected: dict[Path, bytes] = {}
    generated_package_paths: set[Path] = set()
    active_plugin_skill_paths: set[Path] = set()
    active_plugin_command_paths: set[Path] = set()
    package_records: list[dict[str, Any]] = []
    plugin_records: list[dict[str, Any]] = []
    active_names: list[str] = []
    planned_names: list[str] = []

    for adapter in adapters:
        name = adapter["name"]
        mode = adapter["mode"]
        if mode == "planned":
            planned_names.append(name)
            continue

        source_path = resolve_repo_path(repo_root, adapter["canonical_source_path"])
        package_path = resolve_repo_path(repo_root, adapter["package_path"])
        source_raw = read_required(source_path)
        source_text = decode_utf8(source_raw, source_path)
        assert_clean_text(source_text, source_path)
        source_hash = sha256_bytes(source_raw)

        if mode == "generated":
            package_bytes = render_skill(
                adapter,
                source_text,
                source_hash,
                workflow_version,
                generator_version,
            )
            expected[package_path] = package_bytes
            generated_package_paths.add(package_path)
        else:
            if source_path.resolve() != package_path.resolve():
                raise AdapterError(f"passthrough adapter {name} source and package path must match")
            if source_raw.startswith(UTF8_BOM):
                raise AdapterError(f"passthrough skill must be UTF-8 without BOM: {source_path}")
            package_bytes = source_raw

        plugin_path = plugin_root / "skills" / name / "SKILL.md"
        plugin_bytes = normalized_utf8(package_bytes, package_path)
        plugin_text = decode_utf8(plugin_bytes, plugin_path)
        assert_clean_text(plugin_text, plugin_path)
        if plugin_bytes.startswith(UTF8_BOM) or b"\r" in plugin_bytes:
            raise AdapterError(f"plugin skill is not UTF-8/LF normalized: {plugin_path}")
        expected[plugin_path] = plugin_bytes
        active_plugin_skill_paths.add(plugin_path)
        if mode == "generated":
            command_path = plugin_root / "commands" / f"{name}.md"
            command_bytes = normalized_utf8(source_raw, source_path)
            assert_clean_text(decode_utf8(command_bytes, command_path), command_path)
            expected[command_path] = command_bytes
            active_plugin_command_paths.add(command_path)
        active_names.append(name)

        common_record = {
            "name": name,
            "mode": mode,
            "canonical_source_path": adapter["canonical_source_path"],
            "canonical_source_sha256": source_hash,
            "adapter_schema": SKILL_SCHEMA if mode == "generated" else "passthrough",
            "adapter_schema_version": 1,
            "workflow_version": workflow_version,
        }
        package_records.append(
            {
                **common_record,
                "path": adapter["package_path"],
                "sha256": sha256_bytes(package_bytes),
            }
        )
        plugin_records.append(
            {
                **common_record,
                "path": repo_relative(repo_root, plugin_path),
                "sha256": sha256_bytes(plugin_bytes),
            }
        )
        if mode == "generated":
            plugin_records.append(
                {
                    **common_record,
                    "kind": "claude-command",
                    "adapter_schema": CLAUDE_COMMAND_SCHEMA,
                    "path": repo_relative(repo_root, command_path),
                    "sha256": sha256_bytes(command_bytes),
                }
            )

    plugin_adapter_manifest_path = plugin_root / "workflow-adapters.json"
    plugin_adapter_manifest_bytes = normalized_utf8(manifest_raw, manifest_path)
    expected[plugin_adapter_manifest_path] = plugin_adapter_manifest_bytes

    source_manifest_record = {
        "path": repo_relative(repo_root, manifest_path),
        "sha256": sha256_bytes(manifest_raw),
    }
    planned_records = [
        {
            "name": adapter["name"],
            "canonical_source_path": adapter["canonical_source_path"],
            "package_path": adapter["package_path"],
            "required": False,
        }
        for adapter in adapters
        if adapter["mode"] == "planned"
    ]

    package_install = {
        "schema": INSTALL_SCHEMA,
        "schema_version": 1,
        "generator_version": generator_version,
        "workflow_version": workflow_version,
        "source_manifest": source_manifest_record,
        "artifacts": [
            {
                "kind": "version",
                "path": repo_relative(repo_root, version_path),
                "sha256": sha256_bytes(version_raw),
            },
            *package_records,
        ],
        "planned_adapters": planned_records,
    }
    package_install_path = resolve_repo_path(repo_root, manifest["package_install_manifest"])
    expected[package_install_path] = json_bytes(package_install)

    plugin_install = {
        "schema": PLUGIN_INSTALL_SCHEMA,
        "schema_version": 1,
        "generator_version": generator_version,
        "workflow_version": workflow_version,
        "source_manifest": {
            "path": repo_relative(repo_root, plugin_adapter_manifest_path),
            "sha256": sha256_bytes(plugin_adapter_manifest_bytes),
        },
        "artifacts": [
            {
                "kind": "codex-plugin-manifest",
                "path": repo_relative(repo_root, codex_plugin_manifest_path),
                "sha256": sha256_bytes(codex_plugin_manifest_raw),
            },
            {
                "kind": "claude-plugin-manifest",
                "path": repo_relative(repo_root, claude_plugin_manifest_path),
                "sha256": sha256_bytes(claude_plugin_manifest_raw),
            },
            *plugin_records,
        ],
        "planned_adapters": planned_records,
    }
    plugin_install_path = resolve_repo_path(repo_root, manifest["plugin_install_manifest"])
    expected[plugin_install_path] = json_bytes(plugin_install)

    return BuildPlan(
        expected_files=expected,
        generated_package_paths=frozenset(generated_package_paths),
        active_plugin_skill_paths=frozenset(active_plugin_skill_paths),
        active_plugin_command_paths=frozenset(active_plugin_command_paths),
        active_names=tuple(active_names),
        planned_names=tuple(planned_names),
    )


def atomic_write(path: Path, data: bytes) -> None:
    if data.startswith(UTF8_BOM):
        raise AdapterError(f"refusing to write UTF-8 BOM: {path}")
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


def write_plan(plan: BuildPlan) -> int:
    changed = 0
    for path, expected in sorted(plan.expected_files.items(), key=lambda item: str(item[0])):
        actual = path.read_bytes() if path.exists() else None
        if actual == expected:
            continue
        atomic_write(path, expected)
        changed += 1
        print(f"wrote {path}")
    print(
        f"adapter write complete: {len(plan.active_names)} active, "
        f"{len(plan.planned_names)} planned, {changed} files changed"
    )
    return 0


def check_plan(repo_root: Path, plan: BuildPlan, plugin_root: Path) -> int:
    problems: list[str] = []
    for path, expected in sorted(plan.expected_files.items(), key=lambda item: str(item[0])):
        if not path.exists():
            problems.append(f"missing: {repo_relative(repo_root, path)}")
            continue
        actual = path.read_bytes()
        if actual != expected:
            problems.append(f"out of date: {repo_relative(repo_root, path)}")

    actual_plugin_skills = {
        path.resolve() for path in (plugin_root / "skills").glob("*/SKILL.md")
    }
    unmanaged_plugin = sorted(
        repo_relative(repo_root, path)
        for path in actual_plugin_skills - set(plan.active_plugin_skill_paths)
    )
    problems.extend(f"unmanaged plugin skill: {path}" for path in unmanaged_plugin)

    actual_plugin_commands = {
        path.resolve() for path in (plugin_root / "commands").glob("*.md")
    }
    unmanaged_commands = sorted(
        repo_relative(repo_root, path)
        for path in actual_plugin_commands - set(plan.active_plugin_command_paths)
    )
    problems.extend(f"unmanaged plugin command: {path}" for path in unmanaged_commands)

    if problems:
        print("workflow adapter check failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1
    print(
        f"workflow adapter check passed: {len(plan.active_names)} active, "
        f"{len(plan.planned_names)} planned"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or verify Codex workflow adapters and plugin skills."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Verify generated files and hashes.")
    action.add_argument("--write", action="store_true", help="Atomically write generated files.")
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help=f"Repo-relative adapter manifest (default: {DEFAULT_MANIFEST}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        manifest_path = resolve_repo_path(repo_root, args.manifest)
        manifest, _ = load_manifest(repo_root, manifest_path)
        plan = build_plan(repo_root, manifest_path)
        plugin_root = resolve_repo_path(repo_root, manifest["plugin_root"])
        if args.write:
            return write_plan(plan)
        return check_plan(repo_root, plan, plugin_root)
    except AdapterError as exc:
        print(f"workflow adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
