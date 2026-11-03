# Dashboard features

React + FastAPI eval app (replaced the removed Gradio `diagnostics/eval_app.py`). Reads existing run outputs
and scenario task graphs only; it never starts a simulation.

Run: `scripts/launch_dashboard.sh` (dev, hot reload) or `uv run uvicorn dashboard.server.main:app`
after `npm run build` in `dashboard/web`.

Status: **Done** / **Planned**. Features marked "join/leave" belong to a retired direction (see `DEV.md`) and stay until the user says to remove them.
The study's own views (outcome versus reference, unnecessary changes, failure taxonomy per change type) are not built and not yet specified.

## Page: Metrics (`/metrics`)

| Feature | Status |
|---|---|
| Workflow filter | Done |
| Mid-episode-joiners-only filter (Non-stationarity and join timeline sections) | Done (join/leave; not needed for the study) |
| Checklist-score DAG: per-task deterministic score at a chosen timestep (slider + run picker), node intensity = score, hover for details; a task the manager decomposed is scored on its subtasks' combined output | Done |
| Click a checklist-DAG node for its checklist items (pattern, pass/fail) and the output text they were scored against (for a decomposed task, the subtasks' outputs are listed under the subtasks) | Done |
| Runs table with run-health status | Done |
| Non-stationarity aggregate per manager mode (3 cards: never assigned, delayed, avg assignment lag; plus table) | Done (join/leave; not needed for the study) |
| Join / first-assignment timeline table | Done (join/leave; not needed for the study) |
| Failed tasks assigned to recent joiners | Dropped (join/leave) |
| Single-run timeline (task status over time; mark the change event) | Planned |
| Per-seed spread (error bars) on charts | Planned |
| Per-change-type breakdown of the study's metrics | Planned |

## Page: DAG (`/dag`)

| Feature | Status |
|---|---|
| Before/after overlay of two scenarios, matched by task name | Done |
| Node status: added / removed / changed (dependencies, description, checklist, subtasks) / unchanged | Done |
| Diff / before / after view toggle | Done |
| Click a node for before/after description and checklist counts | Done |
| Highlight tasks affected by each injected change | Planned |
| Show which worker each task was assigned to, from a run | Planned |
| Subtask-level expansion | Planned |

## Platform

| Feature | Status |
|---|---|
| Multi-page shell (add a page: one file in `src/pages` + one entry in `App.tsx`) | Done |
| Light/dark theme | Done |
