from __future__ import annotations

import dataclasses
import datetime as dt
import sys
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from scout_core import (  # noqa: E402
    DEFAULT_SOURCE_POLICY,
    assess_candidate_source_mix,
    build_manifest,
    classify_clusters,
    deduplicate_papers,
    journal_rank_weight,
    pattern_card_hash,
    select_candidates,
    source_quality_tier,
    source_plan,
    validate_public_query,
)


def paper(index: int, *, source: str, venue: str, cluster: str, abstract: bool = True) -> dict:
    return {
        "title": f"A sufficiently long economics paper title number {index}",
        "doi": f"10.1234/scout.{index}",
        "url": f"https://doi.org/10.1234/scout.{index}",
        "published": f"2026-0{index}-01",
        "venue": venue,
        "source_family": source,
        "cluster": cluster,
        "abstract": "Evidence from an identified design." if abstract else "",
    }


def candidate(index: int, *, cluster: str, ai: bool, score: float) -> dict:
    return {
        "candidate_id": f"candidate-{index}",
        "title": f"Candidate {index}",
        "cluster": cluster,
        "mechanism": "A binding allocation margin changes durable human capital.",
        "unit": "new workers",
        "exposure": "manager bandwidth shock",
        "outcomes": "retention and promotion",
        "falsifiable_comparison": "effects vanish when feedback is not constrained",
        "data_identification": "manager moves and administrative panel data",
        "why_now": "recent work measures manager-worker links",
        "overlap": "adjacent to an existing novice-learning idea",
        "largest_risk": "manager assignment may be endogenous",
        "nearest_paper_ids": ["doi:10.1/a", "doi:10.1/b"],
        "is_ai_topic": ai,
        "score": score,
    }


class ScoutCoreTests(unittest.TestCase):
    def test_source_plan_is_broad_and_does_not_change_weekly_tracker(self) -> None:
        plan = source_plan(["labor", "education", "metascience"], as_of="2026-07-16")
        self.assertEqual(plan["journal_months"], 24)
        self.assertEqual(plan["working_paper_months"], 12)
        self.assertIn("econ_top5", plan["source_packs"])
        self.assertIn("labor_field", plan["source_packs"])
        self.assertIn("metascience_registries", plan["source_packs"])
        self.assertIn("econometrics_methods", plan["source_packs"])
        self.assertIn("evidence_synthesis", plan["source_packs"])
        self.assertNotIn("Journal of Business & Economic Statistics", plan["sources"]["econometrics_methods"])
        self.assertIn("Journal of Business & Economic Statistics", plan["blocked_or_probe_required"])
        self.assertEqual(plan["topic_budget"]["labor"] + plan["topic_budget"]["education"], 0.7)
        self.assertEqual(plan["source_policy"]["priority_retrieval_target_share"], 0.8)
        self.assertEqual(plan["source_policy"]["openalex_role"], "discovery_index_only")
        self.assertEqual(plan["source_policy"]["arxiv_role"], "supplemental_low_prior")
        self.assertTrue(plan["source_policy"]["abstract_access_required"])
        self.assertTrue(plan["source_policy"]["separate_attention_from_entry_opportunity"])

        default_plan = source_plan(as_of="2026-07-16")
        self.assertEqual(default_plan["scope"], ["labor", "education"])
        self.assertNotIn("metascience_registries", default_plan["source_packs"])

    def test_private_profile_text_cannot_enter_external_query(self) -> None:
        self.assertEqual(validate_public_query("manager feedback novice human capital"), "manager feedback novice human capital")
        for unsafe in (
            "C:\\Users\\name\\researcher_profile.md",
            "private@example.test labor economics",
            "read my researcher_profile and search",
        ):
            with self.assertRaises(ValueError):
                validate_public_query(unsafe)

    def test_title_only_version_suspicions_are_retained_not_auto_merged(self) -> None:
        first = paper(1, source="OpenAlex", venue="AER", cluster="managers")
        duplicate = dict(first)
        duplicate["abstract"] = ""
        duplicate["url"] = "https://example.test/version"
        duplicate.pop("doi")
        papers = deduplicate_papers([duplicate, first, paper(2, source="NBER", venue="NBER", cluster="managers", abstract=False)])
        self.assertEqual(len(papers), 3)
        same_title = [item for item in papers if item.title == first["title"]]
        self.assertEqual(len(same_title), 2)
        self.assertTrue(any(item.suspected_version_of for item in same_title))
        self.assertTrue(any(item.evidence_level == "title_only" for item in papers))

    def test_hotspot_requires_three_papers_and_two_source_families_or_venues(self) -> None:
        papers = deduplicate_papers([
            paper(1, source="OpenAlex", venue="AER", cluster="managers"),
            paper(2, source="NBER", venue="NBER", cluster="managers"),
            paper(3, source="OpenAlex", venue="JOLE", cluster="managers"),
            paper(4, source="OpenAlex", venue="AER", cluster="credentials"),
        ])
        labels = {item["cluster"]: item["label"] for item in classify_clusters(papers)}
        self.assertEqual(labels["managers"], "hotspot")
        self.assertEqual(labels["credentials"], "emerging_signal")

    def test_hotspot_counts_only_papers_inside_the_configured_window(self) -> None:
        recent = [
            paper(1, source="OpenAlex", venue="AER", cluster="managers"),
            paper(2, source="NBER Working Paper", venue="NBER", cluster="managers"),
        ]
        recent[0]["published"] = "2026-06-01"
        recent[1]["published"] = "2026-05-01"
        old = paper(3, source="NBER Working Paper", venue="NBER", cluster="managers")
        old["published"] = "2023-01-01"
        cluster = classify_clusters(
            deduplicate_papers([*recent, old]),
            as_of=dt.date(2026, 7, 16),
            journal_months=24,
            working_paper_months=12,
        )[0]
        self.assertEqual(cluster["label"], "emerging_signal")
        self.assertEqual(cluster["paper_count"], 2)
        self.assertEqual(cluster["total_paper_count"], 3)
        self.assertEqual(len(cluster["out_of_window_or_undated_ids"]), 1)

    def test_hotspot_uses_rank_weighted_attention_not_publication_count_alone(self) -> None:
        low_rank = []
        for index in (1, 2, 3):
            item = paper(index, source="supplemental journal", venue=f"Unknown Journal {index}", cluster="dense")
            item["journal_rank_weight"] = 0.1
            low_rank.append(item)
        cluster = classify_clusters(deduplicate_papers(low_rank))[0]
        self.assertEqual(cluster["paper_count"], 3)
        self.assertEqual(cluster["label"], "emerging_signal")
        self.assertLess(cluster["tier_weighted_attention"], 1.6)

        high_rank = [
            paper(4, source="official_journal", venue="American Economic Review", cluster="frontier"),
            paper(5, source="official_journal", venue="Journal of Labor Economics", cluster="frontier"),
            paper(6, source="NBER working paper", venue="NBER Working Paper", cluster="frontier"),
        ]
        cluster = classify_clusters(deduplicate_papers(high_rank))[0]
        self.assertEqual(cluster["label"], "hotspot")
        self.assertGreaterEqual(cluster["tier_weighted_attention"], 1.6)
        self.assertEqual(cluster["opportunity_status"], "requires_candidate_level_semantic_and_feasibility_review")

    def test_volume_is_reported_as_crowding_not_unbounded_opportunity(self) -> None:
        items = [
            paper(index, source="official_journal", venue="American Economic Review", cluster="crowded")
            for index in range(1, 7)
        ]
        cluster = classify_clusters(deduplicate_papers(items))[0]
        self.assertEqual(cluster["crowding_risk"], "high")
        self.assertNotIn("opportunity_score", cluster)

    def test_catalog_rank_prior_is_attached_to_verified_venue(self) -> None:
        ranked = deduplicate_papers([
            paper(1, source="OpenAlex", venue="Journal of Econometrics", cluster="methods")
        ])[0]
        unknown = deduplicate_papers([
            paper(2, source="OpenAlex", venue="Unknown Journal", cluster="methods")
        ])[0]
        self.assertEqual(journal_rank_weight(ranked), 0.86)
        self.assertEqual(journal_rank_weight(unknown), 0.0)

    def test_openalex_is_discovery_route_not_a_quality_signal(self) -> None:
        verified = paper(1, source="OpenAlex", venue="Quarterly Journal of Economics", cluster="education")
        unknown = paper(2, source="OpenAlex", venue="Unknown Repository Venue", cluster="education")
        arxiv = paper(3, source="arXiv", venue="arXiv", cluster="education")
        normalized = deduplicate_papers([verified, unknown, arxiv])
        tiers = {item.title: source_quality_tier(item) for item in normalized}
        self.assertEqual(tiers[verified["title"]], "priority_economics")
        self.assertEqual(tiers[unknown["title"]], "open_discovery")
        self.assertEqual(tiers[arxiv["title"]], "open_discovery")

        cluster = classify_clusters(
            normalized,
            as_of=dt.date(2026, 7, 16),
            exclude_open_discovery=True,
        )[0]
        self.assertEqual(cluster["paper_count"], 1)
        self.assertEqual(len(cluster["low_prior_support_ids"]), 2)
        self.assertEqual(cluster["label"], "emerging_signal")

    def test_candidate_source_mix_requires_curated_economics_anchors(self) -> None:
        raw_papers = [
            paper(1, source="official_journal", venue="Journal of Labor Economics", cluster="labor"),
            paper(2, source="NBER working paper", venue="NBER Working Paper", cluster="labor"),
            paper(3, source="arXiv", venue="arXiv", cluster="labor"),
        ]
        papers = deduplicate_papers(raw_papers)
        ids = {item.title: item.paper_id for item in papers}
        good = candidate(1, cluster="labor", ai=False, score=1)
        good["nearest_paper_ids"] = [ids[raw_papers[0]["title"]], ids[raw_papers[1]["title"]]]
        result = assess_candidate_source_mix(
            [good], papers, aggregate_min_share=0.7, per_candidate_min_share=0.5
        )
        self.assertEqual(result["priority_share"], 1.0)
        self.assertGreater(result["mean_rank_weight"], 0)

        weak = candidate(2, cluster="labor", ai=False, score=1)
        weak["nearest_paper_ids"] = [ids[raw_papers[2]["title"]], ids[raw_papers[0]["title"]]]
        with self.assertRaisesRegex(ValueError, "aggregate priority share"):
            assess_candidate_source_mix(
                [weak], papers, aggregate_min_share=0.7, per_candidate_min_share=0.5
            )

    def test_candidate_selection_enforces_non_ai_floor_and_cluster_cap(self) -> None:
        selected = select_candidates([
            candidate(1, cluster="a", ai=True, score=10),
            candidate(2, cluster="a", ai=True, score=9),
            candidate(3, cluster="a", ai=True, score=8),
            candidate(4, cluster="b", ai=False, score=7),
            candidate(5, cluster="c", ai=False, score=6),
            candidate(6, cluster="d", ai=False, score=5),
        ], limit=6)
        self.assertGreaterEqual(sum(not item["is_ai_topic"] for item in selected), 3)
        self.assertLessEqual(sum(item["cluster"] == "a" for item in selected), 2)
        self.assertTrue(all(item["idea_origin"] == "ai_generated" for item in selected))

    def test_manifest_contains_hash_not_private_pattern_card(self) -> None:
        style_hash = pattern_card_hash({"likes": ["mechanisms"], "private": "not exported"})
        payload = {
            "run_id": "scout-20260716-test",
            "created_at": "2026-07-16T12:00:00+00:00",
            "style_hash": style_hash,
            "queries": ["labor economics manager feedback"],
            "papers": [paper(1, source="OpenAlex", venue="AER", cluster="managers")],
            "source_health": {"openalex": {"status": "ok", "count": 1}},
        }
        manifest = build_manifest(payload)
        self.assertEqual(manifest["schema_version"], "1.1")
        self.assertTrue(manifest["source_policy"]["abstract_access_required"])
        self.assertEqual(manifest["style_hash"], style_hash)
        self.assertNotIn("private", str(manifest))
        self.assertEqual(len(manifest["manifest_hash"]), 64)

        rebuilt = build_manifest(manifest)
        self.assertEqual(rebuilt, manifest)
        self.assertEqual(rebuilt["manifest_hash"], manifest["manifest_hash"])

    def test_legacy_manifest_rebuild_does_not_guess_new_ranking_fields(self) -> None:
        payload = {
            "schema_version": "1.0",
            "run_id": "scout-20260716-legacy",
            "created_at": "2026-07-16T12:00:00+00:00",
            "style_hash": "b" * 64,
            "queries": ["labor economics"],
            "papers": [paper(1, source="OpenAlex", venue="AER", cluster="labor")],
        }
        manifest = build_manifest(payload)
        self.assertNotIn("journal_rank_weight", manifest["papers"][0])
        self.assertEqual(build_manifest(manifest), manifest)

    def test_manifest_rejects_candidate_citations_outside_run(self) -> None:
        payload = {
            "run_id": "scout-20260716-nearest",
            "created_at": "2026-07-16T12:00:00+00:00",
            "style_hash": "a" * 64,
            "queries": ["labor economics manager feedback"],
            "papers": [paper(1, source="OpenAlex", venue="AER", cluster="managers")],
            "candidates": [candidate(1, cluster="managers", ai=False, score=10)],
            "candidate_limit": 1,
        }
        with self.assertRaisesRegex(ValueError, "absent from the run manifest"):
            build_manifest(payload)

    def test_non_ai_floor_is_a_hard_constraint(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-AI candidates"):
            select_candidates([
                candidate(1, cluster="a", ai=True, score=10),
                candidate(2, cluster="b", ai=False, score=9),
            ], limit=2, min_non_ai_ratio=1.0)


if __name__ == "__main__":
    unittest.main()
