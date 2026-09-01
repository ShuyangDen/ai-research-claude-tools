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
    skill_roots: tuple[Path, ...]
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
) -> WorkbenchSettings:
    repo = _repo_root()
    machine_file = machine_paths_file or Path(
        os.environ.get("RESEARCH_WORKBENCH_MACHINE_PATHS", Path.home() / ".claude" / "machine_paths.md")
    )
    paths = None
    if parse_machine_paths is not None and machine_file.exists():
        paths = parse_machine_paths(machine_file)

    default_state = repo / "apps" / "research-workbench" / ".workbench-state"
    resolved_state = state_root or Path(
        os.environ.get("RESEARCH_WORKBENCH_STATE_ROOT", "") or default_state
    )
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
        skill_roots=skills,
    )
