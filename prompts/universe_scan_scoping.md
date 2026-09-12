# Unconditional universe scan — scope and feasibility ONLY

**Type:** scoping pass. **Executes no scan. Produces no measurement. Fits nothing.**
**Deliverable:** a written feasibility assessment and a cost estimate. That is all.
**Branch:** `scope/universe-scan`, cut from `master`. No `digest.json`. Charts only if T3 yields one.
**Standard:** `docs/Agent_Prompt_Standard.md` §10 and §12 apply. §7, §9 and §11 do not — there is no
measurement to chart and nothing to return to the strategy layer but prose.

> **Landing correction, 2026-08-30** — the branch base read `main`; there is no `main` in this repo
> (`origin/HEAD -> origin/master`), so it reads `master`. Nothing else changed. **This prompt carries no
> `[Cooper]` slot and no threshold**, so unlike Phases 10e and 12 it is not blocked by escalation row 2.

---

## Why this exists, and why it is overdue

`docs/Open-Items-Register.md` records this item as **upgraded to a near-front blocker by D5 consequence
(c) on 2026-08-03**, with the note *"Not scheduled — the phase that takes it on is not yet specified."*
It has been unscheduled ever since, while it multiplies every conditional result in the programme.

The problem, stated exactly:

- **The archive universe** is the q05 power-law filter applied to **completed daily moves**. Its
  selection variable is only knowable after the session ends.
- **The intended live universe** is a real-time screen at **≥ 30% from previous close, pre- and
  post-market inclusive**.
- These are **different populations**. Phase 8 A10.2d confirmed the rejected-candidate population is
  absent from `data/filtered/`, so **the live false-positive rate is not measurable from what is on
  disk** at all.

Under D5's gate-then-trade design the detector's fire-rate in the wild is a **direct PnL term**, not a
caveat. Every markout, every excursion, every cost ratio in this programme is conditional on
power-law-filter membership, which is not knowable at detection time. Risk rows **3, 4 and 9**.

**This pass does not fix that.** It establishes what fixing it would take, so the work can be scheduled
against a real cost instead of remaining an open item indefinitely.

---

## Constraints

- **Read-only on data.** No write to any table. No new materialization. Zero passes over
  `filtered_trades` or `filtered_quotes`.
- **The environment is offline (D14).** Any external data this pass identifies as necessary is named and
  costed, **not fetched**. "We would need X" is the deliverable; obtaining X is not.
- **No estimate of the false-positive rate may be stated**, even bounded, even hedged. Producing one is
  precisely the work this pass is scoping and it is not authorised here.
- **Describe, do not recommend.** The disposition is Cooper's.

---

## Tasks

- [ ] **T1 — Pin the live screen definition exactly**
  Reconstruct, from committed sources only, what the intended live screen fires on: the threshold, the
  reference price, the sessions included, the intraday evaluation frequency, and any universe
  pre-filters. **Cite every element to a file and line.** Where a source is silent or two sources
  disagree, **record the ambiguity rather than resolving it** — an unresolved element is a finding, and
  a screen definition assembled by inference is worse than an incomplete one. Commit.

- [ ] **T2 — Pin the archive selection function exactly**
  The same treatment for `filter_events_power_law.py` and the q05 construction. Risk row 2 records the
  filter's exact mechanics as **open, script unread**. Read it. State what it selects on, over what
  window, with what threshold, and what it necessarily cannot see — specifically whether its RTH-scoped
  `momentum_pct` construction (D4's universe-selection exception) can observe the extended-hours moves
  the live screen is meant to fire on. Commit.

- [ ] **T3 — What is already on disk that bears on the gap**
  Risk row 5 records *"`daily/` universe breadth for control-set construction"* as an open audit item.
  Audit it: how many distinct tickers, over what date range, with what completeness. **Report breadth
  only.** Do **not** construct a control set and do **not** compare populations beyond stating what a
  comparison would require. If a breadth chart is genuinely informative, one chart is permitted; it
  carries n and a caption and nothing else. Commit.

- [ ] **T4 — The gap, and what would close it**
  Enumerate every route to an unconditional population, each with: what data it needs, whether that data
  exists on disk, what it would cost to obtain, what it would and would not establish, and its failure
  mode. **At minimum consider:** a universe-wide daily bar source; an intraday scan replay over a
  historical window; flanking-day pseudo-controls (already noted as a partial patch, and its limits
  stated); and any route that establishes a *bound* rather than a rate. Commit.

- [ ] **T5 — Cost and sequencing**
  For each route in T4: an order-of-magnitude estimate in passes, wall time, and storage, using the
  programme's own measured throughput rather than a guess. State which routes are blocked by the offline
  constraint and which are not. **Propose no route.** Commit.

- [ ] **T6 — Write `results/scope_universe_scan/REPORT.md`**
  Audience is a fresh session with no context. Sections, in order: the two population definitions with
  every element cited; the ambiguities found and left unresolved; the `daily/` breadth audit; the route
  table from T4; the cost table from T5; and a closing section listing every question this pass could
  not answer and why. **Any prose the agent authored itself is quoted in full in its own labelled
  section**, per the `redirect_d5` precedent, so Cooper reviews the words rather than inferring them
  from a diff. Commit; `git status` clean.

---

## Escalation Criteria

| # | Condition | Action |
|---|---|---|
| 1 | Working tree dirty at T1 | Hard stop |
| 2 | Any pass over `filtered_trades` / `filtered_quotes` | Hard stop |
| 3 | Any write to a table, or any new materialization | Hard stop |
| 4 | Any estimate of the live false-positive rate, bounded or hedged, appears anywhere in the output | Hard stop — this pass scopes that work, it does not do it |
| 5 | A screen or filter element stated without a file-and-line citation | Hard stop |
| 6 | An ambiguity resolved by inference rather than recorded | Hard stop |
| 7 | A control set constructed, or populations compared | Hard stop — T3 reports breadth only |
| 8 | Any external fetch attempted | Hard stop — D14 |
| 9 | A route recommended, or characterised as best / cheapest / obvious | Report sent back |
| 10 | Write outside `results/scope_universe_scan/`, `prompts/`, `docs/Open-Items-Register.md` | Hard stop |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/universe_scan_scoping.md` | This prompt, committed first | [ ] |
| `results/scope_universe_scan/screen_definition.json` | T1 — every element with its citation, ambiguities flagged | [ ] |
| `results/scope_universe_scan/archive_selection.json` | T2 — the q05 filter's actual mechanics | [ ] |
| `results/scope_universe_scan/daily_breadth_audit.json` | T3 — tickers, date range, completeness | [ ] |
| `results/scope_universe_scan/routes_and_costs.json` | T4 + T5 | [ ] |
| `results/scope_universe_scan/REPORT.md` | The deliverable | [ ] |
| `docs/Open-Items-Register.md` | Risk rows 2, 3, 4, 5, 9 annotated with what this pass established | [ ] |

---

## Reporting

Post: the two population definitions with citations · the ambiguity list · the `daily/` breadth table ·
the route table · the cost table · the escalation check, all 10 rows · the unanswered-questions list ·
commit list.

**No recommendation. No route proposed. No rate estimated.**

---

## Approval Gate

This pass gates nothing and unblocks nothing on its own. It exists so that the scan can be **scheduled
against a real cost**. Cooper reads the report and decides whether, when, and by which route.
