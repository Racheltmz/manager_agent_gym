"""
Shared trait-tuple pool for the AHT (autoscaling / heterogeneous-team) benchmark variants.

See docs/benchmark_aht/open_aht_benchmark_plan_prev.md §3.3. Concrete (model_name, model_version,
capability_tier) instances are defined exactly once here and pulled by name into each
scenario's team.py — scenarios never invent tuple values inline.
"""

from manager_agent_gym.schemas.workflow_agents import AIAgentConfig

TRAIT_POOL: dict[str, tuple[str, str, str]] = {
    "reasoning_gpt4o": ("gpt-4o", "latest", "reasoning"),
    "fast_gpt4o_mini": ("gpt-4o-mini", "latest", "fast"),
    "extraction_gpt4o": ("gpt-4o", "latest", "extraction"),
    # Added for legal_m_and_a's T6 split (see examples/end_to_end_examples_aht/legal_m_and_a/AHT_DIFF.md §3) —
    # T6b/T13b need a tuple genuinely distinct from reasoning_gpt4o so the two Objective-1
    # subtasks are actually discriminating, not just differently worded.
    "privacy_reasoning_gpt4o": ("gpt-4o", "latest", "privacy_reasoning"),
}


def with_trait_tuple(agent: AIAgentConfig, tuple_name: str) -> AIAgentConfig:
    """Return a copy of `agent` with model_name/model_version/capability_tier set from TRAIT_POOL."""
    model_name, model_version, capability_tier = TRAIT_POOL[tuple_name]
    return agent.model_copy(
        update={
            "model_name": model_name,
            "model_version": model_version,
            "capability_tier": capability_tier,
        }
    )
