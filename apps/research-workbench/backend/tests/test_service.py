from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from research_workbench.models import PaperActionRequest, ProjectModuleCreateRequest, ProjectNoteRequest, ProjectUpsertRequest, current_iso_week
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


@pytest.mark.asyncio
async def test_reading_action_sidecar_and_rolling_refill_do_not_change_plan(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    service = WorkbenchService(settings, codex)
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
    skill_path = settings.repo_root / "packages" / "codex" / "skills" / "paper-reading-tutor" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# test Trevor skill", encoding="utf-8")
    codex.responses.appendleft(
        "【当前阶段】阶段 0 · 摘要导读\n【研究问题】AI 如何改变学习？\n【只问一个问题】你选择精读还是定向粗读？"
    )
    deep = await service.act_on_paper("paper:1", PaperActionRequest(action="deep"), week)
    for _ in range(10):
        await asyncio.sleep(0)
        if service.get_session(deep["session"].session_id).messages:
            break
    assert deep["session"].read_depth == "deep"
    current_session = service.get_session(deep["session"].session_id)
    assert current_session.agent_name == "Trevor"
    assert current_session.workflow_version == 3
    assert current_session.source_scope == "abstract"
    assert len(current_session.messages) == 1
    assert "【当前阶段】" in current_session.messages[0].text
    assert "not a generic summarizer" in codex.prompts[-1]
    assert "WORKBENCH_TREVOR_PREFLIGHT_V1" in codex.prompts[-1]
    assert codex.prompt_kwargs[-1]["cwd"] == settings.ai_education_root
    assert codex.prompt_kwargs[-1]["skill"] == ("paper-reading-tutor", skill_path)
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
async def test_reading_followup_reloads_trevor_skill_and_persists_whole_messages(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    skill_path = settings.repo_root / "packages" / "codex" / "skills" / "paper-reading-tutor" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# test Trevor skill", encoding="utf-8")
    service = WorkbenchService(settings, codex)
    codex.responses.appendleft("【当前阶段】阶段 0\n【只问一个问题】精读吗？")
    created = await service.act_on_paper("paper:1", PaperActionRequest(action="deep"), current_iso_week())
    for _ in range(10):
        await asyncio.sleep(0)
        if service.get_session(created["session"].session_id).messages:
            break
    codex.responses.appendleft("【当前阶段】阶段 1 · 数学必要性门槛\n【只问一个问题】先解释哪一个量？")
    updated = await service.message_session(created["session"].session_id, "继续精读")
    assert updated.phase == "phase-1"
    assert [message.role for message in updated.messages] == ["assistant", "user", "assistant"]
    assert updated.messages[1].text == "继续精读"
    assert "math-necessity gate" in codex.prompts[-1]
    assert "WORKBENCH_TREVOR_PREFLIGHT_V1" in codex.prompts[-1]
    assert codex.prompt_kwargs[-1]["cwd"] == settings.ai_education_root
    assert codex.prompt_kwargs[-1]["skill"] == ("paper-reading-tutor", skill_path)


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
