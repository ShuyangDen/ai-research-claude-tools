#!/usr/bin/env python3
"""Regression tests for the Codex workflow adapter release layer."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPO_ROOT / "scripts" / "generate_codex_workflow_adapters.py"
SPEC = importlib.util.spec_from_file_location("workflow_adapter_generator", GENERATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {GENERATOR_PATH}")
generator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generator
SPEC.loader.exec_module(generator)


class WorkflowAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest_path = REPO_ROOT / generator.DEFAULT_MANIFEST
        cls.manifest, _ = generator.load_manifest(REPO_ROOT, cls.manifest_path)
        cls.plan = generator.build_plan(REPO_ROOT, cls.manifest_path)

    def test_manifest_covers_every_package_skill(self) -> None:
        declared = {
            adapter["name"]
            for adapter in self.manifest["adapters"]
            if adapter["mode"] != "planned"
        }
        actual = {
            path.parent.name
            for path in (REPO_ROOT / "packages" / "codex" / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(actual, declared)

    def test_idea_chat_is_generated_from_the_canonical_command(self) -> None:
        adapter = next(
            item for item in self.manifest["adapters"] if item["name"] == "idea-chat"
        )
        self.assertEqual(adapter["mode"], "generated")
        self.assertTrue((REPO_ROOT / adapter["canonical_source_path"]).exists())
        self.assertIn("idea-chat", self.plan.active_names)

    def test_generated_outputs_are_utf8_no_bom_lf(self) -> None:
        for path, data in self.plan.expected_files.items():
            with self.subTest(path=path):
                self.assertFalse(data.startswith(generator.UTF8_BOM))
                self.assertNotIn(b"\r", data)
                data.decode("utf-8")

    def test_generated_skills_embed_source_metadata(self) -> None:
        pattern = re.compile(r"<!-- workflow-adapter: (\{.*\}) -->")
        for adapter in self.manifest["adapters"]:
            if adapter["mode"] != "generated":
                continue
            package_path = REPO_ROOT / adapter["package_path"]
            text = self.plan.expected_files[package_path].decode("utf-8")
            match = pattern.search(text)
            self.assertIsNotNone(match, adapter["name"])
            metadata = json.loads(match.group(1))
            source_path = REPO_ROOT / adapter["canonical_source_path"]
            self.assertEqual(metadata["schema"], generator.SKILL_SCHEMA)
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(metadata["source_path"], adapter["canonical_source_path"])
            self.assertEqual(
                metadata["source_sha256"],
                generator.sha256_bytes(source_path.read_bytes()),
            )
            self.assertEqual(
                metadata["workflow_version"],
                (REPO_ROOT / self.manifest["release_version_file"]).read_text(
                    encoding="utf-8-sig"
                ).strip(),
            )

    def test_no_forbidden_markers_in_active_skills(self) -> None:
        active = {
            adapter["name"]: adapter
            for adapter in self.manifest["adapters"]
            if adapter["mode"] != "planned"
        }
        for name, adapter in active.items():
            package_path = REPO_ROOT / adapter["package_path"]
            if package_path in self.plan.expected_files:
                package_data = self.plan.expected_files[package_path]
            else:
                package_data = package_path.read_bytes()
            plugin_path = (
                REPO_ROOT
                / self.manifest["plugin_root"]
                / "skills"
                / name
                / "SKILL.md"
            )
            plugin_data = self.plan.expected_files[plugin_path]
            for label, data in (("package", package_data), ("plugin", plugin_data)):
                text = generator.decode_utf8(data, package_path)
                with self.subTest(name=name, location=label):
                    for marker in generator.FORBIDDEN_TEXT:
                        self.assertNotIn(marker, text)

    def test_generated_skills_have_no_unexpanded_home_placeholder(self) -> None:
        for path, data in self.plan.expected_files.items():
            if path.name != "SKILL.md":
                continue
            with self.subTest(path=path):
                text = data.decode("utf-8")
                self.assertNotIn("{{HOME}}", text)
                self.assertNotRegex(text, r"\{\{[A-Z][A-Z0-9_]+\}\}")
                self.assertIn("~/.claude/machine_paths.md", text)

    def test_runtime_workflows_reject_setup_placeholders(self) -> None:
        with self.assertRaisesRegex(generator.AdapterError, "unresolved setup placeholder"):
            generator.assert_clean_text("email=<YOUR_EMAIL>", Path("runtime.md"))

    def test_passthrough_package_files_are_not_rewritten(self) -> None:
        for adapter in self.manifest["adapters"]:
            if adapter["mode"] != "passthrough":
                continue
            package_path = REPO_ROOT / adapter["package_path"]
            self.assertNotIn(package_path, self.plan.generated_package_paths)
            self.assertNotIn(package_path, self.plan.expected_files)

    def test_install_manifest_hashes_match_planned_artifacts(self) -> None:
        install_path = REPO_ROOT / self.manifest["package_install_manifest"]
        install = json.loads(self.plan.expected_files[install_path].decode("utf-8"))
        self.assertEqual(install["schema"], generator.INSTALL_SCHEMA)
        for artifact in install["artifacts"]:
            path = REPO_ROOT / artifact["path"]
            expected = (
                self.plan.expected_files[path]
                if path in self.plan.expected_files
                else path.read_bytes()
            )
            self.assertEqual(artifact["sha256"], generator.sha256_bytes(expected))

    def test_claude_plugin_commands_are_exact_canonical_mirrors(self) -> None:
        plugin_root = REPO_ROOT / self.manifest["plugin_root"]
        for adapter in self.manifest["adapters"]:
            if adapter["mode"] != "generated":
                continue
            source = REPO_ROOT / adapter["canonical_source_path"]
            command = plugin_root / "commands" / f"{adapter['name']}.md"
            expected = generator.normalized_utf8(source.read_bytes(), source)
            self.assertEqual(self.plan.expected_files[command], expected)
            self.assertIn(command, self.plan.active_plugin_command_paths)

    def test_both_plugin_manifests_match_root_release_version(self) -> None:
        root_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
        plugin_root = REPO_ROOT / self.manifest["plugin_root"]
        for surface in (".codex-plugin", ".claude-plugin"):
            path = plugin_root / surface / "plugin.json"
            manifest = json.loads(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(manifest["name"], "ai-research-tools")
            self.assertEqual(manifest["version"], root_version)

    def test_atomic_write_replaces_without_bom_or_temp_leak(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact.json"
            target.write_bytes(b"old")
            generator.atomic_write(target, b'{"ok":true}\n')
            self.assertEqual(target.read_bytes(), b'{"ok":true}\n')
            self.assertEqual(list(target.parent.glob(f".{target.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
