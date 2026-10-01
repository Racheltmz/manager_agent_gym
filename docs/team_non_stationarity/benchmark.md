# Benchmark Design

Part of [`index.md`](index.md). Metrics are in [`metrics.md`](metrics.md); this doc covers only
how scenarios are built so that those metrics are meaningful.

## Core problem to solve

Worker prompts today are quite generic, so a good model performs well regardless of who it is
assigned to. If that holds, the manager can ignore a new worker, or drop a task whose worker left,
and still score well, so roster changes would have no measurable consequence.

**Design principle: every roster event must change what the correct delegation is, and a wrong
delegation must visibly fail a deterministic check.**

## 1. Worker-private content

Each worker's prompt includes content **only that worker holds**, which a generic model could not
know or guess:

- a specific required output format (field names, section order, delimiter, ID scheme), or
- internal rules (e.g. a mandatory clause, a naming convention, a fixed escalation line).

Workers share one base model, so the *only* thing differentiating them is this prompt content.

Requirements for the private content:

- **Deterministically checkable** from the task's output (regex, schema, string presence), so it
  can drive checklist items without an LLM judge.
- **Not inferable** from the task description or the worker's public `agent_capabilities` text. The
  manager sees the capability description, not the private rule, so the capability text should
  describe the worker's *domain*, not leak the rule itself.
- **Disjoint across workers** where tasks are meant to be gated to a single worker.

## 2. Gated tasks

A **gated task** has a checklist that can only be fully passed by a worker holding the matching
private content (e.g. output must follow format F, which only worker W knows).

Each gated task has a hidden mapping to its correct worker(s). See [`metrics.md`](metrics.md#hidden-task-to-worker-mapping).

## 3. Event types

### Join events

- Schedule at least one task that **depends on the new worker**: it can pass its checklist only if
  assigned to that worker.
- Why: otherwise the manager can skip the new worker entirely and still score well.
- Expected good behavior: notice the join, route the gated task to the new worker.

### Leave events

- A worker is removed **mid-task**, and the task it was running is gated on its private content.
- Only a *remaining* or *newly joined* worker with the matching private content can finish it.
- Why: otherwise dropping the task would cost nothing.
- Expected good behavior: detect the orphaned task, reassign it to the right worker.

Design note: for a leave event to be recoverable, a worker holding the matching private content
must exist after the leave (either already on the roster or joining at/after the leave). A leave
where nobody can finish the task is a different scenario ("graceful degradation") and should be
a separately labelled variant, not mixed in.

### Control tasks

Every scenario keeps **unaffected tasks** that no event touches. They check the manager does not
disrupt work it should leave alone (e.g. needlessly reassigning a task whose worker stayed).
Control tasks are the denominator side of disruption cost in [`metrics.md`](metrics.md).

## 4. Schedule

- The join/leave schedule is **predefined and replayable**: a fixed `{timestep: [(action,
  agent_cfg, reason), ...]}` dict, the same shape `create_team_timeline()` already returns, so no
  engine interface change.
- The schedule is independent of the manager's behavior (exogenous), so runs across manager types
  are comparable.
- Reason strings should describe the scaling event ("scale-out: worker pool expanded"), not name
  the task it is meant to serve.
- Leave timing is deliberately **mid-task**: the leaving worker must have an in-progress task at
  the event timestep. Verify against task durations / dependency graph when authoring, since
  the earlier AHT design's rule that a worker never leaves mid-work is intentionally inverted here.

## 5. Gate validation (if feasible)

For each gated task, run the task with **every non-matching worker** and confirm it **fails** the
checklist; run with the matching worker and confirm it **passes**.

- Confirms the gate actually discriminates, i.e. that a generic model with the wrong private
  prompt cannot pass by being good.
- Costs: this runs workers (LLM calls). It must be run only on an explicit ask per `CLAUDE.md`,
  never proactively.
- Output: a table `task × worker → pass/fail`, stored alongside the scenario; this table also
  *is* the source of truth for the hidden mapping.

## 6. Scenario starting point

Candidate: adapt `examples/end_to_end_examples/legal_m_and_a` into
`examples/end_to_end_examples_team/legal_m_and_a` (it has a `team_timeline`; its human roles must be
converted to AI agents). Work to do:

- [ ] Add private content to each worker prompt
- [ ] Add checklist items that depend on that content to the gated tasks
- [ ] Place at least one join-gated task and one leave-gated (mid-task) task
- [ ] Keep a set of untouched control tasks
- [ ] Write the predefined timeline
- [ ] Run gate validation (needs explicit approval to spend API budget)

## Open questions

- How many events per scenario (one join + one leave, or several)? Starting small keeps the
  metrics interpretable.
- Should a leave event ever be *predictable* (announced ahead of time) as a variant? Spec says
  abrupt, so default is no.
- Checklists use `TaskRequirement` in
  [`tasks.py`](../../manager_agent_gym/schemas/core/tasks.py): each item has a regex `pattern`
  matched against the task output (`passes()`). The schema exists; the evaluator that turns
  items into a per-task score is not built yet (see [`metrics.md`](metrics.md)).
