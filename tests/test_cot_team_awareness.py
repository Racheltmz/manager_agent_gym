"""Chain-of-thought manager: roster changes and failed-action causes in the prompt (team runs only)."""

import asyncio
from uuid import uuid4

from manager_agent_gym.core.manager_agent.structured_manager import ChainOfThoughtManagerAgent
from manager_agent_gym.core.workflow_agents.registry import AgentRegistry
from manager_agent_gym.schemas.execution.manager import ManagerObservation, RosterChange, RunningTaskInfo
from manager_agent_gym.schemas.execution.manager_actions import ActionResult
from manager_agent_gym.schemas.preferences.preference import Preference, PreferenceWeights
from manager_agent_gym.schemas.workflow_agents import AIAgentConfig
from manager_agent_gym.schemas.workflow_agents.stakeholder import StakeholderPublicProfile


def manager(team_awareness):
    m = ChainOfThoughtManagerAgent(
        preferences=PreferenceWeights(preferences=[Preference(name="quality", weight=1.0)])
    )
    m.set_team_awareness(team_awareness)
    return m


def obs(timestep, changes=(), running=()):
    return ManagerObservation(
        timestep=timestep,
        workflow_summary="",
        workflow_id=uuid4(),
        execution_state="running",
        task_status_counts={},
        ready_task_ids=[],
        running_task_ids=[],
        completed_task_ids=[],
        failed_task_ids=[],
        available_agent_metadata=[],
        recent_messages=[],
        workflow_progress=0.0,
        constraints=[],
        task_ids=[],
        resource_ids=[],
        agent_ids=[],
        roster_changes=list(changes),
        running_task_info=list(running),
        stakeholder_profile=StakeholderPublicProfile(display_name="S", role="Owner"),
    )


JOIN = RosterChange(timestep=6, action="joined", agent_id="ip_counsel", description="IP lawyer",
                    capabilities=["Validates IP", "Drafts schedules"], reason="scale out: more capacity")
LEAVE = RosterChange(timestep=30, action="left", agent_id="tax_ai", description="Tax aide",
                     capabilities=["Models elections"], reason="scale in: pool shrinks")


def record(m, timestep, action_type, summary, success):
    m.record_action(ActionResult(action_type=action_type, summary=summary, kind="mutation",
                                 data={}, timestep=timestep, success=success))


def test_roster_block_marks_only_the_current_change_as_new():
    m = manager(True)
    text = m._prepare_context(obs(30, [JOIN, LEAVE]))
    assert "### Roster Changes" in text
    assert "[NEW] t=30 LEFT (no longer assignable) tax_ai" in text and "Models elections" in text
    assert "t=6 JOINED ip_counsel" in text and "[NEW] t=6" not in text
    assert text.index("t=30 LEFT") < text.index("t=6 JOINED")  # newest first
    assert "re-evaluate unassigned and pending work" in text


def test_log_without_a_new_change_has_no_instruction_and_nothing_future_appears():
    text = manager(True)._prepare_context(obs(7, [JOIN]))
    assert "t=6 JOINED ip_counsel" in text and "[NEW]" not in text
    assert "re-evaluate" not in text and "tax_ai" not in text


def test_no_roster_block_when_awareness_is_off_or_there_are_no_changes():
    assert "Roster Changes" not in manager(False)._prepare_context(obs(6, [JOIN]))
    assert "Roster Changes" not in manager(True)._prepare_context(obs(3))


def test_history_shows_flag_and_cause_only_for_failures():
    m = manager(True)
    record(m, 1, "assign_task", "Assigned T1 to a", True)
    record(m, 2, "assign_task", "Failed: agent zz is not on the roster", False)
    text = m._prepare_context(obs(3))
    assert "t=1: assign_task [SUCCESS] — Result: Assigned T1 to a" in text
    assert "t=2: assign_task [FAILED] — Cause: Failed: agent zz is not on the roster" in text
    assert "Cause" not in text.split("[SUCCESS]")[1].split("\n")[0]
    assert "do not repeat an action that failed for the same reason" in text


def test_history_without_failures_has_no_failure_instruction():
    m = manager(True)
    record(m, 1, "assign_task", "Assigned T1 to a", True)
    assert "FAILED" not in m._prepare_context(obs(2))


def test_history_format_is_unchanged_when_awareness_is_off():
    m = manager(False)
    record(m, 2, "assign_task", "Failed: x", False)
    text = m._prepare_context(obs(3))
    assert "t=2: assign_task — Result: Failed: x" in text and "[FAILED]" not in text


def test_observation_carries_changes_only_when_awareness_is_on():
    for enabled in (True, False):
        m = manager(enabled)
        m.set_roster_changes([JOIN])
        o = asyncio.run(m.create_observation(
            workflow=_empty_workflow(), execution_state="running",
            stakeholder_profile=StakeholderPublicProfile(display_name="S", role="Owner"),
            current_timestep=6, running_tasks={}, completed_task_ids=set(), failed_task_ids=set()))
        assert (o.roster_changes == [JOIN]) is enabled


def _empty_workflow():
    from tests.helpers.stubs import make_empty_workflow
    return make_empty_workflow()


def test_registry_logs_joins_and_a_leavers_profile(monkeypatch):
    from types import SimpleNamespace

    reg = AgentRegistry()
    # Avoid building a real AIAgent (needs the Agents SDK and optional clients)
    monkeypatch.setattr(
        reg, "register_ai_agent",
        lambda config, tools: reg._agents.__setitem__(config.agent_id, SimpleNamespace(config=config, agent_id=config.agent_id)),
    )
    cfg = AIAgentConfig(agent_id="w1", system_prompt="private prompt", agent_description="Worker one",
                        agent_capabilities=["does x"])
    reg.schedule_agent_add(6, cfg, "scale out")
    reg.schedule_agent_remove(9, "w1", "scale in")
    reg.apply_scheduled_changes_for_timestep(6)
    reg.apply_scheduled_changes_for_timestep(9)
    assert [(c["timestep"], c["action"], c["agent_id"]) for c in reg.change_log] == [(6, "joined", "w1"), (9, "left", "w1")]
    left = reg.change_log[1]
    assert left["description"] == "Worker one" and left["capabilities"] == ["does x"]
    assert "private prompt" not in str(reg.change_log)  # system prompts are never exposed


def running(n, name="Negotiation & Redlines", agent="redline_explainer", t=11):
    return RunningTaskInfo(task_id=uuid4(), name=name, agent_id=agent, started_timestep=t) if n == 1 else [
        RunningTaskInfo(task_id=uuid4(), name=f"Task {i}", agent_id="a", started_timestep=i) for i in range(n)
    ]


def test_running_tasks_block_shows_name_worker_and_start_timestep():
    text = manager(True)._prepare_context(obs(12, running=[running(1)]))
    assert "### Running Tasks" in text
    assert "- Negotiation & Redlines (id " in text
    assert "| worker redline_explainer | started t=11" in text


def test_running_tasks_block_is_capped_and_off_without_awareness():
    text = manager(True)._prepare_context(obs(12, running=running(13)))
    assert text.count("| worker a |") == 10 and "(+3 more running)" in text
    assert "### Running Tasks" not in manager(False)._prepare_context(obs(12, running=[running(1)]))
    assert "### Running Tasks" not in manager(True)._prepare_context(obs(12))


def test_observation_lists_running_tasks_with_worker_and_start_timestep_when_aware():
    from manager_agent_gym.schemas.core.base import TaskStatus
    from manager_agent_gym.schemas.core.tasks import Task

    for enabled in (True, False):
        m = manager(enabled)
        w = _empty_workflow()
        t = Task(name="Drafting", description="d", status=TaskStatus.RUNNING, assigned_agent_id="schedules_builder",
                 started_timestep=12)
        w.add_task(t)
        o = asyncio.run(m.create_observation(
            workflow=w, execution_state="running",
            stakeholder_profile=StakeholderPublicProfile(display_name="S", role="Owner"),
            current_timestep=13, running_tasks={t.id: None}, completed_task_ids=set(), failed_task_ids=set()))
        got = [(r.name, r.agent_id, r.started_timestep) for r in o.running_task_info]
        assert got == ([("Drafting", "schedules_builder", 12)] if enabled else [])
