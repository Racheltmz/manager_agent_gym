"""
Mechanical helpers for the create-team-benchmark skill (.claude/skills/create-team-benchmark).

The skill does the creative conversion. This tool does the parts that must be exact:

  status [name ...]   which scenarios are missing, current, or stale (and why)
  plan <name>         rotation index and input files for one scenario
  reset <name>        back up and delete the generated scenario, so a rerun starts from scratch
  check <name>        static checks of a generated scenario against the benchmark rules
  stamp <name>        record the hashes of the inputs a scenario was generated from
  gate-run <name>     (DEFERRED, needs --enable) gate validation: Claude plays every worker on every affected task, the
                      outputs are scored against the checklist patterns, and the correct workers
                      are derived from the pass/fail table
  gate-score <name>   rescore the saved gate outputs without calling Claude

A scenario is stale when docs/team_non_stationarity/benchmark.md or metrics.md, the skill's
SKILL.md, or the source scenario changed after it was generated. Never launches a simulation
and never calls the OpenAI API. Only `gate-run` calls an LLM, and it is Claude (`claude -p`, no
tools), so it spends Claude usage and no OpenAI credits.

Usage (from the repo root):
    uv run python scripts/team_benchmark.py status
    uv run python scripts/team_benchmark.py check legal_m_and_a
    uv run python scripts/team_benchmark.py gate-run legal_m_and_a
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = "examples/end_to_end_examples"
TEAM_DIR = "examples/end_to_end_examples_team"
SKILL_FILE = ".claude/skills/create-team-benchmark/SKILL.md"
RULE_DOCS = ["docs/team_non_stationarity/benchmark.md", "docs/team_non_stationarity/metrics.md"]
STAMP_NAME = ".generated.json"

# Case names written into TeamChangeSpec.cases. benchmark.md lists the cases in its
# "Change-affected cases" table; `check` warns when that table and this set disagree.
KNOWN_CASES = ("specialist", "running_task")

# Gate validation output, written inside the generated scenario.
GATE_DIR = "gate_validation"
GATE_TABLE = "table.json"
DEFAULT_GATE_MODEL = "sonnet"
# Appended to the real worker task prompt so the reply is the deliverable text itself, which is
# what the checklist scores (a worker's output resource content).
GATE_SUFFIX = (
    "\n\nFor this run, reply with only the full text of the main deliverable you would produce as "
    "a resource: no preamble, no JSON wrapper, no self-assessment."
)


@dataclass(frozen=True)
class Layout:
    root: Path = REPO_ROOT
    source_dir: str = SOURCE_DIR
    team_dir: str = TEAM_DIR
    skill_file: str = SKILL_FILE
    rule_docs: tuple[str, ...] = tuple(RULE_DOCS)

    @property
    def team_package(self) -> str:
        return self.team_dir.replace("/", ".")


def _sha(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def source_workflows(lay: Layout) -> list[str]:
    base = lay.root / lay.source_dir
    return sorted(d.name for d in base.iterdir() if (d / "workflow.py").exists())


def _require_source(lay: Layout, name: str) -> None:
    if name not in source_workflows(lay):
        raise SystemExit(f"unknown workflow '{name}'; choices: {', '.join(source_workflows(lay))}")


def input_hashes(lay: Layout, name: str) -> dict[str, str]:
    """Hashes of everything a generated scenario depends on."""
    src = lay.root / lay.source_dir / name
    hashes = {d: _sha([lay.root / d]) for d in lay.rule_docs}
    hashes[lay.skill_file] = _sha([lay.root / lay.skill_file]) if (lay.root / lay.skill_file).exists() else "missing"
    hashes[f"{lay.source_dir}/{name}"] = _sha(list(src.glob("*.py")))
    return hashes


# --- status ------------------------------------------------------------------------------


def scenario_status(lay: Layout, name: str) -> dict[str, Any]:
    target = lay.root / lay.team_dir / name
    if not target.is_dir() or not any(target.iterdir()):
        return {"workflow": name, "state": "missing", "reasons": []}
    stamp_path = target / STAMP_NAME
    if not stamp_path.exists():
        return {"workflow": name, "state": "unstamped", "reasons": ["no .generated.json"]}
    stamped = json.loads(stamp_path.read_text()).get("inputs", {})
    now = input_hashes(lay, name)
    reasons = [f"{k} changed" for k, v in now.items() if stamped.get(k) != v]
    return {"workflow": name, "state": "stale" if reasons else "current", "reasons": reasons}


def cmd_status(lay: Layout, names: list[str]) -> int:
    rows = [scenario_status(lay, n) for n in (names or source_workflows(lay))]
    if not rows:
        print("no source workflows found")
        return 0
    width = max(len(r["workflow"]) for r in rows)
    for r in rows:
        print(f"{r['workflow']:<{width}}  {r['state']:<9}  {'; '.join(r['reasons'])}")
    counts = {s: sum(r["state"] == s for r in rows) for s in ("current", "stale", "unstamped", "missing")}
    print("\n" + ", ".join(f"{v} {k}" for k, v in counts.items()))
    return 0


# --- plan / reset / stamp ----------------------------------------------------------------


def cmd_plan(lay: Layout, name: str) -> int:
    _require_source(lay, name)
    names = source_workflows(lay)
    print(
        json.dumps(
            {
                "workflow": name,
                "rotation_index": names.index(name),
                "workflow_count": len(names),
                "source_files": sorted(p.name for p in (lay.root / lay.source_dir / name).glob("*.py")),
                "source_midrun_changes": source_midrun_changes(lay, name),
                "rule_docs": list(lay.rule_docs),
                "status": scenario_status(lay, name),
            },
            indent=2,
        )
    )
    return 0


def cmd_reset(lay: Layout, name: str) -> int:
    """Delete the generated scenario so the rerun starts from scratch. Keeps a backup."""
    _require_source(lay, name)
    team_root = lay.root / lay.team_dir
    team_root.mkdir(parents=True, exist_ok=True)
    (team_root / "__init__.py").touch(exist_ok=True)
    target = team_root / name
    if target.exists():
        backup = Path(tempfile.mkdtemp(prefix=f"team_benchmark_{name}_")) / name
        shutil.copytree(target, backup, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.rmtree(target)
        print(f"deleted {target.relative_to(lay.root)} (backup: {backup})")
    else:
        print(f"nothing to delete at {target.relative_to(lay.root)}")
    return 0


def cmd_stamp(lay: Layout, name: str) -> int:
    _require_source(lay, name)
    target = lay.root / lay.team_dir / name
    if not target.is_dir():
        raise SystemExit(f"{target} does not exist; generate the scenario first")
    stamp = {
        "workflow": name,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": input_hashes(lay, name),
    }
    (target / STAMP_NAME).write_text(json.dumps(stamp, indent=2) + "\n")
    print(f"stamped {target.relative_to(lay.root) / STAMP_NAME}")
    return 0


# --- check -------------------------------------------------------------------------------


def _case_count_in_doc(lay: Layout) -> int | None:
    path = lay.root / lay.rule_docs[0]
    if not path.exists():
        return None
    text = path.read_text()
    m = re.search(r"^##\s+.*[Cc]hange-affected cases.*?(?=^## )", text, re.S | re.M)
    if not m:
        return None
    return len(re.findall(r"^\|\s*\*\*", m.group(0), re.M))


def _scoreable(reqs: list) -> bool:
    return bool(reqs) and all(getattr(r, "pattern", None) for r in reqs)


def _prefer_root(lay: Layout) -> None:
    """Put this layout's root first on sys.path so its packages win over another layout's."""
    root = str(lay.root)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    importlib.invalidate_caches()


def _load_scenario(lay: Layout, name: str) -> tuple[Any, Any, dict, Any]:
    """Import a generated scenario fresh. Returns (package, workflow, timeline, spec)."""
    pkg_name = f"{lay.team_package}.{name}"
    _prefer_root(lay)
    for mod in [m for m in sys.modules if m == lay.team_package or m.startswith(lay.team_package + ".")]:
        del sys.modules[mod]  # always load the current files
    pkg = importlib.import_module(pkg_name)
    spec_mod = importlib.import_module(f"{pkg_name}.team_change_spec")
    return pkg, pkg.create_workflow(), pkg.create_team_timeline(), spec_mod.create_team_change_spec()


def _agent_id(payload: Any) -> str:
    return payload.agent_id if hasattr(payload, "agent_id") else str(payload)


def _timeline_changes(timeline: dict) -> list[tuple[int, str, str, Any, str]]:
    """Flatten a team timeline to (timestep, action, agent_id, payload, reason), in time order."""
    return [
        (ts, action, _agent_id(p), p, reason)
        for ts, items in sorted(timeline.items())
        for action, p, reason in items
    ]


def _roster_after(changes: list, ts: int) -> set[str]:
    alive: set[str] = set()
    for t, action, aid, _, _ in changes:
        if t > ts:
            break
        alive.add(aid) if action == "add" else alive.discard(aid)
    return alive


def source_midrun_changes(lay: Layout, name: str) -> int | None:
    """Joins and leaves after timestep 0 in the source scenario's team timeline.

    A worker re-added while still on the roster is not a join. None if the source has no
    importable `create_team_timeline`.
    """
    pkg = lay.source_dir.replace("/", ".")
    _prefer_root(lay)
    for mod in [m for m in sys.modules if m == pkg or m.startswith(pkg + ".")]:
        del sys.modules[mod]
    try:
        timeline = importlib.import_module(f"{pkg}.{name}").create_team_timeline()
        changes = _timeline_changes(timeline)
    except Exception:  # noqa: BLE001 - a source without a usable timeline just has no count
        return None
    alive: set[str] = set()
    count = 0
    for ts, action, aid, _, _ in changes:
        if action == "add":
            if aid in alive:
                continue
            alive.add(aid)
        else:
            alive.discard(aid)
        count += ts > 0
    return count


def check_scenario(lay: Layout, name: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a generated scenario. Static checks only."""
    from manager_agent_gym.schemas.workflow_agents import HumanAgentConfig

    errors: list[str] = []
    warnings: list[str] = []

    try:
        _, workflow, timeline, spec = _load_scenario(lay, name)
    except Exception as e:  # noqa: BLE001 - report any import or build failure
        return [f"cannot load scenario: {type(e).__name__}: {e}"], warnings

    # Roster, from the timeline.
    changes = _timeline_changes(timeline)
    for ts, action, aid, payload, _ in changes:
        if action == "add" and isinstance(payload, HumanAgentConfig):
            errors.append(f"t={ts}: '{aid}' is a HumanAgentConfig; the benchmark is AI agents only")
    present: dict[str, int] = {}
    removed: set[str] = set()
    for ts, action, aid, _, _ in changes:
        if action == "add":
            present[aid] = ts
        elif action == "remove":
            if aid not in present or aid in removed:
                errors.append(f"t={ts}: '{aid}' removed but not on the roster")
            removed.add(aid)

    def roster_after(ts: int) -> set[str]:
        return _roster_after(changes, ts)

    # Tasks.
    from manager_agent_gym.core.evaluation.task_requirements_evaluator import flatten_tasks

    by_name: dict[str, Any] = {}
    for t in flatten_tasks(workflow.tasks.values()):
        if t.name in by_name:
            errors.append(f"duplicate task name '{t.name}' (metrics look tasks up by name)")
        by_name[t.name] = t
    affected_all = {n for e in spec.events for n in e.affected_tasks}

    # Spec events must match the mid-episode timeline changes, both ways.
    spec_events = {(e.timestep, e.action, e.agent_id) for e in spec.events}
    mid_changes = {(ts, action, aid) for ts, action, aid, _, _ in changes if ts > 0}
    for ev in sorted(mid_changes - spec_events):
        errors.append(f"timeline change {ev} has no event in team_change_spec")
    for ev in sorted(spec_events - mid_changes):
        errors.append(f"spec event {ev} is not in the team timeline")

    if not any(e.action == "add" for e in spec.events):
        errors.append("no join event: at least one task must depend on a new worker")
    if not any(e.action == "remove" for e in spec.events):
        errors.append("no leave event")

    for e in spec.events:
        if not e.affected_tasks:
            errors.append(f"event {(e.timestep, e.action, e.agent_id)} affects no task")
        alive = roster_after(e.timestep)
        for n in e.affected_tasks:
            t = by_name.get(n)
            if t is None:
                errors.append(f"affected task '{n}' is not in the workflow")
                continue
            if t.subtasks:
                errors.append(f"affected task '{n}' is composite; only leaf tasks are assigned, pick a subtask")
            if not _scoreable(t.requirements):
                errors.append(f"affected task '{n}' needs a checklist where every item has a pattern")
            correct = spec.correct_agents.get(n)
            if not correct:
                errors.append(f"affected task '{n}' has no correct_agents entry")
            else:
                gone = sorted(c for c in correct if c not in alive)
                if gone:
                    errors.append(f"task '{n}': correct worker(s) {gone} are not on the roster after t={e.timestep}")
                if e.action == "remove" and e.agent_id in correct:
                    errors.append(f"task '{n}': the leaving worker '{e.agent_id}' is listed as correct")
            if e.action == "add":
                case = spec.cases.get(n)
                if case not in KNOWN_CASES:
                    errors.append(f"join-affected task '{n}' needs a case in {KNOWN_CASES}, got {case!r}")
        # A reason string describes the scaling event, it must not name the task it serves.
        for ts, action, aid, _, reason in changes:
            if (ts, action, aid) == (e.timestep, e.action, e.agent_id):
                named = [n for n in e.affected_tasks if n.lower() in (reason or "").lower()]
                if named:
                    errors.append(f"reason for {(ts, action, aid)} names task(s) {named}; describe the scaling event instead")
    stray = sorted(set(spec.cases) - affected_all)
    if stray:
        warnings.append(f"spec.cases has tasks no event affects: {stray}")

    # Event count against the source (benchmark.md, "Event count").
    src_n = source_midrun_changes(lay, name)
    if src_n is not None and len(spec.events) < src_n:
        warnings.append(
            f"{len(spec.events)} change event(s) against {src_n} mid-run join/leave(s) in the source: "
            "every dropped one needs its reason in CONVERSION.md"
        )

    # Controls.
    controls = [t for n, t in by_name.items() if n not in affected_all]
    if not controls:
        errors.append("no control tasks: every task is affected by an event")
    elif not any(_scoreable(t.requirements) for t in controls):
        warnings.append("no control task has a pattern-based checklist, so there is no baseline score")

    # Leave rule: only the statically checkable part.
    for e in spec.events:
        if e.action == "remove":
            pre = sorted(t.name for t in by_name.values() if t.assigned_agent_id == e.agent_id)
            if pre:
                errors.append(f"leaving worker '{e.agent_id}' is pre-assigned to {pre}; it must finish its tasks before leaving")
    if any(e.action == "remove" for e in spec.events):
        warnings.append(
            "leave timing is not checked: whether the leaver has finished every assigned task "
            "depends on the manager's runtime assignments. Record the reasoning in CONVERSION.md."
        )

    # Gate validation result, if it has been run.
    table = _read_gate_table(lay, name)
    if table is None:
        warnings.append(
            "correct_agents is a judgment from task and worker descriptions; gate validation is deferred "
            "(see benchmark.md, Gate validation)"
        )
    else:
        gate_errors, _ = gate_verdict(spec, changes, table["cells"])
        errors.extend(f"gate validation: {e}" for e in gate_errors)
        if _gate_table_is_stale(lay, name, table, by_name, changes, gate_workers(spec, changes)):
            warnings.append("gate validation table is stale: a worker prompt or task changed since it ran (rerun gate-run)")

    # Drift between the doc and this tool.
    n_doc = _case_count_in_doc(lay)
    if n_doc is not None and n_doc != len(KNOWN_CASES):
        warnings.append(
            f"benchmark.md lists {n_doc} change-affected cases but scripts/team_benchmark.py knows "
            f"{len(KNOWN_CASES)} ({', '.join(KNOWN_CASES)}); update KNOWN_CASES"
        )
    return errors, warnings


# --- gate validation ---------------------------------------------------------------------
#
# For every affected task, Claude plays every worker that can receive it: the worker's own system prompt
# is the system prompt, and the user prompt is the real worker task template with no input
# resources. The reply is scored against the task's checklist patterns, so a cell is a
# deterministic pass or fail. Claude stands in for the worker model, so this verifies the gates
# on a proxy, not on the model used in manager runs.

Generate = Callable[[str, str, str], str]  # (system_prompt, user_prompt, model) -> reply text


def _worker_configs(changes: list) -> dict[str, Any]:
    """Every AI worker that ever joins, by agent id (the roster gate validation tests)."""
    return {aid: p for _, action, aid, p, _ in changes if action == "add" and hasattr(p, "system_prompt")}


def gate_workers(spec: Any, changes: list) -> dict[str, list[str]]:
    """Per affected task, the workers it can be assigned to (the ones gate validation tests).

    For an event at timestep t: everyone on the roster after t, plus anyone who joins later (the
    manager can assign at any time after the event), plus the leaver of a leave event (the rule
    that the leaver passes needs its cell). A worker who left before t can never receive the task.
    A task affected by several events gets the union.
    """
    out: dict[str, set[str]] = {}
    for e in spec.events:
        eligible = _roster_after(changes, e.timestep)
        eligible |= {aid for ts, action, aid, _, _ in changes if action == "add" and ts > e.timestep}
        if e.action == "remove":
            eligible.add(e.agent_id)
        for n in e.affected_tasks:
            out.setdefault(n, set()).update(eligible)
    return {n: sorted(ws) for n, ws in out.items()}


def _worker_prompts(task: Any, cfg: Any) -> tuple[str, str]:
    """(system prompt, user prompt) a worker would get for `task`, mirroring AIAgent."""
    from manager_agent_gym.core.workflow_agents.prompts.ai_agent_prompts import (
        AI_AGENT_TASK_TEMPLATE,
        NO_RESOURCES_MESSAGE,
    )

    user = AI_AGENT_TASK_TEMPLATE.format(
        task_name=task.name,
        task_description=task.description,
        input_resources=NO_RESOURCES_MESSAGE,
    )
    return cfg.system_prompt, user + GATE_SUFFIX


def _cell_key(system: str, user: str, model: str) -> str:
    return hashlib.sha256("\x00".join([system, user, model]).encode()).hexdigest()[:16]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60]


def _gate_dir(lay: Layout, name: str) -> Path:
    return lay.root / lay.team_dir / name / GATE_DIR


def _read_gate_table(lay: Layout, name: str) -> dict[str, Any] | None:
    path = _gate_dir(lay, name) / GATE_TABLE
    return json.loads(path.read_text()) if path.exists() else None


def _gate_table_is_stale(
    lay: Layout, name: str, table: dict, by_name: dict, changes: list, eligible: dict[str, list[str]]
) -> bool:
    workers = _worker_configs(changes)
    for task_name, want in eligible.items():
        if sorted(table["cells"].get(task_name, {})) != sorted(w for w in want if w in workers):
            return True
    for task_name, row in table["cells"].items():
        task = by_name.get(task_name)
        if task is None:
            return True
        for wid, cell in row.items():
            cfg = workers.get(wid)
            if cfg is None or cell.get("key") != _cell_key(*_worker_prompts(task, cfg), table["model"]):
                return True
    return False


def claude_generate(system: str, user: str, model: str, timeout: int = 900) -> str:
    """One worker reply from Claude: text only, no tools, no session, run outside the repo."""
    cmd = [
        "claude", "-p", user,
        "--system-prompt", system,
        "--tools", "",
        "--model", model,
        "--no-session-persistence",
        "--output-format", "text",
    ]  # fmt: skip
    with tempfile.TemporaryDirectory(prefix="team_gate_") as cwd:  # no CLAUDE.md or memory pickup
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"claude exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:300]}")
    return proc.stdout


def gate_verdict(spec: Any, changes: list, cells: dict[str, dict[str, dict]]) -> tuple[list[str], dict[str, list[str]]]:
    """Judge a pass/fail table. Returns (errors, derived correct_agents per affected task).

    Join task: exactly the joining worker passes. Leave task: the leaver passes and at least one
    worker still on the roster passes, so the task stays solvable. The derived correct workers
    are the passing workers on the roster after the event, and the spec must list the same set.
    """
    errors: list[str] = []
    derived: dict[str, list[str]] = {}
    for e in spec.events:
        alive = _roster_after(changes, e.timestep)
        for n in e.affected_tasks:
            row = cells.get(n)
            if row is None:
                errors.append(f"task '{n}' has no gate validation row")
                continue
            broken = sorted(w for w, c in row.items() if "error" in c)
            if broken:
                errors.append(f"task '{n}': no reply for worker(s) {broken}; rerun gate-run")
                continue
            holders = {w for w, c in row.items() if c["passed"]}
            if e.action == "add":
                if e.agent_id not in holders:
                    errors.append(f"task '{n}': the joining worker '{e.agent_id}' fails its own gate")
                extra = sorted(holders - {e.agent_id})
                if extra:
                    errors.append(f"task '{n}': gate does not discriminate, {extra} also pass without being the joining worker")
            else:
                if e.agent_id not in holders:
                    errors.append(f"task '{n}': the leaving worker '{e.agent_id}' fails the gate, so its leave changes nothing")
                if not (holders - {e.agent_id}) & alive:
                    errors.append(f"task '{n}': no worker remaining after t={e.timestep} passes, so the task cannot be completed")
            now = sorted(holders & alive)
            derived[n] = now
            want = spec.correct_agents.get(n)
            if want is not None and set(want) != set(now):
                errors.append(f"task '{n}': correct_agents is {sorted(want)} but gate validation derives {now}")
    return errors, derived


def gate_validate(
    lay: Layout,
    name: str,
    generate: Generate | None,
    model: str = DEFAULT_GATE_MODEL,
    jobs: int = 4,
    force: bool = False,
) -> tuple[list[str], dict[str, list[str]], dict[str, Any]]:
    """Generate (when `generate` is given), score and judge. Writes gate_validation/table.json.

    Saved replies are reused when the worker prompt, task and model are unchanged. With
    `generate=None` only saved replies are used and a missing one is an error.
    """
    from manager_agent_gym.core.evaluation.task_requirements_evaluator import flatten_tasks, score_checklist

    _, workflow, timeline, spec = _load_scenario(lay, name)
    changes = _timeline_changes(timeline)
    workers = _worker_configs(changes)
    by_name = {t.name: t for t in flatten_tasks(workflow.tasks.values())}
    eligible = gate_workers(spec, changes)
    task_names = sorted(n for n in eligible if n in by_name)
    out_dir = _gate_dir(lay, name) / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    def reply_for(task_name: str, wid: str) -> dict[str, Any]:
        system, user = _worker_prompts(by_name[task_name], workers[wid])
        key = _cell_key(system, user, model)
        path = out_dir / f"{_slug(task_name)}__{wid}.json"
        if path.exists() and not force:
            saved = json.loads(path.read_text())
            if saved.get("key") == key:
                return {"key": key, "output": saved["output"]}
        if generate is None:
            return {"key": key, "error": "no saved reply (run gate-run to generate it)"}
        try:
            output = generate(system, user, model)
        except Exception as e:  # noqa: BLE001 - one failed cell must not stop the rest
            return {"key": key, "error": f"{type(e).__name__}: {e}"}
        path.write_text(json.dumps({"key": key, "model": model, "output": output}, indent=2))
        return {"key": key, "output": output}

    pairs = [(t, w) for t in task_names for w in eligible[t] if w in workers]
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        replies = list(pool.map(lambda tw: reply_for(*tw), pairs))

    cells: dict[str, dict[str, dict]] = {t: {} for t in task_names}
    for (t, w), r in zip(pairs, replies):
        if "error" in r:
            cells[t][w] = {"key": r["key"], "error": r["error"]}
            continue
        res = score_checklist(by_name[t].requirements, r["output"])
        cells[t][w] = {
            "key": r["key"],
            "passed": not res.failed_keys,
            "score": res.passed / res.total if res.total else 0.0,
            "failed": list(res.failed_keys),
        }
    errors, derived = gate_verdict(spec, changes, cells)
    table = {
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cells": cells,
        "derived_correct_agents": derived,
        "errors": errors,
    }
    (_gate_dir(lay, name) / GATE_TABLE).write_text(json.dumps(table, indent=2) + "\n")
    return errors, derived, table


def _print_gate(table: dict[str, Any], derived: dict[str, list[str]], errors: list[str]) -> None:
    for task, row in table["cells"].items():
        passing = sorted(w for w, c in row.items() if c.get("passed"))
        broken = sorted(w for w, c in row.items() if "error" in c)
        print(f"{task}\n  passes: {passing or 'nobody'} ({len(row) - len(passing) - len(broken)} fail"
              f"{f', {len(broken)} no reply' if broken else ''})")
    print("\nderived correct_agents (workers that pass and are on the roster after the event):")
    for task, workers in derived.items():
        print(f"  {task!r}: frozenset({set(workers)!r})")
    for e in errors:
        print(f"ERROR: {e}")
    print("GATE OK" if not errors else f"{len(errors)} gate error(s)")


def cmd_gate(lay: Layout, name: str, run: bool, model: str, jobs: int, force: bool) -> int:
    _require_source(lay, name)
    if not run:  # rescoring: keep the model the saved replies were generated with
        model = (_read_gate_table(lay, name) or {}).get("model", model)
    errors, derived, table = gate_validate(lay, name, claude_generate if run else None, model, jobs, force)
    _print_gate(table, derived, errors)
    return 1 if errors else 0


def cmd_check(lay: Layout, name: str) -> int:
    _require_source(lay, name)
    errors, warnings = check_scenario(lay, name)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").add_argument("names", nargs="*")
    for c in ("plan", "reset", "check", "stamp"):
        sub.add_parser(c).add_argument("name")
    for c in ("gate-run", "gate-score"):
        g = sub.add_parser(c)
        g.add_argument("name")
        if c == "gate-run":
            g.add_argument("--model", default=DEFAULT_GATE_MODEL, help="Claude model alias or id (default: sonnet)")
            g.add_argument("--jobs", type=int, default=4, help="parallel Claude calls (default: 4)")
            g.add_argument("--enable", action="store_true", help="required: gate validation is deferred because it costs one Claude call per task per worker")
            g.add_argument("--force", action="store_true", help="regenerate replies even if saved ones are current")
    args = ap.parse_args(argv)
    lay = Layout()
    if args.cmd == "status":
        return cmd_status(lay, args.names)
    if args.cmd == "gate-run":
        if not args.enable:
            print("gate-run is deferred: correct_agents is set by judgment. Pass --enable to run it (one Claude call per affected task per worker).")
            return 2
        return cmd_gate(lay, args.name, True, args.model, args.jobs, args.force)
    if args.cmd == "gate-score":
        return cmd_gate(lay, args.name, False, DEFAULT_GATE_MODEL, 1, False)
    return {"plan": cmd_plan, "reset": cmd_reset, "check": cmd_check, "stamp": cmd_stamp}[args.cmd](lay, args.name)


if __name__ == "__main__":
    raise SystemExit(main())
