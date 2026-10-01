# Updates made for team-membership non-stationarity

Changes relative to the original MA-Gym code, grouped by component. Docs live in
[`docs/team_non_stationarity/`](docs/team_non_stationarity/index.md). Status is **Done**
(in the working tree) or **Planned** (decided, not built).

## Manager agent

| Update | Files | Purpose | Status |
|---|---|---|---|
| Baselines are `cot` and `random`; `assign_all` excluded; `cot_aware` removed from mode lists and comments | [`scripts/run.sh`](scripts/run.sh), [`scripts/eval.sh`](scripts/eval.sh), [`docs/team_non_stationarity/index.md`](docs/team_non_stationarity/index.md) | `cot_aware` is not a manager the factory supports, and `assign_all` sidesteps the delegation decision being measured | Done |
| Tell the manager about join/leave events (roster-change field in the observation and prompt) | `manager_agent_gym/schemas/execution/manager.py`, `core/manager_agent/*`, `core/execution/engine.py` | Scope requires the manager to be told about roster changes. An earlier version was reverted in `f55bd5e`. | Planned |
| Tracker of upstream MA-Gym bugs that affect manager runs (ML-052 assign no-op, ML-053 rejection feedback, ML-049 one action per timestep) | [`docs/team_non_stationarity/known_bugs.md`](docs/team_non_stationarity/known_bugs.md) | Tracks which of the shared bug list change what the manager can do or learn. Items are open. | Done |
| Make a leave interrupt the departing worker's in-flight task | `manager_agent_gym/core/execution/engine.py` | Checked: removing an agent only deletes it from the registry and workflow. Its running asyncio task is never cancelled, so it still completes. An abrupt leave needs the engine to cancel the task and return it to the manager. | Planned |

## Benchmark

| Update | Files | Purpose | Status |
|---|---|---|---|
| Benchmark design doc: private worker content, gated tasks, join/leave events, control tasks, replayable schedule, gate validation | [`docs/team_non_stationarity/benchmark.md`](docs/team_non_stationarity/benchmark.md) | Specifies how scenarios force the manager to use new workers and recover from departures | Done |
| Tracker of upstream MA-Gym bugs that constrain scenario design (ML-001/002/006 no handoff, ML-008 decomposition, ML-050/051 phantom failures) | [`docs/team_non_stationarity/known_bugs.md`](docs/team_non_stationarity/known_bugs.md) | Records what scenarios must avoid so failures are not mistaken for manager errors | Done |
| Overview, scope, research gap, and differences from the earlier AHT design | [`docs/team_non_stationarity/index.md`](docs/team_non_stationarity/index.md) | Shared context for the benchmark and metrics docs | Done |
| `TaskRequirement` gains a regex `pattern`, `case_sensitive`, and `passes()`; `Task` checklist fields documented for this benchmark | [`manager_agent_gym/schemas/core/tasks.py`](manager_agent_gym/schemas/core/tasks.py) | Makes each checklist item exactly and deterministically checkable | Done |
| Removed `model_version` / `capability_tier` from `AgentConfig`; the old `trait_pool.py` helper that used them is gone with the removed AHT examples | [`manager_agent_gym/schemas/workflow_agents/config.py`](manager_agent_gym/schemas/workflow_agents/config.py) | Workers share one base model and differ by prompt, not by trait tuple | Done |
| Add worker-private prompt content, gated tasks, control tasks, and a mid-task leave to a scenario | `examples/end_to_end_examples_team/legal_m_and_a/` | Builds the first runnable scenario | Planned |
| Gate validation (every non-matching worker fails the gated checklist) | scenario spec | Verifies the gates, and yields the hidden task-to-worker mapping. Calls the OpenAI API, so it needs an explicit ask. | Planned |

## Metric

| Update | Files | Purpose | Status |
|---|---|---|---|
| Metric definitions: post-change score, disruption cost, hidden task-to-worker mapping, comparison protocol | [`docs/team_non_stationarity/metrics.md`](docs/team_non_stationarity/metrics.md) | Specifies how manager performance is quantified | Done |
| Tracker of upstream MA-Gym bugs that distort the metrics (ML-052, ML-005, ML-050, ML-092) | [`docs/team_non_stationarity/known_bugs.md`](docs/team_non_stationarity/known_bugs.md) | Shows which numbers cannot be trusted until a bug is fixed or worked around | Done |
| Requirements evaluator (items passed / total per task) | [`manager_agent_gym/core/evaluation/task_requirements_evaluator.py`](manager_agent_gym/core/evaluation/task_requirements_evaluator.py) | Computes the deterministic per-task checklist score | Done |
| Post-change score, baseline, disruption cost (raw, necessary vs unnecessary), computed from per-timestep snapshots | [`manager_agent_gym/core/evaluation/team_change_metrics.py`](manager_agent_gym/core/evaluation/team_change_metrics.py), [`tests/test_team_change_metrics.py`](tests/test_team_change_metrics.py) | Quantifies how well the manager handled each join/leave event | Done |
| CLI that scores existing runs and writes `team_change_metrics.json`; dashboard table of the metrics per run and manager | [`dashboard/analysis/analyze_team_changes.py`](dashboard/analysis/analyze_team_changes.py), [`dashboard/web/src/pages/MetricsPage.tsx`](dashboard/web/src/pages/MetricsPage.tsx) | Reports the metrics per run and per manager without running any simulation | Done |

## Dashboard

| Update | Files | Purpose | Status |
|---|---|---|---|
| React + FastAPI: Metrics page and a before/after DAG diff page; feature tracker in [`dashboard/FEATURES.md`](dashboard/FEATURES.md) | [`dashboard/`](dashboard/), [`scripts/launch_dashboard.sh`](scripts/launch_dashboard.sh), [`.claude/commands/eval-app.md`](.claude/commands/eval-app.md), [`tests/test_dashboard_dag.py`](tests/test_dashboard_dag.py) | Lets you inspect metrics and see how scenario changes alter the task graph. Read-only. | Done |
| Run analysis (summary.json per run) moved from the removed `diagnostics/` to `dashboard/analysis/`; run outputs now live in `dashboard/outputs/` (override with `$MAG_OUTPUTS_DIR`); `scripts/run.sh`, `run_all.sh`, `eval.sh` updated; Gradio launcher removed | [`dashboard/analysis/analyze_runs.py`](dashboard/analysis/analyze_runs.py), [`dashboard/server/data.py`](dashboard/server/data.py), [`scripts/`](scripts/) | Keeps the analysis the dashboard depends on after `diagnostics/` was removed | Done |
| First scenario's `team_change_spec.py` (events, affected tasks, hidden mapping) | `examples/end_to_end_examples_team/<workflow>/team_change_spec.py` | Metrics need a scenario that defines its affected tasks and pattern-based checklists. None exists yet. | Planned |
