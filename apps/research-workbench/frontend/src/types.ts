export type NavKey = "week" | "papers" | "reading" | "ideas" | "projects" | "skills" | "runs";

export interface Paper {
  paper_id: string;
  title: string;
  abstract: string;
  abstract_evidence: "complete" | "insufficient" | "missing";
  abstract_word_count: number;
  abstract_ready: boolean;
  chinese_explanation: string;
  authors: string;
  venue: string;
  url: string;
  published: string;
  source: string;
  methodology: string;
  relevance_reason: string;
  public_reason: string;
  tier: number;
  lane: string;
  cluster_id: string;
  status: string;
  score: number;
  pdf_path: string;
  note_path: string;
}

export interface PlanTask {
  task_id: string;
  category: string;
  title: string;
  related_id: string;
  priority: number;
  due_date: string;
  completed: boolean;
}

export interface WeeklyPlan {
  week: string;
  status: "draft" | "confirmed";
  generated_at: string;
  confirmed_at: string;
  capacity: Record<string, number>;
  tasks: PlanTask[];
}

export interface Cluster {
  cluster_id: string;
  question: string;
  mechanism: string;
  paper_ids: string[];
  status: string;
}

export interface Attention {
  attention_id: string;
  kind: string;
  severity: "info" | "warning" | "error";
  title: string;
  detail: string;
  action_label: string;
  related_id: string;
}

export interface Idea {
  slug: string;
  title: string;
  status: string;
  stage?: string;
  role?: string;
  checkpoint?: string;
  priority?: string;
  paused?: string;
  pause_reason?: string;
  path: string;
}

export interface ResearchProject {
  slug: string;
  title: string;
  project_path: string;
  status: string;
  stage: string;
  summary: string;
  current_focus: string;
  open_issues: number;
  last_sync: string;
  recent_change: string;
  zotero_collection: string;
}

export type ProjectItemStatus = "todo" | "in_progress" | "waiting_human" | "waiting_ai" | "done" | "blocked";

export interface ProjectBoardItem {
  item_id: string;
  title: string;
  detail: string;
  status: ProjectItemStatus;
  source_path: string;
  action_label: string;
}

export interface ProjectBoardSection {
  section_id: string;
  title: string;
  kind: string;
  summary: string;
  items: ProjectBoardItem[];
}

export interface ProjectNote {
  note_id: string;
  text: string;
  source_type: "text" | "image";
  asset_path: string;
  created_at: string;
}

export interface ProjectModule {
  module_id: string;
  title: string;
  description: string;
  section: ProjectBoardSection;
  created_at: string;
}

export interface ProjectWorkspace {
  schema: string;
  schema_version: number;
  slug: string;
  updated_at: string;
  notes: ProjectNote[];
  sections: ProjectBoardSection[];
}

export interface ProjectChatMessage {
  role: "user" | "assistant" | "system";
  text: string;
  at: string;
}

export interface ProjectChatSession {
  schema: string;
  schema_version: number;
  slug: string;
  codex_thread_id: string;
  status: string;
  messages: ProjectChatMessage[];
  last_activity_at: string;
}

export interface ProjectWorkspaceView {
  project: ResearchProject;
  workspace: ProjectWorkspace;
  session: ProjectChatSession;
}

export interface SkillInfo {
  name: string;
  title: string;
  description: string;
  original_description: string;
  path: string;
  applies_to: string[];
  recommended: boolean;
}

export interface Slate {
  week: string;
  pool_hash: string;
  generated_by: string;
  ranking_version: number;
  generated_at: string;
  codex_thread_id: string;
  current_top5: string[];
  promotion_history: Array<{ at: string; removed_paper_id: string; promoted_paper_id: string; reason: string }>;
}

export interface Dashboard {
  week: string;
  top5: Paper[];
  plan: WeeklyPlan;
  clusters: Cluster[];
  attention: Attention[];
  tracker_health: Record<string, unknown>;
  ideas: Idea[];
  slate: Slate;
  migration: { weeks: unknown[]; consecutive_successes: number; checkpoint_ready: boolean; gemini_enabled: boolean };
}

export interface RunReceipt {
  run_id: string;
  run_type: string;
  status: string;
  started_at: string;
  finished_at: string;
  resumable: boolean;
  error: string;
  steps: Array<{ name: string; status: string; detail: string }>;
  artifacts: string[];
  metadata: Record<string, unknown>;
}

export interface ReadingSession {
  session_id: string;
  paper_id: string;
  codex_thread_id: string;
  phase: string;
  read_depth: string;
  status: string;
  note_path: string;
  pdf_path: string;
  agent_name: string;
  workflow_version: number;
  source_scope: "abstract" | "full-paper";
  messages: Array<{
    message_id: string;
    role: "user" | "assistant" | "system";
    text: string;
    phase: string;
    at: string;
  }>;
  last_error: string;
  last_activity_at: string;
}

export interface GitRepositoryState {
  repository_id: string;
  name: string;
  roles: string[];
  available: boolean;
  branch: string;
  remote: string;
  has_upstream: boolean;
  dirty_count: number;
  sensitive_change_count: number;
  ahead: number;
  behind: number;
  last_commit: string;
  tracked_count: number;
  tracked_pdf_count: number;
  untracked_count: number;
  ignored_count: number;
  included_scope: string[];
  excluded_scope: string[];
  state: "clean" | "dirty" | "ahead" | "behind" | "diverged" | "unavailable" | "error";
  detail: string;
}

export interface GitSyncOverview {
  generated_at: string;
  repositories: GitRepositoryState[];
  privacy: string[];
}

export interface GitSyncResult {
  repository_id: string;
  name: string;
  status: "succeeded" | "failed" | "skipped";
  detail: string;
}

export interface GitSyncResponse {
  run_id: string;
  status: "succeeded" | "failed";
  results: GitSyncResult[];
  overview: GitSyncOverview;
}
