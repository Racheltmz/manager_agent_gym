"""
Legal M&A acquisition scenario (Pydantic-based) aligned with ICAAP example flow.

Mid-Market Tech Acquisition – end-to-end workflow from intake to signing/closing.
"""

from uuid import uuid4, UUID

from manager_agent_gym.schemas.core.workflow import Workflow
from manager_agent_gym.schemas.core.tasks import Task, TaskRequirement
from manager_agent_gym.schemas.core.base import TaskStatus
from manager_agent_gym.schemas.preferences import Constraint


# Affected tasks (each is the target of one roster event; see team_change_spec.py). Every other
# leaf task is a control.
TASK_LEGAL_DD_CONTRACTS = "Legal Diligence – Material Contracts, IP, & Privacy"
TASK_REG_ASSESSMENT = "Regulatory & Antitrust Assessment (HSR/CFIUS)"
TASK_STRUCTURE_TAX = "Deal Structure & Tax Planning"
TASK_DRAFTING = "Drafting – SPA and Schedules (v1)"
TASK_NEGOTIATION = "Negotiation & Redlines"
TASK_REG_FILINGS = "Regulatory Filings (HSR/CFIUS)"
TASK_CLOSING_MECHANICS = "Closing Mechanics & Bring-Down Diligence"
TASK_SIGNING = "Signing & Closing"
TASK_POST_CLOSING = "Post-Closing & Day-1 Integration Readiness"


def _req(key: str, description: str, pattern: str) -> TaskRequirement:
    return TaskRequirement(key=key, description=description, pattern=pattern)


def _gated(prefix: str, header: str, id_pat: str, id_desc: str, line_pat: str, line_desc: str,
           topic_pat: str, topic_desc: str) -> list[TaskRequirement]:
    """Gated checklist: three items only a worker holding the private format can pass, plus a
    topic item any competent worker passes. A task passes only if all four items pass."""
    return [
        _req(f"{prefix}_header", "Opens with the required document header.", header),
        _req(f"{prefix}_ids", id_desc, id_pat),
        _req(f"{prefix}_line", line_desc, line_pat),
        _req(f"{prefix}_topic", topic_desc, topic_pat),
    ]


def create_workflow() -> Workflow:
    """Create a Legal M&A workflow using the shared Pydantic schemas.

    Mirrors the ICAAP example structure: constructs a `Workflow`, registers
    `Task`s with dependencies and subtasks, and attaches governance `Constraint`s.
    """

    workflow = Workflow(
        name="Mid-Market Tech Acquisition – Legal M&A",
        workflow_goal=(
            """
            Objective: Coordinate end-to-end legal workstreams for a mid-market tech acquisition and
            reach signing/closing within ~90 days while preserving key customer relationships and
            minimizing regulatory risk.

            Primary deliverables:
            - SPA drafts and a redline history with change rationales and crisp decision memos
            - Evidence-linked disclosure schedules and consent lists mapped to diligence artifacts
            - HSR submission (and CFIUS notice if elected) with waiting-period tracking and mitigations
            - Funds-flow, sources/uses, signature packets, and a complete closing set with bring-down plan
            - Risk register, RAID log, weekly status cadence, and board/committee approvals

            Acceptance criteria (aligned with evaluators):
            - Drafting completeness/consistency across SPA core sections with coherent fallback ladders
            - Disclosure schedules are precise, current, and cite supporting evidence from the data room
            - Funds-flow and closing set are execution-ready; bring-down confirmations planned
            - HSR/CFIUS filings prepared and submitted as required; third-party consents actively managed
            - Governance artifacts captured; no hard gating items outstanding at close

            Team alignment (see team configuration and timeline):
            - AI agents only. Workers differ by the house formats they hold; the roster changes on a
              predefined schedule (specialists join, two workers leave once their work is done)
            - Preference dynamics emphasize early momentum (speed), then raise quality and compliance as signing approaches.
            """
        ),
        owner_id=uuid4(),
    )

    # T1: Intake & objectives
    t1 = Task(
        id=UUID(int=2000),
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
            id=UUID(int=2100),
            name="Stakeholder Kickoff & Deal Memo v0",
            description="Initial stakeholder session; produce v0 deal memo and RAID seed.",
            status=TaskStatus.PENDING,
            requirements=[
                _req("t1a_memo", "Mentions the deal memo.", r"deal memo"),
                _req("t1a_raid", "Seeds a RAID log.", r"RAID"),
            ],
            estimated_duration_hours=3.0,
            estimated_cost=600.0,
        ),
        Task(
            id=UUID(int=2101),
            name="Dataroom Structure & Permissions",
            description="Create secure dataroom, access controls, and audit trail.",
            status=TaskStatus.PENDING,
            estimated_duration_hours=2.0,
            estimated_cost=400.0,
        ),
    ]

    # T2: Governance readiness
    t2 = Task(
        id=UUID(int=2001),
        name="Authority & Governance Readiness",
        description=(
            "Map approvals/decision rights; draft resolutions; confirm conflicts and engagements."
        ),
        status=TaskStatus.PENDING,
        requirements=[
            _req("t2_resolutions", "Drafts resolutions.", r"resolution"),
            _req("t2_conflicts", "Confirms conflicts or engagements.", r"conflict|engagement"),
        ],
        dependency_task_ids=[t1.id],
        estimated_duration_hours=5.0,
        estimated_cost=1000.0,
    )

    # T3: Diligence scope and RFIs
    t3 = Task(
        id=UUID(int=2002),
        name="Diligence Scope & RFI Program",
        description=(
            "Define diligence scope (legal/financial/tax/commercial/IP/privacy/HR/security),"
            " issue RFIs, and establish evidence standards with provenance."
        ),
        status=TaskStatus.PENDING,
        requirements=[
            _req("t3_rfi", "Issues RFIs.", r"\bRFIs?\b"),
            _req("t3_evidence", "Sets evidence standards or provenance.", r"evidence standard|provenance"),
        ],
        dependency_task_ids=[t1.id],
        estimated_duration_hours=8.0,
        estimated_cost=1600.0,
    )

    # T4: Financial diligence (QoE/WC)
    t4 = Task(
        id=UUID(int=2003),
        name="Financial Diligence – QoE & Working Capital",
        description=(
            "Coordinate QoE and WC analysis; inform price, earnout metrics, and SPA drafting."
        ),
        status=TaskStatus.PENDING,
        requirements=[
            _req("t4_qoe", "Covers quality of earnings.", r"quality of earnings|\bQoE\b"),
            _req("t4_wc", "Covers working capital.", r"working capital"),
        ],
        dependency_task_ids=[t3.id],
        estimated_duration_hours=10.0,
        estimated_cost=2000.0,
    )

    # T5: Corporate/equity/litigation diligence
    t5 = Task(
        id=UUID(int=2004),
        name="Legal Diligence – Corporate, Equity, & Litigation",
        description=(
            "Verify corporate standing, cap table, equity plans, disputes; summarize exposures."
        ),
        status=TaskStatus.PENDING,
        requirements=[
            _req("t5_cap", "Covers the cap table or equity plans.", r"cap(italization)? table|equity plan"),
            _req("t5_disputes", "Covers disputes or litigation.", r"litigation|dispute"),
        ],
        dependency_task_ids=[t3.id],
        estimated_duration_hours=9.0,
        estimated_cost=1800.0,
    )

    # T6: Contracts/IP/privacy diligence
    t6 = Task(
        id=UUID(int=2005),
        name=TASK_LEGAL_DD_CONTRACTS,
        description=(
            "Review key contracts (consents/MFN/termination), IP chain-of-title/OSS, and privacy posture."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t6", r"IP-CHAIN/v2",
            r"\bIP-\d{3}\b", "Numbers each finding IP-001, IP-002, ...",
            r"OSS-VERDICT:\s*(CLEAR|FLAGGED|BLOCKED)", "Ends with an OSS-VERDICT line.",
            r"chain[- ]of[- ]title|open[- ]source|\bOSS\b|\bMFN\b|consent", "Covers contracts, IP or privacy topics.",
        ),
        dependency_task_ids=[t3.id],
        estimated_duration_hours=12.0,
        estimated_cost=2400.0,
    )

    # T7: Regulatory & antitrust assessment
    t7 = Task(
        id=UUID(int=2006),
        name=TASK_REG_ASSESSMENT,
        description=(
            "Assess HSR reportability and CFIUS triggers; outline filing timeline and risk-sharing."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t7", r"HSR-SCREEN/v4",
            r"FILING-PATH:\s*(HSR-ONLY|HSR\+CFIUS|NONE)", "States the FILING-PATH.",
            r"WAIT-DAYS:\s*\d+", "States the WAIT-DAYS.",
            r"HSR|antitrust|CFIUS", "Covers HSR, antitrust or CFIUS.",
        ),
        dependency_task_ids=[t1.id, t3.id],
        estimated_duration_hours=6.0,
        estimated_cost=1200.0,
    )

    # T8: Structure & tax planning
    t8 = Task(
        id=UUID(int=2007),
        name=TASK_STRUCTURE_TAX,
        description=(
            "Select structure (asset/stock/merger), elections, and rollover/earnout mechanics; draft step-plan."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t8", r"STEP-PLAN/v3",
            r"STEP-\d{2}:", "Numbers each step STEP-01:, STEP-02:, ...",
            r"ELECTION:\s*(338\(h\)\(10\)|336\(e\)|NONE)", "States the ELECTION.",
            r"asset|stock|merger", "Compares asset, stock or merger structures.",
        ),
        dependency_task_ids=[t4.id, t5.id, t6.id, t7.id],
        estimated_duration_hours=8.0,
        estimated_cost=1600.0,
    )

    # T9: Financing and RWI
    t9 = Task(
        id=UUID(int=2008),
        name="Financing Workstream (Debt/RWI)",
        description=(
            "Secure debt commitments; coordinate RWI underwriting; align with SPA conditionality."
        ),
        status=TaskStatus.PENDING,
        requirements=[
            _req("t9_debt", "Covers debt commitments.", r"debt commitment|commitment paper"),
            _req("t9_rwi", "Covers RWI underwriting.", r"\bRWI\b|representations (and|&) warranties insurance"),
        ],
        dependency_task_ids=[t4.id, t8.id],
        estimated_duration_hours=7.0,
        estimated_cost=1400.0,
    )

    # T10: Drafting – SPA v1 and schedules
    t10 = Task(
        id=UUID(int=2009),
        name=TASK_DRAFTING,
        description=(
            "Produce SPA v1 reflecting structure and diligence; seed disclosure schedules and consent lists."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t10", r"SCHED-INDEX/v2",
            r"\bSCH-\d{3}\b", "Numbers each schedule entry SCH-001, SCH-002, ...",
            r"EVIDENCE-LINK:\s*DR-\d{3}", "Links each exception with an EVIDENCE-LINK.",
            r"\bSPA\b|disclosure schedule", "Covers the SPA or disclosure schedules.",
        ),
        dependency_task_ids=[t5.id, t6.id, t8.id],
        estimated_duration_hours=10.0,
        estimated_cost=2200.0,
    )

    # T11: Negotiation and redlines
    t11 = Task(
        id=UUID(int=2010),
        name=TASK_NEGOTIATION,
        description=(
            "Iterative redlines with clear rationales and issue resolution; exec decision memos."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t11", r"REDLINE-RATIONALE/v2",
            r"\bGG-\d{2}:", "Numbers each give-get GG-01:, GG-02:, ...",
            r"TRADE-PACKAGE:\s*\S+", "Names a TRADE-PACKAGE.",
            r"redline|rationale|give", "Covers redlines and rationales.",
        ),
        dependency_task_ids=[t10.id],
        estimated_duration_hours=8.0,
        estimated_cost=1600.0,
    )

    # T12: Regulatory filings
    t12 = Task(
        id=UUID(int=2011),
        name=TASK_REG_FILINGS,
        description=(
            "Prepare/file HSR and any CFIUS notices; track requests and waiting periods."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t12", r"FILING-TRACKER/v1",
            r"\bREQ-\d{3}\b", "Numbers each agency request REQ-001, REQ-002, ...",
            r"WAITING-PERIOD-END:\s*\d{4}-\d{2}-\d{2}", "States the WAITING-PERIOD-END date.",
            r"HSR|CFIUS", "Covers HSR or CFIUS filings.",
        ),
        dependency_task_ids=[t7.id, t10.id, t11.id],
        estimated_duration_hours=6.0,
        estimated_cost=1200.0,
    )

    # T13: Closing mechanics & bring‑down
    t13 = Task(
        id=UUID(int=2012),
        name=TASK_CLOSING_MECHANICS,
        description=(
            "Build closing checklist; finalize consents and funds flow; bring-down reps/covenants."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t13", r"FUNDS-FLOW/v5",
            r"\bWIRE-\d{3}\b", "Numbers each wire WIRE-001, WIRE-002, ...",
            r"TIEOUT:\s*(BALANCED|UNBALANCED)", "States the sources/uses TIEOUT.",
            r"consent|bring-down|closing checklist", "Covers consents, bring-down or the closing checklist.",
        ),
        dependency_task_ids=[t9.id, t11.id, t12.id],
        estimated_duration_hours=7.0,
        estimated_cost=1400.0,
    )

    # T14: Signing & closing
    t14 = Task(
        id=UUID(int=2013),
        name=TASK_SIGNING,
        description=(
            "Execute signatures; confirm conditions precedent; release funds; circulate closing set."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t14", r"CLOSING-SET/v2",
            r"\bCS-\d{3}\b", "Numbers each closing-set item CS-001, CS-002, ...",
            r"SIGPACK:\s*(COMPLETE|PENDING)", "States the SIGPACK status.",
            r"signature|conditions precedent|closing set", "Covers signatures, conditions precedent or the closing set.",
        ),
        dependency_task_ids=[t13.id],
        estimated_duration_hours=4.0,
        estimated_cost=800.0,
    )

    # T15: Post‑closing & Day‑1
    t15 = Task(
        id=UUID(int=2014),
        name=TASK_POST_CLOSING,
        description=(
            "Track covenants (escrow/earnout/indemnities); ensure Day‑1 legal/commercial readiness."
        ),
        status=TaskStatus.PENDING,
        requirements=_gated(
            "t15", r"TAX-COV-LEDGER/v1",
            r"\bTC-\d{3}\b", "Numbers each covenant TC-001, TC-002, ...",
            r"ESCROW-RELEASE:\s*\d{4}-\d{2}-\d{2}", "States the ESCROW-RELEASE date.",
            r"escrow|earn-?out|indemnit", "Covers escrow, earnout or indemnities.",
        ),
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
        t6,
        t7,
        t8,
        t9,
        t10,
        t11,
        t12,
        t13,
        t14,
        t15,
    ]:
        workflow.add_task(task)

    # Governance and compliance constraints
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
                    "Financing Workstream (Debt/RWI)",
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
