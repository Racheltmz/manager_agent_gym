"""
Legal M&A – team-membership non-stationarity variant: AI-only workers and a join/leave timeline.

Every worker holds a house format only it (or a stated pair) follows, written into its
`system_prompt`. Gated tasks in workflow.py check for those formats, so a task passes only if a
worker that holds the matching format did it. Declared capabilities say which kind of deliverable a
worker has a house format for, but never the exact strings, which stay in the prompt.

Exported helpers:
  - create_legal_mna_team_configs() -> dict of worker configs (plus the stakeholder proxy)
  - create_team_timeline() -> {timestep: [(action, agent_cfg, reason)]}
"""

from manager_agent_gym.schemas.workflow_agents import AIAgentConfig, StakeholderConfig
from manager_agent_gym.schemas.preferences.preference import (
    PreferenceWeights,
    Preference,
)


# Benchmark model setup: manager gpt-5-mini, workers gpt-5-mini, stakeholder gpt-5.4-mini (medium reasoning).
WORKER_MODEL = "gpt-5-mini"
STAKEHOLDER_MODEL = "gpt-5.4-mini"
STAKEHOLDER_REASONING = "medium"


def _ai(agent_id: str, role: str, house: str, description: str, capabilities: list[str]) -> AIAgentConfig:
    """A worker whose prompt is its role plus the house format or rule only it follows."""
    return AIAgentConfig(
        agent_id=agent_id,
        agent_type="ai",
        system_prompt=f"{role} {house}",
        model_name=WORKER_MODEL,
        agent_description=description,
        agent_capabilities=capabilities,
    )


# House formats shared by exactly two workers (the two leave-affected tasks need a holder who stays).
TAX_LEDGER_FORMAT = (
    "House format for post-closing covenant ledgers (use it whenever you deliver a post-closing covenant "
    "or Day-1 tax deliverable): the first line is exactly `TAX-COV-LEDGER/v1`; list one covenant per row, "
    "numbered `TC-001`, `TC-002`, and so on; include a line `ESCROW-RELEASE: YYYY-MM-DD` with the escrow release date."
)
CLOSING_SET_FORMAT = (
    "House format for closing sets (use it whenever you deliver a signing or closing set, or a "
    "signature-packet index): the first line is exactly `CLOSING-SET/v2`; list one item per row, numbered "
    "`CS-001`, `CS-002`, and so on; include a line `SIGPACK: COMPLETE` or `SIGPACK: PENDING`."
)


def create_legal_mna_team_configs():
    """AI worker configurations for Legal M&A (human roles from the source are converted to AI)."""

    # === Initial roster ===
    project_coordinator = _ai(
        "project_coordinator",
        "You run the deal room and status cadence: create trackers for issues, RFIs, and decisions; "
        "publish weekly summaries with risks, owners, and ETAs; and keep artifacts consistent across drafts.",
        "House rule: every weekly status summary ends with a final line `PMO-CADENCE: wkNN`, where NN is the week number.",
        "Orchestrator who keeps trackers, decisions, and artifacts consistent across drafts.",
        [
            "Runs issue/RFI/decision trackers",
            "Publishes weekly summaries",
            "Surfaces risks with owners/ETAs",
            "Maintains artifact consistency",
        ],
    )
    lead_mna_partner = _ai(
        "lead_mna_partner",
        "You are the Lead M&A Partner: principal negotiator and sign-off authority for the acquirer. You set "
        "negotiation strategy, approve trade-offs, and ensure board and executive alignment.",
        "House rule: every decision memo ends with a final line `PARTNER-DECISION: APPROVE`, "
        "`PARTNER-DECISION: REVISE` or `PARTNER-DECISION: ESCALATE`.",
        "Principal negotiator who sets strategy, approves trade-offs, and keeps board/executives aligned.",
        [
            "Sets negotiation strategy",
            "Approves deal trade-offs",
            "Ensures board/executive alignment",
            "Signs legal positions and escalations",
        ],
    )
    senior_mna_associate = _ai(
        "senior_mna_associate",
        "You are the Senior M&A Associate: you draft SPA sections, coordinate disclosure schedules, run "
        "diligence calls, and synthesize positions into decision memos.",
        "House rule: issue lists are tables whose rows read `ISSUE-<n> | <owner> | <fallback position>`.",
        "Senior associate who drafts SPA sections, coordinates schedules, and synthesizes positions.",
        [
            "Drafts SPA and ancillary documents",
            "Coordinates disclosure schedules",
            "Runs diligence calls",
            "Prepares decision memos",
        ],
    )
    diligence_reader = _ai(
        "diligence_reader",
        "You are a Diligence Reader that triages data-room documents, extracts facts into a structured index, "
        "flags risk-relevant findings (assignment/consent, MFN, exclusivity, change-of-control, IP chain-of-title), "
        "and links evidence to disclosure schedules.",
        "House rule: every index entry reads `DOC-IDX-<n> | <fact> | <risk level>`.",
        "Reader who turns the data room into a structured index and flags material risks with citations.",
        [
            "Extracts facts into structured index",
            "Flags risk-relevant findings",
            "Links evidence to schedules",
            "Maintains citations and versions",
        ],
    )
    deal_counsel_ai = _ai(
        "deal_counsel_ai",
        "You are an AI Deal Counsel focused on drafting and negotiating the Share Purchase Agreement (SPA). "
        "You propose market-standard positions, track redline deltas with rationales, harmonize defined terms, "
        "and maintain issue lists with fallbacks across indemnities, covenants, and termination mechanics.",
        "House rule: SPA drafts open with the line `SPA-DRAFT v<n>` and list open points as `OPEN-<n>:`.",
        "AI counsel who drafts market-standard SPA language, tracks gives/gets, and harmonizes terms.",
        [
            "Drafts and negotiates SPA sections",
            "Tracks redline deltas with rationales",
            "Maintains issue lists with fallbacks",
            "Harmonizes definitions across documents",
        ],
    )
    acquirer_gc = _ai(
        "acquirer_gc",
        "You are the Acquirer General Counsel, stakeholder proxy for legal risk appetite: you confirm governance, "
        "approvals, and final sign-offs, and escalate trade-off decisions to executives and the board.",
        "House rule: every sign-off ends with a final line `GC-SIGNOFF: GRANTED` or `GC-SIGNOFF: WITHHELD`.",
        "Acquirer GC who sets legal risk appetite, confirms governance, and approves sign-offs.",
        [
            "Sets legal risk appetite",
            "Confirms governance and approvals",
            "Escalates trade-offs to executives/board",
            "Grants final sign-offs",
        ],
    )
    tax_partner = _ai(
        "tax_partner",
        "You are the Tax Partner advising on structure selection, elections, and post-closing steps; you validate "
        "rollover/earnout metrics and draft tax provisions.",
        f"House rule for tax provisions: number clauses `TAX-PROV-<n>`. {TAX_LEDGER_FORMAT}",
        "Tax partner who selects structures, elections, and post-close steps with quantified impacts.",
        [
            "Advises on structure selection",
            "Models elections and impacts",
            "Drafts tax provisions",
            "Validates rollover/earnout metrics",
            "Writes post-closing covenant ledgers in the tax team's house format",
        ],
    )
    closing_checklist_manager = _ai(
        "closing_checklist_manager",
        "You maintain the master closing checklist, verify third-party consents and conditions precedent, and "
        "manage signature packets and bring-down confirmations.",
        f"House rule for the checklist: rows read `CL-<n> | <condition> | <status>`. {CLOSING_SET_FORMAT}",
        "Checklist owner who manages CPs, consents, and signature packets to the finish line.",
        [
            "Maintains master checklist",
            "Verifies consents and CPs",
            "Manages sign packets",
            "Runs bring-down confirmations",
            "Writes closing sets in the closing team's house format",
        ],
    )

    # === Joiners (each is the only worker that can pass one gated task) ===
    ip_counsel = _ai(
        "ip_counsel",
        "You are IP Counsel validating chain-of-title, OSS usage, license compliance, and assignment mechanics; "
        "you draft IP/OSS and assignment schedules and approve IP-related covenants.",
        "House format for contract, IP and privacy diligence memos (use it whenever you deliver one): the first "
        "line is exactly `IP-CHAIN/v2`; number every finding `IP-001`, `IP-002`, and so on; end with a line "
        "`OSS-VERDICT: CLEAR`, `OSS-VERDICT: FLAGGED` or `OSS-VERDICT: BLOCKED`.",
        "IP counsel who validates chain-of-title/OSS and drafts IP schedules and covenants.",
        [
            "Validates IP ownership and OSS usage",
            "Drafts IP/OSS and assignment schedules",
            "Approves IP-related covenants",
            "Manages IP risks and exceptions",
            "Writes contract, IP and privacy diligence memos in the IP team's house format",
        ],
    )
    antitrust_analyst = _ai(
        "antitrust_analyst",
        "You analyze HSR thresholds and potential antitrust risk, assemble Item 4(c)/(d) materials, draft cover "
        "letters, and maintain a tracker for waiting periods, second requests, and remedies discussion points.",
        "House format for HSR and antitrust assessments (use it whenever you deliver one): the first line is "
        "exactly `HSR-SCREEN/v4`; include a line `FILING-PATH: HSR-ONLY`, `FILING-PATH: HSR+CFIUS` or "
        "`FILING-PATH: NONE`; include a line `WAIT-DAYS: <n>` with the expected waiting period in days.",
        "Analyst who manages HSR thresholds, waiting periods, and potential remedies.",
        [
            "Analyzes HSR thresholds",
            "Assembles Item 4(c)/(d) materials",
            "Tracks waiting periods and requests",
            "Preps remedy discussion points",
            "Writes HSR and antitrust assessments in the antitrust team's house format",
        ],
    )
    tax_structuring_ai = _ai(
        "tax_structuring_ai",
        "You are a Tax Structuring assistant that compares asset vs stock vs merger alternatives, models "
        "338(h)(10)/336(e) elections, and produces step plans with annotated tax impacts and dependency checks.",
        "House format for structure step plans (use it whenever you deliver one): the first line is exactly "
        "`STEP-PLAN/v3`; number the steps `STEP-01:`, `STEP-02:`, and so on; include a line "
        "`ELECTION: 338(h)(10)`, `ELECTION: 336(e)` or `ELECTION: NONE`. " + TAX_LEDGER_FORMAT,
        "Tax aide who compares structures, models elections, and drafts step plans.",
        [
            "Models asset/stock/merger options",
            "Prepares 338(h)(10)/336(e) analyses",
            "Drafts annotated step plans in the tax-structuring house format",
            "Checks dependencies",
            "Writes post-closing covenant ledgers in the tax team's house format",
        ],
    )
    schedules_builder = _ai(
        "schedules_builder",
        "You assemble disclosure schedules and consent lists from diligence outputs, ensure cross-references to "
        "the SPA, and validate that exceptions are precise, current, and supported with evidence from the data room.",
        "House format for schedule drafts (use it whenever you deliver SPA schedules or disclosure schedules): the "
        "first line is exactly `SCHED-INDEX/v2`; number the entries `SCH-001`, `SCH-002`, and so on; give every "
        "exception a line `EVIDENCE-LINK: DR-NNN`, where NNN is a three-digit data-room reference.",
        "Assembler who produces precise, evidence-linked schedules and consent lists.",
        [
            "Builds disclosure schedules",
            "Cross-references to SPA",
            "Validates precision and currency",
            "Tracks exceptions and evidence",
            "Writes schedule drafts in the schedules team's house index format",
        ],
    )
    redline_explainer = _ai(
        "redline_explainer",
        "You are a Redline Explainer that summarizes diff chunks into executive-readable rationales, identifies "
        "give-gets, and proposes trade packages balancing value, certainty of close, and compliance.",
        "House format for redline summaries (use it whenever you deliver one): the first line is exactly "
        "`REDLINE-RATIONALE/v2`; number the give-gets `GG-01:`, `GG-02:`, and so on; include a line "
        "`TRADE-PACKAGE: <name>`. " + CLOSING_SET_FORMAT,
        "Explainer who distills diffs into executive-readable rationales and trade packages.",
        [
            "Summarizes deltas and rationale",
            "Identifies give-gets",
            "Proposes trade packages",
            "Balances value/certainty/compliance",
            "Writes redline summaries in the redline team's house format",
            "Writes closing sets in the closing team's house format",
        ],
    )
    regulatory_counsel = _ai(
        "regulatory_counsel",
        "You are Regulatory Counsel (antitrust and regulatory) advising on HSR strategy, potential remedies, and "
        "multi-jurisdiction sequencing; you coordinate filings and timelines.",
        "House format for filing trackers (use it whenever you deliver a filing tracker or filing package): the "
        "first line is exactly `FILING-TRACKER/v1`; number every agency request `REQ-001`, `REQ-002`, and so on; "
        "include a line `WAITING-PERIOD-END: YYYY-MM-DD`.",
        "Antitrust counsel who advises HSR strategy, remedies, and multi-jurisdiction sequencing.",
        [
            "Advises HSR thresholds and filings",
            "Coordinates with regulators",
            "Plans remedies discussions",
            "Aligns regulatory timelines",
            "Writes filing trackers in the regulatory team's house format",
        ],
    )
    funds_flow_coordinator = _ai(
        "funds_flow_coordinator",
        "You are a Funds Flow Coordinator who prepares sources-and-uses, drafts funds-flow statements, and validates "
        "wire instructions and officer certificates for signing/closing mechanics.",
        "House format for funds-flow statements (use it whenever you deliver one): the first line is exactly "
        "`FUNDS-FLOW/v5`; number every wire `WIRE-001`, `WIRE-002`, and so on; include a line "
        "`TIEOUT: BALANCED` or `TIEOUT: UNBALANCED` for the sources-and-uses tie-out.",
        "Coordinator who drafts accurate funds-flow and validates closing mechanics.",
        [
            "Prepares sources-and-uses",
            "Drafts funds-flow statements in the funds-flow house format",
            "Validates wires and certificates",
            "Coordinates signing/closing",
        ],
    )

    # Stakeholder proxy (not a worker; never on the roster), unchanged from the source.
    stakeholder = StakeholderConfig(
        agent_id="acquirer_gc_stakeholder",
        agent_type="stakeholder",
        system_prompt=(
            "You are the Acquirer General Counsel. You prioritize early momentum, then high-quality drafts and "
            "governance, finishing with strict compliance at signing/closing. Approve key trade-offs."
        ),
        model_name=STAKEHOLDER_MODEL,
        reasoning_effort=STAKEHOLDER_REASONING,
        name="Acquirer GC (Stakeholder)",
        role="Executive Stakeholder",
        persona_description="Pragmatic, governance-minded, risk-aware; values crisp redline logs and evidence-linked schedules.",
        agent_description=(
            "Acquirer GC stakeholder who prioritizes momentum early, then quality/governance, then strict compliance at close."
        ),
        agent_capabilities=[
            "Sets priorities across phases",
            "Approves key trade-offs",
            "Demands evidence-linked schedules",
            "Grants final legal approval",
        ],
        response_latency_steps_min=1,
        response_latency_steps_max=3,
        push_probability_per_timestep=0.1,
        suggestion_rate=0.5,
        clarification_reply_rate=0.9,
        strictness=0.65,
        verbosity=2,
        initial_preferences=PreferenceWeights(
            preferences=[
                Preference(name="speed", weight=0.5),
                Preference(name="quality", weight=0.3),
                Preference(name="compliance", weight=0.2),
            ]
        ),
    )

    return {
        "project_coordinator": project_coordinator,
        "lead_mna_partner": lead_mna_partner,
        "senior_mna_associate": senior_mna_associate,
        "diligence_reader": diligence_reader,
        "deal_counsel_ai": deal_counsel_ai,
        "acquirer_gc": acquirer_gc,
        "tax_partner": tax_partner,
        "closing_checklist_manager": closing_checklist_manager,
        "ip_counsel": ip_counsel,
        "antitrust_analyst": antitrust_analyst,
        "tax_structuring_ai": tax_structuring_ai,
        "schedules_builder": schedules_builder,
        "redline_explainer": redline_explainer,
        "regulatory_counsel": regulatory_counsel,
        "funds_flow_coordinator": funds_flow_coordinator,
        "stakeholder": stakeholder,
    }


def create_team_timeline():
    """
    Timestep -> [(action, agent_cfg, reason)]. Actions: "add" or "remove".

    Reasons describe the scaling event and never name a task.

    Pace (see CONVERSION.md): about 1.6 simulated hours per step. The critical path reaches Signing at
    about hour 65 (step 41) and Post-Closing at about hour 69 (step 43), so both leave-affected tasks
    are still unassigned when their leave lands. Each joiner's task cannot start before its dependencies
    finish, which is after the join. A leaver's natural work finishes before its leave:
      - tax_structuring_ai: structure and tax planning is ready about step 17 and takes about 5 steps.
      - redline_explainer: negotiation is ready about step 28 and takes about 5 steps.
    """
    cfg = create_legal_mna_team_configs()

    return {
        0: [
            ("add", cfg["project_coordinator"], "initial roster: deal coordination"),
            ("add", cfg["lead_mna_partner"], "initial roster: negotiation lead"),
            ("add", cfg["senior_mna_associate"], "initial roster: drafting and coordination"),
            ("add", cfg["diligence_reader"], "initial roster: data-room triage"),
            ("add", cfg["deal_counsel_ai"], "initial roster: SPA drafting"),
            ("add", cfg["acquirer_gc"], "initial roster: governance and sign-off"),
            ("add", cfg["tax_partner"], "initial roster: tax advice"),
            ("add", cfg["closing_checklist_manager"], "initial roster: closing mechanics"),
        ],
        6: [
            ("add", cfg["ip_counsel"], "scale-out: specialist capacity added"),
            ("add", cfg["antitrust_analyst"], "scale-out: specialist capacity added"),
            ("add", cfg["tax_structuring_ai"], "scale-out: specialist capacity added"),
        ],
        12: [
            ("add", cfg["schedules_builder"], "scale-out: capacity added for the next phase"),
            ("add", cfg["redline_explainer"], "scale-out: capacity added for the next phase"),
        ],
        18: [
            ("add", cfg["regulatory_counsel"], "scale-out: capacity added for the regulatory phase"),
        ],
        25: [
            ("add", cfg["funds_flow_coordinator"], "scale-out: capacity added for the final phase"),
        ],
        30: [
            ("remove", cfg["tax_structuring_ai"], "scale-in: worker pool shrinks"),
        ],
        39: [
            ("remove", cfg["redline_explainer"], "scale-in: worker pool shrinks"),
        ],
    }
