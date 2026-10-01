# Dashboard features

React + FastAPI replacement for `diagnostics/eval_app.py` (Gradio). Reads existing run outputs
and scenario task graphs only; it never starts a simulation.

Run: `scripts/launch_dashboard.sh` (dev, hot reload) or `uv run uvicorn dashboard.server.main:app`
after `npm run build` in `dashboard/web`.

Status: **Done** / **Planned** / **Gradio only** (still in `eval_app.py`, not yet ported).

## Page: Metrics (`/metrics`)

| Feature | Status |
|---|---|
| Workflow, variant, and mid-episode-joiner filters | Done |
| Headline metrics per manager mode (5 small bar charts, mean across runs) | Done |
| Runs table with run-health status | Done |
| Team-change metrics: post-change vs baseline, disruption cost (charts + table) | Done |
| Non-stationarity aggregate per manager mode (charts + table) | Done |
| Join / first-assignment timeline table | Done |
| Failed tasks assigned to recent joiners | Gradio only |
| Single-run timeline (task status + team size over time, join/leave markers) | Gradio only |
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
| Retire `diagnostics/eval_app.py` once the Gradio-only rows above are ported | Planned |
