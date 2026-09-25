# Converting an Existing Scenario to its AHT Variant

Companion to [`index.md`](index.md) (shared context/definitions) and
[`autoscaling_team_churn.md`](autoscaling_team_churn.md) (the pool-autoscaling mechanism in
full detail). This doc covers the generic, repeatable procedure — applied concretely via
[`.claude/commands/create-aht-benchmark.md`](../../.claude/commands/create-aht-benchmark.md) and
[`benchmark_conversion_template.yaml`](benchmark_conversion_template.yaml).

**If you haven't yet, read [`index.md`](index.md)'s "The picture" section first** — everything
below is the mechanical *how* behind that narrative: pools standing in for "agents show up as
tasks show up," the 6-step procedure's steps 4-5 being how Objective 1 (cold start) and
Objective 2 (reuse-or-switch) actually get built into a scenario.

## What MA-Gym already gives us for free

Non-stationary team composition is **already plumbed end-to-end** — this procedure builds on it,
doesn't replace it:

- `AgentRegistry.schedule_agent_add` / `schedule_agent_remove` / `apply_scheduled_changes_for_timestep`
  ([`manager_agent_gym/core/workflow_agents/registry.py:189-214`](../../manager_agent_gym/core/workflow_agents/registry.py)) —
  agents join/leave at a declared timestep during the run.
- Every scenario's `team.py::create_team_timeline()` returns a
  `{timestep: [("add"|"remove", AgentConfig, reason), ...]}` dict, and
  `examples/run_examples.py:111-122` feeds it straight into the registry calls above. **Reused
  unchanged** — conversion changes *how the dict's contents get decided*, never this interface.
- `ManagerObservation.available_agent_metadata`
  ([`manager_agent_gym/schemas/execution/manager.py:39`](../../manager_agent_gym/schemas/execution/manager.py))
  already exposes the live roster (`agent_capabilities`, free text) to the manager at each step.
- `diagnostics/analyze_diagnostic_runs.py` already re-derives the ground-truth join timeline and
  diffs it against the manager's *first assignment timestep* per agent — the behavioural half of
  disruption-cost tracking. **Reused unchanged.**

## Decision: edit scenarios in place, one at a time

Modify MA-Gym's existing `examples/end_to_end_examples/*` scenarios into
`examples/end_to_end_examples_aht/*` variants rather than writing new scenarios from scratch —
apply the generic procedure below to one scenario, land it, repeat. The dependency graph,
`team_timeline`, and `preferences.py` machinery already exist per scenario and are already
exercised by `examples/scenarios.py`, `scripts/run.sh`/`scripts/eval.sh`, and
`diagnostics/analyze_diagnostic_runs.py` — editing keeps all of that working unchanged.

**Heavy modification is allowed, not just grafting new tasks alongside.** Rewrite existing task
names, descriptions, and structure — split, merge, reword, reorder — wherever that's what it
actually takes to create a genuine graft point. Accepted cost: once a workflow's existing tasks
are rewritten, that scenario's *old* baseline runs no longer apply — a new baseline must be
established against the edited version, not diffed against the pre-edit original. The point of
conversion is a workflow that can actually demonstrate trait-tuple fit, not a diff-minimal edit
against a baseline that couldn't test the thing this needs tested.

**Worker pool restriction:** `AIAgentConfig` only in every converted scenario — no
`HumanAgentConfig` instances survive. Human-worker constraints (certification, contracts, safety
regs) are out of scope and add a confound to trait-tuple fit measurement. Enforced by step 2
below.

## Picking which scenario to convert next

Prefer scenarios the diagnostic suite already targets by name in `scripts/run.sh`/`scripts/eval.sh`
— they already have a `team_timeline` wired through `AgentRegistry` and are already what
`analyze_diagnostic_runs.py` reports on, so no diagnostics plumbing needs to change, only what
it's pointed at.

**Expect to author new tasks or rework existing ones, not simply find a ready-made seam.**
Scenarios surveyed so far (`legal_m_and_a`, `orsa`, spot-checked `marketing_campaign` and
`tech_company_acquisition`) are all structured as a single linear/branching DAG of topically
*distinct* phases run once, not a multi-client pipeline where a request type recurs — none
contained two already-similarly-worded tasks needing different trait tuples, or a task type
recurring at a non-adjacent point, ready-made. Don't expect the next scenario to be different;
plan to create the graft point, not discover it.

## The generic 6-step procedure

Applicable to **any** scenario. Run once per scenario, in order:

1. **Check feasibility.** Does this workflow have a task whose description already bundles 2+
   genuinely different specialties (a natural split point), or can existing tasks be
   rewritten/restructured to create one?
2. **Convert/drop human-only roles.** Per-role audit against every `HumanAgentConfig`: convert
   to `AIAgentConfig` if the role is really just "another knowledge worker" (equivalent
   `agent_description`/`agent_capabilities`), or drop it and hand its dependent tasks to a
   surviving role if it exists only for a human-specific reason (sign-offs, executive approval)
   the AI-only restriction rules out. Cross-reference `workflow.py`/`preferences.py` for what
   depends on each `agent_id` — this is a judgment call, done per-role, not mechanical.
3. **Identify which pool tuples are in use.** Which tuples from the shared `TRAIT_POOL`
   (`trait_tuple.md`) are/will be deployed into this scenario — needed before step 4, since a
   checklist can only discriminate against tuples that actually exist in the pool for this run.
4. **Author two similarly-named tasks with disjoint checklists** — the Objective-1 test. Onto
   the step-1 split point, author (or rewrite into) two similarly-named tasks, each with a
   disjoint `requirements` checklist (`requirements_checklist.md`), each clearable only by one
   specific pool tuple from step 3.
5. **Author one later reuse task** — the Objective-2 test. At a non-adjacent point, author a
   differently-worded task needing the same tuple as one of step 4's tasks, with an overlapping
   `requirements` checklist.
6. **Derive the team timeline for join/leave.** See "Team-churn generation" below — this is not
   picking timesteps that feel plausible, and it must satisfy all three design rules from
   [`index.md`](index.md#two-design-rules-for-every-scenario-generalize-beyond-legal_m_and_a):
   no leave ever forces a hand-off to a different specialist; no agent is removed before every
   task assigned to it is complete and nothing ready still needs its specialty; and no join/leave
   reason string names a specific task ID — describe the specialty/capability demand only, and
   verify which task that demand actually serves separately, in `conversion_spec.yaml`.

`requirements`/`requirements_pass_threshold`/`objective` get added only to the tasks touched in
steps 4-5. Every other task is untouched — the requirements evaluator is a no-op without
`requirements`.

Land the procedure on **one** scenario before starting a second — depth over breadth. The
authoring judgment call in steps 3-4 (what actually makes a checklist item trait-tuple-dependent
in practice) is the hard part of every iteration, not the schema, and is best done by reading
the chosen scenario's actual task graph rather than from this doc alone.

## Team-churn generation: demand-driven roster, not capacity autoscaling (step 6, in full)

**Team churn is derived from which specialty the task graph currently needs, not from a
load/capacity threshold, and not from hand-authored, narratively-justified join/leave events.**
Full mechanism and a worked application: [`autoscaling_team_churn.md`](autoscaling_team_churn.md).

This is a deliberate correction from an earlier "load-driven pool autoscaling" framing (scale a
pool out when `load > capacity`). That framing doesn't hold up: the execution engine has no
per-agent concurrency limit at all (`engine.py`'s ready-task loop starts every ready task with an
assigned agent via `asyncio.create_task`, with no check for whether that agent is already running
something else) — so "capacity" was never actually enforced, and a "pool" scaling to handle
"load" was describing a queueing mechanism that doesn't exist. What the timeline should actually
encode is simpler and matches real demand-driven staffing: **an agent (or a fresh instance of a
specialty) joins when a task needs a specialty nothing on the current roster covers, and an agent
leaves once every task it's doing is finished and no ready task still needs its specialty** — see
the three design rules in [`index.md`](index.md). Three consequences of this correction:

- **A cold-start guess covers a whole bundle, not one task at a time.** When an unknown-capability
  agent joins, the scenario should bet it on the *entire* run of plausibly-same-shaped upcoming
  tasks it might cover (e.g. a newly-joined diligence-triage agent gets guessed onto every
  diligence-shaped task in its window, not just the first one it happens to be assigned). This
  is what makes the cold-start bet cheap and one-shot, matching the "infer cheaply, from scratch"
  framing in `index.md`.
- **That agent stays until the whole bundle is done, then leaves — it never gets pulled off
  mid-bundle to be replaced by a different specialist.** If a scenario's draft timeline would
  remove an agent while it (or the bundle it was guessed onto) is still incomplete, that is a
  bug in the timeline, not a "failover" moment to design a manager behavior around — see
  `index.md`'s "Explicitly out of scope."
- **The join/leave reason string names the specialty, never the task.** Write "debt-commitment
  and closing-coordination demand opens," not "this agent is for T9." A task-named reason lets two
  agents get silently authored as covering the same task with nothing forcing you to notice — the
  `legal_m_and_a` build hit exactly this (`finance_counsel_ai` and `rwi_packager` were both
  authored "for T9" before this was caught). Verify which task a specialty actually serves
  separately, in the scenario's `conversion_spec.yaml`, which is structured and checkable — not in
  a free-text sentence nothing validates.

Pool capacity per trait tuple is derived from when that tuple's tasks become ready in the
dependency graph, then baked into the same `{timestep: [(action, agent_cfg, reason), ...]}` dict
`create_team_timeline()` already produces — the engine interface never changes, only how the
dict's contents are decided.

**Method: `offline_static`, not `runtime_dynamic` — a principled choice, not convenience.** A
live policy driven by ready-or-in-progress task counts has a fatal flaw: task readiness and
completion timing are themselves downstream of the manager's own assignment and execution
choices — assign well, the next specialty's demand is met sooner; assign badly, it isn't. That
makes the signal **manager-reactive**, not externally imposed, which disqualifies it as a test of
adaptation to non-stationarity at all — real demand-driven staffing reacts to external work
arriving, not to the on-call engineer's own performance. Externally-triggered, with no real
external demand signal to hook into, means **precomputed**: a fixed schedule authored from the
task graph's *dependency structure* (which tasks share a dependency, not task identity),
simulating what external demand would have done. Deriving from shared structure rather than
identity is also what keeps join/leave timing from telegraphing which agent is "meant for" which
task (e.g. two Objective-1 specialties become needed at the same timestep because their tasks
share a dependency, not because either is "the" intended one) — this works precomputed exactly as
well as it would live, so runtime computation buys nothing. **No engine change needed** —
`create_team_timeline()` stays a static dict, reasoned from the graph, same as always.

## Sequencing

1. **Schema + one scenario, offline.** No simulation runs needed — pure schema editing plus
   `team.py`/`workflow.py`/`preferences.py` edits on the chosen scenario.
2. **Baseline diagnostic re-run on the edited scenario**, not the untouched original — the point
   where `requirements_met` becomes checkable per task instead of "did anything get produced."
   Requires running `scripts/run.sh` against the edited scenario, which calls the OpenAI API —
   **do not run this without an explicit, separate ask**, even once edits are made (per
   `CLAUDE.md`).
