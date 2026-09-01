from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_workbench.models import PaperActionRequest, current_iso_week
from research_workbench.service import WorkbenchService


def test_dashboard_builds_top5_plan_clusters_and_ideas(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    service = WorkbenchService(settings, codex)
    dashboard = service.dashboard(current_iso_week())
    assert [paper.paper_id for paper in dashboard.top5] == [f"paper:{index}" for index in range(1, 6)]
    assert len(dashboard.plan.tasks) == 3
    assert dashboard.plan.capacity == {"deep": 1, "targeted": 2}
    assert dashboard.ideas[0]["title"] == "Teacher-AI Complementarity"
    assert dashboard.clusters


@pytest.mark.asyncio
async def test_reading_action_sidecar_and_rolling_refill_do_not_change_plan(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    service = WorkbenchService(settings, codex)
    week = current_iso_week()
    plan = service.get_plan(week)
    plan.status = "confirmed"
    service.save_plan(plan)
    deep = await service.act_on_paper("paper:1", PaperActionRequest(action="deep"), week)
    assert deep["session"].read_depth == "deep"
    assert ":" not in deep["session"].session_id
    assert deep["session"].codex_thread_id.startswith("thr_test_")
    restarted = WorkbenchService(settings, codex)
    assert restarted.get_session(deep["session"].session_id).codex_thread_id == deep["session"].codex_thread_id
    skipped = await service.act_on_paper("paper:2", PaperActionRequest(action="skip"), week)
    assert "paper:2" not in skipped["slate"].current_top5
    assert "paper:6" in skipped["slate"].current_top5
    saved_plan = service.get_plan(week)
    assert saved_plan.status == "confirmed"
    assert [task.task_id for task in saved_plan.tasks] == [task.task_id for task in plan.tasks]


@pytest.mark.asyncio
async def test_codex_ranking_keeps_missing_pool_items_as_fallback(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    codex.responses.appendleft(json.dumps({
        "entries": [
            {"paper_id": "paper:3", "rank": 1, "private_reason": "fit", "public_reason": "Strong design", "score": 99},
            {"paper_id": "paper:1", "rank": 2, "private_reason": "fit", "public_reason": "Core question", "score": 98},
        ]
    }))
    service = WorkbenchService(settings, codex)
    slate = await service.rank_week(current_iso_week())
    assert slate.generated_by == "codex-app-server"
    assert slate.codex_thread_id
    assert len(slate.entries) == 7
    assert slate.current_top5[:2] == ["paper:3", "paper:1"]
    migration = service.migration_status()
    assert migration["weeks"][0]["codex_success"] is True
    assert migration["weeks"][0]["top5_overlap"] == 5


@pytest.mark.asyncio
async def test_codex_cluster_and_plan_drafts_require_confirmation(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    codex.responses.extendleft(reversed([
        json.dumps({"clusters": [{
            "cluster_id": "teacher-ai", "question": "How does AI change teaching?", "mechanism": "feedback",
            "paper_ids": ["paper:1", "paper:2", "unknown"], "status": "proposed",
        }]}),
        json.dumps({
            "capacity": {"deep": 1, "targeted": 2},
            "tasks": [{
                "task_id": "deep-paper-1", "category": "deep", "title": "Read Paper 1", "related_id": "paper:1",
                "priority": 1, "due_date": "", "completed": False,
            }],
        }),
    ]))
    service = WorkbenchService(settings, codex)
    clusters = await service.propose_clusters(current_iso_week())
    assert clusters[0].paper_ids == ["paper:1", "paper:2"]
    plan = await service.draft_plan_codex(current_iso_week())
    assert plan.status == "draft"
    assert plan.tasks[0].related_id == "paper:1"


def test_pdf_binding_is_scoped_and_validated(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    service = WorkbenchService(settings, codex)
    with pytest.raises(ValueError):
        service.bind_pdf("paper:1", b"not a pdf")
    session = service.bind_pdf("paper:1", b"%PDF-1.7\nfixture")
    path = Path(session.pdf_path)
    assert path.is_relative_to(settings.tracker_root)
    assert service.pdf_path("paper:1") == path.resolve()
