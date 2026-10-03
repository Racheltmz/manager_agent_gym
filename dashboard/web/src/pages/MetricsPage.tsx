import { useMemo, useState } from "react";
import { api, type Run, type TeamChangeRow } from "../api";
import { useAsync } from "../useAsync";
import DataTable from "../components/DataTable";
import ChecklistDag from "../components/ChecklistDag";

const MODE_ORDER = ["random", "cot", "assign_all"];
const byMode = (a: { manager_mode: string }, b: { manager_mode: string }) =>
  (MODE_ORDER.indexOf(a.manager_mode) + 1 || 99) - (MODE_ORDER.indexOf(b.manager_mode) + 1 || 99);

/** Mean of `key` per manager mode, skipping nulls. */
function meanByMode<T extends { manager_mode: string }>(rows: T[], keys: string[]) {
  const modes = [...new Set(rows.map((r) => r.manager_mode))].map((manager_mode) => ({ manager_mode })).sort(byMode);
  return modes.map(({ manager_mode }) => {
    const mine = rows.filter((r) => r.manager_mode === manager_mode) as Record<string, unknown>[];
    const out: Record<string, string | number | null> = { manager_mode };
    for (const k of keys) {
      const vals = mine.map((r) => r[k]).filter((v): v is number => typeof v === "number");
      out[k] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    }
    return out;
  });
}

type Stat = { key: string; label: string; digits?: number };

/** Single-value metrics as dashboard cards: one big number per manager mode. */
function StatCards({ data, stats }: { data: Record<string, string | number | null>[]; stats: Stat[] }) {
  return (
    <div className="grid" style={{ marginBottom: 16 }}>
      {stats.map((st) => (
        <div className="card" key={st.key}>
          <h3>{st.label}</h3>
          <div style={{ display: "flex", gap: 24, padding: "6px 0 10px" }}>
            {data.map((d) => (
              <div key={String(d.manager_mode)}>
                <div style={{ fontSize: 34, fontWeight: 600, lineHeight: 1.1 }}>
                  {typeof d[st.key] === "number" ? (d[st.key] as number).toFixed(st.digits ?? 3) : "–"}
                </div>
                <div className="muted">{d.manager_mode}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function MetricsPage() {
  const runs = useAsync(() => api.runs(), []);
  const teamChange = useAsync(() => api.teamChange(), []);
  const [workflow, setWorkflow] = useState<string>("");
  const [midOnly, setMidOnly] = useState(true);

  const workflows = useMemo(() => [...new Set((runs.data ?? []).map((r) => r.workflow))].sort(), [runs.data]);
  const wf = workflow || workflows[0] || "";

  const wfRuns: Run[] = useMemo(
    () => (runs.data ?? []).filter((r) => r.workflow === wf),
    [runs.data, wf],
  );

  const ns = useAsync(() => (wf ? api.nonstationarity(wf, midOnly) : Promise.resolve([])), [wf, midOnly]);
  const joins = useAsync(() => (wf ? api.joins(wf, midOnly) : Promise.resolve([])), [wf, midOnly]);

  const tc: TeamChangeRow[] = (teamChange.data ?? []).filter((r) => r.workflow === wf);
  const tcByMode = useMemo(
    () => meanByMode(tc, ["post_change_score", "baseline_score", "disruption_cost", "specialist", "running_task", "leave"]),
    [tc],
  );

  if (runs.error) return <div className="error">{runs.error}</div>;

  return (
    <>
      <div className="filters">
        <label>
          Workflow
          <select value={wf} onChange={(e) => setWorkflow(e.target.value)}>
            {workflows.map((w) => (
              <option key={w}>{w}</option>
            ))}
          </select>
        </label>
      </div>

      <h2>Metrics (mean across runs)</h2>
      <StatCards
        data={tcByMode}
        stats={[
          { key: "post_change_score", label: "Post-change score" },
          { key: "disruption_cost", label: "Disruption score" },
          { key: "baseline_score", label: "Baseline score" },
          { key: "leave", label: "Post-change: leave" },
        ]}
      />
      {tc.length === 0 ? (
        <div className="muted">None for this workflow. Run dashboard/analysis/analyze_team_changes.py.</div>
      ) : (
        <DataTable
          rows={[...tc].sort(byMode)}
          columns={[
            { key: "manager_mode", label: "mode" },
            { key: "run" },
            { key: "post_change_score", label: "post-change", digits: 3 },
            { key: "baseline_score", label: "baseline", digits: 3 },
            { key: "post_change_gap", label: "gap", digits: 3 },
            { key: "disruption_cost", label: "disruption", digits: 3 },
            { key: "leave", digits: 3 },
          ]}
        />
      )}

      <h2>Checklist score by task over time</h2>
      <ChecklistDag runs={[...wfRuns].sort(byMode)} />

      <h2>Runs</h2>
      <DataTable
        rows={[...wfRuns].sort(byMode)}
        columns={[
          { key: "manager_mode", label: "mode" },
          { key: "workflow_folder", label: "folder" },
          { key: "run_status", label: "status" },
          { key: "weighted_preference_total", label: "pref", digits: 3 },
          { key: "constraint_adherence", label: "constraint", digits: 3 },
          { key: "stakeholder_management", label: "stakeholder", digits: 3 },
          { key: "goal_achievement", label: "goal", digits: 3 },
          { key: "workflow_completion_time_hours", label: "hours", digits: 1 },
          { key: "completed_tasks", label: "done" },
          { key: "total_tasks", label: "tasks" },
          { key: "never_assigned_agents", label: "never assigned" },
          { key: "delayed_assignment_agents", label: "delayed" },
          { key: "rubric_violations", label: "violations" },
        ]}
      />

      <h2>Non-stationarity handling</h2>
      <div className="filters">
        <label>
          <input type="checkbox" checked={midOnly} onChange={(e) => setMidOnly(e.target.checked)} />
          Mid-episode joiners only
        </label>
      </div>
      <StatCards
        data={(ns.data ?? []) as unknown as Record<string, string | number | null>[]}
        stats={[
          { key: "never_assigned_agents", label: "Agents never assigned", digits: 0 },
          { key: "delayed_assignment_agents", label: "Agents delayed", digits: 0 },
          { key: "avg_assignment_lag_timesteps", label: "Avg assignment lag (timesteps)" },
        ]}
      />
      <DataTable rows={ns.data ?? []} columns={[
        { key: "manager_mode", label: "mode" },
        { key: "agents_tracked", label: "agents" },
        { key: "never_assigned_agents", label: "never assigned" },
        { key: "delayed_assignment_agents", label: "delayed" },
        { key: "avg_assignment_lag_timesteps", label: "avg lag", digits: 2 },
        { key: "capability_gap_at_join", label: "capability gap" },
        { key: "failed_tasks_recent_joiners", label: "failed (recent joiners)" },
        { key: "rubric_violations", label: "violations" },
      ]} />

      <h2>Join / first-assignment timeline</h2>
      <DataTable rows={joins.data ?? []} columns={[
        { key: "manager_mode", label: "mode" },
        { key: "run" },
        { key: "agent_id", label: "agent" },
        { key: "join_timestep", label: "joined" },
        { key: "first_assignment_timestep", label: "first assigned" },
        { key: "assignment_lag", label: "lag" },
        { key: "delayed" },
        { key: "never_assigned", label: "never assigned" },
        { key: "capabilities_visible_at_join", label: "caps visible" },
      ]} />
    </>
  );
}
