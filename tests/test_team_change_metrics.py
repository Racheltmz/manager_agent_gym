"""Tests for team-membership non-stationarity metrics (docs/team_non_stationarity/metrics.md).

Scenario used throughout (timesteps 0-6):
  A  control, finished early by w0
  D  control, running on w2 the whole time
  B  specialist case: gated on new worker w3's format, unassigned until w3 joins
  C  running-task case: running on w1 when w3 joins; best action is to hand it to w3
  E  leave-affected: unassigned gated task; w1 leaves (idle once C is handed over) and
     the task must go to the remaining holder w3
Events: w3 joins at t2 (affects B, C); w1 leaves at t5 (affects E).
"""

import copy

import pytest

from manager_agent_gym.core.evaluation.task_requirements_evaluator import (
    score_checklist,
    task_output_text,
)
from manager_agent_gym.core.evaluation.team_change_metrics import (
    TeamChangeEvent,
    TeamChangeSpec,
    compute_team_change_metrics,
)
from manager_agent_gym.schemas.core.tasks import TaskRequirement


def fmt(task_name):
    return f"FMT-{task_name}: new-worker format"  # only w3 knows this format


def reqs(name):
    return [
        TaskRequirement(key=f"{name}_fmt", description="d", pattern=rf"^FMT-{name}:"),
        TaskRequirement(key=f"{name}_text", description="d", pattern="format"),
    ]


REQS = {
    "A": [TaskRequirement(key="a_ok", description="d", pattern="done")],
    "D": [TaskRequirement(key="d_ok", description="d", pattern="done")],
    "B": reqs("B"),
    "C": reqs("C"),
    "E": reqs("E"),
}
SPEC = TeamChangeSpec(
    events=(
        TeamChangeEvent(2, "add", "w3", ("B", "C")),
        TeamChangeEvent(5, "remove", "w1", ("E",)),
    ),
    correct_agents={t: frozenset({"w3"}) for t in "BCE"},
    cases={"B": "specialist", "C": "running_task"},
)


def task(name, agent=None, status="pending", has_output=False):
    return {
        "id": name,
        "name": name,
        "assigned_agent_id": agent,
        "status": status,
        "output_resource_ids": [f"r_{name}"] if has_output else [],
    }


def snap(ts, tasks, outputs=None):
    return {
        "timestep": ts,
        "tasks": {t["id"]: copy.deepcopy(t) for t in tasks},  # no sharing between timesteps
        "resources": {f"r_{k}": {"content": v} for k, v in (outputs or {}).items()},
    }


def perfect_history():
    a = task("A", "w0", "completed", True)
    early = {"A": "done"}
    pre = [a, task("B"), task("C", "w1", "running"), task("D", "w2", "running"), task("E")]
    joined = [a, task("B", "w3", "running"), task("C", "w3", "running"), task("D", "w2", "running"), task("E")]
    mid = [a, task("B", "w3", "completed", True), task("C", "w3", "running"), task("D", "w2", "running"), task("E")]
    left = [a, task("B", "w3", "completed", True), task("C", "w3", "running"), task("D", "w2", "running"), task("E", "w3", "running")]
    done = [
        a,
        task("B", "w3", "completed", True),
        task("C", "w3", "completed", True),
        task("D", "w2", "completed", True),
        task("E", "w3", "completed", True),
    ]
    return {
        0: snap(0, pre, early),
        1: snap(1, pre, early),
        2: snap(2, joined, early),
        3: snap(3, joined, early),
        4: snap(4, mid, {**early, "B": fmt("B")}),
        5: snap(5, left, {**early, "B": fmt("B")}),
        6: snap(
            6,
            done,
            {"A": "done", "B": fmt("B"), "C": fmt("C"), "D": "done", "E": fmt("E")},
        ),
    }


def test_checklist_score_is_fraction_of_items_passed():
    r = score_checklist(REQS["B"], "FMT-B: wrong")
    assert (r.passed, r.total, r.score) == (1, 2, 0.5)
    assert r.failed_keys == ("B_text",)


def test_output_text_joins_resources_and_skips_missing():
    res = {"r1": {"content": "x"}, "r2": {"content": "y"}}
    assert task_output_text(["r1", "r2", "missing"], res) == "x\ny"


def test_perfect_manager_scores_one_with_zero_disruption():
    m = compute_team_change_metrics(SPEC, perfect_history(), REQS)
    assert m["post_change_score"] == 1.0
    assert m["baseline_score"] == 1.0
    assert m["post_change_gap"] == 0.0
    assert m["disruption_cost"] == 0.0
    assert m["control_tasks"] == 2 and m["control_disrupted"] == []  # controls: A and D
    assert all(r["assigned_correctly"] for e in m["events"] for r in e["affected"])


def test_moving_an_affected_task_is_not_disruption():
    m = compute_team_change_metrics(SPEC, perfect_history(), REQS)
    join = m["events"][0]
    assert join["affected_reassigned"] == ["C"]  # handed to w3: informational only
    assert m["disruption_cost"] == 0.0


def test_thrashing_a_control_task_is_disruption():
    h = perfect_history()
    for ts in (3, 4, 5, 6):  # D moved off w2, who never left, after the first event
        h[ts]["tasks"]["D"]["assigned_agent_id"] = "w3"
    m = compute_team_change_metrics(SPEC, h, REQS)
    assert m["control_disrupted"] == ["D"]
    assert m["disruption_cost"] == 0.5  # 1 disrupted of 2 control tasks (A, D)


def test_a_move_is_counted_once_when_events_share_a_timestep():
    spec = TeamChangeSpec(
        events=(
            TeamChangeEvent(2, "add", "w3", ("B",)),
            TeamChangeEvent(2, "add", "w4", ("C",)),
            TeamChangeEvent(5, "remove", "w1", ("E",)),
        ),
        correct_agents=SPEC.correct_agents,
        cases=SPEC.cases,
    )
    h = perfect_history()
    for ts in (3, 4, 5, 6):
        h[ts]["tasks"]["D"]["assigned_agent_id"] = "w3"
    m = compute_team_change_metrics(spec, h, REQS)
    assert m["control_disrupted"] == ["D"] and m["disruption_cost"] == 0.5  # not 3 events x 1 move


def test_a_move_before_the_first_event_is_not_counted():
    h = perfect_history()
    for ts in range(1, 7):  # D changes workers between t0 and t1; the first event is at t2
        h[ts]["tasks"]["D"]["assigned_agent_id"] = "w3"
    m = compute_team_change_metrics(SPEC, h, REQS)
    assert m["control_disrupted"] == [] and m["disruption_cost"] == 0.0


def test_reassigning_a_finished_control_task_is_not_a_move():
    h = perfect_history()
    for ts in (3, 4, 5, 6):  # A finished with w0 at t0; a later (recorded) reassign changes nothing
        h[ts]["tasks"]["A"]["assigned_agent_id"] = "w3"
    m = compute_team_change_metrics(SPEC, h, REQS)
    assert m["control_disrupted"] == [] and m["disruption_cost"] == 0.0


def test_first_assignment_is_not_a_move_and_composites_are_not_controls():
    h = perfect_history()
    for ts, snapshot in h.items():
        snapshot["tasks"]["F"] = task("F", "w2" if ts >= 3 else None, "running" if ts >= 3 else "pending")
        snapshot["tasks"]["P"] = {**task("P"), "subtasks": [{"name": "c1"}]}  # composite parent
    m = compute_team_change_metrics(SPEC, h, REQS)
    assert m["control_tasks"] == 3  # A, D, F (P is composite)
    assert m["control_disrupted"] == [] and m["disruption_cost"] == 0.0


def test_ignoring_the_new_worker_fails_the_gate_without_disruption():
    h = perfect_history()
    for ts in (2, 3, 4, 5, 6):  # C is left with w1, which writes the wrong format
        h[ts]["tasks"]["C"]["assigned_agent_id"] = "w1"
    h[6]["resources"]["r_C"] = {"content": "plain output with format"}
    m = compute_team_change_metrics(SPEC, h, REQS)
    row = next(r for r in m["events"][0]["affected"] if r["task"] == "C")
    assert row["score"] == 0.5
    assert row["assigned_correctly"] is False
    assert m["post_change_score"] < 1.0
    assert m["disruption_cost"] == 0.0  # a missed opportunity, not a disruption


def test_assigning_the_gated_task_to_the_departed_worker_scores_zero():
    h = perfect_history()
    for ts in (5, 6):  # manager keeps pointing E at w1, who left, so it never runs
        h[ts]["tasks"]["E"].update(assigned_agent_id="w1", status="pending", output_resource_ids=[])
    m = compute_team_change_metrics(SPEC, h, REQS)
    leave = m["events"][1]
    assert leave["affected"][0]["score"] == 0.0
    assert leave["post_change_score"] == 0.0


def test_results_are_reported_per_case():
    h = perfect_history()
    h[6]["resources"]["r_C"] = {"content": "plain output with format"}  # C half right
    m = compute_team_change_metrics(SPEC, h, REQS)
    assert m["by_case"] == {
        "leave": {"tasks": 1, "post_change_score": 1.0},
        "running_task": {"tasks": 1, "post_change_score": 0.5},
        "specialist": {"tasks": 1, "post_change_score": 1.0},
    }


def test_removed_affected_task_scores_zero_instead_of_crashing():
    h = perfect_history()
    for ts in (4, 5, 6):  # the manager deletes the specialist-case task from the graph
        del h[ts]["tasks"]["B"]
    m = compute_team_change_metrics(SPEC, h, REQS)
    row = next(r for r in m["events"][0]["affected"] if r["task"] == "B")
    assert row["score"] == 0.0 and row["completed"] is False


def test_event_at_first_timestep_counts_moves_from_the_start():
    spec = TeamChangeSpec(events=(TeamChangeEvent(0, "add", "w3", ("B", "C")),))
    h = perfect_history()
    for ts in range(1, 7):
        h[ts]["tasks"]["D"]["assigned_agent_id"] = "w3"  # moved at t1, after the event at t0
    m = compute_team_change_metrics(spec, h, REQS)
    assert m["control_tasks"] == 3 and m["control_disrupted"] == ["D"]  # controls: A, D, E
    assert m["disruption_cost"] == pytest.approx(1 / 3)


def test_no_control_tasks_gives_no_disruption_cost():
    spec = TeamChangeSpec(events=(TeamChangeEvent(2, "add", "w3", ("A", "B", "C", "D", "E")),))
    reqs = {**REQS}
    m = compute_team_change_metrics(spec, perfect_history(), reqs)
    assert m["control_tasks"] == 0 and m["disruption_cost"] is None


def test_affected_task_never_in_the_workflow_raises():
    spec = TeamChangeSpec(events=(TeamChangeEvent(2, "add", "w3", ("nope",)),))
    with pytest.raises(KeyError):
        compute_team_change_metrics(spec, perfect_history(), REQS)


def test_affected_task_without_checklist_raises():
    with pytest.raises(ValueError):
        compute_team_change_metrics(SPEC, perfect_history(), {k: v for k, v in REQS.items() if k != "B"})


def test_prose_only_control_checklists_are_left_out_of_the_baseline():
    legacy = TaskRequirement(key="prose", description="no pattern")
    m = compute_team_change_metrics(SPEC, perfect_history(), {**REQS, "D": [legacy]})
    assert m["baseline_score"] == 1.0  # only A is scored
    with pytest.raises(ValueError):
        compute_team_change_metrics(SPEC, perfect_history(), {**REQS, "B": [legacy]})


def test_requirements_are_collected_from_subtasks_too():
    from manager_agent_gym.core.evaluation.task_requirements_evaluator import (
        flatten_tasks,
        requirements_by_task_name,
    )
    from manager_agent_gym.schemas.core.tasks import Task

    leaf = Task(name="leaf", description="d", requirements=reqs("L"))
    parent = Task(name="parent", description="d", subtasks=[leaf])
    plain = Task(name="plain", description="d")
    assert [t.name for t in flatten_tasks([parent, plain])] == ["parent", "leaf", "plain"]
    assert list(requirements_by_task_name([parent, plain])) == ["leaf"]
