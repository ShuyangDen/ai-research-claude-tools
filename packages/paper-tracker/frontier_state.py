"""Validated state transitions for incremental economics frontier reviews."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Mapping

from frontier_core import (
    SCHEMA_VERSION,
    _validate_previous_state,
    build_update_plan,
)
from frontier_tokens import estimate_tokens
from frontier_validation import validate_cluster_synthesis
from scout_core import stable_json_hash


def build_frontier_state(
    payload: Mapping[str, Any],
    previous_state: Mapping[str, Any] | None = None,
    *,
    require_materialization_hash: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate a synthesized run and return durable state plus an audit manifest."""

    previous = _validate_previous_state(previous_state)
    plan = build_update_plan(payload, previous)
    committed_history = list(dict.fromkeys(
        str(item) for item in previous.get("committed_run_ids", [])
    ))
    if previous.get("last_run_id") and str(previous["last_run_id"]) not in committed_history:
        committed_history.append(str(previous["last_run_id"]))
    committed_run_ids = set(committed_history)
    if plan["run_id"] in committed_run_ids:
        raise ValueError(f"Frontier run_id is already committed: {plan['run_id']}")
    if not payload.get("plan_hash"):
        raise ValueError("Frontier materialization requires the recorded plan_hash")
    if str(payload.get("plan_hash")) != plan["plan_hash"]:
        raise ValueError("Frontier materialization plan_hash does not match current inputs")
    routed_ids = set(plan["inventory"]["new_ids"]) | set(
        plan["inventory"]["changed_ids"]
    ) | set(plan["inventory"]["reconcile_sample_ids"])
    assigned_ids = {item["paper_id"] for item in plan["assignments"]}
    if assigned_ids != routed_ids:
        missing = sorted(routed_ids - assigned_ids)
        extra = sorted(assigned_ids - routed_ids)
        raise ValueError(
            "Frontier assignments must exactly match routed papers; "
            f"missing={missing}, extra={extra}"
        )
    known_papers = {
        paper_id: dict(row)
        for paper_id, row in dict(previous.get("papers", {})).items()
        if isinstance(row, Mapping)
    }
    known_papers.update({row["paper_id"]: row for row in plan["papers"]})
    syntheses = [
        validate_cluster_synthesis(
            item,
            known_papers,
            full_text_cap=plan["budget"]["targeted_full_text_per_cluster"],
            synthesis_token_cap=plan["budget"]["worker_packet_tokens"],
        )
        for item in payload.get("clusters", [])
    ]
    if plan["worker_packets"] and not syntheses:
        raise ValueError("Frontier materialization needs cluster syntheses for worker packets")
    by_cluster = {item["cluster_id"]: item for item in syntheses}
    if len(by_cluster) != len(syntheses):
        raise ValueError("Frontier materialization has duplicate cluster IDs")
    required_clusters = {item["cluster_id"] for item in plan["worker_packets"]}
    missing_clusters = sorted(required_clusters - set(by_cluster))
    extra_clusters = sorted(set(by_cluster) - required_clusters)
    if missing_clusters or extra_clusters:
        raise ValueError(
            "Frontier syntheses must exactly match planned worker clusters; "
            f"missing={missing_clusters}, extra={extra_clusters}"
        )
    expected_memberships: dict[str, set[str]] = {
        cluster_id: set(row.get("paper_ids", []))
        for cluster_id, row in dict(previous.get("clusters", {})).items()
        if isinstance(row, Mapping)
    }
    expired_ids = set(plan["inventory"]["expired_previous_ids"])
    for paper_id in expired_ids:
        for members in expected_memberships.values():
            members.discard(paper_id)
    for assignment in plan["assignments"]:
        paper_id = assignment["paper_id"]
        old = previous.get("papers", {}).get(paper_id, {})
        old_memberships = {
            value
            for value in (
                old.get("primary_cluster_id") if isinstance(old, Mapping) else None,
                *((old.get("secondary_cluster_ids", []) or []) if isinstance(old, Mapping) else []),
            )
            if value
        }
        new_memberships = {
            assignment["primary_cluster_id"],
            *assignment["secondary_cluster_ids"],
        }
        for cluster_id in old_memberships - new_memberships:
            expected_memberships.setdefault(str(cluster_id), set()).discard(paper_id)
        for cluster_id in new_memberships:
            expected_memberships.setdefault(str(cluster_id), set()).add(paper_id)
            cluster = by_cluster.get(str(cluster_id))
            if cluster is None or paper_id not in cluster["paper_ids"]:
                raise ValueError(
                    "Frontier synthesis omits an assigned cluster membership: "
                    f"{paper_id} -> {cluster_id}"
                )
    for cluster_id in required_clusters:
        expected = expected_memberships.get(cluster_id, set())
        actual = set(by_cluster[cluster_id]["paper_ids"])
        if actual != expected:
            raise ValueError(
                "Frontier synthesis paper membership differs from the planned transition: "
                f"{cluster_id}; missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}"
            )
        if not actual and by_cluster[cluster_id]["status"] != "superseded":
            raise ValueError(
                f"Frontier empty cluster must be marked superseded: {cluster_id}"
            )
        if actual and by_cluster[cluster_id]["status"] == "superseded":
            raise ValueError(
                f"Frontier cluster with live papers cannot be superseded: {cluster_id}"
            )

    materialization_hash = stable_json_hash({
        "plan_hash": plan["plan_hash"],
        "clusters": syntheses,
    })
    supplied_materialization_hash = str(payload.get("materialization_hash", "") or "")
    if require_materialization_hash and not supplied_materialization_hash:
        raise ValueError(
            "Frontier materialization requires the hash returned by validate"
        )
    if supplied_materialization_hash and supplied_materialization_hash != materialization_hash:
        raise ValueError("Frontier materialization_hash does not match validated synthesis")
    full_text_input_tokens = sum(
        check["evidence_input_tokens"]
        for synthesis in syntheses
        for check in synthesis["full_text_checks"]
    )
    synthesis_output_tokens = estimate_tokens(
        json.dumps(syntheses, ensure_ascii=False, sort_keys=True)
    )
    estimated_total_tokens = (
        plan["estimated_input_tokens"]
        + plan.get("reserved_partial_output_tokens", 0)
        + full_text_input_tokens
        + synthesis_output_tokens
    )
    if estimated_total_tokens > plan["budget"]["run_input_token_ceiling"]:
        raise ValueError(
            "Frontier validated run exceeds the selected total token ceiling: "
            f"{estimated_total_tokens} > {plan['budget']['run_input_token_ceiling']}"
        )

    run_time = plan["created_at"]
    papers = {
        paper_id: dict(row)
        for paper_id, row in dict(previous.get("papers", {})).items()
        if isinstance(row, Mapping)
    }
    for paper_id in expired_ids:
        if paper_id not in papers:
            continue
        old_primary = papers[paper_id].get("primary_cluster_id")
        old_secondary = list(papers[paper_id].get("secondary_cluster_ids", []) or [])
        papers[paper_id] = {
            **papers[paper_id],
            "frontier_status": "out_of_window",
            "expired_at": run_time,
            "former_primary_cluster_id": old_primary,
            "former_secondary_cluster_ids": old_secondary,
            "primary_cluster_id": None,
            "secondary_cluster_ids": [],
        }
    assignment_by_id = {item["paper_id"]: item for item in plan["assignments"]}
    evidence_downgraded = set(plan["inventory"]["evidence_downgraded_ids"])
    for row in plan["papers"]:
        paper_id = row["paper_id"]
        old = papers.get(paper_id, {})
        assignment = assignment_by_id.get(paper_id, {})
        if paper_id in evidence_downgraded and old:
            durable_row = {
                **old,
                "latest_retrieval_evidence_level": row.get("evidence_level"),
                "latest_retrieval_fingerprint": row.get("fingerprint"),
                "evidence_downgrade_at": run_time,
            }
        else:
            durable_row = row
        papers[paper_id] = {
            **durable_row,
            "frontier_status": "active",
            "first_seen_at": old.get("first_seen_at", run_time),
            "last_seen_at": run_time,
            "primary_cluster_id": assignment.get(
                "primary_cluster_id", old.get("primary_cluster_id")
            ),
            "secondary_cluster_ids": assignment.get(
                "secondary_cluster_ids", old.get("secondary_cluster_ids", [])
            ),
        }

    clusters = {
        cluster_id: dict(row)
        for cluster_id, row in dict(previous.get("clusters", {})).items()
        if isinstance(row, Mapping)
    }
    updated_cluster_ids: list[str] = []
    for synthesis in syntheses:
        cluster_id = synthesis["cluster_id"]
        old = clusters.get(cluster_id, {})
        input_hash = stable_json_hash({
            paper_id: papers[paper_id]["fingerprint"]
            for paper_id in synthesis["paper_ids"]
        })
        row = {
            **synthesis,
            "first_seen_at": old.get("first_seen_at", run_time),
            "last_updated_at": run_time,
            "synthesis_input_hash": input_hash,
        }
        cluster_papers = [papers[paper_id] for paper_id in synthesis["paper_ids"]]
        row["source_breadth"] = len({
            str(paper.get("source_family", "")).casefold()
            for paper in cluster_papers
            if paper.get("source_family")
        })
        row["tier_weighted_attention"] = round(sum(
            float(paper.get("journal_rank_weight", 0.0) or 0.0)
            for paper in cluster_papers
        ), 4)
        evidence_levels: dict[str, int] = defaultdict(int)
        for paper in cluster_papers:
            evidence_levels[str(paper.get("evidence_level", "metadata"))] += 1
        row["evidence_levels"] = dict(sorted(evidence_levels.items()))
        row["synthesis_hash"] = stable_json_hash(row)
        clusters[cluster_id] = row
        updated_cluster_ids.append(cluster_id)

    reconciled = bool(plan["inventory"]["reconcile_sample_ids"])
    last_reconciled_at = previous.get("last_reconciled_at")
    if not previous or reconciled:
        last_reconciled_at = run_time
    full_text_checks = [
        {**check, "cluster_id": synthesis["cluster_id"]}
        for synthesis in syntheses
        for check in synthesis["full_text_checks"]
    ]
    last_run_summary = {
        "run_id": plan["run_id"],
        "source_health": plan["source_health"],
        "inventory": plan["inventory"],
        "estimated_input_tokens": plan["estimated_input_tokens"],
        "reserved_partial_output_tokens": plan.get(
            "reserved_partial_output_tokens", 0
        ),
        "full_text_input_tokens": full_text_input_tokens,
        "synthesis_output_tokens": synthesis_output_tokens,
        "estimated_total_tokens": estimated_total_tokens,
        "full_text_check_count": len(full_text_checks),
    }
    state = {
        "schema_version": SCHEMA_VERSION,
        "scope": plan["scope"],
        "window_months": plan["window_months"],
        "created_at": previous.get("created_at", run_time),
        "updated_at": run_time,
        "last_reconciled_at": last_reconciled_at,
        "last_run_id": plan["run_id"],
        "committed_run_ids": [
            *committed_history,
            plan["run_id"],
        ],
        "run_count": int(previous.get("run_count", 0)) + 1,
        "last_run_summary": last_run_summary,
        "papers": dict(sorted(papers.items())),
        "clusters": dict(sorted(clusters.items())),
    }
    state["state_hash"] = stable_json_hash(state)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": plan["run_id"],
        "created_at": run_time,
        "scope": plan["scope"],
        "window_months": plan["window_months"],
        "token_mode": plan["token_mode"],
        "budget": plan["budget"],
        "queries": plan["queries"],
        "source_health": plan["source_health"],
        "plan_hash": plan["plan_hash"],
        "materialization_hash": materialization_hash,
        "estimated_input_tokens": plan["estimated_input_tokens"],
        "reserved_partial_output_tokens": plan.get(
            "reserved_partial_output_tokens", 0
        ),
        "full_text_input_tokens": full_text_input_tokens,
        "synthesis_output_tokens": synthesis_output_tokens,
        "estimated_total_tokens": estimated_total_tokens,
        "inventory": plan["inventory"],
        "assignments": plan["assignments"],
        "updated_cluster_ids": updated_cluster_ids,
        "full_text_checks": full_text_checks,
        "full_text_check_count": len(full_text_checks),
        "state_hash": state["state_hash"],
    }
    manifest["manifest_hash"] = stable_json_hash(manifest)
    return state, manifest
