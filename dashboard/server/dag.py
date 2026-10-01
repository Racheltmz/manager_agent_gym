"""Scenario task graphs and before/after diffs.

Builds each scenario's workflow exactly as authored (workflow.py only constructs pydantic
Task objects, no LLM or network call), then lays the graph out in layers. A diff overlays two
scenarios by task *name* so renamed tasks show as removed + added.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from .data import REPO_ROOT

# Scenario collections, in the order they are offered. `end_to_end_examples` holds the
# originals; `end_to_end_examples_team` holds the team-membership non-stationarity variants.
SCENARIO_ROOTS = ["end_to_end_examples", "end_to_end_examples_team"]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def list_scenarios() -> list[dict[str, str]]:
    out = []
    for root in SCENARIO_ROOTS:
        base = REPO_ROOT / "examples" / root
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if (d / "workflow.py").exists():
                out.append({"id": f"{root}/{d.name}", "collection": root, "name": d.name})
    return out


def _try_call_zero_arg(fn) -> Any | None:
    try:
        sig = inspect.signature(fn)
        if any(
            p.default is inspect.Parameter.empty
            and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            for p in sig.parameters.values()
        ):
            return None
        return fn()
    except Exception:
        return None


def _find_workflow(module: Any) -> Any | None:
    """Conventional factory names first, then any zero-arg function with 'workflow' in its name."""
    for name in ("create_workflow", "build_workflow", "make_workflow", "init_workflow"):
        fn = getattr(module, name, None)
        if callable(fn):
            wf = _try_call_zero_arg(fn)
            if getattr(wf, "tasks", None) is not None:
                return wf
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if "workflow" in name.lower():
            wf = _try_call_zero_arg(fn)
            if getattr(wf, "tasks", None) is not None:
                return wf
    return None


def _load_workflow(scenario_id: str) -> Any:
    root, _, name = scenario_id.partition("/")
    if root not in SCENARIO_ROOTS or not name or "/" in name or ".." in name:
        raise KeyError(scenario_id)
    path: Path = REPO_ROOT / "examples" / root / name / "workflow.py"
    if not path.exists():
        raise KeyError(scenario_id)
    spec = importlib.util.spec_from_file_location(f"_dashboard_{root}_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    wf = _find_workflow(module)
    if wf is None:
        raise ValueError(f"no workflow factory found in {path}")
    return wf


def _task_view(t: Any) -> dict[str, Any]:
    return {
        "name": t.name,
        "description": t.description or "",
        "subtask_count": len(getattr(t, "subtasks", None) or []),
        "requirements": [r.key for r in (getattr(t, "requirements", None) or [])],
    }


@lru_cache(maxsize=32)
def _load_graph_cached(scenario_id: str, mtime: float) -> dict[str, Any]:
    wf = _load_workflow(scenario_id)
    by_id = {str(tid): t for tid, t in wf.tasks.items()}
    tasks = {t.name: _task_view(t) for t in by_id.values()}
    edges = sorted(
        {
            (by_id[str(d)].name, t.name)
            for t in by_id.values()
            for d in (t.dependency_task_ids or [])
            if str(d) in by_id
        }
    )
    return {"tasks": tasks, "edges": edges}


def load_graph(scenario_id: str) -> dict[str, Any]:
    root, _, name = scenario_id.partition("/")
    path = REPO_ROOT / "examples" / root / name / "workflow.py"
    # Keyed on mtime so an edited workflow.py is picked up without restarting the server.
    return _load_graph_cached(scenario_id, path.stat().st_mtime if path.exists() else 0.0)


def _layout(names: list[str], edges: list[tuple[str, str]]) -> dict[str, tuple[int, int]]:
    """name -> (layer, row). Longest-path layering, then one barycenter pass per layer."""
    deps: dict[str, list[str]] = {n: [] for n in names}
    for a, b in edges:
        deps[b].append(a)
    layer: dict[str, int] = {}

    def depth(n: str, seen: tuple[str, ...] = ()) -> int:
        if n in layer:
            return layer[n]
        if n in seen:  # cycle guard: should not happen for a real workflow
            return 0
        layer[n] = 1 + max((depth(d, (*seen, n)) for d in deps[n]), default=-1)
        return layer[n]

    for n in names:
        depth(n)

    layers: dict[int, list[str]] = {}
    for n in sorted(names):
        layers.setdefault(layer[n], []).append(n)

    pos: dict[str, tuple[int, int]] = {}
    prev: dict[str, float] = {}
    for l in range(max(layers, default=-1) + 1):
        nodes = layers.get(l, [])
        if prev:

            def bary(n: str) -> float:
                ps = [prev[d] for d in deps[n] if d in prev]
                return sum(ps) / len(ps) if ps else float(len(prev))

            nodes.sort(key=bary)
        for row, n in enumerate(nodes):
            pos[n] = (l, row)
        prev = {n: float(i) for i, n in enumerate(nodes)}
    return pos


def diff(before_id: str, after_id: str) -> dict[str, Any]:
    """Overlay of two scenarios' graphs. Node status: added / removed / changed / unchanged."""
    before, after = load_graph(before_id), load_graph(after_id)
    names = sorted(set(before["tasks"]) | set(after["tasks"]))
    be, ae = set(map(tuple, before["edges"])), set(map(tuple, after["edges"]))
    all_edges = sorted(be | ae)
    pos = _layout(names, all_edges)

    nodes = []
    for n in names:
        b, a = before["tasks"].get(n), after["tasks"].get(n)
        if b is None:
            status, fields = "added", []
        elif a is None:
            status, fields = "removed", []
        else:
            fields = [
                f
                for f in ("description", "requirements", "subtask_count")
                if b[f] != a[f]
            ]
            deps_b = sorted(x for x, y in be if y == n)
            deps_a = sorted(x for x, y in ae if y == n)
            if deps_b != deps_a:
                fields.append("dependencies")
            status = "changed" if fields else "unchanged"
        view = a or b
        nodes.append(
            {
                "id": n,
                "status": status,
                "changed_fields": fields,
                "layer": pos[n][0],
                "row": pos[n][1],
                "subtask_count": view["subtask_count"],
                "requirements_before": len(b["requirements"]) if b else None,
                "requirements_after": len(a["requirements"]) if a else None,
                "description_before": b["description"] if b else None,
                "description_after": a["description"] if a else None,
            }
        )
    edges = [
        {
            "source": s,
            "target": t,
            "status": "unchanged" if (s, t) in be and (s, t) in ae
            else "removed" if (s, t) in be
            else "added",
        }
        for s, t in all_edges
    ]
    counts = {k: sum(1 for n in nodes if n["status"] == k) for k in ("added", "removed", "changed", "unchanged")}
    return {"nodes": nodes, "edges": edges, "counts": counts}
