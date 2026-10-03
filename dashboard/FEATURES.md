# Dashboard features

React + FastAPI eval app (replaced the removed Gradio `diagnostics/eval_app.py`). Reads existing run outputs
and scenario task graphs only; it never starts a simulation.

Run: `scripts/launch_dashboard.sh` (dev, hot reload) or `uv run uvicorn dashboard.server.main:app`
after `npm run build` in `dashboard/web`.

Status: **Done** / **Planned**.

## Page: Metrics (`/metrics`)

| Feature | Status |
|---|---|
| Workflow filter | Done |
| Mid-episode-joiners-only filter (Non-stationarity and join timeline sections) | Done |
| Metrics (mean across runs) per manager mode as big-number cards: post-change score, disruption score, baseline score, post-change leave; per-run team-change table below | Done |
| Checklist-score DAG: per-task deterministic score at a chosen timestep (slider + run picker), node intensity = score, hover for details; a task the manager decomposed is scored on its subtasks' combined output | Done |
| Click a checklist-DAG node for its checklist items (pattern, pass/fail) and the output text they were scored against (for a decomposed task, the subtasks' outputs are listed under the subtasks) | Done |
| Runs table with run-health status | Done |
| Non-stationarity aggregate per manager mode (3 cards: never assigned, delayed, avg assignment lag; plus table) | Done |
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
