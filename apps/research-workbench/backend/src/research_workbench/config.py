from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from research_core.machine_paths import MachinePaths, parse_machine_paths
except ImportError:  # pragma: no cover - actionable startup diagnostic handles this
    MachinePaths = object  # type: ignore[misc,assignment]
    parse_machine_paths = None  # type: ignore[assignment]


@dataclass(frozen=True)
class WorkbenchSettings:
    repo_root: Path
    machine_paths_file: Path
    state_root: Path
    tracker_root: Path
    idea_vault: Path
    ai_education_root: Path
    personal_knowledge_vault: Path
    projects_vault: Path
    project_paths: dict[str, Path]
    skill_roots: tuple[Path, ...]
    portable_state_configured: bool = False
    reading_thread_name: str = "论文阅读 · Trevor"
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    )

    @property
    def workbench_root(self) -> Path:
        return self.state_root / "workbench"

    @property
    def allowed_roots(self) -> tuple[Path, ...]:
        roots = {
            self.repo_root.resolve(),
            self.state_root.resolve(),
            self.tracker_root.resolve(),
            self.idea_vault.resolve(),
            self.ai_education_root.resolve(),
            self.personal_knowledge_vault.resolve(),
            self.projects_vault.resolve(),
            *(path.resolve() for path in self.project_paths.values()),
        }
        return tuple(sorted(roots, key=str))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def load_settings(
    *,
    machine_paths_file: Path | None = None,
    state_root: Path | None = None,
    tracker_root: Path | None = None,
    idea_vault: Path | None = None,
    ai_education_root: Path | None = None,
    personal_knowledge_vault: Path | None = None,
    projects_vault: Path | None = None,
    project_paths: dict[str, Path] | None = None,
) -> WorkbenchSettings:
    repo = _repo_root()
    machine_file = machine_paths_file or Path(
        os.environ.get("RESEARCH_WORKBENCH_MACHINE_PATHS", Path.home() / ".claude" / "machine_paths.md")
    )
    paths = None
    if parse_machine_paths is not None and machine_file.exists():
        paths = parse_machine_paths(machine_file)

    default_state = repo / "apps" / "research-workbench" / ".workbench-state"
    environment_state = os.environ.get("RESEARCH_WORKBENCH_STATE_ROOT", "").strip()
    configured_state = state_root or (Path(environment_state) if environment_state else None) or getattr(
        paths, "workbench_state_root", None
    )
    resolved_state = Path(configured_state or default_state)
    resolved_tracker = tracker_root or Path(os.environ.get("RESEARCH_WORKBENCH_TRACKER_ROOT", "") or (
        getattr(paths, "paper_tracker_root", None) or repo / "packages" / "paper-tracker"
    ))
    resolved_ideas = idea_vault or Path(os.environ.get("RESEARCH_WORKBENCH_IDEA_VAULT", "") or (
        getattr(paths, "idea_vault", None) or repo / "packages" / "idea-pipeline" / "obsidian" / "JMP Idea"
    ))
    resolved_ai = ai_education_root or Path(os.environ.get("RESEARCH_WORKBENCH_AI_EDUCATION_ROOT", "") or (
        getattr(paths, "ai_education_root", None) or repo / "packages" / "ai-education"
    ))
    resolved_knowledge = personal_knowledge_vault or Path(
        os.environ.get("RESEARCH_WORKBENCH_PERSONAL_KNOWLEDGE_VAULT", "") or (
            getattr(paths, "personal_knowledge_vault", None) or repo / "personal-knowledge"
        )
    )
    resolved_projects = projects_vault or Path(
        os.environ.get("RESEARCH_WORKBENCH_PROJECTS_VAULT", "") or (
            getattr(paths, "projects_vault", None) or repo / "projects"
        )
    )
    resolved_project_paths = dict(
        project_paths if project_paths is not None else getattr(paths, "project_roots", {}) or {}
    )
    skills = (
        repo / "packages" / "codex" / "skills",
        Path.home() / ".codex" / "skills",
        Path.home() / ".agents" / "skills",
    )
    return WorkbenchSettings(
        repo_root=repo,
        machine_paths_file=machine_file,
        state_root=resolved_state,
        tracker_root=resolved_tracker,
        idea_vault=resolved_ideas,
        ai_education_root=resolved_ai,
        personal_knowledge_vault=resolved_knowledge,
        projects_vault=resolved_projects,
        project_paths=resolved_project_paths,
        skill_roots=skills,
        portable_state_configured=configured_state is not None,
        reading_thread_name=os.environ.get("RESEARCH_WORKBENCH_READING_THREAD", "论文阅读 · Trevor").strip(),
    )
