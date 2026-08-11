from __future__ import annotations

import json
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]


class ReadingProtocolContractTests(unittest.TestCase):
    def test_canonical_protocol_has_strict_adaptive_order(self) -> None:
        system = (PACKAGE_ROOT / "tutor" / "system.md").read_text(encoding="utf-8")

        phase_zero = system.index("1. Phase 0: orient the learner")
        phase_one = system.index("2. Phase 1: run a math-necessity gate")
        phase_two = system.index("3. Phase 2: give one complete")
        self.assertLess(phase_zero, phase_one)
        self.assertLess(phase_one, phase_two)
        self.assertIn("math_gate: waived", system)
        self.assertIn("blocking + teaching-required", system)
        self.assertIn("500-900 Chinese characters", system)
        self.assertIn("repair the earliest missing learner-facing artifact", system)

    def test_bootloader_and_codex_skill_preserve_waivers_and_story_exception(self) -> None:
        claude = (PACKAGE_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        skill = (
            REPO_ROOT / "packages" / "codex" / "skills" / "paper-reading-tutor" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for document in (claude, skill):
            self.assertIn("math-necessity gate", document.lower())
            self.assertIn("known-waived", document)
            self.assertIn("complete story", document.lower())
        self.assertIn("exempt from these character caps", claude)
        self.assertIn("protected comprehension artifact", skill)

    def test_note_template_records_gate_and_story(self) -> None:
        template = (PACKAGE_ROOT / "tutor" / "paper_note_template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Phase 1 Math Necessity Gate", template)
        self.assertIn("known-waived / simple-waived", template)
        self.assertIn("## Phase 2 Complete Story Map", template)
        self.assertIn("### Mechanism Chain", template)

    def test_tutor_personas_do_not_reintroduce_mandatory_prerequisite_lectures(self) -> None:
        for name in ("trevor.md", "mira.md"):
            persona = (PACKAGE_ROOT / "tutor" / name).read_text(encoding="utf-8")
            self.assertIn("math-necessity gate", persona)
            self.assertIn("waive", persona.lower())
            self.assertNotIn("always does math prerequisites", persona)
            self.assertNotIn("always introduces math prerequisites", persona)

    def test_eval_cases_cover_known_hard_compact_and_batch_paths(self) -> None:
        eval_path = PACKAGE_ROOT / "evals" / "paper-reading-tutor" / "evals.json"
        payload = json.loads(eval_path.read_text(encoding="utf-8"))
        names = {case["name"] for case in payload["evals"]}
        self.assertEqual(
            names,
            {
                "known-did-is-waived",
                "unfamiliar-svd-blocks-story",
                "compact-mode-preserves-story",
                "weekly-queue-stays-batch-first",
            },
        )


if __name__ == "__main__":
    unittest.main()
