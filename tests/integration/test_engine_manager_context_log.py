"""One manager-context file per executed timestep, with the manager's input and output."""

import json
import pytest
from uuid import uuid4

from manager_agent_gym.core.execution.engine import WorkflowExecutionEngine
from manager_agent_gym.core.manager_agent import structured_manager as sm
from manager_agent_gym.core.manager_agent.structured_manager import ChainOfThoughtManagerAgent
from manager_agent_gym.core.workflow_agents.registry import AgentRegistry
from manager_agent_gym.core.workflow_agents.stakeholder_agent import StakeholderAgent
from manager_agent_gym.schemas.config import OutputConfig
from manager_agent_gym.schemas.core.tasks import Task
from manager_agent_gym.schemas.core.workflow import Workflow
from manager_agent_gym.schemas.execution.manager_actions import NoOpAction
from manager_agent_gym.schemas.preferences.preference import Preference, PreferenceWeights
from manager_agent_gym.schemas.workflow_agents.stakeholder import StakeholderConfig
from tests.helpers.stubs import ManagerNoOp, StubAgent

pytestmark = pytest.mark.integration

STEPS = 7


def build(tmp_path, manager, agent=None, timestep_logging=False):
    w = Workflow(name="ctx", workflow_goal="d", owner_id=uuid4())
    # Unassigned task: nothing ever starts, so the workflow cannot complete early
    # (with an agent, the task is pre-assigned and finishes)
    w.add_task(Task(name="T", description="d", assigned_agent_id=agent.agent_id if agent else None))
    if agent is not None:
        w.add_agent(agent)
    stakeholder = StakeholderAgent(config=StakeholderConfig(
        agent_id="stakeholder", agent_type="stakeholder", system_prompt="Stakeholder prompt.", model_name="o3",
        name="S", role="Owner", initial_preferences=PreferenceWeights(preferences=[]),
        agent_description="S", agent_capabilities=["S"]))
    out = OutputConfig(base_output_dir=tmp_path, create_run_subdirectory=False)
    engine = WorkflowExecutionEngine(
        workflow=w, agent_registry=AgentRegistry(), manager_agent=manager, stakeholder_agent=stakeholder,
        output_config=out, enable_timestep_logging=timestep_logging, enable_final_metrics_logging=False,
        max_timesteps=STEPS, seed=1,
    )
    stakeholder.is_available = False
    return engine, out


def files(out):
    return sorted(p.name for p in out.manager_context_dir.glob("timestep_*.json"))


@pytest.mark.asyncio
async def test_a_run_of_n_timesteps_writes_exactly_n_files(tmp_path):
    engine, out = build(tmp_path, ManagerNoOp(), timestep_logging=True)
    await engine.run_full_execution()
    assert files(out) == [f"timestep_{i:04d}.json" for i in range(STEPS)]
    # same count as the engine's own per-timestep files
    assert len(list(out.timestep_dir.glob("timestep_0*.json"))) == STEPS


@pytest.mark.asyncio
async def test_a_run_that_completes_early_writes_one_file_per_executed_timestep(tmp_path):
    engine, out = build(tmp_path, ManagerNoOp(), agent=StubAgent(agent_id="w"))
    results = await engine.run_full_execution()
    assert engine.workflow.is_complete()
    assert len(files(out)) == len(results) < STEPS


@pytest.mark.asyncio
async def test_file_holds_input_prompts_output_action_and_result_for_the_cot_manager(tmp_path, monkeypatch):
    seen = []

    async def fake_generate(system_prompt, user_prompt, response_type, seed, model, **kw):
        seen.append((system_prompt, user_prompt, model))
        return type("Parsed", (), {"action": NoOpAction(reasoning="waiting", success=True, result_summary="idle")})()

    monkeypatch.setattr(sm, "generate_structured_response", fake_generate)
    manager = ChainOfThoughtManagerAgent(
        preferences=PreferenceWeights(preferences=[Preference(name="quality", weight=1.0)]), model_name="gpt-5-mini")
    engine, out = build(tmp_path, manager)
    await engine.run_full_execution()

    assert len(files(out)) == STEPS == len(seen)
    for t in (0, STEPS - 1):
        data = json.loads((out.manager_context_dir / f"timestep_{t:04d}.json").read_text())
        assert data["timestep"] == t and data["model"] == "gpt-5-mini"
        assert data["input"]["system_prompt"] == seen[t][0] and data["input"]["user_prompt"] == seen[t][1]
        assert f"timestep {t}" in data["input"]["user_prompt"]
        assert data["output"]["action_type"] == "noop" and data["output"]["reasoning"] == "waiting"
        assert data["result"]["success"] is True


@pytest.mark.asyncio
async def test_managers_that_do_not_record_prompts_still_get_a_file_with_output(tmp_path):
    engine, out = build(tmp_path, ManagerNoOp())
    await engine.run_full_execution()
    data = json.loads((out.manager_context_dir / "timestep_0003.json").read_text())
    assert data["input"] is None and "does not record" in data["input_note"] and data["output"]["action_type"] == "noop"


@pytest.mark.asyncio
async def test_logging_can_be_turned_off(tmp_path):
    engine, out = build(tmp_path, ManagerNoOp())
    engine.log_manager_context = False
    await engine.run_full_execution()
    assert not out.manager_context_dir.exists() or files(out) == []
