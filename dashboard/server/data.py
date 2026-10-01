"""Read-only loaders over diagnostics/outputs/. Ported from diagnostics/eval_app.py.

Reads existing summary.json / team_change_metrics.json / final_metrics.json only. No
simulation, no LLM call.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "diagnostics" / "outputs"

METRICS = [
    "weighted_preference_total",
    "constraint_adherence",
    "stakeholder_management",
    "goal_achievement",
    "workflow_completion_time_hours",
]
MODE_ORDER = ["random", "cot", "assign_all"]
MAIN_VARIANT = "main"
TRUNCATED_TIMESTEP_THRESHOLD = 3

# Run health (how a run ended), derived from timestep_data/final_metrics.json:
#   complete / exhausted (no backlog left) / truncated (<= threshold timesteps, likely
#   interrupted) / in_progress_long (ran normally, didn't finish) / missing_data
HEALTH_EMPTY = {
    "run_status": "missing_data",
    "total_timesteps_recorded": None,
    "workflow_completed": None,
    "final_backlog": None,
    "manager_actions_logged": None,
}


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _summary_paths() -> list[Path]:
    return sorted(OUT_ROOT.glob("*/*/run_seed_*/summary.json"))


def variant_group(run_dir: Path, workflow: str | None) -> str:
    """'main' if the folder name equals the workflow, else the `<workflow>_<variant>`
    suffix (e.g. `_mini`, `_aware`), or 'other'."""
    folder = run_dir.parent.name
    if not workflow or folder == workflow:
        return MAIN_VARIANT
    prefix = f"{workflow}_"
    return folder[len(prefix):] if folder.startswith(prefix) else "other"


def run_health(run_dir: Path) -> dict[str, Any]:
    metrics = _read_json(run_dir / "timestep_data" / "final_metrics.json")
    if metrics is None:
        return dict(HEALTH_EMPTY)

    summary = metrics.get("execution_summary") or {}
    completed = bool(summary.get("workflow_completed"))
    total = summary.get("total_timesteps")

    backlog = None
    results = metrics.get("timestep_results") or []
    if results:
        obs = (results[-1].get("metadata") or {}).get("manager_observation") or {}
        counts = obs.get("task_status_counts") or {}
        backlog = sum(counts.get(k, 0) for k in ("pending", "ready", "running"))

    logged = None
    if run_dir.name.startswith("run_"):
        run_id = run_dir.name[len("run_"):]
        log = _read_json(run_dir / "execution_logs" / f"execution_log_{run_id}.json")
        if log is not None:
            logged = len(log.get("manager_actions") or [])

    if completed:
        status = "complete"
    elif backlog == 0:
        status = "exhausted"
    elif total is not None and total <= TRUNCATED_TIMESTEP_THRESHOLD:
        status = "truncated"
    else:
        status = "in_progress_long"
    return {
        "run_status": status,
        "total_timesteps_recorded": total,
        "workflow_completed": completed,
        "final_backlog": backlog,
        "manager_actions_logged": logged,
    }


def list_runs() -> list[dict[str, Any]]:
    rows = []
    for path in _summary_paths():
        data = _read_json(path)
        if data is None:
            continue
        run_dir = path.parent
        joins = data.get("agent_join_analyses", [])
        workflow = data.get("workflow")
        rows.append(
            {
                "workflow": workflow,
                "workflow_folder": run_dir.parent.name,
                "manager_mode": data.get("manager_mode"),
                "variant_group": variant_group(run_dir, workflow),
                "run": run_dir.name,
                **{m: data.get(m) for m in METRICS},
                "total_tasks": data.get("total_tasks"),
                "completed_tasks": data.get("completed_tasks"),
                "failed_tasks": data.get("failed_tasks"),
                "never_assigned_agents": sum(1 for a in joins if a.get("never_assigned")),
                "delayed_assignment_agents": sum(1 for a in joins if a.get("delayed")),
                "rubric_violations": len(data.get("rubric_violations", [])),
                **run_health(run_dir),
            }
        )
    return rows


def list_joins(workflow: str, mid_episode_only: bool, variant: str = "all") -> list[dict[str, Any]]:
    rows = []
    for path in _summary_paths():
        data = _read_json(path)
        if data is None or data.get("workflow") != workflow:
            continue
        if variant != "all" and variant_group(path.parent, workflow) != variant:
            continue
        for a in data.get("agent_join_analyses", []):
            if mid_episode_only and not (a.get("join_timestep") or 0) > 0:
                continue
            rows.append(
                {
                    "manager_mode": data.get("manager_mode"),
                    "run": path.parent.name,
                    **{
                        k: a.get(k)
                        for k in (
                            "agent_id",
                            "join_timestep",
                            "first_assignment_timestep",
                            "assignment_lag",
                            "delayed",
                            "never_assigned",
                            "capabilities_visible_at_join",
                            "had_backlog_opportunity",
                            "assigned_in_another_mode",
                        )
                    },
                }
            )
    rows.sort(
        key=lambda r: (
            not r["never_assigned"],
            not r["delayed"],
            r["manager_mode"] or "",
            r["join_timestep"] or 0,
        )
    )
    return rows


def nonstationarity_by_mode(
    workflow: str, mid_episode_only: bool, variant: str = "all"
) -> list[dict[str, Any]]:
    """Per-manager-mode aggregate of the non-stationarity signals, across seeds."""
    per_mode: dict[str, dict[str, Any]] = {}
    for path in _summary_paths():
        data = _read_json(path)
        if data is None or data.get("workflow") != workflow:
            continue
        if variant != "all" and variant_group(path.parent, workflow) != variant:
            continue
        mode = data.get("manager_mode")
        agg = per_mode.setdefault(
            mode,
            {
                "manager_mode": mode,
                "agents_tracked": 0,
                "never_assigned_agents": 0,
                "delayed_assignment_agents": 0,
                "capability_gap_at_join": 0,
                "failed_tasks_recent_joiners": 0,
                "rubric_violations": 0,
                "_lags": [],
            },
        )
        for a in data.get("agent_join_analyses", []):
            if mid_episode_only and not (a.get("join_timestep") or 0) > 0:
                continue
            agg["agents_tracked"] += 1
            agg["never_assigned_agents"] += bool(a.get("never_assigned"))
            agg["delayed_assignment_agents"] += bool(a.get("delayed"))
            agg["capability_gap_at_join"] += a.get("capabilities_visible_at_join") is False
            if a.get("assignment_lag") is not None:
                agg["_lags"].append(a["assignment_lag"])
        agg["failed_tasks_recent_joiners"] += len(
            data.get("failed_tasks_assigned_to_recent_joiners", [])
        )
        agg["rubric_violations"] += len(data.get("rubric_violations", []))

    rows = []
    for mode in [m for m in MODE_ORDER if m in per_mode] + sorted(set(per_mode) - set(MODE_ORDER)):
        agg = per_mode[mode]
        lags = agg.pop("_lags")
        agg["avg_assignment_lag_timesteps"] = round(mean(lags), 2) if lags else None
        rows.append(agg)
    return rows


def list_team_change_metrics() -> list[dict[str, Any]]:
    """One row per run with a team_change_metrics.json (diagnostics/analyze_team_changes.py)."""
    rows = []
    for path in sorted(OUT_ROOT.glob("*/*/run_seed_*/team_change_metrics.json")):
        data = _read_json(path)
        if data is None:
            continue
        rows.append(
            {
                "workflow": data.get("workflow"),
                "manager_mode": data.get("manager_mode"),
                "run": path.parent.name,
                **{
                    k: data.get(k)
                    for k in (
                        "post_change_score",
                        "baseline_score",
                        "post_change_gap",
                        "disruption_cost",
                        "unnecessary_disruption_cost",
                        "necessary_coverage",
                    )
                },
            }
        )
    return rows
