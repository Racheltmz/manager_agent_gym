"""A pricing failure must not turn a finished task into a failure (ML-050)."""

from types import SimpleNamespace

from manager_agent_gym.core.workflow_agents import ai_agent as mod
from manager_agent_gym.core.workflow_agents.ai_agent import AIAgent


def agent(model="some-unpriced-model"):
    stub = AIAgent.__new__(AIAgent)  # skip __init__: no SDK agent or API key needed
    stub.config = SimpleNamespace(model_name=model)
    return stub


def result(input_tokens=10, output_tokens=5):
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens, input_tokens_details=None)
    return SimpleNamespace(context_wrapper=SimpleNamespace(usage=usage))


def test_unpriceable_model_costs_zero_instead_of_raising(monkeypatch):
    def boom(**kwargs):
        raise ValueError("model not mapped")

    monkeypatch.setattr(mod, "cost_per_token", boom)
    assert agent()._calculate_accurate_cost(result()) == 0.0


def test_missing_usage_costs_zero(monkeypatch):
    assert agent()._calculate_accurate_cost(SimpleNamespace()) == 0.0


def test_priceable_model_is_still_priced(monkeypatch):
    monkeypatch.setattr(mod, "cost_per_token", lambda **kw: (0.25, 0.5))
    assert agent()._calculate_accurate_cost(result()) == 0.75
