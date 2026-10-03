# CLAUDE.md

## Keep UPDATES.md in sync

`UPDATES.md` (repo root) is the running record of changes made for team-membership
non-stationarity, as three tables: **Manager agent**, **Benchmark**, **Metric**.

Whenever you add, change, or remove an update — code, scripts, dashboard, docs, or a revert —
edit `UPDATES.md` in the same turn, before reporting the work as done:

- **Added** an update: add a row to the table for the component it belongs to. If it touches
  several components, add a row to each.
- **Removed or reverted** an update: delete its row, or change its status. Do not leave a row
  describing something that no longer exists.
- **Planned work that gets built**: change its status from `Planned` to `Done`.
- Each row has: Update, Files, Purpose, Status (`Done` or `Planned`). Link files that exist.
- Which table: changes to how the manager is run, informed, or compared go in **Manager agent**;
  scenarios, tasks, workers, and checklists go in **Benchmark**; scoring, evaluators, and
  analysis and dashboard reporting go in **Metric**.

Verify a row against the working tree (`git diff`, or the file itself) before writing it.

## Dashboard

`dashboard/` is the React + FastAPI eval app (`scripts/launch_dashboard.sh`). It only reads
existing files under `dashboard/outputs/` (override with `$MAG_OUTPUTS_DIR`) and scenario `workflow.py` files, so it is safe to run.
Keep `dashboard/FEATURES.md` in sync the same way as `UPDATES.md`: add, change, or remove a row
whenever a feature is added, changed, or removed.

## Team benchmark skill

`/create-team-benchmark <workflow>` (or `scripts/create_team_benchmark.sh`) converts a workflow into
its team-membership variant from `docs/team_non_stationarity/benchmark.md`. It calls Claude only, never
the OpenAI API, and it never runs `run.sh`, `run_all.sh` or `run_examples.py`. Gate validation
(`scripts/team_benchmark.py gate-run`, Claude plays each worker on each affected task) is deferred
because of its cost: the skill sets `correct_agents` by judgment, and `gate-run` refuses without
`--enable`. On an existing scenario the skill updates in place: `scripts/team_benchmark.py diff` shows
what changed in its inputs since it was stamped, and the skill edits only what that affects
(`--rebuild` deletes and recreates it from scratch, with a backup in the temp directory). Prefer
changing `benchmark.md` or the skill and running the update over hand-editing a generated scenario;
a hand edit leaves `CONVERSION.md` and the stamp out of step unless you also update them. If you edit
the skill, `benchmark.md` or `metrics.md`, tell the user which scenarios
`scripts/create_team_benchmark.sh --status` now reports as stale.
