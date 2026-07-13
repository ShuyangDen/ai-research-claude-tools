"""Read-only diagnostics for paths, text integrity, and installed-file drift."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .machine_paths import MachinePaths, parse_machine_paths
from .util import read_text, sha256_file


_TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yaml", ".yml", ".txt", ".ps1"}
_MOJIBAKE_MARKERS = (
    "\ufffd",
    "\u9225",
    "\u922b",
    "\u59dd\uff45",
    "\u6d63\u72b3",
    "\u9354\u72ba\u6d47",
    "\u7ed4\u5b2a\u5d46",
    "\u93b4\u6223",
)
_MOJIBAKE_PATTERNS = (
    ("three or more replacement question marks", re.compile(r"\?{3,}")),
    (
        "Unicode private-use character",
        re.compile(r"[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]"),
    ),
)
_PLACEHOLDER_PATTERNS = (
    re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}"),
    re.compile(r"\$\(System\.Collections\.Hashtable\.Name\)"),
    re.compile(r"<YOUR_[A-Z0-9_ -]+>"),
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def check_paths(paths: MachinePaths) -> list[Finding]:
    findings: list[Finding] = []
    for name, path in paths.configured_paths().items():
        if not path.exists():
            findings.append(Finding("error", "path.missing", f"Configured {name} does not exist", str(path)))
    required = {
        "personal_knowledge_vault": paths.personal_knowledge_vault,
        "idea_vault": paths.idea_vault,
        "ai_education_root": paths.ai_education_root,
        "paper_tracker_root": paths.paper_tracker_root,
    }
    for name, value in required.items():
        if value is None:
            findings.append(Finding("warning", "path.unconfigured", f"{name} is not configured"))
    return findings


def _iter_text_files(roots: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            yield root
            continue
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            if any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts):
                continue
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield path


def check_text_integrity(roots: Iterable[str | Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_text_files(Path(root) for root in roots):
        if not path.exists():
            findings.append(Finding("error", "scan.missing", "Scan root does not exist", str(path)))
            continue
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            findings.append(Finding("error", "encoding.invalid_utf8", str(exc), str(path)))
            continue
        if raw.startswith(b"\xef\xbb\xbf"):
            findings.append(Finding("warning", "encoding.bom", "UTF-8 BOM present", str(path)))
        for line_number, line in enumerate(text.splitlines(), start=1):
            mojibake_message: str | None = None
            mojibake_severity = "error"
            for marker in _MOJIBAKE_MARKERS:
                if marker in line:
                    mojibake_message = f"Possible mojibake marker {marker!r}"
                    break
            if mojibake_message is None:
                for label, pattern in _MOJIBAKE_PATTERNS:
                    if pattern.search(line):
                        mojibake_message = f"Possible mojibake: {label}"
                        # PDF-to-text tools commonly emit private-use glyphs
                        # for embedded fonts. Keep them visible, but do not
                        # misclassify an extracted paper corpus as corrupted.
                        if label == "Unicode private-use character":
                            mojibake_severity = "warning"
                        break
            if mojibake_message is not None:
                findings.append(Finding(mojibake_severity, "encoding.mojibake", mojibake_message, str(path), line_number))
            for pattern in _PLACEHOLDER_PATTERNS:
                match = pattern.search(line)
                if match:
                    findings.append(
                        Finding(
                            "warning",
                            "placeholder.unresolved",
                            f"Unresolved placeholder {match.group(0)!r}",
                            str(path),
                            line_number,
                        )
                    )
                    break
    return findings


def check_install_manifest(path: str | Path) -> list[Finding]:
    manifest_path = Path(path).resolve()
    findings: list[Finding] = []
    try:
        manifest = json.loads(read_text(manifest_path))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [Finding("error", "install_manifest.invalid", str(exc), str(manifest_path))]
    entries = manifest.get("files")
    if entries is None:
        entries = manifest.get("artifacts")
    if not isinstance(entries, list):
        return [Finding("error", "install_manifest.invalid", "files or artifacts must be an array", str(manifest_path))]

    source_repository = manifest.get("source_repository")
    preferred_source_root: Path | None = None
    if isinstance(source_repository, str) and source_repository:
        preferred_source_root = Path(source_repository).expanduser()
        if not preferred_source_root.is_absolute():
            preferred_source_root = (manifest_path.parent / preferred_source_root).resolve()

    source_manifest = manifest.get("source_manifest")

    def infer_repository_root() -> Path | None:
        if preferred_source_root is not None:
            return preferred_source_root
        if not isinstance(source_manifest, dict) or not source_manifest.get("path"):
            return manifest_path.parent
        anchor = Path(str(source_manifest["path"]))
        if anchor.is_absolute():
            return None
        candidates: list[tuple[Path, Path]] = []
        for ancestor in manifest_path.parents:
            target = ancestor / anchor
            if target.is_file():
                candidates.append((ancestor, target))
        expected = source_manifest.get("sha256")
        matching = [item for item in candidates if isinstance(expected, str) and sha256_file(item[1]) == expected]
        viable = matching or candidates
        if len(viable) == 1:
            return viable[0][0]
        code = "install_manifest.repo_root_ambiguous" if viable else "install_manifest.repo_root_unresolved"
        detail = "multiple source_manifest anchors match" if viable else "source_manifest anchor was not found above the manifest"
        findings.append(Finding("error", code, detail, str(manifest_path)))
        return None

    repository_root = infer_repository_root()

    def resolve(raw: object, *, preferred_root: Path | None = None) -> Path:
        candidate = Path(str(raw))
        if candidate.is_absolute():
            return candidate
        if preferred_root is not None:
            return preferred_root / candidate
        return manifest_path.parent / candidate

    def verify(target: Path, expected: object, *, missing_code: str, drift_code: str, label: str) -> None:
        if not target.exists():
            findings.append(Finding("error", missing_code, f"{label} is missing", str(target)))
            return
        if not target.is_file():
            findings.append(Finding("error", missing_code, f"{label} is not a regular file", str(target)))
            return
        if isinstance(expected, str) and expected and sha256_file(target) != expected:
            findings.append(Finding("error", drift_code, f"{label} hash differs", str(target)))

    if isinstance(source_manifest, dict) and source_manifest.get("path"):
        anchor = Path(str(source_manifest["path"]))
        if anchor.is_absolute() or repository_root is not None:
            verify(
                anchor if anchor.is_absolute() else resolve(anchor, preferred_root=repository_root),
                source_manifest.get("sha256"),
                missing_code="install.source_manifest_missing",
                drift_code="install.source_manifest_drift",
                label="Source manifest",
            )

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            findings.append(Finding("error", "install_manifest.entry", f"Entry {index} is not an object", str(manifest_path)))
            continue
        source_raw = entry.get("source")
        installed_raw = entry.get("installed", entry.get("destination"))
        if source_raw and installed_raw:
            source = resolve(source_raw, preferred_root=preferred_source_root)
            installed = resolve(installed_raw)
            verify(
                source,
                entry.get("source_sha256"),
                missing_code="install.source_missing",
                drift_code="install.source_drift",
                label="Source file",
            )
            verify(
                installed,
                entry.get("installed_sha256") or entry.get("rendered_sha256"),
                missing_code="install.target_missing",
                drift_code="install.target_drift",
                label="Installed file",
            )
            continue

        artifact_raw = entry.get("path")
        if artifact_raw:
            if repository_root is None:
                continue
            verify(
                resolve(artifact_raw, preferred_root=repository_root),
                entry.get("sha256"),
                missing_code="install.artifact_missing",
                drift_code="install.artifact_drift",
                label="Repository artifact",
            )
            canonical_raw = entry.get("canonical_source_path")
            if canonical_raw:
                verify(
                    resolve(canonical_raw, preferred_root=repository_root),
                    entry.get("canonical_source_sha256"),
                    missing_code="install.source_missing",
                    drift_code="install.source_drift",
                    label="Canonical source",
                )
            continue

        findings.append(
            Finding(
                "error",
                "install_manifest.entry",
                f"Entry {index} needs source+installed/destination or path+sha256",
                str(manifest_path),
            )
        )
    return findings


def run_doctor(
    *,
    machine_paths_path: str | Path | None = None,
    scan_roots: Iterable[str | Path] = (),
    install_manifest: str | Path | None = None,
) -> dict[str, object]:
    findings: list[Finding] = []
    if machine_paths_path is not None:
        try:
            findings.extend(check_paths(parse_machine_paths(machine_paths_path)))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            findings.append(Finding("error", "machine_paths.invalid", str(exc), str(machine_paths_path)))
    findings.extend(check_text_integrity(scan_roots))
    if install_manifest is not None:
        findings.extend(check_install_manifest(install_manifest))
    counts = {severity: sum(item.severity == severity for item in findings) for severity in ("error", "warning", "info")}
    return {
        "ok": counts["error"] == 0,
        "counts": counts,
        "findings": [item.to_dict() for item in findings],
    }
