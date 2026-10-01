"""Tests for team-membership non-stationarity metrics (docs/team_non_stationarity/metrics.md)."""

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

# Only worker w3 knows the "FMT-" output format, so B and C are gated on w3.
GOOD_B = "FMT-B: new-worker format"
GOOD_C = "FMT-C: new-worker format"
REQS = {
    "A": [TaskRequirement(key="a_ok", description="d", pattern="done")],
    "B": [
        TaskRequirement(key="b_fmt", description="d", pattern=r"^FMT-B:"),
        TaskRequirement(key="b_text", description="d", pattern="format"),
    ],
    "C": [
        TaskRequirement(key="c_fmt", description="d", pattern=r"^FMT-C:"),
        TaskRequirement(key="c_text", description="d", pattern="format"),
    ],
    "D": [TaskRequirement(key="d_ok", description="d", pattern="done")],
}
SPEC = TeamChangeSpec(
    events=(
        TeamChangeEvent(2, "add", "w3", ("B",)),  # join: B is gated on the new worker
        TeamChangeEvent(4, "remove", "w1", ("C",)),  # leave: w1 holds C mid-task
    ),
    correct_agents={"B": frozenset({"w3"}), "C": frozenset({"w3"})},
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
        "tasks": {t["id"]: t for t in tasks},
        "resources": {f"r_{k}": {"content": v} for k, v in (outputs or {}).items()},
    }


def perfect_history():
    """A done early; D runs on w2 throughout; C runs on w1 until it leaves at t4."""
    a = task("A", "w0", "completed", True)
    early = {"A": "done"}
    return {
        0: snap(0, [a, task("B"), task("C", "w1", "running"), task("D", "w2", "running")], early),
        1: snap(1, [a, task("B"), task("C", "w1", "running"), task("D", "w2", "running")], early),
        2: snap(2, [a, task("B", "w3", "running"), task("C", "w1", "running"), task("D", "w2", "running")], early),
        3: snap(3, [a, task("B", "w3", "running"), task("C", "w1", "running"), task("D", "w2", "running")], early),
        4: snap(
            4,
            [a, task("B", "w3", "completed", True), task("C", "w3", "running"), task("D", "w2", "running")],
            {"A": "done", "B": GOOD_B},
        ),
        5: snap(
            5,
            [a, task("B", "w3", "completed", True), task("C", "w3", "completed", True), task("D", "w2", "completed", True)],
            {"A": "done", "B": GOOD_B, "C": GOOD_C, "D": "done"},
        ),
    }


def test_checklist_score_is_fraction_of_items_passed():
    r = score_checklist(REQS["B"], "FMT-B: wrong")
    assert (r.passed, r.total, r.score) == (1, 2, 0.5)
    assert r.failed_keys == ("b_text",)


def test_output_text_joins_resources_and_skips_missing():
    res = {"r1": {"content": "x"}, "r2": {"content": "y"}}
    assert task_output_text(["r1", "r2", "missing"], res) == "x\ny"


def test_perfect_manager_scores_one_and_moves_only_orphaned_task():
    m = compute_team_change_metrics(SPEC, perfect_history(), REQS)
    assert m["post_change_score"] == 1.0
    assert m["baseline_score"] == 1.0
    join, leave = m["events"]
    assert join["reassigned"] == []  # B was newly assigned, not reassigned
    assert leave["reassigned"] == ["C"]
    assert leave["necessary_reassigned"] == ["C"]
    assert leave["unnecessary_reassigned"] == []
    assert leave["already_assigned"] == 3  # B, C and D (A already completed)
    assert leave["disruption_cost"] == pytest.approx(1 / 3)
    assert leave["unnecessary_disruption_cost"] == 0.0
    assert leave["necessary_coverage"] == 1.0
    assert all(r["assigned_correctly"] for e in m["events"] for r in e["affected"])


def test_thrashing_manager_pays_unnecessary_disruption():
    h = perfect_history()
    h[4]["tasks"]["D"]["assigned_agent_id"] = "w3"  # D moved off w2, who never left
    m = compute_team_change_metrics(SPEC, h, REQS)
    leave = m["events"][1]
    assert leave["unnecessary_reassigned"] == ["D"]
    assert leave["unnecessary_disruption_cost"] == pytest.approx(1 / 3)
    assert leave["disruption_cost"] == pytest.approx(2 / 3)


def test_ignoring_the_new_worker_fails_the_gate():
    h = perfect_history()
    for ts in (2, 3, 4, 5):  # B goes to generic w0, which writes the wrong format
        h[ts]["tasks"]["B"]["assigned_agent_id"] = "w0"
    for ts in (4, 5):
        h[ts]["resources"]["r_B"] = {"content": "plain output with format"}
    m = compute_team_change_metrics(SPEC, h, REQS)
    row = m["events"][0]["affected"][0]
    assert row["score"] == 0.5
    assert row["assigned_correctly"] is False
    assert m["post_change_score"] < 1.0


def test_dropping_the_orphaned_task_scores_zero_and_zero_coverage():
    h = perfect_history()
    for ts in (4, 5):  # C still points at the departed worker and never finishes
        h[ts]["tasks"]["C"].update(assigned_agent_id="w1", status="running", output_resource_ids=[])
    m = compute_team_change_metrics(SPEC, h, REQS)
    leave = m["events"][1]
    assert leave["affected"][0]["score"] == 0.0
    assert leave["necessary_coverage"] == 0.0
    assert leave["reassigned"] == []
    assert leave["post_change_score"] == 0.0


def test_event_at_first_timestep_has_no_prior_assignments():
    spec = TeamChangeSpec(events=(TeamChangeEvent(0, "add", "w3", ("B",)),))
    m = compute_team_change_metrics(spec, perfect_history(), REQS)
    assert m["events"][0]["already_assigned"] == 0
    assert m["events"][0]["disruption_cost"] is None


def test_affected_task_missing_from_workflow_raises():
    spec = TeamChangeSpec(events=(TeamChangeEvent(2, "add", "w3", ("nope",)),))
    with pytest.raises(KeyError):
        compute_team_change_metrics(spec, perfect_history(), REQS)


def test_affected_task_without_checklist_raises():
    reqs = {k: v for k, v in REQS.items() if k != "B"}
    with pytest.raises(ValueError):
        compute_team_change_metrics(SPEC, perfect_history(), reqs)


def test_legacy_prose_only_items_are_excluded_from_baseline_but_not_affected_tasks():
    legacy = TaskRequirement(key="prose", description="no pattern")
    reqs = {**REQS, "D": [legacy]}  # D is a control with an unscoreable checklist
    m = compute_team_change_metrics(SPEC, perfect_history(), reqs)
    assert m["baseline_score"] == 1.0  # only A is scored
    with pytest.raises(ValueError):
        compute_team_change_metrics(SPEC, perfect_history(), {**REQS, "B": [legacy]})
