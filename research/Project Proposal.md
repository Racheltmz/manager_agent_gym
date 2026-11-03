# Adaptive Planning for Multi-Agent Workflows

*An empirical study of manager agents: handling preference, goal and environmental changes in multi-agent workflows*

> **Working copy, not final.** Transcribed on 2026-11-03 from `Project Proposal.pdf` (the PDF is a snapshot and is not regenerated from this file). **Edit this file.** When it changes the design, update `decisions.md`, `preregistration.md` and `problem.md` to match (`CLAUDE.md` says how).
> Text is kept as in the PDF, including its unfinished parts (marked with an editor's note in a comment) so nothing is silently fixed.

## Research Direction

- Use an established multi-agent benchmark and add a layer of mid-workflow changes.
- Run a baseline manager agent, analyse its errors for each change type, then test targeted improvements one at a time.
- Compare against reference conditions (ignore the change, replan from scratch), not against other published methods.

## Problem Definition

In multi-agent workflows, a manager agent decomposes a task, delegates it to worker agents and tracks progress. During execution the workflow can change after some work is already committed: the environment changes (for example road closures or delays), the user's preferences shift (how options are ranked), or the user's goals change (what counts as success). The manager must decide which completed and in-progress work to keep, which to revise, and how to reassign the remainder. Restarting wastes completed work, while ignoring the change delivers the wrong outcome.

This study evaluates how a baseline manager agent handles each change type, analyses its failures, and tests which training-free improvements help for which type.

## Research Questions

1. How does a baseline manager agent behave under environmental, preference and goal changes, and what are its main failure modes?
2. Which training-free design factors reduce those failures, and for which change type? Candidates are an explicit continue, repair or replan decision, identifying affected tasks from dependencies, and tracking the active requirements.
3. How do results depend on when the change arrives and how much of the remaining plan it affects?
4. What does each improvement cost in model calls?

## Why This Is a Real Problem

- **Changes after work starts are normal.** Requirements change in real projects and cause delays and extra cost (study), and users of AI agents add and revise requests as the agent works (PersonaForge).
- **Agents handle changes poorly.** Performance drops when the user changes what they want (Tack et al.), and strong models struggle when interrupted mid-task (InterruptBench).
- **Restarting is costly.** Repairing an existing plan usually needs fewer changes than replanning from scratch (Fox et al., 2006), and enterprise systems already handle requests that change while in progress (Oracle).
- **Many agents make it harder.** Planners fail to adapt when they do not track what is already done (REALM-Bench), and many multi-agent failures come from unclear or lost instructions (MAST). How often users change their minds in multi-agent workflows has not been measured, so this is stated as an assumption.

## Setting

- Benchmark: MA-Gym existing benchmarks
- Environmental changes: the benchmark's existing disruptions (traffic, road closures, delays).
- Preference and goal changes: injected at controlled points. A preference change alters how options are ranked. A goal change alters what counts as success.
- Reference answer: where an exact solver exists, re-solve the remaining problem under the new objective.

<!-- Editor's note: "traffic, road closures, delays" are REALM-Bench's disruptions (the earlier draft used REALM-Bench as the benchmark). With MA-Gym as the benchmark, decide where environmental changes come from, and whether an exact solver exists for any MA-Gym workflow. -->

## Method

1. **Baseline:** define and freeze one manager agent (model, prompt, visible state, delegation).
2. **Error analysis:** categorise failures for each change type, for example ignoring the update, restarting everything, losing track of completed work, or replanning the wrong part.
3. **Improvements:** for each frequent failure, add one targeted modification, test it alone, then in combination.
4. **Held-out check:** develop on one set of scenarios and report final results on a separate set.

## Variables

- Change type: environmental, preference, goal.
- Timing: early, mid or late in the workflow.
- Share of the remaining plan affected by the change.
- Whether the change is stated explicitly or only implied.
- One factor is varied at a time from a default setting.

## What kind of Benchmark is MA-Gym

| Capability | How MA-Gym covers it |
|---|---|
| Planning | Actions to decompose a task, refine it and add dependencies |
| Delegation | Actions to assign one task or all pending tasks. The Assign-All baseline gets higher goal completion but worse constraint adherence |
| Coordination | Dependencies gate execution, so human actions can block downstream tasks (a CoT run averaged 46.9 simulated hours) |
| Monitoring | Actions for workflow status, task inspection and available agents |
| Communication | A messaging action, scored by a stakeholder-management metric |
| Adaptation | Partial. Preference change-points and workers joining or leaving mid-run |
| Governance | Hard and soft constraints feed the score, but the paper treats the wider topic mostly as a research agenda |

## Problems with MA-Gym's benchmark and metrics (two core issues)

*Added 2026-11-03. Not in the PDF. Implementation bugs (handoff, judge truncation, seeding, state) are deliberately not listed here.*

**Issue 1: no metric measures how well the manager handled a change**
- Metrics are workflow-level (preference alignment, goal achievement, constraint adherence, stakeholder management, completion time). They score the whole run, not the response to a specific change.
- Most goal and preference scoring is LLM-judged against rubrics, with no deterministic per-task check. Whether a task was handled correctly after a change cannot be verified.
- A high score does not show the change was handled. The manager can ignore the change, or keep using the original workers or plan, and still score well. Change handling is confounded with overall workflow quality.
- Before-and-after comparison is unreliable. Changes are clustered or overlapping, so there is no stable baseline and effects cannot be attributed to a single change.
- Nothing measures unnecessary disruption (changing work the change did not affect). There is no control using unaffected tasks.
- **Implication:** the study needs change-specific metrics: (a) outcome quality on the change-affected tasks after the change, scored deterministically where possible; (b) disruption cost: unnecessary changes to unaffected work; (c) cost in model calls and tokens.

**Issue 2: no justification for why and when changes are injected**
- Change points are fixed by design: preference change-points at roughly one-third and two-thirds of the action budget (paper Appendix C.6), and scripted worker join and leave times. The paper gives no stated justification that these match when changes occur in real workflows.
- Scenarios are synthetic, not grounded in real-world evidence of how and when changes occur.
- Without grounding, results cannot be shown to apply to real use. It is unclear whether failures reflect real conditions or an arbitrary injection point.
- **Implication:** justify the injected changes from real-world evidence (the sources under "Why This Is a Real Problem"). Vary timing (early, mid, late) and the share of the remaining plan affected, instead of using one fixed point, and state the assumptions behind the chosen change types and timings.

<!-- Editor's notes (conflicts and checks, 2026-11-03):
1. "Why This Is a Real Problem" sources show that changes happen and that agents handle them poorly; they do not say when or how often (the proposal itself says this is an assumption). Issue 2 can only be answered by stating assumptions, unless a source on timing is found.
2. Issue 2 asks for grounding, but the earlier direction that tried to build a grounded benchmark was dropped because it needed domain knowledge and data. Decided 2026-11-03: justify and vary (decisions.md D29), not ground in records. Claims are limited accordingly.
3. The Setting section reuses MA-Gym's preference mechanism, whose change-points are the fixed ones in Issue 2 (the repo's legal_m_and_a hard-codes t=35 and t=70). If reused, re-time them. The "one-third and two-thirds of the action budget" and "Appendix C.6" details are from the paper and were not checked here.
4. "Metrics" in Issue 1 means MA-Gym's own. The deterministic checklists (TaskRequirement) in this repo are an addition made for the study, not part of MA-Gym. -->

## Evaluation

- Outcome quality after the change, compared with the re-solved reference.
- Unnecessary changes to work the change does not affect, using unaffected tasks as a control.
- Cost in model calls and tokens.
- Repeated runs for each condition to report variability.

## Scope and Limitations

- One benchmark and cheap model tiers. Task changes and agent unavailability are future work.
- <!-- Editor's note: this bullet is cut off in the PDF (it reads "instances, so it is used as a controlled testbed for LLM managers."). It was the REALM-Bench caveat that exact solvers exist for small instances. Rewrite it for MA-Gym. -->
- Findings from a planning benchmark may not transfer to other workflows.
- MA-Gym was published at DAI 2025 (International Conference on Distributed Artificial Intelligence, London; arXiv version Oct 2025). Its metrics were not designed to measure change handling (Issue 1), so their validity for this study is argued directly.

## Next Steps

1. Understand the problems with MA-Gym benchmarks.
2. Understand what I can add from other peer-reviewed benchmarks.
   - Read: REALM-Bench, EntCollabBench, OrchestrationBench. Questions to ask of each are in `decisions.md` D28.
3. Will inject:
   1. No changes
   2. Environment changes
   3. Goal changes
   4. Preference changes
4. Run experiments starting with baseline, which is just the manager agent with CoT.
5. Then understand the metrics.
6. Empirical study making improvements to the manager agent with CoT.
