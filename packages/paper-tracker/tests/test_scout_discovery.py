from __future__ import annotations

import sys
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from scout_discovery import discover_openalex  # noqa: E402


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "results": [{
                "id": "https://openalex.org/W123",
                "ids": {
                    "openalex": "https://openalex.org/W123",
                    "doi": "https://doi.org/10.1234/example",
                },
                "title": "Managers and worker learning in organizations",
                "publication_date": "2026-01-01",
                "primary_location": {"source": {"display_name": "American Economic Review"}},
                "authorships": [{"author": {"display_name": "A. Author"}}],
                "abstract_inverted_index": {"Managers": [0], "improve": [1], "learning": [2]},
            }]
        }


class ScoutDiscoveryTests(unittest.TestCase):
    def test_discovery_accepts_only_public_scope_enums(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported public scout scope"):
            discover_openalex(["my private profile"], request_func=lambda *args, **kwargs: FakeResponse())

    def test_discovery_queries_are_public_and_missing_abstract_is_not_filled_by_title(self) -> None:
        calls = []

        def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

        result = discover_openalex(
            ["labor"],
            as_of="2026-07-16",
            per_query=1,
            request_func=fake_get,
            api_key="test-key",
        )
        self.assertTrue(calls)
        self.assertTrue(all("researcher_profile" not in query for query in result["queries"]))
        self.assertTrue(all(call[1]["params"]["api_key"] == "test-key" for call in calls))
        self.assertNotIn("test-key", str(result))
        self.assertEqual(result["papers"][0]["evidence_level"], "abstract")

    def test_methods_and_evidence_synthesis_scopes_activate_their_journal_packs(self) -> None:
        result = discover_openalex(
            ["econometrics", "meta_analysis"],
            as_of="2026-07-16",
            per_query=1,
            request_func=lambda *args, **kwargs: FakeResponse(),
            api_key="test-key",
        )
        self.assertTrue(any("venue_issn=0304-4076" in query for query in result["queries"]))
        self.assertTrue(any("venue_issn=0022-0515" in query for query in result["queries"]))


if __name__ == "__main__":
    unittest.main()
