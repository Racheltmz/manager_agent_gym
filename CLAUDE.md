# CLAUDE.md

## Keep UPDATES.md in sync

`UPDATES.md` (repo root) is the running record of changes made for team-membership
non-stationarity, as three tables: **Manager agent**, **Benchmark**, **Metric**.

Whenever you add, change, or remove an update — code, scripts, diagnostics, docs, or a revert —
edit `UPDATES.md` in the same turn, before reporting the work as done:

- **Added** an update: add a row to the table for the component it belongs to. If it touches
  several components, add a row to each.
- **Removed or reverted** an update: delete its row, or change its status. Do not leave a row
  describing something that no longer exists.
- **Planned work that gets built**: change its status from `Planned` to `Done`.
- Each row has: Update, Files, Purpose, Status (`Done` or `Planned`). Link files that exist.
- Which table: changes to how the manager is run, informed, or compared go in **Manager agent**;
  scenarios, tasks, workers, and checklists go in **Benchmark**; scoring, evaluators, and
  diagnostics reporting go in **Metric**.

Verify a row against the working tree (`git diff`, or the file itself) before writing it.

## Dashboard

`dashboard/` is the React + FastAPI diagnostics app (`scripts/launch_dashboard.sh`). It only reads
existing files under `diagnostics/outputs/` and scenario `workflow.py` files, so it is safe to run.
Keep `dashboard/FEATURES.md` in sync the same way as `UPDATES.md`: add, change, or remove a row
whenever a feature is added, changed, or removed.
