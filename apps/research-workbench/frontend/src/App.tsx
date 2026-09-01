import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, Archive, ArrowRight, BookOpen, Bot, Check, ChevronRight, CircleAlert,
  CircleCheck, Clock3, FileText, FolderKanban, GitBranch, HeartPulse, Home, Layers3, Lightbulb,
  ListChecks, LoaderCircle, Menu, MessageSquareText, Moon, Pencil, Play, Plus, RefreshCw, Search,
  Settings2, ShieldCheck, Sparkles, Sun, Workflow, X,
} from "lucide-react";
import { bootstrap, get, mutate, sessionSocket, uploadPdf } from "./api";
import type {
  Dashboard, GitRepositoryState, GitSyncOverview, GitSyncResponse, Idea, NavKey,
  Paper, ReadingSession, ResearchProject, RunReceipt, Slate, WeeklyPlan,
} from "./types";

const navigation: Array<{ key: NavKey; label: string; icon: typeof Home }> = [
  { key: "week", label: "本周", icon: Home },
  { key: "papers", label: "论文", icon: FileText },
  { key: "reading", label: "阅读室", icon: BookOpen },
  { key: "ideas", label: "Ideas", icon: Lightbulb },
  { key: "projects", label: "项目", icon: FolderKanban },
  { key: "skills", label: "流程", icon: Workflow },
  { key: "runs", label: "运行记录", icon: Activity },
];

const laneName: Record<string, string> = {
  exploit: "核心方向",
  adjacent: "相邻方向",
  contradiction: "反证/挑战",
  methodology: "方法",
};

type TierFilter = 0 | 1 | 2 | 3;

function TierFilters({ value, papers, onChange, label = "按优先级筛选" }: {
  value: TierFilter; papers: Paper[]; onChange: (value: TierFilter) => void; label?: string;
}) {
  return <div className="tier-filter-row" aria-label={label}>
    {([0, 1, 2, 3] as TierFilter[]).map((tier) => <button key={tier} className={`filter ${value === tier ? "active" : ""}`} onClick={() => onChange(tier)}>
      {tier === 0 ? "全部" : `T${tier}`} <span>{tier === 0 ? papers.length : papers.filter((paper) => paper.tier === tier).length}</span>
    </button>)}
  </div>;
}

function statusLabel(status: string) {
  return ({ queued: "待处理", in_progress: "阅读中", backlog: "Backlog", completed: "已完成", skipped: "已跳过", clustered: "仅聚类" } as Record<string, string>)[status] || status;
}

function SectionTitle({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: React.ReactNode }) {
  return <div className="section-title">
    <div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2></div>
    {action}
  </div>;
}

function Empty({ icon: Icon = FileText, title, detail }: { icon?: typeof FileText; title: string; detail: string }) {
  return <div className="empty"><Icon size={28} /><strong>{title}</strong><span>{detail}</span></div>;
}

function PaperMeta({ paper }: { paper: Paper }) {
  return <div className="paper-meta">
    <span className={`lane lane-${paper.lane}`}>{laneName[paper.lane] || paper.lane}</span>
    <span>Tier {paper.tier}</span>
    {paper.methodology && <span>{paper.methodology}</span>}
    {paper.published && <span>{paper.published}</span>}
  </div>;
}

function PaperCard({ paper, rank, onOpen, onAction, busy }: {
  paper: Paper; rank?: number; onOpen: () => void; onAction: (action: string) => void; busy: boolean;
}) {
  return <article className="paper-card">
    {rank && <div className="rank">{String(rank).padStart(2, "0")}</div>}
    <div className="paper-card-body">
      <PaperMeta paper={paper} />
      <button className="title-link" onClick={onOpen}>{paper.title}</button>
      <div className="authors">{paper.authors || paper.venue || paper.source}</div>
      <p className="reason">{paper.public_reason || paper.relevance_reason || "确定性预排；本地 Codex 正在补充推荐理由。"}</p>
      <div className="card-actions">
        <button className="primary small" disabled={busy} onClick={() => onAction("deep")}><Play size={14} />开始精读</button>
        <button className="ghost small" disabled={busy} onClick={() => onAction("targeted")}>定向阅读</button>
        <button className="ghost small" disabled={busy} onClick={() => onAction("backlog")}>稍后</button>
        <button className="icon-button" aria-label="查看论文" onClick={onOpen}><ChevronRight size={18} /></button>
      </div>
    </div>
  </article>;
}

export default function App() {
  const [nav, setNav] = useState<NavKey>("week");
  const [week, setWeek] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [health, setHealth] = useState<Record<string, any> | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [session, setSession] = useState<ReadingSession | null>(null);
  const [skills, setSkills] = useState<Array<{ name: string; description: string }>>([]);
  const [runs, setRuns] = useState<RunReceipt[]>([]);
  const [syncOverview, setSyncOverview] = useState<GitSyncOverview | null>(null);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [query, setQuery] = useState("");
  const [skillQuery, setSkillQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [ranking, setRanking] = useState(false);
  const [error, setError] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem("workbench-theme") === "dark");
  const autoRankAttempted = useRef(new Set<string>());

  async function loadDashboard(targetWeek?: string) {
    const chosen = targetWeek || week;
    const data = await get<Dashboard>(`/api/dashboard${chosen ? `?week=${encodeURIComponent(chosen)}` : ""}`);
    setDashboard(data);
    setWeek(data.week);
    return data;
  }

  useEffect(() => {
    (async () => {
      try {
        const boot = await bootstrap();
        setWeek(boot.week);
        const [data, healthData] = await Promise.all([
          get<Dashboard>(`/api/dashboard?week=${boot.week}`),
          get<Record<string, any>>("/api/health"),
        ]);
        setDashboard(data);
        setHealth(healthData);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : String(reason));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("workbench-theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    if (!week) return;
    if (nav === "papers" || nav === "reading") get<Paper[]>(`/api/weeks/${week}/papers`).then(setPapers).catch(showError);
    if (nav === "skills") get<Array<{ name: string; description: string }>>(`/api/skills?q=${encodeURIComponent(skillQuery)}`).then(setSkills).catch(showError);
    if (nav === "runs") Promise.all([
      get<RunReceipt[]>("/api/runs"),
      get<GitSyncOverview>("/api/sync"),
    ]).then(([runData, syncData]) => {
      setRuns(runData);
      setSyncOverview(syncData);
    }).catch(showError);
    if (nav === "ideas") get<Idea[]>("/api/ideas").then(setIdeas).catch(showError);
    if (nav === "projects") get<ResearchProject[]>("/api/projects").then(setProjects).catch(showError);
  }, [nav, week, skillQuery]);

  useEffect(() => {
    if (!dashboard || health?.codex?.logged_in !== true) return;
    if (dashboard.slate.generated_by === "codex-app-server" && dashboard.slate.ranking_version >= 3) return;
    const key = `${dashboard.week}:${dashboard.slate.pool_hash}:${dashboard.slate.ranking_version}`;
    if (autoRankAttempted.current.has(key)) return;
    autoRankAttempted.current.add(key);
    setRanking(true);
    mutate(`/api/workflows/rank/${dashboard.week}`, "POST")
      .then(() => loadDashboard(dashboard.week))
      .catch((reason) => setError(`本地 Codex 自动排名未完成：${reason instanceof Error ? reason.message : String(reason)}`))
      .finally(() => setRanking(false));
  }, [dashboard?.week, dashboard?.slate.generated_by, dashboard?.slate.pool_hash, dashboard?.slate.ranking_version, health?.codex?.logged_in]);

  function showError(reason: unknown) {
    setError(reason instanceof Error ? reason.message : String(reason));
  }

  async function openPaper(paper: Paper, destination: NavKey = "reading") {
    try {
      const detail = await get<Paper>(`/api/papers/${encodeURIComponent(paper.paper_id)}?week=${week}`);
      setSelectedPaper(detail);
      setNav(destination);
      try {
        setSession(await get<ReadingSession>(`/api/papers/${encodeURIComponent(paper.paper_id)}/session`));
      } catch {
        setSession(null);
      }
    } catch (reason) { showError(reason); }
  }

  async function paperAction(paper: Paper, action: string, clusterId = "") {
    setBusy(`${paper.paper_id}:${action}`);
    try {
      const result = await mutate<{ paper: Paper; session: ReadingSession | null; slate: Slate }>(
        `/api/papers/${encodeURIComponent(paper.paper_id)}/actions?week=${week}`,
        "POST",
        { action, cluster_id: clusterId },
      );
      setSelectedPaper(result.paper);
      setSession(result.session);
      await loadDashboard();
      if (action === "deep" || action === "targeted") setNav("reading");
      if (nav === "papers" || nav === "reading") setPapers(await get<Paper[]>(`/api/weeks/${week}/papers`));
    } catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function rankWeek() {
    setRanking(true);
    try {
      await mutate(`/api/workflows/rank/${week}`, "POST");
      await loadDashboard();
    } catch (reason) { showError(reason); }
    finally { setRanking(false); }
  }

  async function saveProject(project: ResearchProject, existingSlug = "") {
    setBusy(`project:${existingSlug || project.slug}`);
    try {
      await mutate(existingSlug ? `/api/projects/${encodeURIComponent(existingSlug)}` : "/api/projects", existingSlug ? "PATCH" : "POST", project);
      setProjects(await get<ResearchProject[]>("/api/projects"));
    } catch (reason) { showError(reason); throw reason; }
    finally { setBusy(""); }
  }

  async function confirmPlan(plan: WeeklyPlan) {
    setBusy("plan");
    try {
      await mutate(`/api/plans/${week}`, "POST", plan);
      await loadDashboard();
    } catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function updatePlan(plan: WeeklyPlan) {
    setBusy("plan-edit");
    try {
      await mutate(`/api/plans/${week}`, "PATCH", { tasks: plan.tasks, capacity: plan.capacity });
      await loadDashboard();
    } catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function draftPlan() {
    setBusy("draft-plan");
    try { await mutate(`/api/workflows/plan/${week}`, "POST"); await loadDashboard(); }
    catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function proposeClusters() {
    setBusy("clusters");
    try { await mutate(`/api/workflows/cluster/${week}`, "POST"); await loadDashboard(); }
    catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function setClusterStatus(clusterId: string, status: "confirmed" | "dismissed") {
    setBusy(`cluster:${clusterId}`);
    try { await mutate(`/api/clusters/${week}/${encodeURIComponent(clusterId)}`, "PATCH", { status }); await loadDashboard(); }
    catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function answerApproval(approvalId: string, decision: "accept" | "decline") {
    setBusy(`approval:${approvalId}`);
    try { await mutate(`/api/approvals/${encodeURIComponent(approvalId)}`, "POST", { decision }); await loadDashboard(); }
    catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function runIdea(idea: Idea, action: "idea-chat" | "idea-next") {
    setBusy(`${idea.slug}:${action}`);
    try {
      await mutate(`/api/ideas/${encodeURIComponent(idea.slug)}/actions/${action}`, "POST");
      setNav("runs");
      setRuns(await get<RunReceipt[]>("/api/runs"));
    } catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  async function syncRepositories(repositoryIds: string[] = []) {
    const scope = repositoryIds.length ? "这个仓库" : "所有已配置仓库";
    if (!window.confirm(`现在同步${scope}吗？\n\n工作台只会同步已经提交的 Git 内容，不会自动 add 或 commit。`)) return;
    const busyKey = repositoryIds.length === 1 ? `sync:${repositoryIds[0]}` : "sync:all";
    setBusy(busyKey);
    try {
      const response = await mutate<GitSyncResponse>("/api/sync", "POST", {
        mode: "sync",
        repository_ids: repositoryIds,
      });
      setSyncOverview(response.overview);
      setRuns(await get<RunReceipt[]>("/api/runs"));
      const failures = response.results.filter((result) => result.status === "failed");
      if (failures.length) {
        setError(failures.map((result) => `${result.name}：${result.detail}`).join("；"));
      }
    } catch (reason) { showError(reason); }
    finally { setBusy(""); }
  }

  function switchNav(key: NavKey) {
    setNav(key);
    setMobileNav(false);
  }

  function launchSkill(name: string) {
    if (name === "idea-chat" || name === "idea-next") return switchNav("ideas");
    if (name === "paper-reading-tutor") return switchNav(selectedPaper ? "reading" : "papers");
    if (name === "paper-done") return switchNav("reading");
    if (name === "paper-batch-triage") return switchNav("papers");
    return switchNav("week");
  }

  const filteredPapers = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return papers;
    return papers.filter((paper) => `${paper.title} ${paper.abstract} ${paper.authors} ${paper.methodology}`.toLocaleLowerCase().includes(needle));
  }, [papers, query]);

  if (loading) return <div className="splash"><div className="brand-mark"><BookOpen /></div><LoaderCircle className="spin" /><span>正在打开研究工作台…</span></div>;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
      <div className="brand"><div className="brand-mark"><BookOpen size={20} /></div><div><strong>Research</strong><span>Workbench</span></div></div>
      <nav>
        {navigation.map(({ key, label, icon: Icon }) => <button key={key} className={nav === key ? "active" : ""} onClick={() => switchNav(key)}>
          <Icon size={18} /><span>{label}</span>{key === "week" && dashboard?.attention.length ? <em>{dashboard.attention.length}</em> : null}
        </button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className={`system-chip ${health?.status === "ok" ? "ok" : "warning"}`}><HeartPulse size={15} /><span>{health?.status === "ok" ? "系统正常" : "需要检查"}</span></div>
        <button className="theme-toggle" onClick={() => setDark((value) => !value)}>{dark ? <Sun size={17} /> : <Moon size={17} />}<span>{dark ? "浅色模式" : "深色模式"}</span></button>
      </div>
    </aside>
    {mobileNav && <button className="backdrop" aria-label="关闭导航" onClick={() => setMobileNav(false)} />}
    <main>
      <header className="topbar">
        <button className="mobile-menu" onClick={() => setMobileNav(true)}><Menu size={20} /></button>
        <div><span className="crumb">AI Research Workbench</span><strong>{navigation.find((item) => item.key === nav)?.label}</strong></div>
        <div className="topbar-actions"><span className="week-chip"><Clock3 size={14} />{week}</span><button className="icon-button" onClick={() => loadDashboard().catch(showError)} aria-label="刷新"><RefreshCw size={17} /></button></div>
      </header>
      {error && <div className="toast error"><CircleAlert size={18} /><span>{error}</span><button onClick={() => setError("")}><X size={16} /></button></div>}
      <div className={`page page-${nav}`}>
        {nav === "week" && dashboard && <WeekView dashboard={dashboard} busy={busy} ranking={ranking} onOpen={openPaper} onAction={paperAction} onRank={rankWeek} onConfirmPlan={confirmPlan} onUpdatePlan={updatePlan} onDraftPlan={draftPlan} onClusters={proposeClusters} onClusterStatus={setClusterStatus} onApproval={answerApproval} />}
        {nav === "papers" && <PapersView papers={filteredPapers} query={query} setQuery={setQuery} busy={busy} onOpen={openPaper} onAction={paperAction} />}
        {nav === "reading" && <ReadingView paper={selectedPaper} papers={papers} session={session} busy={busy} onOpen={openPaper} onAction={paperAction} setSession={setSession} showError={showError} />}
        {nav === "ideas" && <IdeasView ideas={ideas} busy={busy} onAction={runIdea} />}
        {nav === "projects" && <ProjectsView projects={projects} busy={busy} onSave={saveProject} />}
        {nav === "skills" && <SkillsView skills={skills} query={skillQuery} setQuery={setSkillQuery} onLaunch={launchSkill} />}
        {nav === "runs" && <RunsView runs={runs} syncOverview={syncOverview} onSync={syncRepositories} onResume={async (run) => {
          setBusy(run.run_id); try { await mutate(`/api/runs/${encodeURIComponent(run.run_id)}/resume`, "POST"); setRuns(await get("/api/runs")); } catch (reason) { showError(reason); } finally { setBusy(""); }
        }} busy={busy} />}
      </div>
    </main>
  </div>;
}

function WeekView({ dashboard, busy, ranking, onOpen, onAction, onRank, onConfirmPlan, onUpdatePlan, onDraftPlan, onClusters, onClusterStatus, onApproval }: {
  dashboard: Dashboard; busy: string; ranking: boolean; onOpen: (paper: Paper) => void; onAction: (paper: Paper, action: string, cluster?: string) => void;
  onRank: () => void; onConfirmPlan: (plan: WeeklyPlan) => void; onUpdatePlan: (plan: WeeklyPlan) => void;
  onDraftPlan: () => void; onClusters: () => void; onClusterStatus: (clusterId: string, status: "confirmed" | "dismissed") => void;
  onApproval: (approvalId: string, decision: "accept" | "decline") => void;
}) {
  const [tierFilter, setTierFilter] = useState<TierFilter>(0);
  const rankedTop5 = dashboard.top5
    .map((paper, index) => ({ paper, rank: index + 1 }))
    .filter(({ paper }) => tierFilter === 0 || paper.tier === tierFilter);
  return <div className="dashboard-grid">
    <section className="top5-panel panel">
      <SectionTitle eyebrow="WEEKLY SLATE" title="本周推荐（最多五篇）" action={<button className="secondary" disabled={ranking || !!busy} onClick={onRank}>{ranking ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}{ranking ? "Codex 正在生成" : "Codex 重新排名"}</button>} />
      <div className="slate-note"><span className="status-dot" />{ranking ? "本地 Codex 正在逐篇阅读完整摘要并排名" : dashboard.slate.generated_by === "codex-app-server" && dashboard.slate.ranking_version >= 3 ? "已由本地 Codex 读完摘要后排名并生成理由" : "摘要完整性门槛尚未通过；不会显示标题型预排"}<span>· 完成后自动补位</span></div>
      <TierFilters value={tierFilter} papers={dashboard.top5} onChange={setTierFilter} label="筛选本周推荐" />
      <div className="paper-stack">
        {rankedTop5.length ? rankedTop5.map(({ paper, rank }) => <PaperCard key={paper.paper_id} paper={paper} rank={rank} onOpen={() => onOpen(paper)} onAction={(action) => onAction(paper, action)} busy={busy.startsWith(paper.paper_id)} />) : <Empty title={dashboard.top5.length ? "这个 Tier 暂无推荐" : "尚无合规推荐"} detail={dashboard.top5.length ? "切换到全部或其他 Tier 查看。" : "只有完整摘要已持久化、且由本地 Codex 逐篇读完后，论文才会出现在这里。"} />}
      </div>
    </section>
    <div className="dashboard-side">
      <section className="panel plan-panel">
        <SectionTitle eyebrow="WEEK PLAN" title="这周要完成什么" action={<div className="title-actions"><span className={`plan-status ${dashboard.plan.status}`}>{dashboard.plan.status === "confirmed" ? "已确认" : "草稿"}</span>{dashboard.plan.status === "draft" && <button className="icon-button" title="让 Codex 重拟草稿" disabled={!!busy} onClick={onDraftPlan}>{busy === "draft-plan" ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}</button>}</div>} />
        <div className="capacity"><span>默认容量</span><strong>1 篇精读</strong><span>+</span><strong>最多 2 篇定向</strong></div>
        <div className="task-list">
          {dashboard.plan.tasks.map((task) => <div key={task.task_id} className="task"><input type="checkbox" checked={task.completed} onChange={() => onUpdatePlan({ ...dashboard.plan, tasks: dashboard.plan.tasks.map((item) => item.task_id === task.task_id ? { ...item, completed: !item.completed } : item) })} /><span>{dashboard.plan.status === "draft" ? <select value={task.category} onChange={(event) => onUpdatePlan({ ...dashboard.plan, tasks: dashboard.plan.tasks.map((item) => item.task_id === task.task_id ? { ...item, category: event.target.value } : item) })}><option value="deep">deep</option><option value="targeted">targeted</option><option value="idea">idea</option><option value="workflow">workflow</option><option value="recovery">recovery</option><option value="other">other</option></select> : <em>{task.category}</em>}{task.title}</span>{dashboard.plan.status === "draft" && <button className="icon-button remove-task" aria-label={`删除 ${task.title}`} onClick={() => onUpdatePlan({ ...dashboard.plan, tasks: dashboard.plan.tasks.filter((item) => item.task_id !== task.task_id) })}><X size={14} /></button>}</div>)}
        </div>
        {dashboard.plan.status === "draft" && <button className="primary wide" disabled={busy === "plan"} onClick={() => onConfirmPlan(dashboard.plan)}><Check size={16} />确认本周计划</button>}
        <p className="microcopy">滚动补位不会自动改动已确认计划。</p>
      </section>
      <section className="panel attention-panel">
        <SectionTitle eyebrow="DECISION QUEUE" title="待我决定" />
        {dashboard.attention.length ? dashboard.attention.map((item) => <div className={`attention ${item.severity}`} key={item.attention_id}>
          {item.severity === "error" ? <CircleAlert size={17} /> : <Clock3 size={17} />}<div><strong>{item.title}</strong><p>{item.detail}</p>{item.kind === "decision" && <div className="attention-actions"><button className="primary small" disabled={busy === `approval:${item.related_id}`} onClick={() => onApproval(item.related_id, "accept")}>允许一次</button><button className="ghost small" disabled={busy === `approval:${item.related_id}`} onClick={() => onApproval(item.related_id, "decline")}>拒绝</button></div>}</div>
        </div>) : <div className="all-clear"><CircleCheck size={22} /><div><strong>没有待处理问题</strong><span>运行与数据状态都在预期内。</span></div></div>}
      </section>
      <section className="panel compact-panel">
        <div className="metric"><span>Tracker 健康度</span><strong>{String(dashboard.tracker_health.status || "unknown").toUpperCase()}</strong></div>
        <div className="metric"><span>双轨验证</span><strong>{dashboard.migration.consecutive_successes} / 4 周</strong></div>
      </section>
      <section className="panel clusters-panel">
        <SectionTitle eyebrow="CLUSTERS" title="建议聚类" action={<button className="icon-button" title="让 Codex 重新聚类" disabled={!!busy} onClick={onClusters}>{busy === "clusters" ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}</button>} />
        {dashboard.clusters.filter((cluster) => cluster.status !== "dismissed").slice(0, 3).map((cluster) => <div className="cluster" key={cluster.cluster_id}><Layers3 size={17} /><div><strong>{cluster.question}</strong><span>{cluster.paper_ids.length} 篇 · {cluster.status}</span></div>{cluster.status === "proposed" && <div className="cluster-actions"><button className="icon-button" aria-label="确认聚类" disabled={busy === `cluster:${cluster.cluster_id}`} onClick={() => onClusterStatus(cluster.cluster_id, "confirmed")}><Check size={14} /></button><button className="icon-button" aria-label="忽略聚类" disabled={busy === `cluster:${cluster.cluster_id}`} onClick={() => onClusterStatus(cluster.cluster_id, "dismissed")}><X size={14} /></button></div>}</div>)}
        {!dashboard.clusters.length && <Empty icon={Layers3} title="暂无聚类" detail="候选池形成相邻主题后会自动提出建议。" />}
      </section>
    </div>
  </div>;
}

function PapersView({ papers, query, setQuery, busy, onOpen, onAction }: {
  papers: Paper[]; query: string; setQuery: (value: string) => void; busy: string;
  onOpen: (paper: Paper) => void; onAction: (paper: Paper, action: string) => void;
}) {
  const [visibleCount, setVisibleCount] = useState(40);
  const [statusFilter, setStatusFilter] = useState<"all" | "reading" | "archived" | "backlog">("all");
  const [tierFilter, setTierFilter] = useState<TierFilter>(0);
  const archivedStatuses = new Set(["completed", "completed_full", "completed_rough", "dismissed", "skipped", "expired", "clustered"]);
  const statusPapers = papers.filter((paper) => {
    if (statusFilter === "reading") return paper.status === "in_progress";
    if (statusFilter === "archived") return archivedStatuses.has(paper.status);
    if (statusFilter === "backlog") return paper.status === "backlog";
    return true;
  });
  const filtered = statusPapers.filter((paper) => tierFilter === 0 || paper.tier === tierFilter);
  useEffect(() => setVisibleCount(40), [query, papers.length, statusFilter, tierFilter]);
  const visiblePapers = filtered.slice(0, visibleCount);
  return <section className="panel library-panel">
    <SectionTitle eyebrow="PAPER LIBRARY" title="候选与历史档案" action={<div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索题目、摘要、方法…" /></div>} />
    <div className="filter-row">
      <button className={`filter ${statusFilter === "all" ? "active" : ""}`} onClick={() => setStatusFilter("all")}>全部 <span>{papers.length}</span></button>
      <button className={`filter ${statusFilter === "reading" ? "active" : ""}`} onClick={() => setStatusFilter("reading")}>阅读中 <span>{papers.filter((paper) => paper.status === "in_progress").length}</span></button>
      <button className={`filter ${statusFilter === "archived" ? "active" : ""}`} onClick={() => setStatusFilter("archived")}>已归档 <span>{papers.filter((paper) => archivedStatuses.has(paper.status)).length}</span></button>
      <button className={`filter ${statusFilter === "backlog" ? "active" : ""}`} onClick={() => setStatusFilter("backlog")}>Backlog <span>{papers.filter((paper) => paper.status === "backlog").length}</span></button>
    </div>
    <TierFilters value={tierFilter} papers={statusPapers} onChange={setTierFilter} label="筛选论文库优先级" />
    <div className="paper-table">
      {visiblePapers.map((paper) => <div className="paper-row" key={paper.paper_id}>
        <div className="paper-row-main"><PaperMeta paper={paper} /><button className="title-link" onClick={() => onOpen(paper)}>{paper.title}</button><span>{paper.authors || paper.venue}</span></div>
        <span className={`status status-${paper.status}`}>{statusLabel(paper.status)}</span>
        <div className="row-actions"><button className="ghost small" disabled={busy.startsWith(paper.paper_id)} onClick={() => onAction(paper, "deep")}>开始阅读</button><button className="icon-button" onClick={() => onOpen(paper)}><ChevronRight size={18} /></button></div>
      </div>)}
      {!filtered.length && <Empty title="没有匹配的论文" detail="换一个分类、Tier 或关键词，或检查候选池是否已同步。" />}
      {visibleCount < filtered.length && <button className="secondary load-more" onClick={() => setVisibleCount((count) => count + 40)}>再显示 40 篇 <span>{visibleCount} / {filtered.length}</span></button>}
    </div>
  </section>;
}

function ReadingView({ paper, papers, session, busy, onOpen, onAction, setSession, showError }: {
  paper: Paper | null; papers: Paper[]; session: ReadingSession | null; busy: string; onOpen: (paper: Paper) => void;
  onAction: (paper: Paper, action: string) => void;
  setSession: (session: ReadingSession) => void; showError: (reason: unknown) => void;
}) {
  const [messages, setMessages] = useState<Array<{ kind: string; text: string }>>([]);
  const [draft, setDraft] = useState("");
  const [tierFilter, setTierFilter] = useState<TierFilter>(0);
  useEffect(() => {
    if (!session) return;
    const socket = sessionSocket(session.session_id);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.method === "item/agentMessage/delta" && payload.params?.delta) {
        setMessages((items) => [...items, { kind: "assistant", text: payload.params.delta }]);
      } else if (payload.method === "workbench/approval-required") {
        setMessages((items) => [...items, { kind: "system", text: "这个步骤需要你批准，已加入待决定队列。" }]);
      } else if (payload.method === "workbench/error") {
        setMessages((items) => [...items, { kind: "system", text: payload.params.detail }]);
      }
    };
    return () => socket.close();
  }, [session?.session_id]);
  const readingPapers = papers.filter((item) => item.status === "in_progress");
  const visibleReading = readingPapers.filter((item) => tierFilter === 0 || item.tier === tierFilter);
  const queuePanel = <section className="reading-queue-panel panel">
    <div className="reading-queue-head"><div><span>IN PROGRESS</span><strong>正在阅读</strong></div><TierFilters value={tierFilter} papers={readingPapers} onChange={setTierFilter} label="筛选阅读中论文优先级" /></div>
    <div className="reading-queue-list">
      {visibleReading.map((item) => <button key={item.paper_id} className={`reading-queue-item ${paper?.paper_id === item.paper_id ? "active" : ""}`} onClick={() => onOpen(item)}><span>T{item.tier}</span><strong>{item.title}</strong><em>{statusLabel(item.status)}</em></button>)}
      {!visibleReading.length && <span className="reading-queue-empty">这个 Tier 暂无阅读中的论文。</span>}
    </div>
  </section>;
  if (!paper) return <div className="reading-room-page">{queuePanel}<section className="panel"><Empty icon={BookOpen} title="先选择一篇论文" detail="从“本周”或“论文”打开论文后，这里会保留 PDF、Codex 对话与阅读阶段。" /></section></div>;
  const paperId = paper.paper_id;
  async function sendMessage() {
    if (!session || !draft.trim()) return;
    const text = draft.trim(); setDraft(""); setMessages((items) => [...items, { kind: "user", text }]);
    try { setSession(await mutate(`/api/sessions/${session.session_id}/messages`, "POST", { message: text })); } catch (reason) { showError(reason); }
  }
  async function choosePdf(file?: File) {
    if (!file) return;
    try { setSession(await uploadPdf<ReadingSession>(paperId, file)); } catch (reason) { showError(reason); }
  }
  async function explainCn() {
    try {
      const result = await mutate<{ text: string }>(`/api/papers/${encodeURIComponent(paperId)}/explanation`, "POST");
      setMessages((items) => [...items, { kind: "assistant", text: result.text }]);
    } catch (reason) { showError(reason); }
  }
  const pdfSource = paper.pdf_path ? `/api/papers/${encodeURIComponent(paper.paper_id)}/pdf` : (paper.url.toLowerCase().endsWith(".pdf") ? paper.url : "");
  return <div className="reading-room-page">{queuePanel}<div className="reading-layout">
    <section className="reader panel">
      <div className="reader-head"><div><PaperMeta paper={paper} /><h2>{paper.title}</h2><span>{paper.authors}</span></div>{paper.url && <a className="secondary" href={paper.url} target="_blank" rel="noreferrer">来源 <ArrowRight size={15} /></a>}</div>
      {pdfSource ? <iframe title={paper.title} src={pdfSource} className="pdf-frame" /> : <div className="abstract-view"><div className="abstract-label">PHASE 0 · ABSTRACT PREVIEW</div><h3>Abstract</h3><p>{paper.abstract || "候选池中没有摘要。可以打开来源或选择本地 PDF 后继续。"}</p><div className="abstract-tools"><button className="secondary" onClick={explainCn}><Sparkles size={14} />生成中文解释</button><label className="secondary file-picker"><FileText size={14} />选择本地 PDF<input type="file" accept="application/pdf,.pdf" onChange={(event) => choosePdf(event.target.files?.[0])} /></label></div><div className="missing-pdf"><FileText size={19} /><div><strong>尚未绑定 PDF</strong><span>仍可先完成摘要预览；之后从来源获取开放版本或选择本地文件。</span></div></div></div>}
    </section>
    <section className="conversation panel">
      <div className="conversation-head"><div className="bot-avatar"><Bot size={18} /></div><div><strong>Trevor · Codex</strong><span>{session?.status === "waiting" ? "等待 Codex 登录" : "论文阅读助手"}</span></div><span className="live-dot" /></div>
      <div className="messages">
        {!messages.length && <div className="welcome-message"><Sparkles size={20} /><strong>准备好一起读这篇论文</strong><p>开始阅读后，Codex 会先做 Phase 0 摘要预览，再按你的节奏推进，而不是直接替你总结完。</p></div>}
        {messages.map((message, index) => <div key={index} className={`message ${message.kind}`}>{message.text}</div>)}
      </div>
      <div className="composer"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder={session ? "提问、回答或记录你的判断…" : "先点击右侧“开始精读”建立会话"} disabled={!session} /><button className="primary" onClick={sendMessage} disabled={!session || !draft.trim()}><ArrowRight size={17} /></button></div>
    </section>
    <aside className="reading-state panel">
      <SectionTitle eyebrow="READING STATE" title="阅读进度" />
      <div className="phase-list">{["Phase 0 · 摘要预览", "Phase 1 · 问题与贡献", "Phase 2 · 识别与证据", "Phase 3 · 判断与连接"].map((phase, index) => <div className={`phase ${index === 0 ? "active" : ""}`} key={phase}><span>{index === 0 ? <Play size={12} /> : index + 1}</span><div><strong>{phase}</strong><em>{index === 0 ? (session?.status || "ready") : "尚未开始"}</em></div></div>)}</div>
      {!session && <button className="primary wide" disabled={!!busy} onClick={() => onAction(paper, "deep")}><Play size={16} />开始精读</button>}
      {session && <div className="completion-actions"><button className="primary wide" disabled={!!busy} onClick={() => onAction(paper, "complete-full")}><Archive size={16} />完成并完整归档</button><button className="secondary wide" disabled={!!busy} onClick={() => onAction(paper, "complete-rough")}>粗读完成</button></div>}
      <div className="side-note"><MessageSquareText size={16} /><span>Thread {session?.codex_thread_id ? "已绑定，可恢复" : "尚未创建"}</span></div>
    </aside>
  </div></div>;
}

function IdeasView({ ideas, busy, onAction }: { ideas: Idea[]; busy: string; onAction: (idea: Idea, action: "idea-chat" | "idea-next") => void }) {
  const stages = [
    { key: "capture", label: "捕捉 / S1" },
    { key: "explore", label: "探索 / S2" },
    { key: "question", label: "问题 / S3" },
    { key: "development", label: "数据与发展" },
    { key: "archived", label: "已归档" },
  ];
  function ideaStage(idea: Idea) {
    const status = (idea.stage || idea.status || "capture").toLowerCase();
    if (status === "capture" || status === "interest") return "capture";
    if (status === "explore" || status === "s2") return "explore";
    if (status === "question" || status === "s3") return "question";
    if (status.includes("archive") || status.includes("stop")) return "archived";
    return "development";
  }
  return <div>
    <SectionTitle eyebrow="IDEA PIPELINE" title="研究想法在哪里" />
    <div className="idea-board">
      {stages.map((stage) => {
        const items = ideas.filter((idea) => ideaStage(idea) === stage.key);
        return <section className="idea-column" key={stage.key}><div className="column-head"><span>{stage.label}</span><em>{items.length}</em></div>
          {items.map((idea) => <article className="idea-card" key={idea.slug}><div className="idea-tags"><span>{idea.role || idea.priority || "candidate"}</span>{idea.checkpoint && <span>{idea.checkpoint}</span>}{idea.paused === "true" && <span>paused</span>}</div><h3>{idea.title}</h3><p>{idea.status}</p><div className="card-actions"><button className="ghost small" disabled={busy.startsWith(idea.slug)} onClick={() => onAction(idea, "idea-chat")}><MessageSquareText size={14} />讨论</button><button className="ghost small" disabled={busy.startsWith(idea.slug) || stage.key === "archived"} onClick={() => onAction(idea, "idea-next")}>下一阶段 <ArrowRight size={14} /></button></div></article>)}
          {!items.length && <div className="column-empty">暂无 Idea</div>}
        </section>;
      })}
    </div>
  </div>;
}

function blankProject(): ResearchProject {
  return {
    slug: "", title: "", project_path: "", status: "active", stage: "", summary: "",
    current_focus: "", open_issues: 0, last_sync: "", recent_change: "", zotero_collection: "pending",
  };
}

function ProjectsView({ projects, busy, onSave }: {
  projects: ResearchProject[];
  busy: string;
  onSave: (project: ResearchProject, existingSlug?: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState<ResearchProject | null>(null);
  const [editingSlug, setEditingSlug] = useState("");
  const active = projects.filter((project) => project.status === "active");
  const inactive = projects.filter((project) => project.status !== "active");
  function edit(project?: ResearchProject) {
    setDraft(project ? { ...project } : blankProject());
    setEditingSlug(project?.slug || "");
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!draft) return;
    await onSave(draft, editingSlug);
    setDraft(null);
    setEditingSlug("");
  }
  const cards = (items: ResearchProject[]) => <div className="project-grid">{items.map((project) => <article className="project-card" key={project.slug}>
    <div className="project-card-head"><div><span>{project.slug}</span><h3>{project.title}</h3></div><em className={`project-status status-${project.status}`}>{project.status}</em></div>
    <div className="project-stage">{project.stage || "尚未填写阶段"}</div>
    <p>{project.summary || "尚未填写项目简介。"}</p>
    <div className="project-focus"><strong>现在在做</strong><span>{project.current_focus || project.recent_change || "尚未填写当前重点。"}</span></div>
    <div className="project-meta"><span>Open issues {project.open_issues}</span><span>上次同步 {project.last_sync || "—"}</span></div>
    <div className="project-path">{project.project_path}</div>
    <button className="secondary" disabled={busy.startsWith("project:")} onClick={() => edit(project)}><Pencil size={14} />编辑状态</button>
  </article>)}</div>;
  return <div className="projects-page">
    <SectionTitle eyebrow="ACTIVE PROJECTS" title="正在推进的研究项目" action={<button className="primary" onClick={() => edit()}><Plus size={15} />添加项目</button>} />
    <div className="project-boundary"><FolderKanban size={19} /><div><strong>这里直接使用 Projects vault</strong><span>新增和编辑会写回现有项目索引，因此也能被 project-status、project-sync 和跨电脑 Git 流程继续使用。</span></div></div>
    {active.length ? cards(active) : <Empty icon={FolderKanban} title="还没有进行中的项目" detail="点击“添加项目”，把已有研究目录登记进来。" />}
    {inactive.length > 0 && <section className="inactive-projects"><SectionTitle title="暂停或已完成" />{cards(inactive)}</section>}
    {draft && <div className="project-editor-backdrop" role="presentation" onMouseDown={() => setDraft(null)}>
      <form className="project-editor panel" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
        <div className="project-editor-head"><div><span>PROJECT PROFILE</span><h2>{editingSlug ? "编辑项目" : "添加进行中的项目"}</h2></div><button type="button" className="icon-button" onClick={() => setDraft(null)}><X size={18} /></button></div>
        <div className="project-form-grid">
          <label><span>Slug</span><input required disabled={!!editingSlug} value={draft.slug} onChange={(event) => setDraft({ ...draft, slug: event.target.value.toLowerCase() })} placeholder="major" /></label>
          <label><span>名称</span><input required value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Major / College Program Catalog" /></label>
          <label className="full"><span>本机项目路径</span><input required value={draft.project_path} onChange={(event) => setDraft({ ...draft, project_path: event.target.value })} placeholder="E:\\Binghamton_PhD\\major\\econ-enrollment-project" /></label>
          <label><span>状态</span><select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="active">active</option><option value="paused">paused</option><option value="completed">completed</option><option value="archived">archived</option></select></label>
          <label><span>当前阶段</span><input value={draft.stage} onChange={(event) => setDraft({ ...draft, stage: event.target.value })} placeholder="初稿完成 / 数据搜集" /></label>
          <label className="full"><span>项目简介</span><textarea value={draft.summary} onChange={(event) => setDraft({ ...draft, summary: event.target.value })} placeholder="研究问题、主要 idea 和当前产出。" /></label>
          <label className="full"><span>最近在做什么</span><textarea value={draft.current_focus} onChange={(event) => setDraft({ ...draft, current_focus: event.target.value })} placeholder="例如：继续补 health channel。" /></label>
        </div>
        <div className="project-editor-actions"><button type="button" className="ghost" onClick={() => setDraft(null)}>取消</button><button className="primary" disabled={busy.startsWith("project:")}>{busy.startsWith("project:") ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />}保存到项目库</button></div>
      </form>
    </div>}
  </div>;
}

function SkillsView({ skills, query, setQuery, onLaunch }: { skills: Array<{ name: string; description: string }>; query: string; setQuery: (value: string) => void; onLaunch: (name: string) => void }) {
  const featured = ["paper-reading-tutor", "paper-done", "paper-batch-triage", "idea-chat", "idea-next", "weekly-research-loop"];
  return <div>
    <SectionTitle eyebrow="WORKFLOW LAUNCHER" title="常用研究流程" action={<div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索全部 skills…" /></div>} />
    <div className="featured-grid">{skills.filter((skill) => featured.includes(skill.name)).map((skill) => <article className="workflow-card featured" key={skill.name}><div className="workflow-icon"><Sparkles size={19} /></div><div><h3>{skill.name}</h3><p>{skill.description || "使用现有 AI Research Tools 工作流。"}</p></div><button className="icon-button" title="选择对应对象" onClick={() => onLaunch(skill.name)}><Play size={16} /></button></article>)}</div>
    <section className="panel all-skills"><SectionTitle title="全部已安装流程" /><div className="skill-list">{skills.map((skill) => <div className="skill-row" key={skill.name}><div className="workflow-icon"><GitBranch size={17} /></div><div><strong>{skill.name}</strong><span>{skill.description}</span></div><ChevronRight size={17} /></div>)}</div></section>
  </div>;
}

function syncStatus(repository: GitRepositoryState) {
  if (!repository.available) return "未配置";
  if (repository.state === "dirty") return `${repository.dirty_count} 个未提交改动`;
  if (repository.state === "diverged") return `已分叉 · 本地 +${repository.ahead} / 远端 +${repository.behind}`;
  if (repository.state === "ahead") return `待推送 ${repository.ahead} 个提交`;
  if (repository.state === "behind") return `待拉取 ${repository.behind} 个提交`;
  if (repository.state === "error") return "检查失败";
  return "已同步";
}

function RunsView({ runs, syncOverview, onSync, onResume, busy }: {
  runs: RunReceipt[];
  syncOverview: GitSyncOverview | null;
  onSync: (repositoryIds?: string[]) => void;
  onResume: (run: RunReceipt) => void;
  busy: string;
}) {
  const syncBusy = busy.startsWith("sync:");
  return <div className="runs-layout">
    <section className="panel sync-panel">
      <SectionTitle eyebrow="GITHUB SYNC" title="两台电脑保持一致" action={<button className="primary" disabled={syncBusy || !syncOverview?.repositories.some((repo) => repo.available)} onClick={() => onSync()}>{busy === "sync:all" ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}同步全部</button>} />
      <div className="sync-boundary"><ShieldCheck size={18} /><div><strong>只同步已提交的 Git 内容</strong><span>不会自动提交，也不会同步机器路径、登录凭据、Codex 会话、私人推荐理由、PDF 或工作台本地状态。</span></div></div>
      <div className="sync-grid">
        {syncOverview?.repositories.map((repository) => {
          const blocked = !repository.available || !repository.has_upstream || repository.dirty_count > 0 || repository.state === "diverged";
          return <article className={`sync-repository state-${repository.state}`} key={repository.repository_id}>
            <div className="sync-repo-head"><div><strong>{repository.name}</strong><span>{repository.roles.join(" · ")}</span></div><em>{syncStatus(repository)}</em></div>
            {repository.available && <div className="sync-repo-meta"><span>{repository.branch || "detached"}</span>{repository.remote && <span>{repository.remote}</span>}</div>}
            {repository.last_commit && <p>{repository.last_commit}</p>}
            {(repository.detail || !repository.has_upstream) && <div className="sync-warning">{repository.detail || "没有可同步的 upstream，请先配置 Git remote。"}</div>}
            {repository.sensitive_change_count > 0 && <div className="sync-warning danger">检测到 {repository.sensitive_change_count} 个疑似敏感文件改动；不会自动提交。</div>}
            <button className="secondary wide" disabled={syncBusy || blocked} title={blocked ? "请先处理未提交改动、分叉或 Git remote 配置" : "拉取远端更新并推送本地已提交内容"} onClick={() => onSync([repository.repository_id])}>{busy === `sync:${repository.repository_id}` ? <LoaderCircle className="spin" size={14} /> : <RefreshCw size={14} />}同步这个仓库</button>
          </article>;
        })}
        {!syncOverview && <Empty icon={RefreshCw} title="正在读取 Git 状态" detail="这里只检查预先配置的研究数据仓库。" />}
      </div>
    </section>
    <section className="panel runs-panel">
      <SectionTitle eyebrow="RUN RECEIPTS" title="每一步发生了什么" />
      <div className="run-list">{runs.map((run) => <article className="run" key={`${run.run_type}-${run.run_id}`}><div className={`run-icon ${run.status}`}>{run.status === "succeeded" ? <Check size={17} /> : run.status === "failed" ? <CircleAlert size={17} /> : <LoaderCircle size={17} />}</div><div className="run-main"><div className="run-title"><strong>{run.run_id}</strong><span>{run.run_type}</span><em>{run.status}</em></div><span>{run.started_at}</span>{run.error && <p>{run.error}</p>}{run.steps?.length > 0 && <div className="run-steps">{run.steps.map((step) => <span key={step.name} className={step.status}>{step.name}</span>)}</div>}</div>{run.resumable && <button className="secondary" disabled={busy === run.run_id} onClick={() => onResume(run)}><RefreshCw size={14} />恢复</button>}</article>)}</div>
      {!runs.length && <Empty icon={Activity} title="还没有运行回执" detail="Tracker、Codex 排名、Git 同步和研究流程运行后都会在这里留下可恢复记录。" />}
    </section>
  </div>;
}
