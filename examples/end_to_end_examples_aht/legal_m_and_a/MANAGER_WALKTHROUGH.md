# Manager Agent Walkthrough — `legal_m_and_a` AHT Variant

**What this is:** a manual, offline dry run of the manager's decisions across this scenario's
task graph and pool timeline — done by reasoning it through directly, not by running
`scripts/run.sh` (no OpenAI API calls; per `CLAUDE.md`, that script is never run without an
explicit ask). The goal is to sanity-check, concretely, whether the benchmark's mechanics
(task descriptions, requirements checklists, pool timeline) actually discriminate a correct
assignment from an incorrect one — the thing all the schema/doc work exists to make possible.

**Method:** at each point a task becomes ready, I only use what the manager would actually see —
task `name` + `description`, and the live roster's `agent_description`/`agent_capabilities` (free
text) — never the hidden `requirements` checklist or the trait tuple. Assignment decisions below
are what a competent reader would plausibly conclude from that information alone. For the six
AHT-graded tasks (T6a, T6b, T9a, T9b, T13b, T13c — 4 checkpoints: 2x Objective 1, 2x Objective 2)
I additionally drafted a plausible in-character output for each candidate assignment and graded it
by hand against the actual deterministic substring checks in `workflow.py`, so the pass/fail
claims below are checked, not assumed.

**Regenerated a third time — now with 4 graded checkpoints, not 2.** History: pass 1 fixed the
timeline (`docs/benchmark_aht/index.md` rules 1–2: no reassignment-on-leave, no removal before a
bundle is genuinely done). Pass 2 fixed a labeling bug the first pass introduced (rule 3: reason
strings must name a specialty, never a task ID — this is what surfaced `finance_counsel_ai` and
`rwi_packager` both being implicitly "for" T9). Pass 3 (this one) acts on that finding rather than
just working around it: **T9 is now split into T9a "Debt Commitment Review" / T9b "RWI Insurance
Packaging"** (checkpoint 2, Objective 1 — resolves the ambiguity outright instead of leaving it a
judgment call), and **T13c "Post-Signing Tax Position Reconfirmation"** is added (checkpoint 4,
Objective 2 — formalizes the T8→T13 tax-reuse pattern that was previously just an unformalized
"bonus pattern"). The episode now tests cold-start fit twice (checkpoints 1–2) and reuse-recognition
twice (checkpoints 3–4), instead of once each.

---

## 1–2. Timestep-by-timestep roster and delegation

`ip_counsel_ai`/`privacy_counsel_ai` (`P_privacy_reasoning`) never leave — its cold-start bundle
explicitly spans T6b *and* T13b from t=6 onward, so rule 2 can't fire on it until after T13b,
which is the entire mechanism the reuse test depends on.

| t | Roster joins | Roster leaves | Newly ready tasks | Assignment | Rationale |
|---|---|---|---|---|---|
| **0** | `project_coordinator`, `diligence_reader`, `deal_counsel_ai` | — | T1 Deal Intake & Objectives (+ subtasks) | T1 → **`project_coordinator`** | Only ready task; "runs issue/RFI/decision trackers" matches kickoff/deal-memo work directly. `project_coordinator` is cold-start bundled onto T1+T2+T15 for the whole run; `diligence_reader` is bundled onto **T3+T4+T5 as one demand window** (rule 1 — it stays on all three until done, never split); `deal_counsel_ai` is bundled onto T6a+T10, ahead of readiness. |
| **≈6** | `ip_counsel_ai`, `privacy_counsel_ai`, `antitrust_analyst`, `regulatory_strategist_ai`, `tax_structuring_ai` | — | T2, T3, T4, T5, T6a, T6b, T7 | T2 → **`project_coordinator`** (already bundled at t=0); T3, T4, T5 → **`diligence_reader`** (single bundle, per t=0); T7 → **`antitrust_analyst`** (bundled with the later T12 reuse); **T6a → `deal_counsel_ai`**, **T6b → `ip_counsel_ai` or `privacy_counsel_ai`** (bundled with the later T13b reuse) | T6a/T6b are the Objective-1 decision point — worked in full in §3.1–3.2. *(No true QoE specialist exists on this roster for T4 specifically — a pre-existing coverage gap, unrelated to the timing fix.)* |
| **12** | `schedules_builder`, `redline_explainer`, `finance_counsel_ai` | — | (T9a nearly ready) | fresh capacity staged ahead of readiness; `finance_counsel_ai`'s "debt-commitment/financing-coordination demand" reason (rule 3 — no task named) points at **T9a Debt Commitment Review** once it reads the task text (checkpoint 2's first half — see §3.3) | None of these cover a departure — `diligence_reader`'s T3/T4/T5 bundle is still running, untouched, alongside them. |
| **≈18** | `cfius_analyst`, `rwi_packager` | `diligence_reader` | T8 Deal Structure & Tax Planning (nearly ready); T9b nearly ready | T8 → **`tax_structuring_ai`** (already on the roster since t=6); `rwi_packager`'s "RWI underwriting-coordination demand" points at **T9b RWI Insurance Packaging** (checkpoint 2's second half — see §3.3) | `diligence_reader`'s T3+T4+T5 bundle is **`COMPLETED`**; T10 isn't ready yet — still gated on T8. Rule 2 satisfied cleanly, no hand-off needed. Checkpoint 2 is now visible as two genuinely disjoint pools (`P_debt_commitment_fast`, `P_rwi_ops_fast`), unlike the old single-`P_closing_ops_fast` build where this was ambiguous. |
| **≈25** | `funds_flow_coordinator`, `senior_associate_ai` | `tax_structuring_ai` | T9a, T9b, T10 Drafting SPA v1 | **T9a → `finance_counsel_ai`**, **T9b → `rwi_packager`** (both clean matches now — see §3.3); T10 → **`senior_associate_ai`** (switches off `deal_counsel_ai`'s earlier bet — see §3.6) | `tax_structuring_ai`'s T8 bundle is **`COMPLETED`** — leaves on time. Splitting T9 removed the ambiguity outright rather than leaving it a judgment call; T10 remains ungraded but is resolved cleanly by capability match. |
| **≈25–45** | `closing_checklist_manager`, `tax_partner_ai` (at 45) | `redline_explainer` (at 45) | T11 Negotiation & Redlines, T12 Filings, T13 Closing Mechanics | T11 → **`redline_explainer`** (its bundle completes before it leaves); T12 → **`antitrust_analyst`** (bundled with T7 since t=6; `cfius_analyst` a plausible alternate for the CFIUS half); T13 → **`closing_checklist_manager`** | `redline_explainer`'s T11 bundle is **`COMPLETED`** before its t=45 departure. `tax_partner_ai`'s join is a *fresh* demand tied to **T13c** (checkpoint 4 — see §3.5), unrelated to `tax_structuring_ai`'s already-finished departure 20 timesteps earlier. |
| **≈50** | — | — | T13b Post-Signing Privacy/IP Bring-Down; T13c Post-Signing Tax Position Reconfirmation | T13b: **`privacy_counsel_ai`** (intended reuse) vs. **`closing_checklist_manager`** (plausible red herring) — §3.4. T13c: **`tax_partner_ai`** (intended reuse) vs. a generalist (§3.5) | Two Objective-2 decision points now, not one. Neither roster event marks readiness, by design — `P_privacy_reasoning` has sat unremovable since t=6, `tax_partner_ai` since t=45. |
| **55** | — | `antitrust_analyst` | — | — | T7+T12 bundle **`COMPLETED`** (filings submitted) — leaves on time; `regulatory_strategist_ai`/`cfius_analyst` remain. |
| **tail** | — | — | T14 Signing & Closing, T15 Post-Closing & Day-1 | T14 → **`closing_checklist_manager`**; T15 → **`project_coordinator`** | Direct capability matches; T15 was part of `project_coordinator`'s original t=0 bundle. |

---

## 3. The four graded decision points, worked in detail

### 3.1 T6a — clean discrimination (works as intended)

**Task:** *"Review the target's key commercial contracts for consent-to-assign and
most-favored-nation triggers, and flag any provisions that could disrupt continuity of the
counterparty relationship after closing; summarize negotiation-relevant terms and open issues for
the SPA drafting team."*
**Checklist:** needs `"indemnif"` + `"covenant"` (req 1) and `"termination"` (req 2), threshold 2.

**Correct assignment — `deal_counsel_ai`:**

> Reviewed the top-12 revenue contracts and three critical vendor agreements for consent-to-assign
> and MFN triggers ahead of the SPA close. Four contracts contain change-of-control consent
> requirements; two carry MFN language that could be triggered by post-closing pricing changes. On
> continuity: several agreements contain termination-for-convenience clauses exercisable by the
> counterparty on a change of control, which could disrupt key customer relationships if
> triggered. Recommend the SPA carry indemnification protection and specific covenants requiring
> the seller to use best efforts to secure consents and to indemnify the buyer for losses arising
> from a counterparty's exercise of termination rights.

Check: "indemnif" ✓, "covenant" ✓, "termination" ✓ → **2/2, PASS.**

**Counterfactual — misassigned to `ip_counsel_ai`:**

> Reviewed the referenced commercial contracts through an IP and licensing lens. No embedded
> open-source licensing conflicts identified. Assignment mechanics appear standard; no
> chain-of-title concerns arise since these are non-IP vendor agreements. Recommend confirming
> with commercial counsel whether any require counterparty consent to assign.

Check: no "indemnif," no "covenant," no "termination" → **0/2, FAIL.** T6a discriminates exactly
as designed — good fit passes, wrong-specialty fit fails visibly.

### 3.2 T6b — the checklist can fail even when the manager assigns the right pool

**Task:** *"Assess whether the target's intellectual property can be established as cleanly
owned, including any third-party or openly-licensed code embedded in the product that could
create encumbrances; separately, evaluate whether the target's practices for sharing data with
vendors and moving it across jurisdictions meet buyer-side expectations..."*
**Checklist:** needs `"chain-of-title"`/`"chain of title"` + `"OSS"` (req 1) **and**
`"DPA"`/`"data processing agreement"` + `"cross-border"` (req 2), threshold **2** (both required).

The task description itself says "separately" — it bundles two genuinely disjoint specialties
(IP ownership vs. data/privacy) into **one task with one `assigned_agent_id`**. `P_privacy_reasoning`
has exactly two members, each covering one half:

**Assigned to `ip_counsel_ai` only** (its own specialty — IP/OSS):

> Validated chain-of-title for the core patent portfolio and confirmed clean assignment from all
> three founding engineers via PIIA agreements. OSS scan of the codebase identified two
> GPL-licensed components in a non-distributed internal tool (low risk) and one MIT-licensed
> dependency in the shipped product (no obligations triggered). No unresolved IP ownership
> encumbrances. On the data-handling side, a lightweight review suggests standard data-sharing
> terms are in place; a fuller assessment of the target's **cross-jurisdiction** data practices
> would benefit from dedicated privacy counsel input, which I'd recommend routing separately.

Check: req 1 — "chain-of-title" ✓ + "OSS" ✓ → **passes**. req 2 — no "DPA"/"data processing
agreement", and "cross-jurisdiction" ≠ "cross-border" → **fails**. **Net: 1/2 → below threshold
→ task_credit = 0**, despite `ip_counsel_ai` being a legitimately correct pool member.

**Assigned to `privacy_counsel_ai` only** (its own specialty — data/privacy):

> Assessed the target's data-sharing agreements with its top five processors and its
> **cross-border** transfer mechanisms for EU/UK personal data; found two vendor relationships
> relying on outdated transfer mechanisms that should be remediated via updated **DPAs** before
> close. On intellectual property, a preliminary read of the engineering repo did not surface
> obvious licensing red flags, but a full **chain-of-title** and open-source audit would need IP
> counsel's sign-off before this item can be cleared.

Check: req 2 — "DPA" ✓ ("DPAs") + "cross-border" ✓ → **passes**. req 1 — "chain-of-title" ✓ but no
literal "OSS" ("open-source" doesn't contain that substring) → **fails**. **Net: 1/2 → below
threshold → task_credit = 0 again.**

**Finding:** neither correct-pool member, individually, reliably clears T6b's threshold — not
because the manager assigned the wrong pool, but because the task requires *both* pool members'
distinct specialties inside a single-agent output, and the engine only supports one
`assigned_agent_id` per task. A perfectly-reasoning manager can get this exactly right and the
benchmark would still score it as a miss. **This is a scenario-authoring defect, not a manager
failure** — it would silently penalize good assignment behavior. Two fixes, either is sufficient:
split T6b into two subtasks (mirroring how T6 was already split into T6a/T6b), one per specialty
with its own single requirement; or lower `requirements_pass_threshold` to 1 so either specialist
alone can clear it (weaker test of "did the manager get the full picture," but at least
non-punishing).

### 3.3 T9a/T9b — checkpoint 2, and a cleaner pair than T6a/T6b

**T9a "Debt Commitment Review":** *"Review the buyer's proposed financing package for the
acquisition — confirm debt commitments are firm and assess whether the credit terms among lenders
could complicate closing certainty; prepare whatever closing-readiness confirmations the lenders
will require."* **Checklist:** needs `"intercreditor"` + `"solvency"`, threshold 2.

**Correct assignment — `finance_counsel_ai`:**

> Confirmed all three debt commitment letters remain firm through the extended outside date.
> Reviewed the credit terms among the syndicate lenders and flagged one intercreditor provision
> that could complicate closing if the mezzanine tranche isn't subordinated cleanly — recommend
> resolving before signing. Lenders will require updated solvency certificates from the company's
> CFO dated within 5 business days of closing; drafting the certificate template now.

Check: "intercreditor" ✓, "solvency" ✓ → **2/2, PASS.**

**Counterfactual — misassigned to `rwi_packager`:**

> Reviewed the buyer's financing materials from an insurance-coordination lens. No RWI-specific
> gaps identified in the financing package. Recommend confirming with the debt team whether any
> lender conditions overlap with policy exclusions.

Check: no "intercreditor," no "solvency" → **0/2, FAIL.**

**T9b "RWI Insurance Packaging":** *"Prepare the insurance underwriter's submission package to
support the buyer's warranty coverage — compile diligence findings the underwriter will want to
see, and be ready to explain how known risk items are being handled outside the policy."*
**Checklist:** needs `"exclusion"` + `"risk allocation"`, threshold 2.

**Correct assignment — `rwi_packager`:**

> Assembled the underwriting packet with the top diligence findings flagged for underwriter
> review. Reconciled the policy's proposed exclusions against the SPA's risk allocation — two
> known litigation items are carved out as exclusions consistent with the indemnity cap, and I've
> documented the rationale for the underwriter's file.

Check: "exclusion" ✓, "risk allocation" ✓ → **2/2, PASS.**

**Counterfactual — misassigned to `finance_counsel_ai`:**

> Reviewed the insurance submission requirements from a financing-coordination perspective.
> Confirmed the underwriter has been added to the closing distribution list. No specific
> commentary on policy terms — recommend routing detailed underwriting questions to the RWI team.

Check: no "exclusion," no "risk allocation" → **0/2, FAIL.**

**Finding: checkpoint 2 discriminates cleanly in both directions**, unlike T6b — both halves of
the original T9 map to exactly one specialist each, with no leftover bundled specialty. This is
what splitting T9 (rather than leaving it a single-assignee judgment call, per the earlier
revision's T9/T10 section) actually buys: a clean, gradable Objective-1 pair instead of an unresolvable
bundling defect.

### 3.4 T13b — the reuse test is trivially satisfiable regardless of assignment

**Task:** *"Reconfirm that the representations underpinning the original data-sharing and
intellectual-property review still hold true as of the closing date..."* — **name:**
`"Post-Signing Privacy/IP Bring-Down"`.
**Checklist:** needs `"bring-down"` + (`"privacy"` or `"IP"`), threshold 1.

Per `ai_agent_prompts.py`'s `AI_AGENT_TASK_TEMPLATE`, the executing agent receives **both**
`task_name` and `task_description` — so "Bring-Down" and "Privacy/IP" reach the model via the
name alone, regardless of who gets assigned. Two demonstrations:

**A plausible, believable wrong assignment — `closing_checklist_manager`** (a *realistic*
red herring: its own capability list literally says "Runs bring‑down confirmations," making it a
tempting pick purely by keyword proximity to "Bring-Down," despite having no privacy/IP
expertise):

> Post-Signing Privacy/IP Bring-Down — Status. Per the closing checklist, all standard bring-down
> confirmations are complete: conditions precedent satisfied, consents current, signature packets
> executed. No changes to privacy or IP representations have been flagged by the deal team since
> the original diligence review; treating those reps as reconfirmed for the closing set absent
> contrary notice.

Check: "bring-down" ✓, "privacy" ✓, "IP" ✓ → **PASSES** — despite doing **zero actual privacy/IP
verification work**, just echoing the task's own title and waving the item through ("absent
contrary notice"). This is the worst-case outcome the whole `requirements` mechanism exists to
catch, and it slips through anyway.

**The "correct" reuse assignment — `privacy_counsel_ai`** also passes, but largely because any
agent that titles its output after the task name (a completely ordinary habit) gets "Privacy/IP"
for free:

> **Post-Signing Privacy/IP Bring-Down** — Reconfirmation. Re-verified the data-sharing and
> cross-border transfer posture assessed during the original review: no changes to DPA terms with
> the top-five processors...

Both the right and the wrong assignment pass, for the same reason (the header echoes the task
name). **Finding:** T13b's single requirement is currently non-discriminating almost by
construction — it cannot currently tell a genuine reuse-recognition from a rubber stamp. This
compounds the task-name leak already flagged separately: fixing the description wasn't enough
while the name still carries "Bring-Down"/"Privacy/IP." Recommend renaming the task (e.g.
"Post-Closing Diligence Reconfirmation") **and** rewriting the requirement to need something a
generalist parroting the title couldn't produce — e.g., require the output to reference a specific
artifact only the original T6b review would have produced (a named transfer mechanism, a specific
processor, a specific OSS finding), not just the words "privacy"/"IP" appearing anywhere.

### 3.5 T13c — checkpoint 4, a cleaner reuse test than T13b

**Task:** *"Reconfirm that the tax elections and structural assumptions underpinning the deal
remain accurate as of the closing date, and flag any change since the original structuring
analysis."* **Checklist:** needs `("338(h)(10)"` or `"336(e)")` **and** `("rollover"` or
`"earnout")`, threshold 1. Unlike T13b, the name ("Post-Signing Tax Position Reconfirmation")
names the *domain* (tax) but not the technical terms the checklist searches for, and the
description doesn't leak them either — a lesson applied directly from T13b's failure (§3.4).

**Correct reuse — `tax_partner_ai`** (on the roster since t=45 for exactly this purpose,
matching its own profile: "validates rollover/earnout metrics and finalizes tax provisions and
bring-down confirmations"):

> Reconfirmed the target's 338(h)(10) election remains valid post-signing with no intervening
> ownership changes that would disqualify it. Rollover equity mechanics for the founder group are
> unchanged from the structuring memo; earnout thresholds tied to the Year-1 revenue target still
> align with the original tax treatment. No changes to flag for the closing set.

Check: "338(h)(10)" ✓ and ("rollover" ✓ / "earnout" ✓) → **requirement passes, 1/1, PASS.**

**Counterfactual — misassigned to `closing_checklist_manager`** (a plausible pick purely by
proximity — it's already running T13's general closing mechanics):

> Confirmed the closing checklist item for tax reconfirmation is marked complete per the deal
> team's sign-off. No changes flagged since the original structuring analysis; treating this as
> reconfirmed for the closing set.

Check: no "338(h)(10)"/"336(e)", no "rollover"/"earnout" → **FAIL.** Unlike T13b's equivalent
counterfactual, this one actually fails — because neither the task name nor the description hands
out the technical vocabulary a genuine tax reconfirmation would use, a rubber-stamp answer has
nothing to echo. **Finding: checkpoint 4 is a working reuse test**, in direct contrast to
checkpoint 3 (T13b, §3.4).

### 3.6 T10 — resolved by capability matching (ungraded)

T10 has no `requirements` checklist, so nothing here scores — but rule 3 forced an actual decision
instead of reading one out of a comment, so it's worth showing the reasoning. **T10 — "Produce SPA
v1 reflecting structure and diligence; seed disclosure schedules and consent lists."** Two clauses,
three candidates on the roster by t=25:

| Candidate | Capabilities | Covers |
|---|---|---|
| `deal_counsel_ai` (on roster since t=0) | Drafts/negotiates SPA sections, tracks redline deltas, harmonizes definitions | SPA drafting only |
| `schedules_builder` (since t=12) | Builds disclosure schedules, cross-references to SPA, tracks exceptions/evidence | Schedule-seeding only |
| `senior_associate_ai` (since t=25) | **Drafts SPA and ancillary documents, coordinates disclosure schedules**, runs diligence calls, prepares decision memos | **Both clauses** |

`senior_associate_ai` is the only candidate whose own profile spans both halves of the task — not
a coin flip. **Resolution: T10 → `senior_associate_ai`.** This means `deal_counsel_ai`'s t=0
cold-start bet on T10 doesn't pan out as the better fit once a fuller-matching profile shows up at
t=25 — a legitimate *switch*, not chasing a shinier newcomer: there's textual evidence
(`senior_associate_ai` literally covers the clause `deal_counsel_ai` doesn't), not just recency.
T10 remains the one ambiguous-but-ungraded case in this scenario; if it's ever pulled into a graded
objective, it would need the same split treatment T9 just got.

---

## 4. Overall suitability verdict

- **T6a works as intended** — right pool passes, wrong pool visibly fails. Objective-1 half of the
  scenario is sound for this task.
- **T6b does not currently work**, even for a manager that reasons perfectly — the two-specialty
  bundle behind a single `assigned_agent_id` means correct-pool assignments can still fail the
  threshold. This needs a scenario-authoring fix (split the task, or lower the threshold) before
  it can be trusted as an Objective-1 signal.
- **T9a/T9b work as intended (§3.3)** — same clean discrimination as T6a, in both directions, on
  both halves. Checkpoint 2 is sound, and splitting T9 (rather than leaving it an unresolved
  judgment call) is what made that possible.
- **T13b does not currently work (§3.4)** — both correct and incorrect assignments pass, because
  the task name alone (independent of the description fix already made) hands the executing agent
  the exact words the checklist searches for, and titling a deliverable after its task name is
  normal behavior, not a shortcut unique to a lazy or wrong agent. Checkpoint 3 is not currently
  measuring anything.
- **T13c works as intended (§3.5)** — the correct reuse passes, a plausible rubber-stamp wrong
  assignment fails, because neither the name nor the description hands out the technical
  vocabulary the checklist searches for. Checkpoint 4 is sound, and applying T13b's lesson (don't
  leak through the name) directly to a new task is what made that possible.
- **T10 remains the one loose end (§3.6, ungraded):** resolves cleanly by capability match
  (`senior_associate_ai` covers both clauses), so it's not currently a problem — but it's the same
  shape of bundling that made T6b and the old T9 defective, just not yet pulled into a graded
  objective. Same for T12 (HSR+CFIUS bundle, not deep-dived here). Worth splitting if either is
  ever promoted to a checkpoint.

**Bottom line:** of the 4 checkpoints this episode now carries, **3 work as designed** (checkpoints
1, 2, 4 — T6a, T9a/T9b, T13c) and **1 doesn't (checkpoint 3 — T13b)**, for the same root cause
already diagnosed and not yet fixed: the task's own name leaks the checklist's answer regardless of
description wording. That's a real improvement in signal density from the 2-checkpoint version (1
of 2 working) to the 4-checkpoint version (3 of 4 working) — going from 2 to 4 checkpoints didn't
just add volume, applying what T13b got wrong to fixing T9 and building T13c correctly is what
pushed the working fraction up. The roster timeline itself cleanly satisfies all three design rules
throughout (§1–2). Recommend fixing T6b's single-assignee/two-specialty mismatch and T13b's
name-leak — rename it and drop the technical-term requirement to something T13c-style, not
leakable through either name or description — before treating a real run of this scenario as
evidence of anything.
