---
name: create-team-benchmark
description: Convert a workflow in examples/end_to_end_examples into its team-membership non-stationarity variant in examples/end_to_end_examples_team, following docs/team_non_stationarity/benchmark.md. Creates it if missing; otherwise edits only what the changed inputs affect (--rebuild recreates it from scratch).
argument-hint: <workflow-name> [--plan-only] [--rebuild]
allowed-tools: Read Write Edit Glob Grep Bash(uv run python scripts/team_benchmark.py *) Bash(uv run python -c *) Bash(uv run pytest *)
---

# Create team benchmark: $ARGUMENTS

Convert `examples/end_to_end_examples/<name>/` into `examples/end_to_end_examples_team/<name>/`.
`<name>` is the first word of the arguments above. If `--plan-only` is present, stop after the plan
(step 3 when creating, step U2 when updating).

## Mode

Run `uv run python scripts/team_benchmark.py plan <name>`; its `status.state` picks the mode:

- **create**: state `missing`, or `--rebuild` was passed. Follow **Steps** below (step 4 deletes any
  existing output). `--rebuild` is also the fallback when an update cannot be made cleanly.
- **update**: the scenario exists and `--rebuild` was not passed. Follow **Update steps**. This edits
  only what the changed inputs affect and is cheaper, since the rest of the scenario is not
  regenerated.

## Ground rules

- **The rules live in the docs, not here.** When creating or rebuilding, read `docs/team_non_stationarity/benchmark.md` fresh,
  plus the **Scope** section of `index.md` and the **Scenario contract** and
  **Definitions** in `metrics.md`. When updating, read only what step U1 names. This file only says how to apply them. If the docs and this file
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
- **Create and `--rebuild` start from scratch.** Step 4 deletes the existing output. Do not try to
  preserve or merge earlier output in those modes.
- **Update never deletes.** It edits files in place, touches only what the diff affects, and leaves
  every other file and line as it is.

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
   - engine support the benchmark assumes: the roster-change notice and restart-on-reassign are built
     for team runs (see `UPDATES.md`); check the planned rows there for anything still missing.

## Update steps

Used when the scenario already exists. The goal is the same scenario a rebuild would give for the
changed rules, reached by editing instead of regenerating.

U0. **Find what changed.** Run `uv run python scripts/team_benchmark.py diff <name>`. It prints unified
   diffs of every input (the rule docs, this skill, the source scenario) against the copy saved when
   the scenario was last stamped.
   - `NO CHANGES`: report that and stop.
   - `NO SNAPSHOT` (exit 2): there is nothing to diff against. Say so and stop; the user either
     stamps a baseline (`stamp <name>`) when the scenario already matches the current rules, or
     reruns with `--rebuild`. Do not guess what changed.

U1. **Read** the diff, then only the parts of the docs and source it touches (plus the sections of the
   docs those rules point to). Print **"Changes since the last stamp"**: one bullet per changed rule
   or source change, naming the doc heading or file.

U2. **Print an edit plan** before editing: for each change, the files and the exact items to edit,
   and the files left untouched. Use this map:

   | Change in | Edit |
   |---|---|
   | Worker-private content, roster | `team.py` (worker prompts, capabilities), `CONVERSION.md` |
   | Gated tasks, checklists, controls | `workflow.py`, `team_change_spec.py`, `CONVERSION.md` |
   | Cases, events, schedule, event count | `team.py` timeline, `team_change_spec.py`, `CONVERSION.md` (disposition table, leave timing) |
   | Scenario contract or definitions in `metrics.md` | `team_change_spec.py` |
   | A source task, worker or timeline change | the matching team file, `preferences.py` if it names the worker, `CONVERSION.md` |
   | This skill's procedure | only what the changed step produces; otherwise no scenario edit |

   If the changes touch most of the rules, or reach into several files in ways that cannot be edited
   cleanly, stop and recommend `--rebuild` instead. If `--plan-only`, stop here.

U3. **Edit in place** with the Edit tool, only the files and items in the plan. Keep source task
   names stable. Do not run `reset`, do not delete files, and do not rewrite untouched ones.

U4. **Verify** as in step 6: `check` until `OK` (stop after 5 failed attempts and recommend
   `--rebuild`), the import check, and the walk through *Event types*, *Gated tasks* and *Rules
   for the rest of the scenario* for what changed. Redo step 7 (judged mapping) for any affected
   task or worker, and update `correct_agents`.

U5. **Record.** Update the affected sections of `CONVERSION.md` and add a line to an **Update log**
   section at its end (date, what changed, files edited). Run `stamp <name>`, which also moves the
   baseline that the next `diff` compares against. Update the `UPDATES.md` rows if the scenario's
   description changed.

U6. **Report**, in at most 15 lines: the input changes, the files edited and the files left untouched,
   check result and warnings, `correct_agents` changes, and what is not done (as in step 9).

## Keeping this skill current

- **Change the benchmark:** edit `docs/team_non_stationarity/benchmark.md` (or `metrics.md`). This
  skill reads it live. Run `scripts/create_team_benchmark.sh --status` to see which generated
  scenarios are now stale, then run the skill on them: it updates each in place from the diff.
- **Change the procedure:** edit this file. Its hash is part of each scenario's stamp, so every
  scenario shows as stale afterwards; the update then edits only what the changed step affects.
- **Mechanical checks and the deferred gate validation** are in `scripts/team_benchmark.py`. They mirror the benchmark rules, and
  the tool warns when the *Change-affected cases* table gains or loses a case so `KNOWN_CASES`
  can be updated.
