# Main commands for developer

> Direction: empirical study of how a manager agent handles mid-workflow changes on MA-Gym's benchmarks, improved with other peer-reviewed benchmarks (`CLAUDE.md`, `research/decisions.md`). **No study command exists yet**: the borrowed benchmark elements, the
> change layer, the scorer and the study runner are not built. Only the generic MA-Gym commands below exist. Run from the repo root with `uv run`.

## Free (no LLM call)

```
uv run pytest tests -q                  # whole suite
uv run pytest tests/test_assign_restart.py tests/test_cot_team_awareness.py tests/test_skip_llm_judge.py -q   # fixes the study relies on (ML-052, ML-053, no-judge)
bash scripts/eval.sh                    # analyse existing runs only (reads files)
bash scripts/launch_dashboard.sh        # dashboard on :5173 (read-only; never starts a run)
```

## Costs money (only when the user's current message asks for it)

```
bash scripts/run.sh                     # one MA-Gym example workflow, one manager mode, then analysis (OpenAI API)
```

`scripts/run.sh` is the closest thing to a study runner but targets MA-Gym's example workflows (`WORKFLOWS`, `MODE`). It will need adapting to the study's scenarios; do not run it to test edits (check with `bash -n`, or `STAGE=eval`).

## Planned for the study (not built)

Benchmark flaws list and borrowed elements, a no-change run, one run per change type (environment, preference, goal), the frozen CoT baseline run, the reference conditions (ignore, replan from scratch), the
improvement runs, the analysis script and a no-spend cost estimator (build the real prompts and count tokens without calling a model). Add each command here when it exists.

## Removed on 2026-11-03 (not needed for the study)

`scripts/create_benchmark.sh` and `.claude/skills/create-benchmark/` (drove the retired agent-loss benchmark; their tools did not exist), `scripts/run_all.sh` (join/leave suite),
stale `scripts/__pycache__/`, `dev.txt`, `docker-compose.yaml` and `nixpacks.toml` (upstream deployment files for a different app), `.ruff_cache/` (a regenerable cache), the stale `diagnostics/`
entries in `.claude/settings.local.json`, the join/leave metrics (`core/evaluation/team_change_metrics.py`, `tests/test_team_change_metrics.py`, `dashboard/analysis/analyze_team_changes.py`, and the
dashboard's `/api/team-change` endpoint, cards and table), and the agent-unavailability hooks (`Workflow.unavailable_agents`, the `_can_start` engine hook, the rejection branches in `manager_actions.py`,
`AvailabilityNotice` and the "Worker Availability" block in the `cot` prompt). The suite passes (97 passed, 1 skipped) and the dashboard type-checks.

## Still present, not needed for the study (not deleted)

The MA-Gym example workflows are **not** in this list: they are the base benchmark (see the end of this file).

| Item | Why it is not needed | Suggested action |
|---|---|---|
| Dashboard: "Non-stationarity handling", join timeline, "mid-episode joiners" filter (`MetricsPage.tsx`, `dashboard/server/data.py`, `/api/joins`, `/api/nonstationarity`, join fields in `analyze_runs.py`) | Join/leave views over upstream run summaries | Remove if you want a leaner dashboard |
| `AgentRegistry.schedule_agent_add/remove` and the team-timeline wiring in `examples/run_examples.py` (`create_team_timeline`) | Upstream join/leave support; inert when a scenario has no timeline | Leave |
| `docs/` (MA-Gym docs site, `_tmp_graphviz/` scratch), `mkdocs.yml`, root copies of `LIBRARY_DOCUMENTATION.md`, `QUICK_START_GUIDE.md`, `TECHNICAL_ARCHITECTURE.md` | Upstream documentation of MA-Gym itself | Leave |
| `dashboard/outputs/cot/legal_m_and_a_team*` (about 146 MB) and `simulation_outputs/` | Outputs of the retired join/leave runs; git-ignored, so **not recoverable** once deleted | Your call: archive or delete |

Still needed and easy to miss: `examples/end_to_end_examples/` (21 MA-Gym workflows), `examples/scenarios.py` and `examples/cli.py` (the base benchmark the study improves, `decisions.md` D22), `scripts/run.sh` and `scripts/eval.sh` (to adapt), `examples/run_examples.py` (the only runner, to adapt), `manager_agent_gym/core/manager_agent/` (CoT, Random, Assign-All),
`core/common/usage.py` (cost), `core/evaluation/task_requirements_evaluator.py` (reusable checklist scorer), `tests/test_cot_team_awareness.py`, `tests/test_assign_restart.py`, `tests/test_skip_llm_judge.py`,
`tests/integration/test_engine_manager_context_log.py` (the fixes and the context log), and the dashboard's checklist DAG and DAG diff page.
