"""
Legal M&A acquisition scenario — AHT (autoscaling / heterogeneous-team) benchmark variant.

Derived from examples/end_to_end_examples/legal_m_and_a/workflow.py by applying the two
grafts from docs/benchmark_aht/benchmark_conversion.md steps 4-5 (diagrammed in
examples/end_to_end_examples_aht/legal_m_and_a/AHT_DIFF.md §1):

  - T6 ("Legal Diligence – Material Contracts, IP, & Privacy") split into T6a/T6b —
    the Objective-1 test: two similarly-scoped subtasks with disjoint `requirements`
    checklists, each clearable only by a specific trait-tuple pool (team.py).
  - T13b ("Post-Signing Privacy/IP Bring-Down") added at a non-adjacent point, reusing the
    same pool/tuple as T6b — the Objective-2 test.

Every other task (T1-T5, T7-T12, T14-T15) is content-identical to the original; only task
`id`s changed (new UUID range, since both scenario modules can coexist). `requirements` on
T6a/T6b/T13b describe deterministic checks by `key` — the actual checker-function registry
(`task_requirements_evaluator.py`, plan §4) is not wired up yet; that's the deliberate next
step, not done in this pass.
"""

from uuid import uuid4, UUID

from manager_agent_gym.schemas.core.workflow import Workflow
from manager_agent_gym.schemas.core.tasks import Task, TaskRequirement
from manager_agent_gym.schemas.core.base import TaskStatus
from manager_agent_gym.schemas.preferences import Constraint


def create_workflow() -> Workflow:
    """Create the Legal M&A AHT-variant workflow."""

    workflow = Workflow(
        name="Mid-Market Tech Acquisition – Legal M&A (AHT variant)",
        workflow_goal=(
            """
            Objective: Coordinate end-to-end legal workstreams for a mid-market tech acquisition and
            reach signing/closing within ~90 days while preserving key customer relationships and
            minimizing regulatory risk.

            AHT-benchmark note: team staffing is modeled as enterprise autoscaling capability pools
            (docs/benchmark_aht/autoscaling_team_churn.md), not a fixed cast — see team.py. T6a/T6b test
            whether the manager assigns the correct pool to two similarly-scoped subtasks
            (Objective 1); T13b tests whether a confirmed-fit pool is reused correctly on a later,
            differently-worded task (Objective 2).

            Primary deliverables:
            - SPA drafts and a redline history with change rationales and crisp decision memos
            - Evidence-linked disclosure schedules and consent lists mapped to diligence artifacts
            - HSR submission (and CFIUS notice if elected) with waiting-period tracking and mitigations
            - Funds-flow, sources/uses, signature packets, and a complete closing set with bring-down plan
            - Risk register, RAID log, weekly status cadence, and board/committee approvals

            Team alignment (see team.py):
            - AI-only pools: P_intake_orchestration, P_diligence_extraction, P_deal_drafting_reasoning,
              P_privacy_reasoning, P_regulatory_reasoning, P_structure_tax_reasoning, P_closing_ops_fast
            - Preference dynamics emphasize early momentum (speed), then raise quality and compliance as signing approaches.
            """
        ),
        owner_id=uuid4(),
    )

    # T1: Intake & objectives
    t1 = Task(
        id=UUID(int=3000),
        name="Deal Intake & Objectives",
        description=(
            "Kickoff; define EV, consideration mix, must-have protections (RWI, escrow),"
            " risks, and cadence. Produce deal memo and seed risk register."
        ),
        status=TaskStatus.PENDING,
        estimated_duration_hours=6.0,
        estimated_cost=1200.0,
    )
    t1.subtasks = [
        Task(
            id=UUID(int=3100),
            name="Stakeholder Kickoff & Deal Memo v0",
            description="Initial stakeholder session; produce v0 deal memo and RAID seed.",
            status=TaskStatus.PENDING,
            estimated_duration_hours=3.0,
            estimated_cost=600.0,
        ),
        Task(
            id=UUID(int=3101),
            name="Dataroom Structure & Permissions",
            description="Create secure dataroom, access controls, and audit trail.",
            status=TaskStatus.PENDING,
            estimated_duration_hours=2.0,
            estimated_cost=400.0,
        ),
    ]

    # T2: Governance readiness
    t2 = Task(
        id=UUID(int=3001),
        name="Authority & Governance Readiness",
        description=(
            "Map approvals/decision rights; draft resolutions; confirm conflicts and engagements."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t1.id],
        estimated_duration_hours=5.0,
        estimated_cost=1000.0,
    )

    # T3: Diligence scope and RFIs
    t3 = Task(
        id=UUID(int=3002),
        name="Diligence Scope & RFI Program",
        description=(
            "Define diligence scope (legal/financial/tax/commercial/IP/privacy/HR/security),"
            " issue RFIs, and establish evidence standards with provenance."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t1.id],
        estimated_duration_hours=8.0,
        estimated_cost=1600.0,
    )

    # T4: Financial diligence (QoE/WC)
    t4 = Task(
        id=UUID(int=3003),
        name="Financial Diligence – QoE & Working Capital",
        description=(
            "Coordinate QoE and WC analysis; inform price, earnout metrics, and SPA drafting."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t3.id],
        estimated_duration_hours=10.0,
        estimated_cost=2000.0,
    )

    # T5: Corporate/equity/litigation diligence
    t5 = Task(
        id=UUID(int=3004),
        name="Legal Diligence – Corporate, Equity, & Litigation",
        description=(
            "Verify corporate standing, cap table, equity plans, disputes; summarize exposures."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t3.id],
        estimated_duration_hours=9.0,
        estimated_cost=1800.0,
    )

    # T6a: Contract Terms Review — Objective-1 split, pool: P_deal_drafting_reasoning (reasoning_gpt4o)
    t6a = Task(
        id=UUID(int=3005),
        name="Contract Terms Review",
        description=(
            "Review the target's key commercial contracts for consent-to-assign and "
            "most-favored-nation triggers, and flag any provisions that could disrupt "
            "continuity of the counterparty relationship after closing; summarize "
            "negotiation-relevant terms and open issues for the SPA drafting team."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t3.id],
        estimated_duration_hours=7.0,
        estimated_cost=1400.0,
        requirements=[
            TaskRequirement(
                key="contract_terms_indemnity_covenant_cited",
                description=(
                    "Output resource text explicitly references indemnity and covenant terms "
                    "(deterministic: substring match for 'indemnif' and 'covenant')."
                ),
            ),
            TaskRequirement(
                key="contract_terms_termination_mechanics_cited",
                description=(
                    "Output resource text references termination mechanics "
                    "(deterministic: substring match for 'termination')."
                ),
            ),
        ],
        requirements_pass_threshold=2,
        objective="objective_1",
    )

    # T6b: IP & Privacy Compliance Review — Objective-1 split, pool: P_privacy_reasoning (privacy_reasoning_gpt4o)
    t6b = Task(
        id=UUID(int=3006),
        name="IP & Privacy Compliance Review",
        description=(
            "Assess whether the target's intellectual property can be established as cleanly "
            "owned, including any third-party or openly-licensed code embedded in the product "
            "that could create encumbrances; separately, evaluate whether the target's practices "
            "for sharing data with vendors and moving it across jurisdictions meet buyer-side "
            "expectations. Summarize exceptions for the disclosure schedules."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t3.id],
        estimated_duration_hours=7.0,
        estimated_cost=1400.0,
        requirements=[
            TaskRequirement(
                key="ip_chain_of_title_cited",
                description=(
                    "Output resource text references IP chain-of-title / OSS assignment mechanics "
                    "(deterministic: substring match for 'chain-of-title' or 'chain of title', and 'OSS')."
                ),
            ),
            TaskRequirement(
                key="privacy_dpa_cross_border_cited",
                description=(
                    "Output resource text references DPA / cross-border transfer posture "
                    "(deterministic: substring match for 'DPA' or 'data processing agreement', and 'cross-border')."
                ),
            ),
        ],
        requirements_pass_threshold=2,
        objective="objective_1",
    )

    # T7: Regulatory & antitrust assessment
    t7 = Task(
        id=UUID(int=3007),
        name="Regulatory & Antitrust Assessment (HSR/CFIUS)",
        description=(
            "Assess HSR reportability and CFIUS triggers; outline filing timeline and risk-sharing."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t1.id, t3.id],
        estimated_duration_hours=6.0,
        estimated_cost=1200.0,
    )

    # T8: Structure & tax planning
    t8 = Task(
        id=UUID(int=3008),
        name="Deal Structure & Tax Planning",
        description=(
            "Select structure (asset/stock/merger), elections, and rollover/earnout mechanics; draft step-plan."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t4.id, t5.id, t6a.id, t6b.id, t7.id],
        estimated_duration_hours=8.0,
        estimated_cost=1600.0,
    )

    # T9a: Debt Commitment Review — Objective-1 split (checkpoint 2 of 4), pool:
    # P_debt_commitment_fast (finance_counsel_ai). Resolves the T9 single-assignee/
    # two-specialty ambiguity flagged in MANAGER_WALKTHROUGH.md §3.4 by splitting it the
    # same way T6 was split, instead of leaving it as an unresolved judgment call.
    t9a = Task(
        id=UUID(int=3009),
        name="Debt Commitment Review",
        description=(
            "Review the buyer's proposed financing package for the acquisition — confirm debt "
            "commitments are firm and assess whether the credit terms among lenders could "
            "complicate closing certainty; prepare whatever closing-readiness confirmations the "
            "lenders will require."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t4.id, t8.id],
        estimated_duration_hours=4.0,
        estimated_cost=800.0,
        requirements=[
            TaskRequirement(
                key="debt_intercreditor_terms_cited",
                description=(
                    "Output resource text references intercreditor terms among lenders "
                    "(deterministic: substring match for 'intercreditor')."
                ),
            ),
            TaskRequirement(
                key="debt_solvency_certificate_cited",
                description=(
                    "Output resource text references solvency certificates as a closing "
                    "requirement (deterministic: substring match for 'solvency')."
                ),
            ),
        ],
        requirements_pass_threshold=2,
        objective="objective_1",
    )

    # T9b: RWI Insurance Packaging — Objective-1 split (checkpoint 2 of 4), pool:
    # P_rwi_ops_fast (rwi_packager). Same trait tuple as T9a (fast_gpt4o_mini) — the
    # discriminating signal is the persona's system_prompt, not the tuple label (already
    # established: capability_tier has no execution-level effect), matching the precedent
    # that P_regulatory_reasoning/P_structure_tax_reasoning also share reasoning_gpt4o.
    t9b = Task(
        id=UUID(int=3017),
        name="RWI Insurance Packaging",
        description=(
            "Prepare the insurance underwriter's submission package to support the buyer's "
            "warranty coverage — compile diligence findings the underwriter will want to see, "
            "and be ready to explain how known risk items are being handled outside the policy."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t4.id, t8.id],
        estimated_duration_hours=3.0,
        estimated_cost=600.0,
        requirements=[
            TaskRequirement(
                key="rwi_exclusions_reconciled_cited",
                description=(
                    "Output resource text references reconciling policy exclusions "
                    "(deterministic: substring match for 'exclusion')."
                ),
            ),
            TaskRequirement(
                key="rwi_risk_allocation_cited",
                description=(
                    "Output resource text references SPA risk allocation "
                    "(deterministic: substring match for 'risk allocation')."
                ),
            ),
        ],
        requirements_pass_threshold=2,
        objective="objective_1",
    )

    # T10: Drafting – SPA v1 and schedules
    t10 = Task(
        id=UUID(int=3010),
        name="Drafting – SPA and Schedules (v1)",
        description=(
            "Produce SPA v1 reflecting structure and diligence; seed disclosure schedules and consent lists."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t5.id, t6a.id, t6b.id, t8.id],
        estimated_duration_hours=10.0,
        estimated_cost=2200.0,
    )

    # T11: Negotiation and redlines
    t11 = Task(
        id=UUID(int=3011),
        name="Negotiation & Redlines",
        description=(
            "Iterative redlines with clear rationales and issue resolution; exec decision memos."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t10.id],
        estimated_duration_hours=8.0,
        estimated_cost=1600.0,
    )

    # T12: Regulatory filings
    t12 = Task(
        id=UUID(int=3012),
        name="Regulatory Filings (HSR/CFIUS)",
        description=(
            "Prepare/file HSR and any CFIUS notices; track requests and waiting periods."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t7.id, t10.id, t11.id],
        estimated_duration_hours=6.0,
        estimated_cost=1200.0,
    )

    # T13: Closing mechanics & bring‑down
    t13 = Task(
        id=UUID(int=3013),
        name="Closing Mechanics & Bring-Down Diligence",
        description=(
            "Build closing checklist; finalize consents and funds flow; bring-down reps/covenants."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t9a.id, t9b.id, t11.id, t12.id],
        estimated_duration_hours=7.0,
        estimated_cost=1400.0,
    )

    # T13b: Post-Signing Privacy/IP Bring-Down — Objective-2 reuse task, same pool as T6b
    t13b = Task(
        id=UUID(int=3014),
        name="Post-Signing Privacy/IP Bring-Down",
        description=(
            "Reconfirm that the representations underpinning the original data-sharing and "
            "intellectual-property review still hold true as of the closing date, and flag any "
            "change in the target's posture on either front since that review for the closing set."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t13.id],
        estimated_duration_hours=3.0,
        estimated_cost=600.0,
        requirements=[
            TaskRequirement(
                key="bring_down_privacy_ip_reconfirmed",
                description=(
                    "Output resource text reconfirms privacy/IP representations as of closing "
                    "(deterministic: substring match for 'bring-down' and ('privacy' or 'IP'))."
                ),
            ),
        ],
        requirements_pass_threshold=1,
        objective="objective_2",
    )

    # T13c: Post-Signing Tax Position Reconfirmation — Objective-2 reuse task (checkpoint 4 of
    # 4), formalizing the T8->T13-bring-down tax pattern already noted as an unformalized
    # "bonus pattern" in AHT_DIFF.md. Reuses P_structure_tax_reasoning/reasoning_gpt4o (same
    # tuple as T8) — tax_partner_ai already joins at t=45 for exactly this purpose (team.py),
    # this task just makes it gradable. Name deliberately avoids "Bring-Down" (unlike T13b,
    # whose name independently leaks its checklist answer per MANAGER_WALKTHROUGH.md §3.3) —
    # learned from that mistake instead of repeating it.
    t13c = Task(
        id=UUID(int=3018),
        name="Post-Signing Tax Position Reconfirmation",
        description=(
            "Reconfirm that the tax elections and structural assumptions underpinning the deal "
            "remain accurate as of the closing date, and flag any change since the original "
            "structuring analysis."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t13.id],
        estimated_duration_hours=3.0,
        estimated_cost=600.0,
        requirements=[
            TaskRequirement(
                key="tax_election_and_earnout_reconfirmed",
                description=(
                    "Output resource text references a specific tax election and the "
                    "rollover/earnout mechanics tied to it (deterministic: substring match for "
                    "'338(h)(10)' or '336(e)', and 'rollover' or 'earnout')."
                ),
            ),
        ],
        requirements_pass_threshold=1,
        objective="objective_2",
    )

    # T14: Signing & closing
    t14 = Task(
        id=UUID(int=3015),
        name="Signing & Closing",
        description=(
            "Execute signatures; confirm conditions precedent; release funds; circulate closing set."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t13.id],
        estimated_duration_hours=4.0,
        estimated_cost=800.0,
    )

    # T15: Post‑closing & Day‑1
    t15 = Task(
        id=UUID(int=3016),
        name="Post-Closing & Day-1 Integration Readiness",
        description=(
            "Track covenants (escrow/earnout/indemnities); ensure Day‑1 legal/commercial readiness."
        ),
        status=TaskStatus.PENDING,
        dependency_task_ids=[t14.id],
        estimated_duration_hours=5.0,
        estimated_cost=1000.0,
    )

    for task in [
        t1,
        t2,
        t3,
        t4,
        t5,
        t6a,
        t6b,
        t7,
        t8,
        t9a,
        t9b,
        t10,
        t11,
        t12,
        t13,
        t13b,
        t13c,
        t14,
        t15,
    ]:
        workflow.add_task(task)

    # Governance and compliance constraints — unchanged from the original scenario
    workflow.constraints.extend(
        [
            Constraint(
                name="Board Approvals Before Signing",
                description="Acquirer and target board approvals must be executed before signing.",
                constraint_type="hard",
                enforcement_level=1.0,
                applicable_task_types=[
                    "Authority & Governance Readiness",
                    "Signing & Closing",
                ],
                metadata={},
            ),
            Constraint(
                name="HSR Acceptance Before Close",
                description=(
                    "HSR filing accepted and waiting period expired or early termination granted before closing."
                ),
                constraint_type="hard",
                enforcement_level=1.0,
                applicable_task_types=[
                    "Regulatory Filings (HSR/CFIUS)",
                    "Signing & Closing",
                ],
                metadata={},
            ),
            Constraint(
                name="No Close Without Required Consents",
                description=(
                    "All required third‑party consents listed on disclosure schedules must be obtained or waived."
                ),
                constraint_type="hard",
                enforcement_level=1.0,
                applicable_task_types=[
                    "Closing Mechanics & Bring-Down Diligence",
                    "Signing & Closing",
                ],
                metadata={},
            ),
            Constraint(
                name="Financing Sources Available",
                description=(
                    "Debt/RWI and funds flow finalized; no unsatisfied financing‑out that jeopardizes closing."
                ),
                constraint_type="hard",
                enforcement_level=1.0,
                applicable_task_types=[
                    "Debt Commitment Review",
                    "RWI Insurance Packaging",
                    "Signing & Closing",
                ],
                metadata={},
            ),
            Constraint(
                name="CFIUS Clearance If Applicable",
                description="CFIUS clearance received if mandatory or elected by the stakeholder.",
                constraint_type="hard",
                enforcement_level=1.0,
                applicable_task_types=[
                    "Regulatory Filings (HSR/CFIUS)",
                    "Signing & Closing",
                ],
                metadata={},
            ),
        ]
    )

    return workflow
