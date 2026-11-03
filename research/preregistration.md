# Preregistration: how a manager agent handles mid-workflow changes (empirical study)

Written **before any run**. Specification only: no code, scenario or result exists for this version. Companion to [`decisions.md`](decisions.md) (design decisions) and
[`Project Proposal.md`](Project%20Proposal.md) (direction; editable working copy of the PDF, not final). Frozen when the user gives the "go"; after that, changes are dated amendments at the bottom.
The earlier version of this file (agent-loss thresholds, 30-scenario grid, experiments E0 to E7) was never frozen and is retired; it is in git at c346d57.

## Questions

| ID | Question (from the proposal) |
|---|---|
| RQ1 | How does a baseline manager behave under environmental, preference and goal changes, and what are its main failure modes? |
| RQ2 | Which training-free design factors reduce those failures, and for which change type? |
| RQ3 | How do results depend on when the change arrives and how much of the remaining plan it affects? |
| RQ4 | What does each improvement cost in model calls? |

## Setting

- **Benchmark:** MA-Gym's existing benchmarks, improved with elements of other peer-reviewed benchmarks (REALM-Bench is the one the proposal names). What is wrong with MA-Gym's benchmarks is established first (`decisions.md` D28).
- **Change types:** environmental (disruptions such as traffic, road closures, delays, from a borrowed benchmark or injected), preference (how options are ranked), goal (what counts as success). Preference and goal changes are injected at controlled points.
- **Fixed:** the baseline manager once frozen (model, prompt, visible state, delegation); cheap model tiers.
- **Out of scope:** agent unavailability, task and requirement drift beyond the goal change, joins and leaves, error recovery, comparison with other published methods.

## Conditions

| ID | Condition | Role |
|---|---|---|
| C0 | No change | Control: the manager's behaviour without a disruption |
| C1 | Ignore the change | Lower reference |
| C2 | Replan from scratch | Reference that wastes completed work |
| C3 | Baseline manager (MA-Gym CoT) | The system whose failures are analysed |
| C4.n | Baseline plus one targeted improvement (n = 1, 2, ...) | Tested alone first, then in combination |
| REF | Re-solved remaining problem under the new objective | Reference answer, where an exact solver exists |

Candidate improvements (the list is a candidate list, not a commitment): an explicit continue/repair/replan decision; identifying affected tasks from dependencies; tracking the active requirements. Each is added only in response to a failure mode that is frequent in C3.

## Factors

One factor varied at a time from a default setting.

| Factor | Levels |
|---|---|
| Change type | environmental, preference, goal |
| Timing | early, mid, late in the workflow |
| Share of the remaining plan affected | to be set when the scenarios exist |
| Explicitness | change stated explicitly, or only implied |

## Method

1. **Baseline:** define and freeze one manager.
2. **Error analysis:** categorise C3's failures per change type; starting taxonomy: ignoring the update, restarting everything, losing track of completed work, replanning the wrong part. Extend it from the data, and list every category added after seeing results.
3. **Improvements:** one targeted modification per frequent failure, tested alone, then in combination.
4. **Held-out check:** develop on one scenario set, report final results on a separate set. The split is fixed before the first improvement is tried.

## Measures

- **Outcome quality after the change**, against the re-solved reference where an exact solver exists.
- **Unnecessary changes:** work the change does not affect that the manager nevertheless moved, restarted or removed (unaffected tasks as control).
- **Cost:** model calls and tokens (wall time if cheap to record).
- **Variability:** repeated runs per condition; report the spread, not only the mean.
- A per-run trace: the change event, each manager decision, which tasks the change affected.

## Open items (to fix before the "go")

None of these has a value yet; the proposal does not give one. Do not invent them while building: ask.

- The assumptions behind the chosen change types and timings, and the justification for each (`decisions.md` D28 Issue 2 and D29: justify and vary, not ground in records); the cited sources do not say when changes occur, so write the assumptions down before the first run.
- How "outcome quality on affected tasks" is scored deterministically (`decisions.md` D28, Issue 1), and which tasks are marked affected and which serve as unaffected controls.
- The list of MA-Gym benchmark flaws, and which are fixed, borrowed or accepted (`decisions.md` D28).
- Which scenarios the study uses, which elements are borrowed from which peer-reviewed benchmark, and the development and held-out split.
- Mapping of borrowed elements onto MA-Gym (`decisions.md` D22).
- The outcome score for preference and goal changes where no exact solver exists.
- Number of repeated runs per condition, and the manager and worker models.
- What counts as a "frequent" failure (the cut-off for adding an improvement) and as a "helpful" improvement (the minimum gain, and the interval or test used).
- Levels of the "share affected" factor and of timing (which steps are early, mid, late).
- Whether the counterfactual pair (the same scenario with and without the change, `decisions.md` D21) is used.

## Thresholds (single source of truth)

None yet. When set they live in one code module, mirrored here, with a test that fails if they disagree; changes after the freeze are dated amendments.

## Assumptions (to be frozen at the "go")

- **A1 (timing):** a change can arrive at any point in the workflow, so timing is varied (early, mid, late). No timing is claimed to be the realistic one. (`decisions.md` D29)
- Add one line per further assumption: change types, the share of the plan affected, explicit versus implied. Each states what is assumed and why it is reasonable, citing a source where there is one.

## Claims the design supports

- Results hold across the timings (early, mid, late) and shares of the plan affected that were tried. They are **not** claimed to match when changes occur in real workflows (`decisions.md` D29).

## What would change my mind

- If the baseline already handles a change type well (small gap to the reference), report that and drop the improvement study for that type; it is a finding.
- If a failure mode is a scoring artefact, name it as one.
- If the no-change condition (C0) scores poorly, the scenario or the manager setup is the problem: fix it before reading any change result.

## Cost

Fixed at the freeze, once the scenarios exist. Estimate by building the real prompts and counting tokens without calling a model; state calls and dollars before the "go". No run is made before then.

## Amendments

- 2026-11-03, before any run: setting changed to MA-Gym's benchmarks improved with peer-reviewed ones (was REALM-Bench alone), following the updated proposal.
- 2026-11-03, before any run: rewritten for the empirical study (Project Proposal, problem definition 3). The agent-loss thresholds, grid and experiment types E0 to E7 are retired.
