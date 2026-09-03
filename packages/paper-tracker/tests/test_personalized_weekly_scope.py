import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import paperextract as paperextract_module
from paperextract import (
    Config,
    ModelConfigurationError,
    Paper,
    build_public_search_terms,
    llm_econ_rigor_check,
    matches_weekly_scope,
    select_tier_capped_papers,
)
from run_weekly_digest import delivery_mode, main as run_weekly_main
from tracker_core import RecommendationProfile, load_recommendation_profile


class _FakeModels:
    def __init__(self) -> None:
        self.prompt = ""

    def generate_content(self, **kwargs):
        self.prompt = kwargs["contents"]
        payload = {
            "accept": True,
            "tier": 2,
            "lane": "adjacent",
            "score": 82,
            "methodology": "DiD",
            "matched_signal": "general_fit",
            "reason": "Rigorous non-AI labor paper with a profile-relevant mechanism.",
        }
        return SimpleNamespace(text=json.dumps(payload))


class _FakeClient:
    def __init__(self) -> None:
        self.models = _FakeModels()


class _PayloadModels:
    def __init__(self, payload=None, error=None) -> None:
        self.payload = payload
        self.error = error
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=json.dumps(self.payload))


class _PayloadClient:
    def __init__(self, payload=None, error=None) -> None:
        self.models = _PayloadModels(payload=payload, error=error)


class PersonalizedWeeklyScopeTests(unittest.TestCase):
    complete_abstract = (
        "We study how labor-market information changes worker sorting and wage bargaining using "
        "a difference-in-differences design around staggered disclosure laws. The analysis links "
        "vacancy postings, applications, offers, and payroll records across firms before and after "
        "the reforms. We find that disclosure changes applicant composition, narrows information "
        "gaps, and shifts realized starting pay, with larger responses in initially opaque markets."
    )

    def setUp(self) -> None:
        self.profile = RecommendationProfile(
            retrieval_terms=[
                "strategic compliance",
                "multidimensional measurement",
                "implementation costs",
            ]
        )

    def test_ai_is_balanced_anchor_not_mandatory_gate(self) -> None:
        terms = build_public_search_terms(self.profile, limit=12)
        self.assertIn("artificial intelligence labor", terms)
        self.assertIn("strategic compliance", terms)
        self.assertIn("labor economics", terms)
        self.assertIn("economics of education", terms)

        self.assertTrue(
            matches_weekly_scope(
                "Pay transparency changes wage bargaining through strategic compliance.",
                self.profile,
            )
        )
        self.assertTrue(
            matches_weekly_scope(
                "Item response methods change school value added estimates.",
                self.profile,
            )
        )
        self.assertTrue(
            matches_weekly_scope(
                "Generative AI changes worker productivity and employment.",
                self.profile,
            )
        )
        self.assertFalse(
            matches_weekly_scope(
                "A clinical oncology trial compares two chemotherapy regimens.",
                self.profile,
            )
        )

    def test_non_ai_labor_paper_can_pass_referee(self) -> None:
        client = _FakeClient()
        paper = Paper(
            source="NBER",
            title="Strategic Wage Disclosure and Worker Sorting",
            abstract=self.complete_abstract,
            url="https://example.test/paper",
            published="2026-07-20",
            venue="NBER Working Paper",
        )
        with mock.patch("paperextract.time.sleep", return_value=None):
            selected = llm_econ_rigor_check(
                client,
                Config(google_api_key="test"),
                [paper],
                self.profile,
            )
        self.assertEqual([item.title for item in selected], [paper.title])
        self.assertIn("AI is one\nsubstantive interest among several", client.models.prompt)
        self.assertIn("AI/LLMs/automation are welcome", client.models.prompt)
        self.assertNotIn("AI IS THE MAIN SUBJECT", client.models.prompt)

    def test_weekly_tier_caps_and_delivery_defaults(self) -> None:
        config = Config(google_api_key="test")
        self.assertEqual((config.tier1_max, config.tier2_max, config.tier3_max), (15, 15, 5))
        self.assertEqual(config.tier1_min_score, 90)
        self.assertEqual(config.weekly_max_new, 35)
        self.assertEqual(delivery_mode({}), "email")
        self.assertEqual(
            delivery_mode({"PAPER_TRACKER_DELIVERY_MODE": "local"}),
            "local",
        )
        with self.assertRaises(ValueError):
            delivery_mode({"PAPER_TRACKER_DELIVERY_MODE": "disabled"})

    def test_tier_caps_are_independent(self) -> None:
        papers = []
        for tier, count in ((1, 18), (2, 19), (3, 9)):
            for index in range(count):
                papers.append(
                    Paper(
                        source="fixture",
                        title=f"T{tier} paper {index}",
                        abstract="A sufficiently long abstract for a deterministic fixture.",
                        url=f"https://example.test/{tier}/{index}",
                        published="2026-07-20",
                        tier=tier,
                        recommendation_score=100 - index,
                    )
                )
        selected = select_tier_capped_papers(
            papers,
            tier1_max=15,
            tier2_max=15,
            tier3_max=5,
        )
        self.assertEqual(sum(paper.tier == 1 for paper in selected), 15)
        self.assertEqual(sum(paper.tier == 2 for paper in selected), 15)
        self.assertEqual(sum(paper.tier == 3 for paper in selected), 5)

    def test_tier1_overflow_becomes_tier2_skims(self) -> None:
        papers = []
        for tier, count in ((1, 27), (2, 2), (3, 22)):
            for index in range(count):
                papers.append(
                    Paper(
                        source="fixture",
                        title=f"T{tier} overflow paper {index}",
                        abstract="A sufficiently long abstract for the tier-overflow fixture.",
                        url=f"https://example.test/overflow/{tier}/{index}",
                        published="2026-07-20",
                        tier=tier,
                        recommendation_score=100 - index,
                    )
                )
        selected = select_tier_capped_papers(
            papers, tier1_max=15, tier2_max=15, tier3_max=5
        )
        self.assertEqual(sum(paper.tier == 1 for paper in selected), 15)
        self.assertEqual(sum(paper.tier == 2 for paper in selected), 14)
        self.assertEqual(sum(paper.tier == 3 for paper in selected), 5)

    def test_rejected_paper_may_return_null_tier(self) -> None:
        client = _PayloadClient(
            payload={
                "accept": False,
                "tier": None,
                "lane": None,
                "score": None,
                "methodology": "Descriptive",
                "matched_signal": None,
                "match_strength": "none",
                "reason": "Outside scope.",
            }
        )
        paper = Paper(
            source="fixture",
            title="Unrelated descriptive paper",
            abstract="This is a sufficiently long abstract for a deterministic rejected-paper fixture.",
            url="https://example.test/reject",
            published="2026-07-20",
        )
        with mock.patch("paperextract.time.sleep", return_value=None):
            selected = llm_econ_rigor_check(
                client, Config(google_api_key="test"), [paper], self.profile
            )
        self.assertEqual(selected, [])

    def test_tier1_requires_direct_high_score_match(self) -> None:
        signal_id = "active:specific-mechanism"
        profile = RecommendationProfile(
            tier_1_signal_ids=[signal_id],
            active_signals=[{"id": signal_id, "text": "A specific mechanism"}],
        )

        def classify(match_strength: str, score: int) -> int:
            client = _PayloadClient(
                payload={
                    "accept": True,
                    "tier": 1,
                    "lane": "exploit",
                    "score": score,
                    "methodology": "DiD",
                    "matched_signal": signal_id,
                    "match_strength": match_strength,
                    "reason": "Fixture.",
                }
            )
            paper = Paper(
                source="fixture",
                title=f"Fixture {match_strength} {score}",
                abstract=self.complete_abstract,
                url=f"https://example.test/{match_strength}/{score}",
                published="2026-07-20",
            )
            with mock.patch("paperextract.time.sleep", return_value=None):
                return llm_econ_rigor_check(
                    client, Config(google_api_key="test"), [paper], profile
                )[0].tier

        self.assertEqual(classify("broad", 99), 2)
        self.assertEqual(classify("direct", 89), 2)
        self.assertEqual(classify("direct", 95), 1)

    def test_invalid_api_key_fails_fast(self) -> None:
        client = _PayloadClient(error=RuntimeError("API_KEY_INVALID: API key not valid"))
        paper = Paper(
            source="fixture",
            title="Fixture paper",
            abstract=self.complete_abstract,
            url="https://example.test/auth",
            published="2026-07-20",
        )
        with mock.patch("paperextract.time.sleep", return_value=None):
            with self.assertRaises(ModelConfigurationError):
                llm_econ_rigor_check(
                    client, Config(google_api_key="test"), [paper], self.profile
                )
        self.assertEqual(client.models.calls, 1)

    def test_markdown_fallback_preserves_human_positive_reasons(self) -> None:
        markdown = """# Researcher Profile
## Retrieval Terms
- labor economics, economics of education, strategic compliance, meta-analysis economics

## Idea Evaluation Preference Signals (Human-Confirmed 2026-07-21)
**1. Hidden strategic responses and overlooked information margins**

Prefer familiar institutional artifacts that reveal an overlooked strategic compliance margin.

**2. Fine-grained methods for important traditional economics questions**

Prefer multidimensional measurement when it changes a traditional labor or education conclusion.

**3. Implementation cost and institutional-capacity heterogeneity**

Prefer mechanisms identifying who bears implementation and enforcement costs.

**4. AI as an aggregation of heterogeneous human judgment**

Treat AI screening as a weighted synthesis of heterogeneous human research tastes.

**5. Data feasibility is necessary but not sufficient**

Require a named exogenous margin and an obtainable dataset before topic appeal can carry an idea.

**6. Candidate-specific low interest must not become an invented broad exclusion**

Do not generalize a candidate-level rejection into a field-wide negative preference.

## Active Research Directions
1. **AI learning ladder**: entry-level task allocation and durable skill formation.
"""
        with tempfile.TemporaryDirectory() as tmp:
            markdown_path = Path(tmp) / "researcher_profile.md"
            markdown_path.write_text(markdown, encoding="utf-8")
            profile = load_recommendation_profile(
                markdown_path, Path(tmp) / "missing-recommendation-profile.json"
            )

        expected_ids = {
            "declared:core-labor-education-human-capital",
            "declared:hidden-strategic-compliance-information",
            "declared:fine-grained-methods-classic-economics",
            "declared:implementation-cost-capacity-heterogeneity",
            "declared:identification-data-feasibility",
        }
        self.assertTrue(expected_ids.issubset(set(profile.tier_1_signal_ids)))
        self.assertIn("labor economics", profile.retrieval_terms)
        self.assertEqual(
            profile.reading_preferences[0]["id"],
            "preference:ai-judgment-aggregation",
        )

    def test_local_mode_returns_before_pdf_or_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_extractor():
                today = __import__("datetime").date.today()
                Path(f"Econ_JMP_Report_EN_{today}.md").write_text("# English", encoding="utf-8")
                Path("source_health.preview.json").write_text("{}", encoding="utf-8")
                return {"source_health_path": "source_health.preview.json"}

            previous = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch.dict(
                    os.environ,
                    {"GOOGLE_API_KEY": "test", "PAPER_TRACKER_DELIVERY_MODE": "local"},
                    clear=False,
                ), mock.patch.object(
                    paperextract_module, "main", side_effect=fake_extractor
                ), mock.patch(
                    "run_weekly_digest.translate_report_to_chinese", return_value="# Chinese"
                ):
                    self.assertEqual(run_weekly_main(), 0)
            finally:
                os.chdir(previous)

            today = __import__("datetime").date.today()
            self.assertTrue((root / f"Econ_JMP_Report_EN_{today}.md").exists())
            self.assertTrue((root / f"Econ_JMP_Report_CN_{today}.md").exists())


if __name__ == "__main__":
    unittest.main()
