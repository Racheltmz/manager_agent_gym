"""Tests for the dashboard's scenario-diff logic (dashboard/server/compare.py, workflow view)."""

from dashboard.server.compare import WorkflowData, workflow_view


def task(name, desc="d", items=(), subtasks=0):
    items = [{"key": k, "pattern": None} for k in items]
    return {
        "name": name,
        "description": desc,
        "subtask_count": subtasks,
        "requirements": [i["key"] for i in items],
        "requirement_items": items,
        "covers": [name],
    }


def wf(tasks, edges=()):
    return WorkflowData(tasks={t["name"]: t for t in tasks}, edges=list(edges))


def statuses(d):
    """node id -> (status on the before pane, status on the after pane)."""
    before = {n["id"]: n["status"] for n in d["before"]["nodes"]}
    after = {n["id"]: n["status"] for n in d["after"]["nodes"]}
    return {i: (before.get(i), after.get(i)) for i in {*before, *after}}


def changed_rows(d, node):
    return {r["label"] for r in d["details"][node]["rows"] if not r["meta"] and r["before"] != r["after"]}


def test_identical_scenarios_have_no_differences():
    g = wf([task("A"), task("B")], [("A", "B")])
    d = workflow_view(g, g)
    assert d["counts"] == {"added": 0, "removed": 0, "changed": 0, "unchanged": 2}


def test_renamed_task_is_removed_plus_added_and_dependent_is_changed():
    before = wf([task("A"), task("B")], [("A", "B")])
    after = wf([task("A2"), task("B")], [("A2", "B")])
    d = workflow_view(before, after)
    s = statuses(d)
    assert s["A"] == ("removed", None) and s["A2"] == (None, "added")
    assert s["B"] == ("changed", "changed") and changed_rows(d, "B") == {"Dependencies"}
    edges = {side: {(e["source"], e["target"]): e["status"] for e in d[side]["edges"]} for side in ("before", "after")}
    assert edges["before"] == {("A", "B"): "removed"} and edges["after"] == {("A2", "B"): "added"}


def test_checklist_and_description_changes_are_flagged():
    d = workflow_view(wf([task("A", "old")]), wf([task("A", "new", items=["k"])]))
    assert statuses(d)["A"] == ("changed", "changed")
    assert changed_rows(d, "A") == {"Description", "Checklist"}
    assert d["counts"]["changed"] == 1
