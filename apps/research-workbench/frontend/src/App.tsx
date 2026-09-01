import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, Archive, ArrowRight, BookOpen, Bot, Camera, Check, ChevronRight, CircleAlert,
  CircleCheck, Clock3, FileText, FolderKanban, GitBranch, HeartPulse, Home, Layers3, Lightbulb,
  ListChecks, LoaderCircle, Menu, MessageSquareText, Moon, Pencil, Play, Plus, RefreshCw, Search,
  Save, Settings2, ShieldCheck, Sparkles, Sun, Workflow, X,
} from "lucide-react";
import { bootstrap, get, mutate, paperSegment, sessionSocket, uploadPdf, uploadProjectImage } from "./api";
import { I18nProvider, useI18n, type Language } from "./i18n";
import type {
  Dashboard, GitRepositoryState, GitSyncOverview, GitSyncResponse, Idea, NavKey,
  Paper, ProjectItemStatus, ProjectModule, ProjectWorkspaceView, ReadingSession, ResearchProject, RunReceipt, SkillInfo, Slate, WeeklyPlan,
} from "./types";

function navigationFor(language: Language): Array<{ key: NavKey; label: string; icon: typeof Home }> {
  const labels = language === "zh"
    ? ["本周", "论文", "阅读室", "Ideas", "项目", "流程", "运行记录"]
    : ["This week", "Papers", "Reading room", "Ideas", "Projects", "Workflows", "Run history"];
  return [Home, FileText, BookOpen, Lightbulb, FolderKanban, Workflow, Activity].map((icon, index) => ({
    key: (["week", "papers", "reading", "ideas", "projects", "skills", "runs"] as NavKey[])[index], label: labels[index], icon,
  }));
}

function laneLabel(lane: string, language: Language) {
  const labels: Record<string, [string, string]> = {
    exploit: ["核心方向", "Core"], adjacent: ["相邻方向", "Adjacent"], contradiction: ["反证/挑战", "Challenge"], methodology: ["方法", "Method"],
  };
  return labels[lane]?.[language === "zh" ? 0 : 1] || lane;
}

type TierFilter = 0 | 1 | 2 | 3;

function TierFilters({ value, papers, onChange, label = "" }: {
  value: TierFilter; papers: Paper[]; onChange: (value: TierFilter) => void; label?: string;
}) {
  const { pick } = useI18n();
  return <div className="tier-filter-row" aria-label={label || pick("按优先级筛选", "Filter by priority")}>
    {([0, 1, 2, 3] as TierFilter[]).map((tier) => <button key={tier} className={`filter ${value === tier ? "active" : ""}`} onClick={() => onChange(tier)}>
      {tier === 0 ? pick("全部", "All") : `T${tier}`} <span>{tier === 0 ? papers.length : papers.filter((paper) => paper.tier === tier).length}</span>
    </button>)}
  </div>;
}

function statusLabel(status: string, language: Language) {
  const labels: Record<string, [string, string]> = {
    queued: ["待处理", "Queued"], in_progress: ["阅读中", "Reading"], backlog: ["稍后", "Backlog"], completed: ["已完成", "Completed"],
    skipped: ["已跳过", "Skipped"], clustered: ["仅聚类", "Cluster only"], expired: ["已过期", "Expired"],
  };
  return labels[status]?.[language === "zh" ? 0 : 1] || status;
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
  const { language } = useI18n();
  return <div className="paper-meta">
    <span className={`lane lane-${paper.lane}`}>{laneLabel(paper.lane, language)}</span>
    <span>Tier {paper.tier}</span>
    {paper.methodology && <span>{paper.methodology}</span>}
    {paper.published && <span>{paper.published}</span>}
  </div>;
}

function PaperCard({ paper, rank, onOpen, onAction, busy }: {
  paper: Paper; rank?: number; onOpen: () => void; onAction: (action: string) => void; busy: boolean;
}) {
  const { pick } = useI18n();
  return <article className="paper-card">
    {rank && <div className="rank">{String(rank).padStart(2, "0")}</div>}
    <div className="paper-card-body">
      <PaperMeta paper={paper} />
      <button className="title-link" onClick={onOpen}>{paper.title}</button>
      <div className="authors">{paper.authors || paper.venue || paper.source}</div>
      <p className="reason">{paper.public_reason || paper.relevance_reason || pick("完整摘要尚未完成 Codex 排名。", "Codex ranking is waiting for a complete abstract.")}</p>
      <div className="card-actions">
        <button className="primary small" disabled={busy} onClick={() => onAction("deep")}><Play size={14} />{pick("开始精读", "Deep read")}</button>
        <button className="ghost small" disabled={busy} onClick={() => onAction("targeted")}>{pick("定向阅读", "Targeted read")}</button>
        <button className="ghost small" disabled={busy} onClick={() => onAction("backlog")}>{pick("稍后", "Later")}</button>
        <button className="icon-button" aria-label={pick("查看论文", "View paper")} onClick={onOpen}><ChevronRight size={18} /></button>
      </div>
    </div>
  </article>;
}

export default function App() {
  return <I18nProvider><WorkbenchApp /></I18nProvider>;
}

function ContextSkillBar({ surface, onLaunch }: { surface: string; onLaunch: (name: string) => void }) {
  const { pick } = useI18n();
  const catalog: Record<string, string[]> = {
    weekly: ["weekly-research-loop", "paper-batch-triage"],
    papers: ["paper-batch-triage", "sync-reading-queue"],
    reading: ["paper-reading-tutor", "paper-done", "paper-rough-done"],
    ideas: ["idea-chat", "idea-next", "idea-status"],
    projects: ["project-status", "project-sync", "record-research-reasoning"],
  };
  const items = catalog[surface] || [];
  return <div className="context-skills"><span><Sparkles size={13} />{pick("此处常用", "Useful here")}</span>{items.map((name) => <button key={name} onClick={() => onLaunch(name)}>{name}</button>)}</div>;
}

function WorkbenchApp() {
  const { language, setLanguage, pick } = useI18n();
  const navigation = navigationFor(language);
  const [nav, setNav] = useState<NavKey>("week");
  const [week, setWeek] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [health, setHealth] = useState<Record<string, any> | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [session, setSession] = useState<ReadingSession | null>(null);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
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
    if (nav === "skills") get<SkillInfo[]>(`/api/skills?q=${encodeURIComponent(skillQuery)}&lang=${language}`).then(setSkills).catch(showError);
    if (nav === "runs") Promise.all([
      get<RunReceipt[]>("/api/runs"),
      get<GitSyncOverview>("/api/sync"),
    ]).then(([runData, syncData]) => {
      setRuns(runData);
      setSyncOverview(syncData);
    }).catch(showError);
    if (nav === "ideas") get<Idea[]>("/api/ideas").then(setIdeas).catch(showError);
    if (nav === "projects") get<ResearchProject[]>("/api/projects").then(setProjects).catch(showError);
  }, [nav, week, skillQuery, language]);

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
      let detail = await get<Paper>(`/api/papers/${paperSegment(paper.paper_id)}?week=${week}`);
      setSelectedPaper(detail);
      setNav(destination);
      if (!detail.abstract_ready) {
        setBusy(`abstract:${paper.paper_id}`);
        try {
          detail = await mutate<Paper>(`/api/papers/${paperSegment(paper.paper_id)}/abstract?week=${week}`, "POST");
          setSelectedPaper(detail);
          setPapers((items) => items.map((item) => item.paper_id === detail.paper_id ? detail : item));
        } finally {
          setBusy("");
        }
      }
      try {
        setSession(await get<ReadingSession>(`/api/papers/${paperSegment(paper.paper_id)}/session`));
      } catch {
        setSession(null);
      }
    } catch (reason) { showError(reason); }
  }

  async function paperAction(paper: Paper, action: string, clusterId = "") {
    setBusy(`${paper.paper_id}:${action}`);
    try {
      const result = await mutate<{ paper: Paper; session: ReadingSession | null; slate: Slate }>(
        `/api/papers/${paperSegment(paper.paper_id)}/actions?week=${week}`,
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
    const scope = repositoryIds.length ? pick("这个仓库", "this repository") : pick("所有已配置仓库", "all configured repositories");
    if (!window.confirm(pick(`现在同步${scope}吗？\n\n工作台只会同步已经提交的 Git 内容，不会自动 add 或 commit。`, `Sync ${scope} now?\n\nThe Workbench only transfers committed Git content; it never stages or commits files.`))) return;
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
    if (name === "sync-reading-queue" || name === "paper-rough-done") return switchNav("reading");
    if (name === "idea-status") return switchNav("ideas");
    if (name === "project-status" || name === "project-sync" || name === "record-research-reasoning") return switchNav("projects");
    return switchNav("week");
  }

  const filteredPapers = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return papers;
    return papers.filter((paper) => `${paper.title} ${paper.abstract} ${paper.authors} ${paper.methodology}`.toLocaleLowerCase().includes(needle));
  }, [papers, query]);

  if (loading) return <div className="splash"><div className="brand-mark"><BookOpen /></div><LoaderCircle className="spin" /><span>{pick("正在打开研究工作台…", "Opening Research Workbench…")}</span></div>;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
      <div className="brand"><div className="brand-mark"><BookOpen size={20} /></div><div><strong>Research</strong><span>Workbench</span></div></div>
      <nav>
        {navigation.map(({ key, label, icon: Icon }) => <button key={key} className={nav === key ? "active" : ""} onClick={() => switchNav(key)}>
          <Icon size={18} /><span>{label}</span>{key === "week" && dashboard?.attention.length ? <em>{dashboard.attention.length}</em> : null}
        </button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className={`system-chip ${health?.status === "ok" ? "ok" : "warning"}`}><HeartPulse size={15} /><span>{health?.status === "ok" ? pick("系统正常", "System healthy") : pick("需要检查", "Check required")}</span></div>
        <button className="theme-toggle language-toggle" onClick={() => setLanguage(language === "zh" ? "en" : "zh")}><span className="language-glyph">文</span><span>{language === "zh" ? "English" : "中文"}</span></button>
        <button className="theme-toggle" onClick={() => setDark((value) => !value)}>{dark ? <Sun size={17} /> : <Moon size={17} />}<span>{dark ? pick("浅色模式", "Light mode") : pick("深色模式", "Dark mode")}</span></button>
      </div>
    </aside>
    {mobileNav && <button className="backdrop" aria-label={pick("关闭导航", "Close navigation")} onClick={() => setMobileNav(false)} />}
    <main>
      <header className="topbar">
        <button className="mobile-menu" onClick={() => setMobileNav(true)}><Menu size={20} /></button>
        <div><span className="crumb">AI Research Workbench</span><strong>{navigation.find((item) => item.key === nav)?.label}</strong></div>
        <div className="topbar-actions"><span className="week-chip"><Clock3 size={14} />{week}</span><button className="icon-button" onClick={() => loadDashboard().catch(showError)} aria-label={pick("刷新", "Refresh")}><RefreshCw size={17} /></button></div>
      </header>
      {error && <div className="toast error"><CircleAlert size={18} /><span>{error}</span><button onClick={() => setError("")}><X size={16} /></button></div>}
      <div className={`page page-${nav}`}>
        {nav === "week" && dashboard && <><ContextSkillBar surface="weekly" onLaunch={launchSkill} /><WeekView dashboard={dashboard} busy={busy} ranking={ranking} onOpen={openPaper} onAction={paperAction} onRank={rankWeek} onConfirmPlan={confirmPlan} onUpdatePlan={updatePlan} onDraftPlan={draftPlan} onClusters={proposeClusters} onClusterStatus={setClusterStatus} onApproval={answerApproval} /></>}
        {nav === "papers" && <><ContextSkillBar surface="papers" onLaunch={launchSkill} /><PapersView papers={filteredPapers} query={query} setQuery={setQuery} busy={busy} onOpen={openPaper} onAction={paperAction} /></>}
        {nav === "reading" && <><ContextSkillBar surface="reading" onLaunch={launchSkill} /><ReadingView paper={selectedPaper} papers={papers} session={session} busy={busy} onOpen={openPaper} onAction={paperAction} setSession={setSession} showError={showError} /></>}
        {nav === "ideas" && <><ContextSkillBar surface="ideas" onLaunch={launchSkill} /><IdeasView ideas={ideas} busy={busy} onAction={runIdea} /></>}
        {nav === "projects" && <><ContextSkillBar surface="projects" onLaunch={launchSkill} /><ProjectsView projects={projects} busy={busy} onSave={saveProject} showError={showError} /></>}
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
  const { pick } = useI18n();
  const [tierFilter, setTierFilter] = useState<TierFilter>(0);
  const rankedTop5 = dashboard.top5
    .map((paper, index) => ({ paper, rank: index + 1 }))
    .filter(({ paper }) => tierFilter === 0 || paper.tier === tierFilter);
  return <div className="dashboard-grid">
    <section className="top5-panel panel">
      <SectionTitle eyebrow="WEEKLY SLATE" title={pick("本周推荐（最多五篇）", "Weekly recommendations (up to five)")} action={<button className="secondary" disabled={ranking || !!busy} onClick={onRank}>{ranking ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}{ranking ? pick("Codex 正在生成", "Codex is ranking") : pick("Codex 重新排名", "Rerank with Codex")}</button>} />
      <div className="slate-note"><span className="status-dot" />{ranking ? pick("本地 Codex 正在逐篇阅读完整摘要并排名", "Local Codex is reading every complete abstract before ranking") : dashboard.slate.generated_by === "codex-app-server" && dashboard.slate.ranking_version >= 3 ? pick("已由本地 Codex 读完摘要后排名并生成理由", "Local Codex read the complete abstracts and generated the ranking rationale") : pick("摘要完整性门槛尚未通过；不会显示标题型预排", "The complete-abstract gate has not passed; title-only ranking is hidden")}<span>{pick("· 完成后自动补位", "· Refilled automatically after completion")}</span></div>
      <TierFilters value={tierFilter} papers={dashboard.top5} onChange={setTierFilter} label={pick("筛选本周推荐", "Filter weekly recommendations")} />
      <div className="paper-stack">
        {rankedTop5.length ? rankedTop5.map(({ paper, rank }) => <PaperCard key={paper.paper_id} paper={paper} rank={rank} onOpen={() => onOpen(paper)} onAction={(action) => onAction(paper, action)} busy={busy.startsWith(paper.paper_id)} />) : <Empty title={dashboard.top5.length ? pick("这个 Tier 暂无推荐", "No recommendations in this tier") : pick("尚无合规推荐", "No eligible recommendations")} detail={dashboard.top5.length ? pick("切换到全部或其他 Tier 查看。", "Switch to All or another tier.") : pick("只有完整摘要已持久化、且由本地 Codex 逐篇读完后，论文才会出现在这里。", "A paper appears here only after a complete abstract is saved and read by local Codex.")} />}
      </div>
    </section>
    <div className="dashboard-side">
      <section className="panel plan-panel">
        <SectionTitle eyebrow="WEEK PLAN" title={pick("这周要完成什么", "What to finish this week")} action={<div className="title-actions"><span className={`plan-status ${dashboard.plan.status}`}>{dashboard.plan.status === "confirmed" ? pick("已确认", "Confirmed") : pick("草稿", "Draft")}</span>{dashboard.plan.status === "draft" && <button className="icon-button" title={pick("让 Codex 重拟草稿", "Ask Codex to redraft")} disabled={!!busy} onClick={onDraftPlan}>{busy === "draft-plan" ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}</button>}</div>} />
        <div className="capacity"><span>{pick("默认容量", "Default capacity")}</span><strong>{pick("1 篇精读", "1 deep read")}</strong><span>+</span><strong>{pick("最多 2 篇定向", "up to 2 targeted reads")}</strong></div>
        <div className="task-list">
          {dashboard.plan.tasks.map((task) => <div key={task.task_id} className="task"><input type="checkbox" checked={task.completed} onChange={() => onUpdatePlan({ ...dashboard.plan, tasks: dashboard.plan.tasks.map((item) => item.task_id === task.task_id ? { ...item, completed: !item.completed } : item) })} /><span>{dashboard.plan.status === "draft" ? <select value={task.category} onChange={(event) => onUpdatePlan({ ...dashboard.plan, tasks: dashboard.plan.tasks.map((item) => item.task_id === task.task_id ? { ...item, category: event.target.value } : item) })}><option value="deep">deep</option><option value="targeted">targeted</option><option value="idea">idea</option><option value="workflow">workflow</option><option value="recovery">recovery</option><option value="other">other</option></select> : <em>{task.category}</em>}{task.title}</span>{dashboard.plan.status === "draft" && <button className="icon-button remove-task" aria-label={`${pick("删除", "Delete")} ${task.title}`} onClick={() => onUpdatePlan({ ...dashboard.plan, tasks: dashboard.plan.tasks.filter((item) => item.task_id !== task.task_id) })}><X size={14} /></button>}</div>)}
        </div>
        {dashboard.plan.status === "draft" && <button className="primary wide" disabled={busy === "plan"} onClick={() => onConfirmPlan(dashboard.plan)}><Check size={16} />{pick("确认本周计划", "Confirm weekly plan")}</button>}
        <p className="microcopy">{pick("滚动补位不会自动改动已确认计划。", "Rolling replacements never alter a confirmed plan automatically.")}</p>
      </section>
      <section className="panel attention-panel">
        <SectionTitle eyebrow="DECISION QUEUE" title={pick("待我决定", "Needs my decision")} />
        {dashboard.attention.length ? dashboard.attention.map((item) => <div className={`attention ${item.severity}`} key={item.attention_id}>
          {item.severity === "error" ? <CircleAlert size={17} /> : <Clock3 size={17} />}<div><strong>{item.title}</strong><p>{item.detail}</p>{item.kind === "decision" && <div className="attention-actions"><button className="primary small" disabled={busy === `approval:${item.related_id}`} onClick={() => onApproval(item.related_id, "accept")}>{pick("允许一次", "Allow once")}</button><button className="ghost small" disabled={busy === `approval:${item.related_id}`} onClick={() => onApproval(item.related_id, "decline")}>{pick("拒绝", "Decline")}</button></div>}</div>
        </div>) : <div className="all-clear"><CircleCheck size={22} /><div><strong>{pick("没有待处理问题", "Nothing needs attention")}</strong><span>{pick("运行与数据状态都在预期内。", "Runs and data state look as expected.")}</span></div></div>}
      </section>
      <section className="panel compact-panel">
        <div className="metric"><span>{pick("Tracker 健康度", "Tracker health")}</span><strong>{String(dashboard.tracker_health.status || "unknown").toUpperCase()}</strong></div>
        <div className="metric"><span>{pick("双轨验证", "Dual-track validation")}</span><strong>{dashboard.migration.consecutive_successes} / {pick("4 周", "4 weeks")}</strong></div>
      </section>
      <section className="panel clusters-panel">
        <SectionTitle eyebrow="CLUSTERS" title={pick("建议聚类", "Suggested clusters")} action={<button className="icon-button" title={pick("让 Codex 重新聚类", "Ask Codex to recluster")} disabled={!!busy} onClick={onClusters}>{busy === "clusters" ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}</button>} />
        {dashboard.clusters.filter((cluster) => cluster.status !== "dismissed").slice(0, 3).map((cluster) => <div className="cluster" key={cluster.cluster_id}><Layers3 size={17} /><div><strong>{cluster.question}</strong><span>{cluster.paper_ids.length} {pick("篇", "papers")} · {cluster.status}</span></div>{cluster.status === "proposed" && <div className="cluster-actions"><button className="icon-button" aria-label={pick("确认聚类", "Confirm cluster")} disabled={busy === `cluster:${cluster.cluster_id}`} onClick={() => onClusterStatus(cluster.cluster_id, "confirmed")}><Check size={14} /></button><button className="icon-button" aria-label={pick("忽略聚类", "Dismiss cluster")} disabled={busy === `cluster:${cluster.cluster_id}`} onClick={() => onClusterStatus(cluster.cluster_id, "dismissed")}><X size={14} /></button></div>}</div>)}
        {!dashboard.clusters.length && <Empty icon={Layers3} title={pick("暂无聚类", "No clusters yet")} detail={pick("候选池形成相邻主题后会自动提出建议。", "Suggestions appear when the candidate pool forms adjacent themes.")} />}
      </section>
    </div>
  </div>;
}

function PapersView({ papers, query, setQuery, busy, onOpen, onAction }: {
  papers: Paper[]; query: string; setQuery: (value: string) => void; busy: string;
  onOpen: (paper: Paper) => void; onAction: (paper: Paper, action: string) => void;
}) {
  const { language, pick } = useI18n();
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
    <SectionTitle eyebrow="PAPER LIBRARY" title={pick("候选与历史档案", "Candidates and archive")} action={<div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={pick("搜索题目、摘要、方法…", "Search title, abstract, method…")} /></div>} />
    <div className="filter-row">
      <button className={`filter ${statusFilter === "all" ? "active" : ""}`} onClick={() => setStatusFilter("all")}>{pick("全部", "All")} <span>{papers.length}</span></button>
      <button className={`filter ${statusFilter === "reading" ? "active" : ""}`} onClick={() => setStatusFilter("reading")}>{pick("阅读中", "Reading")} <span>{papers.filter((paper) => paper.status === "in_progress").length}</span></button>
      <button className={`filter ${statusFilter === "archived" ? "active" : ""}`} onClick={() => setStatusFilter("archived")}>{pick("已归档", "Archived")} <span>{papers.filter((paper) => archivedStatuses.has(paper.status)).length}</span></button>
      <button className={`filter ${statusFilter === "backlog" ? "active" : ""}`} onClick={() => setStatusFilter("backlog")}>Backlog <span>{papers.filter((paper) => paper.status === "backlog").length}</span></button>
    </div>
    <TierFilters value={tierFilter} papers={statusPapers} onChange={setTierFilter} label={pick("筛选论文库优先级", "Filter library tier")} />
    <div className="paper-table">
      {visiblePapers.map((paper) => <div className="paper-row" key={paper.paper_id}>
        <div className="paper-row-main"><PaperMeta paper={paper} /><button className="title-link" onClick={() => onOpen(paper)}>{paper.title}</button><span>{paper.authors || paper.venue}</span><em className={`abstract-state ${paper.abstract_ready ? "ready" : "missing"}`}>{paper.abstract_ready ? pick("摘要完整", "Abstract ready") : pick("点击补摘要", "Fetch on open")}</em></div>
        <span className={`status status-${paper.status}`}>{statusLabel(paper.status, language)}</span>
        <div className="row-actions"><button className="ghost small" disabled={busy.startsWith(paper.paper_id)} onClick={() => onAction(paper, "deep")}>{pick("开始阅读", "Start reading")}</button><button className="icon-button" onClick={() => onOpen(paper)}><ChevronRight size={18} /></button></div>
      </div>)}
      {!filtered.length && <Empty title={pick("没有匹配的论文", "No matching papers")} detail={pick("换一个分类、Tier 或关键词，或检查候选池是否已同步。", "Try another category, tier, or keyword, or check candidate-pool sync.")} />}
      {visibleCount < filtered.length && <button className="secondary load-more" onClick={() => setVisibleCount((count) => count + 40)}>{pick("再显示 40 篇", "Show 40 more")} <span>{visibleCount} / {filtered.length}</span></button>}
    </div>
  </section>;
}

function ReadingView({ paper, papers, session, busy, onOpen, onAction, setSession, showError }: {
  paper: Paper | null; papers: Paper[]; session: ReadingSession | null; busy: string; onOpen: (paper: Paper) => void;
  onAction: (paper: Paper, action: string) => void;
  setSession: (session: ReadingSession) => void; showError: (reason: unknown) => void;
}) {
  const { language, pick } = useI18n();
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
        setMessages((items) => [...items, { kind: "system", text: pick("这个步骤需要你批准，已加入待决定队列。", "This step needs your approval and was added to the decision queue.") }]);
      } else if (payload.method === "workbench/error") {
        setMessages((items) => [...items, { kind: "system", text: payload.params.detail }]);
      }
    };
    return () => socket.close();
  }, [session?.session_id]);
  const readingPapers = papers.filter((item) => item.status === "in_progress");
  const visibleReading = readingPapers.filter((item) => tierFilter === 0 || item.tier === tierFilter);
  const queuePanel = <section className="reading-queue-panel panel">
    <div className="reading-queue-head"><div><span>IN PROGRESS</span><strong>{pick("正在阅读", "Currently reading")}</strong></div><TierFilters value={tierFilter} papers={readingPapers} onChange={setTierFilter} label={pick("筛选阅读中论文优先级", "Filter reading queue tier")} /></div>
    <div className="reading-queue-list">
      {visibleReading.map((item) => <button key={item.paper_id} className={`reading-queue-item ${paper?.paper_id === item.paper_id ? "active" : ""}`} onClick={() => onOpen(item)}><span>T{item.tier}</span><strong>{item.title}</strong><em>{statusLabel(item.status, language)}</em></button>)}
      {!visibleReading.length && <span className="reading-queue-empty">{pick("这个 Tier 暂无阅读中的论文。", "No in-progress papers in this tier.")}</span>}
    </div>
  </section>;
  if (!paper) return <div className="reading-room-page">{queuePanel}<section className="panel"><Empty icon={BookOpen} title={pick("先选择一篇论文", "Choose a paper first")} detail={pick("从“本周”或“论文”打开论文后，这里会保留 PDF、Codex 对话与阅读阶段。", "Open a paper from This week or Papers; its PDF, Codex conversation, and reading stage stay here.")} /></section></div>;
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
      const result = await mutate<{ text: string }>(`/api/papers/${paperSegment(paperId)}/explanation`, "POST");
      setMessages((items) => [...items, { kind: "assistant", text: result.text }]);
    } catch (reason) { showError(reason); }
  }
  const pdfSource = paper.pdf_path ? `/api/papers/${paperSegment(paper.paper_id)}/pdf` : (paper.url.toLowerCase().endsWith(".pdf") ? paper.url : "");
  return <div className="reading-room-page">{queuePanel}<div className="reading-layout">
    <section className="reader panel">
      <div className="reader-head"><div><PaperMeta paper={paper} /><h2>{paper.title}</h2><span>{paper.authors}</span></div>{paper.url && <a className="secondary" href={paper.url} target="_blank" rel="noreferrer">{pick("来源", "Source")} <ArrowRight size={15} /></a>}</div>
      <div className={`abstract-view ${pdfSource ? "with-pdf" : ""}`}><div className="abstract-label">PHASE 0 · ABSTRACT</div><div className="abstract-title-row"><h3>Abstract</h3><em className={`abstract-state ${paper.abstract_ready ? "ready" : "missing"}`}>{paper.abstract_ready ? pick("完整摘要", "Complete abstract") : pick("摘要待补", "Abstract missing")}</em></div><p>{paper.abstract || (busy === `abstract:${paper.paper_id}` ? pick("正在从官方公开元数据源获取完整摘要…", "Fetching the complete abstract from public scholarly metadata…") : pick("Gmail 周报和当前官方元数据源尚未提供可验证的完整摘要；这里不会用标题或截断文本代替。", "The Gmail digest and current public metadata sources have not yielded a verifiable complete abstract; the Workbench will not substitute the title or truncated text."))}</p><div className="abstract-tools"><button className="secondary" onClick={explainCn} disabled={!paper.abstract_ready}><Sparkles size={14} />{pick("生成中文解释", "Explain in Chinese")}</button>{!paper.abstract_ready && <button className="secondary" onClick={() => onOpen(paper)} disabled={busy === `abstract:${paper.paper_id}`}><RefreshCw size={14} />{pick("重试官方摘要", "Retry official abstract")}</button>}<label className="secondary file-picker"><FileText size={14} />{pick("选择本地 PDF", "Choose local PDF")}<input type="file" accept="application/pdf,.pdf" onChange={(event) => choosePdf(event.target.files?.[0])} /></label></div></div>
      {pdfSource ? <iframe title={paper.title} src={pdfSource} className="pdf-frame" /> : <div className="missing-pdf"><FileText size={19} /><div><strong>{pick("尚未绑定 PDF", "No PDF attached")}</strong><span>{pick("摘要与 PDF 分开保存；之后可从来源获取开放版本或选择本地文件。", "Abstract and PDF are stored separately; obtain an open version later or choose a local file.")}</span></div></div>}
    </section>
    <section className="conversation panel">
      <div className="conversation-head"><div className="bot-avatar"><Bot size={18} /></div><div><strong>Trevor · Codex</strong><span>{session?.status === "waiting" ? pick("等待 Codex 登录", "Waiting for Codex sign-in") : pick("论文阅读助手", "Paper reading tutor")}</span></div><span className="live-dot" /></div>
      <div className="messages">
        {!messages.length && <div className="welcome-message"><Sparkles size={20} /><strong>{pick("准备好一起读这篇论文", "Ready to read this paper together")}</strong><p>{pick("开始阅读后，Codex 会先做 Phase 0 摘要预览，再按你的节奏推进，而不是直接替你总结完。", "Codex begins with the Phase 0 abstract preview and advances at your pace instead of replacing the reading with a summary.")}</p></div>}
        {messages.map((message, index) => <div key={index} className={`message ${message.kind}`}>{message.text}</div>)}
      </div>
      <div className="composer"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder={session ? pick("提问、回答或记录你的判断…", "Ask, answer, or record your judgment…") : pick("先点击右侧“开始精读”建立会话", "Start a deep read to create a session")} disabled={!session} /><button className="primary" onClick={sendMessage} disabled={!session || !draft.trim()}><ArrowRight size={17} /></button></div>
    </section>
    <aside className="reading-state panel">
      <SectionTitle eyebrow="READING STATE" title={pick("阅读进度", "Reading progress")} />
      <div className="phase-list">{(language === "zh" ? ["Phase 0 · 摘要预览", "Phase 1 · 问题与贡献", "Phase 2 · 识别与证据", "Phase 3 · 判断与连接"] : ["Phase 0 · Abstract preview", "Phase 1 · Question and contribution", "Phase 2 · Identification and evidence", "Phase 3 · Judgment and connections"]).map((phase, index) => <div className={`phase ${index === 0 ? "active" : ""}`} key={phase}><span>{index === 0 ? <Play size={12} /> : index + 1}</span><div><strong>{phase}</strong><em>{index === 0 ? (session?.status || "ready") : pick("尚未开始", "Not started")}</em></div></div>)}</div>
      {!session && <button className="primary wide" disabled={!!busy} onClick={() => onAction(paper, "deep")}><Play size={16} />{pick("开始精读", "Start deep read")}</button>}
      {session && <div className="completion-actions"><button className="primary wide" disabled={!!busy} onClick={() => onAction(paper, "complete-full")}><Archive size={16} />{pick("完成并完整归档", "Complete and archive")}</button><button className="secondary wide" disabled={!!busy} onClick={() => onAction(paper, "complete-rough")}>{pick("粗读完成", "Rough read complete")}</button></div>}
      <div className="side-note"><MessageSquareText size={16} /><span>Thread {session?.codex_thread_id ? pick("已绑定，可恢复", "bound and resumable") : pick("尚未创建", "not created")}</span></div>
    </aside>
  </div></div>;
}

function IdeasView({ ideas, busy, onAction }: { ideas: Idea[]; busy: string; onAction: (idea: Idea, action: "idea-chat" | "idea-next") => void }) {
  const { language, pick } = useI18n();
  const stages = language === "zh" ? [
    { key: "capture", label: "捕捉 / S1" }, { key: "explore", label: "探索 / S2" }, { key: "question", label: "问题 / S3" },
    { key: "development", label: "数据与发展" }, { key: "archived", label: "已归档" },
  ] : [
    { key: "capture", label: "Capture / S1" }, { key: "explore", label: "Explore / S2" }, { key: "question", label: "Question / S3" },
    { key: "development", label: "Data and development" }, { key: "archived", label: "Archived" },
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
    <SectionTitle eyebrow="IDEA PIPELINE" title={pick("研究想法在哪里", "Where research ideas stand")} />
    <div className="idea-board">
      {stages.map((stage) => {
        const items = ideas.filter((idea) => ideaStage(idea) === stage.key);
        return <section className="idea-column" key={stage.key}><div className="column-head"><span>{stage.label}</span><em>{items.length}</em></div>
          {items.map((idea) => <article className="idea-card" key={idea.slug}><div className="idea-tags"><span>{idea.role || idea.priority || "candidate"}</span>{idea.checkpoint && <span>{idea.checkpoint}</span>}{idea.paused === "true" && <span>paused</span>}</div><h3>{idea.title}</h3><p>{idea.status}</p><div className="card-actions"><button className="ghost small" disabled={busy.startsWith(idea.slug)} onClick={() => onAction(idea, "idea-chat")}><MessageSquareText size={14} />{pick("讨论", "Discuss")}</button><button className="ghost small" disabled={busy.startsWith(idea.slug) || stage.key === "archived"} onClick={() => onAction(idea, "idea-next")}>{pick("下一阶段", "Next stage")} <ArrowRight size={14} /></button></div></article>)}
          {!items.length && <div className="column-empty">{pick("暂无 Idea", "No ideas")}</div>}
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

function ProjectsView({ projects, busy, onSave, showError }: {
  projects: ResearchProject[];
  busy: string;
  onSave: (project: ResearchProject, existingSlug?: string) => Promise<void>;
  showError: (reason: unknown) => void;
}) {
  const { language, pick } = useI18n();
  const [draft, setDraft] = useState<ResearchProject | null>(null);
  const [editingSlug, setEditingSlug] = useState("");
  const [selected, setSelected] = useState<ProjectWorkspaceView | null>(null);
  const [modules, setModules] = useState<ProjectModule[]>([]);
  const [chatDraft, setChatDraft] = useState("");
  const [noteDraft, setNoteDraft] = useState("");
  const [workspaceBusy, setWorkspaceBusy] = useState("");
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

  async function openWorkspace(project: ResearchProject) {
    setWorkspaceBusy("open");
    try {
      const [view, moduleData] = await Promise.all([
        get<ProjectWorkspaceView>(`/api/projects/${encodeURIComponent(project.slug)}/workspace`),
        get<ProjectModule[]>("/api/project-modules"),
      ]);
      setSelected(view);
      setModules(moduleData);
    }
    catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  async function sendProjectMessage(message = chatDraft) {
    if (!selected || !message.trim()) return;
    const text = message.trim();
    setChatDraft("");
    setWorkspaceBusy("chat");
    try { setSelected(await mutate<ProjectWorkspaceView>(`/api/projects/${encodeURIComponent(selected.project.slug)}/messages`, "POST", { message: text })); }
    catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  async function refreshWorkspace() {
    if (!selected) return;
    setWorkspaceBusy("refresh");
    try { setSelected(await mutate<ProjectWorkspaceView>(`/api/projects/${encodeURIComponent(selected.project.slug)}/refresh`, "POST")); }
    catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  async function setItemStatus(itemId: string, status: ProjectItemStatus) {
    if (!selected) return;
    setWorkspaceBusy(`item:${itemId}`);
    try { setSelected(await mutate<ProjectWorkspaceView>(`/api/projects/${encodeURIComponent(selected.project.slug)}/workspace/items/${encodeURIComponent(itemId)}`, "PATCH", { status })); }
    catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  async function saveNote() {
    if (!selected || !noteDraft.trim()) return;
    setWorkspaceBusy("note");
    try {
      setSelected(await mutate<ProjectWorkspaceView>(`/api/projects/${encodeURIComponent(selected.project.slug)}/notes`, "POST", { text: noteDraft.trim(), ask_codex: true }));
      setNoteDraft("");
    } catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  async function uploadNoteImage(file: File) {
    if (!selected) return;
    setWorkspaceBusy("image");
    try { setSelected(await uploadProjectImage<ProjectWorkspaceView>(selected.project.slug, file, noteDraft.trim())); setNoteDraft(""); }
    catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  async function applyModule(moduleId: string) {
    if (!selected) return;
    setWorkspaceBusy(`module:${moduleId}`);
    try { setSelected(await mutate<ProjectWorkspaceView>(`/api/projects/${encodeURIComponent(selected.project.slug)}/modules/apply`, "POST", { module_id: moduleId })); }
    catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  async function saveModule(sectionId: string) {
    if (!selected) return;
    setWorkspaceBusy(`save-module:${sectionId}`);
    try {
      const created = await mutate<ProjectModule>(`/api/projects/${encodeURIComponent(selected.project.slug)}/modules`, "POST", { section_id: sectionId });
      setModules((items) => [...items, created]);
    } catch (reason) { showError(reason); }
    finally { setWorkspaceBusy(""); }
  }

  const projectStatus = (status: string) => ({ active: pick("进行中", "Active"), paused: pick("暂停", "Paused"), completed: pick("完成", "Completed"), archived: pick("归档", "Archived") } as Record<string, string>)[status] || status;
  const boardStatus = (status: ProjectItemStatus) => ({
    todo: pick("待开始", "To do"), in_progress: pick("进行中", "In progress"), waiting_human: pick("等我处理", "Waiting for me"),
    waiting_ai: pick("等 Codex", "Waiting for Codex"), done: pick("已完成", "Done"), blocked: pick("阻塞", "Blocked"),
  } as Record<ProjectItemStatus, string>)[status];
  const projectText = (value: string) => {
    const [zh, en] = value.split("|||");
    return pick(zh, en || zh);
  };

  const cards = (items: ResearchProject[]) => <div className="project-grid">{items.map((project) => <article className="project-card" key={project.slug}>
    <div className="project-card-head"><div><span>{project.slug}</span><h3>{project.title}</h3></div><em className={`project-status status-${project.status}`}>{projectStatus(project.status)}</em></div>
    <div className="project-stage">{project.stage || pick("尚未填写阶段", "Stage not set")}</div>
    <p>{project.summary || pick("尚未填写项目简介。", "Project summary not set.")}</p>
    <div className="project-focus"><strong>{pick("现在在做", "Current focus")}</strong><span>{project.current_focus || project.recent_change || pick("尚未填写当前重点。", "Current focus not set.")}</span></div>
    <div className="project-meta"><span>Open issues {project.open_issues}</span><span>{pick("上次同步", "Last sync")} {project.last_sync || "—"}</span></div>
    <div className="project-path">{project.project_path}</div>
    <div className="project-card-actions"><button className="primary" disabled={workspaceBusy === "open"} onClick={() => openWorkspace(project)}><FolderKanban size={14} />{pick("打开项目工作区", "Open workspace")}</button><button className="secondary" disabled={busy.startsWith("project:")} onClick={() => edit(project)}><Pencil size={14} />{pick("编辑状态", "Edit profile")}</button></div>
  </article>)}</div>;

  if (selected) return <div className="project-workspace-page">
    <div className="project-workspace-header">
      <button className="secondary" onClick={() => setSelected(null)}><ArrowRight className="back-arrow" size={15} />{pick("返回项目列表", "Back to projects")}</button>
      <div><span>{selected.project.slug}</span><h2>{selected.project.title}</h2><p>{selected.project.current_focus}</p></div>
      <div className="title-actions"><button className="secondary" onClick={() => edit(selected.project)}><Pencil size={14} />{pick("项目资料", "Project profile")}</button><button className="primary" disabled={!!workspaceBusy} onClick={refreshWorkspace}>{workspaceBusy === "refresh" ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}{pick("让 Codex 刷新项目状态", "Refresh project with Codex")}</button></div>
    </div>
    <div className="project-workspace-note"><Bot size={18} /><div><strong>{pick("每个项目有自己的板块", "Each project has its own board")}</strong><span>{pick("在右侧直接告诉 Codex 要增加、删除或重排什么；它只更新这个项目的 workspace，不会擅自改研究文件。", "Tell Codex what to add, remove, or rearrange. It updates only this project's workspace and does not silently edit research files.")}</span></div></div>
    <section className="project-notebook panel">
      <div className="project-notebook-head"><div><span>PROJECT NOTEBOOK</span><h3>{pick("把老板指令、临时想法或手写纸先扔进来", "Drop advisor instructions, rough thoughts, or handwritten notes here")}</h3><p>{pick("Codex 会先复述理解，再拆成板块；照片只保存在本机工作台状态中，不进入 Git。", "Codex restates its understanding before changing the board. Photos stay in local Workbench state and are not added to Git.")}</p></div><em>{selected.workspace.notes.length} {pick("条记录", "notes")}</em></div>
      <div className="project-note-input"><textarea value={noteDraft} onChange={(event) => setNoteDraft(event.target.value)} placeholder={pick("例如：这周用现有 A×B 表设计一张图；具体图形还没定…", "For example: this week, design a figure from the existing A×B table; the visual form is not decided yet…")} /><div><label className="secondary file-picker"><Camera size={14} />{workspaceBusy === "image" ? pick("正在读取…", "Reading…") : pick("上传手写/草稿图", "Upload handwritten note")}<input type="file" accept="image/png,image/jpeg,image/webp" disabled={!!workspaceBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) uploadNoteImage(file); event.currentTarget.value = ""; }} /></label><button className="primary" disabled={!noteDraft.trim() || !!workspaceBusy} onClick={saveNote}>{workspaceBusy === "note" ? <LoaderCircle className="spin" size={14} /> : <ArrowRight size={14} />}{pick("记下并交给 Codex", "Save and send to Codex")}</button></div></div>
      {selected.workspace.notes.length > 0 && <details className="project-note-history"><summary>{pick("查看最近记录", "View recent notes")}</summary>{selected.workspace.notes.slice().reverse().map((note) => <div key={note.note_id}><span>{note.source_type === "image" ? pick("图片", "Image") : pick("文字", "Text")} · {note.created_at}</span><p>{note.text}</p></div>)}</details>}
    </section>
    <section className="project-modules panel"><div className="project-modules-head"><div><span>REUSABLE MODULES</span><h3>{pick("调用以前做过的协作模块", "Reuse a proven collaboration module")}</h3></div><p>{pick("复制进来后只改这个项目的内容；不会反向修改模板。", "Applying a module creates a project-specific copy and never mutates the template.")}</p></div><div className="project-module-list">{modules.map((module) => <button key={module.module_id} disabled={!!workspaceBusy} onClick={() => applyModule(module.module_id)}><strong>{projectText(module.title)}</strong><span>{projectText(module.description)}</span><em>+ {pick("加入这个项目", "Add to project")}</em></button>)}</div></section>
    <div className="project-workspace-layout">
      <section className="project-board">
        {selected.workspace.sections.map((section) => <article className={`project-board-section kind-${section.kind}`} key={section.section_id}>
          <div className="project-section-head"><div><span>{section.kind}</span><h3>{projectText(section.title)}</h3></div><div><button className="icon-button" title={pick("保存为以后可复用的模块", "Save as a reusable module")} disabled={!!workspaceBusy} onClick={() => saveModule(section.section_id)}><Save size={14} /></button><em>{section.items.filter((item) => item.status === "done").length}/{section.items.length}</em></div></div>
          {section.summary && <p>{projectText(section.summary)}</p>}
          <div className="project-board-items">{section.items.map((item) => <div className={`project-board-item item-${item.status}`} key={item.item_id}>
            <div className="project-item-top"><em>{boardStatus(item.status)}</em><strong>{projectText(item.title)}</strong></div>
            {item.detail && <p>{projectText(item.detail)}</p>}
            {item.source_path && <code>{item.source_path}</code>}
            <div className="project-item-actions"><button className="ghost small" disabled={!!workspaceBusy} onClick={() => sendProjectMessage(language === "zh" ? `请根据项目证据和我一起处理“${projectText(item.title)}”。先告诉我需要人工做什么、你会做什么；不要把未验证事项标成完成。` : `Help me work through “${projectText(item.title)}” using the project evidence. Separate what I must validate from what Codex can do, and do not mark unverified work complete.`)}><MessageSquareText size={13} />{item.action_label ? projectText(item.action_label) : pick("和 Codex 处理", "Work with Codex")}</button><button className="secondary small" disabled={workspaceBusy === `item:${item.item_id}`} onClick={() => setItemStatus(item.item_id, item.status === "done" ? "todo" : "done")}>{item.status === "done" ? pick("重新打开", "Reopen") : pick("标记完成", "Mark done")}</button></div>
          </div>)}</div>
        </article>)}
      </section>
      <aside className="project-chat panel">
        <div className="conversation-head"><div className="bot-avatar"><Bot size={18} /></div><div><strong>Project Codex</strong><span>{selected.session.codex_thread_id ? pick("对话已绑定，可恢复", "Conversation is bound and resumable") : pick("首次发送后建立可恢复对话", "A resumable conversation starts with your first message")}</span></div><span className="live-dot" /></div>
        <div className="project-chat-prompts"><button onClick={() => sendProjectMessage(pick("$project-status 请先根据现有证据告诉我：这个项目现在正式完成了什么、临时做了什么、下一步最需要我决定什么？", "$project-status Based on current evidence, tell me what is formally complete, what is temporary, and what most needs my decision next."))}>project-status</button><button onClick={() => sendProjectMessage(pick("$project-sync 读取项目最近变化，并建议这个工作台板块应如何更新；不要擅自写研究文件。", "$project-sync Read recent project changes and suggest how this workspace should update; do not edit research files."))}>project-sync</button><button onClick={() => setChatDraft(pick("请把这个项目的板块调整成：", "Please redesign this project's board as follows:"))}>{pick("调整板块", "Redesign board")}</button></div>
        <div className="messages project-messages">{selected.session.messages.length ? selected.session.messages.map((message, index) => <div key={`${message.at}-${index}`} className={`message ${message.role}`}>{message.text}</div>) : <div className="welcome-message"><Sparkles size={20} /><strong>{pick("直接说你想怎么推进这个项目", "Describe how you want to run this project")}</strong><p>{pick("例如：把 Major 改成人工验证队列 + 两个数据状态；或让 Welfare 显示底稿、health channel、实验和导师汇报。", "For example: make Major a human-validation queue plus two dataset checks, or show Welfare's draft, health channel, experiments, and advisor updates.")}</p></div>}</div>
        <div className="composer"><textarea value={chatDraft} onChange={(event) => setChatDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendProjectMessage(); } }} placeholder={pick("告诉 Codex 这个项目要怎么推进，或要怎么改板块…", "Tell Codex how to run this project or change its board…")} /><button className="primary" onClick={() => sendProjectMessage()} disabled={!chatDraft.trim() || workspaceBusy === "chat"}>{workspaceBusy === "chat" ? <LoaderCircle className="spin" size={16} /> : <ArrowRight size={17} />}</button></div>
      </aside>
    </div>
    {draft && projectEditor()}
  </div>;

  function projectEditor() {
    if (!draft) return null;
    return <div className="project-editor-backdrop" role="presentation" onMouseDown={() => setDraft(null)}>
      <form className="project-editor panel" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
        <div className="project-editor-head"><div><span>PROJECT PROFILE</span><h2>{editingSlug ? pick("编辑项目", "Edit project") : pick("添加进行中的项目", "Add active project")}</h2></div><button type="button" className="icon-button" onClick={() => setDraft(null)}><X size={18} /></button></div>
        <div className="project-form-grid">
          <label><span>Slug</span><input required disabled={!!editingSlug} value={draft.slug} onChange={(event) => setDraft({ ...draft, slug: event.target.value.toLowerCase() })} placeholder="major" /></label>
          <label><span>{pick("名称", "Name")}</span><input required value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Major / College Program Catalog" /></label>
          <label className="full"><span>{pick("本机项目路径", "Local project path")}</span><input required value={draft.project_path} onChange={(event) => setDraft({ ...draft, project_path: event.target.value })} placeholder="E:\\Binghamton_PhD\\major\\econ-enrollment-project" /></label>
          <label><span>{pick("状态", "Status")}</span><select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="active">active</option><option value="paused">paused</option><option value="completed">completed</option><option value="archived">archived</option></select></label>
          <label><span>{pick("当前阶段", "Current stage")}</span><input value={draft.stage} onChange={(event) => setDraft({ ...draft, stage: event.target.value })} placeholder={pick("初稿完成 / 数据搜集", "Draft complete / data collection")} /></label>
          <label className="full"><span>{pick("项目简介", "Project summary")}</span><textarea value={draft.summary} onChange={(event) => setDraft({ ...draft, summary: event.target.value })} placeholder={pick("研究问题、主要 idea 和当前产出。", "Research question, main idea, and current outputs.")} /></label>
          <label className="full"><span>{pick("最近在做什么", "Current focus")}</span><textarea value={draft.current_focus} onChange={(event) => setDraft({ ...draft, current_focus: event.target.value })} placeholder={pick("例如：继续补 health channel。", "For example: continue the health channel.")} /></label>
        </div>
        <div className="project-editor-actions"><button type="button" className="ghost" onClick={() => setDraft(null)}>{pick("取消", "Cancel")}</button><button className="primary" disabled={busy.startsWith("project:")}>{busy.startsWith("project:") ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />}{pick("保存到项目库", "Save to project vault")}</button></div>
      </form>
    </div>;
  }

  return <div className="projects-page">
    <SectionTitle eyebrow="ACTIVE PROJECTS" title={pick("正在推进的研究项目", "Active research projects")} action={<button className="primary" onClick={() => edit()}><Plus size={15} />{pick("添加项目", "Add project")}</button>} />
    <div className="project-boundary"><FolderKanban size={19} /><div><strong>{pick("项目资料与专属工作区分开保存", "Project profile and workspace are stored separately")}</strong><span>{pick("项目索引继续兼容 project-status/project-sync；每个项目的板块和 Codex 对话则独立保存并可跨电脑同步。", "The project index stays compatible with project-status/project-sync; each board is saved independently and can sync across computers.")}</span></div></div>
    {active.length ? cards(active) : <Empty icon={FolderKanban} title={pick("还没有进行中的项目", "No active projects")} detail={pick("点击“添加项目”，把已有研究目录登记进来。", "Add an existing research directory to begin.")} />}
    {inactive.length > 0 && <section className="inactive-projects"><SectionTitle title={pick("暂停或已完成", "Paused or completed")} />{cards(inactive)}</section>}
    {draft && projectEditor()}
  </div>;
}

function SkillsView({ skills, query, setQuery, onLaunch }: { skills: SkillInfo[]; query: string; setQuery: (value: string) => void; onLaunch: (name: string) => void }) {
  const { pick } = useI18n();
  const [selectedSkill, setSelectedSkill] = useState<SkillInfo | null>(null);
  const featured = ["paper-reading-tutor", "paper-done", "paper-batch-triage", "idea-chat", "idea-next", "weekly-research-loop"];
  return <div>
    <SectionTitle eyebrow="WORKFLOW LAUNCHER" title={pick("常用研究流程", "Common research workflows")} action={<div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={pick("搜索全部 skills…", "Search all skills…")} /></div>} />
    <div className="featured-grid">{skills.filter((skill) => featured.includes(skill.name)).map((skill) => <article className="workflow-card featured" key={skill.name} onClick={() => setSelectedSkill(skill)}><div className="workflow-icon"><Sparkles size={19} /></div><div><span>{skill.name}</span><h3>{skill.title}</h3><p>{skill.description || pick("使用现有 AI Research Tools 工作流。", "Use the installed AI Research Tools workflow.")}</p></div><button className="icon-button" title={pick("打开适用页面", "Open relevant page")} onClick={(event) => { event.stopPropagation(); onLaunch(skill.name); }}><Play size={16} /></button></article>)}</div>
    <section className="panel all-skills"><SectionTitle title={pick("全部已安装流程", "All installed workflows")} /><div className="skill-list">{skills.map((skill) => <button className="skill-row" key={skill.name} onClick={() => setSelectedSkill(skill)}><div className="workflow-icon"><GitBranch size={17} /></div><div><strong>{skill.title || skill.name}</strong><em>{skill.name}</em><span>{skill.description}</span></div><ChevronRight size={17} /></button>)}</div></section>
    {selectedSkill && <div className="project-editor-backdrop" role="presentation" onMouseDown={() => setSelectedSkill(null)}><section className="skill-detail panel" onMouseDown={(event) => event.stopPropagation()}><div className="project-editor-head"><div><span>SKILL DETAIL</span><h2>{selectedSkill.title || selectedSkill.name}</h2></div><button className="icon-button" onClick={() => setSelectedSkill(null)}><X size={18} /></button></div><code>{selectedSkill.name}</code><p>{selectedSkill.description}</p>{selectedSkill.applies_to.length > 0 && <div className="skill-applies"><strong>{pick("适合放在", "Useful in")}</strong>{selectedSkill.applies_to.map((item) => <span key={item}>{item}</span>)}</div>}<div className="project-editor-actions"><button className="primary" onClick={() => { onLaunch(selectedSkill.name); setSelectedSkill(null); }}><Play size={15} />{pick("打开适用页面", "Open relevant page")}</button></div></section></div>}
  </div>;
}

function syncStatus(repository: GitRepositoryState, language: Language) {
  const zh = language === "zh";
  if (!repository.available) return zh ? "未配置" : "Not configured";
  if (repository.state === "dirty") return zh ? `${repository.dirty_count} 个未提交改动` : `${repository.dirty_count} uncommitted changes`;
  if (repository.state === "diverged") return zh ? `已分叉 · 本地 +${repository.ahead} / 远端 +${repository.behind}` : `Diverged · local +${repository.ahead} / remote +${repository.behind}`;
  if (repository.state === "ahead") return zh ? `待推送 ${repository.ahead} 个提交` : `${repository.ahead} commits to push`;
  if (repository.state === "behind") return zh ? `待拉取 ${repository.behind} 个提交` : `${repository.behind} commits to pull`;
  if (repository.state === "error") return zh ? "检查失败" : "Check failed";
  return zh ? "已同步" : "Synced";
}

function RunsView({ runs, syncOverview, onSync, onResume, busy }: {
  runs: RunReceipt[];
  syncOverview: GitSyncOverview | null;
  onSync: (repositoryIds?: string[]) => void;
  onResume: (run: RunReceipt) => void;
  busy: string;
}) {
  const { language, pick } = useI18n();
  const localizedScope = (value: string) => {
    const [zh, en] = value.split("|||");
    return pick(zh, en || zh);
  };
  const syncBusy = busy.startsWith("sync:");
  return <div className="runs-layout">
    <section className="panel sync-panel">
      <SectionTitle eyebrow="GITHUB SYNC" title={pick("两台电脑保持一致", "Keep both computers aligned")} action={<button className="primary" disabled={syncBusy || !syncOverview?.repositories.some((repo) => repo.available)} onClick={() => onSync()}>{busy === "sync:all" ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}{pick("同步全部", "Sync all")}</button>} />
      <div className="sync-boundary"><ShieldCheck size={18} /><div><strong>{pick("只同步已提交的 Git 内容", "Only committed Git content is transferred")}</strong><span>{pick("不会自动提交。AI Education 的论文笔记会同步，PDF 不同步；Obsidian 的 Ideas、知识库和 Projects 通过同一个私人仓库同步。", "Nothing is committed automatically. AI Education paper notes sync, PDFs do not; Obsidian Ideas, knowledge, and Projects share one private repository.")}</span></div></div>
      <div className="sync-grid">
        {syncOverview?.repositories.map((repository) => {
          const blocked = !repository.available || !repository.has_upstream || repository.dirty_count > 0 || repository.state === "diverged";
          return <article className={`sync-repository state-${repository.state}`} key={repository.repository_id}>
            <div className="sync-repo-head"><div><strong>{repository.name}</strong><span>{repository.roles.join(" · ")}</span></div><em>{syncStatus(repository, language)}</em></div>
            {repository.available && <div className="sync-repo-meta"><span>{repository.branch || "detached"}</span>{repository.remote && <span>{repository.remote}</span>}</div>}
            {repository.last_commit && <p>{repository.last_commit}</p>}
            <div className="sync-counts"><span>{pick("已跟踪", "Tracked")} <strong>{repository.tracked_count}</strong></span><span>{pick("未跟踪", "Untracked")} <strong>{repository.untracked_count}</strong></span><span>{pick("已忽略", "Ignored")} <strong>{repository.ignored_count}</strong></span><span>PDF <strong>{repository.tracked_pdf_count}</strong></span></div>
            <details className="sync-scope"><summary>{pick("具体同步什么", "What exactly syncs")}</summary><div><strong>{pick("包含", "Included")}</strong><ul>{repository.included_scope.map((item) => <li key={item}>{localizedScope(item)}</li>)}</ul><strong>{pick("不包含", "Excluded")}</strong><ul>{repository.excluded_scope.map((item) => <li key={item}>{localizedScope(item)}</li>)}</ul></div></details>
            {(repository.detail || !repository.has_upstream) && <div className="sync-warning">{repository.detail || pick("没有可同步的 upstream，请先配置跟踪分支。", "No upstream branch is configured.")}</div>}
            {repository.sensitive_change_count > 0 && <div className="sync-warning danger">{pick(`检测到 ${repository.sensitive_change_count} 个疑似敏感文件改动；不会自动提交。`, `${repository.sensitive_change_count} potentially sensitive changes detected; they will not be committed automatically.`)}</div>}
            <button className="secondary wide" disabled={syncBusy || blocked} title={blocked ? pick("请先处理未提交改动、分叉或 upstream 配置", "Resolve uncommitted changes, divergence, or upstream configuration first") : pick("拉取远端更新并推送本地已提交内容", "Pull remote updates and push local commits")} onClick={() => onSync([repository.repository_id])}>{busy === `sync:${repository.repository_id}` ? <LoaderCircle className="spin" size={14} /> : <RefreshCw size={14} />}{pick("同步这个仓库", "Sync this repository")}</button>
          </article>;
        })}
        {!syncOverview && <Empty icon={RefreshCw} title={pick("正在读取 Git 状态", "Reading Git status")} detail={pick("这里只检查预先配置的研究数据仓库。", "Only preconfigured research repositories are inspected.")} />}
      </div>
    </section>
    <section className="panel runs-panel">
      <SectionTitle eyebrow="RUN RECEIPTS" title={pick("每一步发生了什么", "What happened at each step")} />
      <div className="run-list">{runs.map((run) => <article className="run" key={`${run.run_type}-${run.run_id}`}><div className={`run-icon ${run.status}`}>{run.status === "succeeded" ? <Check size={17} /> : run.status === "failed" ? <CircleAlert size={17} /> : <LoaderCircle size={17} />}</div><div className="run-main"><div className="run-title"><strong>{run.run_id}</strong><span>{run.run_type}</span><em>{run.status}</em></div><span>{run.started_at}</span>{run.error && <p>{run.error}</p>}{run.steps?.length > 0 && <div className="run-steps">{run.steps.map((step) => <span key={step.name} className={step.status}>{step.name}</span>)}</div>}</div>{run.resumable && <button className="secondary" disabled={busy === run.run_id} onClick={() => onResume(run)}><RefreshCw size={14} />{pick("恢复", "Resume")}</button>}</article>)}</div>
      {!runs.length && <Empty icon={Activity} title={pick("还没有运行回执", "No run receipts yet")} detail={pick("Tracker、Codex 排名、Git 同步和研究流程运行后都会在这里留下可恢复记录。", "Tracker, Codex ranking, Git sync, and research workflows leave resumable receipts here.")} />}
    </section>
  </div>;
}
