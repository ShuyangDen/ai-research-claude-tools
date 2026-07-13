from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))
sys.path.insert(0, str(PACKAGE_DIR.parent / "research-core" / "src"))

from tracker_core import (  # noqa: E402
    SourceConfigurationError,
    SourceFetchError,
    SourceHealthReport,
    crossref_contact_params,
    default_lane,
    enforce_tier_1_contract,
    load_recommendation_profile,
    parse_recipients,
    request_with_retry,
    safe_error_summary,
    stable_paper_id,
    stratified_evaluation_sample,
    update_queue_state,
)
try:
    from research_core.profile import project_profile  # noqa: E402
except ModuleNotFoundError:  # Standalone private Tracker does not vendor research-core.
    project_profile = None


class FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.content = b""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class StablePaperIdTests(unittest.TestCase):
    def test_identifier_priority_and_normalization(self) -> None:
        paper_id = stable_paper_id(
            title="Example",
            url="https://openalex.org/W123",
            doi="https://doi.org/10.1234/ABC.9",
            arxiv_id="2401.01234v2",
        )
        self.assertEqual(paper_id, "doi:10.1234/abc.9")

    def test_arxiv_versions_collapse(self) -> None:
        self.assertEqual(
            stable_paper_id(title="A", url="https://arxiv.org/abs/2401.01234v3"),
            stable_paper_id(title="A", arxiv_id="2401.01234v1"),
        )

    def test_url_fallback_is_stable(self) -> None:
        self.assertEqual(
            stable_paper_id(title="A", url="HTTPS://EXAMPLE.COM/paper/"),
            stable_paper_id(title="Different", url="https://example.com/paper"),
        )

    def test_signal_id_family_defaults_to_exploit_lane(self) -> None:
        self.assertEqual(default_lane(tier=1, matched_signal="active:abc123"), "exploit")
        self.assertEqual(default_lane(tier=1, matched_signal="preference:def456"), "exploit")


class EvaluationAndPrivacyUtilityTests(unittest.TestCase):
    def test_evaluation_sample_is_recent_stratified_and_bounded(self) -> None:
        papers = [
            SimpleNamespace(source="Alpha", published="2026-07-13", title="A new", url="https://a/new"),
            SimpleNamespace(source="Alpha", published="2026-07-01", title="A old", url="https://a/old"),
            SimpleNamespace(source="Beta", published="2026-07-12", title="B new", url="https://b/new"),
            SimpleNamespace(source="Beta", published="2026-06-01", title="B old", url="https://b/old"),
            SimpleNamespace(source="Gamma", published="2026-07-11", title="C new", url="https://c/new"),
        ]
        selected = stratified_evaluation_sample(papers, 4)
        self.assertEqual([paper.title for paper in selected], ["A new", "B new", "C new", "A old"])

    def test_recipient_parser_deduplicates_without_log_formatting(self) -> None:
        self.assertEqual(
            parse_recipients("first@example.test, second@example.test, FIRST@example.test"),
            ["first@example.test", "second@example.test"],
        )
        with self.assertRaises(ValueError):
            parse_recipients(" , ")
        runner = (PACKAGE_DIR / "run_weekly_digest.py").read_text(encoding="utf-8")
        email_util = (PACKAGE_DIR / "utils_pdf_email.py").read_text(encoding="utf-8")
        self.assertNotIn('print(f"Sending to: {recipient_email}")', runner)
        self.assertIn("undisclosed-recipients:;", email_util)

    def test_crossref_contact_is_not_derived_from_recipients(self) -> None:
        self.assertEqual(
            crossref_contact_params({"RECIPIENT_EMAIL": "private@example.test"}),
            {},
        )
        self.assertEqual(
            crossref_contact_params({"PAPER_TRACKER_CONTACT_EMAIL": "contact@example.test"}),
            {"mailto": "contact@example.test"},
        )
        extractor = (PACKAGE_DIR / "paperextract.py").read_text(encoding="utf-8")
        self.assertNotIn('os.environ.get("RECIPIENT_EMAIL"', extractor)

    def test_error_summary_redacts_request_data(self) -> None:
        error = RuntimeError(
            "failed https://example.test/works?mailto=private%40example.test&api_key=topsecret "
            "for private@example.test"
        )
        summary = safe_error_summary(error)
        self.assertNotIn("private", summary)
        self.assertNotIn("topsecret", summary)
        self.assertIn("[redacted]", summary)

        health = SourceHealthReport(run_date="2026-07-13")
        health.failure("example", error, core=True)
        serialized = json.dumps(health.sources)
        self.assertNotIn("private", serialized)
        self.assertNotIn("topsecret", serialized)


class RetryTests(unittest.TestCase):
    def test_retries_500_then_succeeds(self) -> None:
        responses = iter([FakeResponse(500), FakeResponse(200)])
        calls = []

        def fake_get(url: str, **kwargs):
            calls.append((url, kwargs))
            return next(responses)

        response = request_with_retry(
            "test",
            "https://example.test",
            request_func=fake_get,
            max_attempts=2,
            backoff_seconds=0,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls), 2)

    def test_http_400_is_permanent(self) -> None:
        with self.assertRaises(SourceConfigurationError):
            request_with_retry(
                "test",
                "https://example.test",
                request_func=lambda *args, **kwargs: FakeResponse(400),
                backoff_seconds=0,
            )

    def test_network_exception_does_not_retain_request_values(self) -> None:
        def failing_get(*args, **kwargs):
            raise RuntimeError(
                "connection failed for /works?mailto=private%40example.test&token=topsecret"
            )

        with self.assertRaises(SourceFetchError) as caught:
            request_with_retry(
                "test",
                "https://example.test",
                request_func=failing_get,
                max_attempts=1,
                backoff_seconds=0,
            )
        message = str(caught.exception)
        self.assertNotIn("private", message)
        self.assertNotIn("topsecret", message)


class ProfileTests(unittest.TestCase):
    @unittest.skipIf(project_profile is None, "research-core is not installed")
    def test_real_research_core_projection_loads_in_tracker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            markdown = root / "researcher_profile.md"
            structured = root / "recommendation_profile.json"
            markdown.write_text("# fallback", encoding="utf-8")
            common = {
                "schema_version": "1.0",
                "status": "active",
                "mechanism": "learning by doing",
                "retrieval_terms": ["learning by doing"],
                "source_refs": [{"type": "test", "id": "fixture"}],
                "confidence": 1.0,
                "priority": "high",
                "observed_at": "2026-07-01T00:00:00Z",
                "updated_at": "2026-07-01T00:00:00Z",
            }
            projection = project_profile(
                [
                    {
                        **common,
                        "signal_id": "portfolio:real",
                        "signal_type": "portfolio",
                        "title": "AI entry jobs",
                        "human_approved": True,
                    },
                    {
                        **common,
                        "signal_id": "negative:real",
                        "signal_type": "negative",
                        "title": "Generic surveys",
                        "human_approved": False,
                    },
                ],
                now=datetime(2026, 7, 13, tzinfo=timezone.utc),
            )
            structured.write_text(json.dumps(projection), encoding="utf-8")
            profile = load_recommendation_profile(markdown, structured)
            self.assertEqual(profile.active_signals[0]["id"], "portfolio:real")
            self.assertEqual(profile.tier_1_signal_ids, ["portfolio:real"])
            self.assertEqual(profile.negative_signals, ["Generic surveys: learning by doing"])
            self.assertEqual(profile.lane_weights["exploit"], 0.55)

    def test_research_core_projection_is_consumed_without_a_second_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            markdown = root / "researcher_profile.md"
            structured = root / "recommendation_profile.json"
            markdown.write_text("# fallback", encoding="utf-8")
            structured.write_text(
                json.dumps({
                    "recommendation_lane_weights": {
                        "exploit": 0.55,
                        "adjacent": 0.20,
                        "contradiction": 0.15,
                        "methodology": 0.10,
                    },
                    "lanes": {
                        "declared": [{
                            "signal_id": "declared:one",
                            "signal_type": "declared",
                            "title": "Human capital",
                            "mechanism": "learning by doing",
                            "retrieval_terms": ["learning by doing"],
                            "projection_score": 1.0,
                            "tier_1_eligible": True,
                        }],
                        "portfolio": [{
                            "signal_id": "portfolio:one",
                            "signal_type": "portfolio",
                            "title": "AI entry jobs",
                            "mechanism": "task allocation",
                            "retrieval_terms": ["entry jobs"],
                            "projection_score": 0.8,
                            "tier_1_eligible": True,
                        }],
                        "inferred": [{
                            "signal_id": "inferred:one",
                            "signal_type": "inferred",
                            "title": "Null results",
                            "mechanism": "credible counterevidence",
                            "retrieval_terms": ["null result"],
                            "projection_score": 0.5,
                            "tier_1_eligible": False,
                        }],
                        "speculative": [],
                        "negative": [{
                            "signal_id": "negative:one",
                            "signal_type": "negative",
                            "title": "No generic adoption surveys",
                            "mechanism": "low fit",
                            "projection_score": -0.5,
                            "tier_1_eligible": False,
                        }],
                    }
                }),
                encoding="utf-8",
            )
            profile = load_recommendation_profile(markdown, structured)
            self.assertEqual([item["id"] for item in profile.active_signals], ["declared:one", "portfolio:one"])
            self.assertEqual(profile.tier_1_signal_ids, ["declared:one", "portfolio:one"])
            self.assertEqual(profile.retrieval_terms, ["learning by doing", "entry jobs", "null result"])
            self.assertEqual(profile.lane_weights["contradiction"], 0.15)
            self.assertEqual(profile.negative_signals, ["No generic adoption surveys: low fit"])

    def test_markdown_profile_is_compact_and_has_retrieval_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "researcher_profile.md"
            path.write_text(
                """# Profile

## Retrieval Terms
- generative AI, newcomer learning

## Active Research Directions
1. **Learning ladder**: near-frontier practice and human capital.

## Current Interest Signals
- Entry-level task allocation.

## Reading Preference Signals
- High value: credible null results.

## Unrelated Private Prose
""" + ("do not include " * 1000),
                encoding="utf-8",
            )
            profile = load_recommendation_profile(path)
            self.assertEqual(profile.retrieval_terms, ["generative AI", "newcomer learning"])
            self.assertEqual(len(profile.active_signals), 1)
            self.assertEqual(
                profile.tier_1_signal_ids,
                [profile.active_signals[0]["id"]],
            )
            self.assertEqual(
                enforce_tier_1_contract(
                    1, profile.active_signals[0]["id"], profile
                ),
                1,
            )
            self.assertEqual(
                enforce_tier_1_contract(
                    1, profile.current_interests[0]["id"], profile
                ),
                2,
            )
            self.assertEqual(enforce_tier_1_contract(1, "invented:signal", profile), 2)
            prompt = profile.compact_prompt()
            self.assertNotIn("do not include", prompt)
            self.assertLess(len(prompt), 5000)
            self.assertIsInstance(json.loads(prompt), dict)

    def test_large_structured_profile_stays_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            markdown = Path(tmp) / "researcher_profile.md"
            structured = Path(tmp) / "recommendation_profile.json"
            markdown.write_text("# fallback", encoding="utf-8")
            structured.write_text(
                json.dumps({
                    "retrieval_terms": [f"term {i}" for i in range(20)],
                    "active_signals": [
                        {"id": f"active:{i}", "text": "x" * 360, "weight": 1.0}
                        for i in range(20)
                    ],
                    "current_interests": [],
                    "reading_preferences": [],
                    "negative_signals": [],
                }),
                encoding="utf-8",
            )
            prompt = load_recommendation_profile(markdown, structured).compact_prompt(max_chars=1000)
            self.assertLessEqual(len(prompt), 1000)
            self.assertIsInstance(json.loads(prompt), dict)


class QueueStateTests(unittest.TestCase):
    @staticmethod
    def paper(index: int, lane: str, tier: int = 1) -> SimpleNamespace:
        return SimpleNamespace(
            source="test",
            title=f"Paper {index}",
            abstract="Long enough",
            url=f"https://doi.org/10.1234/paper.{index}",
            doi=f"10.1234/paper.{index}",
            arxiv_id="",
            openalex_id="",
            published=f"2026-07-{index:02d}",
            venue="Test Journal",
            authors="A. Author",
            tier=tier,
            lane=lane,
            matched_signal=f"signal:{lane}",
            methodology="Methodology" if lane == "methodology" else "RCT",
            recommendation_score=100 - index,
            paper_id="",
        )

    def test_global_cap_lane_mix_and_legacy_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "queue_state.jsonl"
            markdown = Path(tmp) / "reading_queue.md"
            papers = [
                self.paper(1, "exploit"),
                self.paper(2, "adjacent", 2),
                self.paper(3, "contradiction"),
                self.paper(4, "methodology", 3),
                self.paper(5, "exploit"),
            ]
            summary = update_queue_state(
                papers,
                state_path=state,
                markdown_path=markdown,
                max_new=4,
                lane_weights={
                    "exploit": 0.25,
                    "adjacent": 0.25,
                    "contradiction": 0.25,
                    "methodology": 0.25,
                },
                today="2026-07-13",
            )
            self.assertEqual(summary["added"], 4)
            self.assertEqual(summary["lane_counts"], {
                "exploit": 1,
                "adjacent": 1,
                "contradiction": 1,
                "methodology": 1,
            })
            records = [json.loads(line) for line in state.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 4)
            self.assertTrue(all(record["matched_signal"] for record in records))
            rendered = markdown.read_text(encoding="utf-8")
            self.assertIn("Canonical state: `queue_state.jsonl`", rendered)
            self.assertIn("| candidate-slug | title | tier |", rendered)

    def test_second_run_does_not_readd_same_doi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "queue_state.jsonl"
            markdown = Path(tmp) / "reading_queue.md"
            paper = self.paper(1, "exploit")
            first = update_queue_state(
                [paper], state_path=state, markdown_path=markdown, max_new=5, today="2026-07-13"
            )
            second = update_queue_state(
                [paper], state_path=state, markdown_path=markdown, max_new=5, today="2026-07-20"
            )
            self.assertEqual(first["added"], 1)
            self.assertEqual(second["added"], 0)
            record = json.loads(state.read_text(encoding="utf-8").strip())
            self.assertEqual(record["last_seen"], "2026-07-20")

    def test_legacy_url_identity_upgrades_to_doi_without_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "queue_state.jsonl"
            markdown = Path(tmp) / "reading_queue.md"
            first_paper = self.paper(1, "exploit")
            first_paper.title = "A sufficiently distinctive economics paper title"
            first_paper.url = "https://publisher.example/papers/one"
            first_paper.doi = ""
            update_queue_state(
                [first_paper], state_path=state, markdown_path=markdown, max_new=5, today="2026-07-13"
            )

            doi_version = self.paper(2, "exploit")
            doi_version.title = first_paper.title
            doi_version.url = "https://doi.org/10.1234/same-paper"
            doi_version.doi = "10.1234/same-paper"
            summary = update_queue_state(
                [doi_version], state_path=state, markdown_path=markdown, max_new=5, today="2026-07-20"
            )

            records = [json.loads(line) for line in state.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(summary["added"], 0)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["paper_id"], "doi:10.1234/same-paper")

    def test_legacy_markdown_sorts_newest_first_within_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "queue_state.jsonl"
            markdown = Path(tmp) / "reading_queue.md"
            older = self.paper(1, "exploit")
            newer = self.paper(2, "exploit")
            update_queue_state(
                [older], state_path=state, markdown_path=markdown, max_new=5, today="2026-07-01"
            )
            update_queue_state(
                [newer], state_path=state, markdown_path=markdown, max_new=5, today="2026-07-13"
            )
            rendered = markdown.read_text(encoding="utf-8")
            self.assertLess(rendered.index("paper-2"), rendered.index("paper-1"))

    def test_six_column_legacy_queue_migrates_without_data_loss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "queue_state.jsonl"
            markdown = Path(tmp) / "reading_queue.md"
            markdown.write_text(
                """# Reading Queue

| candidate-slug | title | tier | direction | url | added |
|----------------|-------|------|-----------|-----|-------|
| legacy-paper | Legacy Paper Title | 2 | human-capital | https://example.org/legacy | 2026-07-01 |
""",
                encoding="utf-8",
            )
            summary = update_queue_state(
                [], state_path=state, markdown_path=markdown, max_new=5, today="2026-07-13"
            )
            record = json.loads(state.read_text(encoding="utf-8").strip())
            self.assertEqual(summary["total_active"], 1)
            self.assertEqual(record["candidate_slug"], "legacy-paper")
            self.assertEqual(record["matched_signal"], "manual:human-capital")


class SourceHealthTests(unittest.TestCase):
    def test_degraded_and_failed_threshold(self) -> None:
        health = SourceHealthReport(run_date="2026-07-13")
        health.success("openalex", 3, core=True)
        health.failure("arxiv", RuntimeError("timeout"), core=True)
        self.assertEqual(health.finalize(failure_threshold=2), "degraded")

        failed = SourceHealthReport(run_date="2026-07-13")
        failed.failure("openalex", RuntimeError("timeout"), core=True)
        failed.failure("arxiv", RuntimeError("timeout"), core=True)
        self.assertEqual(failed.finalize(failure_threshold=2), "failed")


if __name__ == "__main__":
    unittest.main()
