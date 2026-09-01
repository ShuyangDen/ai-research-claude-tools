from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from .codex_app_server import CodexAppServer, CodexSdkRunner, CodexUnavailable, diagnose_codex
from .config import WorkbenchSettings
from .file_store import FileCache, atomic_write_bytes, atomic_write_json, atomic_write_jsonl, content_hash, read_json, read_jsonl
from .git_sync import GitSyncService
from .models import (
    AttentionItem,
    ClusterProposal,
    Dashboard,
    GitSyncRequest,
    GitSyncResponse,
    PaperActionRequest,
    PaperRecord,
    PlanTask,
    PromotionEvent,
    Provenance,
    ReadingSession,
    RecommendationEntry,
    RecommendationSlate,
    RunReceipt,
    RunStep,
    WeeklyCandidatePool,
    WeeklyPlan,
    current_iso_week,
    utc_now,
)


TERMINAL_STATUSES = {"completed", "dismissed", "skipped", "expired", "clustered", "completed_full", "completed_rough"}
TOP5_EXCLUDED_STATUSES = TERMINAL_STATUSES | {"backlog"}


def _parse_markdown_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    result: dict[str, Any] = {"slug": path.stem, "title": path.stem, "path": str(path)}
    if text.startswith("---"):
        parts = text.split("---", 2)
        header = parts[1] if len(parts) >= 3 else ""
        for line in header.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip().strip("'\"")
            if key.strip() in {
                "title", "status", "stage", "role", "portfolio_role", "checkpoint", "checkpoint_pending",
                "updated", "primary", "backup", "priority", "paused", "pause_reason",
            }:
                result[key.strip()] = value
    heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if heading:
        result["title"] = heading.group(1).strip()
    result.setdefault("status", result.get("stage", "unknown"))
    result["role"] = result.get("role") or result.get("portfolio_role", "")
    result["checkpoint"] = result.get("checkpoint") or (
        "checkpoint pending" if str(result.get("checkpoint_pending", "")).casefold() == "true" else ""
    )
    return result


def _paper_from_mapping(raw: dict[str, Any]) -> PaperRecord:
    identifiers = raw.get("identifiers") if isinstance(raw.get("identifiers"), dict) else {}
    paper_id = str(raw.get("paper_id") or raw.get("id") or identifiers.get("paper_id") or "")
    provenance_raw = raw.get("provenance") or []
    if isinstance(provenance_raw, dict):
        provenance_raw = [provenance_raw]
    provenance = []
    for item in provenance_raw:
        if isinstance(item, dict):
            provenance.append(Provenance(**{key: item.get(key, "") for key in Provenance.model_fields}))
    return PaperRecord(
        paper_id=paper_id,
        title=str(raw.get("title", "Untitled paper")),
        abstract=str(raw.get("abstract", "")),
        chinese_explanation=str(raw.get("chinese_explanation", "")),
        authors=str(raw.get("authors", "")),
        venue=str(raw.get("venue", "")),
        url=str(raw.get("url", "")),
        published=str(raw.get("published", "")),
        source=str(raw.get("source", "")),
        methodology=str(raw.get("methodology", "")),
        matched_signal=str(raw.get("matched_signal", "")),
        relevance_reason=str(raw.get("relevance_reason", "")),
        public_reason=str(raw.get("public_reason", raw.get("relevance_reason", ""))),
        tier=int(raw.get("tier", 2) or 2),
        lane=str(raw.get("lane", "adjacent")),
        cluster_id=str(raw.get("cluster_id", "")),
        status=str(raw.get("status", "queued")),
        score=float(raw.get("score", raw.get("recommendation_score", 0)) or 0),
        raw_score=float(raw.get("raw_score", raw.get("raw_recommendation_score", 0)) or 0),
        priority_rank=int(raw.get("priority_rank", 0) or 0),
        identifiers={str(k): str(v) for k, v in identifiers.items() if v},
        provenance=provenance,
        pdf_path=str(raw.get("pdf_path", "")),
        note_path=str(raw.get("note_path", "")),
    )


class WorkbenchService:
    def __init__(self, settings: WorkbenchSettings, codex: CodexAppServer | None = None) -> None:
        self.settings = settings
        self.cache = FileCache()
        self.codex = codex or CodexAppServer(cwd=settings.repo_root)
        self.batch_codex = codex if codex is not None else CodexSdkRunner(cwd=settings.repo_root)
        self.git_sync = GitSyncService(
            {
                "tools": settings.repo_root,
                "tracker": settings.tracker_root,
                "ideas": settings.idea_vault,
                "ai-education": settings.ai_education_root,
                "knowledge": settings.personal_knowledge_vault,
            }
        )
        self.settings.workbench_root.mkdir(parents=True, exist_ok=True)

    def _week_root(self, week: str) -> Path:
        if not re.fullmatch(r"\d{4}-W\d{2}", week):
            raise ValueError(f"Invalid ISO week: {week}")
        return self.settings.workbench_root / "weeks" / week

    def _latest_candidate_pool_path(self, week: str) -> Path | None:
        root = self.settings.tracker_root / "archives" / week
        candidates = list(root.glob("*/candidate_pool.json")) if root.exists() else []
        if not candidates:
            direct = self.settings.tracker_root / "candidate_pool.json"
            return direct if direct.exists() else None
        return max(candidates, key=lambda item: item.stat().st_mtime_ns)

    def load_queue(self) -> list[dict[str, Any]]:
        path = self.settings.tracker_root / "queue_state.jsonl"
        return self.cache.get(path, read_jsonl) if path.exists() else []

    def load_pool(self, week: str) -> WeeklyCandidatePool:
        path = self._latest_candidate_pool_path(week)
        queue = self.load_queue()
        queue_by_id = {str(item.get("paper_id")): item for item in queue}
        if path:
            raw = self.cache.get(path, lambda item: read_json(item, {}))
            papers_raw = raw.get("papers", raw.get("candidates", [])) if isinstance(raw, dict) else []
            papers = [_paper_from_mapping(item) for item in papers_raw if isinstance(item, dict)]
            for paper in papers:
                overlay = queue_by_id.get(paper.paper_id)
                if overlay:
                    paper.status = str(overlay.get("status", paper.status))
                    paper.score = float(overlay.get("score", paper.score) or paper.score)
                    paper.lane = str(overlay.get("lane", paper.lane))
                    paper.tier = int(overlay.get("tier", paper.tier) or paper.tier)
            pool = WeeklyCandidatePool(
                week=str(raw.get("week", week)),
                github_run_id=str(raw.get("github_run_id", raw.get("run_id", path.parent.name))),
                generated_at=str(raw.get("generated_at", raw.get("created_at", utc_now()))),
                source_health=raw.get("source_health", {}),
                papers=papers,
                content_hash=str(raw.get("content_hash", "")),
            )
        else:
            papers = [_paper_from_mapping(item) for item in queue]
            health_path = self.settings.tracker_root / "source_health.json"
            health = self.cache.get(health_path, lambda item: read_json(item, {})) if health_path.exists() else {}
            pool = WeeklyCandidatePool(week=week, github_run_id="legacy-queue", source_health=health, papers=papers)
        if not pool.content_hash:
            pool.content_hash = content_hash([paper.model_dump(mode="json") for paper in pool.papers])
        return pool

    def list_papers(self, week: str, **filters: str) -> list[PaperRecord]:
        papers = self.load_pool(week).papers
        for key in ("status", "lane", "cluster_id"):
            value = filters.get(key)
            if value:
                papers = [paper for paper in papers if getattr(paper, key) == value]
        tier = filters.get("tier")
        if tier:
            papers = [paper for paper in papers if paper.tier == int(tier)]
        query = filters.get("q", "").casefold().strip()
        if query:
            papers = [
                paper
                for paper in papers
                if query in " ".join((paper.title, paper.abstract, paper.authors, paper.methodology)).casefold()
            ]
        return papers

    def get_paper(self, paper_id: str, week: str | None = None) -> PaperRecord:
        target_week = week or current_iso_week()
        weeks = [target_week]
        archive_root = self.settings.tracker_root / "archives"
        if archive_root.exists():
            weeks.extend(path.name for path in sorted(archive_root.iterdir(), reverse=True) if path.is_dir())
        seen: set[str] = set()
        for item in weeks:
            if item in seen:
                continue
            seen.add(item)
            for paper in self.load_pool(item).papers:
                if paper.paper_id == paper_id:
                    session = self.get_session_by_paper(paper_id)
                    if session:
                        paper.pdf_path = session.pdf_path
                        paper.note_path = session.note_path
                    explanation_path = self.settings.workbench_root / "explanations" / f"{self._safe_paper_key(paper_id)}.json"
                    explanation = read_json(explanation_path, {})
                    if isinstance(explanation, dict):
                        paper.chinese_explanation = str(explanation.get("text", ""))
                    return paper
        raise KeyError(paper_id)

    @staticmethod
    def _sort_papers(papers: Iterable[PaperRecord]) -> list[PaperRecord]:
        return sorted(
            papers,
            key=lambda paper: (
                paper.priority_rank <= 0,
                paper.priority_rank if paper.priority_rank > 0 else 99999,
                paper.tier,
                -paper.score,
                paper.title.casefold(),
            ),
        )

    def ensure_slate(self, week: str) -> RecommendationSlate:
        path = self._week_root(week) / "slate.json"
        pool = self.load_pool(week)
        if path.exists():
            try:
                slate = RecommendationSlate.model_validate(read_json(path, {}))
                if slate.pool_hash == pool.content_hash:
                    return self._refresh_top5(slate, pool, save=True)
            except (ValidationError, ValueError):
                pass
        ordered = self._sort_papers(pool.papers)
        entries = [
            RecommendationEntry(
                paper_id=paper.paper_id,
                rank=index,
                private_reason=paper.relevance_reason,
                public_reason=paper.public_reason or "与当前研究方向及方法偏好相关。",
                score=paper.score,
            )
            for index, paper in enumerate(ordered, 1)
            if paper.paper_id
        ]
        slate = RecommendationSlate(week=week, pool_hash=pool.content_hash, entries=entries, current_top5=[])
        return self._refresh_top5(slate, pool, save=True)

    def _refresh_top5(self, slate: RecommendationSlate, pool: WeeklyCandidatePool, *, save: bool) -> RecommendationSlate:
        papers = {paper.paper_id: paper for paper in pool.papers}
        previous = list(slate.current_top5)
        keep = [
            paper_id
            for paper_id in previous
            if paper_id in papers and papers[paper_id].status == "in_progress"
        ]
        for entry in sorted(slate.entries, key=lambda item: item.rank):
            paper = papers.get(entry.paper_id)
            if not paper or paper.paper_id in keep or paper.status in TOP5_EXCLUDED_STATUSES:
                continue
            keep.append(paper.paper_id)
            if len(keep) == 5:
                break
        slate.current_top5 = keep[:5]
        if save:
            atomic_write_json(self._week_root(slate.week) / "slate.json", slate)
        return slate

    async def rank_week(self, week: str) -> RecommendationSlate:
        pool = self.load_pool(week)
        receipt = RunReceipt(
            run_id=f"codex-rank-{week}-{uuid.uuid4().hex[:8]}",
            run_type="codex",
            status="running",
            steps=[RunStep(name="rank", status="running", started_at=utc_now())],
            metadata={"week": week},
        )
        self.save_run(receipt)
        payload = [
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "methodology": paper.methodology,
                "lane": paper.lane,
                "tier": paper.tier,
            }
            for paper in pool.papers
        ]
        prompt = (
            "Rank this existing weekly candidate pool for the researcher's reading queue. "
            "Do not browse or add papers. Return ONLY JSON with `entries`, an array of objects "
            "containing paper_id, rank, private_reason, public_reason, score. Private reasons may "
            "use the local profile; public reasons must remove personal-profile wording.\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        try:
            result = await self.batch_codex.run_prompt(prompt, timeout=300)
            parsed = self._extract_json(result.text)
            entries = [RecommendationEntry.model_validate(item) for item in parsed.get("entries", [])]
            known = {paper.paper_id for paper in pool.papers}
            entries = [entry for entry in entries if entry.paper_id in known]
            missing = [paper for paper in self._sort_papers(pool.papers) if paper.paper_id not in {e.paper_id for e in entries}]
            entries.extend(
                RecommendationEntry(
                    paper_id=paper.paper_id,
                    rank=len(entries) + index,
                    public_reason=paper.public_reason or "Existing candidate pool fallback.",
                    score=paper.score,
                )
                for index, paper in enumerate(missing, 1)
            )
            slate = RecommendationSlate(
                week=week,
                pool_hash=pool.content_hash,
                codex_thread_id=result.thread_id,
                generated_by="codex-app-server",
                entries=entries,
                current_top5=[],
            )
            self._refresh_top5(slate, pool, save=True)
            receipt.status = "succeeded"
            receipt.finished_at = utc_now()
            receipt.steps[0].status = "succeeded"
            receipt.steps[0].finished_at = receipt.finished_at
            receipt.artifacts = [str(self._week_root(week) / "slate.json")]
            self.save_run(receipt)
            self._record_parallel_validation(week, slate, pool)
            return slate
        except Exception as exc:
            receipt.status = "failed"
            receipt.finished_at = utc_now()
            receipt.error = str(exc)
            receipt.resumable = True
            receipt.steps[0].status = "failed"
            receipt.steps[0].detail = str(exc)
            self.save_run(receipt)
            raise

    def _record_parallel_validation(
        self, week: str, slate: RecommendationSlate, pool: WeeklyCandidatePool
    ) -> None:
        migration_path = self.settings.workbench_root / "migration.json"
        raw = read_json(migration_path, {})
        if not isinstance(raw, dict):
            raw = {}
        weeks = raw.setdefault("weeks", [])
        deterministic_top5 = [paper.paper_id for paper in self._sort_papers(pool.papers)[:5]]
        overlap = len(set(deterministic_top5) & set(slate.current_top5))
        archive_manifest = self._latest_candidate_pool_path(week)
        manifest = {}
        if archive_manifest:
            manifest = read_json(archive_manifest.with_name("manifest.json"), {})
        item = {
            "week": week,
            "gemini_success": bool(
                isinstance(manifest, dict)
                and manifest.get("status") == "succeeded"
                and manifest.get("mode") == "digest-and-discovery"
            ),
            "codex_success": True,
            "candidate_count": len(pool.papers),
            "top5_overlap": overlap,
            "top5_overlap_rate": overlap / 5,
            "recorded_at": utc_now(),
        }
        weeks[:] = [existing for existing in weeks if existing.get("week") != week]
        weeks.append(item)
        weeks.sort(key=lambda existing: str(existing.get("week", "")))
        raw.setdefault("gemini_enabled", True)
        atomic_write_json(migration_path, raw)

    async def propose_clusters(self, week: str) -> list[ClusterProposal]:
        pool = self.load_pool(week)
        payload = [
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "methodology": paper.methodology,
            }
            for paper in pool.papers
        ]
        prompt = (
            "Group only these papers into useful research-reading clusters. Return ONLY JSON with `clusters`; "
            "each item must contain cluster_id, question, mechanism, paper_ids, and status='proposed'. "
            "Use 2-8 papers per cluster and do not invent paper IDs.\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        receipt = RunReceipt(
            run_id=f"codex-cluster-{week}-{uuid.uuid4().hex[:8]}",
            run_type="codex",
            status="running",
            steps=[RunStep(name="cluster", status="running", started_at=utc_now())],
            metadata={"week": week},
        )
        self.save_run(receipt)
        try:
            result = await self.batch_codex.run_prompt(prompt, timeout=300)
            parsed = self._extract_json(result.text)
            known = {paper.paper_id for paper in pool.papers}
            clusters = [ClusterProposal.model_validate(item) for item in parsed.get("clusters", [])]
            for cluster in clusters:
                cluster.paper_ids = [paper_id for paper_id in cluster.paper_ids if paper_id in known][:8]
            clusters = [cluster for cluster in clusters if len(cluster.paper_ids) >= 2]
            atomic_write_json(
                self._week_root(week) / "clusters.json",
                [cluster.model_dump(mode="json") for cluster in clusters],
            )
            receipt.status = "succeeded"
            receipt.finished_at = utc_now()
            receipt.steps[0].status = "succeeded"
            receipt.steps[0].finished_at = receipt.finished_at
            receipt.artifacts = [str(self._week_root(week) / "clusters.json")]
            self.save_run(receipt)
            return clusters
        except Exception as exc:
            receipt.status = "failed"
            receipt.finished_at = utc_now()
            receipt.error = str(exc)
            receipt.resumable = True
            receipt.steps[0].status = "failed"
            receipt.steps[0].detail = str(exc)
            self.save_run(receipt)
            raise

    async def draft_plan_codex(self, week: str) -> WeeklyPlan:
        current = self.get_plan(week)
        if current.status == "confirmed":
            raise ValueError("Confirmed plans are not automatically rewritten")
        dashboard_context = {
            "top5": [paper.model_dump(mode="json") for paper in self.dashboard(week).top5],
            "ideas": self.ideas()[:10],
            "failed_runs": [run.model_dump(mode="json") for run in self.runs() if run.status == "failed"][:5],
            "capacity": {"deep": 1, "targeted": 2},
        }
        prompt = (
            "Draft this week's research plan from the supplied Top 5, idea checkpoints, and failed runs. "
            "Respect capacity: exactly one deep-reading slot and at most two targeted-reading slots. "
            "Return ONLY JSON with `capacity` and `tasks`. Every task needs task_id, category, title, "
            "related_id, priority, due_date, completed=false. Do not mark the plan confirmed.\n\n"
            + json.dumps(dashboard_context, ensure_ascii=False)
        )
        result = await self.batch_codex.run_prompt(prompt, timeout=300)
        parsed = self._extract_json(result.text)
        plan = WeeklyPlan(
            week=week,
            status="draft",
            capacity={str(k): int(v) for k, v in parsed.get("capacity", {"deep": 1, "targeted": 2}).items()},
            tasks=[PlanTask.model_validate(item) for item in parsed.get("tasks", [])],
        )
        return self.save_plan(plan)

    def set_gemini_migration(self, enabled: bool) -> dict[str, Any]:
        path = self.settings.workbench_root / "migration.json"
        raw = read_json(path, {})
        if not isinstance(raw, dict):
            raw = {}
        raw["gemini_enabled"] = enabled
        raw["changed_at"] = utc_now()
        atomic_write_json(path, raw)
        return self.migration_status()

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Codex ranking response did not contain JSON")
        value = json.loads(cleaned[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("Codex ranking response must be an object")
        return value

    def get_plan(self, week: str) -> WeeklyPlan:
        path = self._week_root(week) / "plan.json"
        if path.exists():
            return WeeklyPlan.model_validate(read_json(path, {}))
        slate = self.ensure_slate(week)
        papers = {paper.paper_id: paper for paper in self.load_pool(week).papers}
        tasks: list[PlanTask] = []
        for index, paper_id in enumerate(slate.current_top5[:3]):
            paper = papers.get(paper_id)
            if not paper:
                continue
            category = "deep" if index == 0 else "targeted"
            tasks.append(
                PlanTask(
                    task_id=f"paper-{paper_id}-{category}",
                    category=category,
                    title=f"{'精读' if category == 'deep' else '定向阅读'}：{paper.title}",
                    related_id=paper_id,
                    priority=index + 1,
                )
            )
        plan = WeeklyPlan(week=week, tasks=tasks)
        atomic_write_json(path, plan)
        return plan

    def save_plan(self, plan: WeeklyPlan) -> WeeklyPlan:
        if plan.status == "confirmed" and not plan.confirmed_at:
            plan.confirmed_at = utc_now()
        atomic_write_json(self._week_root(plan.week) / "plan.json", plan)
        return plan

    def clusters(self, week: str) -> list[ClusterProposal]:
        path = self._week_root(week) / "clusters.json"
        if path.exists():
            raw = read_json(path, [])
            if isinstance(raw, list):
                return [ClusterProposal.model_validate(item) for item in raw]
        papers = self.load_pool(week).papers
        grouped: dict[str, list[PaperRecord]] = {}
        for paper in papers:
            key = paper.cluster_id or paper.lane
            grouped.setdefault(key, []).append(paper)
        result = [
            ClusterProposal(
                cluster_id=f"{week}-{key}",
                question=f"{key.title()} lane 的共同研究问题是什么？",
                mechanism=", ".join(sorted({paper.methodology for paper in items if paper.methodology}))[:240],
                paper_ids=[paper.paper_id for paper in items[:8]],
            )
            for key, items in grouped.items()
            if len(items) >= 2
        ]
        atomic_write_json(path, [item.model_dump(mode="json") for item in result])
        return result

    def update_cluster(self, week: str, cluster_id: str, status: str) -> ClusterProposal:
        if status not in {"proposed", "confirmed", "dismissed"}:
            raise ValueError(f"Unsupported cluster status: {status}")
        clusters = self.clusters(week)
        cluster = next((item for item in clusters if item.cluster_id == cluster_id), None)
        if not cluster:
            raise KeyError(cluster_id)
        cluster.status = status  # type: ignore[assignment]
        atomic_write_json(
            self._week_root(week) / "clusters.json",
            [item.model_dump(mode="json") for item in clusters],
        )
        return cluster

    def ideas(self) -> list[dict[str, Any]]:
        root = self.settings.idea_vault / "ideas"
        if not root.exists():
            return []
        result = []
        for path in sorted(root.glob("*.md")):
            if path.name.startswith("_") or path.stem in {"index", "log"}:
                continue
            try:
                result.append(_parse_markdown_frontmatter(path))
            except OSError:
                continue
        return result

    def skills(self, query: str = "") -> list[dict[str, str]]:
        found: dict[str, dict[str, str]] = {}
        for root in self.settings.skill_roots:
            if not root.exists():
                continue
            for path in root.glob("*/SKILL.md"):
                text = path.read_text(encoding="utf-8-sig", errors="replace")[:3000]
                name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
                description_match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
                name = (name_match.group(1).strip().strip("'\"") if name_match else path.parent.name)
                description = description_match.group(1).strip().strip("'\"") if description_match else ""
                found.setdefault(name, {"name": name, "description": description, "path": str(path)})
        values = sorted(found.values(), key=lambda item: item["name"])
        if query:
            needle = query.casefold()
            values = [item for item in values if needle in f"{item['name']} {item['description']}".casefold()]
        return values

    def get_session(self, session_id: str) -> ReadingSession:
        path = self.settings.workbench_root / "sessions" / f"{session_id}.json"
        if not path.exists():
            raise KeyError(session_id)
        return ReadingSession.model_validate(read_json(path, {}))

    def get_session_by_paper(self, paper_id: str) -> ReadingSession | None:
        root = self.settings.workbench_root / "sessions"
        if not root.exists():
            return None
        for path in root.glob("*.json"):
            raw = read_json(path, {})
            if isinstance(raw, dict) and raw.get("paper_id") == paper_id:
                return ReadingSession.model_validate(raw)
        return None

    @staticmethod
    def _safe_paper_key(paper_id: str) -> str:
        return hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:24]

    def bind_pdf(self, paper_id: str, data: bytes) -> ReadingSession:
        if not data.startswith(b"%PDF"):
            raise ValueError("Selected file is not a PDF")
        if len(data) > 50 * 1024 * 1024:
            raise ValueError("PDF exceeds the 50 MB local limit")
        paper = self.get_paper(paper_id)
        path = self.settings.tracker_root / "pdf_cache" / f"{self._safe_paper_key(paper_id)}.pdf"
        atomic_write_bytes(path, data)
        session = self.get_session_by_paper(paper_id) or ReadingSession(
            session_id=f"paper-{self._safe_paper_key(paper.paper_id)}", paper_id=paper.paper_id
        )
        session.pdf_path = str(path)
        return self.save_session(session)

    def pdf_path(self, paper_id: str) -> Path:
        session = self.get_session_by_paper(paper_id)
        if not session or not session.pdf_path:
            raise KeyError(paper_id)
        path = Path(session.pdf_path).resolve()
        if path.suffix.casefold() != ".pdf" or not any(
            path.is_relative_to(root) for root in self.settings.allowed_roots
        ):
            raise ValueError("PDF path is outside configured roots")
        if not path.exists():
            raise KeyError(paper_id)
        return path

    async def explain_paper_cn(self, paper_id: str, week: str) -> dict[str, str]:
        paper = self.get_paper(paper_id, week)
        prompt = (
            "Explain the following paper abstract in concise Chinese for a researcher. Preserve all technical "
            "terms, causal claims, and uncertainty; do not claim anything beyond the abstract. Return plain text only.\n\n"
            f"Title: {paper.title}\nAbstract: {paper.abstract}"
        )
        result = await self.codex.run_prompt(prompt, timeout=180)
        payload = {
            "paper_id": paper_id,
            "text": result.text.strip(),
            "thread_id": result.thread_id,
            "generated_at": utc_now(),
        }
        atomic_write_json(
            self.settings.workbench_root / "explanations" / f"{self._safe_paper_key(paper_id)}.json",
            payload,
        )
        return payload

    def save_session(self, session: ReadingSession) -> ReadingSession:
        session.last_activity_at = utc_now()
        atomic_write_json(self.settings.workbench_root / "sessions" / f"{session.session_id}.json", session)
        return session

    async def act_on_paper(self, paper_id: str, request: PaperActionRequest, week: str) -> dict[str, Any]:
        paper = self.get_paper(paper_id, week)
        status_map = {
            "deep": "in_progress",
            "targeted": "in_progress",
            "cluster-only": "clustered",
            "skip": "skipped",
            "backlog": "backlog",
            "complete-full": "completed",
            "complete-rough": "completed",
        }
        if request.action == "cluster-only" and not request.cluster_id:
            raise ValueError("cluster-only requires cluster_id")
        self._update_queue_record(paper, status=status_map[request.action], action=request.action, cluster_id=request.cluster_id)
        session = self.get_session_by_paper(paper_id)
        if request.action in {"deep", "targeted"}:
            session = session or ReadingSession(
                session_id=f"paper-{self._safe_paper_key(paper_id)}", paper_id=paper_id
            )
            session.read_depth = "deep" if request.action == "deep" else "targeted"
            session.status = "in_progress"
            try:
                account = await self.codex.account()
                if account.get("account"):
                    session.codex_thread_id = await self.codex.start_thread(thread_id=session.codex_thread_id)
                    self.save_session(session)
                    asyncio.create_task(self._start_reading_turn(session, paper))
                else:
                    session.status = "waiting"
            except CodexUnavailable:
                session.status = "waiting"
            self.save_session(session)
        elif request.action in {"complete-full", "complete-rough"}:
            session = session or ReadingSession(
                session_id=f"paper-{self._safe_paper_key(paper_id)}", paper_id=paper_id
            )
            session.status = "archived"
            session.read_depth = "full" if request.action == "complete-full" else "rough"
            session.phase = "complete"
            self.save_session(session)
            if session.codex_thread_id:
                asyncio.create_task(self._run_completion_turn(session, request.action))
        slate = self.ensure_slate(week)
        before = list(slate.current_top5)
        slate = self._refresh_top5(slate, self.load_pool(week), save=False)
        removed = next((item for item in before if item not in slate.current_top5), "")
        promoted = next((item for item in slate.current_top5 if item not in before), "")
        if removed:
            slate.promotion_history.append(
                PromotionEvent(removed_paper_id=removed, promoted_paper_id=promoted, reason=request.action)
            )
        atomic_write_json(self._week_root(week) / "slate.json", slate)
        return {"paper": self.get_paper(paper_id, week), "session": session, "slate": slate}

    def _update_queue_record(self, paper: PaperRecord, *, status: str, action: str, cluster_id: str = "") -> None:
        path = self.settings.tracker_root / "queue_state.jsonl"
        records = self.load_queue()
        target = next((item for item in records if item.get("paper_id") == paper.paper_id), None)
        today = date.today().isoformat()
        if target is None:
            target = {
                "paper_id": paper.paper_id,
                "candidate_slug": re.sub(r"[^a-z0-9]+", "-", paper.title.casefold()).strip("-")[:60],
                "title": paper.title,
                "tier": paper.tier,
                "lane": paper.lane,
                "matched_signal": paper.matched_signal,
                "authors": paper.authors,
                "venue": paper.venue,
                "url": paper.url,
                "published": paper.published,
                "added": today,
                "last_seen": today,
                "source": paper.source,
                "identifiers": paper.identifiers,
                "schema_version": "1.0",
            }
            records.append(target)
        target["status"] = status
        target["triage_action"] = action
        target["last_seen"] = today
        if cluster_id:
            target["cluster_id"] = cluster_id
        atomic_write_jsonl(path, records)
        self.cache.invalidate(path)

    async def _start_reading_turn(self, session: ReadingSession, paper: PaperRecord) -> None:
        skill_path = self.settings.repo_root / "packages" / "codex" / "skills" / "paper-reading-tutor" / "SKILL.md"
        prompt = (
            f"$paper-reading-tutor Start Phase 0 for this paper. Preserve the English title and abstract, "
            f"then explain in Chinese only when useful. Do not invent missing PDF content.\n\n"
            f"Paper ID: {paper.paper_id}\nTitle: {paper.title}\nAbstract: {paper.abstract}\nURL: {paper.url}"
        )
        try:
            await self.codex.run_prompt(
                prompt,
                thread_id=session.codex_thread_id,
                skill=("paper-reading-tutor", skill_path) if skill_path.exists() else None,
            )
        except Exception as exc:
            session.status = "failed"
            self.save_session(session)
            await self.codex.events.publish(session.codex_thread_id, {"method": "workbench/error", "params": {"detail": str(exc)}})

    async def _run_completion_turn(self, session: ReadingSession, action: str) -> None:
        skill_name = "paper-done" if action == "complete-full" else "paper-rough-done"
        path = self.settings.repo_root / "packages" / "codex" / "skills" / skill_name / "SKILL.md"
        prompt = f"${skill_name} The user explicitly completed this Workbench action for paper {session.paper_id}. Run the post-reading workflow and surface any required approval."
        try:
            await self.codex.run_prompt(
                prompt,
                thread_id=session.codex_thread_id,
                skill=(skill_name, path) if path.exists() else None,
                writable_roots=(
                    self.settings.tracker_root,
                    self.settings.ai_education_root,
                    self.settings.personal_knowledge_vault,
                    self.settings.workbench_root,
                ),
            )
        except Exception as exc:
            await self.codex.events.publish(session.codex_thread_id, {"method": "workbench/error", "params": {"detail": str(exc)}})

    async def message_session(self, session_id: str, message: str) -> ReadingSession:
        if not message.strip():
            raise ValueError("message cannot be empty")
        session = self.get_session(session_id)
        result = await self.codex.run_prompt(message.strip(), thread_id=session.codex_thread_id)
        session.codex_thread_id = result.thread_id
        session.status = "in_progress"
        return self.save_session(session)

    async def idea_action(self, slug: str, action: str) -> dict[str, Any]:
        if action not in {"idea-chat", "idea-next"}:
            raise ValueError(action)
        idea = next((item for item in self.ideas() if item.get("slug") == slug), None)
        if not idea:
            raise KeyError(slug)
        skill_path = self.settings.repo_root / "packages" / "codex" / "skills" / action / "SKILL.md"
        prompt = f"${action} Work with the existing idea `{slug}` at {idea['path']}. Do not advance or write across the vault without the user's explicit confirmation."
        result = await self.codex.run_prompt(
            prompt,
            skill=(action, skill_path) if skill_path.exists() else None,
            writable_roots=(self.settings.idea_vault, self.settings.workbench_root) if action == "idea-next" else (),
        )
        return {"thread_id": result.thread_id, "idea": idea, "status": "started"}

    def save_run(self, receipt: RunReceipt) -> None:
        atomic_write_json(self.settings.workbench_root / "runs" / f"{receipt.run_id}.json", receipt)

    def sync_overview(self):  # type: ignore[no-untyped-def]
        return self.git_sync.overview()

    def sync_repositories(self, request: GitSyncRequest) -> GitSyncResponse:
        run_id = f"github-sync-{uuid.uuid4().hex[:10]}"
        receipt = RunReceipt(
            run_id=run_id,
            run_type="sync",
            status="running",
            steps=[RunStep(name="GitHub repository sync", status="running", started_at=utc_now())],
            metadata={"mode": request.mode, "repository_count": len(request.repository_ids)},
        )
        self.save_run(receipt)
        try:
            results, overview = self.git_sync.sync(request)
            failed = any(item.status == "failed" for item in results)
            receipt.status = "failed" if failed else "succeeded"
            receipt.finished_at = utc_now()
            receipt.error = "部分仓库未同步；请查看同步中心。" if failed else ""
            receipt.steps = [
                RunStep(
                    name=item.name,
                    status="failed" if item.status == "failed" else "succeeded",
                    detail=item.detail,
                    finished_at=receipt.finished_at,
                )
                for item in results
            ]
            self.save_run(receipt)
            return GitSyncResponse(run_id=run_id, status=receipt.status, results=results, overview=overview)
        except Exception as exc:
            receipt.status = "failed"
            receipt.finished_at = utc_now()
            receipt.error = str(exc)[:500]
            receipt.steps[0].status = "failed"
            receipt.steps[0].detail = receipt.error
            self.save_run(receipt)
            raise

    def runs(self) -> list[RunReceipt]:
        result: list[RunReceipt] = []
        root = self.settings.workbench_root / "runs"
        if root.exists():
            for path in root.glob("*.json"):
                try:
                    result.append(RunReceipt.model_validate(read_json(path, {})))
                except ValidationError:
                    continue
        archives = self.settings.tracker_root / "archives"
        if archives.exists():
            for path in archives.glob("*/*/manifest.json"):
                raw = read_json(path, {})
                if not isinstance(raw, dict):
                    continue
                result.append(
                    RunReceipt(
                        run_id=str(raw.get("github_run_id", path.parent.name)),
                        run_type="github",
                        status=str(raw.get("status", "succeeded")),
                        started_at=str(raw.get("started_at", raw.get("generated_at", utc_now()))),
                        finished_at=str(raw.get("finished_at", "")),
                        error=str(raw.get("error", "")),
                        artifacts=[str(item) for item in raw.get("artifacts", [])],
                        metadata={"week": path.parent.parent.name, "manifest": str(path)},
                    )
                )
        return sorted(result, key=lambda item: item.started_at, reverse=True)

    def migration_status(self) -> dict[str, Any]:
        path = self.settings.workbench_root / "migration.json"
        raw = read_json(path, {})
        weeks = raw.get("weeks", []) if isinstance(raw, dict) else []
        consecutive = 0
        for item in reversed(weeks):
            if item.get("gemini_success") and item.get("codex_success"):
                consecutive += 1
            else:
                break
        return {
            "weeks": weeks[-4:],
            "consecutive_successes": consecutive,
            "checkpoint_ready": consecutive >= 4,
            "gemini_enabled": bool(raw.get("gemini_enabled", True)) if isinstance(raw, dict) else True,
        }

    def attention(self, week: str) -> list[AttentionItem]:
        result: list[AttentionItem] = []
        for approval in self.codex.pending_approvals:
            params = approval.get("params", {})
            reason = str(params.get("reason") or params.get("command") or "Codex 请求执行受保护操作")
            result.append(
                AttentionItem(
                    attention_id=f"approval-{approval['approval_id']}",
                    kind="decision",
                    severity="warning",
                    title="Codex 等待审批",
                    detail=reason[:500],
                    action_label="审批",
                    related_id=str(approval["approval_id"]),
                )
            )
        diagnostic = diagnose_codex()
        if not diagnostic.logged_in:
            result.append(
                AttentionItem(
                    attention_id="codex-auth",
                    kind="auth",
                    severity="error",
                    title="Codex 尚未登录",
                    detail="运行 `apps/research-workbench/login.ps1`，使用 ChatGPT subscription 登录后即可排名和阅读。",
                    action_label="查看登录指引",
                )
            )
        pool_path = self._latest_candidate_pool_path(week)
        if not pool_path:
            result.append(
                AttentionItem(
                    attention_id="candidate-pool-missing",
                    kind="missing-data",
                    title="本周还没有结构化候选池",
                    detail="当前会回退读取 legacy queue；运行 discovery-only 后可看到完整摘要。",
                )
            )
        migration = self.migration_status()
        if migration["checkpoint_ready"] and migration["gemini_enabled"]:
            result.append(
                AttentionItem(
                    attention_id="migration-checkpoint",
                    kind="checkpoint",
                    severity="info",
                    title="四周双轨验证已完成",
                    detail="可以人工决定是否关闭 Gemini 排名；Workbench 不会自动切换。",
                )
            )
        for run in self.runs():
            if run.status == "failed":
                result.append(
                    AttentionItem(
                        attention_id=f"run-{run.run_id}",
                        kind="failure",
                        severity="error",
                        title=f"运行失败：{run.run_id}",
                        detail=run.error,
                        related_id=run.run_id,
                        action_label="恢复",
                    )
                )
        return result[:12]

    def health(self) -> dict[str, Any]:
        diagnostic = diagnose_codex()
        paths = {
            "machine_paths": self.settings.machine_paths_file,
            "state_root": self.settings.state_root,
            "tracker_root": self.settings.tracker_root,
            "idea_vault": self.settings.idea_vault,
            "ai_education_root": self.settings.ai_education_root,
        }
        return {
            "status": "ok" if diagnostic.installed and all(path.exists() for key, path in paths.items() if key != "state_root") else "degraded",
            "codex": dataclasses.asdict(diagnostic),
            "paths": {key: {"path": str(path), "exists": path.exists()} for key, path in paths.items()},
            "app_server": {"running": self.codex.running, "pending_approvals": self.codex.pending_approvals},
        }

    def dashboard(self, week: str | None = None) -> Dashboard:
        selected_week = week or current_iso_week()
        pool = self.load_pool(selected_week)
        slate = self.ensure_slate(selected_week)
        by_id = {paper.paper_id: paper for paper in pool.papers}
        health = pool.source_health or {"status": "unknown"}
        return Dashboard(
            week=selected_week,
            top5=[by_id[paper_id] for paper_id in slate.current_top5 if paper_id in by_id],
            plan=self.get_plan(selected_week),
            clusters=self.clusters(selected_week),
            attention=self.attention(selected_week),
            tracker_health=health,
            ideas=self.ideas()[:8],
            slate=slate,
            migration=self.migration_status(),
        )
