from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR / "papers"))

from queue_sync import merge_queue, render_markdown, write_state  # noqa: E402


QUEUE_HEADER = """# Reading Queue

| candidate-slug | title | tier | authors | venue | url | added |
|----------------|-------|------|---------|-------|-----|-------|
"""


class QueueSyncTests(unittest.TestCase):
    def test_completion_updates_canonical_state_and_removes_view_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "queue_state.jsonl"
            remote = root / "remote.md"
            local = root / "local.md"
            completed = root / "completed.md"
            feedback = root / "feedback.jsonl"
            output = root / "next.jsonl"
            remote.write_text(
                QUEUE_HEADER
                + "| paper-one | Paper One | 1 | A | Journal | https://doi.org/10.1234/one | 2026-07-01 |\n",
                encoding="utf-8",
            )
            local.write_text(remote.read_text(encoding="utf-8"), encoding="utf-8")
            completed.write_text("| # | slug | title | completed |\n|---|---|---|---|\n", encoding="utf-8")
            feedback.write_text(
                json.dumps({"slug": "paper-one", "read_depth": "full"}) + "\n",
                encoding="utf-8",
            )

            records, summary = merge_queue(
                state_path=state,
                remote_markdown_path=remote,
                local_markdown_path=local,
                completed_path=completed,
                feedback_path=feedback,
            )
            write_state(output, records)

            payload = json.loads(output.read_text(encoding="utf-8").strip())
            self.assertEqual(summary["migrated"], 1)
            self.assertEqual(summary["terminal_updates"], 1)
            self.assertEqual(payload["status"], "completed")
            self.assertNotIn("paper-one", render_markdown(records))

    def test_local_manual_entry_is_preserved_without_overwriting_remote_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "queue_state.jsonl"
            remote = root / "remote.md"
            local = root / "local.md"
            completed = root / "completed.md"
            canonical = {
                "paper_id": "doi:10.1234/remote",
                "candidate_slug": "remote-paper",
                "title": "Remote Paper",
                "tier": 1,
                "lane": "contradiction",
                "matched_signal": "active:123",
                "authors": "Remote Author",
                "venue": "Remote Journal",
                "url": "https://doi.org/10.1234/remote",
                "published": "2026-07-10",
                "added": "2026-07-11",
                "last_seen": "2026-07-11",
                "status": "queued",
                "score": 99,
                "source": "openalex",
                "identifiers": {"doi": "10.1234/remote"},
            }
            state.write_text(json.dumps(canonical) + "\n", encoding="utf-8")
            remote.write_text(QUEUE_HEADER, encoding="utf-8")
            local.write_text(
                QUEUE_HEADER
                + "| remote-paper | Remote Paper | 2 | | | https://doi.org/10.1234/remote | 2026-07-12 |\n"
                + "| manual-paper | Manual Paper | 2 | Me | | https://example.org/manual | 2026-07-13 |\n",
                encoding="utf-8",
            )
            completed.write_text("", encoding="utf-8")

            records, summary = merge_queue(
                state_path=state,
                remote_markdown_path=remote,
                local_markdown_path=local,
                completed_path=completed,
            )

            self.assertEqual(summary["local_added"], 1)
            self.assertEqual(len(records), 2)
            remote_record = next(record for record in records if record.candidate_slug == "remote-paper")
            self.assertEqual(remote_record.lane, "contradiction")
            self.assertEqual(remote_record.tier, 1)

    def test_skipped_feedback_sets_skipped_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "missing.jsonl"
            remote = root / "remote.md"
            local = root / "local.md"
            completed = root / "completed.md"
            feedback = root / "feedback.jsonl"
            row = "| skip-me | Skip Me | 2 | | | https://example.org/skip | 2026-07-13 |\n"
            remote.write_text(QUEUE_HEADER + row, encoding="utf-8")
            local.write_text(QUEUE_HEADER + row, encoding="utf-8")
            completed.write_text("", encoding="utf-8")
            feedback.write_text(json.dumps({"slug": "skip-me", "read_depth": "skipped"}) + "\n", encoding="utf-8")

            records, _ = merge_queue(
                state_path=state,
                remote_markdown_path=remote,
                local_markdown_path=local,
                completed_path=completed,
                feedback_path=feedback,
            )
            self.assertEqual(records[0].status, "skipped")

    def test_feedback_matches_canonical_paper_id_before_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "queue_state.jsonl"
            first = {
                    "paper_id": "doi:10.1234/stable",
                    "candidate_slug": "new-slug",
                    "title": "Stable paper",
                    "tier": 1,
                    "lane": "portfolio_fit",
                    "matched_signal": "test",
                    "authors": "A",
                    "venue": "J",
                    "url": "https://doi.org/10.1234/stable",
                    "published": "2026-07-01",
                    "added": "2026-07-13",
                    "last_seen": "2026-07-13",
                    "status": "queued",
                    "score": 1,
                    "source": "test",
                    "identifiers": {"doi": "10.1234/stable"},
                }
            second = {
                **first,
                "paper_id": "doi:10.1234/other",
                "candidate_slug": "old-slug",
                "title": "Other paper",
                "url": "https://doi.org/10.1234/other",
                "identifiers": {"doi": "10.1234/other"},
            }
            state.write_text(
                json.dumps(first) + "\n" + json.dumps(second) + "\n",
                encoding="utf-8",
            )
            feedback = root / "feedback.jsonl"
            feedback.write_text(
                json.dumps({
                    "paper_id": "doi:10.1234/stable",
                    "slug": "old-slug",
                    "read_depth": "full",
                }) + "\n",
                encoding="utf-8",
            )
            empty = root / "empty.md"
            empty.write_text("", encoding="utf-8")
            records, _ = merge_queue(
                state_path=state,
                remote_markdown_path=empty,
                local_markdown_path=empty,
                completed_path=empty,
                feedback_path=feedback,
            )
            status_by_id = {record.paper_id: record.status for record in records}
            self.assertEqual(status_by_id["doi:10.1234/stable"], "completed")
            self.assertEqual(status_by_id["doi:10.1234/other"], "queued")


if __name__ == "__main__":
    unittest.main()
