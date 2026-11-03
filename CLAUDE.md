# CLAUDE.md

## Project: empirical study of how a manager agent handles mid-workflow changes

Direction is set by `research/Project Proposal.md` (the **editable working copy** of `Project Proposal.pdf`, not final; edit the Markdown, the PDF is a 2026-11-03 snapshot); the
specification of record is `research/decisions.md` (D21 to D28) and `research/preregistration.md`. Summary:

- **Tone:** an **empirical study** run on **MA-Gym's existing benchmarks**. MA-Gym's benchmarks have flaws for this purpose (first establish which, `decisions.md` D28), so they are
  improved by leveraging other peer-reviewed benchmarks (the proposal names REALM-Bench), not replaced or rebuilt.
- **Two core issues with MA-Gym's benchmark** (`decisions.md` D28): (1) no metric measures how well the manager handled a change (workflow-level, mostly LLM-judged scores; no
  unaffected-task control), so the study needs change-specific metrics; (2) no justification for why and when changes are injected (fixed change-points, synthetic scenarios), so the study
  justifies, varies and states assumptions about them (D29: justify and vary, not ground in records). Implementation bugs are not part of these. Questions to ask other benchmarks (REALM-Bench, EntCollabBench, OrchestrationBench) are in D28.
- **Study:** add a layer of mid-workflow changes to that benchmark, run a baseline manager (MA-Gym **CoT**), analyse its
  failures per change type, then test targeted training-free improvements one at a time. Compare against reference conditions (ignore the change, replan from scratch),
  not against other published methods.
- **Change types:** environmental (disruptions such as traffic, road closures, delays; MA-Gym has none of its own), preference (how options are ranked), goal (what counts as success).
- **Research questions:** (1) baseline behaviour and main failure modes per change type; (2) which training-free factors reduce them, for which type (explicit
  continue/repair/replan decision, identifying affected tasks from dependencies, tracking active requirements); (3) dependence on timing and on how much of the remaining
  plan is affected; (4) cost in model calls.
- **Measures:** outcome quality after the change versus the re-solved reference, unnecessary changes to unaffected work, model calls and tokens, repeated runs for variability. Final results on held-out scenarios.
- **Out of scope:** agent unavailability and task changes (future work), error recovery, joins and leaves, comparison with other published methods.
- **Earlier directions are retired** (join/leave teamwork; adaptive replanning under agent loss, with its specialist-loss benchmark). Keep only a line about them in
  the docs. Do not rebuild or extend them unless asked.

Status (2026-11-03): **specification only.** No change layer, no borrowed benchmark elements, scorer or study code exists, and the earlier directions' benchmark packages, scripts, tests and shared-code hooks have been removed (2026-11-03). The aim is the original MA-Gym code plus core logic changes and bug fixes. Do not write study code unless asked. No LLM run until the user's "go".

## Three components, each with one home

Do not create a fourth place for any of them. The code homes are **not chosen yet**: ask before creating a package or folder, then record the choice here.

| Component | What it is | Code | Docs | UPDATES.md table |
|---|---|---|---|---|
| **Benchmark** | MA-Gym's benchmarks (`examples/end_to_end_examples/`), improved with elements of peer-reviewed benchmarks; the change layer (environmental, preference, goal); reference solutions | not yet created | `research/decisions.md` (D22, D23, D28) | Benchmark |
| **Metric** | outcome quality vs the re-solved reference, unnecessary changes, cost, failure taxonomy, analysis | not yet created (reusable now: `core/evaluation/task_requirements_evaluator.py`) | `research/preregistration.md` | Metric |
| **Manager agent** | the frozen CoT baseline, the reference conditions, the targeted improvements | `manager_agent_gym/core/manager_agent/` (existing CoT, Random, Assign-All) | `research/decisions.md` (D24, D25) | Manager agent |

## Where things live

- `research/decisions.md` (design decisions) and `research/preregistration.md` (design, measures, open items, decision rules) are the only docs for this work, with
  `research/problem.md` (problem statement) and `research/Project Proposal.md` (the editable proposal). **Edit them; do not add new documents.** Record a new decision as a new `D<n>` in `decisions.md` (next is D30).
- **All project specs and research notes live in `research/`** (the proposal, as `Project Proposal.md` and a PDF snapshot, `decisions.md`, `preregistration.md`, `problem.md`); `docs/` is the original MA-Gym documentation site.
  `CLAUDE.md` stays at the repo root because Claude Code only loads it from there.
- The repo is upstream MA-Gym plus: the ML-050/052/053 fixes, task checklists (`TaskRequirement`), a no-LLM-judge option, a manager context log, a usage tracker, and the dashboard and run scripts.
  `DEV.md` lists what is left over from the retired directions.
- Commands: `DEV.md`. Running record of changes: `UPDATES.md`. Dashboard features: `dashboard/FEATURES.md`.

## Keep things in step (maintenance)

- **`UPDATES.md`**: whenever you add, change or remove an update (code, scripts, docs, dashboard, a revert), edit it in the same turn, before reporting the work done. Three tables:
  **Manager agent**, **Benchmark**, **Metric** (plus Dashboard). Each row: Update, Files (link files that exist), Purpose, Status (`Done` or `Planned`). Removed work: delete the row.
  Built planned work: `Planned` to `Done`. Verify a row against the working tree (`git diff`) before writing it. Leftover join/leave code is listed in `DEV.md`, not deleted until the user says so.
- **Thresholds have one source** once they exist: a single code module mirrored in `research/preregistration.md`, with a test that fails if they disagree. None are set yet; do not invent them (ask).
- **Shared MA-Gym code is edited only additively**, with the new path inert by default, so existing managers and benchmarks behave as before. Prove it with a test and keep the whole
  suite green: `uv run pytest tests -q`.
- A failing scenario or no-change check means the **scenario or manager setup** is broken, not the finding: fix it before reading any change result.
- Dashboard: `dashboard/` only reads existing files under `dashboard/outputs/` (override `$MAG_OUTPUTS_DIR`). Keep `dashboard/FEATURES.md` in sync the same way as `UPDATES.md`.

## Never spend money without an explicit ask in the user's current message

Not `scripts/run.sh`, `examples/run_examples.py` or `examples/cli.py` (each calls the OpenAI API), and not any future study runner. Tests, `scripts/eval.sh` with
existing runs, and anything that only reads files are free. Do not invoke a run script "to test" argument handling; check script edits with `bash -n` or `STAGE=eval`.
Tests mock the model.

## Claude agent

- `problem-checker` agent: fact-checks `research/problem.md` against prior work and, if `research/inputs.md` exists, the preregistration and results. Its text still describes the
  retired agent-loss problem (conjunction of agent unavailability, specialised sub-agents and grounded records); update it before using it on the current statement.
- If you change the agent, `decisions.md` or `preregistration.md`, say which other files now disagree.
