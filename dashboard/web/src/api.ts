export type Run = {
  workflow: string;
  workflow_folder: string;
  manager_mode: string;
  variant_group: string;
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

export type Scenario = { id: string; collection: string; name: string };

export type DiffStatus = "added" | "removed" | "changed" | "unchanged";

export type DagNode = {
  id: string;
  status: DiffStatus;
  changed_fields: string[];
  layer: number;
  row: number;
  subtask_count: number;
  requirements_before: number | null;
  requirements_after: number | null;
  description_before: string | null;
  description_after: string | null;
};

export type DagEdge = { source: string; target: string; status: "added" | "removed" | "unchanged" };

export type DagDiff = {
  nodes: DagNode[];
  edges: DagEdge[];
  counts: Record<DiffStatus, number>;
};

async function get<T>(path: string, params: Record<string, string | boolean> = {}): Promise<T> {
  const qs = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
  const res = await fetch(`/api/${path}${qs.size ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(`${path}: ${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  runs: () => get<Run[]>("runs"),
  nonstationarity: (workflow: string, midEpisodeOnly: boolean, variant: string) =>
    get<NonStationarityRow[]>("nonstationarity", { workflow, mid_episode_only: midEpisodeOnly, variant }),
  joins: (workflow: string, midEpisodeOnly: boolean, variant: string) =>
    get<JoinRow[]>("joins", { workflow, mid_episode_only: midEpisodeOnly, variant }),
  teamChange: () => get<TeamChangeRow[]>("team-change"),
  scenarios: () => get<Scenario[]>("scenarios"),
  dagDiff: (before: string, after: string) => get<DagDiff>("dag/diff", { before, after }),
};
