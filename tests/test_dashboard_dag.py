"""Tests for the dashboard's scenario-diff logic (dashboard/server/dag.py)."""

from dashboard.server import dag


def task(desc="d", reqs=(), subtasks=0):
    return {"description": desc, "requirements": list(reqs), "subtask_count": subtasks}


def graphs(monkeypatch, before, after):
    monkeypatch.setattr(dag, "load_graph", lambda sid: {"b": before, "a": after}[sid])


def test_identical_scenarios_have_no_differences(monkeypatch):
    g = {"tasks": {"A": task(), "B": task()}, "edges": [("A", "B")]}
    graphs(monkeypatch, g, g)
    assert dag.diff("b", "a")["counts"] == {"added": 0, "removed": 0, "changed": 0, "unchanged": 2}


def test_renamed_task_is_removed_plus_added_and_dependent_is_changed(monkeypatch):
    before = {"tasks": {"A": task(), "B": task()}, "edges": [("A", "B")]}
    after = {"tasks": {"A2": task(), "B": task()}, "edges": [("A2", "B")]}
    graphs(monkeypatch, before, after)
    d = dag.diff("b", "a")
    status = {n["id"]: (n["status"], n["changed_fields"]) for n in d["nodes"]}
    assert status["A"][0] == "removed" and status["A2"][0] == "added"
    assert status["B"] == ("changed", ["dependencies"])
    edges = {(e["source"], e["target"]): e["status"] for e in d["edges"]}
    assert edges == {("A", "B"): "removed", ("A2", "B"): "added"}


def test_checklist_and_description_changes_are_flagged(monkeypatch):
    before = {"tasks": {"A": task("old")}, "edges": []}
    after = {"tasks": {"A": task("new", reqs=["k"])}, "edges": []}
    graphs(monkeypatch, before, after)
    node = dag.diff("b", "a")["nodes"][0]
    assert node["status"] == "changed"
    assert set(node["changed_fields"]) == {"description", "requirements"}
    assert (node["requirements_before"], node["requirements_after"]) == (0, 1)


def test_layout_places_dependencies_in_earlier_layers():
    pos = dag._layout(["A", "B", "C"], [("A", "B"), ("B", "C")])
    assert pos["A"][0] < pos["B"][0] < pos["C"][0]


def test_unknown_or_unsafe_scenario_ids_are_rejected():
    import pytest

    for bad in ("nope/x", "end_to_end_examples/../x", "end_to_end_examples"):
        with pytest.raises(KeyError):
            dag._load_workflow(bad)
