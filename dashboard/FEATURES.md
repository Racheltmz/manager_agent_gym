# Dashboard features

React + FastAPI eval app (replaced the removed Gradio `diagnostics/eval_app.py`). Reads existing run outputs
and scenario task graphs only; it never starts a simulation.

Run: `scripts/launch_dashboard.sh` (dev, hot reload) or `uv run uvicorn dashboard.server.main:app`
after `npm run build` in `dashboard/web`.

Status: **Done** / **Planned**.

## Page: Metrics (`/metrics`)

| Feature | Status |
|---|---|
| Workflow, variant, and mid-episode-joiner filters | Done |
| Headline metrics per manager mode (5 small bar charts, mean across runs) | Done |
| Runs table with run-health status | Done |
| Team-change metrics: post-change vs baseline, disruption cost (control tasks moved), post-change score by case (charts + table) | Done |
| Non-stationarity aggregate per manager mode (charts + table) | Done |
| Join / first-assignment timeline table | Done |
| Failed tasks assigned to recent joiners | Planned (was in the removed Gradio app) |
| Single-run timeline (task status + team size over time, join/leave markers) | Planned (was in the removed Gradio app) |
| Per-seed spread (error bars) on charts | Planned |
| Per-event breakdown of team-change metrics | Planned |

## Page: DAG (`/dag`)

| Feature | Status |
|---|---|
| Before/after overlay of two scenarios, matched by task name | Done |
| Node status: added / removed / changed (dependencies, description, checklist, subtasks) / unchanged | Done |
| Diff / before / after view toggle | Done |
| Click a node for before/after description and checklist counts | Done |
| Highlight tasks affected by each join/leave event (from the team-change spec) | Planned |
| Show which worker each task was assigned to, from a run | Planned |
| Subtask-level expansion | Planned |

## Platform

| Feature | Status |
|---|---|
| Multi-page shell (add a page: one file in `src/pages` + one entry in `App.tsx`) | Done |
| Light/dark theme | Done |
| `/eval-app start` and `/eval-app stop` Claude Code command (`.claude/commands/eval-app.md`) | Done |
