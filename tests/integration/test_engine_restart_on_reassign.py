"""Reassigning a RUNNING task cancels the old run and the new agent redoes it from scratch."""

import asyncio
import pytest
from uuid import uuid4

from manager_agent_gym.core.execution.engine import WorkflowExecutionEngine
from manager_agent_gym.core.workflow_agents.registry import AgentRegistry
from manager_agent_gym.core.workflow_agents.stakeholder_agent import StakeholderAgent
from manager_agent_gym.schemas.config import OutputConfig
from manager_agent_gym.schemas.core import Resource
from manager_agent_gym.schemas.core.base import TaskStatus
from manager_agent_gym.schemas.core.tasks import Task
from manager_agent_gym.schemas.core.workflow import Workflow
from manager_agent_gym.schemas.execution.manager_actions import AssignTaskAction, NoOpAction
from manager_agent_gym.schemas.preferences.preference import PreferenceWeights
from manager_agent_gym.schemas.workflow_agents.stakeholder import StakeholderConfig
from tests.helpers.stubs import ManagerNoOp, StubAgent

pytestmark = pytest.mark.integration


class SlowOldWorker(StubAgent):
    """Runs far longer than the test; records whether its run was cancelled."""

    cancelled = False

    async def execute_task(self, task, resources):
        try:
            return await super().execute_task(task, resources)
        except asyncio.CancelledError:
            SlowOldWorker.cancelled = True
            raise


class HandOverManager(ManagerNoOp):
    """At timestep 1 (the task is RUNNING with the old worker) hands it to the new worker."""

    def __init__(self, task_id):
        super().__init__()
        self.task_id = task_id

    async def step(self, *args, current_timestep, **kwargs):
        if current_timestep == 1:
            await asyncio.sleep(0.05)  # the old worker runs while the manager "thinks", as with a real LLM call
            return AssignTaskAction(reasoning="hand over", task_id=str(self.task_id), agent_id="new",
                                    success=None, result_summary=None)
        return NoOpAction(reasoning="noop", success=True, result_summary="noop")


async def run(tmp_path, strict):
    SlowOldWorker.cancelled = False
    w = Workflow(name="restart", workflow_goal="d", owner_id=uuid4())
    t = Task(name="T", description="d", assigned_agent_id="old")
    w.add_task(t)
    w.add_agent(SlowOldWorker(agent_id="old", delay_s=30.0))
    w.add_agent(StubAgent(agent_id="new", resources_to_emit=[Resource(name="by-new", description="d", content="new worker output", content_type="text/plain")]))
    stakeholder = StakeholderAgent(config=StakeholderConfig(
        agent_id="stakeholder", agent_type="stakeholder", system_prompt="Stakeholder prompt.", model_name="o3",
        name="S", role="Owner", initial_preferences=PreferenceWeights(preferences=[]),
        agent_description="S", agent_capabilities=["S"]))
    engine = WorkflowExecutionEngine(
        workflow=w, agent_registry=AgentRegistry(), manager_agent=HandOverManager(t.id), stakeholder_agent=stakeholder,
        output_config=OutputConfig(base_output_dir=tmp_path, create_run_subdirectory=False),
        enable_timestep_logging=False, enable_final_metrics_logging=False, max_timesteps=4, seed=1,
        restart_on_reassign=strict,
    )
    stakeholder.is_available = False
    await asyncio.wait_for(engine.run_full_execution(), timeout=20)
    return w, w.tasks[t.id]


@pytest.mark.asyncio
async def test_running_task_is_cancelled_and_redone_by_the_new_agent(tmp_path):
    w, task = await run(tmp_path, strict=True)
    assert SlowOldWorker.cancelled
    assert task.status == TaskStatus.COMPLETED and task.assigned_agent_id == "new"
    assert task.restart_count == 1 and not task.restart_requested
    assert any("Restarted" in n for n in task.execution_notes)
    assert task.started_timestep == 1  # restarted at the timestep of the handover
    assert [w.resources[r].content for r in task.output_resource_ids] == ["new worker output"]
