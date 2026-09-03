from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from frontier_core import (  # noqa: E402
    TOKEN_MODES,
    build_update_plan,
)
from frontier_render import (  # noqa: E402
    extract_human_notes,
    render_cluster_note,
    render_index,
)
from frontier_state import build_frontier_state  # noqa: E402
from frontier_validation import validate_cluster_synthesis  # noqa: E402
import frontier_review as frontier_review_module  # noqa: E402
from frontier_review import _materialize, _state_lock, frontier_source_plan  # noqa: E402


def paper(
    index: int,
    *,
    venue: str,
    source: str = "official_journal",
    abstract: str | None = None,
) -> dict:
    return {
        "title": f"A sufficiently descriptive frontier economics paper {index}",
        "authors": f"Author {index}",
        "published": f"2026-0{index}-10",
        "venue": venue,
        "source_family": source,
        "url": f"https://doi.org/10.1234/frontier.{index}",
        "doi": f"10.1234/frontier.{index}",
        "abstract": abstract
        if abstract is not None
        else f"Paper {index} studies a causal labor or education mechanism using administrative data.",
        "evidence_level": "abstract" if abstract != "" else "metadata",
        "cluster": "unclustered",
    }


def base_payload(*, created_at: str = "2026-08-17T12:00:00+00:00") -> dict:
    return {
        "run_id": "frontier-20260817-test",
        "created_at": created_at,
        "scope": ["labor", "education"],
        "window_months": 12,
        "token_mode": "standard",
        "queries": ["QJE labor education 2026 abstracts", "NBER education working papers"],
        "source_health": {"status": "ok"},
        "papers": [
            paper(1, venue="Quarterly Journal of Economics"),
            paper(2, venue="Journal of Labor Economics"),
            paper(3, venue="NBER Working Paper", source="NBER working paper"),
            paper(4, venue="Unknown Journal", source="OpenAlex", abstract=""),
        ],
    }


def routed_payload(
    *,
    mixed_full_text: bool = False,
    created_at: str = "2026-08-17T12:00:00+00:00",
) -> dict:
    payload = base_payload(created_at=created_at)
    plan = build_update_plan(payload)
    eligible = [
        row["paper_id"] for row in plan["papers"] if row["evidence_level"] == "abstract"
    ]
    payload["assignments"] = [
        {
            "paper_id": paper_id,
            "primary_cluster_id": "teacher-labor-markets",
            "secondary_cluster_ids": [],
            "routing_confidence": "high",
            "routing_note": "The abstract studies teacher labor supply or human-capital production.",
        }
        for paper_id in eligible
    ]
    full_text_checks = []
    evidence_basis = "abstract_only"
    confidence = "moderate"
    if mixed_full_text:
        evidence_basis = "mixed_with_targeted_full_text"
        confidence = "high"
        full_text_checks = [
            {
                "paper_id": eligible[2],
                "version_url": "https://www.nber.org/papers/w30003",
                "matched_by": "verified_title_authors",
                "version_title": payload["papers"][2]["title"],
                "version_authors": payload["papers"][2]["authors"],
                "sections": ["Introduction", "Empirical design", "Conclusion"],
                "checked_claims": ["The design isolates an institutional hiring shock."],
                "evidence_input_tokens": 1200,
            }
        ]
    payload["clusters"] = [
        {
            "cluster_id": "teacher-labor-markets",
            "title": "Teacher Labor Markets and Human Capital",
            "aliases": ["teacher supply"],
            "research_question": "How do labor-market institutions shape teacher supply and student outcomes?",
            "current_consensus": [
                {
                    "claim": "Administrative data make teacher mobility and student exposure jointly observable.",
                    "supporting_paper_ids": eligible,
                }
            ],
            "disagreements": [
                {
                    "type": "mechanism",
                    "statement": "The papers differ on whether pay or working conditions drive retention.",
                    "relationship": "competing mechanisms in overlapping settings",
                    "side_a_paper_ids": [eligible[0]],
                    "side_b_paper_ids": [eligible[1]],
                    "resolution_status": "open",
                }
            ],
            "progress": [
                {
                    "dimension": "data",
                    "before": "Teacher and student histories were often studied separately.",
                    "now": "Linked panels trace mobility and downstream student outcomes.",
                    "supporting_paper_ids": eligible,
                }
            ],
            "open_questions": ["Do effects persist outside centralized pay systems?"],
            "paper_ids": eligible,
            "evidence_basis": evidence_basis,
            "evidence_note": "Claims are bounded by abstracts and the explicitly recorded targeted checks.",
            "full_text_checks": full_text_checks,
            "confidence": confidence,
            "change_summary": "Initial cluster map created from three recent records.",
        }
    ]
    payload["plan_hash"] = build_update_plan(payload)["plan_hash"]
    _, manifest = build_frontier_state(payload)
    payload["materialization_hash"] = manifest["materialization_hash"]
    return payload


class FrontierCoreTests(unittest.TestCase):
    def test_frontier_source_plan_excludes_unrequested_methods_and_meta_packs(self) -> None:
        plan = frontier_source_plan(["labor", "education"], as_of="2026-08-17")
        self.assertEqual(plan["journal_months"], 12)
        self.assertEqual(plan["working_paper_months"], 12)
        self.assertIn("econ_top5", plan["source_packs"])
        self.assertIn("applied_secondary", plan["source_packs"])
        self.assertNotIn("econometrics_methods", plan["source_packs"])
        self.assertNotIn("evidence_synthesis", plan["source_packs"])
        self.assertEqual(sum(plan["topic_budget"].values()), 1.0)

    def test_initial_plan_routes_only_abstract_evidence_with_bounded_packets(self) -> None:
        plan = build_update_plan(base_payload())
        self.assertEqual(plan["inventory"]["retrieved_count"], 4)
        self.assertEqual(len(plan["inventory"]["new_ids"]), 3)
        self.assertEqual(len(plan["inventory"]["metadata_only_ids"]), 1)
        routed_ids = {
            row["paper_id"] for packet in plan["router_batches"] for row in packet["papers"]
        }
        self.assertEqual(routed_ids, set(plan["inventory"]["new_ids"]))
        self.assertTrue(
            all(packet["estimated_tokens"] <= TOKEN_MODES["standard"]["router_batch_tokens"]
                for packet in plan["router_batches"])
        )

    def test_assignments_create_cluster_packets_without_full_history(self) -> None:
        payload = routed_payload()
        plan = build_update_plan(payload)
        self.assertEqual(len(plan["worker_packets"]), 1)
        packet = plan["worker_packets"][0]
        self.assertEqual(packet["cluster_id"], "teacher-labor-markets")
        self.assertLessEqual(len(packet["papers"]), TOKEN_MODES["standard"]["worker_packet_papers"])
        self.assertIsNone(packet["previous_cluster_card"])

    def test_multi_packet_cluster_has_one_quota_and_reducer_protocol(self) -> None:
        payload = base_payload()
        payload["papers"] = [
            {
                **paper(index, venue="Journal of Labor Economics"),
                "published": "2026-06-10",
            }
            for index in range(1, 11)
        ]
        initial = build_update_plan(payload)
        payload["assignments"] = [
            {
                "paper_id": paper_id,
                "primary_cluster_id": "large-cluster",
                "secondary_cluster_ids": [],
                "routing_confidence": "high",
                "routing_note": "All records answer the same bounded fixture question.",
            }
            for paper_id in initial["inventory"]["new_ids"]
        ]
        plan = build_update_plan(payload)
        packets = plan["worker_packets"]
        self.assertEqual(len(packets), 2)
        self.assertTrue(
            all(packet["output_contract"] == "partial_analysis" for packet in packets)
        )
        self.assertEqual(
            sum(packet["targeted_full_text_cap"] for packet in packets),
            TOKEN_MODES["standard"]["targeted_full_text_per_cluster"],
        )
        self.assertEqual(len(plan["reducer_packets"]), 1)
        reducer = plan["reducer_packets"][0]
        self.assertEqual(reducer["input_packet_ids"], [p["packet_id"] for p in packets])
        self.assertLessEqual(
            reducer["estimated_tokens"],
            TOKEN_MODES["standard"]["worker_packet_tokens"],
        )
        self.assertEqual(
            plan["reserved_partial_output_tokens"],
            sum(packet["output_token_cap"] for packet in packets),
        )
        self.assertEqual(
            plan["estimated_plan_tokens"],
            plan["estimated_input_tokens"]
            + plan["reserved_partial_output_tokens"],
        )
        self.assertLessEqual(
            plan["estimated_plan_tokens"],
            TOKEN_MODES["standard"]["run_input_token_ceiling"],
        )
        payload["clusters"] = [{
            "cluster_id": "large-cluster",
            "title": "A Large Labor Cluster",
            "aliases": [],
            "research_question": "What does the large fixture cluster study?",
            "current_consensus": [{
                "claim": "The fixture papers study a common labor-market question.",
                "supporting_paper_ids": initial["inventory"]["new_ids"],
            }],
            "disagreements": [],
            "progress": [],
            "open_questions": [],
            "paper_ids": initial["inventory"]["new_ids"],
            "evidence_basis": "abstract_only",
            "evidence_note": "This fixture is bounded by the supplied abstracts.",
            "full_text_checks": [],
            "confidence": "moderate",
            "change_summary": "Initial multi-packet fixture synthesis.",
        }]
        payload["plan_hash"] = plan["plan_hash"]
        _, manifest = build_frontier_state(payload)
        self.assertEqual(
            manifest["estimated_total_tokens"],
            manifest["estimated_input_tokens"]
            + manifest["reserved_partial_output_tokens"]
            + manifest["full_text_input_tokens"]
            + manifest["synthesis_output_tokens"],
        )

    def test_unchanged_papers_are_reused_and_changed_abstract_is_rerouted(self) -> None:
        first_payload = routed_payload()
        state, _ = build_frontier_state(first_payload)
        second = base_payload(created_at="2026-08-24T12:00:00+00:00")
        second["run_id"] = "frontier-20260824-test"
        plan = build_update_plan(second, state)
        self.assertEqual(len(plan["inventory"]["unchanged_ids"]), 3)
        self.assertEqual(plan["router_batches"], [])

        second["papers"][0]["abstract"] += " The updated version adds longer-run outcomes."
        changed = build_update_plan(second, state)
        self.assertEqual(len(changed["inventory"]["changed_ids"]), 1)
        self.assertEqual(
            sum(len(packet["papers"]) for packet in changed["router_batches"]), 1
        )

    def test_quarterly_reconciliation_samples_unchanged_memory(self) -> None:
        state, _ = build_frontier_state(routed_payload())
        later = base_payload(created_at="2026-12-01T12:00:00+00:00")
        later["run_id"] = "frontier-20261201-test"
        plan = build_update_plan(later, state)
        self.assertTrue(plan["reconciliation_due"])
        self.assertEqual(len(plan["inventory"]["reconcile_sample_ids"]), 1)

    def test_disagreement_references_and_full_text_provenance_are_enforced(self) -> None:
        payload = routed_payload(mixed_full_text=True)
        state, manifest = build_frontier_state(payload)
        self.assertEqual(manifest["full_text_check_count"], 1)
        cluster = state["clusters"]["teacher-labor-markets"]
        self.assertEqual(cluster["confidence"], "high")

        bad = dict(payload["clusters"][0])
        bad["evidence_basis"] = "abstract_only"
        with self.assertRaisesRegex(ValueError, "Abstract-only"):
            validate_cluster_synthesis(
                bad,
                state["papers"],
                full_text_cap=TOKEN_MODES["standard"]["targeted_full_text_per_cluster"],
            )

        bad = dict(payload["clusters"][0])
        bad["full_text_checks"] = [{
            **payload["clusters"][0]["full_text_checks"][0],
            "matched_by": "looks_similar",
        }]
        with self.assertRaisesRegex(ValueError, "version match"):
            validate_cluster_synthesis(
                bad,
                state["papers"],
                full_text_cap=TOKEN_MODES["standard"]["targeted_full_text_per_cluster"],
            )

    def test_materialization_requires_exact_assignments_and_cluster_set(self) -> None:
        payload = routed_payload()
        payload["assignments"] = payload["assignments"][:-1]
        payload["plan_hash"] = build_update_plan(payload)["plan_hash"]
        with self.assertRaisesRegex(ValueError, "exactly match routed papers"):
            build_frontier_state(payload)

        payload = routed_payload()
        extra = {**payload["clusters"][0], "cluster_id": "unplanned-cluster"}
        payload["clusters"].append(extra)
        with self.assertRaisesRegex(ValueError, "exactly match planned worker clusters"):
            build_frontier_state(payload)

    def test_claims_require_abstract_evidence_and_cluster_membership(self) -> None:
        payload = routed_payload()
        metadata_id = next(
            build_update_plan(payload)["inventory"]["metadata_only_ids"].__iter__()
        )
        payload["clusters"][0]["progress"][0]["supporting_paper_ids"] = [metadata_id]
        with self.assertRaisesRegex(ValueError, "unknown papers"):
            build_frontier_state(payload)

        payload = routed_payload()
        removed = payload["clusters"][0]["paper_ids"].pop()
        payload["clusters"][0]["current_consensus"][0]["supporting_paper_ids"] = [
            paper_id
            for paper_id in payload["clusters"][0]["current_consensus"][0]["supporting_paper_ids"]
            if paper_id != removed
        ]
        payload["clusters"][0]["progress"][0]["supporting_paper_ids"] = [
            paper_id
            for paper_id in payload["clusters"][0]["progress"][0]["supporting_paper_ids"]
            if paper_id != removed
        ]
        with self.assertRaisesRegex(ValueError, "assigned cluster membership"):
            build_frontier_state(payload)

    def test_full_text_cap_url_claims_and_match_are_enforced(self) -> None:
        payload = routed_payload(mixed_full_text=True)
        base_check = payload["clusters"][0]["full_text_checks"][0]
        payload["clusters"][0]["full_text_checks"] = [
            {**base_check, "paper_id": paper_id}
            for paper_id in payload["clusters"][0]["paper_ids"]
        ]
        with self.assertRaisesRegex(ValueError, "per-cluster cap"):
            build_frontier_state(payload)

        payload = routed_payload(mixed_full_text=True)
        payload["clusters"][0]["full_text_checks"][0]["version_url"] = "not-a-url"
        with self.assertRaisesRegex(ValueError, "HTTP"):
            build_frontier_state(payload)

        payload = routed_payload(mixed_full_text=True)
        payload["clusters"][0]["full_text_checks"][0]["checked_claims"] = []
        with self.assertRaisesRegex(ValueError, "checked claims"):
            build_frontier_state(payload)

    def test_reconciliation_clock_is_not_advanced_by_ordinary_updates(self) -> None:
        first, _ = build_frontier_state(routed_payload(created_at="2026-08-01T12:00:00+00:00"))
        october = base_payload(created_at="2026-10-01T12:00:00+00:00")
        october["run_id"] = "frontier-20261001-test"
        october["plan_hash"] = build_update_plan(october, first)["plan_hash"]
        october_state, _ = build_frontier_state(october, first)
        self.assertEqual(october_state["last_reconciled_at"], first["last_reconciled_at"])

        december = base_payload(created_at="2026-12-01T12:00:00+00:00")
        december["run_id"] = "frontier-20261201-test"
        self.assertTrue(build_update_plan(december, october_state)["reconciliation_due"])

    def test_evidence_downgrade_retains_last_verified_abstract(self) -> None:
        state, _ = build_frontier_state(routed_payload())
        update = base_payload(created_at="2026-08-24T12:00:00+00:00")
        update["run_id"] = "frontier-20260824-downgrade"
        old_id = build_update_plan(update, state)["papers"][0]["paper_id"]
        old_abstract = state["papers"][old_id]["abstract"]
        update["papers"][0]["abstract"] = ""
        update["papers"][0]["evidence_level"] = "metadata"
        plan = build_update_plan(update, state)
        self.assertIn(old_id, plan["inventory"]["evidence_downgraded_ids"])
        update["plan_hash"] = plan["plan_hash"]
        updated, _ = build_frontier_state(update, state)
        self.assertEqual(updated["papers"][old_id]["abstract"], old_abstract)
        self.assertEqual(
            updated["papers"][old_id]["latest_retrieval_evidence_level"],
            "metadata",
        )

    def test_expired_papers_retire_cluster_and_do_not_repeat(self) -> None:
        state, _ = build_frontier_state(routed_payload())
        later = base_payload(created_at="2027-05-20T12:00:00+00:00")
        later["run_id"] = "frontier-20270520-expire"
        plan = build_update_plan(later, state)
        self.assertEqual(len(plan["inventory"]["expired_previous_ids"]), 4)
        self.assertEqual({p["cluster_id"] for p in plan["worker_packets"]}, {
            "teacher-labor-markets"
        })
        later["clusters"] = [{
            "cluster_id": "teacher-labor-markets",
            "title": "Teacher Labor Markets and Human Capital",
            "aliases": ["teacher supply"],
            "status": "superseded",
            "research_question": "How do labor-market institutions shape teacher supply and student outcomes?",
            "current_consensus": [],
            "disagreements": [],
            "progress": [],
            "open_questions": [],
            "paper_ids": [],
            "evidence_basis": "abstract_only",
            "evidence_note": "All supporting papers left the rolling window.",
            "full_text_checks": [],
            "confidence": "provisional",
            "change_summary": "Retired after all evidence aged out of the 12-month window.",
        }]
        later["plan_hash"] = build_update_plan(later, state)["plan_hash"]
        updated, _ = build_frontier_state(later, state)
        self.assertEqual(updated["clusters"]["teacher-labor-markets"]["status"], "superseded")
        self.assertTrue(all(
            updated["papers"][paper_id]["frontier_status"] == "out_of_window"
            for paper_id in plan["inventory"]["expired_previous_ids"]
        ))

        next_run = base_payload(created_at="2027-06-20T12:00:00+00:00")
        next_run["run_id"] = "frontier-20270620-no-repeat"
        next_plan = build_update_plan(next_run, updated)
        self.assertEqual(next_plan["inventory"]["expired_previous_ids"], [])
        self.assertEqual(next_plan["worker_packets"], [])

    def test_state_time_scope_window_and_hash_are_monotonic(self) -> None:
        state, _ = build_frontier_state(routed_payload())
        corrupt = {**state, "run_count": 999}
        with self.assertRaisesRegex(ValueError, "state_hash"):
            build_update_plan(base_payload(created_at="2026-08-24T12:00:00+00:00"), corrupt)

        backdated = base_payload(created_at="2026-08-01T12:00:00+00:00")
        backdated["run_id"] = "frontier-20260801-backdated"
        with self.assertRaisesRegex(ValueError, "later than"):
            build_update_plan(backdated, state)

        changed_window = base_payload(created_at="2026-08-24T12:00:00+00:00")
        changed_window["run_id"] = "frontier-20260824-window"
        changed_window["window_months"] = 24
        with self.assertRaisesRegex(ValueError, "window_months cannot change"):
            build_update_plan(changed_window, state)

    def test_public_query_window_and_reserved_slug_guards(self) -> None:
        private = base_payload()
        private["queries"] = [r"C:\Users\researcher\private profile"]
        with self.assertRaisesRegex(ValueError, "local paths"):
            build_update_plan(private)

        dated = base_payload()
        dated["papers"][0]["published"] = "2020-01-01"
        dated["papers"][1]["published"] = "not-a-date"
        plan = build_update_plan(dated)
        self.assertEqual(len(plan["inventory"]["out_of_window_ids"]), 1)
        self.assertEqual(len(plan["inventory"]["undated_ids"]), 1)

        coarse = base_payload()
        coarse["papers"][0]["published"] = "2025"
        coarse_plan = build_update_plan(coarse)
        coarse_id = next(
            row["paper_id"]
            for row in coarse_plan["papers"]
            if row["title"] == coarse["papers"][0]["title"]
        )
        self.assertIn(coarse_id, coarse_plan["inventory"]["date_uncertain_ids"])
        self.assertNotIn(coarse_id, coarse_plan["inventory"]["out_of_window_ids"])

        reserved = base_payload()
        initial = build_update_plan(reserved)
        reserved["assignments"] = [{
            "paper_id": initial["inventory"]["new_ids"][0],
            "primary_cluster_id": "con",
            "secondary_cluster_ids": [],
            "routing_confidence": "high",
            "routing_note": "Reserved-name regression fixture.",
        }]
        with self.assertRaisesRegex(ValueError, "reserved Windows"):
            build_update_plan(reserved)

    def test_unicode_version_match_does_not_collapse_to_empty(self) -> None:
        payload = routed_payload(mixed_full_text=True)
        payload["papers"][2]["title"] = "最低工资与企业培训"
        payload["papers"][2]["authors"] = "张三"
        check = payload["clusters"][0]["full_text_checks"][0]
        check["version_title"] = "教师工资与学生成绩"
        check["version_authors"] = "李四"
        payload["plan_hash"] = build_update_plan(payload)["plan_hash"]
        payload.pop("materialization_hash")
        with self.assertRaisesRegex(ValueError, "title/author match"):
            build_frontier_state(payload)

    def test_title_author_match_requires_nonempty_authors(self) -> None:
        payload = routed_payload(mixed_full_text=True)
        payload["papers"][2]["authors"] = ""
        check = payload["clusters"][0]["full_text_checks"][0]
        check["version_authors"] = ""
        check["version_title"] = payload["papers"][2]["title"]
        payload["plan_hash"] = build_update_plan(payload)["plan_hash"]
        payload.pop("materialization_hash")
        with self.assertRaisesRegex(ValueError, "title/author match"):
            build_frontier_state(payload)

    def test_live_cluster_cannot_be_silently_superseded(self) -> None:
        payload = routed_payload()
        payload["clusters"][0]["status"] = "superseded"
        payload["clusters"][0]["current_consensus"] = []
        payload.pop("materialization_hash")
        with self.assertRaisesRegex(ValueError, "live papers cannot be superseded"):
            build_frontier_state(payload)

    def test_materializer_rejects_reused_committed_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "frontiers" / "economics"
            payload = routed_payload()
            _materialize(payload, root, require_materialization_hash=False)
            with self.assertRaisesRegex(ValueError, "already committed"):
                _materialize(payload, root, require_materialization_hash=False)

    def test_materializer_requires_validated_hash_and_exclusive_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "frontiers" / "economics"
            payload = routed_payload()
            payload.pop("materialization_hash")
            with self.assertRaisesRegex(ValueError, "hash returned by validate"):
                _materialize(payload, root)

            with _state_lock(root):
                with self.assertRaisesRegex(ValueError, "holds the state lock"):
                    _materialize(routed_payload(), root)

    def test_materializer_lock_releases_after_owner_exits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "frontiers" / "economics"
            with _state_lock(root):
                pass
            result = _materialize(routed_payload(), root)
            self.assertEqual(result["run_id"], "frontier-20260817-test")

    def test_materializer_recovers_orphan_artifacts_after_state_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "frontiers" / "economics"
            payload = routed_payload()
            original = frontier_review_module._atomic_write

            def fail_state(path: Path, data: bytes, *, allowed_root: Path) -> None:
                if path.name == "state.json":
                    raise OSError("synthetic state-write failure")
                original(path, data, allowed_root=allowed_root)

            with mock.patch.object(frontier_review_module, "_atomic_write", fail_state):
                with self.assertRaisesRegex(OSError, "synthetic"):
                    _materialize(payload, root)
            self.assertFalse((root / "state.json").exists())
            self.assertTrue(
                (root / "runs" / payload["run_id"] / "manifest.json").exists()
            )

            recovered = _materialize(payload, root)
            self.assertEqual(recovered["run_id"], payload["run_id"])
            state = json.loads((root / "state.json").read_text(encoding="utf-8"))
            self.assertIn(payload["run_id"], state["committed_run_ids"])

    def test_cluster_projection_preserves_human_notes(self) -> None:
        state, _ = build_frontier_state(routed_payload())
        cluster = state["clusters"]["teacher-labor-markets"]
        text = render_cluster_note(
            cluster,
            state["papers"],
            human_notes="My note: distinguish urban and rural systems.",
        )
        self.assertEqual(
            extract_human_notes(text),
            "My note: distinguish urban and rural systems.",
        )
        self.assertIn("No source-supported disagreement", render_cluster_note({
            **cluster,
            "disagreements": [],
        }, state["papers"]))
        provisional = {
            **state,
            "clusters": {
                "teacher-labor-markets": {**cluster, "status": "provisional"}
            },
        }
        self.assertIn("teacher-labor-markets", render_index(provisional))

    def test_cli_materializer_writes_complete_obsidian_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "frontiers" / "economics"
            result = _materialize(routed_payload(), root)
            self.assertTrue((root / "state.json").exists())
            self.assertTrue((root / "index.md").exists())
            self.assertTrue((root / "clusters" / "teacher-labor-markets.md").exists())
            self.assertTrue((root / "runs" / result["run_id"] / "manifest.json").exists())
            self.assertTrue((root / "runs" / result["run_id"] / "plan.json").exists())
            self.assertTrue((root / "runs" / result["run_id"] / "report.md").exists())
            self.assertEqual(len(list((root / "papers").glob("*.md"))), 4)


if __name__ == "__main__":
    unittest.main()
