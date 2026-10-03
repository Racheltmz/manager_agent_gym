"""The engine hands the manager the roster changes that have happened so far (team runs only)."""

import pytest
from uuid import uuid4

from manager_agent_gym.core.execution.engine import WorkflowExecutionEngine
from manager_agent_gym.core.workflow_agents.registry import AgentRegistry
from manager_agent_gym.core.workflow_agents.stakeholder_agent import StakeholderAgent
from manager_agent_gym.schemas.config import OutputConfig
from manager_agent_gym.schemas.core.tasks import Task
from manager_agent_gym.schemas.core.workflow import Workflow
from manager_agent_gym.schemas.preferences.preference import PreferenceWeights
from manager_agent_gym.schemas.workflow_agents import AIAgentConfig
from manager_agent_gym.schemas.workflow_agents.stakeholder import StakeholderConfig
from tests.helpers.stubs import ManagerNoOp, StubAgent

pytestmark = pytest.mark.integration


class RecordingManager(ManagerNoOp):
    """Records, per timestep, the roster changes the engine had given it before it acted."""

    def __init__(self):
        super().__init__()
        self.seen: dict[int, list[tuple[int, str, str]]] = {}

    async def step(self, *args, current_timestep, **kwargs):
        self.seen[current_timestep] = [(c.timestep, c.action, c.agent_id) for c in self._roster_changes]
        return await super().step(*args, current_timestep=current_timestep, **kwargs)


def cfg(agent_id):
    return AIAgentConfig(agent_id=agent_id, system_prompt="A worker prompt.", agent_description=f"{agent_id} d",
                         agent_capabilities=["c"])


async def run(tmp_path, monkeypatch, team_awareness):
    w = Workflow(name="roster", workflow_goal="d", owner_id=uuid4())
    w.add_task(Task(name="A", description="d"))
    reg = AgentRegistry()
    monkeypatch.setattr(
        reg, "register_ai_agent",
        lambda config, tools: reg.register_agent(StubAgent(agent_id=config.agent_id, agent_type="ai")),
    )
    reg.schedule_agent_add(0, cfg("w0"), "initial roster")
    reg.schedule_agent_add(2, cfg("w1"), "scale out")
    reg.schedule_agent_remove(4, "w1", "scale in")
    stakeholder = StakeholderAgent(config=StakeholderConfig(
        agent_id="stakeholder", agent_type="stakeholder", system_prompt="Stakeholder prompt.", model_name="o3",
        name="S", role="Owner", initial_preferences=PreferenceWeights(preferences=[]),
        agent_description="S", agent_capabilities=["S"]))
    manager = RecordingManager()
    engine = WorkflowExecutionEngine(
        workflow=w, agent_registry=reg, manager_agent=manager, stakeholder_agent=stakeholder,
        output_config=OutputConfig(base_output_dir=tmp_path, create_run_subdirectory=False),
        enable_timestep_logging=False, enable_final_metrics_logging=False, max_timesteps=6, seed=1,
        team_awareness=team_awareness,
    )
    stakeholder.is_available = False
    await engine.run_full_execution()
    return manager


@pytest.mark.asyncio
async def test_manager_sees_changes_only_once_they_have_happened_and_not_the_initial_roster(tmp_path, monkeypatch):
    m = await run(tmp_path, monkeypatch, True)
    assert m.seen[1] == []                                   # t=0 roster is the baseline, not a change
    assert m.seen[2] == [(2, "joined", "w1")]                # shown at the timestep it happens
    assert m.seen[3] == [(2, "joined", "w1")]                # and kept afterwards
    assert m.seen[4] == [(2, "joined", "w1"), (4, "left", "w1")]


@pytest.mark.asyncio
async def test_manager_sees_nothing_when_awareness_is_off(tmp_path, monkeypatch):
    m = await run(tmp_path, monkeypatch, False)
    assert all(v == [] for v in m.seen.values())
