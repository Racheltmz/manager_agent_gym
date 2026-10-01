import { useMemo, useState } from "react";
import { api, type Run, type TeamChangeRow } from "../api";
import { useAsync } from "../useAsync";
import DataTable from "../components/DataTable";
import ModeBars from "../components/ModeBars";

const MODE_ORDER = ["random", "cot", "assign_all"];
const HEADLINE = [
  { key: "weighted_preference_total", label: "Preference alignment", color: "#1f77b4" },
  { key: "constraint_adherence", label: "Constraint adherence", color: "#ff7f0e" },
  { key: "stakeholder_management", label: "Stakeholder management", color: "#d62728" },
  { key: "goal_achievement", label: "Goal achievement", color: "#2ca02c" },
  { key: "workflow_completion_time_hours", label: "Completion time (hrs)", color: "#9467bd" },
] as const;

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

export default function MetricsPage() {
  const runs = useAsync(() => api.runs(), []);
  const teamChange = useAsync(() => api.teamChange(), []);
  const [workflow, setWorkflow] = useState<string>("");
  const [variant, setVariant] = useState<string>("main");
  const [midOnly, setMidOnly] = useState(true);

  const workflows = useMemo(() => [...new Set((runs.data ?? []).map((r) => r.workflow))].sort(), [runs.data]);
  const variants = useMemo(() => [...new Set((runs.data ?? []).map((r) => r.variant_group))].sort(), [runs.data]);
  const wf = workflow || workflows[0] || "";

  const wfRuns: Run[] = useMemo(
    () => (runs.data ?? []).filter((r) => r.workflow === wf && (variant === "all" || r.variant_group === variant)),
    [runs.data, wf, variant],
  );
  const headline = useMemo(() => meanByMode(wfRuns, HEADLINE.map((h) => h.key)), [wfRuns]);

  const ns = useAsync(() => (wf ? api.nonstationarity(wf, midOnly, variant) : Promise.resolve([])), [wf, midOnly, variant]);
  const joins = useAsync(() => (wf ? api.joins(wf, midOnly, variant) : Promise.resolve([])), [wf, midOnly, variant]);

  const tc: TeamChangeRow[] = (teamChange.data ?? []).filter((r) => r.workflow === wf);
  const tcByMode = useMemo(
    () => meanByMode(tc, ["post_change_score", "baseline_score", "disruption_cost", "unnecessary_disruption_cost"]),
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
        <label>
          Variant
          <select value={variant} onChange={(e) => setVariant(e.target.value)}>
            {variants.map((v) => (
              <option key={v}>{v}</option>
            ))}
            <option value="all">all</option>
          </select>
        </label>
        <label>
          <input type="checkbox" checked={midOnly} onChange={(e) => setMidOnly(e.target.checked)} />
          Mid-episode joiners only
        </label>
      </div>

      <h2>Headline metrics (mean across runs)</h2>
      <div className="grid">
        {HEADLINE.map((h) => (
          <div className="card" key={h.key}>
            <h3>{h.label}</h3>
            <ModeBars data={headline} series={[h]} />
          </div>
        ))}
      </div>

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

      <h2>Team-change metrics</h2>
      {tc.length === 0 ? (
        <div className="muted">None for this workflow. Run diagnostics/analyze_team_changes.py.</div>
      ) : (
        <>
          <div className="grid">
            <div className="card">
              <h3>Post-change vs baseline score</h3>
              <ModeBars
                data={tcByMode}
                series={[
                  { key: "post_change_score", label: "post-change", color: "#2563eb" },
                  { key: "baseline_score", label: "baseline", color: "#9aa3af" },
                ]}
              />
            </div>
            <div className="card">
              <h3>Disruption cost</h3>
              <ModeBars
                data={tcByMode}
                series={[
                  { key: "disruption_cost", label: "raw", color: "#d99a1c" },
                  { key: "unnecessary_disruption_cost", label: "unnecessary", color: "#d1495b" },
                ]}
              />
            </div>
          </div>
          <DataTable
            rows={[...tc].sort(byMode)}
            columns={[
              { key: "manager_mode", label: "mode" },
              { key: "run" },
              { key: "post_change_score", label: "post-change", digits: 3 },
              { key: "baseline_score", label: "baseline", digits: 3 },
              { key: "post_change_gap", label: "gap", digits: 3 },
              { key: "disruption_cost", label: "disruption", digits: 3 },
              { key: "unnecessary_disruption_cost", label: "unnecessary", digits: 3 },
              { key: "necessary_coverage", label: "coverage", digits: 3 },
            ]}
          />
        </>
      )}

      <h2>Non-stationarity handling</h2>
      {ns.data && ns.data.length > 0 && (
        <div className="grid">
          <div className="card">
            <h3>Agents never assigned / delayed</h3>
            <ModeBars
              data={ns.data as unknown as Record<string, string | number | null>[]}
              series={[
                { key: "never_assigned_agents", label: "never assigned", color: "#d62728" },
                { key: "delayed_assignment_agents", label: "delayed", color: "#ff7f0e" },
              ]}
              digits={0}
            />
          </div>
          <div className="card">
            <h3>Avg assignment lag (timesteps)</h3>
            <ModeBars
              data={ns.data as unknown as Record<string, string | number | null>[]}
              series={[{ key: "avg_assignment_lag_timesteps", label: "lag", color: "#9467bd" }]}
              digits={1}
            />
          </div>
        </div>
      )}
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
