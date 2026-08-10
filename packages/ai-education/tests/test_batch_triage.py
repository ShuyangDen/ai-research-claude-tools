from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PAPERS_DIR = Path(__file__).resolve().parents[1] / "papers"
sys.path.insert(0, str(PAPERS_DIR))

from batch_triage import (  # noqa: E402
    append_idempotent,
    apply_queue_decisions,
    build_comparison,
    build_decision,
    main,
    prepare_batch,
)


class BatchTriageTests(unittest.TestCase):
    @staticmethod
    def queue_record(index: int, *, status: str = "queued", tier: int = 1) -> dict[str, object]:
        return {
            "paper_id": f"doi:10.1234/{index}",
            "candidate_slug": f"paper-{index}",
            "title": f"Paper {index}",
            "tier": tier,
            "lane": "exploit",
            "score": 100 - index,
            "priority_rank": index,
            "status": status,
        }

    def test_prepare_is_bounded_and_does_not_claim_reading(self) -> None:
        queue = [self.queue_record(index) for index in range(1, 13)]
        queue.append(self.queue_record(20, status="backlog"))

        batch = prepare_batch(
            queue,
            batch_id="triage-test",
            max_papers=10,
            created_at="2026-08-10T12:00:00+00:00",
        )

        self.assertEqual(batch["candidate_count"], 10)
        self.assertEqual(batch["status"], "awaiting_human_decisions")
        self.assertNotIn("doi:10.1234/20", {item["paper_id"] for item in batch["candidates"]})

    def test_decisions_validate_action_specific_fields_and_update_queue(self) -> None:
        deep = build_decision(
            {
                "paper_id": "doi:10.1234/1",
                "action": "deep",
                "reason_codes": ["importance"],
                "would_build_on": True,
                "predicted_value": 5,
            },
            batch_id="batch-one",
            recorded_at="2026-08-10T12:00:00+00:00",
        )
        cluster = build_decision(
            {
                "paper_id": "doi:10.1234/2",
                "action": "cluster-only",
                "reason_codes": ["duplicate"],
                "cluster_id": "mechanism-one",
            },
            batch_id="batch-one",
            recorded_at="2026-08-10T12:00:00+00:00",
        )
        queue = apply_queue_decisions(
            [self.queue_record(1), self.queue_record(2)], [deep, cluster]
        )

        self.assertEqual(queue[0]["status"], "in_progress")
        self.assertTrue(queue[0]["pinned"])
        self.assertEqual(queue[1]["status"], "clustered")
        self.assertEqual(deep.actor, "human")
        with self.assertRaisesRegex(ValueError, "selected_sections"):
            build_decision(
                {
                    "paper_id": "doi:10.1234/3",
                    "action": "targeted",
                    "reason_codes": ["identification"],
                },
                batch_id="batch-one",
            )

    def test_append_is_idempotent_but_rejects_changed_human_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "triage.jsonl"
            base = {
                "paper_id": "doi:10.1234/1",
                "action": "skip",
                "reason_codes": ["low-fit"],
                "rationale": "Not connected to the current question",
            }
            first = build_decision(
                base,
                batch_id="batch-one",
                recorded_at="2026-08-10T12:00:00+00:00",
            )
            rerun = build_decision(
                base,
                batch_id="batch-one",
                recorded_at="2026-08-11T12:00:00+00:00",
            )
            changed = build_decision(
                {**base, "action": "deep"},
                batch_id="batch-one",
                recorded_at="2026-08-11T12:00:00+00:00",
            )

            self.assertEqual(append_idempotent(log, [first], id_field="decision_id"), 1)
            self.assertEqual(append_idempotent(log, [rerun], id_field="decision_id"), 0)
            with self.assertRaisesRegex(ValueError, "Conflicting event"):
                append_idempotent(log, [changed], id_field="decision_id")
            self.assertEqual(len(log.read_text(encoding="utf-8").splitlines()), 1)

    def test_pairwise_comparison_uses_human_provenance(self) -> None:
        comparison = build_comparison(
            {
                "winner_paper_id": "doi:10.1234/1",
                "loser_paper_id": "doi:10.1234/2",
                "reason_codes": ["feasibility"],
                "rationale": "The data path is executable",
            },
            batch_id="batch-one",
            recorded_at="2026-08-10T12:00:00+00:00",
        )
        self.assertEqual(comparison.actor, "human")
        self.assertTrue(comparison.comparison_id.startswith("comparison:"))

    def test_apply_validates_queue_before_writing_event_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "queue.jsonl"
            batch = root / "batch.json"
            decisions = root / "decisions.json"
            triage_log = root / "triage.jsonl"
            comparison_log = root / "comparisons.jsonl"
            queue.write_text(json.dumps(self.queue_record(1)) + "\n", encoding="utf-8")
            batch.write_text(
                json.dumps(
                    {
                        "batch_id": "batch-one",
                        "candidates": [
                            {"paper_id": "doi:10.1234/1"},
                            {"paper_id": "doi:10.1234/2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            decisions.write_text(
                json.dumps(
                    {
                        "decisions": [
                            {
                                "paper_id": f"doi:10.1234/{index}",
                                "action": "skip",
                                "reason_codes": ["low-fit"],
                            }
                            for index in (1, 2)
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "absent from queue"):
                main(
                    [
                        "apply",
                        "--batch",
                        str(batch),
                        "--decisions",
                        str(decisions),
                        "--queue-state",
                        str(queue),
                        "--triage-log",
                        str(triage_log),
                        "--comparison-log",
                        str(comparison_log),
                    ]
                )
            self.assertFalse(triage_log.exists())
            self.assertFalse(comparison_log.exists())


if __name__ == "__main__":
    unittest.main()
