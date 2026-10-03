---
name: create-team-benchmark
description: Convert a workflow in examples/end_to_end_examples into its team-membership non-stationarity variant in examples/end_to_end_examples_team, following docs/team_non_stationarity/benchmark.md. Rerunning recreates the variant from scratch.
argument-hint: <workflow-name> [--plan-only]
allowed-tools: Read Write Edit Glob Grep Bash(uv run python scripts/team_benchmark.py *) Bash(uv run python -c *) Bash(uv run pytest *)
---

# Create team benchmark: $ARGUMENTS

Convert `examples/end_to_end_examples/<name>/` into `examples/end_to_end_examples_team/<name>/`.
`<name>` is the first word of the arguments above. If `--plan-only` is present, stop after step 3.

## Ground rules

- **The rules live in the docs, not here.** Read `docs/team_non_stationarity/benchmark.md` fresh on
  every run, plus the **Scope** section of `index.md` and the **Scenario contract** and
  **Definitions** in `metrics.md`. This file only says how to apply them. If the docs and this file
  disagree, the docs win, and you say so in the report.
- Refer to doc sections by their **heading name**, never by number, because numbering changes.
- **Never run** `scripts/run.sh`, `scripts/run_all.sh`, `examples/run_examples.py`, or anything else
  that calls the OpenAI API. Those cost money and need an explicit ask from the user in their
  current message.
- **Gate validation is deferred.** Do not run `scripts/team_benchmark.py gate-run` (it refuses
  without `--enable`, because it costs one Claude call per affected task per worker). Step 7 sets
  `correct_agents` by your own judgment instead. Never run it unless the user's current message asks.
- Write only inside `examples/end_to_end_examples_team/<name>/`, plus one row in `UPDATES.md`
  (step 8). Do not edit the source scenario, `examples/scenarios.py`, or any other scenario.
- **A rerun starts from scratch.** Step 4 deletes the existing output. Do not try to preserve or
  merge earlier output.

## Steps

0. **Validate the argument.** Run `uv run python scripts/team_benchmark.py plan <name>`. It prints
   the rotation index, the source files, and `source_midrun_changes` (the source's joins and leaves
   after timestep 0), and fails for an unknown name.

1. **Read the rules.** Read the docs named above, then print a short **"Rules applied this run"**
   list (8 to 12 bullets, each naming the doc heading it comes from). This makes a changed doc
   visible in the output. Note any rule you cannot satisfy and why.

2. **Read the source.** Every `.py` file in the source scenario. For exact signatures read the code,
   do not guess: `manager_agent_gym/schemas/core/tasks.py` (`Task`, `TaskRequirement`),
   `manager_agent_gym/schemas/workflow_agents/config.py` (`AIAgentConfig`, `HumanAgentConfig`),
   `manager_agent_gym/core/evaluation/team_change_metrics.py` (`TeamChangeSpec`, `TeamChangeEvent`).

3. **Design, and print it as a plan** before writing anything:
   - **Roster.** AI agents only, so convert every `HumanAgentConfig` to an `AIAgentConfig` with an
     equivalent, accurate description and capabilities.
   - **Private content.** What each gated worker holds, following the requirements under
     *Worker-private content*.
   - **Gated tasks.** Which tasks, their checklist patterns, which worker holds the content.
     Affected tasks must be **leaf tasks**: only leaf tasks are assigned and run, so use a subtask
     rather than its composite parent. Subtasks are matched by name like any other task.
   - **Cases.** Read the kept cases from the *Change-affected cases* table, in table order. The
     primary case for this workflow is `kept[rotation_index % len(kept)]`. Give each
     change-affected task exactly one case and its fixed best action.
   - **Events.** Join and leave events satisfying everything under *Event types*. Restate the
     doc's requirements as a checklist and tick each one. Follow *Event count*: go through every
     source join and leave and either convert it into a compliant event or drop it, and list each
     one as `converted` (which case and tasks) or `dropped` (why). Aim for `source_midrun_changes`,
     but drop rather than force-fit.
   - **Controls.** Tasks no event touches. Give some a checklist so a baseline score exists.
   - **Schedule.** Timesteps for each event. For every leave, reason against the task dependency
     graph and durations that the leaving worker has finished everything assigned to it, and say
     what you assumed. Reason strings describe the scaling event and never name a task.

   If `--plan-only`, stop here.

4. **Reset.** Run `uv run python scripts/team_benchmark.py reset <name>`. It deletes the old output
   and keeps a backup in the system temp directory; mention the backup path in the report.

5. **Generate** these files in `examples/end_to_end_examples_team/<name>/`:
   - `__init__.py`: the same export names as the source `__init__.py`, plus `create_team_change_spec`.
   - `workflow.py`: the source tasks with checklists (`TaskRequirement` with a `pattern`) on the
     gated, affected and some control tasks. Keep source task names stable, because the metrics look
     tasks up by name. Do not pre-assign tasks to workers.
   - `team.py`: AI-only worker configs (`model_name="gpt-5-mini"`; see *Models* in `index.md`) with private content in `system_prompt` and accurate
     capabilities, and `create_team_timeline()` returning `{timestep: [(action, config, reason)]}`
     in the same shape as the source (a `remove` takes the config, as the source does).
   - `preferences.py`: adapted from the source. Drop references to agents that were removed or
     renamed, and anything human-specific. Leave the evaluators otherwise unchanged.
   - `team_change_spec.py`: `create_team_change_spec()` following the *Scenario contract*: events,
     affected tasks by name, `correct_agents` (scorer-only; diagnostics and the authoring check, not the headline metrics),
     and `cases`. Write your intended `correct_agents` now; step 7 confirms it by judgment.
   - `CONVERSION.md`: what changed from the source, the rules applied, the plan from step 3, a table
     of every source join and leave with its disposition (converted or dropped, and why), the
     leave-timing reasoning, assumptions, and open items.

6. **Verify.** Run `uv run python scripts/team_benchmark.py check <name>` and fix every error, then
   rerun until it prints `OK`. Stop after 5 failed attempts and report what is still wrong. Also
   run `uv run python -c "import examples.end_to_end_examples_team.<name> as m; m.create_workflow(); m.create_team_timeline()"`.
   The check covers only the mechanical rules. Walk through the remaining requirements in *Event
   types* and *Gated tasks* yourself and fix any gap. Also walk through **every agent and every
   task** against *Rules for the rest of the scenario*, not only the ones events name. Carry every warning into the report.

7. **Map tasks to workers by judgment** (gate validation is deferred). No Claude calls. For every
   affected task and every worker that can receive it (roster after the event, later joiners, and the
   leaver of a leave event), read the task name and description and the worker's `system_prompt` and
   capabilities, and decide whether that worker holds the private content the checklist patterns need.
   - Set `correct_agents` to the workers that would pass and are on the roster after the event.
   - Apply the pass rules from *Gate validation* in `benchmark.md` as a self-check: join-affected,
     only the joiner holds the content; leave-affected, the leaver and at least one remaining worker
     hold it. If the descriptions do not make that clear (the task description leaks the format, or
     private content is vague), fix `team.py` or `workflow.py`. Never change a pattern to fit the mapping.
   - Put a task × worker table (holds / does not hold, with the one-line reason) in `CONVERSION.md`,
     labelled as a judgment and not a measured result.

8. **Stamp and record.** Run `uv run python scripts/team_benchmark.py stamp <name>`. Then update
   the `UPDATES.md` Benchmark row "Team scenarios generated by /create-team-benchmark" so it lists
   this workflow (per `CLAUDE.md`).

9. **Report**, in at most 25 lines: the workflow; the rules applied (and any doc/skill conflict); the
   case rotation; gated tasks; events kept against the source count and each one dropped with its
   reason; controls; check result and warnings; the files written; the
   backup path if one was made; the judged mapping (who holds each gated task's content); and what is
   **not** done:
   - the scenario has not been run: `scripts/run.sh team` (or `examples/run_examples.py --benchmark team`) runs it, and needs no registration, but calls the OpenAI API and needs an explicit ask;
   - gate validation was not run: `correct_agents` is a judgment from descriptions, unverified by any worker output;
   - engine support that the benchmark assumes but may not exist yet (see the planned rows in
     `UPDATES.md`: roster-change notice, restarting a handed-over running task).

## Keeping this skill current

- **Change the benchmark:** edit `docs/team_non_stationarity/benchmark.md` (or `metrics.md`). This
  skill reads it live. Run `scripts/create_team_benchmark.sh --status` to see which generated
  scenarios are now stale, then rerun them.
- **Change the procedure:** edit this file. Its hash is part of each scenario's stamp, so every
  scenario shows as stale afterwards.
- **Mechanical checks and the deferred gate validation** are in `scripts/team_benchmark.py`. They mirror the benchmark rules, and
  the tool warns when the *Change-affected cases* table gains or loses a case so `KNOWN_CASES`
  can be updated.
