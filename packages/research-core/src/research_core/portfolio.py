"""Read-only portfolio snapshot used by the JMP dashboard workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .s2check import parse_frontmatter
from .util import read_text, stable_hash, utc_now


PORTFOLIO_ROLES = {"primary", "backup", "parked", "none", ""}


def _idea_records(idea_vault: Path) -> list[dict[str, Any]]:
    ideas_dir = idea_vault / "ideas"
    output: list[dict[str, Any]] = []
    ignored = {"index.md", "log.md", "idea-map.md"}
    for path in sorted(ideas_dir.glob("*.md")):
        if path.name.startswith("_") or path.name in ignored:
            continue
        frontmatter, _, _ = parse_frontmatter(read_text(path))
        role = frontmatter.get("portfolio_role", "none").casefold()
        if role not in PORTFOLIO_ROLES:
            role = "invalid"
        slug = path.stem
        feasibility = ideas_dir / "feasibility" / f"{slug}-feasibility.md"
        gate_frontmatter: dict[str, str] = {}
        if feasibility.exists():
            gate_frontmatter, _, _ = parse_frontmatter(read_text(feasibility))
        output.append(
            {
                "slug": slug,
                "status": frontmatter.get("status", "capture"),
                "priority": frontmatter.get("priority", "medium"),
                "paused": frontmatter.get("paused", "false").casefold() == "true",
                "portfolio_role": role,
                "idea_origin": frontmatter.get("idea_origin", "legacy_unclassified"),
                "project_slug": frontmatter.get("project_slug", ""),
                "feasibility_path": str(feasibility.resolve()) if feasibility.exists() else None,
                "feasibility_status": gate_frontmatter.get("gate_status"),
                "feasibility_decision": gate_frontmatter.get("human_decision"),
                "sprint_deadline": gate_frontmatter.get("sprint_deadline"),
            }
        )
    return output


def _project_rows(projects_vault: Path | None) -> list[dict[str, str]]:
    if projects_vault is None or not (projects_vault / "index.md").exists():
        return []
    rows: list[dict[str, str]] = []
    for line in read_text(projects_vault / "index.md").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] in {"slug", "---"} or set(cells[0]) == {"-"}:
            continue
        rows.append(
            {
                "slug": cells[0],
                "title": cells[1],
                "status": cells[3],
                "open_issues": cells[4],
                "last_sync": cells[5],
            }
        )
    return rows


def build_portfolio_snapshot(
    idea_vault: str | Path, *, projects_vault: str | Path | None = None
) -> dict[str, Any]:
    idea_root = Path(idea_vault)
    project_root = Path(projects_vault) if projects_vault else None
    ideas = _idea_records(idea_root)
    primaries = [idea for idea in ideas if idea["portfolio_role"] == "primary"]
    backups = [idea for idea in ideas if idea["portfolio_role"] == "backup"]
    projects = _project_rows(project_root)
    project_slugs = {project["slug"] for project in projects}
    violations: list[dict[str, str]] = []
    if len(primaries) != 1:
        violations.append(
            {
                "code": "portfolio.primary_count",
                "message": f"Exactly one primary idea is required; found {len(primaries)}",
            }
        )
    if len(backups) > 1:
        violations.append(
            {
                "code": "portfolio.backup_count",
                "message": f"At most one backup idea is allowed; found {len(backups)}",
            }
        )
    for idea in ideas:
        if idea["portfolio_role"] == "invalid":
            violations.append(
                {
                    "code": "portfolio.invalid_role",
                    "message": f"Idea {idea['slug']} has an unsupported portfolio role",
                }
            )
    for idea in [*primaries, *backups]:
        if not idea["feasibility_path"]:
            violations.append(
                {
                    "code": "portfolio.feasibility_missing",
                    "message": f"{idea['portfolio_role']} idea {idea['slug']} has no feasibility gate",
                }
            )
        if idea["paused"]:
            violations.append(
                {
                    "code": "portfolio.paused_active_role",
                    "message": f"Paused idea {idea['slug']} cannot occupy an active portfolio role",
                }
            )
        if idea["feasibility_decision"] != "continue":
            violations.append(
                {
                    "code": "portfolio.feasibility_not_continued",
                    "message": (
                        f"{idea['portfolio_role']} idea {idea['slug']} needs a human "
                        "continue decision from its feasibility gate"
                    ),
                }
            )
        if project_root is not None and (
            not idea["project_slug"] or idea["project_slug"] not in project_slugs
        ):
            violations.append(
                {
                    "code": "portfolio.project_missing",
                    "message": (
                        f"{idea['portfolio_role']} idea {idea['slug']} is not linked to "
                        "a tracked execution project"
                    ),
                }
            )
    snapshot = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "idea_vault": str(idea_root.resolve()),
        "ideas": ideas,
        "projects": projects,
        "summary": {
            "idea_count": len(ideas),
            "primary_count": len(primaries),
            "backup_count": len(backups),
            "parked_count": sum(
                1 for idea in ideas if idea["portfolio_role"] in {"parked", "none", ""}
            ),
        },
        "violations": violations,
    }
    snapshot["snapshot_hash"] = stable_hash(
        {key: value for key, value in snapshot.items() if key != "generated_at"}
    )
    return snapshot
