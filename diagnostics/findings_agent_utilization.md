# Agent utilization after mid-episode joins — backlog-opportunity check

## Question

Original claim (from gpt-4o-mini runs): the manager "ignores new agents" —
most mid-episode joiners are never assigned a task, or are assigned very
late. Before trusting that claim, the obvious objection is: maybe there
just wasn't any work for them to do. This note checks that objection.

## Method

Added `had_backlog_opportunity` to each `AgentJoinAnalysis` entry in
`diagnostics/analyze_diagnostic_runs.py` (`check_had_backlog_opportunity`,
using `get_backlog_by_timestep`). For each joiner, it looks at the window
from their `join_timestep` to their `first_assignment_timestep` (or to the
end of the run, if never assigned), and checks whether `pending + ready`
task counts (from the manager's own per-timestep observation in
`timestep_data/final_metrics.json`) were ever > 0 during that window.

**This is a floor check, not proof of a capability match.** Tasks have no
structured `required_capabilities` field — `agent_capabilities` is freeform
text the manager must reason about semantically — so there's no cheap way
to confirm a *specific* task needed *that* agent's skill. `True` means
"there was *some* unclaimed work sitting in the queue the whole time they
waited" — it rules out "the backlog was completely empty," but doesn't
prove the backlog contained work matching their specialty. `None` means no
usable timestep data existed in that window (e.g. the agent joined after
the run's recorded metrics ended).

## Result: `had_backlog_opportunity` is `True` almost universally

Run on the two full-model (non-`_mini`) benchmarks currently available —
`legal_m_and_a` and `marketing_campaign`, across `cot`, `random`, and
`assign_all` — every single never-assigned or delayed joiner shows
`had_backlog_opportunity=True`, with the sole exceptions being a couple of
very-late joiners (e.g. `tax_partner` joining at t=55) where timestep data
ran out and the field is `None` (not `False`).

Examples (cot, `marketing_campaign`):
```
! cmo joined@t=0 (NEVER_ASSIGNED) capabilities_visible_at_join=True had_backlog_opportunity=True
! seo_analyst_ai joined@t=5 (NEVER_ASSIGNED) capabilities_visible_at_join=True had_backlog_opportunity=True
! creative_director_ai joined@t=10 (delayed_lag=23) capabilities_visible_at_join=True had_backlog_opportunity=True
```

Examples (cot, `legal_m_and_a`):
```
! acquirer_gc joined@t=0 (NEVER_ASSIGNED) capabilities_visible_at_join=True had_backlog_opportunity=True
! ip_counsel joined@t=6 (delayed_lag=7) capabilities_visible_at_join=True had_backlog_opportunity=True
! regulatory_counsel joined@t=18 (NEVER_ASSIGNED) capabilities_visible_at_join=True had_backlog_opportunity=True
```

Same pattern holds for `random` and (structurally, since it only ever
assigns once at t=0 and therefore can never assign to any later joiner by
construction) `assign_all`.

## Interpretation

- **The "no work available" explanation does not hold.** There was
  unclaimed backlog the entire time these agents waited, in both cot and
  random, on both full-model benchmarks. This strengthens rather than
  undermines the original "manager under-utilizes new agents" claim.
- **What's still open:** whether the *specific* tasks sitting in that
  backlog actually required the joiner's specialty. That's not checkable
  without a structured capability/requirement tag on tasks or a semantic
  LLM-judge pass over task descriptions vs. agent capability text — out of
  scope for this floor check.
- **`assign_all` is a structural non-comparison for this question** — it's
  a one-shot assignment pass at t=0 (`OneShotDelegateManagerAgent` in
  `manager_agent_gym/core/manager_agent/random_manager.py`), so by design it
  can never assign a task to an agent that joins later, regardless of
  backlog. Its never-assigned counts shouldn't be read as evidence of
  "ignoring" new agents the same way cot/random's can.

## Follow-up: cross-mode evidence of genuine fit (`assigned_in_another_mode`)

`had_backlog_opportunity` only proves *some* work existed, not that any of
it matched the joiner's specific skills. As a free, no-LLM way to get at
that, added `assigned_in_another_mode` to `AgentJoinAnalysis`
(`get_agents_assigned_in_other_modes` in `analyze_diagnostic_runs.py`): for
each joiner, check whether that same `agent_id` was ever assigned a task in
a *different* manager_mode's run of the same workflow/seed. If another
manager matched it to a real task, the agent's capabilities clearly map to
something in this workflow's task pool — making "never assigned here"
harder to wave away as "no fit," and easier to read as this run's manager
under-utilizing a genuinely useful agent. `False` is weaker evidence (could
still mean a real skill/task mismatch, or that every mode we have data for
missed the same opportunity).

Caveat: `assign_all` is a one-shot t=0 assignment
(`OneShotDelegateManagerAgent`), so it can never assign anything to a
post-t0 joiner regardless of fit — its `False` contributes no information
for those agents, though a `True` from it (for a starting-roster agent) is
still valid evidence.

### Result: mixed — most non-assignments are NOT corroborated elsewhere

Re-running on `legal_m_and_a` / `marketing_campaign` × cot/random:

- **cot, marketing_campaign**: of 21 flagged joiners, only `consent_compliance_ai`
  (joined t=0, eventually assigned late) shows `True` — assigned by random
  too. The other 20 show `False`: no mode we have data for ever used them.
- **cot, legal_m_and_a**: of 17 flagged joiners, only `deal_counsel_ai` and
  `acquirer_gc` (both t=0 starting-roster agents) show `True`. The rest
  (all `t>=6` joiners) show `False`.
- **random**: shows more `True`s than cot for early/starting-roster agents
  (since it's being checked against cot, which used a few of them), but
  **late joiners (t>=18) are `False` across the board, in every mode
  checked** — no manager mode we have data for ever assigned these agents
  anything.

### Revised interpretation

The strongest, most defensible claim shifts to: **late-joining specialists
(t>=18, e.g. `regulatory_counsel`, `cfius_analyst`, `funds_flow_coordinator`,
`target_ceo`, `closing_checklist_manager` in legal_m_and_a) are never used
by *any* manager mode we've tested**, not just cot. That's either a
genuine shared blind spot across all three baseline strategies, or those
agents' capabilities simply never matched anything left in the backlog by
the time they joined (which — given `had_backlog_opportunity=True` for all
of them — means backlog existed, just maybe not backlog suited to them).

For *early* joiners (t=0 or shortly after), there's now real corroborating
evidence for a handful (`consent_compliance_ai`, `deal_counsel_ai`,
`acquirer_gc`, several in `random`'s legal_m_and_a run) that a fit existed
and cot specifically missed it — that subset is now a stronger case of
"cot under-utilizes an agent another mode found useful."

## Caveats / follow-ups

- This was run only on the two full-model benchmarks currently available
  (`legal_m_and_a`, `marketing_campaign`); re-run once more full-model
  benchmarks exist.
- `None` entries (timestep data ran out before/at join) should be excluded
  from "confirmed opportunity" counts rather than treated as true or false.
- Natural next step: a continuous assignment-latency metric (lag normalized
  by remaining episode length after join) to quantify how much the new
  model closed the gap vs. the gpt-4o-mini runs, rather than relying on the
  binary `delayed`/`never_assigned` flags.
