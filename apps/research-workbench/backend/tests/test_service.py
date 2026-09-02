from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from research_workbench.models import PaperActionRequest, ProjectModuleCreateRequest, ProjectNoteRequest, ProjectUpsertRequest, current_iso_week
from research_workbench.codex_task_queue import CodexTaskNotFoundError, FakeCodexTaskQueue
from research_workbench.service import WorkbenchService


def test_dashboard_builds_top5_plan_clusters_and_ideas(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    service = WorkbenchService(settings, codex)
    dashboard = service.dashboard(current_iso_week())
    assert dashboard.top5 == []
    assert dashboard.plan.tasks == []
    assert dashboard.plan.capacity == {"deep": 1, "targeted": 2}
    assert dashboard.ideas[0]["title"] == "Teacher-AI Complementarity"
    assert dashboard.clusters
    assert dashboard.slate.ranking_version == 0


def test_projects_use_the_projects_vault_and_support_add_update(workbench_fixture, tmp_path: Path) -> None:
    settings, codex = workbench_fixture
    service = WorkbenchService(settings, codex)
    assert service.projects()[0].current_focus == "health channel"
    major_root = tmp_path / "major"
    major_root.mkdir()
    created = service.save_project(ProjectUpsertRequest(
        slug="major", title="Major", project_path=str(major_root), status="active",
        stage="data collection", summary="Main idea is defined.", current_focus="Collecting catalog data.",
    ))
    assert created.slug == "major"
    assert (settings.projects_vault / "major" / "snapshot.json").exists()
    updated = service.save_project(ProjectUpsertRequest(
        slug="welfare", title="Welfare", project_path=str(settings.repo_root), status="active",
        stage="draft complete", summary="Draft paper exists.", current_focus="Extending the health channel.",
    ), existing_slug="welfare")
    assert updated.current_focus == "Extending the health channel."
    assert "| major | Major |" in (settings.projects_vault / "index.md").read_text(encoding="utf-8")


def test_projects_use_machine_specific_path_overrides(workbench_fixture, tmp_path: Path) -> None:
    settings, codex = workbench_fixture
    local_welfare = tmp_path / "local-welfare"
    local_welfare.mkdir()
    overridden = dataclasses.replace(settings, project_paths={"welfare": local_welfare})

    project = WorkbenchService(overridden, codex).projects()[0]

    assert project.slug == "welfare"
    assert project.project_path == str(local_welfare)


@pytest.mark.asyncio
async def test_project_notebook_modules_and_welfare_current_week(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    service = WorkbenchService(settings, codex)
    view = service.project_workspace("welfare")
    assert view.workspace.sections[0].section_id == "this-week"
    assert "A×B" in view.workspace.sections[0].summary
    assert view.workspace.notes
    codex.responses.appendleft(json.dumps({"reply": "已拆成任务。", "workspace": None}))
    updated = await service.add_project_note("welfare", ProjectNoteRequest(text="老板让我先比较两种图形方案。"))
    assert any("两种图形" in note.text for note in updated.workspace.notes)
    created = service.create_project_module("welfare", ProjectModuleCreateRequest(section_id="this-week"))
    assert created.module_id.startswith("custom-this-week-")
    applied = service.apply_project_module("welfare", "evidence-to-figure")
    assert applied.workspace.sections[0].kind == "evidence-to-figure"
    codex.responses.appendleft(json.dumps({"reply": "图片已读取。", "workspace": None}))
    image_view = await service.add_project_image("welfare", b"\x89PNG\r\n\x1a\nfixture", "scratch.png")
    assert image_view.workspace.notes[-1].source_type == "image"
    stored_workspace = json.loads((settings.projects_vault / "welfare" / "workspace.json").read_text(encoding="utf-8"))
    assert stored_workspace["notes"][-1]["asset_path"].startswith("{WORKBENCH_STATE_ROOT}/")


@pytest.mark.asyncio
async def test_reading_action_sidecar_and_rolling_refill_do_not_change_plan(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    reading_queue = FakeCodexTaskQueue()
    service = WorkbenchService(settings, codex, reading_queue=reading_queue)
    week = current_iso_week()
    codex.responses.appendleft(json.dumps({"entries": [
        {"paper_id": f"paper:{index}", "rank": index, "private_reason": "fit",
         "public_reason": f"摘要说明论文 {index} 使用随机设计并报告学习结果。", "score": 100 - index}
        for index in range(1, 8)
    ]}))
    await service.rank_week(week)
    plan = service.get_plan(week)
    plan.status = "confirmed"
    service.save_plan(plan)
    deep = await service.act_on_paper("paper:1", PaperActionRequest(action="deep"), week)
    assert deep["session"].read_depth == "deep"
    current_session = service.get_session(deep["session"].session_id)
    assert current_session.agent_name == "Trevor"
    assert current_session.workflow_version == 4
    assert current_session.source_scope == "abstract"
    assert current_session.handoff_status == "queued"
    assert current_session.handoff_target == "论文阅读 · Trevor"
    assert current_session.handoff_message_id == "queued-1"
    assert "WORKBENCH_CODEX_HANDOFF_V1" in reading_queue.messages[-1]
    assert "$paper-reading-tutor" in reading_queue.messages[-1]
    assert "lawful/open copy" in reading_queue.messages[-1]
    assert "MarkItDown" in reading_queue.messages[-1]
    assert "Never treat the abstract as the paper" in reading_queue.messages[-1]
    assert ":" not in deep["session"].session_id
    assert deep["session"].codex_thread_id == "论文阅读 · Trevor"
    restarted = WorkbenchService(settings, codex, reading_queue=reading_queue)
    assert restarted.get_session(deep["session"].session_id).codex_thread_id == deep["session"].codex_thread_id
    skipped = await service.act_on_paper("paper:2", PaperActionRequest(action="skip"), week)
    assert skipped["session"].handoff_decision == "skip"
    assert "what specifically made the paper uninteresting" in reading_queue.messages[-1]
    assert "$record-reading-feedback" in reading_queue.messages[-1]
    assert "$sync-reading-queue" in reading_queue.messages[-1]
    assert next(item for item in service.load_queue() if item["paper_id"] == "paper:2")["status"] == "queued"
    saved_plan = service.get_plan(week)
    assert saved_plan.status == "confirmed"
    assert [task.task_id for task in saved_plan.tasks] == [task.task_id for task in plan.tasks]


@pytest.mark.asyncio
async def test_targeted_read_queues_visible_codex_task_without_using_app_server(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    reading_queue = FakeCodexTaskQueue("论文阅读 · Trevor")
    service = WorkbenchService(settings, codex, reading_queue=reading_queue)
    created = await service.act_on_paper("paper:1", PaperActionRequest(action="targeted"), current_iso_week())
    assert created["session"].read_depth == "targeted"
    assert created["session"].handoff_status == "queued"
    assert "first confirm the exact section or question" in reading_queue.messages[0]
    assert codex.prompts == []


@pytest.mark.asyncio
async def test_first_reading_handoff_creates_named_codex_task_automatically(workbench_fixture) -> None:
    settings, codex = workbench_fixture

    class MissingReadingTask(FakeCodexTaskQueue):
        def enqueue(self, message: str):  # type: ignore[no-untyped-def]
            raise CodexTaskNotFoundError("No active session found matching '论文阅读 · Trevor'.")

    service = WorkbenchService(settings, codex, reading_queue=MissingReadingTask())
    result = await service.act_on_paper(
        "paper:1", PaperActionRequest(action="deep"), current_iso_week()
    )

    assert result["session"].handoff_status == "queued"
    assert result["session"].handoff_target == "论文阅读 · Trevor"
    assert result["session"].codex_thread_id == "thr_named_1"
    assert codex.named_prompts[0][0] == "论文阅读 · Trevor"
    assert codex.named_prompts[0][2] == settings.ai_education_root.resolve()
    queue_record = next(item for item in service.load_queue() if item["paper_id"] == "paper:1")
    assert queue_record["status"] == "in_progress"
    assert queue_record["user_updated_at"]


@pytest.mark.asyncio
async def test_codex_ranking_requires_every_complete_abstract(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    codex.responses.appendleft(json.dumps({
        "entries": [
            {"paper_id": "paper:3", "rank": 1, "private_reason": "fit", "public_reason": "Strong design", "score": 99},
            {"paper_id": "paper:1", "rank": 2, "private_reason": "fit", "public_reason": "Core question", "score": 98},
        ]
    }))
    service = WorkbenchService(settings, codex)
    with pytest.raises(ValueError, match="did not evaluate every complete abstract"):
        await service.rank_week(current_iso_week())


@pytest.mark.asyncio
async def test_codex_ranking_reads_full_abstracts_and_creates_no_fallback(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    pool_path = next((settings.tracker_root / "archives" / current_iso_week()).glob("*/candidate_pool.json"))
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    pool["papers"][0]["abstract"] = " ".join(["complete evidence"] * 160) + " ABSTRACT-END-MARKER"
    pool_path.write_text(json.dumps(pool), encoding="utf-8")
    codex.responses.appendleft(json.dumps({"entries": [
        {"paper_id": f"paper:{index}", "rank": index, "private_reason": "fit",
         "public_reason": f"摘要说明论文 {index} 使用随机设计并报告学习结果。", "score": 100 - index}
        for index in range(1, 8)
    ]}))
    service = WorkbenchService(settings, codex)
    slate = await service.rank_week(current_iso_week())
    assert slate.generated_by == "codex-app-server"
    assert slate.ranking_version == 3
    assert slate.codex_thread_id
    assert len(slate.entries) == 7
    assert [entry.rank for entry in slate.entries] == list(range(1, 8))
    assert slate.current_top5 == [f"paper:{index}" for index in range(1, 6)]
    assert "ABSTRACT-END-MARKER" in codex.prompts[-1]
    migration = service.migration_status()
    assert migration["weeks"][0]["codex_success"] is True
    assert migration["weeks"][0]["top5_overlap"] == 5


@pytest.mark.asyncio
async def test_ranked_pool_and_paths_are_portable_across_machine_roots(workbench_fixture, tmp_path: Path) -> None:
    settings, codex = workbench_fixture
    codex.responses.appendleft(json.dumps({"entries": [
        {"paper_id": f"paper:{index}", "rank": index, "private_reason": "private fit",
         "public_reason": f"摘要证据 {index}", "score": 100 - index}
        for index in range(1, 8)
    ]}))
    first = WorkbenchService(settings, codex)
    ranked = await first.rank_week(current_iso_week())
    session = first.bind_pdf("paper:1", b"%PDF-1.7\nfixture")
    stored_session = json.loads((settings.workbench_root / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert stored_session["pdf_path"].startswith("{PAPER_TRACKER_ROOT}/")
    assert (settings.workbench_root / "weeks" / current_iso_week() / "pool.json").exists()

    second_tracker = tmp_path / "different-drive" / "tracker"
    second_tracker.mkdir(parents=True)
    (second_tracker / "queue_state.jsonl").write_text("", encoding="utf-8")
    second_settings = dataclasses.replace(settings, tracker_root=second_tracker)
    second = WorkbenchService(second_settings, codex)
    restored_pool = second.load_pool(current_iso_week())
    restored_slate = second.ensure_slate(current_iso_week())
    restored_session = second.get_session(session.session_id)
    assert len(restored_pool.papers) == 7
    assert all(paper.abstract_ready for paper in restored_pool.papers)
    assert restored_slate.current_top5 == ranked.current_top5
    assert restored_slate.entries[0].private_reason == "private fit"
    assert Path(restored_session.pdf_path).is_relative_to(second_tracker)


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
