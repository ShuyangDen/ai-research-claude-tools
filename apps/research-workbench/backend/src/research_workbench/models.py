from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


PaperAction = Literal[
    "deep",
    "targeted",
    "cluster-only",
    "skip",
    "backlog",
    "complete-full",
    "complete-rough",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Provenance(BaseModel):
    source: str = ""
    source_id: str = ""
    fetched_at: str = ""
    url: str = ""


class PaperRecord(BaseModel):
    paper_id: str
    title: str
    abstract: str = ""
    chinese_explanation: str = ""
    authors: str = ""
    venue: str = ""
    url: str = ""
    published: str = ""
    source: str = ""
    methodology: str = ""
    matched_signal: str = ""
    relevance_reason: str = ""
    public_reason: str = ""
    tier: int = 2
    lane: str = "adjacent"
    cluster_id: str = ""
    status: str = "queued"
    score: float = 0.0
    raw_score: float = 0.0
    priority_rank: int = 0
    identifiers: dict[str, str] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)
    pdf_path: str = ""
    note_path: str = ""


class WeeklyCandidatePool(ContractModel):
    schema_name: str = Field(default="ai-research-workbench.candidate-pool", alias="schema")
    schema_version: int = 1
    week: str
    github_run_id: str
    generated_at: str = Field(default_factory=utc_now)
    source_health: dict[str, Any] = Field(default_factory=dict)
    papers: list[PaperRecord] = Field(default_factory=list)
    content_hash: str = ""


class RecommendationEntry(BaseModel):
    paper_id: str
    rank: int
    private_reason: str = ""
    public_reason: str = ""
    score: float = 0.0


class PromotionEvent(BaseModel):
    at: str = Field(default_factory=utc_now)
    removed_paper_id: str
    promoted_paper_id: str = ""
    reason: str


class RecommendationSlate(ContractModel):
    schema_name: str = Field(default="ai-research-workbench.recommendation-slate", alias="schema")
    schema_version: int = 1
    week: str
    pool_hash: str
    profile_hash: str = ""
    codex_thread_id: str = ""
    generated_at: str = Field(default_factory=utc_now)
    generated_by: str = "deterministic-fallback"
    entries: list[RecommendationEntry] = Field(default_factory=list)
    current_top5: list[str] = Field(default_factory=list)
    promotion_history: list[PromotionEvent] = Field(default_factory=list)


class ClusterProposal(BaseModel):
    cluster_id: str
    question: str
    mechanism: str = ""
    paper_ids: list[str] = Field(default_factory=list)
    status: Literal["proposed", "confirmed", "dismissed"] = "proposed"


class PlanTask(BaseModel):
    task_id: str
    category: Literal["deep", "targeted", "idea", "workflow", "recovery", "other"]
    title: str
    related_id: str = ""
    priority: int = 2
    due_date: str = ""
    completed: bool = False


class WeeklyPlan(ContractModel):
    schema_name: str = Field(default="ai-research-workbench.weekly-plan", alias="schema")
    schema_version: int = 1
    week: str
    status: Literal["draft", "confirmed"] = "draft"
    generated_at: str = Field(default_factory=utc_now)
    confirmed_at: str = ""
    capacity: dict[str, int] = Field(default_factory=lambda: {"deep": 1, "targeted": 2})
    tasks: list[PlanTask] = Field(default_factory=list)


class ReadingSession(ContractModel):
    schema_name: str = Field(default="ai-research-workbench.reading-session", alias="schema")
    schema_version: int = 1
    session_id: str
    paper_id: str
    codex_thread_id: str = ""
    phase: str = "phase-0"
    read_depth: Literal["preview", "targeted", "deep", "rough", "full"] = "preview"
    status: Literal["ready", "in_progress", "waiting", "completed", "archived", "failed"] = "ready"
    note_path: str = ""
    pdf_path: str = ""
    last_activity_at: str = Field(default_factory=utc_now)


class AttentionItem(BaseModel):
    attention_id: str
    kind: Literal["decision", "failure", "stale", "auth", "missing-data", "checkpoint"]
    severity: Literal["info", "warning", "error"] = "warning"
    title: str
    detail: str = ""
    action_label: str = ""
    related_id: str = ""


class RunStep(BaseModel):
    name: str
    status: Literal["pending", "running", "succeeded", "failed", "waiting"]
    detail: str = ""
    started_at: str = ""
    finished_at: str = ""


class RunReceipt(ContractModel):
    schema_name: str = Field(default="ai-research-workbench.run-receipt", alias="schema")
    schema_version: int = 1
    run_id: str
    run_type: Literal["github", "research-core", "codex", "tracker", "sync"]
    status: Literal["pending", "running", "succeeded", "failed", "waiting"]
    started_at: str = Field(default_factory=utc_now)
    finished_at: str = ""
    resumable: bool = False
    error: str = ""
    steps: list[RunStep] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperActionRequest(BaseModel):
    action: PaperAction
    cluster_id: str = ""


class PlanPatch(BaseModel):
    tasks: list[PlanTask] | None = None
    capacity: dict[str, int] | None = None


class GitRepositoryState(BaseModel):
    repository_id: str
    name: str
    roles: list[str] = Field(default_factory=list)
    available: bool = True
    branch: str = ""
    remote: str = ""
    has_upstream: bool = False
    dirty_count: int = 0
    sensitive_change_count: int = 0
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""
    state: Literal["clean", "dirty", "ahead", "behind", "diverged", "unavailable", "error"] = "clean"
    detail: str = ""


class GitSyncOverview(BaseModel):
    generated_at: str = Field(default_factory=utc_now)
    repositories: list[GitRepositoryState] = Field(default_factory=list)
    privacy: list[str] = Field(default_factory=list)


class GitSyncRequest(BaseModel):
    mode: Literal["fetch", "pull", "push", "sync"] = "sync"
    repository_ids: list[str] = Field(default_factory=list)


class GitSyncResult(BaseModel):
    repository_id: str
    name: str
    status: Literal["succeeded", "failed", "skipped"]
    detail: str


class GitSyncResponse(BaseModel):
    run_id: str
    status: Literal["succeeded", "failed"]
    results: list[GitSyncResult]
    overview: GitSyncOverview


class Dashboard(BaseModel):
    week: str
    top5: list[PaperRecord]
    plan: WeeklyPlan
    clusters: list[ClusterProposal]
    attention: list[AttentionItem]
    tracker_health: dict[str, Any]
    ideas: list[dict[str, Any]]
    slate: RecommendationSlate
    migration: dict[str, Any]


def current_iso_week(today: date | None = None) -> str:
    value = today or date.today()
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
