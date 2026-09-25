# Task Requirements Checklist: Worked Example

Companion to `open_aht_benchmark_plan_prev.md` §3.2/§4. That doc describes the
`Task.requirements` mechanism at a design level; this doc traces one concrete task through
every layer — schema, per-item grading, aggregation, wiring — using the real MA-Gym classes
plus the proposed additions, so the connections between them are unambiguous before any code
is written.

## Worked example

```python
# 1. On the Task itself (proposed addition, schemas/core/tasks.py)
task = Task(
    name="IP & Privacy Compliance Review",
    requirements=[
        TaskRequirement(key="id_verification_flow", description="...", check="deterministic"),
        TaskRequirement(key="retention_clause_cited", description="...", check="llm_classifier"),
    ],
    requirements_pass_threshold=2,   # both must pass
)

# 2. One WorkflowRubric PER requirement item (real class, schemas/preferences/rubric.py)
#    — deterministic and llm_classifier items can't share a rubric, so each gets its own.
def check_id_verification(workflow, context) -> tuple[float, str]:
    t = workflow.tasks[task.id]                     # exact task_id lookup, no name matching
    outputs = [workflow.resources[rid] for rid in t.output_resource_ids]
    passed = any("identity_verification" in r.content for r in outputs)
    return (1.0 if passed else 0.0), "checked output resources for id-verification flow"

rubric_1 = WorkflowRubric(
    name=f"{task.id}::id_verification_flow",
    evaluator_function=check_id_verification,        # deterministic path
    max_score=1.0,
    run_condition=RunCondition.ON_COMPLETION,
)
rubric_2 = WorkflowRubric(
    name=f"{task.id}::retention_clause_cited",
    llm_prompt="Does the output cite a data-retention clause? Answer 1 if yes, 0 if no.",
    max_score=1.0,                                   # llm_classifier path — narrow yes/no, not open scoring
    run_condition=RunCondition.ON_COMPLETION,
)

# 3. Custom aggregation (same pattern as hard_zero_agg in constraint_evaluator.py)
def requirements_pass_agg(scores, rubrics, workflow=None, context=None) -> float:
    passed = sum(1 for s in scores if s >= 1.0)
    return 1.0 if passed >= task.requirements_pass_threshold else 0.0

# 4. Evaluator (real class, schemas/preferences/evaluator.py) wraps them
evaluator = Evaluator(
    name=f"requirements::{task.id}",
    aggregation=requirements_pass_agg,               # binary, not weighted average
    rubrics=[rubric_1, rubric_2],
)

# 5. Wiring (proposed: common_evaluators.py) — one such Evaluator per task that sets `requirements`
def build_default_evaluators(workflow):
    evaluators = [build_constraint_evaluator(), build_stakeholder_evaluator(), ...]
    for t in workflow.tasks.values():
        if t.requirements:
            evaluators.append(build_requirements_evaluator(t))   # generates rubrics 1-3 above
    return evaluators
```

## Key connection points

- **`Task.requirements` never reaches the manager.** `ManagerObservation` does not carry it —
  unlike `Constraint`, which is fed straight into `ManagerObservation.constraints` every step
  (`manager_agent_gym/core/manager_agent/interface.py:158`). That's the specific reason the
  checklist lives on `Task`, not on `Constraint`: anything in `Constraint.metadata` would leak
  the grading criteria to the agent under test.
- **One rubric per checklist item, not one per task.** A `WorkflowRubric` takes exactly one of
  `evaluator_function` or `llm_prompt` (`schemas/preferences/rubric.py:33-46`) — it can't mix
  both within itself. Since `TaskRequirement.check` picks between `"deterministic"` and
  `"llm_classifier"` per item, each item becomes its own `WorkflowRubric`.
- **Exact task lookup, not name matching.** `check_id_verification` closes over `task.id` and
  indexes `workflow.tasks[task.id]` directly. This is what `Constraint.applicable_task_types`
  can't do — it matches by substring on `task.name` (`core/evaluation/constraint_evaluator.py:33`),
  which breaks the moment two tasks are deliberately similarly named (exactly the Objective 1
  setup).
- **The aggregation function is what turns "N/M items passed" into a binary signal.** It plays
  the same role `hard_zero_agg` plays for `constraint_adherence`
  (`core/evaluation/constraint_evaluator.py:186-200`) — counting instead of averaging. This is
  also where `requirements_pass_threshold` actually gets enforced; the rubrics themselves just
  report each item's 0/1.
- **Wiring is additive, but needs one signature change.** `build_default_evaluators()`
  (`common_evaluators.py:11`) currently takes only `communication_service` — it has no
  `workflow` parameter and so no way to loop over `workflow.tasks` today. That has to be added
  so it can append a requirements-evaluator per task that sets `requirements`; every existing
  scenario's evaluator list, and every task without a checklist, stays untouched either way.
  It has exactly one call site (`examples/run_examples.py:170-172`), where `workflow` is
  already in scope, so the change is small and low-risk.

## Does an LLM decide whether requirements are fulfilled?

Depends on the item's `check` mode, and even then it's narrow:

- **`check="deterministic"`** → plain Python (`evaluator_function`). No LLM involved at all.
- **`check="llm_classifier"`** → yes, an LLM is involved, via `WorkflowRubric.llm_prompt`. The
  actual executor behind `llm_prompt` is `_llm_validate` in
  `core/evaluation/validation_rules.py:161-210`, and it explicitly supports a plain
  `boolean (true/false)` output type (line 184), not just the 0–10 partial-credit scoring MA-Gym
  uses for its open-ended quality rubrics elsewhere. So an `llm_classifier` item is a narrow
  yes/no question scoped to one fact about the task's output ("does it cite X?") — not an
  open-ended judgment call, and it uses the same LLM-judge infrastructure already in the
  codebase, not a new mechanism.

Either way, **no LLM ever decides "was the right agent assigned."** That inference is a
byproduct of the binary aggregation step (§ counting passes vs. `requirements_pass_threshold`),
which is always plain code — consistent with the "no gold label, fit is demonstrated not
asserted" design in `open_aht_benchmark_plan_prev.md`.
