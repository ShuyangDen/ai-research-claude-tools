from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from research_workbench.app import create_app
from research_workbench.codex_app_server import CodexUnavailable
from research_workbench.codex_task_queue import FakeCodexTaskQueue
from research_workbench.models import current_iso_week


def test_url_safe_paper_id_preserves_slashes(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    app = create_app(settings, codex=codex)
    app.state.service.get_paper = lambda paper_id, week=None: {"paper_id": paper_id, "week": week}
    paper_id = "doi:10.1234/example/path"
    encoded = base64.urlsafe_b64encode(paper_id.encode()).decode().rstrip("=")
    with TestClient(app) as client:
        response = client.get(f"/api/papers/~{encoded}?week=2026-W36")
        assert response.status_code == 200
        assert response.json() == {"paper_id": paper_id, "week": "2026-W36"}


def test_api_requires_csrf_and_exposes_core_read_models(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    app = create_app(settings, codex=codex)
    with TestClient(app) as client:
        bootstrap = client.get("/api/bootstrap")
        assert bootstrap.status_code == 200
        assert bootstrap.json()["frontend_version"] == "0.3.0"
        assert bootstrap.headers["cache-control"] == "no-store"
        token = bootstrap.json()["csrf_token"]
        dashboard = client.get(f"/api/dashboard?week={current_iso_week()}")
        assert dashboard.status_code == 200
        assert dashboard.json()["top5"] == []
        rejected = client.post(
            f"/api/papers/paper%3A1/actions?week={current_iso_week()}", json={"action": "backlog"}
        )
        assert rejected.status_code == 403
        accepted = client.post(
            f"/api/papers/paper%3A1/actions?week={current_iso_week()}",
            json={"action": "backlog"},
            headers={"X-Workbench-CSRF": token},
        )
        assert accepted.status_code == 200
        plan = client.get(f"/api/plans/{current_iso_week()}").json()
        plan["tasks"] = [{
            "task_id": "manual-check", "category": "other", "title": "Check abstract gate",
            "related_id": "", "priority": 2, "due_date": "", "completed": False,
        }]
        confirmed = client.post(
            f"/api/plans/{current_iso_week()}", json=plan, headers={"X-Workbench-CSRF": token}
        )
        assert confirmed.status_code == 200
        plan["tasks"][0]["completed"] = True
        updated = client.patch(
            f"/api/plans/{current_iso_week()}",
            json={"tasks": plan["tasks"]},
            headers={"X-Workbench-CSRF": token},
        )
        assert updated.status_code == 200
        assert updated.json()["tasks"][0]["completed"] is True
        projects = client.get("/api/projects")
        assert projects.status_code == 200
        assert projects.json()[0]["slug"] == "welfare"
        created_project = client.post(
            "/api/projects",
            json={
                "slug": "major", "title": "Major", "project_path": str(settings.repo_root),
                "status": "active", "stage": "data collection", "summary": "Main idea exists.",
                "current_focus": "Collecting data.",
            },
            headers={"X-Workbench-CSRF": token},
        )
        assert created_project.status_code == 200
        assert created_project.json()["current_focus"] == "Collecting data."
        workspace = client.get("/api/projects/welfare/workspace")
        assert workspace.status_code == 200
        assert workspace.json()["workspace"]["sections"][0]["section_id"] == "this-week"
        modules = client.get("/api/project-modules")
        assert modules.status_code == 200
        assert any(item["module_id"] == "evidence-to-figure" for item in modules.json())
        note = client.post(
            "/api/projects/welfare/notes",
            json={"text": "把本周老板指令拆成任务。", "ask_codex": False},
            headers={"X-Workbench-CSRF": token},
        )
        assert note.status_code == 200
        assert note.json()["workspace"]["notes"][-1]["text"] == "把本周老板指令拆成任务。"
        cluster_id = dashboard.json()["clusters"][0]["cluster_id"]
        cluster = client.patch(
            f"/api/clusters/{current_iso_week()}/{cluster_id}",
            json={"status": "confirmed"},
            headers={"X-Workbench-CSRF": token},
        )
        assert cluster.status_code == 200
        assert cluster.json()["status"] == "confirmed"

        sync_overview = client.get("/api/sync")
        assert sync_overview.status_code == 200
        assert str(settings.repo_root) not in sync_overview.text
        sync_without_csrf = client.post("/api/sync", json={"mode": "sync", "repository_ids": []})
        assert sync_without_csrf.status_code == 403
        unknown_repository = client.post(
            "/api/sync",
            json={"mode": "sync", "repository_ids": ["not-an-allowlisted-id"]},
            headers={"X-Workbench-CSRF": token},
        )
        assert unknown_repository.status_code == 400


def test_pdf_upload_and_loopback_host_guard(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    app = create_app(settings, codex=codex)
    with TestClient(app) as client:
        token = client.get("/api/bootstrap").json()["csrf_token"]
        response = client.post(
            "/api/papers/paper%3A1/pdf",
            files={"file": ("paper.pdf", b"%PDF-1.7\nfixture", "application/pdf")},
            headers={"X-Workbench-CSRF": token},
        )
        assert response.status_code == 200
        fetched = client.get("/api/papers/paper%3A1/pdf")
        assert fetched.status_code == 200
        assert fetched.content.startswith(b"%PDF")
        forbidden = client.get("/api/health", headers={"host": "192.168.1.50"})
        assert forbidden.status_code == 403


def test_codex_protocol_error_is_exposed_as_service_unavailable(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    app = create_app(settings, codex=codex)

    async def fail_message(_: str, __: str):
        raise CodexUnavailable("App Server thread/start failed: protocol mismatch")

    app.state.service.message_session = fail_message
    with TestClient(app) as client:
        token = client.get("/api/bootstrap").json()["csrf_token"]
        response = client.post(
            "/api/sessions/example/messages",
            json={"message": "hello"},
            headers={"X-Workbench-CSRF": token},
        )
        assert response.status_code == 503
        assert response.json() == {"detail": "App Server thread/start failed: protocol mismatch"}


def test_reading_action_queues_trevor_handoff_without_web_chat(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    reading_queue = FakeCodexTaskQueue()
    app = create_app(settings, codex=codex, reading_queue=reading_queue)
    with TestClient(app) as client:
        token = client.get("/api/bootstrap").json()["csrf_token"]
        response = client.post(
            f"/api/papers/paper%3A1/actions?week={current_iso_week()}",
            json={"action": "deep"},
            headers={"X-Workbench-CSRF": token},
        )
        assert response.status_code == 200
        session = response.json()["session"]
        assert session["handoff_status"] == "queued"
        assert session["handoff_target"] == "论文阅读 · Trevor"
        assert "WORKBENCH_CODEX_HANDOFF_V1" in reading_queue.messages[0]
