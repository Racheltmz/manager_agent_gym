"""Tests for scripts/team_benchmark.py, the helper behind the create-team-benchmark skill."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "team_benchmark.py"
spec = importlib.util.spec_from_file_location("team_benchmark_tool", TOOL_PATH)
tool = importlib.util.module_from_spec(spec)
sys.modules["team_benchmark_tool"] = tool  # dataclasses look the module up by name
spec.loader.exec_module(tool)

@pytest.fixture(autouse=True)
def isolated_imports():
    """Each test builds its own scenario packages; keep one test's tmp root from leaking into the next."""
    saved = list(sys.path)
    yield
    sys.path[:] = saved
    for m in [m for m in sys.modules if m.split(".")[0] in ("fake_team_pkg", "src_scenarios")]:
        del sys.modules[m]


BENCHMARK_MD = """# Benchmark
## 3. Change-affected cases
| Case | Setup | Fixed best action |
|---|---|---|
| **Specialist worker** | x | y |
| **Running task** | x | y |

## 4. Event types
"""

WORKFLOW_PY = '''
from manager_agent_gym.schemas.core.tasks import Task, TaskRequirement
from types import SimpleNamespace

def req(key, pat="OK"):
    return [TaskRequirement(key=key, description="d", pattern=pat)]

def create_workflow():
    tasks = [
        Task(name="Gated join task", description="d", requirements=req("g")),
        Task(name="Gated leave task", description="d", requirements=req("l")),
        Task(name="Control task", description="d", requirements=req("c")),
    ]
    __EXTRA_TASK__
    parent = Task(name="Composite parent", description="d", subtasks=[Task(name="Leaf child", description="d", requirements=req("k"))])
    tasks.append(parent)
    return SimpleNamespace(tasks={t.id: t for t in tasks})
'''

TEAM_PY = '''
from manager_agent_gym.schemas.workflow_agents import AIAgentConfig, HumanAgentConfig

def ai(aid):
    return AIAgentConfig(agent_id=aid, system_prompt=f"Worker {aid}: a prompt long enough.",
                         agent_description="d", agent_capabilities=["c"])

def create_team_timeline():
    return {
        0: [("add", ai("w1"), "initial roster"), ("add", ai("w2"), "initial roster")],
        3: [("add", ai("w3"), "__JOIN_REASON__")],
        6: [("remove", "w1", "scale in: pool shrinks")],
    }
'''

SPEC_PY = '''
from manager_agent_gym.core.evaluation.team_change_metrics import TeamChangeEvent, TeamChangeSpec

def create_team_change_spec():
    return TeamChangeSpec(
        events=(
            TeamChangeEvent(3, "add", "w3", ("Gated join task",)),
            TeamChangeEvent(6, "remove", "w1", ("Gated leave task",)),
        ),
        correct_agents={"Gated join task": frozenset({"w3"}), "Gated leave task": frozenset({"w2"})},
        cases={"Gated join task": "specialist"},
    )
'''

INIT_PY = """
from .workflow import create_workflow
from .team import create_team_timeline
"""


def make_repo(tmp_path, *, with_scenario=True, join_reason="scale out: pool grows", extra_task="", spec_py=SPEC_PY):
    root = tmp_path
    (root / "docs/team_non_stationarity").mkdir(parents=True)
    (root / "docs/team_non_stationarity/benchmark.md").write_text(BENCHMARK_MD)
    (root / "docs/team_non_stationarity/metrics.md").write_text("# Metrics\n")
    (root / ".claude/skills/create-team-benchmark").mkdir(parents=True)
    (root / ".claude/skills/create-team-benchmark/SKILL.md").write_text("skill v1\n")
    src = root / "src_scenarios" / "wf1"
    src.mkdir(parents=True)
    (src / "workflow.py").write_text("# original\n")
    (root / "src_scenarios" / "wf0").mkdir()
    (root / "src_scenarios" / "wf0" / "workflow.py").write_text("# other\n")
    lay = tool.Layout(root=root, source_dir="src_scenarios", team_dir="fake_team_pkg")
    if with_scenario:
        pkg = root / "fake_team_pkg"
        (pkg / "wf1").mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "wf1/__init__.py").write_text(INIT_PY)
        (pkg / "wf1/workflow.py").write_text(WORKFLOW_PY.replace("__EXTRA_TASK__", extra_task))
        (pkg / "wf1/team.py").write_text(TEAM_PY.replace("__JOIN_REASON__", join_reason))
        (pkg / "wf1/team_change_spec.py").write_text(spec_py)
    return lay


# ---- status / stamp / reset ----------------------------------------------------------


def test_missing_scenario_is_reported_missing(tmp_path):
    lay = make_repo(tmp_path, with_scenario=False)
    assert tool.scenario_status(lay, "wf1")["state"] == "missing"


def test_scenario_without_stamp_is_unstamped(tmp_path):
    lay = make_repo(tmp_path)
    assert tool.scenario_status(lay, "wf1")["state"] == "unstamped"


def test_stamp_makes_it_current_and_each_input_change_makes_it_stale(tmp_path):
    lay = make_repo(tmp_path)
    tool.cmd_stamp(lay, "wf1")
    assert tool.scenario_status(lay, "wf1")["state"] == "current"

    (tmp_path / "docs/team_non_stationarity/benchmark.md").write_text(BENCHMARK_MD + "\nnew rule\n")
    st = tool.scenario_status(lay, "wf1")
    assert st["state"] == "stale" and "docs/team_non_stationarity/benchmark.md changed" in st["reasons"]

    tool.cmd_stamp(lay, "wf1")
    (tmp_path / ".claude/skills/create-team-benchmark/SKILL.md").write_text("skill v2\n")
    assert "SKILL.md changed" in " ".join(tool.scenario_status(lay, "wf1")["reasons"])

    tool.cmd_stamp(lay, "wf1")
    (tmp_path / "src_scenarios/wf1/workflow.py").write_text("# original, edited\n")
    assert any("wf1 changed" in r for r in tool.scenario_status(lay, "wf1")["reasons"])


def test_status_of_one_scenario_does_not_depend_on_another(tmp_path):
    lay = make_repo(tmp_path)
    tool.cmd_stamp(lay, "wf1")
    (tmp_path / "src_scenarios/wf0/workflow.py").write_text("# changed\n")
    assert tool.scenario_status(lay, "wf1")["state"] == "current"


def test_reset_deletes_the_scenario_but_keeps_a_backup(tmp_path, capsys):
    lay = make_repo(tmp_path)
    tool.cmd_reset(lay, "wf1")
    assert not (tmp_path / "fake_team_pkg/wf1").exists()
    out = capsys.readouterr().out
    backup = Path(out.split("backup: ")[1].strip().rstrip(")"))
    assert (backup / "team.py").exists()
    assert (tmp_path / "fake_team_pkg/__init__.py").exists()  # parent package kept for the rerun


def test_reset_leaves_other_scenarios_alone(tmp_path):
    lay = make_repo(tmp_path)
    other = tmp_path / "fake_team_pkg/wf0"
    other.mkdir()
    (other / "workflow.py").write_text("x")
    tool.cmd_reset(lay, "wf1")
    assert (other / "workflow.py").exists()


def test_unknown_or_unsafe_names_are_rejected(tmp_path):
    lay = make_repo(tmp_path)
    for bad in ("nope", "../wf1", "wf1/.."):
        with pytest.raises(SystemExit):
            tool.cmd_reset(lay, bad)


def test_plan_gives_a_stable_rotation_index(tmp_path, capsys):
    lay = make_repo(tmp_path)
    tool.cmd_plan(lay, "wf1")
    plan = json.loads(capsys.readouterr().out)
    assert plan["rotation_index"] == 1 and plan["workflow_count"] == 2  # wf0, wf1 sorted


# ---- check ---------------------------------------------------------------------------


def test_valid_scenario_passes(tmp_path):
    errors, warnings = tool.check_scenario(make_repo(tmp_path), "wf1")
    assert errors == []
    assert any("leave timing is not checked" in w for w in warnings)


def test_human_agent_is_an_error(tmp_path):
    lay = make_repo(tmp_path)
    team = tmp_path / "fake_team_pkg/wf1/team.py"
    team.write_text(team.read_text().replace(
        'ai("w2")', 'HumanAgentConfig(agent_id="w2", system_prompt="A human prompt long enough.", '
        'agent_description="d", agent_capabilities=["c"], name="n", role="r")'))
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("HumanAgentConfig" in e for e in errors)


def test_reason_naming_the_task_is_an_error(tmp_path):
    lay = make_repo(tmp_path, join_reason="scale out for Gated join task")
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("names task" in e for e in errors)


def test_affected_task_missing_from_workflow_is_an_error(tmp_path):
    lay = make_repo(tmp_path, spec_py=SPEC_PY.replace('("Gated join task",))', '("Nope",))', 1))
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("'Nope' is not in the workflow" in e for e in errors)


def test_affected_task_without_pattern_is_an_error(tmp_path):
    lay = make_repo(tmp_path)
    wf = tmp_path / "fake_team_pkg/wf1/workflow.py"
    wf.write_text(wf.read_text().replace('requirements=req("g")', "requirements=[TaskRequirement(key='g', description='prose only')]"))
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("every item has a pattern" in e for e in errors)


def test_join_task_without_a_valid_case_is_an_error(tmp_path):
    lay = make_repo(tmp_path, spec_py=SPEC_PY.replace('cases={"Gated join task": "specialist"}', "cases={}"))
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("needs a case" in e for e in errors)


def test_correct_worker_that_leaves_is_an_error(tmp_path):
    lay = make_repo(tmp_path, spec_py=SPEC_PY.replace('frozenset({"w2"})', 'frozenset({"w1"})'))
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("leaving worker" in e or "not on the roster" in e for e in errors)


def test_timeline_change_missing_from_spec_is_an_error(tmp_path):
    spec = SPEC_PY.replace('            TeamChangeEvent(6, "remove", "w1", ("Gated leave task",)),\n', "")
    lay = make_repo(tmp_path, spec_py=spec)
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("has no event in team_change_spec" in e for e in errors)
    assert any("no leave event" in e for e in errors)


def test_leaver_pre_assigned_to_a_task_is_an_error(tmp_path):
    lay = make_repo(tmp_path, extra_task='tasks[2].assigned_agent_id = "w1"')
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("pre-assigned" in e for e in errors)


def test_every_task_affected_leaves_no_control(tmp_path):
    spec = SPEC_PY.replace('("Gated leave task",))', '("Gated leave task", "Control task"))')
    spec = spec.replace('frozenset({"w3"}), "Gated leave', 'frozenset({"w3"}), "Control task": frozenset({"w2"}), "Gated leave')
    lay = make_repo(tmp_path, spec_py=spec)
    wf = tmp_path / "fake_team_pkg/wf1/workflow.py"  # drop the extra composite task, leaving only three
    wf.write_text("\n".join(l for l in wf.read_text().splitlines() if "Composite parent" not in l and "tasks.append(parent)" not in l))
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any("no control tasks" in e for e in errors)


def test_doc_listing_a_new_case_warns_that_the_tool_is_out_of_date(tmp_path):
    lay = make_repo(tmp_path)
    doc = tmp_path / "docs/team_non_stationarity/benchmark.md"
    doc.write_text(doc.read_text().replace("| **Running task** | x | y |", "| **Running task** | x | y |\n| **Split or merge** | x | y |"))
    _, warnings = tool.check_scenario(lay, "wf1")
    assert any("update KNOWN_CASES" in w for w in warnings)


def test_a_scenario_that_does_not_load_reports_one_clear_error(tmp_path):
    lay = make_repo(tmp_path)
    (tmp_path / "fake_team_pkg/wf1/team.py").write_text("raise RuntimeError('boom')\n")
    errors, _ = tool.check_scenario(lay, "wf1")
    assert len(errors) == 1 and "cannot load scenario" in errors[0] and "boom" in errors[0]


def test_a_subtask_can_be_an_affected_task(tmp_path):
    spec = SPEC_PY.replace('("Gated leave task",))', '("Leaf child",))').replace(
        '"Gated leave task": frozenset({"w2"})', '"Leaf child": frozenset({"w2"})')
    errors, _ = tool.check_scenario(make_repo(tmp_path, spec_py=spec), "wf1")
    assert errors == []


def test_a_composite_task_cannot_be_affected(tmp_path):
    spec = SPEC_PY.replace('("Gated leave task",))', '("Composite parent",))').replace(
        '"Gated leave task": frozenset({"w2"})', '"Composite parent": frozenset({"w2"})')
    wf_fix = make_repo(tmp_path, spec_py=spec)
    wf = tmp_path / "fake_team_pkg/wf1/workflow.py"
    wf.write_text(wf.read_text().replace('Task(name="Composite parent", description="d",',
                                         'Task(name="Composite parent", description="d", requirements=req("p"),'))
    errors, _ = tool.check_scenario(wf_fix, "wf1")
    assert any("is composite" in e for e in errors)


# ---- gate validation -----------------------------------------------------------------


def fake_claude(holders_by_task, calls=None):
    """Stand-in for claude_generate: a worker passes a task if its id is in that task's holders."""

    def generate(system, user, model):
        if calls is not None:
            calls.append((system, user, model))
        for task, holders in holders_by_task.items():
            if task in user:
                return "OK" if any(f"Worker {w}:" in system for w in holders) else "nope"
        return "nope"

    return generate


GOOD = {"Gated join task": {"w3"}, "Gated leave task": {"w1", "w2"}}


def run_gate(tmp_path, holders=GOOD, **kw):
    lay = make_repo(tmp_path)
    errors, derived, table = tool.gate_validate(lay, "wf1", fake_claude(holders), **kw)
    return lay, errors, derived, table


def test_gate_passes_and_derives_the_mapping(tmp_path):
    lay, errors, derived, table = run_gate(tmp_path)
    assert errors == []
    assert derived == {"Gated join task": ["w3"], "Gated leave task": ["w2"]}  # leaver w1 is off the roster
    assert (tool._gate_dir(lay, "wf1") / "table.json").exists()
    assert table["cells"]["Gated join task"]["w3"]["passed"] is True
    assert table["cells"]["Gated join task"]["w2"]["passed"] is False


def test_gate_that_other_workers_also_pass_is_an_error(tmp_path):
    _, errors, _, _ = run_gate(tmp_path, {**GOOD, "Gated join task": {"w3", "w2"}})
    assert any("does not discriminate" in e and "w2" in e for e in errors)


def test_joining_worker_that_fails_its_own_gate_is_an_error(tmp_path):
    _, errors, _, _ = run_gate(tmp_path, {**GOOD, "Gated join task": {"w2"}})
    assert any("fails its own gate" in e for e in errors)


def test_leaver_that_does_not_hold_the_content_is_an_error(tmp_path):
    _, errors, _, _ = run_gate(tmp_path, {**GOOD, "Gated leave task": {"w2"}})
    assert any("leaving worker 'w1' fails the gate" in e for e in errors)


def test_leave_task_nobody_remaining_can_pass_is_an_error(tmp_path):
    _, errors, _, _ = run_gate(tmp_path, {**GOOD, "Gated leave task": {"w1"}})
    assert any("cannot be completed" in e for e in errors)


def test_spec_that_disagrees_with_the_derived_mapping_is_an_error(tmp_path):
    _, errors, derived, _ = run_gate(tmp_path, {**GOOD, "Gated leave task": {"w1", "w2", "w3"}})
    assert derived["Gated leave task"] == ["w2", "w3"]
    assert any("correct_agents is ['w2'] but gate validation derives ['w2', 'w3']" in e for e in errors)


def test_a_failed_generation_is_an_error_not_a_fail(tmp_path):
    lay = make_repo(tmp_path)

    def broken(system, user, model):
        raise RuntimeError("boom")

    errors, _, table = tool.gate_validate(lay, "wf1", broken)
    assert any("no reply" in e for e in errors)
    assert "error" in table["cells"]["Gated join task"]["w1"]


def test_saved_replies_are_reused_until_the_worker_prompt_changes(tmp_path):
    lay = make_repo(tmp_path)
    calls: list = []
    tool.gate_validate(lay, "wf1", fake_claude(GOOD, calls))
    first = len(calls)
    assert first == 3 * 2  # 3 workers x 2 affected tasks
    tool.gate_validate(lay, "wf1", fake_claude(GOOD, calls))
    assert len(calls) == first
    team = tmp_path / "fake_team_pkg/wf1/team.py"
    team.write_text(team.read_text().replace("Worker {aid}:", "Changed {aid}:"))
    tool.gate_validate(lay, "wf1", fake_claude(GOOD, calls))
    assert len(calls) == first + 3 * 2  # every worker prompt changed, so all replies regenerate


def test_rescoring_without_a_generator_uses_saved_replies_only(tmp_path):
    lay, *_ = run_gate(tmp_path)
    errors, _, _ = tool.gate_validate(lay, "wf1", None)
    assert errors == []
    empty = make_repo(tmp_path / "other")
    errors, _, _ = tool.gate_validate(empty, "wf1", None)
    assert any("no reply" in e for e in errors)


def test_gate_run_is_deferred_unless_enabled(tmp_path, capsys):
    make_repo(tmp_path)
    assert tool.main(["gate-run", "wf1"]) == 2
    assert "deferred" in capsys.readouterr().out


def test_check_warns_when_gate_validation_has_not_run_and_errors_when_it_failed(tmp_path):
    lay = make_repo(tmp_path)
    errors, warnings = tool.check_scenario(lay, "wf1")
    assert errors == [] and any("gate validation is deferred" in w for w in warnings)
    tool.gate_validate(lay, "wf1", fake_claude({**GOOD, "Gated join task": {"w3", "w2"}}))
    errors, _ = tool.check_scenario(lay, "wf1")
    assert any(e.startswith("gate validation:") and "does not discriminate" in e for e in errors)


def test_check_flags_a_stale_gate_table(tmp_path):
    lay, *_ = run_gate(tmp_path)
    errors, warnings = tool.check_scenario(lay, "wf1")
    assert errors == [] and not any("stale" in w for w in warnings)
    team = tmp_path / "fake_team_pkg/wf1/team.py"
    team.write_text(team.read_text().replace("Worker {aid}:", "Changed {aid}:"))
    _, warnings = tool.check_scenario(lay, "wf1")
    assert any("gate validation table is stale" in w for w in warnings)


# ---- event count against the source ----------------------------------------------------

SOURCE_TEAM_PY = """
def create_team_timeline():
    return {
        0: [("add", "a", "r"), ("add", "b", "r")],
        2: [("add", "c", "r"), ("add", "a", "re-add of a worker already on the roster")],
        5: [("remove", "b", "r"), ("add", "d", "r")],
    }
"""


def test_source_midrun_changes_counts_joins_and_leaves_but_not_re_adds(tmp_path):
    lay = make_repo(tmp_path)
    src = tmp_path / "src_scenarios" / "wf1"
    (src / "__init__.py").write_text("from .team import create_team_timeline\n")
    (src / "team.py").write_text(SOURCE_TEAM_PY)
    assert tool.source_midrun_changes(lay, "wf1") == 3  # add c, remove b, add d
    errors, warnings = tool.check_scenario(lay, "wf1")
    assert errors == []
    assert any("2 change event(s) against 3" in w for w in warnings)


def test_source_without_a_timeline_has_no_count_and_no_warning(tmp_path):
    lay = make_repo(tmp_path)
    assert tool.source_midrun_changes(lay, "wf1") is None
    _, warnings = tool.check_scenario(lay, "wf1")
    assert not any("against" in w for w in warnings)


# ---- which workers gate validation tests -----------------------------------------------


def test_gate_workers_are_the_ones_that_can_receive_the_task():
    from types import SimpleNamespace as NS

    changes = [
        (0, "add", "a", None, ""), (0, "add", "b", None, ""), (0, "add", "x", None, ""),
        (2, "remove", "x", None, ""),   # left before the event: never tested
        (5, "add", "j", None, ""),      # the event: joiner
        (5, "remove", "b", None, ""),   # the event: leaver is tested for the leave rule
        (8, "add", "late", None, ""),   # joins after the event: the manager can still assign to it
    ]
    spec = NS(events=[NS(timestep=5, action="add", agent_id="j", affected_tasks=("T",)),
                      NS(timestep=5, action="remove", agent_id="b", affected_tasks=("U",))])
    got = tool.gate_workers(spec, changes)
    assert got["T"] == ["a", "j", "late"]
    assert got["U"] == ["a", "b", "j", "late"]
    assert "x" not in got["T"] + got["U"]


def test_gate_only_calls_workers_that_can_receive_each_task(tmp_path):
    lay = make_repo(tmp_path)
    seen: list = []
    tool.gate_validate(lay, "wf1", fake_claude(GOOD, seen))
    # join at 3: w1,w2,w3 can receive it; leave at 6: w2,w3 remain, w1 is the tested leaver
    assert len(seen) == 6
