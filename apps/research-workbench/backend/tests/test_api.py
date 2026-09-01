from __future__ import annotations

from fastapi.testclient import TestClient

from research_workbench.app import create_app
from research_workbench.models import current_iso_week


def test_api_requires_csrf_and_exposes_core_read_models(workbench_fixture) -> None:
    settings, codex = workbench_fixture
    app = create_app(settings, codex=codex)
    with TestClient(app) as client:
        bootstrap = client.get("/api/bootstrap")
        assert bootstrap.status_code == 200
        token = bootstrap.json()["csrf_token"]
        dashboard = client.get(f"/api/dashboard?week={current_iso_week()}")
        assert dashboard.status_code == 200
        assert len(dashboard.json()["top5"]) == 5
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
