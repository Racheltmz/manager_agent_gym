"""
Team-change spec for the legal_m_and_a team-membership scenario (docs/team_non_stationarity/metrics.md,
Scenario contract). Scorer-only: the manager never sees this.

Affected tasks are fixed in advance and listed by name. Every other task is a control.
`correct_agents` is derived from gate validation (docs/team_non_stationarity/benchmark.md, Gate
validation): the workers that pass a task's checklist and are on the roster after its event.
"""

from manager_agent_gym.core.evaluation.team_change_metrics import TeamChangeEvent, TeamChangeSpec

from .workflow import (
    TASK_CLOSING_MECHANICS,
    TASK_DRAFTING,
    TASK_LEGAL_DD_CONTRACTS,
    TASK_NEGOTIATION,
    TASK_POST_CLOSING,
    TASK_REG_ASSESSMENT,
    TASK_REG_FILINGS,
    TASK_SIGNING,
    TASK_STRUCTURE_TAX,
)


def create_team_change_spec() -> TeamChangeSpec:
    return TeamChangeSpec(
        events=(
            # Joins (specialist case): each task is gated on its joiner's house format.
            TeamChangeEvent(6, "add", "ip_counsel", (TASK_LEGAL_DD_CONTRACTS,)),
            TeamChangeEvent(6, "add", "antitrust_analyst", (TASK_REG_ASSESSMENT,)),
            TeamChangeEvent(6, "add", "tax_structuring_ai", (TASK_STRUCTURE_TAX,)),
            TeamChangeEvent(12, "add", "schedules_builder", (TASK_DRAFTING,)),
            TeamChangeEvent(12, "add", "redline_explainer", (TASK_NEGOTIATION,)),
            TeamChangeEvent(18, "add", "regulatory_counsel", (TASK_REG_FILINGS,)),
            TeamChangeEvent(25, "add", "funds_flow_coordinator", (TASK_CLOSING_MECHANICS,)),
            # Leaves: the later unassigned task is gated on a format the leaver shares with a
            # worker who stays.
            TeamChangeEvent(30, "remove", "tax_structuring_ai", (TASK_POST_CLOSING,)),
            TeamChangeEvent(39, "remove", "redline_explainer", (TASK_SIGNING,)),
        ),
        correct_agents={
            TASK_LEGAL_DD_CONTRACTS: frozenset({"ip_counsel"}),
            TASK_REG_ASSESSMENT: frozenset({"antitrust_analyst"}),
            TASK_STRUCTURE_TAX: frozenset({"tax_structuring_ai"}),
            TASK_DRAFTING: frozenset({"schedules_builder"}),
            TASK_NEGOTIATION: frozenset({"redline_explainer"}),
            TASK_REG_FILINGS: frozenset({"regulatory_counsel"}),
            TASK_CLOSING_MECHANICS: frozenset({"funds_flow_coordinator"}),
            TASK_POST_CLOSING: frozenset({"tax_partner"}),
            TASK_SIGNING: frozenset({"closing_checklist_manager"}),
        },
        cases={
            TASK_LEGAL_DD_CONTRACTS: "specialist",
            TASK_REG_ASSESSMENT: "specialist",
            TASK_STRUCTURE_TAX: "specialist",
            TASK_DRAFTING: "specialist",
            TASK_NEGOTIATION: "specialist",
            TASK_REG_FILINGS: "specialist",
            TASK_CLOSING_MECHANICS: "specialist",
        },
    )
