"""Dashboard API. Run from the repo root:

    uv run uvicorn dashboard.server.main:app --port 8000 --reload

Read-only: serves existing run outputs and scenario task graphs. Never launches a run.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import dag, data

app = FastAPI(title="MA-Gym dashboard API")


@app.get("/api/runs")
def runs():
    return data.list_runs()


@app.get("/api/joins")
def joins(workflow: str, mid_episode_only: bool = True, variant: str = "all"):
    return data.list_joins(workflow, mid_episode_only, variant)


@app.get("/api/nonstationarity")
def nonstationarity(workflow: str, mid_episode_only: bool = True, variant: str = "all"):
    return data.nonstationarity_by_mode(workflow, mid_episode_only, variant)


@app.get("/api/team-change")
def team_change():
    return data.list_team_change_metrics()


@app.get("/api/scenarios")
def scenarios():
    return dag.list_scenarios()


@app.get("/api/dag/diff")
def dag_diff(before: str, after: str):
    try:
        return dag.diff(before, after)
    except KeyError as e:
        raise HTTPException(404, f"unknown scenario: {e.args[0]}")
    except ValueError as e:
        raise HTTPException(422, str(e))


# Serve the built frontend if present (npm run build in dashboard/web). Unknown paths fall
# back to index.html so client-side routes such as /metrics survive a page refresh.
_dist = Path(__file__).resolve().parents[1] / "web" / "dist"
if _dist.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        target = (_dist / path).resolve()
        if path and target.is_file() and _dist in target.parents:
            return FileResponse(target)
        return FileResponse(_dist / "index.html")
