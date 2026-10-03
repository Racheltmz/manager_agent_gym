# Metrics

Part of [`index.md`](index.md). Scenario construction is in [`benchmark.md`](benchmark.md).

**Principle:** task requirements are evaluated **deterministically at each step**, so we can
quantify how well the manager actually performed without an LLM judge.

**What is measured:** outcomes. *Fit* is how well each affected task came out given the worker it was
assigned to (the checklist score). *Disruption* is how much reassignment churn the manager caused
(moves of control tasks). The metrics do **not** check whether the manager "identified" the correct
worker; that is only a diagnostic (see the mapping below).

## Task-to-worker mapping (optional, diagnostics only)

`correct_agents` in the scenario's `team_change_spec.py`: for each affected task, the worker(s) that
should hold it.

- **Not used by the headline metrics.** Post-change score and disruption cost come from the
  checklist outcome and from control-task moves alone.
- **Used for three optional things:**
  - the `assigned_correctly` diagnostic (did the affected task end with a listed worker?), which
    separates "wrong worker" from "right worker, bad output";
  - the authoring check (every affected task has an entry, and a correct worker remains after each
    event);
  - an **oracle manager** that reads it to give an upper bound. Not built, and it would be a
    validity tool, never a baseline in reported results.
- **Scorer-only.** Never exposed to the manager (it sees only task descriptions and public
  `agent_capabilities`).
- **Set by judgment for now**: the converting model maps each affected task's description to the
  workers' descriptions and private content. Gate validation (`task × worker → pass/fail`, see
  [`benchmark.md`](benchmark.md#7-gate-validation)) would derive it from worker outputs but is
  deferred; if a gate table exists, the spec must match it (the authoring check enforces it).
  Either way it is not verified on the model used in manager runs.
- Control tasks need no entry.

## Affected tasks and control tasks

After each join or leave event, the **affected tasks are fixed in advance** (in the scenario spec),
not computed from the run:

- Join event → tasks gated on the new worker (the specialist and running-task cases).
- Leave event → unassigned tasks gated to a worker who remains.

Every other task is a **control task**: no event touches it, and its current assignment is already
best by the fixed ground truth.

## Metric 1: Post-change score

Mean deterministic checklist score over the affected tasks, after the event.

```
task_score(t)      = items_passed(t) / total_items(t)
post_change_score  = mean over t in affected(event) of task_score(t)
```

- Computed per event, then averaged per scenario/run.
- **Compare against general workflow performance**: mean `task_score` over all control tasks in the
  same run. The gap (`post_change_score - baseline_score`) shows how much the roster change
  specifically hurt or helped.
- Unfinished or never-assigned affected tasks score `0` (not excluded), otherwise dropping a task
  would be free.
- Reassigning an affected task correctly (for example moving a gated task to the specialist)
  **shows up here**, not in disruption cost.

## Metric 2: Disruption cost

```
disruption_cost = control tasks moved to a different worker
                  / control tasks that already had an agent assigned at the event
```

- **Numerator:** control tasks (not affected by the join or leave) that the manager moved to a
  different worker. These are unnecessary by definition, since the fixed ground truth says the
  current assignment was already best.
- **Denominator:** all control tasks that had an agent assigned at the time of the event.
- **Range:** 0 to 1. **0 means the manager left everything it should have alone.**
- Reassigning an affected task correctly does **not** count against it.

## Metric 3: Cost (later)

Cost in time, resources and so on. To be worked on later.

## Reading the first two together

| Post-change score | Disruption cost | Interpretation |
|---|---|---|
| High | Low | Delegated correctly and left other work alone |
| High | High | Fixed the affected tasks, but churned control tasks (thrashing) |
| Low | Low | Ignored the roster change (e.g. never used the new worker, or left a gated task unrouted) |
| Low | High | Moved a lot of work, to the wrong workers |

## Implementation

Computed post hoc from the per-timestep snapshots a run already writes
(`workflow_outputs/workflow_execution_<run_id>_t<NNNN>.json`), so there is no engine change and no
LLM call. Running it only reads existing files.

| Piece | Where | Status |
|---|---|---|
| Per-task checklist score (items passed / total) | [`task_requirements_evaluator.py`](../../manager_agent_gym/core/evaluation/task_requirements_evaluator.py) | Matches this doc |
| Post-change score, baseline, disruption cost (control tasks only), per-case scores | [`team_change_metrics.py`](../../manager_agent_gym/core/evaluation/team_change_metrics.py) | Matches this doc |
| CLI over existing runs, writes `team_change_metrics.json` per run | [`dashboard/analysis/analyze_team_changes.py`](../../dashboard/analysis/analyze_team_changes.py) | Matches this doc |
| Dashboard table and charts (including per case) | [`dashboard/web/src/pages/MetricsPage.tsx`](../../dashboard/web/src/pages/MetricsPage.tsx) | Matches this doc |
| Tests | [`tests/test_team_change_metrics.py`](../../tests/test_team_change_metrics.py) | Cover the definitions above on a made-up run (join with specialist and running-task cases, then a leave) |

Run: `uv run python dashboard/analysis/analyze_team_changes.py --workflow <name> --mode cot random`.

**Scenario contract.** A scenario opts in under `examples/end_to_end_examples_team/<workflow>/`:

- `team_change_spec.py` with `create_team_change_spec() -> TeamChangeSpec`: the events (timestep,
  `add`/`remove`, agent id) with their **affected tasks fixed by name**, plus the optional
  `correct_agents` mapping (scorer-only, diagnostics only; the authoring check requires it, the
  headline metrics ignore it), plus `cases`: the **case** of each join-affected task
  (`specialist` or `running_task`) so results can be reported per case. Affected tasks of a leave
  are reported as `leave`. The control set is every task no event affects, so it needs no entry.
- `workflow.py` with `create_workflow()`, whose affected tasks carry `requirements` where every
  item has a `pattern`.

**Timing convention.** A roster change at timestep `t` is applied at the start of `t`, then the
manager acts, then the snapshot for `t` is written. So the state *before* an event is the last
snapshot before `t`, and the manager's response is read from snapshots from `t` up to (not
including) the next event.

**Definitions**

- A control task counts toward the disruption denominator only if it had an assigned agent and was
  not yet finished at the event, since a finished task can no longer be moved.
- Unfinished affected tasks score 0, and so does an affected task the manager removed or renamed.
  A task name that appears in no snapshot is a typo in the spec and raises an error.
- Run-level numbers pool the events: `disruption_cost` is total moved control tasks over total
  assigned control tasks, and `post_change_score` is the mean of the per-event scores.

## Comparison protocol

- Managers: `cot`, `random`, and the naive "reassign all tasks to new workers" baseline
  (**not** `assign_all`).
- Same predefined schedule and same worker prompts for every manager, so differences come from the
  manager only.
- `random` gives a floor: if gated tasks are rarely passed under `random`, the gates discriminate.
- The naive baseline should score a high disruption cost, since it moves control tasks too.
- Run multiple seeds per manager; report mean and spread per metric.

## Open questions

- Are metrics aggregated per event or per run? (Suggest both: per-event for diagnosis, per-run
  for the headline number.)
- Timing: should the post-change score reward speed of routing (steps between the event and the
  affected task going to a worker that passes its gate), or only the final checklist outcome?
- Does the existing workflow-level scoring (quality / speed / cost) stay as a secondary report,
  or is this benchmark's score standalone?
- Should results be broken down per case (specialist, running task), given the case rotates across
  workflows?
