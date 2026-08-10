from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TUTOR_DIR = Path(__file__).resolve().parents[1] / "tutor"
sys.path.insert(0, str(TUTOR_DIR))

from taste_calibration import (  # noqa: E402
    append_calibration,
    evaluate_rankings,
    pairwise_agreement,
    precision_at_k,
)


class TasteCalibrationTests(unittest.TestCase):
    def test_precision_and_pairwise_agreement(self) -> None:
        predicted = ["a", "b", "c", "d"]
        human = ["b", "a", "d", "c"]
        self.assertEqual(precision_at_k(predicted, human, 2), 1.0)
        self.assertAlmostEqual(pairwise_agreement(predicted, human), 4 / 6)
        metrics = evaluate_rankings(predicted, human, k=3)
        self.assertEqual(metrics["shared_count"], 4)
        self.assertAlmostEqual(metrics["precision_at_k"], 2 / 3, places=6)

    def test_requires_two_shared_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least two shared"):
            evaluate_rankings(["a", "b"], ["a", "c"])

    def test_calibration_log_is_idempotent_and_conflict_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calibration.jsonl"
            event = {
                "calibration_id": "calibration:test",
                "recorded_at": "2026-08-10T12:00:00+00:00",
                "batch_id": "batch-one",
                "metrics": {"precision_at_k": 1.0},
            }
            rerun = {**event, "recorded_at": "2026-08-11T12:00:00+00:00"}
            conflict = {**rerun, "metrics": {"precision_at_k": 0.0}}

            self.assertTrue(append_calibration(log, event))
            self.assertFalse(append_calibration(log, rerun))
            with self.assertRaisesRegex(ValueError, "Conflicting calibration"):
                append_calibration(log, conflict)
            rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
