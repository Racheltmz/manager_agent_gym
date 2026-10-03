# Team-Membership Non-Stationarity (Auto Scaling Use Case)

Focus area: how well an LLM manager agent **delegates tasks when the set of available workers
changes mid-workflow** (open ad hoc teamwork, applied to a manager rather than a teammate).

**Why team-membership:** it isolates handling a dynamic team size while the team members and their
capabilities stay known, which is the situation an auto scaler creates.

This folder is split so the benchmark and the metrics can be worked on independently:

| Doc | Covers | Status |
|---|---|---|
| [`benchmark.md`](benchmark.md) | Scenario design: private worker content, gated tasks, change-affected cases, join/leave events, controls, replayable schedule, gate validation | Draft |
| [`metrics.md`](metrics.md) | Post-change score, disruption cost, the hidden task→worker mapping, baselines | Draft |
| [`known_bugs.md`](known_bugs.md) | Upstream MA-Gym bugs that affect this work, with a progress checklist | Tracking |

## Use case

An **external auto scaler** adds and removes worker agents during a workflow. The manager is told
about each roster change and must delegate accordingly.

- Mirrors how worker agents already join in MA-Gym's existing workflows
  (`AgentRegistry.schedule_agent_add` / `schedule_agent_remove`, driven by each scenario's
  `team_timeline`).
- Separation of roles: the scaler owns roster changes and the manager owns delegation, so no single
  agent orchestrates everything at once.

## Scope

- Every worker and its capabilities are **declared and accurate**: the profile the manager sees is
  true, and is enough to tell which worker suits a task.
- The manager **is informed** of every roster change, join or leave, before its next assignment
  decision.
- The team changes **only in ways the manager can respond to**. A worker is **never removed while it
  is mid-task**: a worker that has been assigned a task finishes it before leaving, so a leave never
  requires reassigning assigned work.
- **Task decomposition:** when a change makes the existing plan a poor fit for the new roster, the
  manager should edit the task graph if necessary.
- **Reassignment happens only when the manager deems it necessary.**
- **Task failures are out of scope for now.**
- AI agents only (no `HumanAgentConfig`).
- Workers share **one base model** (for now) and are differentiated only by their prompt.

## Research gap

No existing benchmark evaluates LLM manager agents on delegation under team-membership
non-stationarity, and no existing manager agent is designed to handle it.

## Existing work

Open AHT (e.g. GPL) studies changing team composition, but for RL agents acting as *teammates*, not
a manager delegating tasks across a changing set of workers, and mostly in game settings rather
than reasoning tasks.

## How this differs from the earlier AHT design

The earlier AHT docs (removed from the working tree; see commit `aec04bb`) targeted **cold-start
capability inference** under a demand-driven roster. This focus differs, so some of those design
rules are deliberately *not* carried over:

| | Earlier AHT design | This folder |
|---|---|---|
| Who triggers churn | Task-graph demand (specialty needed / exhausted) | External auto scaler, predefined schedule |
| Leave mid-task | Forbidden (leave only after the bundle is done) | Also forbidden: an assigned worker finishes its task before leaving |
| What a leave tests | Frees a specialty that is no longer needed | Removes a capability, so unassigned gated work must go to a worker that remains |
| What a join tests | Cold-start capability inference | Whether the manager uses the new worker where it is better, including handing over a running task |
| Task graph | Fixed | The manager may edit it when the roster makes the plan a poor fit |
| Ground-truth mapping | "No-label correction": no stored task→agent label | Hidden task→worker mapping, used **only for scoring**, never shown to the manager |
| What differentiates workers | Trait tuple `(model, version, tier)` | Private prompt content on one shared base model |

The hidden mapping is compatible with the no-label principle at runtime (the manager never sees
it), but it does reverse the "no stored ground truth" stance for the *scorer*. Worth deciding
explicitly whether the two benchmark families coexist or this one supersedes the other.

## Benchmarked managers

- The existing managers `cot` and `random` (see `manager_agent_gym/core/manager_agent/factory.py`).
  **`assign_all` is excluded**: assigning everything to everyone sidesteps the delegation decision.
- A **naive baseline**: reassign all tasks to the new workers, without asking whether a task is
  better handled by another worker or at a different granularity. It does not exist yet.

## Out of scope for now

- Task failures.
- Resuming a handed-over running task from partial progress (a handed-over task restarts fresh).
- The split/merge case (a new worker suits a different task granularity), kept in view until a
  prompt-based granularity limit is shown to be reliable.
- Cost in time and resources (a metric to add later).

## Open questions (cross-cutting)

- Scenario authoring has to guarantee the leave rule: for every scheduled leave, check against task
  durations and the dependency graph that every task assigned to the worker is finished by then.
  This also avoids the engine silently never starting a task assigned to a missing agent (see
  [`known_bugs.md`](known_bugs.md)).
- When the manager hands a running task to another worker, who cancels the current run and
  restarts it? Today `assign_task` only overwrites `assigned_agent_id` (see [`known_bugs.md`](known_bugs.md)).
- Does the manager have a way to see that a reassignment happened? Disruption cost depends on it
  being observable.
