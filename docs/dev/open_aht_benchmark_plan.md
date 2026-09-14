# Open AHT Benchmark: Concrete Modification Plan

Status: planning doc for FYP Goal 1 (Benchmark). Companion to `Project Proposal Ver2.pdf`.

This doc answers one question: **starting from MA-Gym's existing example scenarios, what
concretely needs to change so we can tell whether an agent was a good fit for a task when the
team roster changes mid-workflow?** Everything here is additive — no existing scenario, schema
field, or evaluator needs to be removed.

**Important correction from the last pass:** there is no task-to-agent *label* anywhere in
this design — no stored ground-truth field saying "agent X (or type X) is the correct
assignment for task Y." Fit is never asserted, only demonstrated: a task's `requirements`
checklist is authored so that only a worker with the right trait tuple can plausibly pass it,
and we read fit off the *outcome* (did the checklist pass, at what quality) rather than off a
label comparison. This matches the concern that a fixed capability label is an abstraction
that doesn't reflect how real agentic systems vary — see §2 and §3 below.

## Problem statement (what the solution must achieve)

> Given a multi-agent environment, the agent team changes over time (agents join/leave via
> autoscaling or failure). New agents' capability is uncertain as only a declared profile is
> known, and tasks that appear similarly described can actually require different agent types.
> The manager must assign (and reassign) agents to tasks correctly despite this uncertainty,
> without disrupting the workflow more than necessary.

Everything else in this doc is scaffolding for that one sentence. Breaking it into the pieces
the benchmark has to be able to independently measure:

| Requirement in the statement | Benchmark must be able to tell us |
|---|---|
| "team changes over time (join/leave)" | Whether the manager reacts to a roster change at all, and how fast — **already covered**, §1 |
| "new agents' capability is uncertain, only a declared profile is known" | Whether an *initial* assignment made from the declared profile alone (no track record yet) was a good fit — §3.2, §5.3 steps 3-4 (Objective 1) |
| "tasks that appear similarly described can require different agent types" | Whether the manager avoids matching on surface wording when two tasks' `requirements` genuinely diverge — §5.3 step 4 |
| "assign **and reassign** ... correctly" | Whether the manager corrects a *bad* assignment once evidence of the mismatch appears (not just whether the first guess was right) — **gap, addressed below in §5a** |
| "without disrupting the workflow more than necessary" | Whether the manager reassigns *only* when the current assignment is actually failing, not by default whenever a new candidate joins — **gap, addressed below in §5a** |

The last two rows were not covered by the previous version of this plan, which only tested the
*first* assignment (Objective 1) and reuse of a *confirmed* fit on a recurring task
(Objective 2). Neither exercises correcting a live mismatch, and neither exercises restraint.
§5a below adds the scenario elements needed for those two rows; nothing already in §3/§4 needs
to change to support them — they reuse the same `requirements`-outcome mechanism, just observed
mid-workflow instead of once at completion.

## Definitions carried over from the proposal (so this doc doesn't drift from it)

- **Where non-stationarity comes from:** workers only — agents join/leave mid-workflow via
  autoscaling or agent failure. Tasks are *not* non-stationary: the task distribution itself
  doesn't change over time, individual tasks are just heterogeneous in content (an earlier
  task and a later task are simply different tasks).
- **What distinguishes a worker:** not an abstract capability score, but a concrete, inspectable
  trait tuple — **(model, model version, capability)**, e.g. `('gpt-4o', 'reasoning')` where the
  model string already carries the version and the second element names the declared capability
  category. Two worker instances with the same trait tuple are the same declared type and
  assumed to share capability, consistent with how autoscaled replicas are actually deployed.
- **Worker pool for the gated scenarios:** AI agents only. `HumanAgentConfig` instances are
  excluded from these scenarios — human-worker constraints (certification, contracts, safety
  regs) are out of scope per the proposal, and mixing them in adds a confound we don't need for
  measuring trait-tuple fit.
- **What's actually being measured:** task-dependent *fit* (how well a given trait tuple
  performs on a given task) and *disruption* (reassignment cost), not whether the manager
  "correctly identified" a fixed label. Static capability is cheap to probe directly if we ever
  needed it; the interesting, hard-to-fake signal is outcome quality under a changing roster.

## 1. What MA-Gym already gives us for free

Non-stationary team composition is **already plumbed end-to-end**, it's just never used to
test correctness:

- `AgentRegistry.schedule_agent_add` / `schedule_agent_remove` / `apply_scheduled_changes_for_timestep`
  ([`manager_agent_gym/core/workflow_agents/registry.py:189-214`](../../manager_agent_gym/core/workflow_agents/registry.py)) —
  agents join/leave at a declared timestep during the run.
- Every scenario's `team.py::create_team_timeline()` returns a
  `{timestep: [("add"|"remove", AgentConfig, reason), ...]}` dict, and
  `examples/run_examples.py:111-122` feeds it straight into the registry calls above. This is
  the mechanism behind every "Join/Leave Schedule" table in `docs/benchmark/*.md`
  (see `data_science_analytics.md` for an example). **We reuse this unchanged.**
- `ManagerObservation.available_agent_metadata`
  ([`manager_agent_gym/schemas/execution/manager.py:39`](../../manager_agent_gym/schemas/execution/manager.py))
  already exposes the live roster (including `agent_capabilities`, free text) to the manager
  at each step.
- `diagnostics/analyze_diagnostic_runs.py` already re-derives the ground-truth join timeline
  and diffs it against the manager's *first assignment timestep* per agent — i.e. we already
  measure "how long after joining did the manager use this agent" and "did the manager's own
  observation see the agent's capabilities before assigning it." This is exactly the
  behavioural half of disruption-cost tracking. **We reuse this unchanged too.**

## 2. What's missing: no way to read fit off an outcome

Two gaps, both on the scoring/schema side, neither on the orchestration side. Note there is
**no third gap for "a required-type field on Task"** — deliberately: see the correction above.

| Gap | Where | Why it blocks the project plan |
|---|---|---|
| `AgentConfig` has no declared, inspectable trait tuple | [`manager_agent_gym/schemas/workflow_agents/config.py:9-21`](../../manager_agent_gym/schemas/workflow_agents/config.py) | `model_name` exists, but nothing declares a model *version* or a `capability` category on the config — those are only implicit in free-text `agent_capabilities`. Without these being fields, two worker instances can't be compared for "same declared type," which blocks both cold-start reasoning and Objective 2 reuse |
| Scoring is workflow-level rubrics (LLM-judge quality, function-based speed/cost, stakeholder, constraints) — no per-task deterministic requirements checklist | [`manager_agent_gym/schemas/preferences/rubric.py:25`](../../manager_agent_gym/schemas/preferences/rubric.py), `core/evaluation/common_evaluators.py:11` | Proposal's scoring needs a binary per-task checklist that can only be passed by a worker with the right trait tuple — that's what lets us *infer* fit from the outcome instead of asserting it with a label |

## 3. Schema changes

### 3.1 Trait tuple — make the worker's identity concrete and inspectable

Add to `manager_agent_gym/schemas/workflow_agents/config.py`:

```python
class AgentConfig(BaseModel):
    ...
    # model_name already exists (line 18) — trait-tuple component #1 (model),
    # and already carries the version in practice, e.g. "gpt-4o".
    model_version: str = Field(
        default="latest",
        description=(
            "Declared model version, where distinct from model_name (trait-tuple "
            "component #2). Defaults to 'latest' when the model_name string "
            "already fully identifies the version, e.g. 'gpt-4o'."
        ),
    )
    capability: str = Field(
        ...,
        description=(
            "Declared capability category for this agent, e.g. 'reasoning', "
            "'fast', 'multimodal' (trait-tuple component #3). Example tuple: "
            "('gpt-4o', 'latest', 'reasoning')."
        ),
    )
```

`(model_name, model_version, capability)` **is** the declared type — there's no separate type
label. Two `AgentConfig` instances with identical tuples are treated as the same type, which is
what lets a confirmed fit be reused across worker instances later (Objective 2) and what lets a
scenario author reason concretely about "this task needs a `('gpt-4o', 'latest', 'reasoning')`
worker" instead of "this task needs a skilled agent." `agent_capabilities` (existing, free text)
stays as-is — it's still what the manager *reads* to reason about fit; the trait tuple is the
underlying identity a scenario author uses to make sure the requirements checklist below is
actually tuple-dependent (e.g. a requirement item that a `'reasoning'`-tagged worker clears but
a `'fast'`-tagged one on the same base model reliably misses).

### 3.2 `Task.requirements` — where fit gets demonstrated, not asserted

Add to `manager_agent_gym/schemas/core/tasks.py`. No gold-label field — see the correction at
the top of this doc.

```python
class TaskRequirement(BaseModel):
    key: str                     # e.g. "identity_verification_flow"
    description: str
    check: Literal["deterministic", "llm_classifier"]

class Task(BaseModel):
    ...
    requirements: list[TaskRequirement] = Field(default_factory=list)
    requirements_pass_threshold: int | None = Field(
        default=None,
        description="Minimum requirements that must pass for completion credit.",
    )
    objective: Literal["objective_1", "objective_2"] | None = Field(
        default=None,
        description=(
            "Which AHT benchmark objective this task tests, purely for grouping "
            "results after scoring — never read by the grader or the manager."
        ),
    )
```

The manager sees exactly what it sees today: `name`, `description`, and the roster's
`agent_capabilities`. There is nothing new for it to peek at. What changes is entirely on the
authoring side: `requirements` must be written so that, of the trait tuples present in the
scenario, only the intended one can plausibly clear `requirements_pass_threshold` — the
ambiguity Point 1 asks for lives in the *task description* (similarly worded, genuinely
different needs), while `requirements` stays unambiguous and checkable.

### 3.3 Shared trait-tuple pool — defined once, deployed per scenario

`(model_name, model_version, capability)` (§3.1) is a *type* of tuple, not a specific one. To
make checklist authoring possible (§3.2's "only the intended one can plausibly clear it"), a
scenario author needs a fixed, enumerable set of *concrete* tuples to write checklists against
— not a fresh, ad hoc invention per scenario. That's a shared pool, independent of any one
scenario:

```python
# examples/end_to_end_examples/trait_pool.py (new, proposed)
TRAIT_POOL: dict[str, tuple[str, str, str]] = {
    "reasoning_gpt4o":   ("gpt-4o",      "latest", "reasoning"),
    "fast_gpt4o_mini":   ("gpt-4o-mini", "latest", "fast"),
    "extraction_gpt4o":  ("gpt-4o",      "latest", "extraction"),
    # ...grow as new scenarios need new tuples; each entry stays reusable across scenarios.
}
```

A scenario's `team.py` doesn't invent `model_version`/`capability` values inline — it pulls a
named entry from `TRAIT_POOL` and assigns it to an `AIAgentConfig`. This is what makes step 3
of the generic rule (§5.3) possible: "which pool tuples are deployed into this scenario" is a
well-defined, small, known set the checklist author can enumerate and write against, not an
open-ended judgment call re-made from scratch every time.

## 4. Scoring changes

Add a new deterministic evaluator, `manager_agent_gym/core/evaluation/task_requirements_evaluator.py`,
following the existing function-based pattern in `examples/end_to_end_examples/standard_rules.py:24,44`
(`speed_rubric`, `cost_rubric`) rather than the LLM-prompt `WorkflowRubric` path:

- **`requirements_met(task)`** — int pass count vs. `task.requirements_pass_threshold`, each
  `TaskRequirement` graded per its own `check` mode (deterministic checker function, or a
  narrow LLM classifier prompt scoped to one requirement — never an open-ended quality score,
  and never a comparison against a stored "correct agent" value, because there isn't one).
- **`task_credit(task)`** — full credit iff `requirements_met >= requirements_pass_threshold`.
  This is deliberately the *only* signal: if the assigned worker's trait tuple was wrong for
  the task, that shows up here as a failed requirement, not as a separate flag.

Wire this in as a fourth evaluator alongside `build_constraint_evaluator()`,
`build_stakeholder_evaluator()`, `build_operational_efficiency_evaluator()` in
`common_evaluators.py:11`, gated so it's a no-op (scores nothing) on tasks that don't set
`requirements` — existing scenarios' totals don't shift.

Because scoring stays per-task, results can be grouped after the fact by the `objective` field
(`"objective_1"` / `"objective_2"`) — matches the proposal's "results can be grouped by
objective afterward," without that field ever entering the grading logic itself.

**Fit and disruption, read together (Point 3):** `requirements_met` outcomes are then joined
post-hoc against the *existing* join/first-assignment-timestep diagnostics already in
`diagnostics/analyze_diagnostic_runs.py` (see §1). That join is where "fit" and "disruption"
actually become visible as a pair — e.g. an agent that got assigned quickly after joining but
whose task then failed `requirements_met` tells you the manager moved fast but guessed wrong;
an agent that sat unassigned for many timesteps despite a matching task piling up tells you the
opposite failure mode. Neither of those needs a label — they fall out of joining two things we
already have: assignment timing (existing) and requirements outcome (new, §3.2).

**Replanning disruption, per task, in one line: count how many times a task's
`assigned_agent_id` changes across a run's per-timestep snapshots, then label each change
necessary/unnecessary by whether `requirements_met` was failing/passing at that point.** Derived,
not a new schema field — the snapshots already exist (same ones the diagnostics script reads for
join timing, §1). Combined with `requirements_met`, this is what actually answers "correctly,
without disrupting more than necessary" (the last two rows of the problem statement in the
intro): a reassignment that preceded a `FAILED → COMPLETED` recovery is *necessary*; a
reassignment away from a task that was already on track to pass is *unnecessary*.

**This must be a reported metric of every run, not just a diagnostics-only side analysis.**
Performance (`requirements_met`/`task_credit`) is already a first-class scored output — it's
wired into an `Evaluator` that runs as part of every scenario execution and lands in
`evaluation_outputs/final_evaluation_*.json` automatically. Reassignment count must be surfaced
the same way, or the benchmark ends up measuring performance as a main outcome and disruption
only as an afterthought someone has to remember to compute separately — exactly the imbalance
flagged against the "task-dependent fit, with performance and disruption as the main outcomes"
framing. Concretely: compute it in `diagnostics/analyze_diagnostic_runs.py` (§7) as before (it's
an analysis over existing per-timestep logs, so it doesn't need a new `Evaluator`/schema field),
but write it into that run's `summary.json` as a standing per-task/per-run field, not just a
number that only appears when someone happens to invoke the script. It still doesn't need to
enter the preference-weighted score — "reported" and "scored" are different things — but it must
be reported by default.

## 5. Edit an existing MA-Gym scenario in place, one workflow at a time

**Decision (updated from the previous version of this plan):** modify MA-Gym's existing
`examples/end_to_end_examples/*` scenarios rather than writing a new folder from scratch, and
do it **one workflow at a time** — apply a generic, repeatable procedure to a single scenario,
land it, then repeat for the next. The pieces this needs (a dependency graph, a `team_timeline`,
a `preferences.py`) already exist per scenario and are already exercised by
`examples/scenarios.py`, `scripts/run.sh` / `scripts/eval.sh`, and
`diagnostics/analyze_diagnostic_runs.py` — editing in place keeps all of that working unchanged
and keeps each iteration's diff reviewable against a known-good baseline.

### 5.0 Picking which workflow to edit this iteration

Prefer one of the four scenarios the diagnostic suite already targets by name in
`scripts/run.sh` / `scripts/eval.sh` (`marketing_campaign`, `legal_m_and_a`,
`tech_company_acquisition`, `orsa`) — these already have a `team_timeline` with join/leave
events wired through `AgentRegistry` (§1) and are already what `analyze_diagnostic_runs.py`
reports on, so no diagnostics plumbing needs to change, only what it's pointed at. Re-run this
selection each time a new workflow is picked up; the rest of §5 assumes it's already been done
for the workflow at hand.

**Read-through finding (applies to every candidate, not just the first pick):** read
`legal_m_and_a/workflow.py` (356 lines, 15 top-level tasks) and `orsa/workflow.py` (418 lines,
16 top-level tasks) in full, and spot-checked the task-name lists of `marketing_campaign` and
`tech_company_acquisition`. All four are structured the same way: a single linear/branching DAG
of topically-**distinct** phases (e.g. `legal_m_and_a` runs Intake → Diligence → Structuring →
Drafting → Filings → Closing once; `orsa` runs Governance → Risk ID → Scenario Design →
Quantification → Reporting once). None contains two tasks that are already similarly-worded but
need different trait tuples, and none contains a task *type* that recurs at a non-adjacent
timestep — because these scenarios each model one enterprise program run once, not a
multi-client pipeline where the same request type recurs (unlike the proposal's own Appendix
example, which is explicitly about a team serving many clients whose requests repeat). Earlier
considering "Data Migration Planning" vs. "Data Migration & Validation" in
`tech_company_acquisition` as a candidate pair doesn't actually hold up either — those are
sequential phases of the *same* migration and plausibly want the *same* trait tuple, not
different ones.

**Practical consequence, carried into §5.3 step 1:** the "find, don't invent" instinct won't be
satisfiable by scanning any of the four candidates as-is — expect to graft new tasks/subtasks
onto an existing natural bundling point, not repurpose existing wording, for every workflow this
procedure is applied to.

`legal_m_and_a` is the first pick: smallest task count (15) among the four, and its existing
`team.py` already has two AI agents with clearly different, concrete trait-tuple-shaped jobs —
see §5.4.

### 5.1 End-to-end flow of the trait tuple

Before the generic per-workflow rule (§5.3), the connective piece: how one trait tuple travels
from definition to graded outcome, and who gets to see what, at each stage.

1. **Define the schema** (§3.1) — a tuple type, `(model, model_version, capability)`, that any
   worker can be labeled with.
2. **Declare a shared worker pool** (§3.3) — a set of concrete tuple *instances* (e.g.
   `"reasoning_gpt4o" → ('gpt-4o', 'latest', 'reasoning')`) that exist independently of any one
   scenario.
3. **Deploy workers into a scenario** — at scenario-build time, `team.py`/`team_timeline` pulls
   specific tuple instances from that pool and assigns them to agent slots, including join/leave
   timing for autoscaling (§5.3 steps 3 and 6).
4. **Author checklists with pool knowledge** (§3.2) — whoever writes a task's `requirements`
   knows which tuples exist in the pool *for that scenario* (§5.3 step 3), and writes checks
   that only the intended tuple could structurally pass.
5. **Runtime — the manager stays blind.** During the run, the manager only ever sees
   `description` + `agent_capabilities` (free text, via `ManagerObservation`, §1). It never sees
   the tuple or the checklist.
6. **Grading — fit inferred, not asserted** (§4). After the task completes, `requirements_met`
   is checked. If the assigned worker's tuple was right, the checklist passes; if wrong, it
   fails. Nobody ever compares against a stored "correct agent" — the pass/fail outcome *is* the
   fit signal.

**One-line summary:** tuple is *defined* once (shared pool) → *deployed* into a scenario (which
agent has which tuple, and when) → *known* to the checklist author (so checks are
tuple-discriminating) → *invisible* to the manager at runtime → *inferred* after the fact from
whether the checklist passed.

### 5.2 Worker pool restriction

`AIAgentConfig` only (Point 1) in every edited scenario — no `HumanAgentConfig` instances.
Human-worker constraints (certification, contracts, safety regs) are out of scope per the
proposal, and mixing them in adds a confound to trait-tuple fit measurement that isn't needed.
Applied per-workflow as step 2 of §5.3.

### 5.3 Generic rule, per workflow

Applied once per scenario, in order, each time a new workflow is taken on:

1. **Check feasibility** — does this workflow have a task whose description already bundles 2+
   genuinely different specialties (a natural graft point)? Per §5.0's read-through finding:
   none of the four candidates have this ready-made — expect to be grafting new tasks, not
   finding them, for every workflow.
2. **Convert/drop human-only roles.** Per-role audit: convert to `AIAgentConfig` if the role is
   really just "another knowledge worker" (fine — equivalent `agent_description`/
   `agent_capabilities`), or drop/reassign the tasks that specifically depend on it if the role
   only exists for a human-specific reason (sign-offs, executive approval) the AI-only
   restriction (§5.2) rules out. Done per-role by reading `team.py` and cross-referencing
   `workflow.py`/`preferences.py` for what depends on each `agent_id` — not mechanically.
3. **Identify which tuples from the shared pool (§3.3) will be deployed into this scenario.**
   Needed *before* step 4, since a checklist can only discriminate against tuples that actually
   exist in the pool for this run — pick 2+ pool entries whose declared `capability` plausibly
   diverges on the graft point identified in step 1.
4. **Graft two similarly-named subtasks with disjoint `requirements` checklists** onto the
   natural graft point from step 1, each authored (§3.2) to be clearable only by one specific
   pool tuple from step 3 — the Objective-1 test.
5. **Graft one later, differently-worded task** at a non-adjacent timestep that needs the same
   tuple as one of step 4's new subtasks, with an overlapping `requirements` checklist — the
   Objective-2 reuse test.
6. **Deploy workers with the needed tuples (from step 3) into the scenario's `team_timeline`**,
   timed to simulate autoscaling (join/leave) around the grafted tasks from steps 4-5 — tuples
   come from the shared pool, not invented inline in this scenario's `team.py`.

Add `requirements`/`requirements_pass_threshold`/`objective` (§3.2) only to the tasks touched in
steps 4-5, plus whichever task(s) are chosen for the §5a reassignment/restraint elements. Every
other task in the workflow is untouched — the requirements evaluator (§4) is a no-op without
`requirements`, so the rest of the scenario's existing scoring behavior doesn't move.

Land the generic rule on **one** workflow before touching a second — the proposal's own Scope
note says depth over breadth for the September–October window. Expect to keep iterating on what
actually makes a checklist item trait-tuple-dependent in practice — that authoring judgment call
is the hard part of every iteration of step 3-4, not the schema, and it's best done by reading
the chosen workflow's actual task graph rather than from this doc alone.

### 5.4 First application: `legal_m_and_a`

Working through §5.3's six steps for the first workflow (mirrors the Appendix example in the
proposal — "Build checkout page" / "Build user profile page" was illustrative there; the actual
pair is grafted onto T6 below):

1. **Feasibility (step 1):** existing task T6, **"Legal Diligence – Material Contracts, IP, &
   Privacy"** (`legal_m_and_a/workflow.py`, no subtasks currently), bundles contract review, IP
   chain-of-title, and privacy posture — three genuinely different specialties inside one
   generically-worded task. That's the graft point.
2. **Human-role audit (step 2):** `legal_m_and_a/team.py` is 11 `AIAgentConfig` /
   ~12 `HumanAgentConfig` entries (checked directly) — every `HumanAgentConfig` gets converted
   or its dependent tasks dropped/reassigned per the per-role process in §5.3 step 2.
3. **Pool tuples for this scenario (step 3):** two of `legal_m_and_a/team.py`'s existing AI
   agents already suggest which pool entries fit — `deal_counsel_ai` (drafts/negotiates SPA
   language, judgment-heavy trade-offs across indemnities and covenants: `"reasoning_gpt4o"`)
   and `diligence_reader` (triages data-room documents into a structured index, high-volume
   pattern-matching extraction: `"fast_gpt4o_mini"` or `"extraction_gpt4o"`). These become the
   two pool tuples this scenario deploys against T6's graft point.
4. **Objective-1 graft (step 4):** split T6 into two subtasks with generic, similar-sounding
   names (e.g. "Contract Terms Review" / "IP & Privacy Compliance Review") consistent with T6's
   existing bundled framing. One's `requirements` checklist is clearable by the
   `"reasoning_gpt4o"` tuple, the other's only by the privacy/compliance-suited tuple. Both
   tagged `objective="objective_1"`.
5. **Objective-2 graft (step 5):** add one new task/subtask at a later phase (e.g. under T13,
   "Closing Mechanics & Bring-Down Diligence") worded differently from the IP/privacy subtask
   but needing the same tuple, with an overlapping `requirements` checklist — tagged
   `objective="objective_2"`.
6. **Deploy into the timeline (step 6):** `deal_counsel_ai` is already on the team at the
   scenario's existing join timestep — no change needed there. A worker carrying the
   privacy/compliance tuple (a converted `privacy_counsel`, or `diligence_reader`, depending on
   how step 2's conversion lands) joins later at a non-adjacent timestep — either an existing
   join event in the current `team_timeline` if one already lands near the right point,
   otherwise a small, deliberate addition. Success is read off each grafted task's own
   `requirements_met` outcome once assigned — not off which worker the manager picked. If the
   manager assigns the familiar `deal_counsel_ai` to the privacy subtask instead, that
   checklist fails on its own; no separate correctness check needed.

`legal_m_and_a`'s own existing unrelated tasks (financial diligence, antitrust/CFIUS, financing,
closing mechanics, etc.) and agent joins already provide the "noisy roster" — nothing to add
there.

### 5a. Reassignment-when-warranted and restraint — the two new rows from the problem statement

These extend whichever workflow §5.3 is currently being applied to — they aren't a separate
scenario, and they're grafted using the same step 4-6 mechanics. Both reuse `TaskStatus.FAILED`
([`manager_agent_gym/schemas/core/base.py:15`](../../manager_agent_gym/schemas/core/base.py)),
which is already an observable status the manager reacts to — no schema change needed here,
only scenario authoring:

1. **Reassignment-when-warranted.** One task in the scenario is deliberately mis-assigned early
   (e.g. the manager's most plausible reading of an ambiguous description points at the wrong
   trait tuple — this can happen "for free" if step 4's ambiguity works as intended, or be
   forced by only having the wrong-tuple worker available at t=0). Its execution fails one or
   more `requirements` checks badly enough that the task ends `FAILED` rather than `COMPLETED`,
   goes back to unassigned, and a worker with the right trait tuple is available (already on
   the team, or joins shortly after — deployed per step 6). Correct behavior: the manager
   reassigns it and the retry clears `requirements_pass_threshold`. This directly tests
   "reassign ... correctly," not just "assign correctly the first time."
2. **Restraint.** A separate task is assigned correctly at t=0 and is already on track to clear
   its `requirements` checklist. Partway through, a new worker joins whose declared profile
   *also* looks plausible for that task (a deliberate red herring, e.g. overlapping
   `agent_capabilities` wording but a different pool tuple). Correct behavior: the manager
   leaves the existing assignment alone. Wrong behavior: churn — reassigning to the new arrival
   for no evidence-based reason, which is exactly the "chasing optimality" failure mode the
   proposal warns against.

Both are graded the same way as everything else — via `requirements_met` on the task's
eventual outcome — plus the reassignment-count signal from §4. The reassignment-when-warranted
item wants that count to go from wrong-fit to right-fit exactly once; the restraint item wants
it to stay at zero after the red-herring joins. Neither scenario element needs the manager to
see anything it doesn't already see — the setup produces the test condition, the outcome plus
the reassignment count is what gets graded.

## 6. Sequencing (per your pasted guidance)

1. **This step — trait-tuple + requirements schema, and editing one existing scenario
   in place** (§5.0-§5.4, §5a). No simulation runs needed; this is pure schema editing plus
   `team.py`/`workflow.py`/`preferences.py` edits on the chosen scenario, fully offline.
2. **Baseline diagnostic re-run on the edited scenario**, not the untouched original — this is
   the point where `requirements_met` becomes checkable per task instead of just "did anything
   get produced." Per `CLAUDE.md`, this step requires running `scripts/run.sh` against the
   edited scenario, which calls the OpenAI API — **do not run this without an explicit, separate
   ask**, even once the edits are made.
3. **Disruption-cost instrumentation on top** — extend
   `diagnostics/analyze_diagnostic_runs.py`'s existing join/first-assignment-timestep logic
   with the per-task reassignment count (§4) and join it against `requirements_met`, so
   "reassigned to a worker that then failed the checklist," "never reassigned when the
   incumbent's task was failing" (misses the reassignment-when-warranted case in §5a), and
   "reassigned even though the incumbent was already clearing its checklist" (the restraint
   case in §5a) become distinguishable, not just raw event counts.

## 7. File-by-file change list

| File | Change |
|---|---|
| `manager_agent_gym/schemas/workflow_agents/config.py` | add `AgentConfig.model_version: str`, `AgentConfig.capability: str` |
| `manager_agent_gym/schemas/core/tasks.py` | add `TaskRequirement` model; add `Task.requirements`, `Task.requirements_pass_threshold`, `Task.objective` |
| `manager_agent_gym/core/evaluation/task_requirements_evaluator.py` (new) | `requirements_met`, `task_credit` functions + evaluator builder |
| `manager_agent_gym/core/evaluation/common_evaluators.py` | add a `workflow` parameter to `build_default_evaluators()` (currently takes only `communication_service`, `common_evaluators.py:11` — it has no way to loop over `workflow.tasks` today) so it can attach a requirements-evaluator per task that sets `requirements` (no-op otherwise); update its one call site in `examples/run_examples.py:170-172`, where `workflow` is already in scope |
| `examples/end_to_end_examples/trait_pool.py` (new) | shared `TRAIT_POOL` dict of named `(model_name, model_version, capability)` instances (§3.3), imported by `team.py` across scenarios instead of inventing values inline |
| `examples/end_to_end_examples/legal_m_and_a/team.py` | convert/drop `HumanAgentConfig` entries per §5.3 step 2; assign pool tuples (§3.3) via `model_version`/`capability` on remaining `AIAgentConfig`s per §5.3 step 3/§5.4 step 3; adjust `team_timeline` only where §5.3 step 6/§5a needs a specific join |
| `examples/end_to_end_examples/legal_m_and_a/workflow.py` | split T6 into two subtasks for Objective 1 (§5.3 step 4/§5.4 step 4), add one new task under T13 for Objective 2 (§5.3 step 5/§5.4 step 5), add `requirements`/`requirements_pass_threshold`/`objective` to those plus the §5a tasks only — all other tasks untouched |
| `examples/end_to_end_examples/legal_m_and_a/preferences.py` | audit for rubrics that reference a role dropped in §5.3 step 2's human-role audit; update/remove as needed |
| `examples/scenarios.py` | no change — the chosen scenario is already registered |
| `scripts/run.sh`, `scripts/eval.sh` | swap `WORKFLOWS="marketing_campaign"` → `WORKFLOWS="legal_m_and_a"` (already a valid, listed option in both — just not the current default) so §6 step 2's baseline diagnostic re-run actually targets the edited scenario |
| `diagnostics/analyze_diagnostic_runs.py` | add per-task reassignment-count helper (§4); join existing join/assignment-timestep analysis against the new per-task `requirements_met` outcome and reassignment count; write reassignment count into `summary.json` as a standing per-run field (§4) rather than a number only produced on manual invocation |

## 8. Explicitly out of scope for this pass

- Worker-*leave* handling beyond what `schedule_agent_remove` already does (per the proposal:
  "explore if time permits").
- The manager's own capability-estimate/memory solution (proposal's Goal 3) — this plan only
  makes the benchmark capable of grading that solution once it exists.
- Any change to the "5 values" default preference scoring (quality/speed/cost/stakeholder/constraints)
  — the new evaluator is additive and scoped to tasks that set `requirements`.
- Any stored ground-truth "correct agent/type" field — deliberately not part of this design;
  fit is read off `requirements_met`, never off a label (see the correction at the top).
