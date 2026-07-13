from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import unittest
from pathlib import Path


TUTOR_DIR = Path(__file__).resolve().parents[1] / "tutor"
sys.path.insert(0, str(TUTOR_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "research-core" / "src"))

from reading_feedback import (  # noqa: E402
    build_feedback,
    load_feedback,
    record_feedback,
)
try:
    from research_core.contracts import validate_contract  # noqa: E402
except ModuleNotFoundError:  # Standalone private AI Education does not vendor research-core.
    validate_contract = None


class ReadingFeedbackTests(unittest.TestCase):
    def test_full_feedback_round_trip_and_markdown_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "reading_feedback.jsonl"
            markdown = Path(tmp) / "paper_preferences.md"
            feedback = build_feedback(
                slug="example-paper",
                paper_id="doi:10.1234/example",
                read_depth="full",
                rating="high-value",
                usefulness="Credible counterevidence for a mechanism",
                surprise="The main effect was null",
                belief_changed="Narrowed the expected domain",
                idea_affected=["idea-one", "idea-one", "idea-two"],
                date="2026-07-13",
            )
            self.assertTrue(record_feedback(feedback, jsonl_path=jsonl, markdown_path=markdown))
            records = load_feedback(jsonl)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].idea_affected, ["idea-one", "idea-two"])
            self.assertEqual(records[0].paper_id, "doi:10.1234/example")
            self.assertTrue(records[0].feedback_id.startswith("feedback:"))
            rendered = markdown.read_text(encoding="utf-8")
            self.assertIn("belief_changed", rendered)
            self.assertIn("example-paper", rendered)

    @unittest.skipIf(validate_contract is None, "research-core is not installed")
    def test_real_feedback_writer_matches_research_core_contract(self) -> None:
        feedback = build_feedback(
            slug="contract-paper",
            paper_id="doi:10.1234/contract",
            read_depth="selective",
            rating="useful",
            usefulness="method",
            reason="read identification section",
            run_id="paper-done-contract",
            date="2026-07-13",
        )
        self.assertEqual(validate_contract("reading-feedback", dataclasses.asdict(feedback)), [])

    def test_identical_feedback_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "reading_feedback.jsonl"
            markdown = Path(tmp) / "paper_preferences.md"
            feedback = build_feedback(
                slug="rough-paper",
                paper_id="doi:10.1234/rough",
                read_depth="rough",
                rating="useful",
                usefulness="Citation map",
                date="2026-07-13",
            )
            self.assertTrue(record_feedback(feedback, jsonl_path=jsonl, markdown_path=markdown))
            self.assertFalse(record_feedback(feedback, jsonl_path=jsonl, markdown_path=markdown))
            self.assertEqual(len(jsonl.read_text(encoding="utf-8").splitlines()), 1)

    def test_same_run_cannot_append_conflicting_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "reading_feedback.jsonl"
            markdown = Path(tmp) / "paper_preferences.md"
            first = build_feedback(
                slug="paper",
                paper_id="doi:10.1234/same-run",
                read_depth="rough",
                rating="useful",
                usefulness="method",
                run_id="paper-done-same-run",
            )
            changed = build_feedback(
                slug="paper",
                paper_id="doi:10.1234/same-run",
                read_depth="full",
                rating="high-value",
                usefulness="evidence",
                run_id="paper-done-same-run",
            )
            self.assertEqual(first.feedback_id, changed.feedback_id)
            record_feedback(first, jsonl_path=jsonl, markdown_path=markdown)
            with self.assertRaisesRegex(ValueError, "Conflicting feedback"):
                record_feedback(changed, jsonl_path=jsonl, markdown_path=markdown)

    def test_skip_feedback_is_supported(self) -> None:
        feedback = build_feedback(
            slug="low-fit-paper",
            paper_id="doi:10.1234/low-fit",
            read_depth="skipped",
            rating="low-fit",
            usefulness="none",
            surprise="none",
            belief_changed="none",
            date="2026-07-13",
        )
        payload = json.loads(json.dumps(feedback.__dict__))
        self.assertEqual(payload["read_depth"], "skipped")
        self.assertEqual(payload["outcome"], "skipped")

    def test_legacy_feedback_is_upgraded_on_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "reading_feedback.jsonl"
            jsonl.write_text(
                json.dumps({
                    "event_id": "feedback:legacy",
                    "date": "2026-07-01",
                    "slug": "legacy-paper",
                    "read_depth": "rough",
                    "rating": "useful",
                    "usefulness": "method",
                    "surprise": "none",
                    "belief_changed": "none",
                    "idea_affected": [],
                    "source": "legacy",
                    "created_at": "2026-07-01T12:00:00+00:00",
                }) + "\n",
                encoding="utf-8",
            )
            record = load_feedback(jsonl)[0]
            self.assertEqual(record.feedback_id, "feedback:legacy")
            self.assertEqual(record.paper_id, "slug:legacy-paper")
            self.assertEqual(record.provenance["source"], "legacy")

    def test_usefulness_is_required(self) -> None:
        with self.assertRaises(ValueError):
            build_feedback(
                slug="bad",
                paper_id="doi:10.1234/bad",
                read_depth="full",
                rating="useful",
                usefulness="",
            )

    def test_markdown_view_puts_recent_feedback_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "reading_feedback.jsonl"
            markdown = Path(tmp) / "paper_preferences.md"
            for slug, date in (("older-paper", "2026-07-01"), ("newer-paper", "2026-07-13")):
                record_feedback(
                    build_feedback(
                        slug=slug,
                        paper_id=f"doi:10.1234/{slug}",
                        read_depth="rough",
                        rating="useful",
                        usefulness="method clue",
                        date=date,
                    ),
                    jsonl_path=jsonl,
                    markdown_path=markdown,
                )
            rendered = markdown.read_text(encoding="utf-8")
            self.assertLess(rendered.index("newer-paper"), rendered.index("older-paper"))


if __name__ == "__main__":
    unittest.main()
