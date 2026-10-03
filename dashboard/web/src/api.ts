export type Run = {
  workflow: string;
  workflow_folder: string;
  manager_mode: string;
  run: string;
  weighted_preference_total: number | null;
  constraint_adherence: number | null;
  stakeholder_management: number | null;
  goal_achievement: number | null;
  workflow_completion_time_hours: number | null;
  total_tasks: number | null;
  completed_tasks: number | null;
  failed_tasks: number | null;
  never_assigned_agents: number;
  delayed_assignment_agents: number;
  rubric_violations: number;
  run_status: string;
  total_timesteps_recorded: number | null;
};

export type NonStationarityRow = {
  manager_mode: string;
  agents_tracked: number;
  never_assigned_agents: number;
  delayed_assignment_agents: number;
  avg_assignment_lag_timesteps: number | null;
  capability_gap_at_join: number;
  failed_tasks_recent_joiners: number;
  rubric_violations: number;
};

export type JoinRow = {
  manager_mode: string;
  run: string;
  agent_id: string;
  join_timestep: number | null;
  first_assignment_timestep: number | null;
  assignment_lag: number | null;
  delayed: boolean;
  never_assigned: boolean;
  capabilities_visible_at_join: boolean | null;
};

export type TeamChangeRow = {
  workflow: string;
  manager_mode: string;
  run: string;
  post_change_score: number | null;
  baseline_score: number | null;
  post_change_gap: number | null;
  disruption_cost: number | null;
  specialist: number | null;
  running_task: number | null;
  leave: number | null;
};

export type ChecklistDag = {
  timesteps: number[];
  nodes: {
    id: string;
    total: number;
    layer: number;
    row: number;
    scores: Record<string, { passed: number; total: number; failed_keys: string[]; agent: string | null; status: string } | null>;
  }[];
  edges: [string, string][];
};

export type ChecklistTask = {
  task: string;
  timestep: number;
  parts: {
    task: string;
    requirements: { key: string; description: string | null; pattern: string | null; passed: boolean }[];
    outputs: { name: string | null; content: string | null }[];
  }[];
};

export type Scenario = { id: string; collection: string; name: string };

export type DiffStatus = "added" | "removed" | "changed" | "unchanged";
export type View = "workflow" | "team" | "preferences";

export type GNode = {
  id: string;
  label: string;
  sublabel: string;
  lines: { text: string; status: DiffStatus }[];
  tags: string[];
  status: DiffStatus;
  x: number;
  y: number;
  w: number;
  h: number;
};

export type GEdge = { source: string; target: string; status: "added" | "removed" | "unchanged" };
export type Pane = { nodes: GNode[]; edges: GEdge[] };
export type DetailRow = { label: string; before: string | null; after: string | null; meta: boolean };

export type Compare = {
  view: View;
  orientation: "horizontal" | "vertical";
  canvas: { width: number; height: number };
  before: Pane;
  after: Pane;
  counts: Record<DiffStatus, number>;
  details: Record<string, { title: string; rows: DetailRow[] }>;
};

async function get<T>(path: string, params: Record<string, string | boolean> = {}): Promise<T> {
  const qs = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
  const res = await fetch(`/api/${path}${qs.size ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(`${path}: ${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  runs: () => get<Run[]>("runs"),
  nonstationarity: (workflow: string, midEpisodeOnly: boolean) =>
    get<NonStationarityRow[]>("nonstationarity", { workflow, mid_episode_only: midEpisodeOnly }),
  joins: (workflow: string, midEpisodeOnly: boolean) =>
    get<JoinRow[]>("joins", { workflow, mid_episode_only: midEpisodeOnly }),
  teamChange: () => get<TeamChangeRow[]>("team-change"),
  checklistDag: (workflowFolder: string, managerMode: string, run: string) =>
    get<ChecklistDag>("checklist-dag", { workflow_folder: workflowFolder, manager_mode: managerMode, run }),
  checklistTask: (workflowFolder: string, managerMode: string, run: string, task: string, timestep: number) =>
    get<ChecklistTask>("checklist-task", { workflow_folder: workflowFolder, manager_mode: managerMode, run, task, timestep: String(timestep) }),
  scenarios: () => get<Scenario[]>("scenarios"),
  compare: (view: View, before: string, after: string) => get<Compare>("compare", { view, before, after }),
};
