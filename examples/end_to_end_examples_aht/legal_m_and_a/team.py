"""
Legal M&A – AHT (autoscaling / heterogeneous-team) benchmark variant.

AI-only roster, derived from examples/end_to_end_examples/legal_m_and_a/team.py by applying
the human-role audit (docs/benchmark_aht/benchmark_conversion.md, step 2) and grouping the
surviving agents into trait-tuple pools (open_aht_benchmark_plan_prev.md §3.3; pool/timeline
worked example in examples/end_to_end_examples_aht/legal_m_and_a/AHT_DIFF.md §2-§3a). See
examples/end_to_end_examples_aht/legal_m_and_a/conversion_spec.yaml for the filled
conversion-template record of every decision made here.

Human-role audit outcome (6 converted, 6 dropped — see conversion_spec.yaml for rationale):
  converted -> AI: senior_mna_associate, regulatory_counsel, ip_counsel, privacy_counsel,
                   finance_counsel, tax_partner
  dropped (no AI equivalent kept): lead_mna_partner, employment_counsel, rwi_broker,
                   acquirer_gc, acquirer_cfo, target_ceo
  (rationale: dropped roles' defining function was sign-off/executive authority, already
  covered by the `stakeholder` object below, or — for employment_counsel/rwi_broker — the
  role had no dependent task / was never scheduled in the original timeline at all.)

`create_team_timeline()` below is a hand-derived static dict (the `offline_static` method) —
demand windows are *reasoned from* task-graph readiness and completion estimates (see the
conversion spec), not computed live at runtime, and every join is a one-shot cold-start bundle
that is never split mid-way onto a different specialist (docs/benchmark_aht/index.md "Two design
rules").
"""

from manager_agent_gym.schemas.workflow_agents import AIAgentConfig, StakeholderConfig
from manager_agent_gym.schemas.preferences.preference import (
    PreferenceWeights,
    Preference,
)
from ..trait_pool import with_trait_tuple


# ---------------------------
# TEAM CONFIGS
# ---------------------------
def create_legal_mna_team_configs():
    """AI-only agent configs for the Legal M&A AHT variant, tagged with trait tuples."""

    # === P_deal_drafting_reasoning (reasoning_gpt4o) — feeds T6a, T10, T11 ===
    deal_counsel_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="deal_counsel_ai",
            system_prompt=(
                "You are an AI Deal Counsel focused on drafting and negotiating the Share Purchase Agreement (SPA). "
                "You propose market‑standard positions, track redline deltas with rationales, harmonize defined terms, "
                "and maintain issue lists with fallbacks across indemnities, covenants, and termination mechanics."
            ),
            agent_description=(
                "AI counsel who drafts market‑standard SPA language, tracks gives/gets, and harmonizes terms."
            ),
            agent_capabilities=[
                "Drafts and negotiates SPA sections",
                "Tracks redline deltas with rationales",
                "Maintains issue lists with fallbacks",
                "Harmonizes definitions across documents",
            ],
        ),
        "reasoning_gpt4o",
    )

    redline_explainer = with_trait_tuple(
        AIAgentConfig(
            agent_id="redline_explainer",
            system_prompt=(
                "You are a Redline Explainer that summarizes diff chunks into executive‑readable rationales, "
                "identifies give‑gets, and proposes trade packages balancing value, certainty of close, and compliance."
            ),
            agent_description=(
                "Explainer who distills diffs into executive‑readable rationales and trade packages."
            ),
            agent_capabilities=[
                "Summarizes deltas and rationale",
                "Identifies give‑gets",
                "Proposes trade packages",
                "Balances value/certainty/compliance",
            ],
        ),
        "reasoning_gpt4o",
    )

    # === P_diligence_extraction (extraction_gpt4o) — feeds T3, T4, T5, T10 ===
    diligence_reader = with_trait_tuple(
        AIAgentConfig(
            agent_id="diligence_reader",
            system_prompt=(
                "You are an AI Diligence Reader that triages data‑room documents, extracts facts into a structured index, "
                "flags risk‑relevant findings (assignment/consent, MFN, exclusivity, change‑of‑control, IP chain‑of‑title), "
                "and links evidence to disclosure schedules."
            ),
            agent_description=(
                "Reader who turns the data room into a structured index and flags material risks with citations."
            ),
            agent_capabilities=[
                "Extracts facts into structured index",
                "Flags risk‑relevant findings",
                "Links evidence to schedules",
                "Maintains citations and versions",
            ],
        ),
        "extraction_gpt4o",
    )

    schedules_builder = with_trait_tuple(
        AIAgentConfig(
            agent_id="schedules_builder",
            system_prompt=(
                "You assemble disclosure schedules and consent lists from diligence outputs, ensure cross‑references to the SPA, "
                "and validate that exceptions are precise, current, and supported with evidence from the data room."
            ),
            agent_description=(
                "Assembler who produces precise, evidence‑linked schedules and consent lists."
            ),
            agent_capabilities=[
                "Builds disclosure schedules",
                "Cross‑references to SPA",
                "Validates precision and currency",
                "Tracks exceptions and evidence",
            ],
        ),
        "extraction_gpt4o",
    )

    # Converted from senior_mna_associate (HumanAgentConfig) — drafting/coordination content
    # preserved, identity/persona fields dropped (AIAgentConfig has no name/role/experience_years).
    # Joins later for T10's own SPA-drafting demand (see create_team_timeline) — NOT as a
    # replacement for diligence_reader, which keeps its T3/T4/T5 bundle to completion per rule 1.
    senior_associate_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="senior_associate_ai",
            system_prompt=(
                "You are an AI Senior Associate responsible for drafting SPA sections, coordinating disclosure schedules, "
                "running diligence calls, and synthesizing positions into decision memos."
            ),
            agent_description=(
                "Converted from senior_mna_associate (§5.3 step 2). Drafts SPA sections, coordinates "
                "schedules, and synthesizes diligence positions."
            ),
            agent_capabilities=[
                "Drafts SPA and ancillary documents",
                "Coordinates disclosure schedules",
                "Runs diligence calls",
                "Prepares decision memos",
            ],
        ),
        "extraction_gpt4o",
    )

    # === P_privacy_reasoning (privacy_reasoning_gpt4o, NEW tuple) — feeds T6b, T13b ===
    # Converted from ip_counsel + privacy_counsel (HumanAgentConfig). This is the pool T6's
    # split is built to discriminate against — deliberately a *different* tuple from
    # P_deal_drafting_reasoning above, not just a different name.
    ip_counsel_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="ip_counsel_ai",
            system_prompt=(
                "You are an AI IP Counsel validating chain‑of‑title, OSS usage, license compliance, and assignment mechanics; "
                "you draft IP/OSS and assignment schedules and flag IP‑related covenant issues for review."
            ),
            agent_description=(
                "Converted from ip_counsel (§5.3 step 2). Validates chain‑of‑title/OSS and drafts IP schedules."
            ),
            agent_capabilities=[
                "Validates IP ownership and OSS usage",
                "Drafts IP/OSS and assignment schedules",
                "Flags IP‑related covenant issues",
                "Manages IP risks and exceptions",
            ],
        ),
        "privacy_reasoning_gpt4o",
    )

    privacy_counsel_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="privacy_counsel_ai",
            system_prompt=(
                "You are an AI Privacy Counsel assessing DPAs, cross‑border transfers, and security frameworks; "
                "you align privacy representations, exceptions, and remediation requirements."
            ),
            agent_description=(
                "Converted from privacy_counsel (§5.3 step 2). Aligns DPAs, transfers, and security "
                "representations with reality."
            ),
            agent_capabilities=[
                "Assesses DPAs and transfers",
                "Aligns privacy representations",
                "Tracks exceptions and remediation",
                "Coordinates with security/legal",
            ],
        ),
        "privacy_reasoning_gpt4o",
    )

    # === P_regulatory_reasoning (reasoning_gpt4o, reused — no discrimination needed here) ===
    # feeds T7, T12
    antitrust_analyst = with_trait_tuple(
        AIAgentConfig(
            agent_id="antitrust_analyst",
            system_prompt=(
                "You analyze HSR thresholds and potential antitrust risk, assemble Item 4(c)/(d) materials, draft cover letters, "
                "and maintain a tracker for waiting periods, second requests, and remedies discussion points."
            ),
            agent_description=(
                "Analyst who manages HSR thresholds, waiting periods, and potential remedies."
            ),
            agent_capabilities=[
                "Analyzes HSR thresholds",
                "Assembles Item 4(c)/(d) materials",
                "Tracks waiting periods and requests",
                "Preps remedy discussion points",
            ],
        ),
        "reasoning_gpt4o",
    )

    cfius_analyst = with_trait_tuple(
        AIAgentConfig(
            agent_id="cfius_analyst",
            system_prompt=(
                "You screen for CFIUS topical sensitivities (critical tech, supply chain, personal data), draft short‑form notices, "
                "and coordinate Q&A logs with outside counsel if a filing is elected."
            ),
            agent_description=(
                "Screening analyst who prepares CFIUS short‑form and coordinates Q&A logs."
            ),
            agent_capabilities=[
                "Screens for CFIUS sensitivities",
                "Drafts short‑form notices",
                "Maintains Q&A coordination",
                "Interfaces with outside counsel",
            ],
        ),
        "reasoning_gpt4o",
    )

    # Converted from regulatory_counsel (HumanAgentConfig)
    regulatory_strategist_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="regulatory_strategist_ai",
            system_prompt=(
                "You are an AI Regulatory Strategist advising on HSR strategy, potential remedies, and multi‑jurisdiction "
                "sequencing; you coordinate with antitrust_analyst on filings and timelines."
            ),
            agent_description=(
                "Converted from regulatory_counsel (§5.3 step 2). Advises HSR strategy, remedies, and "
                "multi‑jurisdiction sequencing."
            ),
            agent_capabilities=[
                "Advises HSR thresholds and filings",
                "Coordinates regulatory timelines",
                "Plans remedies discussions",
                "Aligns multi‑jurisdiction sequencing",
            ],
        ),
        "reasoning_gpt4o",
    )

    # === P_structure_tax_reasoning (reasoning_gpt4o, reused) — feeds T8, T13 bring-down ===
    tax_structuring_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="tax_structuring_ai",
            system_prompt=(
                "You are a Tax Structuring assistant that compares asset vs stock vs merger alternatives, models 338(h)(10)/336(e) "
                "elections, and produces step plans with annotated tax impacts and dependency checks."
            ),
            agent_description=(
                "Tax aide who compares structures, models elections, and drafts step plans."
            ),
            agent_capabilities=[
                "Models asset/stock/merger options",
                "Prepares 338(h)(10)/336(e) analyses",
                "Drafts annotated step plans",
                "Checks dependencies",
            ],
        ),
        "reasoning_gpt4o",
    )

    # Converted from tax_partner (HumanAgentConfig) — same tuple as tax_structuring_ai
    # deliberately: this pool's two members (early T8, later T13 bring-down) form the same
    # kind of same-tuple/non-adjacent-task pattern T13b formalizes for the privacy pool.
    tax_partner_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="tax_partner_ai",
            system_prompt=(
                "You are an AI Tax Partner advising on structure selection, elections, and post‑closing steps; "
                "you validate rollover/earnout metrics and finalize tax provisions and bring‑down confirmations."
            ),
            agent_description=(
                "Converted from tax_partner (§5.3 step 2). Finalizes structure/elections and bring‑down "
                "tax confirmations."
            ),
            agent_capabilities=[
                "Advises on structure selection",
                "Models elections and impacts",
                "Finalizes tax provisions",
                "Runs bring‑down tax confirmations",
            ],
        ),
        "reasoning_gpt4o",
    )

    # === P_debt_commitment_fast / P_rwi_ops_fast / P_closing_ops_fast (all fast_gpt4o_mini) ===
    # Split from a single P_closing_ops_fast grouping so T9's split (Objective-1 checkpoint 2
    # of 4) has two named, disjoint pools to route to — same tuple, different personas, same
    # precedent as P_regulatory_reasoning/P_structure_tax_reasoning sharing reasoning_gpt4o.
    # P_debt_commitment_fast feeds T9a; P_rwi_ops_fast feeds T9b; P_closing_ops_fast (the
    # remaining two members below) feeds T13, T14.
    rwi_packager = with_trait_tuple(
        AIAgentConfig(
            agent_id="rwi_packager",
            system_prompt=(
                "You coordinate Representations & Warranties Insurance (RWI) underwriting: assemble underwriting packets, "
                "track diligence responses, and reconcile exclusions with the SPA risk allocation."
            ),
            agent_description=(
                "Coordinator who aligns RWI underwriting with diligence outputs and SPA risk allocation."
            ),
            agent_capabilities=[
                "Assembles underwriting packets",
                "Tracks diligence responses",
                "Reconciles exclusions",
                "Aligns with SPA allocation",
            ],
        ),
        "fast_gpt4o_mini",
    )

    funds_flow_coordinator = with_trait_tuple(
        AIAgentConfig(
            agent_id="funds_flow_coordinator",
            system_prompt=(
                "You are a Funds Flow Coordinator who prepares sources‑and‑uses, drafts funds‑flow statements, and validates wire "
                "instructions and officer certificates for signing/closing mechanics."
            ),
            agent_description=(
                "Coordinator who drafts accurate funds‑flow and validates closing mechanics."
            ),
            agent_capabilities=[
                "Prepares sources‑and‑uses",
                "Drafts funds‑flow statements",
                "Validates wires and certificates",
                "Coordinates signing/closing",
            ],
        ),
        "fast_gpt4o_mini",
    )

    closing_checklist_manager = with_trait_tuple(
        AIAgentConfig(
            agent_id="closing_checklist_manager",
            system_prompt=(
                "You maintain the master closing checklist, verify third‑party consents and conditions precedent, and manage "
                "signature packets and bring‑down confirmations."
            ),
            agent_description=(
                "Checklist owner who manages CPs, consents, and signature packets to the finish line."
            ),
            agent_capabilities=[
                "Maintains master checklist",
                "Verifies consents and CPs",
                "Manages sign packets",
                "Runs bring‑down confirmations",
            ],
        ),
        "fast_gpt4o_mini",
    )

    # Converted from finance_counsel (HumanAgentConfig)
    finance_counsel_ai = with_trait_tuple(
        AIAgentConfig(
            agent_id="finance_counsel_ai",
            system_prompt=(
                "You are an AI Finance Counsel aligning debt commitment papers, intercreditor terms, and conditions with SPA "
                "conditionality; you coordinate closing deliverables and solvency certificates."
            ),
            agent_description=(
                "Converted from finance_counsel (§5.3 step 2). Aligns commitment papers, intercreditor "
                "terms, and closing conditions."
            ),
            agent_capabilities=[
                "Aligns debt commitment papers",
                "Coordinates intercreditor terms",
                "Preps closing deliverables",
                "Drafts solvency certificates",
            ],
        ),
        "fast_gpt4o_mini",
    )

    # === P_intake_orchestration (fast_gpt4o_mini, singleton, not load-scaled) — feeds T1, T3, T15 ===
    project_coordinator = with_trait_tuple(
        AIAgentConfig(
            agent_id="project_coordinator",
            system_prompt=(
                "You run the deal room and status cadence: create trackers for issues, RFIs, and decisions; "
                "publish weekly summaries with risks, owners, and ETAs; and keep artifacts consistent across drafts."
            ),
            agent_description=(
                "Orchestrator who keeps trackers, decisions, and artifacts consistent across drafts. Also "
                "absorbs T2/T14 governance-tracking duties formerly held by dropped human sign-off roles — "
                "actual sign-off semantics are carried by the stakeholder object and workflow Constraints, "
                "not by a worker agent (§5.3 step 2 audit)."
            ),
            agent_capabilities=[
                "Runs issue/RFI/decision trackers",
                "Publishes weekly summaries",
                "Surfaces risks with owners/ETAs",
                "Maintains artifact consistency",
                "Tracks governance approvals and CP status",
            ],
        ),
        "fast_gpt4o_mini",
    )

    # Executive stakeholder — not a worker, out of scope for the §5.2 AI-only worker-pool
    # restriction. Absorbs the sign-off/approval authority of the dropped human roles
    # (lead_mna_partner, acquirer_gc, acquirer_cfo).
    stakeholder = StakeholderConfig(
        agent_id="acquirer_gc_stakeholder",
        agent_type="stakeholder",
        system_prompt=(
            "You are the Acquirer General Counsel. You prioritize early momentum, then high‑quality drafts and "
            "governance, finishing with strict compliance at signing/closing. Approve key trade‑offs."
        ),
        model_name="o3",
        name="Acquirer GC (Stakeholder)",
        role="Executive Stakeholder",
        persona_description="Pragmatic, governance‑minded, risk‑aware; values crisp redline logs and evidence‑linked schedules.",
        agent_description=(
            "Acquirer GC stakeholder who prioritizes momentum early, then quality/governance, then strict compliance at close."
        ),
        agent_capabilities=[
            "Sets priorities across phases",
            "Approves key trade‑offs",
            "Demands evidence‑linked schedules",
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
        # P_deal_drafting_reasoning
        "deal_counsel_ai": deal_counsel_ai,
        "redline_explainer": redline_explainer,
        # P_diligence_extraction
        "diligence_reader": diligence_reader,
        "schedules_builder": schedules_builder,
        "senior_associate_ai": senior_associate_ai,
        # P_privacy_reasoning
        "ip_counsel_ai": ip_counsel_ai,
        "privacy_counsel_ai": privacy_counsel_ai,
        # P_regulatory_reasoning
        "antitrust_analyst": antitrust_analyst,
        "cfius_analyst": cfius_analyst,
        "regulatory_strategist_ai": regulatory_strategist_ai,
        # P_structure_tax_reasoning
        "tax_structuring_ai": tax_structuring_ai,
        "tax_partner_ai": tax_partner_ai,
        # P_rwi_ops_fast
        "rwi_packager": rwi_packager,
        # P_closing_ops_fast
        "funds_flow_coordinator": funds_flow_coordinator,
        "closing_checklist_manager": closing_checklist_manager,
        # P_debt_commitment_fast
        "finance_counsel_ai": finance_counsel_ai,
        # P_intake_orchestration
        "project_coordinator": project_coordinator,
        # Stakeholder (not a worker)
        "stakeholder": stakeholder,
    }


# ---------------------------
# TEAM TIMELINE — demand-driven, not load/capacity-driven (docs/benchmark_aht/index.md
# "Two design rules"; docs/benchmark_aht/autoscaling_team_churn.md "Why reconsider the current
# mechanism")
# ---------------------------
def create_team_timeline():
    """
    Timestep -> [(action, agent_cfg, rationale)].

    Two binding rules, not just style:

    1. **No reassignment-on-leave.** Every `add` below is a one-shot cold-start bundle covering
       *every* task that pool's specialty will plausibly need in its demand window, guessed once
       when the specialty first becomes needed. No agent here is ever pulled off a task mid-way
       and replaced by a different, similar-but-not-identical specialist — e.g. `diligence_reader`
       is bundled onto T3+T4+T5 at t=0 and stays through all three; it is never removed while any
       of them is still running, and `senior_associate_ai` joining later (t=25) is driven by T10's
       *own* new demand, not by covering for `diligence_reader`'s departure.
    2. **A `remove` only fires once every task in that agent's bundle is complete and nothing
       ready at that timestep still needs its specialty** — verified below against
       `workflow.py`'s `estimated_duration_hours` and dependency structure, not picked because the
       timestep merely looks plausible. (The previous version of this timeline violated this for
       `tax_structuring_ai`, removed the same timestep it was assigned T8 — fixed below.)

    Rationale strings name the specialty/capability becoming relevant or exhausted, never a task
    ID and never a load/capacity threshold (index.md "Two design rules," rule 3 — naming a task
    in the reason string just relocates the ground-truth-label mistake from the manager's
    observation into the scenario author's own bookkeeping, and is exactly what let two agents
    get silently authored "for" the same task in an earlier revision of this file; the engine
    also has no per-agent concurrency limit to threshold against — see
    `autoscaling_team_churn.md`). Which task a given agent's declared specialty actually ends up
    matching is verified separately, against the task graph, in `conversion_spec.yaml` — never
    asserted here. Timesteps reuse the original scenario's 0/6/12/18/25/45/55 cadence where it
    lines up with when a specialty's demand window actually opens or the prior bundle actually
    completes.
    """
    cfg = create_legal_mna_team_configs()

    return {
        0: [
            # T1 ready immediately.
            ("add", cfg["project_coordinator"], "P_intake_orchestration — coordination and governance-tracking demand opens as the deal kicks off"),
            # T3 about to become ready once T1 clears; cold-start guess bundles ALL of
            # T3+T4+T5 up front (rule 1) — this agent stays until all three are COMPLETED.
            ("add", cfg["diligence_reader"], "P_diligence_extraction — data-room triage/extraction demand opens as diligence begins (cold-start bundle, stays until fully done — rule 1)"),
            # T6a/T10 will need SPA-drafting once T3 clears; joins ahead of strict readiness.
            ("add", cfg["deal_counsel_ai"], "P_deal_drafting_reasoning — SPA-drafting demand opens ahead of readiness, as deal structure begins taking shape"),
        ],
        6: [
            # T1 clears, T3 nearly done -> T4/T5/T6a/T6b/T7 become ready together.
            # P_privacy_reasoning: bundled onto BOTH T6b and the later T13b reuse from the start,
            # since the reuse pool must already exist for Objective 2 — never scales in before then.
            ("add", cfg["ip_counsel_ai"], "P_privacy_reasoning — IP/privacy compliance demand opens as diligence scope clears (bundle spans this specialty's full demand window — never removed early, rule 2)"),
            ("add", cfg["privacy_counsel_ai"], "P_privacy_reasoning — IP/privacy compliance demand opens as diligence scope clears (bundle spans this specialty's full demand window — never removed early, rule 2)"),
            # P_regulatory_reasoning: bundled onto both T7 and the later T12 reuse up front.
            ("add", cfg["antitrust_analyst"], "P_regulatory_reasoning — regulatory/antitrust assessment demand opens as diligence scope clears (bundle spans this specialty's full demand window)"),
            ("add", cfg["regulatory_strategist_ai"], "P_regulatory_reasoning — regulatory/antitrust assessment demand opens as diligence scope clears (bundle spans this specialty's full demand window)"),
            # T8 will need structure/tax once T4/T5/T6a/T6b/T7 clear; joins ahead of readiness.
            ("add", cfg["tax_structuring_ai"], "P_structure_tax_reasoning — deal-structure/tax-planning demand opens ahead of readiness, as diligence inputs start converging"),
        ],
        12: [
            # New demand ahead of readiness — none of these are covering for a departure.
            ("add", cfg["schedules_builder"], "P_diligence_extraction — schedule/consent-list assembly demand opens ahead of readiness, independent of the existing triage bundle"),
            ("add", cfg["redline_explainer"], "P_deal_drafting_reasoning — redline/negotiation-explanation demand opens ahead of readiness"),
            ("add", cfg["finance_counsel_ai"], "P_debt_commitment_fast — debt-commitment/financing-coordination demand opens ahead of readiness"),
        ],
        18: [
            ("add", cfg["cfius_analyst"], "P_regulatory_reasoning — CFIUS-specific screening demand opens as regulatory filings approach"),
            ("add", cfg["rwi_packager"], "P_rwi_ops_fast — RWI underwriting-coordination demand opens as financing work approaches"),
            # diligence_reader's T3+T4+T5 bundle is COMPLETED by now (durations 8h/10h/9h from a
            # t=6 start); T10 (the only other P_diligence_extraction consumer) isn't ready yet —
            # it needs T8, which hasn't cleared — so nothing ready still needs this specialty.
            # Rule 2 satisfied: bundle done, nothing ready needs it.
            ("remove", cfg["diligence_reader"], "P_diligence_extraction — this bundle's triage/extraction work is complete; nothing ready currently needs that specialty"),
        ],
        25: [
            ("add", cfg["funds_flow_coordinator"], "P_closing_ops_fast — funds-flow/sources-and-uses demand opens as financing and closing work converge"),
            # T10 becomes ready (T5, T6a, T6b, T8 all clear by now) — new demand for a SPA
            # co-drafter, NOT a replacement for diligence_reader (already left at t=18, on time).
            ("add", cfg["senior_associate_ai"], "P_diligence_extraction — SPA co-drafting/coordination demand opens as drafting work becomes ready (a new demand, not a hand-off from any departure)"),
            # tax_structuring_ai's T8 bundle is COMPLETED by now (8h from a ~t=18 ready point);
            # nothing else currently needs structure/tax until T13's bring-down much later.
            # Rule 2 satisfied.
            ("remove", cfg["tax_structuring_ai"], "P_structure_tax_reasoning — this bundle's structure/tax work is complete; nothing ready currently needs that specialty"),
        ],
        45: [
            # T13 approaching -> new closing-ops demand, and a FRESH structure/tax demand for the
            # bring-down (tax_partner_ai is not a replacement for tax_structuring_ai — that
            # departure was already independently complete 20 timesteps earlier).
            ("add", cfg["closing_checklist_manager"], "P_closing_ops_fast — closing-checklist/signature-packet demand opens as closing approaches"),
            ("add", cfg["tax_partner_ai"], "P_structure_tax_reasoning — a fresh bring-down-confirmation demand opens, unrelated to any earlier departure in this pool"),
            # redline_explainer's T11 bundle is COMPLETED by now (8h from a ~t=25-30 ready
            # point); deal_counsel_ai (a different bundle: T6a/T10) remains for anything else
            # P_deal_drafting_reasoning still owns. Rule 2 satisfied.
            ("remove", cfg["redline_explainer"], "P_deal_drafting_reasoning — this bundle's redline/negotiation work is complete; nothing ready currently needs that specialty specifically"),
        ],
        55: [
            # T7+T12 bundle is COMPLETED (filings submitted). Rule 2 satisfied.
            ("remove", cfg["antitrust_analyst"], "P_regulatory_reasoning — this bundle's filings work is complete; nothing ready currently needs that specialty"),
        ],
        # P_privacy_reasoning (ip_counsel_ai/privacy_counsel_ai) is never removed after t=6 — its
        # bundle explicitly includes T13b, so rule 2's "bundle complete" condition can't be met
        # until after T13b, which is the entire mechanism the Objective-2 reuse test depends on.
    }
