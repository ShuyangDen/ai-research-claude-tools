from __future__ import annotations

import asyncio
import base64
import binascii
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .codex_app_server import CodexAppServer, CodexUnavailable
from .config import WorkbenchSettings, load_settings
from .models import (
    GitSyncRequest,
    PaperActionRequest,
    PlanPatch,
    ProjectItemPatch,
    ProjectMessageRequest,
    ProjectModuleApplyRequest,
    ProjectModuleCreateRequest,
    ProjectNoteRequest,
    ProjectUpsertRequest,
    WeeklyPlan,
    current_iso_week,
)
from .service import WorkbenchService


def _decode_paper_id(segment: str) -> str:
    """Decode frontend-safe paper IDs while retaining legacy route support."""
    if not segment.startswith("~"):
        return segment
    token = segment[1:]
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        paper_id = raw.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise HTTPException(400, "Invalid paper ID") from exc
    if not paper_id or len(paper_id) > 2048:
        raise HTTPException(400, "Invalid paper ID")
    return paper_id


def create_app(
    settings: WorkbenchSettings | None = None,
    *,
    codex: CodexAppServer | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings()
    service = WorkbenchService(resolved_settings, codex=codex)
    csrf_token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await service.codex.close()

    app = FastAPI(title="AI Research Workbench", version="0.1.1", lifespan=lifespan)
    app.state.service = service
    app.state.csrf_token = csrf_token

    @app.exception_handler(CodexUnavailable)
    async def codex_unavailable(_: Request, exc: CodexUnavailable) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=503)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-Workbench-CSRF"],
    )

    @app.middleware("http")
    async def local_security(request: Request, call_next):  # type: ignore[no-untyped-def]
        host = (request.headers.get("host") or "").split(":", 1)[0].casefold()
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse({"detail": "Research Workbench only accepts loopback requests."}, status_code=403)
        origin = request.headers.get("origin")
        if origin and origin not in resolved_settings.allowed_origins:
            return JSONResponse({"detail": "Origin is not allowed."}, status_code=403)
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            supplied = request.headers.get("x-workbench-csrf", "")
            if not secrets.compare_digest(supplied, csrf_token):
                return JSONResponse({"detail": "Missing or invalid CSRF token."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self' ws://127.0.0.1:* ws://localhost:*"
        )
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/bootstrap")
    def bootstrap() -> dict[str, Any]:
        return {
            "csrf_token": csrf_token,
            "week": current_iso_week(),
            "version": app.version,
            "frontend_version": "0.1.1",
            "features": ["top5", "plans", "reading", "ideas", "projects", "skills", "runs"],
        }

    @app.get("/api/dashboard")
    def dashboard(week: str | None = None):  # type: ignore[no-untyped-def]
        try:
            return service.dashboard(week)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/weeks/{week}/papers")
    def papers(
        week: str,
        status: str = "",
        lane: str = "",
        tier: str = "",
        cluster_id: str = "",
        q: str = "",
    ):  # type: ignore[no-untyped-def]
        try:
            return service.list_papers(week, status=status, lane=lane, tier=tier, cluster_id=cluster_id, q=q)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/papers/{paper_id}")
    def paper(paper_id: str, week: str | None = None):  # type: ignore[no-untyped-def]
        paper_id = _decode_paper_id(paper_id)
        try:
            return service.get_paper(paper_id, week)
        except KeyError as exc:
            raise HTTPException(404, "Paper not found") from exc

    @app.post("/api/papers/{paper_id}/abstract")
    async def refresh_paper_abstract(paper_id: str, week: str | None = None):  # type: ignore[no-untyped-def]
        paper_id = _decode_paper_id(paper_id)
        try:
            return await asyncio.to_thread(service.refresh_paper_abstract, paper_id, week)
        except KeyError as exc:
            raise HTTPException(404, "Paper not found") from exc

    @app.post("/api/papers/{paper_id}/actions")
    async def paper_action(paper_id: str, request: PaperActionRequest, week: str = Query(default_factory=current_iso_week)):
        paper_id = _decode_paper_id(paper_id)
        try:
            return await service.act_on_paper(paper_id, request, week)
        except KeyError as exc:
            raise HTTPException(404, "Paper not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/papers/{paper_id}/pdf")
    def paper_pdf(paper_id: str):  # type: ignore[no-untyped-def]
        paper_id = _decode_paper_id(paper_id)
        try:
            pdf_path = service.pdf_path(paper_id)
            return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)
        except KeyError as exc:
            raise HTTPException(404, "PDF not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/papers/{paper_id}/session")
    def paper_session(paper_id: str):  # type: ignore[no-untyped-def]
        paper_id = _decode_paper_id(paper_id)
        session = service.get_session_by_paper(paper_id)
        if not session:
            raise HTTPException(404, "Session not found")
        return session

    @app.post("/api/papers/{paper_id}/pdf")
    async def bind_paper_pdf(paper_id: str, file: UploadFile = File(...)):  # type: ignore[no-untyped-def]
        paper_id = _decode_paper_id(paper_id)
        data = await file.read(50 * 1024 * 1024 + 1)
        try:
            return service.bind_pdf(paper_id, data)
        except KeyError as exc:
            raise HTTPException(404, "Paper not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/papers/{paper_id}/explanation")
    async def explain_paper(paper_id: str, week: str = Query(default_factory=current_iso_week)):  # type: ignore[no-untyped-def]
        paper_id = _decode_paper_id(paper_id)
        try:
            return await service.explain_paper_cn(paper_id, week)
        except KeyError as exc:
            raise HTTPException(404, "Paper not found") from exc

    @app.get("/api/plans/{week}")
    def get_plan(week: str):  # type: ignore[no-untyped-def]
        try:
            return service.get_plan(week)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.patch("/api/plans/{week}")
    def patch_plan(week: str, patch: PlanPatch):  # type: ignore[no-untyped-def]
        try:
            plan = service.get_plan(week)
            if patch.tasks is not None:
                plan.tasks = patch.tasks
            if patch.capacity is not None:
                plan.capacity = patch.capacity
            return service.save_plan(plan)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/plans/{week}")
    def confirm_plan(week: str, plan: WeeklyPlan):  # type: ignore[no-untyped-def]
        if plan.week != week:
            raise HTTPException(400, "Plan week does not match URL")
        plan.status = "confirmed"
        return service.save_plan(plan)

    @app.patch("/api/clusters/{week}/{cluster_id}")
    def patch_cluster(week: str, cluster_id: str, payload: dict[str, str]):  # type: ignore[no-untyped-def]
        try:
            return service.update_cluster(week, cluster_id, payload.get("status", ""))
        except KeyError as exc:
            raise HTTPException(404, "Cluster not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/ideas")
    def ideas():  # type: ignore[no-untyped-def]
        return service.ideas()

    @app.get("/api/projects")
    def projects():  # type: ignore[no-untyped-def]
        return service.projects()

    @app.post("/api/projects")
    def create_project(payload: ProjectUpsertRequest):  # type: ignore[no-untyped-def]
        try:
            return service.save_project(payload)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.patch("/api/projects/{slug}")
    def update_project(slug: str, payload: ProjectUpsertRequest):  # type: ignore[no-untyped-def]
        try:
            return service.save_project(payload, existing_slug=slug)
        except KeyError as exc:
            raise HTTPException(404, "Project not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/projects/{slug}/workspace")
    def project_workspace(slug: str):  # type: ignore[no-untyped-def]
        try:
            return service.project_workspace(slug)
        except KeyError as exc:
            raise HTTPException(404, "Project not found") from exc

    @app.post("/api/projects/{slug}/messages")
    async def project_message(slug: str, payload: ProjectMessageRequest):  # type: ignore[no-untyped-def]
        try:
            return await service.message_project(slug, payload.message)
        except KeyError as exc:
            raise HTTPException(404, "Project not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/projects/{slug}/refresh")
    async def refresh_project_workspace(slug: str):  # type: ignore[no-untyped-def]
        try:
            return await service.message_project(
                slug,
                "Read the current project evidence, report what is complete, incomplete, temporary, or blocked, and refresh this project's board without changing its research files.",
                refresh=True,
            )
        except KeyError as exc:
            raise HTTPException(404, "Project not found") from exc
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.patch("/api/projects/{slug}/workspace/items/{item_id}")
    def update_project_item(slug: str, item_id: str, payload: ProjectItemPatch):  # type: ignore[no-untyped-def]
        try:
            return service.update_project_item(slug, item_id, payload)
        except KeyError as exc:
            raise HTTPException(404, "Project or board item not found") from exc

    @app.get("/api/project-modules")
    def project_modules():  # type: ignore[no-untyped-def]
        return service.project_modules()

    @app.post("/api/projects/{slug}/notes")
    async def add_project_note(slug: str, payload: ProjectNoteRequest):  # type: ignore[no-untyped-def]
        try:
            return await service.add_project_note(slug, payload)
        except KeyError as exc:
            raise HTTPException(404, "Project not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/projects/{slug}/notes/image")
    async def add_project_image(
        slug: str,
        file: UploadFile = File(...),
        caption: str = Form(""),
    ):  # type: ignore[no-untyped-def]
        data = await file.read(12 * 1024 * 1024 + 1)
        try:
            return await service.add_project_image(slug, data, file.filename or "project-note", caption)
        except KeyError as exc:
            raise HTTPException(404, "Project not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/projects/{slug}/modules")
    def create_project_module(slug: str, payload: ProjectModuleCreateRequest):  # type: ignore[no-untyped-def]
        try:
            return service.create_project_module(slug, payload)
        except KeyError as exc:
            raise HTTPException(404, "Project or section not found") from exc

    @app.post("/api/projects/{slug}/modules/apply")
    def apply_project_module(slug: str, payload: ProjectModuleApplyRequest):  # type: ignore[no-untyped-def]
        try:
            return service.apply_project_module(slug, payload.module_id)
        except KeyError as exc:
            raise HTTPException(404, "Project or module not found") from exc

    @app.post("/api/ideas/{slug}/actions/{action}")
    async def idea_action(slug: str, action: str):  # type: ignore[no-untyped-def]
        try:
            return await service.idea_action(slug, action)
        except KeyError as exc:
            raise HTTPException(404, "Idea not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/skills")
    def skills(q: str = "", lang: str = "zh"):  # type: ignore[no-untyped-def]
        return service.skills(q, lang=lang)

    @app.get("/api/runs")
    def runs():  # type: ignore[no-untyped-def]
        return service.runs()

    @app.get("/api/sync")
    def sync_overview():  # type: ignore[no-untyped-def]
        return service.sync_overview()

    @app.post("/api/sync")
    async def sync_repositories(payload: GitSyncRequest):  # type: ignore[no-untyped-def]
        try:
            return await asyncio.to_thread(service.sync_repositories, payload)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/runs/{run_id}/resume")
    async def resume_run(run_id: str):  # type: ignore[no-untyped-def]
        run = next((item for item in service.runs() if item.run_id == run_id), None)
        if not run:
            raise HTTPException(404, "Run not found")
        week = str(run.metadata.get("week", current_iso_week()))
        if run.run_type == "codex" and run_id.startswith("codex-rank-"):
            return await service.rank_week(week)
        if run.run_type == "codex" and run_id.startswith("codex-cluster-"):
            return await service.propose_clusters(week)
        raise HTTPException(409, "This run requires explicit recovery in its source system.")

    @app.post("/api/workflows/rank/{week}")
    async def rank_week(week: str):  # type: ignore[no-untyped-def]
        try:
            return await service.rank_week(week)
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/workflows/cluster/{week}")
    async def cluster_week(week: str):  # type: ignore[no-untyped-def]
        try:
            return await service.propose_clusters(week)
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/workflows/plan/{week}")
    async def draft_plan(week: str):  # type: ignore[no-untyped-def]
        try:
            return await service.draft_plan_codex(week)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/api/migration/gemini")
    def set_gemini(payload: dict[str, bool]):  # type: ignore[no-untyped-def]
        if "enabled" not in payload:
            raise HTTPException(400, "enabled is required")
        return service.set_gemini_migration(bool(payload["enabled"]))

    @app.get("/api/sessions/{session_id}")
    def session(session_id: str):  # type: ignore[no-untyped-def]
        try:
            return service.get_session(session_id)
        except KeyError as exc:
            raise HTTPException(404, "Session not found") from exc

    @app.post("/api/sessions/{session_id}/messages")
    async def session_message(session_id: str, payload: dict[str, str]):  # type: ignore[no-untyped-def]
        try:
            return await service.message_session(session_id, payload.get("message", ""))
        except KeyError as exc:
            raise HTTPException(404, "Session not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/approvals/{approval_id}")
    async def answer_approval(approval_id: str, payload: dict[str, str]):  # type: ignore[no-untyped-def]
        try:
            await service.codex.answer_approval(approval_id, payload.get("decision", ""))
            return {"status": "answered"}
        except KeyError as exc:
            raise HTTPException(404, "Approval not found") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/health")
    def health():  # type: ignore[no-untyped-def]
        return service.health()

    @app.websocket("/api/sessions/{session_id}/events")
    async def session_events(websocket: WebSocket, session_id: str):
        origin = websocket.headers.get("origin")
        if origin and origin not in resolved_settings.allowed_origins:
            await websocket.close(code=1008)
            return
        try:
            session = service.get_session(session_id)
        except KeyError:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        channel = session.codex_thread_id or session.session_id
        try:
            # Completed chat messages are persisted in the reading-session
            # sidecar. Only stream new events here; replaying every token on
            # reconnect produced duplicate, one-character bubbles.
            async for event in service.codex.events.subscribe(channel, replay=False):
                await websocket.send_json(event)
        except WebSocketDisconnect:
            return

    frontend = resolved_settings.repo_root / "apps" / "research-workbench" / "frontend" / "dist"
    if frontend.exists():
        assets = frontend / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):  # type: ignore[no-untyped-def]
            candidate = frontend / full_path
            if full_path and candidate.is_file() and candidate.resolve().is_relative_to(frontend.resolve()):
                return FileResponse(candidate)
            return FileResponse(frontend / "index.html")

    return app
