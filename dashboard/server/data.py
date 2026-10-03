"""Read-only loaders over the run outputs directory (dashboard/outputs, or $MAG_OUTPUTS_DIR).

Reads existing summary.json / team_change_metrics.json / final_metrics.json only. No
simulation, no LLM call.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("MAG_OUTPUTS_DIR") or REPO_ROOT / "dashboard" / "outputs")

METRICS = [
    "weighted_preference_total",
    "constraint_adherence",
    "stakeholder_management",
    "goal_achievement",
    "workflow_completion_time_hours",
]
MODE_ORDER = ["random", "cot", "assign_all"]
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


def list_joins(workflow: str, mid_episode_only: bool) -> list[dict[str, Any]]:
    rows = []
    for path in _summary_paths():
        data = _read_json(path)
        if data is None or data.get("workflow") != workflow:
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
    workflow: str, mid_episode_only: bool
) -> list[dict[str, Any]]:
    """Per-manager-mode aggregate of the non-stationarity signals, across seeds."""
    per_mode: dict[str, dict[str, Any]] = {}
    for path in _summary_paths():
        data = _read_json(path)
        if data is None or data.get("workflow") != workflow:
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
    """One row per run with a team_change_metrics.json (dashboard/analysis/analyze_team_changes.py)."""
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
                    for k in ("post_change_score", "baseline_score", "post_change_gap", "disruption_cost")
                },
                # post-change score per case, one column each
                **{
                    case: (data.get("by_case") or {}).get(case, {}).get("post_change_score")
                    for case in ("specialist", "running_task", "leave")
                },
            }
        )
    return rows


def checklist_dag(workflow_folder: str, manager_mode: str, run: str) -> dict[str, Any] | None:
    """Deterministic checklist score per task per timestep for one run, as a DAG.

    Nodes are the final snapshot's top-level tasks that carry a checklist (their subtasks'
    checklists are rolled in). Each timestep's score re-runs the checklist patterns against
    that snapshot's output resources; a checklist on a decomposed task runs on its subtasks'
    combined output. `None` for a task means no output yet.
    """
    import re

    from .dag import _layout

    wo = OUT_ROOT / manager_mode / workflow_folder / run / "workflow_outputs"
    prefix = f"workflow_execution_{run[len('run_'):]}_t"
    paths = sorted(wo.glob(f"{prefix}*.json"))
    if not paths:
        return None
    snaps = {int(p.stem[len(prefix):]): _read_json(p) for p in paths}
    snaps = {t: s for t, s in snaps.items() if s}

    def flat(task: dict) -> list[dict]:
        return [task] + [x for s in task.get("subtasks") or [] for x in flat(s)]

    def subtree_text(x: dict, resources: dict) -> str:
        """Output text of a task and all its subtasks. A checklist is run on this, so a task the
        manager decomposed is scored on its subtasks' combined output, as if it had stayed whole
        (same rule as team_change_metrics)."""
        return "\n".join(
            c
            for y in flat(x)
            for r in y.get("output_resource_ids") or []
            if isinstance(c := (resources.get(str(r)) or {}).get("content"), str)
        )

    def score(task: dict, resources: dict) -> tuple[int, int, list[str], bool]:
        passed = total = 0
        failed: list[str] = []
        has_output = False
        for x in flat(task):
            reqs = x.get("requirements") or []
            has_output = has_output or bool(x.get("output_resource_ids"))
            text = subtree_text(x, resources)
            for q in reqs:
                total += 1
                flags = 0 if q.get("case_sensitive") else re.IGNORECASE
                if q.get("pattern") and re.search(q["pattern"], text, flags):
                    passed += 1
                else:
                    failed.append(q.get("key", ""))
        return passed, total, failed, has_output

    last = snaps[max(snaps)]
    id_name = {str(i): t["name"] for i, t in last["tasks"].items()}
    # The engine also lists every subtask as a task of its own and points dependents at it.
    # Draw the authored structure: subtasks fold into their parent, and an edge to a subtask
    # becomes an edge to the parent.
    owner: dict[str, str] = {}
    for t in last["tasks"].values():
        for x in flat(t)[1:]:
            owner[str(x["id"])] = t["name"]
    nodes = {
        t["name"]: sum(len(x.get("requirements") or []) for x in flat(t))
        for t in last["tasks"].values()
        if t.get("parent_task_id") is None and str(t["id"]) not in owner
    }
    nodes = {n: c for n, c in nodes.items() if c}

    def node_of(task_id: str) -> str | None:
        return owner.get(task_id) or id_name.get(task_id)

    edges = sorted(
        {
            (a, t["name"])
            for t in last["tasks"].values()
            if t["name"] in nodes
            for d in t.get("dependency_task_ids") or []
            if (a := node_of(str(d))) in nodes and a != t["name"]
        }
    )
    pos = _layout(list(nodes), edges)

    scores: dict[str, dict[int, Any]] = {n: {} for n in nodes}
    for ts, snap in sorted(snaps.items()):
        for t in snap["tasks"].values():
            if t["name"] not in nodes or t.get("parent_task_id") is not None:
                continue
            passed, total, failed, has_out = score(t, snap.get("resources") or {})
            scores[t["name"]][ts] = (
                {
                    "passed": passed,
                    "total": total,
                    "failed_keys": failed,
                    "agent": t.get("assigned_agent_id"),
                    "status": t.get("status"),
                }
                if has_out
                else None
            )
    return {
        "timesteps": sorted(snaps),
        "nodes": [
            {"id": n, "total": nodes[n], "layer": pos[n][0], "row": pos[n][1], "scores": scores[n]}
            for n in nodes
        ],
        "edges": edges,
    }


def checklist_task_detail(
    workflow_folder: str, manager_mode: str, run: str, task: str, timestep: int
) -> dict[str, Any] | None:
    """One DAG node at one timestep: each checklist item (pattern, pass/fail) and the output
    resources it was scored against, for the task and its subtasks."""
    import re

    path = (
        OUT_ROOT / manager_mode / workflow_folder / run / "workflow_outputs"
        / f"workflow_execution_{run[len('run_'):]}_t{timestep:04d}.json"
    )
    snap = _read_json(path)
    top = next(
        (t for t in (snap or {}).get("tasks", {}).values() if t["name"] == task and t.get("parent_task_id") is None),
        None,
    )
    if top is None:
        return None

    def flat(t: dict) -> list[dict]:
        return [t] + [x for s in t.get("subtasks") or [] for x in flat(s)]

    resources = snap.get("resources") or {}
    parts = []
    for x in flat(top):
        outs = [resources.get(str(r)) or {} for r in x.get("output_resource_ids") or []]
        # A checklist is run on the task's own output plus its subtasks' (see checklist_dag)
        text = "\n".join(
            c
            for y in flat(x)
            for r in y.get("output_resource_ids") or []
            if isinstance(c := (resources.get(str(r)) or {}).get("content"), str)
        )
        reqs = x.get("requirements") or []
        if not reqs and not outs:
            continue
        parts.append(
            {
                "task": x["name"],
                "requirements": [
                    {
                        "key": q.get("key"),
                        "description": q.get("description"),
                        "pattern": q.get("pattern"),
                        "passed": bool(
                            q.get("pattern")
                            and re.search(q["pattern"], text, 0 if q.get("case_sensitive") else re.IGNORECASE)
                        ),
                    }
                    for q in reqs
                ],
                "outputs": [{"name": o.get("name"), "content": o.get("content")} for o in outs],
                "scored_on_subtasks": bool(reqs and x.get("subtasks")),
            }
        )
    return {"task": task, "timestep": timestep, "parts": parts}
