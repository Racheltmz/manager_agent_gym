# Known MA-Gym bugs that affect this implementation

Part of [`index.md`](index.md). A tracker, not a spec: tick items off and add notes as you go.

**Source:** `magym-undocumented-behaviour.xlsx` (Drive file shared by ziyuan@ieee.org, 2026-09-12),
"Critical and High bugs MA-Gym". It lists 46 bugs (IDs `ML-001` to `ML-092`, `NEW-001`). This doc
keeps the ones that touch the team-membership non-stationarity benchmark and metrics, and lists
the rest under [Not affecting this work](#not-affecting-this-work) so you can disagree.

**Last checked against the working tree:** 2026-10-02. "Verified" below means I read the code in
this repo. "Per sheet" means the claim comes from the spreadsheet's measurements and I did not
reproduce it. Re-verify before relying on a claim.

## How the bugs reach us

What this implementation depends on:

1. **Snapshots**: metrics are computed post hoc from `workflow_execution_<run_id>_t<NNNN>.json`.
2. **`assigned_agent_id` per task per timestep**: disruption cost is read from changes in it.
3. **Task status and output text**: the checklist score only counts `completed` tasks, and
   regex-matches their output resources.
4. **Manager routing work** after a join or leave (and reassigning it, if it chooses to), within the timestep budget.
5. **Seeds**: the comparison protocol runs several seeds per manager.

It does **not** depend on the LLM judge, stakeholder preferences, or artifact handoff between
tasks (gated tasks pass on worker-private prompt content). That is why most of the sheet does not
apply.

## Status key

- **Impact**: Blocker (results are wrong or uninterpretable), High (distorts a metric or
  comparison), Medium (confound or design constraint), Low (watch only).
- **Status**: `Open`, `Mitigated` (worked around, say how in Notes), `Fixed`, `Accepted` (known
  limitation, report it), `Re-verify`.

## Summary

| ✓ | ID | Bug | Impact | Hits | Verified | Status |
|---|---|---|---|---|---|---|
| [x] | ML-052 | `AssignTaskAction` succeeds as a no-op on RUNNING / COMPLETED / unready tasks | Blocker | Disruption cost, `assigned_correctly` | Verified | Fixed (team runs) |
| [ ] | ML-005 | Fabricated default resource counted as success | Blocker | Checklist false passes | Verified (content unchecked) | Open |
| [x] | ML-050 | Cost lookup inside the success path discards completed work | Blocker | Phantom FAILED, score 0 | Verified | Fixed |
| [ ] | ML-051 | FAILED is absorbing; no retry | High | Downstream tasks starve | Verified | Open |
| [ ] | ML-049 | One manager action per timestep; budget runs out | High | Affected tasks unfinished, score 0 | Per sheet | Open |
| [ ] | ML-092 | Seed never reaches the Agents SDK; runs are not reproducible | High | Multi-seed comparison | Per sheet | Open |
| [x] | ML-053 | Engine rejection never reaches the manager | High | Manager cannot learn it failed | Verified | Fixed for `cot` (team runs) |
| [ ] | ML-003 | COMPLETED = "call returned without raising" | High | Completion-based reporting | Verified | Accepted |
| [ ] | ML-015 | Phantom completions, no agent / no start | Medium | Baseline and affected tasks | Per sheet | Open |
| [ ] | ML-075 | Read-tracking never called; stakeholder reply loop | Medium | Manager wastes timesteps | Verified (no callers) | Open |
| [x] | ML-008 | Decomposition rewrites the task graph | Medium | Name-keyed affected tasks | Per sheet | Mitigated (scoring rolls up subtasks; renamed tasks still score 0) |
| [ ] | ML-072 | `enable_timestep_logging` defaults off | Medium | Snapshots are the metric input | Re-verify | Re-verify |
| [ ] | ML-002 / ML-001 / ML-006 | No artifact handoff; scenarios have no resource wiring; 200-char input truncation | Medium | Scenario design | Verified | Accepted |
| [ ] | ML-090 | Agents SDK tracing sends the API token to api.openai.com | Medium | Every run | Verified (no disable) | Open |
| [ ] | ML-070 / ML-073 | State restorer is lossy; only a 10-message window kept | Low | Replaying archived runs | Per sheet | Open |
| [ ] | ML-014 | Summary counters disagree with per-task status | Low | Any report using counters | Per sheet | Open |
| [ ] | ML-013 / ML-045 | No messages persisted; judge records leak into the action stream | Low | Communication or action-stream analysis | Per sheet | Open |

## Details

### ML-052: assign silently succeeds on un-executable tasks (Blocker)

**Sheet:** assign validates only that the task and agent ids exist, sets `assigned_agent_id`, and
returns `success=True`, including for composite parents, tasks with unmet dependencies, and
RUNNING / FAILED / COMPLETED tasks.

**Verified:** [`manager_actions.py:113-175`](../../manager_agent_gym/schemas/execution/manager_actions.py)
has no status check.

**How it hits us:**
- **Running-task case:** handing a RUNNING task to the new worker is the intended best action, but
  assign only overwrites `assigned_agent_id`. The old worker's coroutine is never cancelled, so it
  still finishes the task. The snapshot then shows the new worker while the output came from the old
  one, so the gated checklist fails and `final_agent` / `assigned_correctly` are wrong, and the
  manager is penalised for doing the right thing.
- Disruption cost counts changes in `assigned_agent_id` on control tasks, so an assign on a control
  task that is already RUNNING or COMPLETED registers as a "move" that changed nothing.
- A reassign after completion rewrites `final_agent` on a finished task.

**Options:** (a) fix the engine: assigning a RUNNING task cancels the current run and restarts the
task fresh with the new worker (resuming from partial progress is out of scope), and assign
rejects COMPLETED / FAILED tasks; (b) metrics only: count a control-task move only when the task
was not finished at the time. (b) alone cannot fix the running-task case, because the output
provenance is wrong.

- [x] Decide (a) or (b): (a), built for team runs only (`Workflow.strict_assignment`, engine
  `restart_on_reassign`; the original benchmark keeps the legacy behaviour). A RUNNING task handed
  to another worker is cancelled and restarted fresh (output of the cancelled run dropped,
  `restart_count` recorded); COMPLETED, FAILED and composite assigns are rejected with a cause;
  reassigning to the same worker is a no-op. Unready PENDING tasks can still be pre-assigned, which
  is legitimate.
- [x] Regression tests: `tests/test_assign_restart.py` and
  `tests/integration/test_engine_restart_on_reassign.py`. Because a rejected assign leaves
  `assigned_agent_id` unchanged, no false control-task move is recorded, so the metrics needed no
  change.
- Notes: a restart on a running control task still counts as a move, correctly: it changed worker
  and cost a rerun.

### ML-005: fabricated default resource (Blocker)

**Sheet:** any well-formed worker output is recorded as success, and a default resource is
fabricated when the worker returns none.

**Verified:** [`ai_agent.py:140-150`](../../manager_agent_gym/core/workflow_agents/ai_agent.py)
creates `Resource(content=str(result))` when `output.resources` is empty.

**How it hits us:** the checklist regex runs on `task_output_text`, which concatenates resource
`content`. A fabricated resource holds `str(RunResult)`, not a real deliverable. If that string
includes the task description or the agent instructions (not yet checked), a pattern can pass
without the worker doing the work, which weakens the gate. A refusal fails the regex, which is
fine.

- [ ] Check what `str(result)` actually contains for a run, and whether any pattern could match it
- [ ] Either score fabricated resources as 0 (flag them by name prefix `Completed:`) or make the
  engine fail the task instead
- Notes:

### ML-050: cost lookup inside the success path (Blocker)

**Sheet:** `cost=self._calculate_accurate_cost(result)` is evaluated while building the success
result. LiteLLM raises on routed or unknown model ids, the catch-all returns `success=False` with
no resources, and finished work is thrown away.

**Verified:** still present at [`ai_agent.py:161`](../../manager_agent_gym/core/workflow_agents/ai_agent.py)
and `_calculate_accurate_cost` has no guard.

**How it hits us:** task failures are out of scope as a designed event, so a FAILED task here is a
bug, not a result. A phantom FAILED on an affected task scores 0 and, through ML-051, blocks its
dependents. That looks exactly like the manager mishandling a roster change. The trigger is model
ids LiteLLM cannot price, so it depends on which model the workers use.

- [x] Wrap the cost lookup so a pricing failure yields `cost=0.0`, not a failure (`AIAgent._calculate_accurate_cost`, test in `tests/test_ai_agent_cost.py`)
- [x] Confirm the model id used by the scenario workers is priceable (`gpt-5-mini` and `gpt-5.4-mini` are priced by LiteLLM; checked offline)
- Notes:

### ML-051: FAILED is absorbing (High)

**Verified:** `Task.is_ready_to_start` is `all(dep in completed_task_ids)`, and only COMPLETED
tasks enter that set ([`tasks.py:174-176`](../../manager_agent_gym/schemas/core/tasks.py)). One
failure strands its whole subtree (about 3.2 blocked tasks per failure, per sheet).

**How it hits us:** a genuine failure on a control task depresses the baseline, and on an affected
task it zeroes both its score and its dependents'. Compare managers only when failure counts are
reported alongside the metrics.

- [ ] Report failed-task count per run next to the metrics
- [ ] Decide whether the scenario should be built so no task can strand an affected one
- Notes:

### ML-049: one action per timestep (High)

**Sheet:** the manager takes one action per timestep while the workflow grows, so 45 of 52 cells
exhausted the 100-timestep budget.

**How it hits us:** unfinished affected tasks score 0 by design, so a manager that runs out of
timesteps looks the same as one that ignored the roster change. A leave event late in the run has
little time left for the manager to route its gated task.

- [ ] Pick `max_timesteps` so a competent manager can finish; place events early enough to leave
  recovery time
- [ ] Record timesteps used vs available per run
- Notes:

### ML-092: seed is not honoured (High)

**Sheet:** the seed is passed unconditionally, never reaches the Agents SDK, and is dropped on the
codex lane. Identical-seed runs diverged widely.

**How it hits us:** [`metrics.md`](metrics.md#comparison-protocol) says to run multiple seeds per
manager and report spread. If seeds are not honoured they are independent draws, so the spread is
not controlled and `random` is not reproducible. The roster schedule itself is deterministic.

- [ ] Treat runs as independent samples and say so in the write-up
- [ ] Give `random` its own seeded `random.Random` so the baseline is reproducible
- Notes:

### ML-053: rejection feedback never reaches the manager (High)

**Verified:** the failure paths in `AssignTaskAction.execute` return `ActionResult(success=False)`
without setting `self.success` / `self.result_summary`.

**How it hits us:** after a roster change the manager can repeat a rejected assign every step with
no signal. This matters for the planned roster-change observation: telling the manager about
events does not help if its follow-up actions fail silently.

- [x] Surface the engine verdict in the manager's next observation: the `cot` history now shows
  `[FAILED]` and the cause (team runs only); causes are short, and bulk assigns that skip entries
  say why
- [x] Assigns that did nothing but report success (ML-052) are now rejected or reported as no-ops
  in team runs, so they show as `[FAILED]` with a cause
- [ ] Not changed: the `random` manager has no history in its prompt by design
- Notes: the sheet's claim needs a correction. The failure branches do return `success=False` and a
  summary, and the history stored them; what was missing was showing the flag, and the summary was
  a long id dump cut at 120 characters.

### ML-003: COMPLETED means the call returned (High)

**Verified:** [`engine.py:646-663`](../../manager_agent_gym/core/execution/engine.py) marks a task
COMPLETED on `result.success` alone ("Validation system removed").

**How it hits us:** much less than the other benchmarks, because our score is the checklist, not
the status. Remaining risk: `post_change_score` treats `completed` as the gate, so report
"completed" and "passed checklist" separately and never quote a completion rate as a result.

- [ ] Report completion rate and checklist score as separate numbers
- Notes:

### ML-015: phantom auto-completion (Medium)

**Sheet:** tasks COMPLETED with no agent, no start, and no artifacts. Also, repeated
`RemoveTaskAction` on failures.

**How it hits us:** a phantom completion has no output text, so it scores 0 in the metrics code
(`completed and text`). Lookup is by name, so a manager that removes or renames an affected task
used to make `compute_team_change_metrics` raise `KeyError`. It now scores 0, and only a name that
appears in no snapshot (a spec typo) raises.

- [x] Decide what a removed or renamed affected task should score (0, not an exception; tested in
  [`tests/test_team_change_metrics.py`](../../tests/test_team_change_metrics.py))
- Notes:

### ML-075: read tracking never invoked (Medium)

**Verified:** `mark_message_read` and `Message.mark_read_by` have no callers outside their
definitions.

**How it hits us:** the stakeholder repeats replies and the manager can burn timesteps on one
question (sheet: 44 of 50). Those timesteps are not spent responding to a roster change. Worse
once join/leave notices are added as messages.

- [ ] Deliver roster changes as an observation field, not a message, as already planned
- Notes:

### ML-008: decomposition rewrites the task graph (Medium)

**Sheet:** composite tasks are expanded into leaf subtasks.

**How it hits us:** the metrics key affected and control tasks by **name**. If the manager
decomposes or renames them, names stop matching. Keep affected tasks atomic in the scenario, or
match by a stable id.

- [ ] Make affected tasks atomic, or add an id-based match
- Notes: seen in the first real run (`cot`, seed 42): the manager decomposed Negotiation & Redlines
  (affected) and Financial Diligence – QoE & Working Capital (a control) into five subtasks each,
  using the decompose action its default prompt recommends. Their checklists stayed on the
  parents, which have no output of their own, so Negotiation scored 0 and the baseline was pulled
  down. Decomposition is allowed and not forced. Fixed in the scoring: a decomposed task's checklist
  is now run on the combined output of its leaf subtasks (`team_change_metrics.py`, tests in
  `tests/test_team_change_metrics.py`). Rescoring the same run gave Negotiation 0.25 (it was 0,
  the format items fail because the format holder was never assigned) and the baseline 1.0 (it was
  0.833).

### ML-072: timestep logging default (Medium)

**Sheet:** `enable_timestep_logging` defaults off. **In this tree** the engine signature has
`enable_timestep_logging: bool = True` ([`engine.py:112`](../../manager_agent_gym/core/execution/engine.py)),
so it looks fixed here. The metrics need these snapshots.

- [ ] Confirm that `run.sh` / `run_examples.py` do not turn it off
- Notes:

### ML-002 / ML-001 / ML-006: no artifact handoff (Medium, design constraint)

**Verified:** `input_resource_ids` has no writer in the package, so workers never see a
predecessor's output, and where inputs are wired, `AIAgent._format_resources` truncates each to 200
characters.

**How it hits us:** the gated-task design does not need handoff (the gate is the worker's private
prompt). But it means a scenario cannot make one task depend on another's artifact, and any
checklist item that assumes the worker saw a predecessor's output would fail for the wrong reason.
Converting `legal_m_and_a` inherits this.

- [ ] State in `benchmark.md` that dependencies are precedence-only
- [ ] Keep every checklist item independent of upstream content
- Notes:

### ML-090: tracing sends the API token to api.openai.com (Medium)

**Verified:** no `tracing_disabled` / `set_tracing_disabled` anywhere in the package.

**How it hits us:** a security and cost-hygiene issue on every manager run. Gate validation is not affected, since it calls Claude and not the Agents SDK.

- [ ] Disable Agents SDK tracing before running anything against the API
- Notes:

### Low impact (watch only)

- **ML-070 / ML-073**: the restorer drops manager-created tasks and keeps only 10 messages. Our
  metrics read snapshots directly, so only replaying a run is affected.
- **ML-014**: summary counters disagree with per-task status. Our code reads per-task status, which
  is the safe side. Do not quote the counters.
- **ML-013 / ML-045**: messages are not persisted and judge records inflate the action stream. We
  read neither.

## Not affecting this work

These sit in the LLM judge, stakeholder preference, or handoff-quality paths that this benchmark's
deterministic checklist score does not use. They would start to matter only if the workflow-level
quality score is kept as a secondary report (open question in [`metrics.md`](metrics.md#open-questions)).

| ID | Bug | Why not affecting |
|---|---|---|
| ML-007 | Judge sees a 300-char preview | LLM judge not used |
| ML-009 | ~100% completion vs 42-66% inadequate handoffs | Handoff quality is not measured |
| ML-010 | Wiring artifacts recovers 0.0pp | Handoff scoping result |
| ML-011 | Tasks COMPLETED while the worker says it did not execute | Caught by the checklist regex |
| ML-004 | Readiness ignores acceptance criteria | Scheduling by quality not used |
| ML-012 | `quality_score` never populated | Field not used |
| ML-016 / ML-017 | Aggregation callables unreachable; `zeroing_gate` crash | Judge aggregation |
| ML-019 / ML-020 | Errored rubrics scored 0; `llm_model` dropped | Judge |
| ML-023 | Rubrics never receive `required_context` | Judge |
| ML-025 / ML-026 | Cadence hardcoded; `run_condition` bypass | Judge cadence |
| ML-030 | Name-keyed `rule_*` rubrics zero out on restructure | Preference rubrics (but see ML-008: our metrics are name-keyed too) |
| ML-031 / ML-032 / ML-033 / ML-034 | Rubric scoring defects | Judge or constraint scoring |
| ML-036 | Judge sampling uncontrolled | Judge |
| ML-047 | Judge scored against the wrong stakeholder weight stage | Preferences |
| ML-082 / ML-084 / NEW-001 | Stakeholder private preference copy, templated dialogue, weights mutated in place | Stakeholder preferences |

## Found while checking (not in the sheet)

- [x] **`UPDATES.md` row for `diagnostics/analyze_team_changes.py` pointed at a file that was not
  on disk.** `diagnostics/` was removed on purpose. The analysis scripts now live in
  `dashboard/analysis/` (`analyze_runs.py`, `analyze_team_changes.py`), and `UPDATES.md`, the
  metrics doc and the scripts point there.
- [ ] **A scheduled `remove` leaves a READY task assigned to a missing agent.** In
  `_execute_ready_tasks` the agent lookup returns `None`, so the task is silently never started
  and stays assigned to the departed id. The scope has a worker leave only after every task assigned to it
  is finished, so a valid scenario never hits this. Scenario authoring has to enforce that (see
  `UPDATES.md`); the engine itself does not.
- [ ] **`examples/end_to_end_examples_team/` is empty**, so none of the above has run against a
  real scenario yet. Re-check the "Verified" column once a scenario runs.
