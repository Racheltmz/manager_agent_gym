"""
Error analysis for the team-based non-stationarity / open ad-hoc teamwork
diagnostic suite (see diagnostics/run_diagnostic_suite.sh).

For each (workflow, manager_mode) run this script:
  1. Re-derives the ground-truth team timeline from the scenario's own
     create_team_timeline() (examples/scenarios.py) to get each agent's
     join timestep and join reason.
  2. Reads execution_logs/execution_log_<run_id>.json to find, per agent,
     the first timestep the manager actually assigned it a task
     (assign_task / assign_tasks_to_agents / assign_all_pending_tasks).
  3. Reads workflow_outputs/workflow_execution_<run_id>.json for
     completed/failed task counts and per-task assigned_agent_id + status,
     to correlate failures with agents that had just joined.
  4. Reads evaluation_outputs/final_evaluation_<run_id>.json for the
     weighted preference total and any rubric/constraint violations
     (score < max_score or a non-null error field).
  5. Confirms the capability-visibility timing gap: loads the
     timestep_data snapshot at each agent's join timestep and checks
     whether the agent's full config (incl. agent_capabilities) is already
     present there, and whether that happens at or before the agent's
     first task assignment.

Prints a per-condition summary table and writes
diagnostics/outputs/summary.json with the full structured results.

Usage (after running diagnostics/run_diagnostic_suite.sh):
    python diagnostics/analyze_diagnostic_runs.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from examples.scenarios import SCENARIOS  # noqa: E402

WORKFLOWS = ["legal_m_and_a", "marketing_campaign", "tech_company_acquisition"]
MODES = ["cot", "random", "assign_all"]
OUT_ROOT = REPO_ROOT / "diagnostics" / "outputs"

# How many timesteps after joining an agent must receive its first
# assignment before we flag it as "delayed handling".
DELAY_THRESHOLD_TIMESTEPS = 3


@dataclass
class AgentJoinAnalysis:
    agent_id: str
    join_timestep: int
    join_reason: str
    first_assignment_timestep: int | None
    assignment_lag: int | None
    delayed: bool
    never_assigned: bool
    capabilities_visible_at_join: bool | None  # None if snapshot missing


@dataclass
class RunAnalysis:
    workflow: str
    manager_mode: str
    run_dir: str | None
    weighted_preference_total: float | None
    total_tasks: int | None
    completed_tasks: int | None
    failed_tasks: int | None
    # The five headline metrics (Preference Alignment == weighted_preference_total above).
    constraint_adherence: float | None = None
    stakeholder_management: float | None = None
    goal_achievement: float | None = None
    workflow_completion_time_hours: float | None = None
    failed_task_ids: list[str] = field(default_factory=list)
    failed_tasks_assigned_to_recent_joiners: list[dict] = field(default_factory=list)
    rubric_violations: list[dict] = field(default_factory=list)
    agent_join_analyses: list[AgentJoinAnalysis] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def get_team_join_events(workflow_name: str) -> list[tuple[int, str, str]]:
    """Returns [(join_timestep, agent_id, reason), ...] sorted by timestep."""
    spec = SCENARIOS[workflow_name]
    timeline = spec.create_team_timeline()
    events: list[tuple[int, str, str]] = []
    for t, changes in timeline.items():
        for action, payload, reason in changes:
            if action != "add":
                continue
            agent_id = payload.agent_id if hasattr(payload, "agent_id") else str(payload)
            events.append((t, agent_id, reason))
    events.sort(key=lambda e: e[0])
    return events


def find_latest_run_dir(workflow_name: str, manager_mode: str) -> Path | None:
    scenario_dir = OUT_ROOT / manager_mode / workflow_name
    if not scenario_dir.is_dir():
        return None
    run_dirs = sorted(
        [p for p in scenario_dir.iterdir() if p.is_dir() and p.name.startswith("run_")],
        key=lambda p: p.stat().st_mtime,
    )
    return run_dirs[-1] if run_dirs else None


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def extract_run_id(run_dir: Path) -> str:
    return run_dir.name[len("run_"):]


def get_assignment_timesteps(run_dir: Path, run_id: str) -> dict[str, int]:
    """agent_id -> first timestep any task shows assigned_agent_id == agent_id.

    NOTE: execution_logs/execution_log_<run_id>.json cannot be used for this —
    ManagerAgent.on_action_executed (manager_agent_gym/core/manager_agent/interface.py)
    hardcodes data={} when recording actions into its buffer, discarding the real
    {"task_id":..., "agent_id":...} payload every ActionResult carries. That's a
    library-level logging bug, out of scope to patch here, so we instead derive
    ground truth from the per-timestep workflow snapshots, which do record each
    task's real assigned_agent_id.
    """
    wf_out = run_dir / "workflow_outputs"
    first_assignment: dict[str, int] = {}
    if not wf_out.is_dir():
        return first_assignment

    prefix = f"workflow_execution_{run_id}_t"
    snapshots = sorted(
        wf_out.glob(f"{prefix}*.json"),
        key=lambda p: int(p.stem[len(prefix):]),
    )
    for snap_path in snapshots:
        ts = int(snap_path.stem[len(prefix):])
        snap = load_json(snap_path)
        if not snap:
            continue
        tasks = snap.get("tasks")
        task_list = list(tasks.values()) if isinstance(tasks, dict) else (tasks or [])
        for t in task_list:
            agent_id = t.get("assigned_agent_id")
            if agent_id and agent_id not in first_assignment:
                first_assignment[agent_id] = ts
    return first_assignment


def _walk(obj):
    """Yield every dict found anywhere inside obj (for loose payload scanning)."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def get_workflow_summary(run_dir: Path, run_id: str) -> dict | None:
    return load_json(run_dir / "workflow_outputs" / f"workflow_execution_{run_id}.json")


def get_failed_tasks(summary: dict | None) -> list[dict]:
    if not summary:
        return []
    tasks = summary.get("tasks")
    if isinstance(tasks, dict):
        task_list = list(tasks.values())
    elif isinstance(tasks, list):
        task_list = tasks
    else:
        return []
    return [t for t in task_list if isinstance(t, dict) and t.get("status") == "failed"]


def get_final_evaluation(run_dir: Path, run_id: str) -> dict | None:
    return load_json(run_dir / "evaluation_outputs" / f"final_evaluation_{run_id}.json")


def get_aggregated_score(final_eval: dict | None, evaluator_name: str) -> float | None:
    """Looks up evaluation_results[].aggregated_score for a given evaluator_name."""
    if not final_eval:
        return None
    for group in final_eval.get("evaluation_results", []) or []:
        if group.get("evaluator_name") == evaluator_name:
            score = group.get("aggregated_score")
            return float(score) if score is not None else None
    return None


def get_goal_achievement_evaluator_name(workflow_name: str) -> str | None:
    """Each scenario defines its own goal-achievement evaluator with a workflow-specific
    name (e.g. "legal_mna_goal_achievement_eval"); resolve it via the scenario's own
    factory rather than hardcoding names per workflow."""
    spec = SCENARIOS[workflow_name]
    factory = getattr(spec, "create_evaluator_to_measure_goal_achievement", None)
    if factory is None:
        return None
    return factory().name


def extract_rubric_violations(final_eval: dict | None) -> list[dict]:
    violations: list[dict] = []
    if not final_eval:
        return violations
    for group in final_eval.get("evaluation_results", []) or []:
        for res in _walk(group):
            if "error" in res and res.get("error"):
                violations.append({"name": res.get("name"), "error": res.get("error")})
            elif "score" in res and "max_score" in res:
                try:
                    if float(res["score"]) < float(res["max_score"]):
                        violations.append(
                            {
                                "name": res.get("name"),
                                "score": res.get("score"),
                                "max_score": res.get("max_score"),
                            }
                        )
                except (TypeError, ValueError):
                    pass
    return violations


def check_capabilities_visible_at_join(
    run_dir: Path, run_id: str, join_timestep: int, agent_id: str
) -> bool | None:
    """True if the join-timestep snapshot already exposes this agent's full
    config (incl. agent_capabilities) to the manager-visible workflow state.

    Per-timestep workflow snapshots are written by WorkflowSerialiser.save_timestep
    (manager_agent_gym/core/execution/output_writer.py) as
    workflow_outputs/workflow_execution_<run_id>_t<NNNN>.json.
    """
    wf_out = run_dir / "workflow_outputs"
    snap_path = wf_out / f"workflow_execution_{run_id}_t{join_timestep:04d}.json"
    snap = load_json(snap_path)
    if not snap:
        return None
    agents = snap.get("agents", [])
    for a in agents:
        if a.get("agent_id") == agent_id:
            cfg = a.get("config") or {}
            return bool(cfg.get("agent_capabilities"))
    return None


def analyze_run(workflow_name: str, manager_mode: str) -> RunAnalysis:
    analysis = RunAnalysis(workflow=workflow_name, manager_mode=manager_mode, run_dir=None,
                            weighted_preference_total=None, total_tasks=None,
                            completed_tasks=None, failed_tasks=None)

    run_dir = find_latest_run_dir(workflow_name, manager_mode)
    if run_dir is None:
        analysis.notes.append("no run directory found — run diagnostics/run_diagnostic_suite.sh first")
        return analysis

    analysis.run_dir = str(run_dir)
    run_id = extract_run_id(run_dir)

    summary = get_workflow_summary(run_dir, run_id)
    if summary:
        analysis.total_tasks = summary.get("total_tasks")
        analysis.completed_tasks = summary.get("completed_tasks")
        analysis.failed_tasks = summary.get("failed_tasks")
        analysis.workflow_completion_time_hours = summary.get("total_simulated_hours")

    failed_tasks = get_failed_tasks(summary)
    analysis.failed_task_ids = [
        str(task_id) for t in failed_tasks if (task_id := t.get("id")) is not None
    ]

    final_eval = get_final_evaluation(run_dir, run_id)
    if final_eval:
        per_pref = {
            name: ps.get("score", 0) * ps.get("weight", 0)
            for name, ps in (final_eval.get("preference_scores") or {}).items()
        }
        analysis.weighted_preference_total = sum(per_pref.values()) if per_pref else None
        analysis.constraint_adherence = get_aggregated_score(final_eval, "constraint_adherence")
        analysis.stakeholder_management = get_aggregated_score(final_eval, "stakeholder_management")
        goal_eval_name = get_goal_achievement_evaluator_name(workflow_name)
        if goal_eval_name:
            analysis.goal_achievement = get_aggregated_score(final_eval, goal_eval_name)
    analysis.rubric_violations = extract_rubric_violations(final_eval)

    join_events = get_team_join_events(workflow_name)
    first_assignment = get_assignment_timesteps(run_dir, run_id)

    for join_ts, agent_id, reason in join_events:
        first_ts = first_assignment.get(agent_id)
        lag = (first_ts - join_ts) if first_ts is not None else None
        analysis.agent_join_analyses.append(
            AgentJoinAnalysis(
                agent_id=agent_id,
                join_timestep=join_ts,
                join_reason=reason,
                first_assignment_timestep=first_ts,
                assignment_lag=lag,
                delayed=(lag is not None and lag > DELAY_THRESHOLD_TIMESTEPS),
                never_assigned=(first_ts is None),
                capabilities_visible_at_join=check_capabilities_visible_at_join(
                    run_dir, run_id, join_ts, agent_id
                ),
            )
        )

    recent_joiner_ids_by_ts = {(a.agent_id): a.join_timestep for a in analysis.agent_join_analyses}
    for t in failed_tasks:
        assigned = t.get("assigned_agent_id")
        if assigned in recent_joiner_ids_by_ts:
            analysis.failed_tasks_assigned_to_recent_joiners.append(
                {
                    "task_id": t.get("id"),
                    "assigned_agent_id": assigned,
                    "agent_join_timestep": recent_joiner_ids_by_ts[assigned],
                }
            )

    return analysis


def _fmt(v: float | None, precision: int = 3) -> str:
    return f"{v:.{precision}f}" if v is not None else "n/a"


def print_summary(results: list[RunAnalysis]) -> None:
    header = (
        f"{'workflow':28} {'mode':12} {'pref_align':>10} {'constr':>8} {'stakeh':>8} "
        f"{'goal':>8} {'compl_hrs':>10} {'tasks':>6} {'failed':>7} "
        f"{'delayed_joins':>14} {'never_assigned':>15} {'rubric_viol':>12}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        delayed = sum(1 for a in r.agent_join_analyses if a.delayed)
        never = sum(1 for a in r.agent_join_analyses if a.never_assigned)
        print(
            f"{r.workflow:28} {r.manager_mode:12} {_fmt(r.weighted_preference_total):>10} "
            f"{_fmt(r.constraint_adherence):>8} {_fmt(r.stakeholder_management):>8} "
            f"{_fmt(r.goal_achievement):>8} {_fmt(r.workflow_completion_time_hours, 1):>10} "
            f"{str(r.total_tasks):>6} {str(r.failed_tasks):>7} {delayed:>14} {never:>15} "
            f"{len(r.rubric_violations):>12}"
        )
        for a in r.agent_join_analyses:
            if a.delayed or a.never_assigned:
                flag = "NEVER_ASSIGNED" if a.never_assigned else f"delayed_lag={a.assignment_lag}"
                print(f"    ! {a.agent_id} joined@t={a.join_timestep} ({flag}) "
                      f"capabilities_visible_at_join={a.capabilities_visible_at_join}")
        if r.failed_tasks_assigned_to_recent_joiners:
            for f in r.failed_tasks_assigned_to_recent_joiners:
                print(f"    x failed task {f['task_id']} -> {f['assigned_agent_id']} "
                      f"(joined@t={f['agent_join_timestep']})")
        for note in r.notes:
            print(f"    note: {note}")


def main() -> None:
    results: list[RunAnalysis] = []
    for mode in MODES:
        for wf in WORKFLOWS:
            results.append(analyze_run(wf, mode))

    print_summary(results)

    out_path = OUT_ROOT / "summary.json"
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    serializable = [
        {**asdict(r), "agent_join_analyses": [asdict(a) for a in r.agent_join_analyses]}
        for r in results
    ]
    with open(out_path, "w") as f:
        json.dump(serializable, f, indent=2, default=str)
    print(f"\nWrote full structured results to {out_path}")


if __name__ == "__main__":
    main()
