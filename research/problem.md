# Problem statement (v3: empirical study of mid-workflow changes; from research/Project Proposal.md, the editable working copy of the PDF)

## Problem
Adaptive Planning for Multi-Agent Workflows: an empirical study of how a manager agent handles preference, goal and environmental changes that arrive mid-workflow.

A manager agent decomposes a task, delegates it to workers and tracks progress. After some work is committed, the workflow can change: the environment changes (road closures, delays), the user's preferences shift (how options are ranked), or the user's goals change (what counts as success). The manager must decide which completed and in-progress work to keep, which to revise, and how to reassign the rest. Restarting wastes completed work; ignoring the change delivers the wrong outcome.

## Approach
Use MA-Gym's existing benchmarks, establish what is wrong with them for this purpose, improve them by leveraging other peer-reviewed benchmarks (for example REALM-Bench), add a layer of mid-workflow changes, run a baseline manager (MA-Gym CoT), analyse its errors per change type, then test targeted training-free improvements one at a time. Compare against reference conditions (ignore the change, replan from scratch), not against other published methods.

## Research questions
1. How does a baseline manager behave under environmental, preference and goal changes, and what are its main failure modes?
2. Which training-free design factors reduce those failures, and for which change type? Candidates: an explicit continue/repair/replan decision, identifying affected tasks from dependencies, tracking the active requirements.
3. How do results depend on when the change arrives and how much of the remaining plan it affects?
4. What does each improvement cost in model calls?

## Why it is a real problem (claims as stated in the proposal; sources not re-verified here)
- Changes after work starts are normal: requirements change in real projects (study); users of AI agents add and revise requests as the agent works (PersonaForge).
- Agents handle changes poorly: performance drops when the user changes what they want (Tack et al.); strong models struggle when interrupted mid-task (InterruptBench).
- Restarting is costly: repairing a plan usually needs fewer changes than replanning from scratch (Fox et al., 2006); enterprise systems already handle requests that change in progress (Oracle).
- Many agents make it harder: planners fail to adapt when they do not track what is done (REALM-Bench); many multi-agent failures come from unclear or lost instructions (MAST). How often users change their minds in multi-agent workflows is unmeasured, so this is an assumption.

## Setting
- Benchmark: MA-Gym's existing benchmarks (its example workflows), with elements borrowed from other peer-reviewed benchmarks. Which elements, and from where, is not yet decided; the proposal names REALM-Bench (ride sharing, wedding and Thanksgiving logistics, with traffic, road-closure and delay disruptions).
- Environmental changes: disruptions such as traffic, road closures and delays, from a borrowed benchmark or injected (MA-Gym has none of its own).
- Preference and goal changes: injected at controlled points. A preference change alters how options are ranked; a goal change alters what counts as success.
- Reference answer: where an exact solver exists, re-solve the remaining problem under the new objective.

## Variables
Change type (environmental, preference, goal); timing (early, mid, late); share of the remaining plan affected; explicit versus implied change. One factor varied at a time from a default setting.

## Evaluation
Outcome quality after the change versus the re-solved reference; unnecessary changes to unaffected work (unaffected tasks as control); cost in model calls and tokens; repeated runs per condition for variability. Final results reported on scenarios held out from development.

## Scope and limitations
- One benchmark base, cheap model tiers. Task changes and agent unavailability are future work.
- MA-Gym was published at DAI 2025 (arXiv version Oct 2025). Its metrics were not designed to measure change handling, so their validity for this study is argued directly.
- MA-Gym's flaws that are accepted rather than fixed are limitations (`decisions.md` D28). Where no exact solver exists the reference answer is weaker.
- Findings from a planning benchmark may not transfer to other workflows.

## Core issues with MA-Gym's benchmark (details and conflicts: `decisions.md` D28)
- No metric measures the manager's response to a change: scores are workflow-level and mostly LLM-judged, a high score does not show the change was handled, changes cluster so effects cannot be attributed, and nothing measures unnecessary disruption. The study therefore needs change-specific metrics (affected-task outcome, disruption cost, model calls and tokens).
- No justification for why and when changes are injected: fixed change-points, synthetic scenarios. The study justifies its changes from real-world evidence, varies timing and share affected, and states its assumptions (justify and vary, not ground in records: `decisions.md` D29).

## Open concerns
- The cited sources show that changes happen, not when or how often; timing rests on stated assumptions unless a source is found. Results therefore hold across the timings tried, not necessarily for real workflows.
- What exactly is wrong with MA-Gym's benchmarks for this study (first step of the plan), and what other peer-reviewed benchmarks can supply.
- Whether borrowed elements map onto MA-Gym's worker and manager model, or the manager has to be adapted.
- The PDF's scope section has a cut-off bullet (see the editor's note in `Project Proposal.md`). The proposal's "Next steps" stop at the CoT baseline; the improvement list is a candidate list, not a commitment.

## Earlier versions (retired; kept for the record)
1. Open ad-hoc teamwork for manager agents (join/leave of workers): dropped; it did not fit the manager setup and MA-Gym's benchmark is not built to handle change.
2. Adaptive replanning for external changes (outages, rate limits, agent unavailability): dropped; most of it is solved by infrastructure, and an agentic solution to a deterministic problem was hard to justify. Agent unavailability stays as future work.
