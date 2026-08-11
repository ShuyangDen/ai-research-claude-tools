from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from research_core.feasibility import apply_ready, check_feasibility  # noqa: E402
from research_core.portfolio import build_portfolio_snapshot  # noqa: E402
from research_core.s2check import parse_frontmatter  # noqa: E402


SECTION_TEXT = (
    "This section names concrete empirical evidence, the executable test, "
    "and the main condition that would falsify the proposed mechanism."
)


def write_feasibility(path: Path, *, access_status: str = "tested") -> None:
    artifact = path.parent / "minimum-result.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("verified artifact", encoding="utf-8")
    path.write_text(
        f"""---
gate_schema_version: 2
idea_slug: test-idea
gate_status: draft
ai_readiness: NOT_READY
sprint_started: 2099-01-01
sprint_deadline: 2099-01-15
data_access_status: {access_status}
minimum_artifact_path: minimum-result.txt
estimated_upfront_hours: 20
time_to_first_signal_days: 7
high_cost_collection_required: no
salvage_artifact_path: minimum-result.txt
null_result_value: informative
human_decision: pending
human_decision_by: ""
human_decision_date: ""
---

# Feasibility

## Estimand

{SECTION_TEXT}

## Identification

{SECTION_TEXT}

## Data Access

{SECTION_TEXT}

## Minimum Viable Artifact

{SECTION_TEXT}

## Early Signal and Stopping Rule

{SECTION_TEXT}

## Salvage Value and Null Interpretation

{SECTION_TEXT}

## Nearest-Paper Threat

{SECTION_TEXT}

## Two-Week Sprint Plan

{SECTION_TEXT}

## Human Decision

Outcome: pending
""",
        encoding="utf-8",
    )


class FeasibilityTests(unittest.TestCase):
    def test_ready_gate_can_update_only_generated_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate = Path(tmp) / "test-feasibility.md"
            write_feasibility(gate)

            report = check_feasibility(gate)
            self.assertTrue(report["ready"])
            updated = apply_ready(gate, report)
            frontmatter, _, _ = parse_frontmatter(gate.read_text(encoding="utf-8"))

            self.assertTrue(updated["ready"])
            self.assertEqual(frontmatter["gate_status"], "ready_for_human_decision")
            self.assertEqual(frontmatter["human_decision"], "pending")
            self.assertEqual(frontmatter["human_decision_by"], "")

    def test_available_but_unacquired_data_blocks_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate = Path(tmp) / "test-feasibility.md"
            write_feasibility(gate, access_status="available")

            report = check_feasibility(gate)

            self.assertFalse(report["ready"])
            self.assertIn("data.not_acquired", {item["code"] for item in report["blockers"]})

    def test_late_first_signal_and_missing_salvage_block_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate = Path(tmp) / "test-feasibility.md"
            write_feasibility(gate)
            text = gate.read_text(encoding="utf-8")
            text = text.replace("time_to_first_signal_days: 7", "time_to_first_signal_days: 30")
            text = text.replace("salvage_artifact_path: minimum-result.txt", "salvage_artifact_path: missing.txt")
            gate.write_text(text, encoding="utf-8")

            report = check_feasibility(gate)
            blockers = {item["code"] for item in report["blockers"]}

            self.assertIn("investment.signal_too_late", blockers)
            self.assertIn("investment.salvage_not_found", blockers)


class PortfolioTests(unittest.TestCase):
    @staticmethod
    def write_idea(vault: Path, slug: str, *, role: str, project_slug: str = "") -> None:
        ideas = vault / "ideas"
        ideas.mkdir(parents=True, exist_ok=True)
        (ideas / f"{slug}.md").write_text(
            f"""---
status: s2
priority: high
paused: false
portfolio_role: {role}
project_slug: {project_slug}
idea_origin: human
---

# {slug}
""",
            encoding="utf-8",
        )

    @staticmethod
    def write_gate(vault: Path, slug: str, *, decision: str = "continue") -> None:
        directory = vault / "ideas" / "feasibility"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{slug}-feasibility.md").write_text(
            f"""---
gate_status: ready_for_human_decision
human_decision: {decision}
sprint_deadline: 2099-01-15
---
""",
            encoding="utf-8",
        )

    def test_snapshot_enforces_primary_backup_and_project_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "ideas-vault"
            projects = root / "projects"
            self.write_idea(vault, "primary-idea", role="primary", project_slug="jmp-project")
            self.write_idea(vault, "backup-idea", role="backup")
            self.write_gate(vault, "primary-idea")
            self.write_gate(vault, "backup-idea", decision="pending")
            projects.mkdir(parents=True)
            (projects / "index.md").write_text(
                "| slug | title | path | status | open issues | last sync |\n"
                "|------|-------|------|--------|-------------|-----------|\n"
                "| jmp-project | JMP | projects/jmp | active | none | 2099-01-01 |\n",
                encoding="utf-8",
            )

            snapshot = build_portfolio_snapshot(vault, projects_vault=projects)
            violations = {item["code"] for item in snapshot["violations"]}

            self.assertEqual(snapshot["summary"]["primary_count"], 1)
            self.assertEqual(snapshot["summary"]["backup_count"], 1)
            self.assertNotIn("portfolio.primary_count", violations)
            self.assertIn("portfolio.feasibility_not_continued", violations)
            self.assertIn("portfolio.project_missing", violations)
            self.assertTrue(snapshot["snapshot_hash"])

    def test_invalid_role_and_missing_primary_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "ideas-vault"
            self.write_idea(vault, "bad-role", role="favorite")

            snapshot = build_portfolio_snapshot(vault)
            violations = {item["code"] for item in snapshot["violations"]}

            self.assertIn("portfolio.invalid_role", violations)
            self.assertIn("portfolio.primary_count", violations)


if __name__ == "__main__":
    unittest.main()
