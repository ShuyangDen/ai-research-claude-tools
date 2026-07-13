#!/usr/bin/env python3
"""Safety tests for the local system-file installer."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("sync_local_install.py")
REPO_ROOT = SCRIPT_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("sync_local_install", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {SCRIPT_PATH}")
installer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = installer
SPEC.loader.exec_module(installer)


class LocalInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.repo.mkdir()
        self.home.mkdir()
        (self.repo / "VERSION").write_text("3.0.0\n", encoding="utf-8")

        self.idea = self.root / "vaults" / "JMP Idea"
        self.wiki = self.root / "vaults" / "personal knowledge skill"
        self.ai = self.root / "AI_education"
        self.tracker = self.root / "paper-tracker"
        self.machine_paths = self.home / ".claude" / "machine_paths.md"
        self.machine_paths.parent.mkdir(parents=True)
        self.machine_paths.write_text(
            "\n".join(
                (
                    "# Machine Paths",
                    "## Personal Knowledge Wiki",
                    f"- **Vault**: `{self.wiki}`",
                    "## Research Idea Pipeline",
                    f"- **Vault**: `{self.idea}`",
                    "## AI Education Project",
                    f"- **Project root**: `{self.ai}`",
                    "## Paper Tracker",
                    f"- **Project root**: `{self.tracker}`",
                    "",
                )
            ),
            encoding="utf-8",
        )
        self.variables = installer.resolve_variables(
            self.machine_paths, self.repo, self.home
        )

    def make_source(self, relative: str, data: bytes = b"system\n") -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def make_mapping(self, files: list[dict], trees: list[dict] | None = None) -> tuple[dict, Path]:
        mapping = {
            "schema": installer.MAPPING_SCHEMA,
            "schema_version": 1,
            "installer_version": "1.0.0",
            "release_version_file": "VERSION",
            "default_state_manifest": "{HOME}/.codex/ai-research-tools/install-manifest.json",
            "default_backup_root": "{HOME}/.codex/ai-research-tools/backups",
            "trees": trees or [],
            "files": files,
            "protected_data": [],
        }
        path = self.repo / "mapping.json"
        path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
        return installer.load_mapping(self.repo, path), path

    def test_machine_paths_parser_resolves_current_format(self) -> None:
        self.assertEqual(self.variables["IDEA_VAULT"], self.idea.resolve())
        self.assertEqual(self.variables["WIKI_VAULT"], self.wiki.resolve())
        self.assertEqual(self.variables["OBSIDIAN_ROOT"], self.idea.parent.resolve())
        self.assertEqual(self.variables["AI_EDUCATION_PATH"], self.ai.resolve())
        self.assertEqual(self.variables["PAPER_TRACKER_PATH"], self.tracker.resolve())

    def test_release_marker_template_matches_root_version(self) -> None:
        real_root = SCRIPT_PATH.parent.parent
        marker = json.loads(
            (real_root / "packages" / "codex" / "ai-tools-version.template.json").read_text(
                encoding="utf-8"
            )
        )
        version = (real_root / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(marker["version"], version)
        self.assertIn("research-core", marker["packages"])

    def test_personal_idea_content_is_rejected_even_if_manifest_lists_it(self) -> None:
        self.make_source("system/private.md")
        mapping, _ = self.make_mapping(
            [
                {
                    "scope": "idea-vault",
                    "source": "system/private.md",
                    "destination": "{IDEA_VAULT}/ideas/my-real-idea.md",
                }
            ]
        )
        with self.assertRaisesRegex(installer.InstallError, "protected destination"):
            installer.build_plan(self.repo, mapping, self.variables, {"idea-vault"})

    def test_feedback_and_profile_are_rejected_even_if_manifest_lists_them(self) -> None:
        self.make_source("system/private.jsonl")
        for scope, destination in (
            ("ai-education", "{AI_EDUCATION_PATH}/tutor/reading_feedback.jsonl"),
            ("idea-vault", "{IDEA_VAULT}/recommendation_profile.json"),
        ):
            with self.subTest(destination=destination):
                mapping, _ = self.make_mapping([
                    {
                        "scope": scope,
                        "source": "system/private.jsonl",
                        "destination": destination,
                    }
                ])
                with self.assertRaisesRegex(installer.InstallError, "protected destination"):
                    installer.build_plan(self.repo, mapping, self.variables, {scope})

    def test_all_named_personal_areas_are_protected(self) -> None:
        destinations = (
            self.wiki / "wiki" / "concept.md",
            self.wiki / "sources" / "paper.md",
            self.ai / "papers" / "notes" / "paper.md",
            self.ai / "tutor" / "learner_profile.md",
            self.ai / "tutor" / "paper_preferences.md",
            self.ai / "tutor" / "reading_feedback.jsonl",
            self.ai / "tutor" / "reading_feedback.backup.jsonl",
            self.idea / "recommendation_profile.json",
            self.tracker / "researcher_profile.md",
            self.tracker / "reading_queue.json",
            self.tracker / "feedback.md",
        )
        for destination in destinations:
            with self.subTest(destination=destination):
                self.assertIsNotNone(
                    installer.protected_reason(destination, self.variables)
                )

    def test_templates_are_allowed(self) -> None:
        for destination in (
            self.idea / "ideas" / "_template.md",
            self.idea / "ideas" / "_s2_gate_template.md",
            self.wiki / "sources" / "_template.md",
            self.ai / "papers" / "queue_sync.py",
            self.ai / "tutor" / "reading_feedback.py",
            self.tracker / "recommendation_profile.example.json",
        ):
            with self.subTest(destination=destination):
                self.assertIsNone(installer.protected_reason(destination, self.variables))

    def test_build_and_report_are_read_only(self) -> None:
        self.make_source("system/CLAUDE.md", b"hello {{HOME}}\n")
        mapping, _ = self.make_mapping(
            [
                {
                    "scope": "ai-education",
                    "source": "system/CLAUDE.md",
                    "destination": "{AI_EDUCATION_PATH}/CLAUDE.md",
                }
            ]
        )
        plan = installer.build_plan(
            self.repo, mapping, self.variables, {"ai-education"}
        )
        installer.report_plan(plan)
        self.assertFalse((self.ai / "CLAUDE.md").exists())

    def test_apply_normalizes_utf8_backs_up_and_records_hashes(self) -> None:
        source = self.make_source(
            "system/CLAUDE.md", installer.UTF8_BOM + b"new {{HOME}}\r\n"
        )
        destination = self.ai / "CLAUDE.md"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(installer.UTF8_BOM + b"old\r\n")
        mapping, mapping_path = self.make_mapping(
            [
                {
                    "scope": "ai-education",
                    "source": "system/CLAUDE.md",
                    "destination": "{AI_EDUCATION_PATH}/CLAUDE.md",
                }
            ]
        )
        selected = {"ai-education"}
        plan = installer.build_plan(self.repo, mapping, self.variables, selected)
        state = self.home / "state.json"
        backups = self.home / "backups"
        result = installer.apply_plan(
            self.repo,
            mapping_path,
            mapping,
            self.machine_paths,
            self.variables,
            selected,
            plan,
            state,
            backups,
        )
        self.assertEqual(result, 0)
        installed = destination.read_bytes()
        self.assertFalse(installed.startswith(installer.UTF8_BOM))
        self.assertNotIn(b"\r", installed)
        self.assertIn(str(self.home).encode("utf-8"), installed)
        state_data = json.loads(state.read_text(encoding="utf-8"))
        record = state_data["artifacts"][0]
        self.assertEqual(record["source_sha256"], installer.sha256_bytes(source.read_bytes()))
        self.assertEqual(record["installed_sha256"], installer.sha256_bytes(installed))
        self.assertEqual(record["workflow_version"], "3.0.0")
        backup = Path(record["backup"])
        self.assertTrue(backup.exists())
        self.assertEqual(backup.read_bytes(), installer.UTF8_BOM + b"old\r\n")

    def test_scope_filter_does_not_plan_another_scope(self) -> None:
        self.make_source("system/a.md")
        self.make_source("system/b.md")
        mapping, _ = self.make_mapping(
            [
                {
                    "scope": "ai-education",
                    "source": "system/a.md",
                    "destination": "{AI_EDUCATION_PATH}/a.md",
                },
                {
                    "scope": "paper-tracker",
                    "source": "system/b.md",
                    "destination": "{PAPER_TRACKER_PATH}/b.md",
                },
            ]
        )
        plan = installer.build_plan(
            self.repo, mapping, self.variables, {"paper-tracker"}
        )
        self.assertEqual([item.scope for item in plan], ["paper-tracker"])

    def test_empty_source_is_rejected(self) -> None:
        self.make_source("system/empty.md", b" \r\n")
        mapping, _ = self.make_mapping(
            [
                {
                    "scope": "ai-education",
                    "source": "system/empty.md",
                    "destination": "{AI_EDUCATION_PATH}/empty.md",
                }
            ]
        )
        with self.assertRaisesRegex(installer.InstallError, "empty source"):
            installer.build_plan(self.repo, mapping, self.variables, {"ai-education"})

    def test_real_mapping_installs_the_tracker_ci_test_suite(self) -> None:
        mapping = json.loads(
            (REPO_ROOT / "packages" / "codex" / "local-install-files.json").read_text(
                encoding="utf-8"
            )
        )
        tracker_files = {
            (entry.get("source"), entry.get("destination"))
            for entry in mapping["files"]
            if entry.get("scope") == "paper-tracker"
        }
        self.assertIn(
            (
                "packages/paper-tracker/tests/test_tracker_core.py",
                "{PAPER_TRACKER_PATH}/tests/test_tracker_core.py",
            ),
            tracker_files,
        )
        workflow = (
            REPO_ROOT
            / "packages"
            / "paper-tracker"
            / ".github"
            / "workflows"
            / "weekly_paper_digest.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v", workflow)


if __name__ == "__main__":
    unittest.main()
