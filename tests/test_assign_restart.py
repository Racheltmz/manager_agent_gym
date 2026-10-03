"""Strict assignment (team runs): reassigning a RUNNING task requests a restart; terminal and composite tasks are rejected."""

import asyncio
from uuid import uuid4

from manager_agent_gym.schemas.core.base import TaskStatus
from manager_agent_gym.schemas.core.tasks import Task
from manager_agent_gym.schemas.core.workflow import Workflow
from manager_agent_gym.schemas.execution.manager_actions import (
    AssignAllPendingTasksAction,
    AssignmentPair,
    AssignTaskAction,
    AssignTasksToAgentsAction,
)
from tests.helpers.stubs import StubAgent


def world(strict, status=TaskStatus.PENDING, assigned="a"):
    w = Workflow(name="w", workflow_goal="d", owner_id=uuid4())
    t = Task(name="T", description="d", status=status, assigned_agent_id=assigned)
    w.add_task(t)
    w.add_agent(StubAgent(agent_id="a"))
    w.add_agent(StubAgent(agent_id="b"))
    w.strict_assignment = strict
    return w, t


def assign(w, t, agent):
    return asyncio.run(AssignTaskAction(reasoning="r", task_id=str(t.id), agent_id=agent, success=None, result_summary=None).execute(w))


def test_running_task_reassigned_to_another_agent_requests_a_restart():
    w, t = world(True, TaskStatus.RUNNING)
    r = assign(w, t, "b")
    assert r.success and r.kind == "mutation" and r.data.get("outcome") == "restarted"
    assert t.assigned_agent_id == "b" and t.restart_requested is True
    assert "cancelled" in r.summary and "restarts from scratch" in r.summary


def test_reassign_to_the_same_agent_is_a_noop_not_a_restart():
    w, t = world(True, TaskStatus.RUNNING)
    r = assign(w, t, "a")
    assert r.success and r.kind == "noop" and not t.restart_requested and "No change" in r.summary


def test_completed_failed_and_composite_tasks_are_rejected():
    for status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        w, t = world(True, status)
        r = assign(w, t, "b")
        assert not r.success and r.kind == "failed_action" and t.assigned_agent_id == "a"
    w, t = world(True)
    t.subtasks = [Task(name="child", description="d")]
    r = assign(w, t, "b")
    assert not r.success and "composite" in r.summary and t.assigned_agent_id == "a"


def test_pending_task_is_simply_reassigned_without_a_restart():
    w, t = world(True, TaskStatus.PENDING)
    r = assign(w, t, "b")
    assert r.success and t.assigned_agent_id == "b" and not t.restart_requested


def test_legacy_mode_is_unchanged():
    w, t = world(False, TaskStatus.COMPLETED)
    r = assign(w, t, "b")
    assert r.success and t.assigned_agent_id == "b" and not t.restart_requested
    w, t = world(False, TaskStatus.RUNNING)
    assign(w, t, "b")
    assert not t.restart_requested


def test_bulk_assign_reports_restarts_unchanged_and_causes():
    w, t = world(True, TaskStatus.RUNNING)
    done = Task(name="D", description="d", status=TaskStatus.COMPLETED)
    w.add_task(done)
    action = AssignTasksToAgentsAction(
        reasoning="r", success=None, result_summary=None,
        assignments=[AssignmentPair(task_id=t.id, agent_id="b"), AssignmentPair(task_id=done.id, agent_id="b")],
    )
    r = asyncio.run(action.execute(w))
    assert r.success and r.data["restarted_count"] == 1 and "restarted" in r.summary
    assert "already finished or failed" in r.summary and t.restart_requested


def test_assign_all_pending_skips_composites_only_in_strict_mode():
    for strict, expected in ((True, None), (False, "b")):
        w, t = world(strict, assigned=None)
        t.subtasks = [Task(name="child", description="d")]
        asyncio.run(AssignAllPendingTasksAction(reasoning="r", agent_id="b", success=None, result_summary=None).execute(w))
        assert t.assigned_agent_id == expected
