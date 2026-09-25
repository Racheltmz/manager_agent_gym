---
description: Convert an examples/end_to_end_examples scenario into its AHT (autoscaling / heterogeneous-team) benchmark variant, and report the diff
argument-hint: <benchmark-folder-name, e.g. legal_m_and_a>
---

# Create AHT benchmark: $1

Convert `examples/end_to_end_examples/$1/` into an AHT benchmark variant under
`examples/end_to_end_examples_aht/$1/`, following the same procedure already applied to
`legal_m_and_a` (treat that folder as the reference implementation for structure/style, not
something to copy verbatim). Work bit-by-bit and report progress at each checkpoint below —
don't silently batch everything into one wall of output.

## 0. Read before doing anything

- `docs/benchmark_aht/index.md` — the root doc: problem statement (**"we already trusted this
  agent enough to deploy it — now infer what it's specifically good at, cheaply, from scratch,
  while the workflow is running"**), the **"Two design rules"** section (read this closely — it's
  binding on every scenario this command produces, not just guidance), definitions (including
  exogeneity — the manager never controls or triggers a join/leave), the two-gaps rationale, and
  "Known engine risks to verify" (bugs to flag, not fix).
- `docs/benchmark_aht/benchmark_conversion.md` — the governing procedure for everything in this
  command: the generic 6-step rule, the demand-driven team-churn decision (`offline_static`,
  decided — not a placeholder), and sequencing.
- `docs/benchmark_aht/autoscaling_team_churn.md` — the demand-derivation mechanism in detail;
  offline vs. runtime is resolved in favor of offline, not an open choice — how join/leave timing
  gets reasoned from the task graph. Note its "Why reconsider the current mechanism" section:
  there is no per-agent concurrency limit in the engine, so this is never a load/capacity
  threshold — it's "which specialty does the graph need right now."
- `docs/benchmark_aht/benchmark_conversion_template.yaml` — the structured spec to fill in.
- `examples/end_to_end_examples/$1/workflow.py`, `team.py`, `preferences.py` — the source of
  truth for the original scenario. If `examples/end_to_end_examples/$1/WORKFLOW_MAP.md` exists,
  read it too for the pre-computed task graph/roster; if it doesn't, derive the same
  understanding directly from `workflow.py`/`team.py`.
- `examples/end_to_end_examples_aht/legal_m_and_a/` (workflow.py, team.py, preferences.py,
  conversion_spec.yaml, and `../trait_pool.py`) — the one built-and-verified reference. Match
  its structure (module layout, docstring style, comment density) for the new scenario.

**Idempotency check:** if `examples/end_to_end_examples_aht/$1/` already exists, stop and ask
before overwriting anything in it.

## 1. Feasibility / graft point (benchmark_conversion.md, "The generic 6-step procedure", step 1)

Read `$1`'s task graph. Find a task whose description already bundles 2+ genuinely different
specialties (a natural split point), or identify where an existing task needs rewriting to
create one (per benchmark_conversion.md's "heavy modification is allowed" note). State the graft point
and why, before moving on.

## 2. Human-role audit (benchmark_conversion.md step 2)

For every `HumanAgentConfig` in `$1/team.py`: decide **convert** (equivalent knowledge work, no
load-bearing sign-off/authority language) or **drop** (authority/sign-off is its defining
function, or it's an orphan — no dependent task, or never actually scheduled in
`create_team_timeline()`). Cross-reference `preferences.py` for any rubric that name-matches a
task or references an agent_id that a drop/split would break. Record every decision with its
rationale — this is a judgment call, not mechanical (per `benchmark_conversion.md`'s own
wording), so show the reasoning, don't just assert the outcome.

## 3. Trait-tuple pools (benchmark_conversion.md step 3; tuple schema in open_aht_benchmark_plan_prev.md §3.3)

Reuse existing entries in `examples/end_to_end_examples_aht/trait_pool.py`'s `TRAIT_POOL` where
they fit. Only add a new tuple if the graft point genuinely needs two structurally distinct
pools to discriminate (as `privacy_reasoning_gpt4o` was added for `legal_m_and_a`'s T6 split) —
don't invent tuples for variety's sake. Group the post-audit AI-only roster into named pools
(one trait tuple per pool), each mapped to the tasks it feeds.

## 4. Derive the team timeline (benchmark_conversion.md, "Team-churn generation: demand-driven roster")

**Target method is `offline_static`** — this is a principled choice, not a stopgap (see
`benchmark_conversion.md`). The churn signal has to be independent of the manager's
own decisions to count as externally-triggered non-stationarity at all — a live signal driven
by ready-or-in-progress task counts would be manager-reactive, since task completion timing
depends on assignment quality, which entangles "team changed" with "manager performed well,"
defeating the point of testing adaptation to change the manager doesn't control. Real
demand-driven staffing reacts to external work arriving, not to the on-call engineer's own
performance; simulating that in a benchmark with no real external signal to hook into means
precomputing a fixed schedule, not computing one live.

**This is never a load-vs-capacity computation.** The execution engine has no per-agent
concurrency limit (`engine.py`'s ready-task loop starts every ready task with an assigned agent
concurrently, with no check for whether that agent is already running something else), so a
"pool scales out because load exceeds capacity" framing has nothing real to threshold against.
Instead, for every pool, decide three things directly from the task graph's dependency structure:

1. **Join — a one-shot cold-start bundle, not a per-task event.** When a pool's specialty first
   becomes needed, the new agent is guessed onto *every* task in that demand window at once (e.g.
   a newly-joined diligence-triage agent gets bundled onto every diligence-shaped task in its
   window in one join event, not added again for each task individually). **Rule 1 (binding):**
   that agent is never pulled off the bundle mid-way and replaced by a different specialist —
   there is no "it left, hand its remaining work to someone similar" event anywhere in the
   timeline. If a bundle looks like it needs splitting across two agents, split it at
   authoring time (two smaller bundles, two joins), don't model a live hand-off.
2. **Leave — gated on completion, not on a schedule that merely looks plausible.** **Rule 2
   (binding):** an agent's `remove` event may only fire at a timestep where every task in its
   bundle would plausibly be `COMPLETED` (check against `estimated_duration_hours`, not just
   "some later timestep") **and** no task ready at that timestep still needs its pool. A removal
   timestep that coincides with, or precedes, that same agent's own task assignment is a bug —
   check for this explicitly before finalizing the timeline (`legal_m_and_a`'s original build had
   exactly this bug: an agent removed the same timestep it was assigned a task).
3. **The reason string names the specialty, never the task.** **Rule 3 (binding):** write
   "debt-commitment and closing-coordination demand opens," never "this agent is for T9." Naming
   a task ID in the reason string relocates the ground-truth-label mistake the rest of this design
   already rules out for the manager into the scenario author's own bookkeeping — and it's not
   cosmetic: it's what lets two agents get silently authored as covering the *same* task with
   nothing forcing a check (`legal_m_and_a`'s build hit this too — `finance_counsel_ai` and
   `rwi_packager` were both authored "for T9" before it was caught). Verify which task a given
   specialty actually serves separately, in `conversion_spec.yaml` (structured and checkable),
   never by asserting it in the timeline itself — and while there, confirm no two agents claim the
   same task without one of them being dropped or the task being split.

Deriving join timing from shared dependency structure (which tasks share a dependency, not task
identity) is what keeps it from telegraphing which agent is "meant for" which task (e.g. two
Objective-1 pools both become needed at the same timestep because their tasks share a dependency,
not because either is "the" intended one) — this holds precomputed exactly as well as it would
live, so it does not require live/runtime computation to work.

## 5. Author the grafts (benchmark_conversion.md steps 4-5)

- **Objective 1:** split the step-1 graft point into two similarly-named tasks/subtasks, each
  with a disjoint `requirements` checklist (deterministic-only, `check="deterministic"` — see
  open_aht_benchmark_plan_prev.md §3.2's rule: task can be hard, check must be cheap/exact), each clearable only by one
  specific pool from step 3.
- **Objective 2:** one later, differently-worded task reusing the *same* pool as one of the
  Objective-1 subtasks, at a non-adjacent point in the graph.

Use new `Task` UUIDs distinct from the original scenario's range so both modules can coexist.

## 6. Write the scenario files

Create `examples/end_to_end_examples_aht/$1/`:
- `__init__.py` (mirror the original's exports)
- `team.py` (audited roster, pool-tagged via `with_trait_tuple`, derived timeline)
- `workflow.py` (original tasks content-identical except the two grafts; new UUID range)
- `preferences.py` (copy of the original, fixed for any rubric broken by the grafts — e.g. a
  name-substring match against a task name that no longer exists post-split)

Do **not** touch `manager_agent_gym/core/evaluation/common_evaluators.py`,
`manager_agent_gym/core/evaluation/task_requirements_evaluator.py`, or
`examples/run_examples.py` — those are shared engine call sites used by every scenario. Only
add to `manager_agent_gym/schemas/` (config.py's trait-tuple fields, tasks.py's
`TaskRequirement`/`requirements`/`objective` fields) if they don't already exist there — check
first, since an earlier run of this command may have already added them.

## 7. Verify by construction — no simulation run

Import the new scenario's `create_workflow`, `create_team_timeline`, and
`create_<name>_team_configs`-equivalent functions and call them directly in a throwaway Python
`-c` check. Confirm task counts, `objective`/`requirements` tags, agent trait tuples, and
timeline event counts look right. **Never run `scripts/run.sh`, `scripts/run_all.sh`, or
`examples/run_examples.py`** — those call the OpenAI API and are out of scope for this command
regardless of how this step goes; per `CLAUDE.md`, only run them if the user's own message
explicitly asks.

## 8. Fill the conversion spec

Copy `docs/benchmark_aht/benchmark_conversion_template.yaml` to
`examples/end_to_end_examples_aht/$1/conversion_spec.yaml` and fill every section with what was
actually decided/built in steps 1-7 — `human_role_audit`, `trait_pool_deltas`, `pools`,
`task_graph.grafts`, `requirements_catalog`, `derived_team_timeline`,
`state_action_scoring_mapping` (copy verbatim — it doesn't change per scenario),
`preferences_audit`, `verification_checklist` (mark items `unverified` unless this command
happened to check one directly), and `open_questions` (at minimum: the evaluator-wiring gap
from step 6).

## 9. Output the diff — the actual deliverable

Write `examples/end_to_end_examples_aht/$1/AHT_DIFF.md` (in the **AHT variant's** folder,
alongside `conversion_spec.yaml` — not the original scenario's folder) covering:

- **Task graph diff:** which tasks are unchanged, which were split (Objective 1), what was added
  (Objective 2) — a mermaid diagram of the AHT-variant graph with the changed tasks highlighted,
  same style as the existing example in
  `examples/end_to_end_examples_aht/legal_m_and_a/AHT_DIFF.md` §1.
- **Roster diff:** the human-role audit table (role, decision, rationale) — converts and drops.
- **Pool mapping:** table of pool name, trait tuple, members, tasks fed.
- **Roster timeline diff — concise, comprehensive diagrams highlighting the demand-driven
  churn** (not optional, not just prose): compute this directly from the built
  `create_team_timeline()`, not from illustrative estimates. Three parts, same structure as
  `legal_m_and_a`'s AHT_DIFF.md §3a:
  1. A mermaid Gantt chart of agent presence *grouped by pool* (one section per pool), so a
     join/leave shows as a bar appearing/disappearing within its pool's section.
  2. A headcount grid table — pools × the scenario's actual timeline timesteps, headcount per
     pool right after each timestep's events, plus a total-active row. Cross-check the grid
     against the raw timeline events by hand (each column should sum to the total-active row)
     before writing it down — don't eyeball it off the Gantt. **Also verify rule 2 here**: for
     every `remove` event, confirm the departing agent's bundle tasks are all `COMPLETED`-by
     estimate at that timestep and that timestep doesn't coincide with that same agent's own
     assignment.
  3. Explicit callouts connecting the data to the two objective tests: which two pools become
     needed independently at the Objective-1 split point (disjointness is the test), and which
     pool joins once and *never* leaves before the Objective-2 reuse task's graft point
     (persistence is what makes that test possible at all). Note any bonus
     same-tuple/non-adjacent-task pattern that falls out naturally, even if not formally tagged
     `objective_2` in this pass.
- **Requirements added:** table of the new `TaskRequirement` items, which task, which pool they
  discriminate for.
- **What's explicitly NOT changed:** preferences.py's five scored values, every task outside the
  graft points, the engine/evaluator wiring (still pending, per step 6's boundary).

End the diff doc with a one-line pointer to `conversion_spec.yaml` for the full structured
record, and to `docs/benchmark_aht/index.md`'s "Known engine risks to verify" section for the
engine bugs worth re-checking before trusting a real run of this variant.

## Report back

Close with a short summary: graft point chosen, audit outcome (N converted / N dropped), pools
created, whether any new trait tuple was needed, and the path to the diff doc.
