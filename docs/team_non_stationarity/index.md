# Team-Membership Non-Stationarity (Auto Scaling Use Case)

Focus area: how well an LLM manager agent **delegates tasks when the set of available workers
changes mid-workflow** (open ad hoc teamwork, applied to a manager rather than a teammate).

This folder is split so the benchmark and the metrics can be worked on independently:

| Doc | Covers | Status |
|---|---|---|
| [`benchmark.md`](benchmark.md) | Scenario design: private worker content, gated tasks, join/leave events, controls, replayable schedule, gate validation | Draft |
| [`metrics.md`](metrics.md) | Post-change score, disruption cost, the hidden task→worker mapping, baselines | Draft |
| [`known_bugs.md`](known_bugs.md) | Upstream MA-Gym bugs that affect this work, with a progress checklist | Tracking |

## Use case

An **external auto scaler** adds and removes worker agents during a workflow. The manager is told
about each roster change and must delegate accordingly.

- Mirrors how worker agents already join in MA-Gym's existing workflows
  (`AgentRegistry.schedule_agent_add` / `schedule_agent_remove`, driven by each scenario's
  `team_timeline`).
- Why a *separate* auto scaler: roles stay separated. The scaler owns roster changes, the manager
  owns delegation, and no single agent orchestrates everything at once.

## Scope

- Worker agents and their capabilities are **known** (declared profile visible to the manager).
- The manager **is told** about roster changes (join and leave events appear in its observation).
- Workers can **leave abruptly**, so any task in progress on a departing worker needs reassignment.
- A task already assigned to an agent that stays does **not** need reassignment.
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
| Leave mid-task | Forbidden (rules 1-2: leave only after bundle done) | **Required**: abrupt leave with in-progress work |
| Reassignment | Out of scope (no failover) | **Core behavior under test** |
| Ground-truth mapping | "No-label correction": no stored task→agent label | Hidden task→worker mapping, used **only for scoring**, never shown to the manager |
| What differentiates workers | Trait tuple `(model, version, tier)` | Private prompt content on one shared base model |

The hidden mapping is compatible with the no-label principle at runtime (the manager never sees
it), but it does reverse the "no stored ground truth" stance for the *scorer*. Worth deciding
explicitly whether the two benchmark families coexist or this one supersedes the other.

## Benchmarked managers

Compare against the existing managers: `cot` and `random` (see
`manager_agent_gym/core/manager_agent/factory.py`). **`assign_all` is excluded** as a baseline:
assigning everything to everyone would sidestep the delegation decision this benchmark measures.

## Open questions (cross-cutting)

- What does the engine do today when a worker is removed with a task in flight?
  `AgentRegistry.remove_agent` only deletes the agent from the registry; the in-progress task's
  fate (stays `RUNNING`, fails, returns to `PENDING`) needs checking in
  `core/execution/engine.py` before the leave-event design is final.
- Does the manager get an explicit "task orphaned" signal on leave, or only the roster change?
- Does the manager have a way to reassign an already-assigned task (`assign_task` on a task with
  an existing `assigned_agent_id`)? Disruption cost depends on this being observable.
