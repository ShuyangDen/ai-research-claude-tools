"""Parse the existing Markdown machine-paths file into an explicit model."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .util import read_text


_MISSING_VALUES = {
    "",
    "none",
    "null",
    "not configured",
    "not set",
    "not set up",
    "not set up on this machine",
    "未配置",
    "未设置",
}


def _normal(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    value = value.replace("→", " ").replace("/", " ").replace("_", " ")
    value = re.sub(r"[`*_#]", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return " ".join(value.split())


def _clean_value(value: str) -> str | None:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
        value = value[1:-1]
    value = value.strip().rstrip("\\/") if len(value.strip()) > 3 else value.strip()
    if _normal(value) in _MISSING_VALUES:
        return None
    return value


@dataclass(frozen=True)
class MachinePaths:
    source: Path | None = None
    tools_root: Path | None = None
    personal_knowledge_vault: Path | None = None
    idea_vault: Path | None = None
    zotero_config: Path | None = None
    ai_education_root: Path | None = None
    papers_root: Path | None = None
    textbooks_root: Path | None = None
    paper_tracker_root: Path | None = None
    paper_tracker_profile: Path | None = None
    paper_tracker_repo: str | None = None
    projects_vault: Path | None = None
    workflow_state_root: Path | None = None
    raw: dict[str, dict[str, str | None]] = field(default_factory=dict)

    def configured_paths(self) -> dict[str, Path]:
        result: dict[str, Path] = {}
        for name in (
            "tools_root",
            "personal_knowledge_vault",
            "idea_vault",
            "zotero_config",
            "ai_education_root",
            "papers_root",
            "textbooks_root",
            "paper_tracker_root",
            "paper_tracker_profile",
            "projects_vault",
            "workflow_state_root",
        ):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Path):
                data[key] = str(value)
        if self.source is not None:
            data["source"] = str(self.source)
        return data


def _path(value: str | None, *, base: Path | None = None) -> Path | None:
    if value is None:
        return None
    expanded = os.path.expandvars(os.path.expanduser(value))
    candidate = Path(expanded)
    if not candidate.is_absolute() and base is not None:
        candidate = base / candidate
    return candidate


def _lookup(
    sections: dict[str, dict[str, str | None]],
    section_aliases: Iterable[str],
    key_aliases: Iterable[str],
) -> str | None:
    normalized_sections = {_normal(name): values for name, values in sections.items()}
    normalized_section_aliases = {_normal(value) for value in section_aliases}
    normalized_key_aliases = {_normal(value) for value in key_aliases}
    for section_name, values in normalized_sections.items():
        if section_name not in normalized_section_aliases:
            continue
        for key, value in values.items():
            if _normal(key) in normalized_key_aliases:
                return value
    return None


def parse_machine_paths_text(text: str, *, source: Path | None = None) -> MachinePaths:
    """Parse headings plus Markdown bullets, tolerating bold labels and BOMs."""
    text = text.lstrip("\ufeff")
    sections: dict[str, dict[str, str | None]] = {}
    current = "root"
    sections[current] = {}
    heading = re.compile(r"^\s*#{2,6}\s+(.+?)\s*$")
    item = re.compile(r"^\s*[-*+]\s+(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:\s*(.*?)\s*$")
    plain_item = re.compile(r"^\s*([^:#][^:]{1,80})\s*:\s*(.*?)\s*$")

    for line in text.splitlines():
        heading_match = heading.match(line)
        if heading_match:
            current = heading_match.group(1).strip()
            sections.setdefault(current, {})
            continue
        item_match = item.match(line) or plain_item.match(line)
        if item_match:
            label = item_match.group(1).strip().strip("*")
            sections[current][label] = _clean_value(item_match.group(2))

    base = source.parent if source is not None else None
    tools_root = _lookup(sections, ["AI Research Tools", "Research Tools"], ["Source root", "Project root", "Path", "Root"])
    pkb = _lookup(sections, ["Personal Knowledge Wiki", "Personal Knowledge Base"], ["Vault", "Path", "Root"])
    idea = _lookup(sections, ["Research Idea Pipeline", "Idea Pipeline", "JMP Idea"], ["Vault", "Path", "Root"])
    zotero = _lookup(sections, ["Research Idea Pipeline", "Idea Pipeline", "Zotero"], ["Zotero config", "Config"])
    ai_root = _lookup(sections, ["AI Education Project", "AI Education"], ["Project root", "Path", "Root"])
    papers = _lookup(sections, ["AI Education Project", "AI Education"], ["Papers", "Papers root"])
    textbooks = _lookup(sections, ["AI Education Project", "AI Education"], ["Textbooks", "Textbooks root"])
    tracker = _lookup(sections, ["Paper Tracker"], ["Project root", "Path", "Root"])
    tracker_profile = _lookup(sections, ["Paper Tracker"], ["Researcher profile", "Profile"])
    tracker_repo = _lookup(sections, ["Paper Tracker"], ["PAPER_TRACKER_REPO", "Repository", "Repo"])
    projects = _lookup(sections, ["Projects", "Projects Vault"], ["Vault", "Path", "Root"])
    state_root = _lookup(sections, ["Workflow State", "Research Core", "Orchestrator"], ["Root", "Path", "State root"])

    return MachinePaths(
        source=source,
        tools_root=_path(tools_root, base=base),
        personal_knowledge_vault=_path(pkb, base=base),
        idea_vault=_path(idea, base=base),
        zotero_config=_path(zotero, base=base),
        ai_education_root=_path(ai_root, base=base),
        papers_root=_path(papers, base=base),
        textbooks_root=_path(textbooks, base=base),
        paper_tracker_root=_path(tracker, base=base),
        paper_tracker_profile=_path(tracker_profile, base=base),
        paper_tracker_repo=tracker_repo,
        projects_vault=_path(projects, base=base),
        workflow_state_root=_path(state_root, base=base),
        raw=sections,
    )


def parse_machine_paths(path: str | Path) -> MachinePaths:
    source = Path(path)
    return parse_machine_paths_text(read_text(source), source=source)
