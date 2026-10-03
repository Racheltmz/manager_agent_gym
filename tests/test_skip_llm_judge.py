"""skip_llm_judge: rubrics that need an LLM are not scheduled, rule-based ones still run."""

import asyncio

from manager_agent_gym.core.evaluation.validation_engine import ValidationEngine
from manager_agent_gym.schemas.preferences.evaluator import Evaluator
from manager_agent_gym.schemas.preferences.rubric import RunCondition, WorkflowRubric
from tests.helpers.stubs import make_empty_workflow


def evaluator():
    return Evaluator(
        name="ev",
        rubrics=[
            WorkflowRubric(name="rule", max_score=1.0, evaluator_function=lambda wf: 1.0),
            WorkflowRubric(name="judge", max_score=1.0, llm_prompt="Score this workflow."),
        ],
    )


def run(skip):
    engine = ValidationEngine(seed=0, skip_llm_judge=skip)
    return asyncio.run(
        engine.evaluate_timestep(
            workflow=make_empty_workflow(),
            timestep=0,
            cadence=RunCondition.EACH_TIMESTEP,
            communications=None,
            manager_actions=None,
            workflow_evaluators=[evaluator()],
        )
    )


def test_judge_rubrics_are_not_scheduled_when_skipped():
    result = run(skip=True)
    names = [r.name for r in result.evaluation_results[0].rubric_scores]
    assert names == ["rule"]
    assert result.evaluation_results[0].aggregated_score == 1.0
