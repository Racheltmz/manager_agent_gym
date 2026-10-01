"""
Team-membership non-stationarity metrics (docs/team_non_stationarity/metrics.md).

Computed post hoc from the per-timestep workflow snapshots a run already writes
(`workflow_outputs/workflow_execution_<run_id>_t<NNNN>.json`), so no engine change and
no LLM call is needed.

Timing convention: a roster change at timestep t is applied at the start of t, then the
manager acts, then the snapshot for t is written. So the state *before* an event is the
last snapshot with timestep < t, and the manager's responses are visible in snapshots
with timestep >= t, up to (excluding) the next event's timestep.

Metrics:
- post_change_score: mean checklist score (items passed / total) over each event's
  affected tasks, measured on the final state. Unfinished affected tasks score 0.
- baseline_score: same scoring over every checklist task no event affects.
- disruption_cost: tasks reassigned / tasks that already had an unfinished assignment
  when the event hit. Also split into necessary vs unnecessary reassignments.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Literal

from ...schemas.core.tasks import TaskRequirement
from .task_requirements_evaluator import score_checklist, task_output_text

Snapshot = Mapping[str, Any]

_FINISHED = {"completed", "failed"}


@dataclass(frozen=True)
class TeamChangeEvent:
    timestep: int
    action: Literal["add", "remove"]
    agent_id: str
    # Fixed in advance in the scenario spec, never derived from the run. By task name.
    affected_tasks: tuple[str, ...]


@dataclass(frozen=True)
class TeamChangeSpec:
    events: tuple[TeamChangeEvent, ...]
    # Hidden task-name -> worker ids that should hold the task. Scorer-only, never shown
    # to the manager. Optional: without an entry the correct-assignment check is skipped.
    correct_agents: Mapping[str, frozenset[str]] = field(default_factory=dict)


def _tasks_by_name(snapshot: Snapshot) -> dict[str, Mapping]:
    tasks = snapshot.get("tasks") or {}
    task_list = list(tasks.values()) if isinstance(tasks, Mapping) else list(tasks)
    return {t["name"]: t for t in task_list}


def _scoreable(reqs: list[TaskRequirement] | None) -> bool:
    """A checklist can be scored only if it is non-empty and every item has a pattern."""
    return bool(reqs) and all(r.pattern is not None for r in reqs)


def _status(task: Mapping) -> str:
    return str(task.get("status", "")).lower()


def _score_task(
    name: str,
    final_tasks: Mapping[str, Mapping],
    resources: Mapping[str, Mapping],
    requirements: list[TaskRequirement],
) -> dict[str, Any]:
    """Checklist score for one task on the final state. Unfinished tasks score 0."""
    task = final_tasks[name]
    completed = _status(task) == "completed"
    text = (
        task_output_text(task.get("output_resource_ids") or [], resources)
        if completed
        else ""
    )
    if completed and text:
        result = score_checklist(requirements, text)
        passed, total, failed = result.passed, result.total, list(result.failed_keys)
    else:
        passed, total, failed = 0, len(requirements), [r.key for r in requirements]
    return {
        "task": name,
        "completed": completed,
        "passed": passed,
        "total": total,
        "score": passed / total if total else 0.0,
        "failed_keys": failed,
        "final_agent": task.get("assigned_agent_id"),
    }


def compute_team_change_metrics(
    spec: TeamChangeSpec,
    snapshots: Mapping[int, Snapshot],
    requirements_by_task: Mapping[str, list[TaskRequirement]],
) -> dict[str, Any]:
    """Compute post-change score, baseline, and disruption cost for one run.

    Args:
        spec: events with their fixed affected tasks (+ optional hidden mapping).
        snapshots: timestep -> workflow snapshot dict (needs `tasks` and `resources`).
        requirements_by_task: task name -> checklist. Every affected task needs one.
    """
    if not snapshots:
        raise ValueError("no snapshots to score")
    timesteps = sorted(snapshots)
    final = snapshots[timesteps[-1]]
    final_tasks = _tasks_by_name(final)
    resources = final.get("resources") or {}

    affected_all = {n for e in spec.events for n in e.affected_tasks}
    unknown = sorted(n for n in affected_all if n not in final_tasks)
    if unknown:
        raise KeyError(f"affected tasks not in the workflow: {unknown}")
    unscoreable = sorted(n for n in affected_all if not _scoreable(requirements_by_task.get(n)))
    if unscoreable:
        raise ValueError(f"affected tasks have no scoreable checklist: {unscoreable}")

    event_results: list[dict[str, Any]] = []
    for ev in spec.events:
        # An event's response window ends where the next event starts, so one event's
        # reassignments are never charged to another.
        next_ts = min((e.timestep for e in spec.events if e.timestep > ev.timestep), default=None)
        before = [ts for ts in timesteps if ts < ev.timestep]
        after = [
            ts
            for ts in timesteps
            if ts >= ev.timestep and (next_ts is None or ts < next_ts)
        ]
        pre_tasks = _tasks_by_name(snapshots[before[-1]]) if before else {}

        # Tasks that had an unfinished assignment when the event hit.
        already: dict[str, str] = {
            name: t["assigned_agent_id"]
            for name, t in pre_tasks.items()
            if t.get("assigned_agent_id") and _status(t) not in _FINISHED
        }

        reassigned: dict[str, str] = {}  # task -> first different agent it moved to
        for ts in after:
            post_tasks = _tasks_by_name(snapshots[ts])
            for name, pre_agent in already.items():
                if name in reassigned:
                    continue
                agent = (post_tasks.get(name) or {}).get("assigned_agent_id")
                if agent and agent != pre_agent:
                    reassigned[name] = agent

        # A reassignment is necessary if the holder left, or the hidden mapping says the
        # holder was never a correct worker for that task.
        def needs_move(name: str, pre_agent: str) -> bool:
            if ev.action == "remove" and pre_agent == ev.agent_id:
                return True
            correct = spec.correct_agents.get(name)
            return correct is not None and pre_agent not in correct

        needed = {n for n, a in already.items() if needs_move(n, a)}
        necessary = set(reassigned) & needed
        unnecessary = set(reassigned) - needed

        scored = [
            _score_task(n, final_tasks, resources, requirements_by_task[n])
            for n in ev.affected_tasks
        ]
        for row in scored:
            correct = spec.correct_agents.get(row["task"])
            row["assigned_correctly"] = (
                None if correct is None else row["final_agent"] in correct
            )

        event_results.append(
            {
                "timestep": ev.timestep,
                "action": ev.action,
                "agent_id": ev.agent_id,
                "affected": scored,
                "post_change_score": mean(r["score"] for r in scored)
                if scored
                else None,
                "already_assigned": len(already),
                "reassigned": sorted(reassigned),
                "necessary_reassigned": sorted(necessary),
                "unnecessary_reassigned": sorted(unnecessary),
                "needed_reassignment": sorted(needed),
                "disruption_cost": len(reassigned) / len(already) if already else None,
                "unnecessary_disruption_cost": len(unnecessary) / len(already)
                if already
                else None,
                "necessary_coverage": len(necessary) / len(needed) if needed else None,
            }
        )

    baseline_rows = [
        _score_task(n, final_tasks, resources, reqs)
        for n, reqs in requirements_by_task.items()
        if _scoreable(reqs) and n not in affected_all and n in final_tasks
    ]
    baseline = mean(r["score"] for r in baseline_rows) if baseline_rows else None
    post_scores = [
        e["post_change_score"] for e in event_results if e["post_change_score"] is not None
    ]
    post = mean(post_scores) if post_scores else None

    total_already = sum(e["already_assigned"] for e in event_results)
    total_reassigned = sum(len(e["reassigned"]) for e in event_results)
    total_unnecessary = sum(len(e["unnecessary_reassigned"]) for e in event_results)
    total_needed = sum(len(e["needed_reassignment"]) for e in event_results)
    total_necessary = sum(len(e["necessary_reassigned"]) for e in event_results)

    return {
        "events": event_results,
        "post_change_score": post,
        "baseline_score": baseline,
        "post_change_gap": (post - baseline)
        if post is not None and baseline is not None
        else None,
        "disruption_cost": total_reassigned / total_already if total_already else None,
        "unnecessary_disruption_cost": total_unnecessary / total_already
        if total_already
        else None,
        "necessary_coverage": total_necessary / total_needed if total_needed else None,
    }
