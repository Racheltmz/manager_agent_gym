"""Side-by-side comparison of two scenarios as two graphs, in three views.

- workflow:    tasks and their dependencies, with checklist counts and (for a team scenario) which
               roster event affects each task.
- team:        the roster timeline as a chain of timesteps, each listing who joins and who leaves.
- preferences: weight updates -> preferences -> evaluators -> rubrics.

Both panes of a view share one layout (a union of the two scenarios), so a node sits at the same
position on both sides and a node that exists on one side only leaves a visible gap on the other.
Node status is relative to the other side: removed (only before), added (only after), changed
(on both, but different), unchanged. Everything is read from the scenario modules, which only
build pydantic objects: no simulation, no LLM call.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import dag
from .data import REPO_ROOT

PAD, GAP_X, GAP_Y, LINE_H = 20, 64, 16, 15
VGAP_X, VGAP_Y = 24, 46  # gaps in the top-to-bottom layout
WORKFLOW_W, WORKFLOW_H = 176, 84
TEAM_W = 300
PREF_W, PREF_H = 206, 56
PRIVATE_MARKER = "PRIVATE HOUSE RULES"


# --- data the views consume ------------------------------------------------------------------


@dataclass
class WorkflowData:
    tasks: dict[str, dict]  # node name -> dag._task_view
    edges: list[tuple[str, str]]
    # task name -> events affecting it: {timestep, action, agent_id, case, correct}
    affected: dict[str, list[dict]] = field(default_factory=dict)


@dataclass
class TeamData:
    events: list[dict]  # {timestep, action, agent_id, reason}
    workers: dict[str, dict]  # agent_id -> {agent_type, description, capabilities, system_prompt}


# --- union graph -----------------------------------------------------------------------------


class _Union:
    """Nodes and edges of both sides on one shared layout."""

    def __init__(self, width: int, default_height: int, orientation: str = "horizontal"):
        self.width = width
        self.default_height = default_height
        self.orientation = orientation  # "horizontal": layers are columns; "vertical": layers are rows
        self.nodes: dict[str, dict[str, Any]] = {}
        self.order: list[str] = []
        self.edges: dict[tuple[str, str], dict[str, bool]] = {}

    def add(
        self,
        side: str,
        id: str,
        layer: int,
        label: str,
        sublabel: str = "",
        lines: list[dict] | None = None,
        rows: dict[str, str] | None = None,
        meta: dict[str, str] | None = None,
        tags: list[str] | None = None,
        changed: bool | None = None,
        height: int | None = None,
    ) -> None:
        n = self.nodes.get(id)
        if n is None:
            n = {
                "id": id,
                "layer": layer,
                "label": label,
                "in": {"before": False, "after": False},
                "sublabel": {},
                "lines": {},
                "rows": {},
                "meta": {},
                "tags": {},
                "changed": False,
                "height": None,
            }
            self.nodes[id] = n
            self.order.append(id)
        n["in"][side] = True
        n["sublabel"][side] = sublabel
        n["lines"][side] = lines or []
        n["rows"][side] = rows or {}
        n["meta"][side] = meta or {}
        n["tags"][side] = tags or []
        n["changed"] = n["changed"] or bool(changed)
        if height:
            n["height"] = max(n["height"] or 0, height)

    def edge(self, side: str, source: str, target: str) -> None:
        self.edges.setdefault((source, target), {})[side] = True

    def finalize(self, view: str) -> dict[str, Any]:
        details: dict[str, Any] = {}
        for id, n in self.nodes.items():
            both = n["in"]["before"] and n["in"]["after"]
            rows: list[dict] = []
            for is_meta, key in ((False, "rows"), (True, "meta")):
                b, a = n[key].get("before", {}), n[key].get("after", {})
                for label in dict.fromkeys([*b, *a]):
                    rows.append({"label": label, "before": b.get(label), "after": a.get(label), "meta": is_meta})
            differs = both and any(r["before"] != r["after"] for r in rows if not r["meta"])
            n["is_changed"] = n["changed"] or differs
            details[id] = {"title": n["label"], "rows": rows}

        for n in self.nodes.values():
            n["height"] = n["height"] or self.default_height
        by_layer: dict[int, list[str]] = {}
        for id in self.order:
            by_layer.setdefault(self.nodes[id]["layer"], []).append(id)
        pos: dict[str, tuple[int, int]] = {}
        if self.orientation == "vertical":
            # Layers are rows, centred on the widest one. Narrow canvases suit side-by-side panes.
            col_w = self.width + VGAP_X
            widest = max((len(ids) * col_w - VGAP_X for ids in by_layer.values()), default=self.width)
            y = PAD
            for layer, ids in sorted(by_layer.items()):
                x0 = PAD + (widest - (len(ids) * col_w - VGAP_X)) // 2
                for col, id in enumerate(ids):
                    pos[id] = (x0 + col * col_w, y)
                y += max(self.nodes[i]["height"] for i in ids) + VGAP_Y
            canvas = {"width": widest + PAD * 2, "height": y - VGAP_Y + PAD}
        else:
            bottom = PAD
            for layer, ids in sorted(by_layer.items()):
                y = PAD
                for id in ids:
                    pos[id] = (PAD + layer * (self.width + GAP_X), y)
                    y += self.nodes[id]["height"] + GAP_Y
                bottom = max(bottom, y)
            last = max(by_layer, default=0)
            canvas = {"width": PAD * 2 + (last + 1) * self.width + last * GAP_X, "height": bottom + PAD}

        panes: dict[str, Any] = {}
        for side, other in (("before", "after"), ("after", "before")):
            nodes = []
            for id in self.order:
                n = self.nodes[id]
                if not n["in"][side]:
                    continue
                if not n["in"][other]:
                    status = "removed" if side == "before" else "added"
                else:
                    status = "changed" if n["is_changed"] else "unchanged"
                x, y = pos[id]
                nodes.append(
                    {
                        "id": id,
                        "label": n["label"],
                        "sublabel": n["sublabel"][side],
                        "lines": n["lines"][side],
                        "tags": n["tags"][side],
                        "status": status,
                        "x": x,
                        "y": y,
                        "w": self.width,
                        "h": n["height"],
                    }
                )
            present = {n["id"] for n in nodes}
            edges = []
            for (s, t), sides in self.edges.items():
                if not sides.get(side) or s not in present or t not in present:
                    continue
                shared = sides.get("before") and sides.get("after")
                status = "unchanged" if shared else ("removed" if side == "before" else "added")
                edges.append({"source": s, "target": t, "status": status})
            panes[side] = {"nodes": nodes, "edges": edges}

        counts = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0}
        for n in self.nodes.values():
            if not n["in"]["before"]:
                counts["added"] += 1
            elif not n["in"]["after"]:
                counts["removed"] += 1
            else:
                counts["changed" if n["is_changed"] else "unchanged"] += 1
        return {"view": view, "orientation": self.orientation, "canvas": canvas, **panes, "counts": counts, "details": details}


def _join(values: list[str], empty: str = "–") -> str:
    return ", ".join(values) if values else empty


# --- workflow view ---------------------------------------------------------------------------


def workflow_view(a: WorkflowData, b: WorkflowData) -> dict[str, Any]:
    names = list(dict.fromkeys([*a.tasks, *b.tasks]))
    edges = sorted(set(a.edges) | set(b.edges))
    pos = dag._layout(names, edges)
    u = _Union(WORKFLOW_W, WORKFLOW_H, "vertical")

    for name in sorted(names, key=lambda n: pos[n]):
        for side, sc in (("before", a), ("after", b)):
            task = sc.tasks.get(name)
            if task is None:
                continue
            deps = sorted(s for s, t in sc.edges if t == name)
            items = task["requirement_items"]
            checks = len(items)
            hits = [h for covered in task["covers"] for h in sc.affected.get(covered, [])]
            tags = []
            for h in hits:
                tags.append(f"{'join' if h['action'] == 'add' else 'leave'} t{h['timestep']}")
                if h.get("case"):
                    tags.append(h["case"])
            meta = {}
            if hits:
                meta["Affected by"] = "\n".join(
                    f"{'join' if h['action'] == 'add' else 'leave'} t={h['timestep']}: {h['agent_id']}"
                    + (f" ({h['case']})" if h.get("case") else "")
                    for h in hits
                )
                meta["Correct worker"] = _join(sorted({c for h in hits for c in h.get("correct", [])}))
            u.add(
                side,
                name,
                pos[name][0],
                name,
                sublabel=f"{checks} checks" if checks else "",
                tags=list(dict.fromkeys(tags)),
                rows={
                    "Description": task["description"],
                    "Checklist": "\n".join(f"{i['key']}: {i['pattern'] or '(prose only)'}" for i in items) or "–",
                    "Dependencies": _join(deps),
                    "Subtasks": str(task["subtask_count"]),
                },
                meta=meta,
            )
    for side, sc in (("before", a), ("after", b)):
        for s, t in sc.edges:
            u.edge(side, s, t)
    return u.finalize("workflow")


# --- team view -------------------------------------------------------------------------------


def _profile(w: dict | None) -> str:
    if not w:
        return "–"
    return f"{w['agent_type']} · {len(w['capabilities'])} capabilities · prompt {len(w['system_prompt'])} chars"


def _private_rules(w: dict | None) -> str:
    if not w or PRIVATE_MARKER not in w["system_prompt"]:
        return "–"
    return PRIVATE_MARKER + w["system_prompt"].split(PRIVATE_MARKER, 1)[1].rstrip()


def team_view(a: TeamData, b: TeamData) -> dict[str, Any]:
    def by_step(t: TeamData) -> dict[int, dict[tuple[str, str], str]]:
        out: dict[int, dict[tuple[str, str], str]] = {}
        for e in t.events:
            out.setdefault(e["timestep"], {})[(e["action"], e["agent_id"])] = e.get("reason") or ""
        return out

    sa, sb = by_step(a), by_step(b)
    steps = sorted(set(sa) | set(sb))
    u = _Union(TEAM_W, 44, "vertical")

    def worker_changed(agent_id: str) -> bool:
        wa, wb = a.workers.get(agent_id), b.workers.get(agent_id)
        return bool(wa and wb and wa != wb)

    for layer, ts in enumerate(steps):
        ev_a, ev_b = sa.get(ts, {}), sb.get(ts, {})
        for side, own, other in (("before", ev_a, ev_b), ("after", ev_b, ev_a)):
            if ts not in (sa if side == "before" else sb):
                continue
            lines = []
            for (action, agent_id) in sorted(own, key=lambda k: (k[0] != "add", k[1])):
                if (action, agent_id) not in other:
                    status = "removed" if side == "before" else "added"
                else:
                    status = "changed" if worker_changed(agent_id) else "unchanged"
                lines.append({"text": f"{'+' if action == 'add' else '−'} {agent_id}", "status": status})
            adds = sum(1 for k in own if k[0] == "add")
            rows: dict[str, str] = {}
            for (action, agent_id), reason in sorted(own.items(), key=lambda kv: (kv[0][0] != "add", kv[0][1])):
                sign = "+" if action == "add" else "−"
                rows[f"{sign} {agent_id}"] = reason or "(no reason)"
            u.add(
                side,
                f"t{ts}",
                layer,
                f"t={ts}",
                sublabel=f"+{adds} / −{len(own) - adds}",
                lines=lines,
                rows=rows,
                changed=any(l["status"] == "changed" for l in lines),
                height=52 + LINE_H * max(len(ev_a), len(ev_b)),
            )

    # Worker-level rows, shown in the detail panel of the step where a worker joins.
    for ts in steps:
        node = u.nodes[f"t{ts}"]
        for side, sc, own in (("before", a, sa.get(ts, {})), ("after", b, sb.get(ts, {}))):
            if node["in"][side]:
                for (action, agent_id) in own:
                    if action == "add":
                        node["rows"][side][f"{agent_id}: profile"] = _profile(sc.workers.get(agent_id))
                        rules = _private_rules(sc.workers.get(agent_id))
                        if rules != "–" or _private_rules((b if side == "before" else a).workers.get(agent_id)) != "–":
                            node["rows"][side][f"{agent_id}: private rules"] = rules

    present = {"before": [ts for ts in steps if ts in sa], "after": [ts for ts in steps if ts in sb]}
    for side, seq in present.items():
        for x, y in zip(seq, seq[1:]):
            u.edge(side, f"t{x}", f"t{y}")
    return u.finalize("team")


# --- preferences view ------------------------------------------------------------------------


def preferences_view(a: dict, b: dict) -> dict[str, Any]:
    u = _Union(PREF_W, PREF_H)

    def evaluator_rows(ev: dict) -> dict[str, str]:
        return {"Aggregation": ev.get("aggregation", "–"), "Rubrics": str(len(ev["rubrics"]))}

    for side, sc in (("before", a), ("after", b)):
        for up in sc.get("updates", []):
            uid = f"update:{up['timestep']}"
            u.add(
                side, uid, 0, f"Weights at t={up['timestep']}",
                sublabel=up["mode"],
                rows={"Mode": up["mode"], "Changes": "\n".join(f"{k}: {v:g}" for k, v in sorted(up["changes"].items()))},
            )
        for pref in sc.get("preferences", []):
            u.add(
                side, f"pref:{pref['name']}", 1, pref["name"],
                sublabel=f"weight {pref['weight']:g}",
                rows={"Weight": f"{pref['weight']:g}", "Description": pref.get("description") or "–"},
            )
        groups = [(f"pref:{p['name']}", p["evaluator"]) for p in sc.get("preferences", []) if p.get("evaluator")]
        if sc.get("goal"):
            groups.append((None, sc["goal"]))
        for parent, ev in groups:
            eid = f"eval:{ev['name']}"
            u.add(side, eid, 2, ev["name"], sublabel=f"{len(ev['rubrics'])} rubrics", rows=evaluator_rows(ev))
            for r in ev["rubrics"]:
                rid = f"rubric:{ev['name']}:{r['name']}"
                u.add(
                    side, rid, 3, r["name"],
                    sublabel=f"max {r['max_score']:g} · {r['kind']}",
                    height=48,
                    rows={
                        "Max score": f"{r['max_score']:g}",
                        "Kind": r["kind"],
                        "Run condition": r["run_condition"],
                        "Prompt": r["prompt"] or "–",
                    },
                )
                u.edge(side, eid, rid)
            if parent:
                u.edge(side, parent, eid)
        for up in sc.get("updates", []):
            for name in up["changes"]:
                u.edge(side, f"update:{up['timestep']}", f"pref:{name}")
    return u.finalize("preferences")


# --- loading ---------------------------------------------------------------------------------


def _scenario_dir(scenario_id: str) -> Path:
    root, _, name = scenario_id.partition("/")
    if root not in dag.SCENARIO_ROOTS or not name or "/" in name or ".." in name:
        raise KeyError(scenario_id)
    d = REPO_ROOT / "examples" / root / name
    if not d.is_dir():
        raise KeyError(scenario_id)
    return d


def _signature(d: Path) -> tuple:
    return tuple((p.name, p.stat().st_mtime_ns) for p in sorted(d.glob("*.py")))


def _load_module(d: Path, stem: str, tag: str):
    path = d / f"{stem}.py"
    if not path.exists():
        raise ValueError(f"{path.relative_to(REPO_ROOT)} does not exist")
    spec = importlib.util.spec_from_file_location(f"_dashboard_{tag}_{stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _call_matching(module, predicate) -> Any | None:
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if fn.__module__ == module.__name__ and predicate(name):
            result = dag._try_call_zero_arg(fn)
            if result is not None:
                return result
    return None


@lru_cache(maxsize=16)
def _workflow_cached(scenario_id: str, signature: tuple) -> WorkflowData:
    g = dag.load_graph(scenario_id)
    return WorkflowData(tasks=g["tasks"], edges=[tuple(e) for e in g["edges"]], affected=_load_affected(scenario_id))


def _load_affected(scenario_id: str) -> dict[str, list[dict]]:
    """task name -> events that affect it, read from the scenario's team_change_spec (if any)."""
    root, _, name = scenario_id.partition("/")
    if not (REPO_ROOT / "examples" / root / name / "team_change_spec.py").exists():
        return {}
    package = f"examples.{root}.{name}"
    for mod in [m for m in sys.modules if m == package or m.startswith(package + ".")]:
        del sys.modules[mod]  # the spec uses relative imports, so load it as part of its package
    spec = importlib.import_module(f"{package}.team_change_spec").create_team_change_spec()
    out: dict[str, list[dict]] = {}
    for e in spec.events:
        for task in e.affected_tasks:
            out.setdefault(task, []).append(
                {
                    "timestep": e.timestep,
                    "action": e.action,
                    "agent_id": e.agent_id,
                    "case": spec.cases.get(task) or ("leave" if e.action == "remove" else None),
                    "correct": sorted(spec.correct_agents.get(task, [])),
                }
            )
    return out


def load_workflow(scenario_id: str) -> WorkflowData:
    return _workflow_cached(scenario_id, _signature(_scenario_dir(scenario_id)))


@lru_cache(maxsize=16)
def _team_cached(scenario_id: str, signature: tuple) -> TeamData:
    module = _load_module(_scenario_dir(scenario_id), "team", scenario_id.replace("/", "_"))
    timeline = module.create_team_timeline()
    events, workers = [], {}
    for ts, changes in sorted(timeline.items()):
        for action, payload, reason in changes:
            agent_id = payload.agent_id if hasattr(payload, "agent_id") else str(payload)
            events.append({"timestep": ts, "action": action, "agent_id": agent_id, "reason": reason})
            if hasattr(payload, "agent_id") and agent_id not in workers:
                workers[agent_id] = {
                    "agent_type": getattr(payload, "agent_type", "?"),
                    "description": getattr(payload, "agent_description", ""),
                    "capabilities": list(getattr(payload, "agent_capabilities", []) or []),
                    "system_prompt": getattr(payload, "system_prompt", "") or "",
                }
    return TeamData(events=events, workers=workers)


def load_team(scenario_id: str) -> TeamData:
    return _team_cached(scenario_id, _signature(_scenario_dir(scenario_id)))


def _evaluator_dict(ev: Any) -> dict:
    rubrics = []
    for r in ev.rubrics:
        rubrics.append(
            {
                "name": r.name,
                "max_score": float(r.max_score),
                "kind": "llm" if getattr(r, "llm_prompt", None) else "function",
                "run_condition": str(getattr(getattr(r, "run_condition", None), "value", getattr(r, "run_condition", ""))),
                "prompt": getattr(r, "llm_prompt", None),
            }
        )
    agg = getattr(ev, "aggregation", None)
    return {"name": ev.name, "aggregation": str(getattr(agg, "value", agg)), "rubrics": rubrics}


@lru_cache(maxsize=16)
def _preferences_cached(scenario_id: str, signature: tuple) -> dict:
    module = _load_module(_scenario_dir(scenario_id), "preferences", scenario_id.replace("/", "_"))
    weights = _call_matching(module, lambda n: "preferences" in n and "update" not in n)
    updates = _call_matching(module, lambda n: "update_requests" in n)
    goal = _call_matching(module, lambda n: "goal_achievement" in n)
    return {
        "preferences": [
            {
                "name": p.name,
                "weight": float(p.weight),
                "description": p.description,
                "evaluator": _evaluator_dict(p.evaluator) if p.evaluator else None,
            }
            for p in (weights.preferences if weights else [])
        ],
        "goal": _evaluator_dict(goal) if goal else None,
        "updates": [
            {"timestep": u.timestep, "mode": str(getattr(u.mode, "value", u.mode)), "changes": dict(u.changes)}
            for u in (updates or [])
        ],
    }


def load_preferences(scenario_id: str) -> dict:
    return _preferences_cached(scenario_id, _signature(_scenario_dir(scenario_id)))


VIEWS = ("workflow", "team", "preferences")


def compare(view: str, before_id: str, after_id: str) -> dict[str, Any]:
    if view == "workflow":
        return workflow_view(load_workflow(before_id), load_workflow(after_id))
    if view == "team":
        return team_view(load_team(before_id), load_team(after_id))
    if view == "preferences":
        return preferences_view(load_preferences(before_id), load_preferences(after_id))
    raise ValueError(f"unknown view '{view}'; choices: {', '.join(VIEWS)}")
