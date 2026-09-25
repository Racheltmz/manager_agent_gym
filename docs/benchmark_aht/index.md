# Open AHT Benchmark

This doc answers one question: **starting from MA-Gym's existing example scenarios, what
concretely needs to change so we can tell whether an agent was a good fit for a task when the
team roster changes mid-workflow?** Everything here is additive — no existing scenario, schema
field, or evaluator needs to be removed.

## The picture (read this first — everything else is in service of this)

**The problem this benchmark targets, precisely:** the marketplace/governance literature mostly
answers "should we trust this agent at all" *before* deployment. Nobody's solving "we already
trusted it enough to deploy it — now infer what it's specifically good at, cheaply, from scratch,
while the workflow is running." That's the gap: **online, cheap, in-workflow capability
inference under a demand-driven roster**, not pre-deployment vetting and not fault-tolerant
failover.

Picture a software-dev team. Tasks come in — "fix this bug," "review this PR," "build this
integration." As the kind of work shifts, the team's composition shifts with it: a backend
specialist shows up when backend work piles up, a security reviewer shows up once their kind of
work dries up and nothing current needs them. Nobody on the team *decides* to bring these people
on or let them go — **it just happens, driven by which specialties the current work actually
needs.** That's the whole benchmark's worldview:

- **As tasks get introduced, so do our worker agents — driven by which specialty is needed, not
  by relieving a queue.** The task graph's structure — not the manager — drives who's on the
  roster and when (the demand-driven roster mechanism, `benchmark_conversion.md`). This is *not*
  autoscaling in the "add more replicas of the same specialty because load exceeds capacity"
  sense — the engine has no per-agent capacity limit, so that framing has no engine-enforced
  teeth. It's "the *mix of specialties* present on the roster changes because the mix of work
  needed changes." The manager never asks for anyone; agents just show up, exogenously.
- **An agent leaves only once it's done with everything currently assigned to it, and nothing
  ready at that timestep still needs its specialty.** A departure never orphans in-progress work
  and never triggers a hand-off to a different, similar-but-not-identical specialist mid-task.
  See "Two design rules" below — this is the more important of the two for scenario authors to
  get right.
- **Agents get assigned based on their declared profile.** All the manager ever sees is a
  free-text `agent_capabilities` description per agent — no ground-truth label saying who's
  right for what. It has to read fit from wording, the way you'd read a new teammate's bio, and
  the guess is made *once*, cheaply, at cold start — not re-derived through a failure-recovery
  loop.
- **Objective 1 — cold start.** A new kind of task shows up, worded similarly to another task
  that actually needs a different specialist. Has the manager learned to tell "backend work"
  from "security work" apart from the profile alone, or is it matching on surface wording?
  Tested by two similarly-named tasks with genuinely disjoint requirements checklists, each
  clearable only by one specific agent pool.
- **Objective 2 — reuse or switch.** Later, a differently-worded task shows up that's actually
  *the same kind of work* as something the manager already staffed correctly once. Does the
  manager recognize the match and reuse the agent whose fit is already confirmed — or does it
  get talked into switching to a newer arrival that only *looks* more suited (a deliberate red
  herring), or fail to recognize the match at all and staff it wrong from scratch? Both halves
  of that one judgment call — reuse-when-right, resist-switching-when-wrong — are what gets
  graded.

Every mechanism in this doc tree (trait tuples, requirements checklists, demand-derived
timelines) exists only to make this picture measurable **without ever telling the manager the
answer.**

### Two design rules for every scenario (generalize beyond `legal_m_and_a`)

These apply to any scenario converted by this procedure, not just the worked example:

1. **No reassignment-on-leave, ever.** When an agent joins, its capability is unknown, so the
   scenario cheaply guesses it can plausibly cover a bundle of similarly-shaped upcoming tasks
   (e.g., a newly-joined diligence-triage agent gets cold-start-guessed onto *all* of the
   diligence-shaped tasks it might plausibly handle, not just the first one). Once made, that
   guess is never unwound by scripting the agent's departure mid-bundle and forcing the manager
   to find a substitute. **Do not build or grade "agent leaves, someone similar has to take
   over"** — that's a different problem (fault-tolerant failover / task hand-off), not the
   cold-start capability-inference problem this benchmark targets, and conflating them muddies
   both. If a cold-start bundle turns out to need reshuffling, the fix is scenario-authoring
   (bundle it differently, or don't have it leave until genuinely done), not a manager behavior
   to test.
2. **An agent leaves only after (a) every task currently assigned to it is complete, and (b) no
   task ready at that timestep still needs its specialty.** This is what makes rule 1 actually
   hold in practice — a scenario can't accidentally test failover if a departure can never
   orphan live work. When authoring a `team_timeline`, verify both conditions against the actual
   task durations/dependency graph before picking a removal timestep; a removal timestep that
   coincides with (or precedes) that agent's own task assignment is a bug, not an edge case.
3. **A `team_timeline` join/leave reason never names a specific task.** It states which
   *specialty/capability* is becoming relevant or exhausted (e.g., "debt-commitment and
   closing-coordination demand opens"), never "this agent is for T9." Naming a task ID in the
   reason string is the same ground-truth-label mistake the "no-label correction" above already
   rules out for the manager — it just relocates the label into the scenario author's own
   bookkeeping instead. It's not a cosmetic rule: it's what catches authoring bugs before they
   ship. A task-named reason string lets two agents silently get authored as "for T9" without
   anything forcing the author to notice the collision — describing demand generically forces
   the author to actually compare each candidate agent's `agent_description`/`agent_capabilities`
   against the task's `description` to determine fit, the same inference the manager itself has
   to do, rather than asserting an answer nobody checked. Which task an agent's declared
   specialty ends up matching is something to *verify against the task graph separately*
   (e.g. in a scenario's `conversion_spec.yaml`, which is structured and checkable, not a
   free-text sentence), never something to bake into the join event itself.

Split into one doc per independently-evolving change, so this index stays small as work
progresses instead of one file growing without bound:

| Doc | Covers | Status |
|---|---|---|
| [`benchmark_conversion.md`](benchmark_conversion.md) | Converting an existing scenario into its AHT variant — the generic procedure, the autoscaling-pool team-churn decision, and the template/command that operationalize it | **Written** |
| `trait_tuple.md` | The `(model, model_version, capability_tier)` schema and the shared `TRAIT_POOL` | Not yet split out — see §3.1/§3.3 in [`open_aht_benchmark_plan_prev.md`](open_aht_benchmark_plan_prev.md) |
| `requirements_checklist.md` | `TaskRequirement`/`Task.requirements` schema and the `task_requirements_evaluator.py` scoring design | Not yet split out — see §3.2/§4 in [`open_aht_benchmark_plan_prev.md`](open_aht_benchmark_plan_prev.md) |

## The no-label correction (applies everywhere below)

There is no task-to-agent *label* anywhere in this design — no stored ground-truth field saying
"agent X (or type X) is the correct assignment for task Y." Fit is never asserted, only
demonstrated: a task's `requirements` checklist is authored so that only a worker with the right
trait tuple can plausibly pass it, and fit is read off the *outcome* (did the checklist pass)
rather than off a label comparison. A fixed capability label is an abstraction that doesn't
reflect how real agentic systems vary.

## Problem statement

> We already trusted this agent enough to deploy it. Now infer what it's specifically good at,
> cheaply, from scratch, while the workflow is running — without an onboarding phase, without a
> label, and without treating its eventual, always-planned-for departure as something to recover
> from. Given a multi-agent environment, the agent team changes over time as demand for different
> specialties changes (agents join when their specialty is needed, and leave once it no longer
> is). New agents' capability is uncertain as only a declared profile is known, and tasks that
> appear similarly described can actually require different agent types. The manager must assign
> agents to tasks correctly despite this uncertainty.

Everything else is scaffolding for that one sentence:

| Requirement in the statement | Benchmark must be able to tell us | Where |
|---|---|---|
| "team changes over time (join/leave)" | Whether the manager reacts to a roster change at all, and how fast | Already covered — `AgentRegistry`/`team_timeline` plumbing, see `benchmark_conversion.md` §1 |
| "new agents' capability is uncertain, only a declared profile is known" | Whether an *initial* assignment made from the declared profile alone was a good fit | `requirements_checklist.md` (Objective 1) |
| "tasks that appear similarly described can require different agent types" | Whether the manager avoids matching on surface wording when two tasks' `requirements` genuinely diverge | `benchmark_conversion.md` step 4 |

## Overarching goal

Keep this in mind when designing any task's checklist — it's "The picture" above, restated as
a design rule:

> Checklist passes → right agent for that task (Objective 1) → combined with correct reuse of a
> confirmed fit on a later, similar task (Objective 2) → evidence of good assignment behavior
> under exogenous churn, on the specific patterns tested.

## Definitions

- **Where non-stationarity comes from:** workers only — agents join/leave mid-workflow as the
  demand for their specialty appears/disappears (see "Two design rules" above). Tasks are *not*
  non-stationary: the task distribution itself doesn't change over time, individual tasks are
  just heterogeneous in content.
- **Team composition changes exogenously — the manager never controls or triggers it.** This is
  Open AHT's defining property: the manager has no join/leave action, only `assign`/`inspect`/etc
  (see `benchmark_conversion.md` §1); `AgentRegistry.schedule_agent_add/remove` is called
  exclusively from the scenario-authored `team_timeline`, never from anything the manager does.
  The manager's only role is to *observe* the roster and *adapt* — it doesn't cause, request, or
  influence a single join/leave event. This is also why team-churn derivation must stay
  independent of the manager's own performance (`benchmark_conversion.md`'s "Team-churn
  generation" section) — a signal reactive to the manager's assignment quality would make churn
  partly manager-caused, which isn't exogenous anymore.
- **Each edited scenario is framed as an enterprise multi-agent system**, not a static team with
  a scripted roster event bolted on. Roster composition is a *required*, demand-driven property
  of the operating environment being modeled — *which specialty* is present changes with the
  work, not *how many copies* of one specialty exist — see `benchmark_conversion.md` for what
  that means mechanically.
- **What distinguishes a worker:** not an abstract capability score, but a concrete, inspectable
  trait tuple — `(model, model_version, capability_tier)`. Full schema: `trait_tuple.md` (pending).
- **Worker pool for the gated scenarios:** AI agents only — `HumanAgentConfig` instances are
  excluded (human-worker constraints are out of scope and add a confound to trait-tuple fit
  measurement).
- **What's actually being measured:** task-dependent *fit*, not whether the manager "correctly
  identified" a fixed label.

## What's missing (closed by redesigning the benchmark, not just adding schema)

**None of MA-Gym's existing example scenarios can assess AHT performance at all**, even though
several already script agents joining/leaving mid-run (`docs/benchmark/*.md`'s "Join/Leave
Schedule" tables). Non-stationary team composition is plumbed end-to-end (see
`benchmark_conversion.md` §1), but nothing downstream of it can tell whether a roster change was
*handled well* — there's no per-task signal that depends on which trait tuple got assigned, so a
run where the manager always picks correctly and a run where it always picks wrong currently
score identically on everything except the workflow-level LLM-judge rubrics, which don't isolate
fit at all.

Schema alone doesn't fix this — a scenario's own tasks and roster have to be redesigned too, or
the new schema has nothing genuinely discriminating to attach to. Three pieces close it together:

| Gap | Closed by |
|---|---|
| `AgentConfig` has no declared, inspectable trait tuple — `model_name` exists, but no model *version* or `capability_tier` field; only implicit in free-text `agent_capabilities` | `trait_tuple.md` (pending) |
| Scoring is workflow-level rubrics only (LLM-judge quality, function-based speed/cost, stakeholder, constraints) — no per-task deterministic checklist that can only be passed by the right trait tuple | `requirements_checklist.md` (pending) |
| Existing scenarios' tasks and rosters aren't *designed* to make fit observable — no task bundles genuinely different specialties behind similar wording, no roster is grouped into discriminating trait-tuple pools, and join/leave timing is narrative rather than derived | [`benchmark_conversion.md`](benchmark_conversion.md) — redesigns the scenario itself (the graft points, the human-role audit, the pool-derived timeline) **written** |

None of the three alone is sufficient: a trait tuple with nothing to grade against it is
unobservable, a checklist with no declared tuple to discriminate on has nothing tuple-specific to
test, and either schema piece is inert without a scenario actually redesigned to need them.

## End-to-end flow (how the three pieces connect)

The connective piece across all three docs — how one trait tuple travels from definition to
graded outcome, and who gets to see what, at each stage:

1. **Define the schema** (`trait_tuple.md`) — a tuple type any worker can be labeled with.
2. **Declare a shared worker pool** (`trait_tuple.md`) — concrete tuple *instances* that exist
   independently of any one scenario.
3. **Deploy workers into a scenario** (`benchmark_conversion.md`) — `team.py`/`team_timeline`
   pulls specific tuple instances from the pool, including autoscaling join/leave timing.
4. **Author checklists with pool knowledge** (`requirements_checklist.md`,
   `benchmark_conversion.md` step 4) — whoever writes a task's `requirements` knows which tuples
   exist in the pool for that scenario, and writes checks only the intended tuple could
   structurally pass.
5. **Runtime — the manager stays blind.** It only ever sees `description` + `agent_capabilities`
   (free text). It never sees the tuple or the checklist.
6. **Grading — fit inferred, not asserted** (`requirements_checklist.md`). After the task
   completes, `requirements_met` is checked. Nobody ever compares against a stored "correct
   agent" — the pass/fail outcome *is* the fit signal.

**One-line summary:** tuple is *defined* once → *deployed* into a scenario → *known* to the
checklist author → *invisible* to the manager at runtime → *inferred* after the fact from
whether the checklist passed.

## Known engine risks to verify (shared across all three docs)

Reported defects in the current engine/evaluation code, not settled facts — check each against
the codebase at build time, since a fix may have landed (or not) by then. Also tracked per
scenario in that scenario's `conversion_spec.yaml` `verification_checklist`.

- **Custom aggregation callables on an `Evaluator` may not actually run.** Where a rubric list is
  non-empty, the scoring engine has been observed computing `sum(score)/sum(max_score)` and
  *not* invoking the declared custom aggregation function. `task_credit`'s threshold logic
  (`requirements_checklist.md`) is exactly this shape — confirm before wiring
  `task_requirements_evaluator.py`.

## Explicitly out of scope

- **Failover / hand-off when an agent leaves mid-work.** By construction (the leave-timing rule
  above), this should never arise — an agent only leaves once genuinely done and no longer
  needed, so there is never a live task to hand off. If a scenario's `team_timeline` requires this
  to happen, that timeline is wrong; fix the timing, don't build failover logic.
- Worker-*leave* handling beyond what `schedule_agent_remove` already does.
- The manager's own capability-estimate/memory solution — this effort only makes the benchmark
  capable of grading that solution once it exists.
- Any change to the "5 values" default preference scoring (quality/speed/cost/stakeholder/
  constraints) — the requirements evaluator is additive and scoped to tasks that set
  `requirements`.
- Any stored ground-truth "correct agent/type" field — deliberately not part of this design; see
  the no-label correction above.
