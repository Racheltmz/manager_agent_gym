# Metrics

Part of [`index.md`](index.md). Scenario construction is in [`benchmark.md`](benchmark.md).

**Principle:** task requirements are evaluated **deterministically at each step**, so we can
quantify how well the manager actually performed without an LLM judge.

## Hidden task-to-worker mapping

An invisible mapping from each task to the worker(s) that should be assigned to it.

- Needed to tell whether the manager assigned the *right* agent, and to measure performance
  after a change.
- **Scorer-only.** Never exposed to the manager (it sees only task descriptions and public
  `agent_capabilities`).
- Derived from gate validation (`task × worker → pass/fail`, see
  [`benchmark.md`](benchmark.md#5-gate-validation-if-feasible)), so it is verified, not asserted.
- For control tasks, the mapping is simply "whichever worker currently holds it; no change needed".

## Affected tasks

After each join or leave event, the **affected tasks are fixed in advance** (in the scenario spec),
not computed from the run:

- Join event → tasks gated on the new worker.
- Leave event → the departing worker's in-progress task(s).

## Metric 1: Post-change score

Mean deterministic checklist score over the affected tasks, after the event.

```
task_score(t)      = items_passed(t) / total_items(t)
post_change_score  = mean over t in affected(event) of task_score(t)
```

- Computed per event, then averaged per scenario/run.
- **Compare against general workflow performance**: mean `task_score` over all non-affected tasks
  (controls) in the same run. The gap (`post_change_score - baseline_score`) shows how much the
  roster change specifically hurt or helped.
- Unfinished or never-assigned affected tasks score `0` (not excluded), otherwise dropping a task
  would be free.

## Metric 2: Disruption cost

```
disruption_cost = tasks_reassigned / tasks_already_assigned
```

- `tasks_already_assigned`: tasks that had an agent assigned at the time of the event.
- `tasks_reassigned`: of those, tasks the manager moved to a different agent afterwards.
- Spec rule: a task already assigned to an agent that stays needs no reassignment, so
  reassigning such a task is pure disruption.

Refinement to decide (leave events make some reassignment **necessary**): a raw ratio penalizes the
manager for correctly reassigning a departed worker's task. Options:

| Variant | Numerator | Reading |
|---|---|---|
| Raw (as specified) | All reassignments | Simple, but a perfect manager scores > 0 on leave events |
| **Unnecessary** (suggested) | Reassignments of tasks whose worker did *not* leave | Should be 0 for a good manager |
| Necessary coverage | Departed-worker tasks that *were* reassigned / departed-worker tasks | Complements Metric 1; catches dropped tasks |

Suggest reporting raw (to match the spec) plus the split into unnecessary / necessary.

## Reading the two together

| Post-change score | Disruption cost | Interpretation |
|---|---|---|
| High | Low | Delegated correctly and left other work alone |
| High | High | Fixed affected tasks, but churned unaffected ones (thrashing) |
| Low | Low | Ignored the roster change (e.g. never used the new worker, dropped the orphaned task) |
| Low | High | Reassigned a lot, to the wrong workers |

## Implementation

Computed post hoc from the per-timestep snapshots a run already writes
(`workflow_outputs/workflow_execution_<run_id>_t<NNNN>.json`), so there is no engine change and no
LLM call. Running it only reads existing files.

| Piece | Where |
|---|---|
| Per-task checklist score (items passed / total) | [`task_requirements_evaluator.py`](../../manager_agent_gym/core/evaluation/task_requirements_evaluator.py) |
| Post-change score, baseline, disruption cost | [`team_change_metrics.py`](../../manager_agent_gym/core/evaluation/team_change_metrics.py) |
| CLI over existing runs, writes `team_change_metrics.json` per run | [`dashboard/analysis/analyze_team_changes.py`](../../dashboard/analysis/analyze_team_changes.py) |
| Dashboard table | [`dashboard/web/src/pages/MetricsPage.tsx`](../../dashboard/web/src/pages/MetricsPage.tsx) |
| Tests | [`tests/test_team_change_metrics.py`](../../tests/test_team_change_metrics.py) |

Run: `uv run python dashboard/analysis/analyze_team_changes.py --workflow <name> --mode cot random`.

**Scenario contract.** A scenario opts in under `examples/end_to_end_examples_team/<workflow>/`:

- `team_change_spec.py` with `create_team_change_spec() -> TeamChangeSpec`: the events (timestep,
  `add`/`remove`, agent id) with their **affected tasks fixed by name**, plus the optional hidden
  `correct_agents` mapping (scorer-only).
- `workflow.py` with `create_workflow()`, whose affected tasks carry `requirements` where every
  item has a `pattern`.

**Timing convention.** A roster change at timestep `t` is applied at the start of `t`, then the
manager acts, then the snapshot for `t` is written. So the state *before* an event is the last
snapshot before `t`, and the manager's response is read from snapshots from `t` up to (not
including) the next event.

**Definitions as implemented**

- `already_assigned`: tasks with an assigned agent that were not completed or failed before the
  event. Finished tasks can't be reassigned, so they are excluded from the denominator.
- A reassignment is **necessary** if the holder left, or the hidden mapping says the holder was
  never a correct worker for that task. Otherwise it is **unnecessary**.
- Unfinished affected tasks score 0. Control tasks without a pattern-based checklist are left out
  of the baseline.
- Run-level numbers pool the events: `disruption_cost` is total reassigned over total
  already-assigned, and `post_change_score` is the mean of the per-event scores.

## Comparison protocol

- Managers: `cot`, `random` (**not** `assign_all`).
- Same predefined schedule and same worker prompts for every manager, so differences come from the
  manager only.
- `random` gives a floor: if gated tasks are rarely passed under `random`, the gates discriminate.
- Run multiple seeds per manager; report mean and spread per metric.

## Open questions

- Are metrics aggregated per event or per run? (Suggest both: per-event for diagnosis, per-run
  for the headline number.)
- Timing: should the post-change score reward speed of reassignment (steps between event and
  correct reassignment), or only the final checklist outcome?
- Does the existing workflow-level scoring (quality / speed / cost) stay as a secondary report,
  or is this benchmark's score standalone?
