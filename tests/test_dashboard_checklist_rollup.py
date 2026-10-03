"""The dashboard's checklist DAG scores a decomposed task on its subtasks' combined output."""

import json

from dashboard.server import data


def task(id, name, outs=(), reqs=(), subtasks=(), parent=None, status="completed"):
    return {
        "id": id, "name": name, "status": status, "assigned_agent_id": None, "parent_task_id": parent,
        "output_resource_ids": list(outs), "subtasks": list(subtasks), "dependency_task_ids": [],
        "requirements": [{"key": k, "pattern": p, "description": "d"} for k, p in reqs],
    }


def write_run(tmp_path, monkeypatch):
    b1 = task("B1", "B1", ["r1"], subtasks=[])
    b2 = task("B2", "B2", ["r2"], subtasks=[])
    parent = task("B", "Negotiation", [], reqs=[("hdr", "FMT-V2"), ("topic", "redline")], subtasks=[b1, b2])
    snap = {
        "timestep": 5,
        # the engine lists every subtask as a top-level task of its own as well
        "tasks": {"B": parent, "B1": {**b1, "parent_task_id": "B"}, "B2": {**b2, "parent_task_id": "B"}},
        "resources": {"r1": {"name": "memo", "content": "FMT-V2 header"}, "r2": {"name": "log", "content": "the redline log"}},
    }
    wo = tmp_path / "cot" / "wf_team" / "run_seed_1" / "workflow_outputs"
    wo.mkdir(parents=True)
    (wo / "workflow_execution_seed_1_t0005.json").write_text(json.dumps(snap))
    monkeypatch.setattr(data, "OUT_ROOT", tmp_path)


def test_decomposed_parent_passes_on_the_combined_subtask_output(tmp_path, monkeypatch):
    write_run(tmp_path, monkeypatch)
    dag = data.checklist_dag("wf_team", "cot", "run_seed_1")
    node = next(n for n in dag["nodes"] if n["id"] == "Negotiation")
    assert node["scores"][5]["passed"] == 2 and node["scores"][5]["total"] == 2  # was 0/2: parent has no output


def test_task_detail_marks_the_checklist_as_scored_on_subtasks(tmp_path, monkeypatch):
    write_run(tmp_path, monkeypatch)
    detail = data.checklist_task_detail("wf_team", "cot", "run_seed_1", "Negotiation", 5)
    part = next(p for p in detail["parts"] if p["task"] == "Negotiation")
    assert all(r["passed"] for r in part["requirements"]) and part["scored_on_subtasks"] is True
