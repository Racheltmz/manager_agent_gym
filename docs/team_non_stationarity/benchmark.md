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

Each gated task has a hidden mapping to its correct worker(s). See [`metrics.md`](metrics.md#hidden-task-to-worker-mapping).

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
- Validate the gate by running that task with every non-matching worker and confirming it fails the
  checklist (section 7).

Design note: a leave after which **no** remaining worker holds the needed content makes the task
impossible. That is a different scenario ("graceful degradation"); keep it as a separately labelled
variant, not mixed in.

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

## 7. Gate validation (if feasible)

For each gated task, run the task with **every non-matching worker** and confirm it **fails** the
checklist; run with the matching worker and confirm it **passes**.

- Confirms the gate actually discriminates, i.e. that a generic model with the wrong private
  prompt cannot pass by being good.
- Costs: this runs workers (LLM calls). It must be run only on an explicit ask per `CLAUDE.md`,
  never proactively.
- Output: a table `task × worker → pass/fail`, stored alongside the scenario; this table also
  *is* the source of truth for the hidden mapping.

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
- [ ] Run gate validation (needs explicit approval to spend API budget)

## Open questions

- How many events per scenario (one join + one leave, or several)? Starting small keeps the
  metrics interpretable.
- How is a running task handed over in the engine: does reassigning a RUNNING task cancel and
  restart it, or does it have to be a new action? Today it only overwrites `assigned_agent_id`.
- Checklists use `TaskRequirement` in
  [`tasks.py`](../../manager_agent_gym/schemas/core/tasks.py): each item has a regex `pattern`
  matched against the task output (`passes()`). The schema and the evaluator that turns items into
  a per-task score both exist (see [`metrics.md`](metrics.md)).
