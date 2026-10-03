# Benchmark Design

Part of [`index.md`](index.md). Metrics are in [`metrics.md`](metrics.md); this doc covers only
how scenarios are built so that those metrics are meaningful.

## Core problem to solve

Worker prompts today are quite generic, so a good model performs well regardless of who it is
assigned to. If that holds, the manager can ignore a new worker, or leave a gated task unrouted
after a leave, and still score well, so roster changes would have no measurable consequence.

**Design principle: every roster event must change what the correct delegation is, and a wrong
delegation must visibly fail a deterministic check.** The cases in section 3 make that decision
harder than "always use the new worker".

## 1. Worker-private content

Each worker's prompt includes content **only that worker holds**, which a generic model could not
know or guess:

- a specific required output format (field names, section order, delimiter, ID scheme), or
- internal rules (e.g. a mandatory clause, a naming convention, a fixed escalation line).

Workers share one base model, so the *only* thing differentiating them is this prompt content.

Requirements for the private content:

- **Deterministically checkable** from the task's output (regex, schema, string presence), so it
  can drive checklist items without an LLM judge.
- **Declared and accurate.** Each worker's `agent_capabilities` truthfully describes its
  specialty, and with the task description it is enough to identify which worker should get a gated
  task. What stays hidden is the *exact* private rule (the precise format string or clause) that the
  checklist tests.
- **Disjoint across workers** where tasks are meant to be gated to a single worker.

## 2. Gated tasks

A **gated task** has a checklist that can only be fully passed by a worker holding the matching
private content (e.g. output must follow format F, which only worker W knows). The gate is a
**deterministic format check**.

Each gated task records its correct worker(s) in the scenario spec. This mapping is scorer-only and
is not used by the headline metrics; see [`metrics.md`](metrics.md#task-to-worker-mapping-optional-diagnostics-only).

## 3. Change-affected cases

Each change-affected task is assigned to **exactly one** case, and each case has a **fixed best
action**. The case is rotated across workflows so no single behavior is enough.

| Case | Setup | Fixed best action |
|---|---|---|
| **Specialist worker** | The new worker is better only on certain task types: tasks of that type are gated on its private format. | Route tasks of that type to the new worker; leave other task types where they are. |
| **Running task** | A join happens while a task is in progress with the current worker, and the task is gated on the new worker's format. | Hand the running task to the new worker rather than letting the current worker finish it. |

Notes:

- **A handed-over running task restarts fresh.** Resuming from partial progress is left for future
  work.
- The case is attached to the task in the scenario spec (with the correct worker), and results can
  be reported per case.
- Both cases use the deterministic format gate from section 2.
- Task failures are out of scope for now, so no case depends on a task failing.

Not kept for now: a **split/merge** case (the new worker suits a different task granularity). It is
set aside until a prompt-based granularity limit is shown to be reliable.

## 4. Event types

### Join events

- Schedule at least one task that **depends on the new worker**: it can pass its checklist only if
  assigned to that worker.
- Why: otherwise the manager can skip the new worker entirely and still score well.
- The manager is **notified of the join before its next assignment decision**.
- Expected good behavior: notice the join and apply the fixed best action for each affected case.

### Leave events

- A worker that has been assigned a task **finishes it before leaving**, so a leave never requires
  reassigning assigned work.
- After a leave the worker **cannot be given new tasks**, and the manager is **notified of the
  leave before its next assignment decision**.
- Every task not yet assigned is **still required** and must be completed by a worker that remains.
- **At least one unassigned task is gated to a worker who remains.** Otherwise a leave changes
  nothing the manager must do, and dropping a task would cost nothing.
- Expected good behavior: stop assigning to the departed worker and route the unassigned gated task
  to the remaining worker that holds the matching content.
- Validate the gate: no non-matching worker should be able to pass the checklist (judged for now;
  measured by gate validation when re-adopted, section 7).

Design note: a leave after which **no** remaining worker holds the needed content makes the task
impossible. That is a different scenario ("graceful degradation"); keep it as a separately labelled
variant, not mixed in.

### Event count

- **Target: the source scenario's number of mid-run changes.** An event is one worker joining or
  leaving after timestep 0 (several can share a timestep), and a worker re-added under an id already
  on the roster is not a join. Matching the source keeps the benchmark from being weaker than the
  original and gives the manager as much churn.
- **Compliance beats count.** Every kept event must meet the join or leave rules above in full: a
  gated task that depends on it, a task still gated to a remaining worker after a leave, and a leave
  that lands only after the worker's assigned tasks are finished.
- **Drop an event rather than force-fit it.** If a source change cannot become a compliant event
  without bending the task graph, drop it: the worker joins at timestep 0 if still needed, or is
  left out. Never keep a roster change that no affected task depends on; the static check rejects it.
- **Every dropped event is listed in `CONVERSION.md`** with the reason, and the static check warns
  when the scenario has fewer events than the source.

### Rules for the rest of the scenario

The rules apply to every agent and task, not only the ones an event names:

- **Agents:** AI only, with an accurate declared profile and private content held by that worker
  (section 1). No worker is pre-assigned a task.
- **Tasks:** gated tasks follow section 2, and every task no event touches is a control task.
  Controls with a checklist give the baseline score.
- **Roster at the start:** everything on the initial roster follows the same agent rules.
- The skill walks through every agent and task against these rules, not only the events.

### Control tasks

Every scenario keeps **unaffected tasks** that no event touches. They check the manager does not
disrupt work it should leave alone. The ground truth says their current assignment was already
best, so any move of a control task is unnecessary. They are the numerator and denominator of
disruption cost in [`metrics.md`](metrics.md).

## 5. Task graph editing

When a change makes the existing plan a poor fit for the new roster, the manager should edit the
task graph if necessary. No case in section 3 currently requires this (it belongs to the deferred
split/merge case), but the manager keeps the ability, and scoring must tolerate it: a manager that
removes or renames an affected task must score 0 for it, not crash the metrics (see
[`known_bugs.md`](known_bugs.md), ML-015).

## 6. Schedule

- The join/leave schedule is **predefined and replayable**: a fixed `{timestep: [(action,
  agent_cfg, reason), ...]}` dict, the same shape `create_team_timeline()` already returns, so no
  engine interface change.
- The schedule is independent of the manager's behavior (exogenous), so runs across manager types
  are comparable.
- Reason strings should describe the scaling event ("scale-out: worker pool expanded"), not name
  the task it is meant to serve.
- Leave timing is constrained: when authoring, check against task durations and the dependency
  graph that **every task assigned to the leaving worker is finished** at the event timestep, and
  that at least one unassigned gated task still lies ahead. This also rules out an
  assigned-but-unstarted task, which the engine would silently never start (see
  [`known_bugs.md`](known_bugs.md)).

## 7. Gate validation

> **Status: deferred.** Considered and built, but not used for now because it costs one Claude call
> per affected task per worker. Conversion instead sets `correct_agents` by judgment: the converting
> model reads each affected task's description against each worker's description and private content
> and applies the pass rules below as a self-check. The mapping is then unverified by worker output.
> Run `gate-run <workflow> --enable` only when this is re-adopted.

Confirms that each gate discriminates, and **derives the task-to-worker mapping** from the result.

**How it runs** (`scripts/team_benchmark.py gate-run <workflow>`):

- For every affected task and every worker that **can receive it**, Claude (Sonnet, `claude -p`
  with no tools) plays that worker. The workers that can receive a task are everyone on the roster
  after its event, plus anyone who joins later (the manager can assign at any time after the event),
  plus the leaver of a leave event (the leave rule needs its result). A worker who left before the
  event is not tested. Only the affected tasks are validated; control tasks are not gated. The system prompt is the worker's own `system_prompt`. The user
  prompt is the real worker task template with the task's name and description and no input
  resources, plus one line asking for the deliverable text only.
- The reply is scored against the task's checklist patterns. A cell **passes** only if every item
  passes, so each cell is a deterministic pass or fail. Nothing is judged by an LLM.
- Output: a `task × worker → pass/fail` table and the saved replies, in
  `examples/end_to_end_examples_team/<workflow>/gate_validation/`. Replies are reused until the
  worker prompt, task or model changes.

**Pass rules** (the run fails if any is broken):

- **Join-affected task:** exactly the joining worker passes among the workers that can receive it. Any other worker passing means the
  gate does not discriminate. The joining worker failing means the gate is unreachable.
- **Leave-affected task:** the leaving worker passes, and at least one worker still on the roster
  after the event passes, so the task stays solvable and the leave changes the correct delegation.
- Every cell needs a reply. A failed generation is an error, never a fail.

**Derived mapping.** The correct workers for a task are the workers that pass it and are on the
roster after its event. The scenario's `correct_agents` must equal this set (the authoring check
enforces it), so the mapping comes from the table, not from the plan.

**Limits**

- **Claude stands in for the worker model.** Manager runs use a different model, so this verifies
  the gates on a proxy. A gate that a Claude worker without the private content cannot pass is
  still not proof for every model.
- **One reply per cell**, so the table is one sample, not a pass rate. A borderline gate can flip
  between runs.
- **No upstream resources.** Real workers also receive their input resources; validation does not.
- **Cost:** one Claude call per affected task per worker that can receive it, in Claude usage and
  never OpenAI credits. It scales with affected tasks × the roster at the time of assignment.

## 8. Scenario starting point

Candidate: adapt `examples/end_to_end_examples/legal_m_and_a` into
`examples/end_to_end_examples_team/legal_m_and_a` (it has a `team_timeline`; its human roles must be
converted to AI agents). Work to do:

- [ ] Add private content to each worker prompt
- [ ] Add checklist items that depend on that content to the gated tasks
- [ ] Add change-affected tasks for the kept cases (specialist, running task), one case per task,
  rotated across workflows
- [ ] Place a leave that lands after the worker's assigned tasks are finished, with at least one
  unassigned task still gated to a remaining worker
- [ ] Keep a set of untouched control tasks
- [ ] Write the predefined timeline
- [ ] Judge the task-to-worker mapping (done by the skill; gate validation is deferred)

## 9. Generating scenarios from this doc

Scenarios in `examples/end_to_end_examples_team/` are generated from this doc by the
`create-team-benchmark` skill ([`SKILL.md`](../../.claude/skills/create-team-benchmark/SKILL.md)),
which reads this doc fresh on every run. So the way to change what every scenario looks like is to
edit this doc and rerun.

- Convert one workflow: `scripts/create_team_benchmark.sh <workflow>` (or `/create-team-benchmark
  <workflow>` inside Claude Code). A rerun **recreates the scenario from scratch**.
- See what is out of date: `scripts/create_team_benchmark.sh --status`. A scenario is stale when this
  doc, `metrics.md`, the skill, or its source workflow changed after it was generated.
- Mechanical checks (AI-only roster, spec matches timeline, checklists have patterns, controls
  exist, and so on): `uv run python scripts/team_benchmark.py check <workflow>`. If you add or remove
  a case in the table above, update `KNOWN_CASES` in that script; it warns when they disagree.

## 10. Validating a scenario

Three layers, cheapest first. The first two test the **benchmark**. The third uses manager runs, so
it tests whether the benchmark **discriminates between managers**.

| Layer | Tests | How | Cost | Status |
|---|---|---|---|---|
| Static check | The scenario follows the structural rules (AI-only roster, spec matches timeline, checklists have patterns, controls exist, `correct_agents` matches the gate table) | `scripts/team_benchmark.py check <workflow>`, run by the skill | Free, no LLM | Built |
| Gate validation | Each gate discriminates between workers, and the task-to-worker mapping is derived from the result (see *Gate validation*) | `scripts/team_benchmark.py gate-run <workflow> --enable` | One Claude call per task per worker | Built, deferred (mapping is judged instead) |
| Manager runs | Scores respond to delegation: `random` scores clearly below its control baseline on the affected tasks, and `cot` scores above `random` on them | Run `cot` and `random` over several seeds, read the post-change score, baseline and disruption cost from `metrics.md` | OpenAI API calls, only on an explicit ask | Not built: no pass/fail rule or dashboard indicator yet |

Notes:

- **`assigned_correctly` is not one of these layers.** It is a diagnostic on a manager run (did this
  manager give the task to a derived-correct worker), so a bad manager fails it on a perfect
  benchmark. Use it to explain a result, not to validate a scenario.
- If the manager-run layer looks wrong, check the first two layers before suspecting the manager.
  A red result cannot say whether the cause is a weak gate, a bad schedule, or a weak manager.
- An **oracle manager** that assigns from the derived mapping would give an upper bound for the
  third layer (see [`metrics.md`](metrics.md#task-to-worker-mapping-optional-diagnostics-only)). It
  is not built.

## Open questions

- How is a running task handed over in the engine: does reassigning a RUNNING task cancel and
  restart it, or does it have to be a new action? Today it only overwrites `assigned_agent_id`.
- Checklists use `TaskRequirement` in
  [`tasks.py`](../../manager_agent_gym/schemas/core/tasks.py): each item has a regex `pattern`
  matched against the task output (`passes()`). The schema and the evaluator that turns items into
  a per-task score both exist (see [`metrics.md`](metrics.md)).
