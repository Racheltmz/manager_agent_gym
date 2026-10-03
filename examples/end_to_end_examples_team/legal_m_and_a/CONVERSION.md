# Conversion: legal_m_and_a (team-membership non-stationarity)

Source: `examples/end_to_end_examples/legal_m_and_a/`. Rules: `docs/team_non_stationarity/benchmark.md`
and `metrics.md`.

> **Provenance.** This file and the scenario were written by hand (not by `/create-team-benchmark`),
> and the task-to-worker mapping below is a **judgment from the task and worker descriptions**, not
> a gate-validation result (gate validation is deferred; see *Gate validation* in `benchmark.md`).
> Regenerating with the skill replaces all of it.

## What changed from the source

- **Roster.** Every worker is an `AIAgentConfig` (the source's `HumanAgentConfig` roles converted, same
  descriptions and capabilities). `general_counsel` is `acquirer_gc`. Workers use `gpt-5-mini`.
- **Private content.** Each gated worker's `system_prompt` carries a house format only it (or, for a
  leave case, one other worker) follows. Workers differ by prompt only.
- **Checklists.** `TaskRequirement` items with a regex `pattern` on the 9 affected tasks (header, ids,
  a final line, and a topic item) and on 6 control tasks.
- **Timeline.** 8 workers at t=0, then 7 joins and 2 leaves (below). `closing_checklist_manager` and
  `tax_partner` start at t=0 because they are the remaining holders for the two leave cases.
- **Spec.** `team_change_spec.py` lists the events, affected tasks, cases and `correct_agents`.
- Preferences and the stakeholder proxy follow the source; references to removed workers were dropped.

## Rules applied (benchmark.md headings)

- *Worker-private content*: private formats in prompts, disjoint where a task is gated to one worker.
- *Gated tasks*: a task passes only if all four checklist items pass; three need the private format.
- *Change-affected cases*: specialist case for every join; leave case for both leaves.
- *Join events*: each joiner is the only worker holding its task's format.
- *Leave events*: each leave is followed by an unassigned task gated to a worker who remains.
- *Event count*: every source change converted or dropped, with a reason (table below).
- *Rules for the rest of the scenario* and *Control tasks*: unaffected tasks are controls.
- *Schedule*: a fixed timeline, with no task named in any reason string.

## Plan

- **Cases.** Specialist (7 joins). Leave (2 leaves). The running-task case is not used.
- **Gated tasks and holders.** See the mapping table.
- **Controls.** Every other task: Deal Intake & Objectives (and its subtasks), Authority & Governance
  Readiness, Diligence Scope & RFI Program, Financial Diligence, Legal Diligence – Corporate, Equity &
  Litigation, Financing Workstream. Checklists on Stakeholder Kickoff, Authority, Diligence Scope,
  Financial Diligence, Legal Diligence – Corporate and Financing give a baseline score.
- **Schedule.** t=0 initial roster; t=6 `ip_counsel`, `antitrust_analyst`, `tax_structuring_ai`;
  t=12 `schedules_builder`, `redline_explainer`; t=18 `regulatory_counsel`; t=25
  `funds_flow_coordinator`; t=30 `tax_structuring_ai` leaves; t=39 `redline_explainer` leaves.

## Source joins and leaves (after t=0)

| Source t | Change | Disposition |
|---|---|---|
| 6 | add `ip_counsel` | converted: specialist, Legal Diligence – Material Contracts, IP, & Privacy (t=6) |
| 6 | add `privacy_counsel` | dropped: no distinct gated task; would duplicate the contracts task |
| 6 | add `employment_counsel` | dropped: same |
| 6 | add `antitrust_analyst` | converted: specialist, Regulatory & Antitrust Assessment (t=6) |
| 6 | add `tax_structuring_ai` | converted: specialist, Deal Structure & Tax Planning (t=6) |
| 12 | add `schedules_builder` | converted: specialist, Drafting – SPA and Schedules (t=12) |
| 12 | add `redline_explainer` | converted: specialist, Negotiation & Redlines (t=12) |
| 12 | add `finance_counsel` | dropped: no gated task; the financing task stays a control |
| 12 | add `acquirer_cfo` | dropped: stakeholder-style role, no gated task |
| 12 | remove `diligence_reader` | dropped: no unassigned gated task would remain for a leave; `diligence_reader` stays on the roster |
| 18 | add `regulatory_counsel` | converted: specialist, Regulatory Filings (t=18) |
| 18 | add `cfius_analyst` | dropped: CFIUS is "if elected" in the source and overlaps the filings task |
| 18 | add `rwi_packager` | dropped: no gated task |
| 18 | remove `tax_structuring_ai` | converted as a leave, moved to t=30; unassigned gated task: Post-Closing & Day-1 Integration Readiness |
| 25 | add `funds_flow_coordinator` | converted: specialist, Closing Mechanics & Bring-Down Diligence (t=25) |
| 25 | add `target_ceo` | dropped: stakeholder-style role, no gated task |
| 35 | re-add `senior_mna_associate` | dropped: re-adds an agent already on the roster (not a join) |
| 45 | add `closing_checklist_manager` | moved to t=0: the remaining holder for the Signing & Closing leave case |
| 45 | remove `redline_explainer` | converted as a leave, moved to t=39; unassigned gated task: Signing & Closing |
| 55 | add `tax_partner` | moved to t=0: the remaining holder for the Post-Closing leave case |
| 55 | remove `antitrust_analyst` | dropped: after its task, nothing gated remains that only it could hold; leave count kept at two |

That is 21 listed changes; `team_benchmark.py plan` counts 20 (it does not count the t=35 re-add).
The scenario keeps 9 events, so `check` warns that 9 < 20; the 12 other changes are dropped or moved
as above.

## Task-to-worker mapping (judged, not measured)

A worker "holds" a task if its `system_prompt` contains the header the checklist requires.
I confirmed this by searching every worker prompt for each header.

| Affected task | Case | Event | Holds the format | `correct_agents` |
|---|---|---|---|---|
| Legal Diligence – Material Contracts, IP, & Privacy (`IP-CHAIN/v2`) | specialist | join `ip_counsel` t=6 | `ip_counsel` | `ip_counsel` |
| Regulatory & Antitrust Assessment (`HSR-SCREEN/v4`) | specialist | join `antitrust_analyst` t=6 | `antitrust_analyst` | `antitrust_analyst` |
| Deal Structure & Tax Planning (`STEP-PLAN/v3`) | specialist | join `tax_structuring_ai` t=6 | `tax_structuring_ai` | `tax_structuring_ai` |
| Drafting – SPA and Schedules (`SCHED-INDEX/v2`) | specialist | join `schedules_builder` t=12 | `schedules_builder` | `schedules_builder` |
| Negotiation & Redlines (`REDLINE-RATIONALE/v2`) | specialist | join `redline_explainer` t=12 | `redline_explainer` | `redline_explainer` |
| Regulatory Filings (`FILING-TRACKER/v1`) | specialist | join `regulatory_counsel` t=18 | `regulatory_counsel` | `regulatory_counsel` |
| Closing Mechanics & Bring-Down Diligence (`FUNDS-FLOW/v5`) | specialist | join `funds_flow_coordinator` t=25 | `funds_flow_coordinator` | `funds_flow_coordinator` |
| Post-Closing & Day-1 Integration Readiness (`TAX-COV-LEDGER/v1`) | leave | leave `tax_structuring_ai` t=30 | `tax_structuring_ai`, `tax_partner` | `tax_partner` |
| Signing & Closing (`CLOSING-SET/v2`) | leave | leave `redline_explainer` t=39 | `redline_explainer`, `closing_checklist_manager` | `closing_checklist_manager` |

Join tasks: only the joiner holds the format (the joiner passes, nobody else can). Leave tasks: the
leaver and one remaining worker hold it, so the task stays solvable and the leave changes who
should get it. A worker could in principle produce a header without being told it; a gate run would
measure that, and this judgment cannot.

## Leave timing

Both leavers should have finished everything assigned to them by their leave. This is **reasoned,
not enforced** (`check` cannot verify it; it depends on the manager's runtime assignments).

- `tax_structuring_ai` (leaves t=30) is gated only on Deal Structure & Tax Planning. That task needs
  Financial Diligence, Legal Diligence (Corporate and Contracts) and the Regulatory Assessment, which
  in turn follow Deal Intake and the RFI program: a chain of four dependency levels. The leaver also
  holds the post-closing ledger format, but that task sits behind Signing & Closing, so it is
  still unassigned at t=30.
- `redline_explainer` (leaves t=39) is gated on Negotiation & Redlines, which follows Drafting. Signing
  & Closing sits behind Closing Mechanics and Regulatory Filings, so it is unassigned at t=39.
- **Assumption:** each task finishes within about one to two timesteps of assignment, and the manager
  assigns at least one task per timestep. Task durations in the workflow are simulated hours, not
  timesteps.

## Assumptions and open items

- **Not run.** No run exists, `correct_agents` is unmeasured, and no gate-validation table exists.
- **Joins can be pre-empted.** Contracts, Regulatory Assessment and Deal Structure become ready
  shortly after the joins at t=6, and may be assigned to a non-holder earlier. Check against a first
  run, and move a join earlier if so.
- **Leave timing depends on the manager.** Under ML-049 (one action per timestep) the leaver may still
  hold an unfinished task at its leave. Check the first runs.
- **Engine support** the benchmark assumes but may not exist yet (see the planned rows in
  `UPDATES.md`): a roster-change notice to the manager, and restarting a handed-over running task
  (unused here, since this scenario has no running-task case).
- Open upstream bugs that distort scores: ML-052, ML-050, ML-051, ML-049, ML-092
  (`docs/team_non_stationarity/known_bugs.md`).
- Dropped workers (`privacy_counsel`, `employment_counsel`, `finance_counsel`, `acquirer_cfo`,
  `cfius_analyst`, `rwi_packager`, `target_ceo`) are not in this roster.
