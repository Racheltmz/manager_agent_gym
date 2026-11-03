# Decisions: empirical study of how a manager agent handles mid-workflow changes

Status (2026-11-03): **specification only.** Nothing for this version is built. The earlier agent-loss benchmark's package, scripts and tests are no longer in the working tree, and its inert hooks in shared code were removed on 2026-11-03.
Source of direction: [`Project Proposal.md`](Project%20Proposal.md), the editable working copy of [`Project Proposal.pdf`](Project%20Proposal.pdf) (not final; the PDF is a snapshot of 2026-11-03, the earlier PDF is in git at c346d57). The tone of the project: an **empirical study**, run on MA-Gym's benchmarks, whose flaws are examined first and then improved by borrowing from other peer-reviewed benchmarks.
Design, measures and open items: [`preregistration.md`](preregistration.md). Problem statement: [`problem.md`](problem.md).
Labels: **Verified** (I read the code), **Inferred** (reasoned from it).

## The study in one paragraph

Take MA-Gym's existing benchmarks, find what is wrong with them for this purpose, and improve them by leveraging other peer-reviewed benchmarks (for example REALM-Bench). Add a layer of mid-workflow changes (environmental, preference, goal), run one frozen baseline manager (MA-Gym CoT), analyse its failures per change type, then test targeted training-free improvements one at a time. Compare against reference conditions (ignore the change, replan from scratch), not against published methods. Questions: baseline behaviour and failure modes; which design factors reduce them, for which change type; dependence on timing and on how much of the plan is affected; cost in model calls.

## Decisions

**D21. Direction: empirical study (Problem Definition 3).** Supersedes D1 to D20 (summarised under "Earlier directions"; their text was removed, see git c346d57). Deliverable: an empirical study aligned with what a manager agent does (keep, revise or reassign work after a change), with the baseline, the per-type failure analysis and the targeted improvements. The earlier plan to build a benchmark, metrics and a manager for agent unavailability is dropped because building a grounded benchmark needs domain knowledge and data, and a genuine gap was hard to find; reusing MA-Gym's benchmarks and borrowing from peer-reviewed ones (D22) avoids the first problem.

**D22. Benchmark: MA-Gym's existing benchmarks, improved with elements of other peer-reviewed benchmarks, plus a change layer.** The base is MA-Gym (engine, action space, Random, CoT and Assign-All managers, and its example workflows under `examples/end_to_end_examples/`). The proposal's own table rates MA-Gym's coverage of *adaptation* as partial (preference change-points and workers joining or leaving mid-run), and its flaws are to be established (D28). What to add is to be taken from other peer-reviewed benchmarks; the proposal names REALM-Bench (planning scenarios with disruptions such as traffic, road closures and delays, and exact solvers for small instances) as a source, and its evidence list cites InterruptBench, MAST, Tack et al. and PersonaForge (peer-review status of each is not yet checked). Changes are injected at controlled points rather than by inventing workflows. Task goals are fixed except under the goal-change type. **Open:** which benchmark supplies what (scenarios, environmental disruptions, reference solvers, scoring); how borrowed elements map onto MA-Gym's `Workflow`, `Task` and worker classes.

**D23. Three change types.**
- *Environmental*: the benchmark's disruptions (traffic, road closures, delays). MA-Gym has none of its own (its adaptation coverage is preference change-points and join/leave), so these come from a borrowed benchmark or are injected.
- *Preference*: how options are ranked changes. MA-Gym already has a preference-update mechanism (`PreferenceWeightUpdateRequest`, `create_preference_update_requests` in `examples/scenarios.py`); **Inferred** that it can seed this type, to be checked against what the borrowed scenarios need.
- *Goal*: what counts as success changes.
Preference and goal changes are injected at controlled points. Task and requirement drift beyond these, agent unavailability, error recovery and joins are out of scope (future work for the first).

**D24. Baseline, then targeted improvements.** (1) Define and freeze one manager (model, prompt, visible state, delegation); the baseline is MA-Gym CoT. (2) Categorise failures per change type (for example ignoring the update, restarting everything, losing track of completed work, replanning the wrong part). (3) For each frequent failure add one targeted modification, test it alone, then in combination. Candidates from the proposal: an explicit continue/repair/replan decision, identifying affected tasks from dependencies, tracking the active requirements. All training-free. (4) Develop on one scenario set; report final results on a held-out set.

**D25. Reference conditions, not published methods.** *Ignore the change* and *replan from scratch* bracket the manager. Where an exact solver exists for the instance, the reference answer is the re-solved remaining problem under the new objective. Cheap model tiers throughout.

**D26. Variables and measures.** Variables: change type, timing (early, mid, late), share of the remaining plan affected, explicit versus implied change; one factor varied at a time from a default. Measures: outcome quality after the change against the re-solved reference; unnecessary changes to work the change does not affect (unaffected tasks as control); cost in model calls and tokens; repeated runs per condition for variability. Thresholds and the decision rule are not yet set: see the open items in `preregistration.md`.

**D27. Order of work (the proposal's next steps).** (1) Understand the problems with MA-Gym's benchmarks; (2) understand what can be added from other peer-reviewed benchmarks; (3) inject no change, environment, goal and preference changes, separately; (4) run the CoT baseline; (5) understand the metrics; (6) run the improvement study. Each step is a `Planned` row in `UPDATES.md`.

**D28. MA-Gym's benchmark and metrics have two core issues; establish them before anything is borrowed or built** (user decision, 2026-11-03). The study stays empirical, but the benchmark it runs on is not taken as given. Implementation bugs (handoff, judge truncation, seeding, state) are **not** core issues and are not listed as such.

*Issue 1: no metric measures how well the manager handled a change.*
- Metrics are workflow-level (preference alignment, goal achievement, constraint adherence, stakeholder management, completion time): they score the whole run, not the response to one change.
- Most goal and preference scoring is LLM-judged against rubrics; no deterministic per-task check, so correct handling after a change cannot be verified.
- A high score does not show the change was handled: the manager can ignore it, or keep the original workers or plan, and still score well (change handling is confounded with workflow quality).
- Before-and-after comparison is unreliable: changes are clustered or overlapping, so there is no stable baseline and no attribution to a single change.
- Nothing measures unnecessary disruption (changes to work the change did not affect); no control from unaffected tasks.
- **Implication:** change-specific metrics: (a) outcome quality on the change-affected tasks after the change, deterministic where possible; (b) disruption cost on unaffected work; (c) cost in model calls and tokens. These are D26's measures; this is why they exist.

*Issue 2: no justification for why and when changes are injected.*
- Change points are fixed by design: preference change-points at about one-third and two-thirds of the action budget (paper Appendix C.6), and scripted join and leave times. No stated justification that they match real workflows. (Verified in the repo: `legal_m_and_a` hard-codes weight changes at t=35 and t=70; the paper's Appendix C.6 and the one-third/two-thirds figure are not checked here.)
- Scenarios are synthetic, not grounded in evidence of how and when changes occur.
- Without grounding, results cannot be shown to apply to real use; failures may reflect an arbitrary injection point.
- **Implication:** justify injected changes from real-world evidence (the sources in `problem.md`); vary timing (early, mid, late) and share of the remaining plan affected instead of one fixed point; state the assumptions behind change types and timings.

*Conflicts with other sections (flagged, nothing overwritten):*
- The sources in `problem.md` show that changes happen and hurt agents, not *when* or how often; the proposal calls this an assumption. Issue 2 can be met by stating assumptions, unless a source on timing is found.
- Issue 2 asks for grounding, but D21 dropped the earlier plan to build a grounded benchmark (domain knowledge and data). **Resolved 2026-11-03: justify and vary (D29).**
- D23 proposes MA-Gym's preference mechanism to seed the preference type; its change-points are the fixed ones in Issue 2. If reused, re-time them.
- The deterministic checklists (`TaskRequirement`) are this repo's addition, not MA-Gym's.

**D29. Injected changes are justified and varied, not grounded in records** (user decision, 2026-11-03). Answers Issue 2 the cheap way.
- Justify each change type and timing from the sources in `problem.md` and, where a borrowed benchmark states its own reasons, from those.
- Vary timing (early, mid, late) and the share of the remaining plan affected, one factor at a time from a default (D26), instead of one fixed point.
- Write down every assumption behind the chosen change types and timings (for example "a change can arrive at any point in the workflow") in `preregistration.md`, and carry them into the report.
- Do not build scenarios from incident or change records (the retired v2 route).
- **Consequence for claims:** results hold across the timings and shares tried; the study does not claim they match when changes occur in real workflows. State this in the report.
- **Chosen 2026-11-03: state the assumption openly; no search for a timing source is planned.** The assumption is "a change can arrive at any point in the workflow, so we test early, mid and late"; no timing is claimed to be the realistic one. The cited sources show changes happen, not when, so the study does not depend on one.
- If a source on when changes occur turns up anyway (see "What to learn from other benchmarks", question 5), it may set the default; that is optional, not a change of route.

*What to learn from other benchmarks* (REALM-Bench is named in the proposal; EntCollabBench and OrchestrationBench are named by the user; **their contents have not been read, nothing is assumed about them**). For each, answer:
1. Does it score the response to a change separately from the whole run? (Issue 1)
2. Per-task deterministic checks, or LLM judges?
3. Is there an unaffected-task control or a disruption measure?
4. Is there a stable baseline per change (one change at a time, a no-change run)?
5. How are change type and timing chosen, and what evidence is cited? (Issue 2)
6. Is timing varied, and the share of the plan affected?
7. Peer-review status and venue.
8. Can its scenarios or metrics be reused on MA-Gym's `Workflow`?

*Earlier-draft notes (partly overlap the issues above; the seed and ML-0xx items are implementation issues, not core, kept for reference):*
- Adaptation is only partially covered: preference change-points and join/leave exist; environmental and goal changes do not (proposal table).
- Scoring partly rests on LLM judges (non-deterministic and costly); the repo has `skip_llm_judge` and deterministic task checklists as a response.
- Worker LLM calls ignore the seed (see "Seeds" below). Bugs found and fixed in the repo: ML-050, ML-052, ML-053; documentation-versus-behaviour mismatches are listed below.
- A CoT run averaged 46.9 simulated hours because human actions block downstream tasks (proposal table); whether that is a flaw for this study is open.
- To investigate: no exact reference solver for MA-Gym workflows; scenario size and quality.
Output: a list of flaws with evidence, each marked fixed here, fix by borrowing (from which benchmark), or accepted as a limitation.

## Earlier directions (retired; one line each)

| ID | Was | Why retired |
|---|---|---|
| (v1) | Open ad-hoc teamwork: managers handling workers joining and leaving; join/leave benchmark and metrics | Did not fit the manager setup (uncertain capabilities and team) and MA-Gym is not built to handle change. Code and docs removed 2026-10-21 (commit c346d57). |
| D1 to D14, D17 (v2) | Adaptive replanning under agent unavailability: scripted-worker benchmark of outages and rate limits on three converted MA-Gym workflows, 30 scenarios, scripted and rule-based baselines, an LLM diagnostic | Most outages are solved by infrastructure (deterministic routing and fallbacks), so an agentic fix was hard to justify. Package, scripts and tests are no longer in the working tree; its hooks in shared code were removed 2026-11-03. |
| D15, D16, D18, D19, D20 (v2) | Proposal alignment for v2: substitute-share sweep, unannounced changes, grounded scenarios from public incident records, prompt versus policy manager | Superseded by D21 to D27. Agent unavailability remains future work. The "explicit continue/repair/replan policy" survives as one candidate improvement (D24). |

Two ideas carry over: the *counterfactual pair* (the same scenario run with and without the change, with unaffected tasks as controls) and *deterministic checklist scoring* (`TaskRequirement`, already in the tree). Whether either fits REALM-Bench's own scoring is open.

## What the existing code does (shared MA-Gym facts that still apply)

### Fixes the study depends on

| Fix | Status in the tree | Gap |
|---|---|---|
| ML-050: a completed task is not marked FAILED with score 0 | Present. `AIAgent._calculate_accurate_cost` ([`ai_agent.py:216`](../manager_agent_gym/core/workflow_agents/ai_agent.py)) catches any pricing failure and returns 0.0. Test: `tests/test_ai_agent_cost.py`. | None. |
| ML-052: reassignments are applied properly | Present but **opt-in**. `apply_assignment` ([`manager_actions.py:114`](../manager_agent_gym/schemas/execution/manager_actions.py)) cancels and restarts a RUNNING task and rejects COMPLETED, FAILED and composite tasks only when `Workflow.strict_assignment` is on (engine arg `restart_on_reassign`, off by default). | `AssignAllPendingTasksAction` still bypasses `apply_assignment`. Relevant to "reassign" decisions after a change; decide whether the study turns it on. |
| ML-053: the manager is told when an action is rejected | Present but **only for `cot`, and only with `team_awareness=True`** (the flag name is a leftover of the join/leave work; it now only controls the failure-cause and running-task blocks). `ChainOfThoughtManagerAgent._prepare_context` ([`structured_manager.py:262`](../manager_agent_gym/core/manager_agent/structured_manager.py)). | `assign_all` never reads its action history. |

### Seeds

Verified, by call site. `cot` and `assign_all` send `seed` to the OpenAI call (best effort; `temperature` defaults to 1, so runs still vary). Worker LLM calls (`AIAgent.execute_task`) **do not** use the seed (ML-092). The stakeholder's `random.Random` is seeded, but its one LLM call is unseeded. `decompose_task` passes `workflow.seed`, which nothing sets (always 42). Judge and rubrics use `ValidationEngine(seed=...)`. Consequence: expect run-to-run variance from workers as well as the manager unless workers are made deterministic; the proposal asks for repeated runs per condition, so budget for it.

### Scoring in MA-Gym

`ValidationEngine.evaluate_timestep` ([`validation_engine.py`](../manager_agent_gym/core/evaluation/validation_engine.py)) scores preference rubrics and workflow evaluators (some LLM-judged, some code) into a per-timestep reward vector. `skip_llm_judge` drops the LLM-judged rubrics. The study's outcome measure is instead task-specific (quality versus the re-solved reference), so MA-Gym's scoring is likely only a source of per-step snapshots. **Inferred; confirm when the scorer is designed.**

### Documentation versus behaviour

1. `Workflow.seed`: documented as set by the engine; never set.
2. `create_manager_agent(..., manager_mode="assign_all")` ignores `model_name`; `OneShotDelegateManagerAgent` always uses `o3`.
3. `AIAgent`'s `configure_seed` reads as if it makes workers deterministic; it does not.
4. `CreateTaskAction` and `RemoveTaskAction` mutate `workflow.tasks` without fixing dependants: removing a task leaves its dependants waiting forever. Matters for a "replan" action that removes tasks.

## Limitations to carry into the report

- One benchmark base (MA-Gym, improved) and cheap model tiers; findings may not transfer to other workflows.
- MA-Gym was published at DAI 2025 (International Conference on Distributed Artificial Intelligence, London; arXiv version Oct 2025). Its metrics were not designed to measure change handling (D28, Issue 1), so their validity for this study is argued directly.
- MA-Gym's flaws (D28) that are accepted rather than fixed are limitations of the study; borrowed elements may not fit MA-Gym's model of workers exactly.
- Where no exact solver exists, the reference for outcome quality is weaker; say which scenarios have one.
- Preference and goal changes are injected by the study, not taken from the benchmark. How often users change their minds in multi-agent workflows is unmeasured (assumption).
- Agent unavailability and task changes are out of scope.
