from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from journal_access import eligible_journals, probe_crossref, validate_registry  # noqa: E402


def registry(status: str = "verified_primary", enabled: bool = True) -> dict:
    return {
        "abstract_access_policy": {"freshness_days": 180},
        "journals": [{
            "journal_id": "jole",
            "name": "Journal of Labor Economics",
            "rank_weight": 0.86,
            "field_tags": ["labor"],
            "enabled_by_default": enabled,
            "abstract_access": {
                "status": status,
                "route": "crossref",
                "checked_at": "2026-07-20",
                "sample_title": "A paper",
            },
        }],
    }


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"message": {"items": [{
            "DOI": "10.1/test",
            "title": ["Test paper"],
            "abstract": "<jats:p>An identified result.</jats:p>",
        }]}}


class JournalAccessTests(unittest.TestCase):
    def test_enabled_journal_requires_fresh_verified_abstract_route(self) -> None:
        result = validate_registry(registry(), as_of=dt.date(2026, 7, 20))
        self.assertEqual(result["verified_count"], 1)
        with self.assertRaisesRegex(ValueError, "lack a fresh verified abstract route"):
            validate_registry(registry("metadata_only"), as_of=dt.date(2026, 7, 20))
        stale = registry()
        stale["journals"][0]["abstract_access"]["checked_at"] = "2025-01-01"
        with self.assertRaisesRegex(ValueError, "lack a fresh verified abstract route"):
            validate_registry(stale, as_of=dt.date(2026, 7, 20))

    def test_field_multiplier_changes_retrieval_priority_not_rank_weight(self) -> None:
        rows = eligible_journals(registry(), fields=["labor"], as_of=dt.date(2026, 7, 20))
        self.assertEqual(rows[0]["rank_weight"], 0.86)
        self.assertEqual(rows[0]["retrieval_priority_score"], 1.032)

    def test_crossref_probe_requires_an_actual_abstract(self) -> None:
        calls = []

        def fake_get(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeResponse()

        result = probe_crossref("0734-306X", from_date="2025-01-01", request_func=fake_get)
        self.assertTrue(result["abstract_found"])
        self.assertEqual(result["sample_doi"], "10.1/test")
        self.assertEqual(calls[0][1]["params"]["rows"], 20)


if __name__ == "__main__":
    unittest.main()
