# ISO share as a hold-length state variable — candidate (b)

**Date:** 2026-09-12
**Type:** measurement phase. Not a numbered Operating Plan row — a targeted follow-on scoped by
`claude/what_would_change_a_decision.md` §2(b), run after candidate (a) (impact by participation,
`prompts/impact_by_participation.md`) closed negative and, per §3 of that same document, either
raised or left candidate (b)'s own threshold in place.
**Branch:** `iso-share-hold-length`, cut from `master` — `master` fast-forwarded to `phase/10e`'s
tip on 2026-09-12 (PR #1, merge `e32bbfe`) and Agent Prompt Standard v1.4 landed in the same
history (PR #2, merge `5b80914`), so `master` is the current, up-to-date base and there is no
stale-branch risk this time.
**Standard:** `docs/Agent_Prompt_Standard.md` **v1.4** (adopted 2026-09-12, this is the first prompt
written against it). Section numbers below follow v1.4: §3/§3b Plan Authorship / Task Checklist
(skipped here — see the callout in §3, this phase's targets are pre-registered below, but the
route to them is not yet derived far enough for agent-authored planning to be safe), §5 Escalation
Criteria (two-tier, `HARD STOP`/`LOG`), §6 Output File Contract, §9 Approval Gate, §10 Chart
Contract, §11 Verification Block, §12 Digest Contract, §13 Git Discipline. **The Control Standard**
(above §1 in the standard) governs every "separates continuation from fade" claim below — see T3.
**Governing scope note:** price/size-channel work throughout. **Not barred by D4** (every input is
tick-derived or a cost-config constant). **Not barred by D26** (D26 closes the *timing* channel
only, and its own §"survives and carried forward" names ISO share of aggressive volume as a
by-product Phase 11/this channel is unblocked to use). **Long-only, D5** — no short-side or fade
*execution* construct is specified or implemented; "fade" below is a descriptive label for a
markout outcome, never a position.

---

## 0. Why this exists, and the gate it has to pass

Per `claude/what_would_change_a_decision.md` §2(b): **decision it moves** is D5's successor
question — an entry/hold-length condition, not D5 itself (archived). **Threshold:** ISO share
observed at or before the entry anchor must separate a "continuation" subgroup from the pooled
population by enough that the subgroup's own markout clears the 70.98 bp round-trip cost — derived
below from the already-committed Phase 8/10e markout re-read, not chosen. **Both outcomes
informative:** if it clears, D5's successor question reopens with a real, ex-ante-available state
variable; if it does not, it closes the price/size channel's most literature-supported candidate
(Chakravarty, Jain, Upson & Wood, *Clean Sweep*, JFQA 2012 — ISOs carry disproportionate price
discovery relative to volume share) and narrows D26's "not evidence these events lack tradeable
structure" considerably, per the source document's own framing.

**What candidate (a) changed and did not change.** Per `what_would_change_a_decision.md` §3, if (a)
had confirmed the 70.98 bp stack outright, (b)'s threshold would be known and possibly
unreachable before starting; if (a) had come back materially lower, (b)'s threshold would move and
the channel would reopen more easily. **What (a) actually returned is neither pole.** The exact
reclassification (`results/impact_by_participation/REPORT.md` §7-8) needed a round-trip cost of
**~11.0 bp** to close the nearest barrier cell's gap — an 84.5% reduction from baseline — and the
cheapest achievable participation decile delivered only a 28.5% reduction (50.71 bp), **4.6×** short.
**So the cost floor this phase is held to is the original 70.98 bp, unmoved** — (a)'s measured
reduction was real but far too small to relax it.

**This is explicitly a hold-length question, not an entry-timing one.** D24's cost-scaling argument
(fixed cost against √H movement) has already closed entry-timing improvements. Every comparison
below holds the **entry anchor fixed** (detection + 5 minutes — Phase 11's own "cost of record"
latency, `results/phase_11/REPORT.md`) and varies only the **hold horizon**.

---

## 1. The pre-registered threshold, derived here from already-committed artifacts

**Source, re-read not re-measured.** `results/phase_10e/artifacts/t5_costed_markouts.json` —
Phase 8's markout grid, already re-cut against the 70.98 bp cost in the post-10e pass (no tick pass,
no new computation; `research/phase_10e/t5_costed_markouts.py`). At **latency = 5 minutes**, the
grid's `median_gap_to_cost_bp` by horizon:

| horizon | approx. hold | pooled median markout (bp) | gap to 70.98 bp cost (bp) | **required separation** |
|---|---|---|---|---|
| det+15 | 15 min | −62.9 | −133.9 | 133.9 bp |
| det+30 | 30 min | −129.5 | −200.5 | 200.5 bp |
| det+60 | 60 min | −189.8 | −260.7 | 260.7 bp |
| t0_close | ~3.25 h | −249.5 | −320.5 | 320.5 bp |
| t1_close | ~1 session later | −575.1 | −646.1 | 646.1 bp |
| t3_close | ~3 sessions later | −790.9 | −861.8 | 861.8 bp |

**What "required separation" means, precisely.** For a given horizon, the high-ISO-share subgroup's
**own conditional median markout** must exceed +70.98 bp for that subgroup to be a tradeable
"continuation" bucket. Because the pooled median at every horizon is already deeply negative, the
subgroup has to improve on the pooled median by at least the tabulated amount — that is the primary
criterion, computed per horizon in T3/T4. The raw separation itself (high-group median minus
low-group median) is reported alongside as a secondary, always-informative statistic, since the
source document's own phrasing ("separates continuation from fade") is stateable either way and
Evidence Standard bars picking one framing and hiding the other.

**Reference, not just a threshold** (`what_would_change_a_decision.md` §5: "a threshold without a
reference is a number without a scale"). The only other print-level covariate measured on this exact
cohort is candidate (a)'s participation rate, and its **achieved** separation in round-trip-equivalent
cost was **50.71 bp (cheapest decile) to 71.46 bp (priciest decile) — a 20.75 bp range**
(`results/impact_by_participation/REPORT.md` §6/§8). If ISO share, another print-level microstructure
covariate on the same cohort, produces separation of similar order (tens of bp), it falls roughly an
order of magnitude short of even the smallest required separation above (133.9 bp at det+15), and two
orders short of the day-scale requirement (646–862 bp). **This is a plausibility calibration, not an
assumption about ISO share's behavior** — T3/T4 measure the real thing directly, and a result at or
above this reference scale would itself be a notable finding regardless of whether it clears cost.

---

## Context & Constraints

- **The `conditions` column is not in DuckDB.** `DESCRIBE filtered_trades` / `filtered_trades_dev_v4`
  (checked 2026-09-12) carry no `conditions` field — it was dropped at ingestion. ISO share **cannot**
  be built from the ingested DuckDB tables and must be read from the raw per-event files
  (`data/filtered/{TICKER}_{DATE}_{MP}/trades.parquet`, column `conditions`, a list of SIP codes),
  exactly as `research/scale_field/fragmentation_identity.py` already does (`COLS`, `read_full()`).
  **Reuse that reader and its per-event file helpers (`trade_files()`, `session_window()` from
  `research/phase_10/common.py` / `research/phase_10d_diag1/common.py`) — do not write a second
  path to the same files.** This is a targeted per-event read (50 dev events, two files each), not a
  full-table materialization, and does not conflict with the DuckDB-SQL-over-pandas rule, which
  governs the 4.9B/3.8B-row ingested tables specifically.
- **Condition code 14 = Intermarket Sweep is CONFIRMED**, not `[verify]` — D26 point 3
  (`docs/Universe-Decisions.md`), supplied from the public trade-conditions glossary at Cooper's
  review. No re-derivation needed.
- Two-tier execution: **T0–T4 run dev-tier only** (the 50 `primary`-cohort events,
  `config/dev_sample_v3.json`, `dev_cohort='primary'` — per the same correction candidate (a)'s T2
  needed, `results/impact_by_participation/REPORT.md` §4). No full-tier pass (~15,337 candidate
  events) is authorised in this prompt.
- D4: no spine numeric column enters any computed quantity. `conditions`, `size`, `price`, and every
  timestamp field are tick-derived, not spine.
- Long-only (D5). No short-side, no SSR, no borrow logic. "Fade" is a markout-outcome label only.
- **The Control Standard applies to T3's central claim** ("ISO share separates continuation from
  fade by enough to matter"). All four controls (negative, positive, null-parameter sweep,
  blindness) are required before that claim is reported as anything more than a raw number — see T3.
- `results/phase_8/`, `results/phase_10e/`, `results/phase_11/`, `results/impact_by_participation/`
  are **read-only inputs**. Nothing in them, or in `src/`, is written or rebuilt by this phase.
- Reuse before build: `research/scale_field/fragmentation_identity.py`'s condition-code reading;
  Phase 8/10e's detection-anchor and minute-index machinery (T0 identifies the exact function to
  reuse for "minutes since detection" before T2 computes anything against it).

---

## Tasks

- [ ] **T0 — Audit: the entry-anchor window, exactly**
  Two things, both cited to file and line before T2 runs:
  1. Confirm the read path above (`conditions` absent from DuckDB; raw parquet is the only source)
     against the live schema, not just this prompt's 2026-09-12 check.
  2. Identify the **exact existing function or artifact** that converts a raw trade's
     `sip_timestamp` into "minutes since detection" for a given event, matching Phase 8/10e's own
     convention (candidates: `research/phase_10e/t1_candidate_entries.py`'s `det_minute` construction,
     or Phase 8's own detection-anchor script). **Reuse it — do not redefine detection time.** State
     which function is reused and what "detection time" means operationally (a price-trigger
     crossing, a bar index, etc.) before T2 computes any window against it.
  Report both findings, cited. If no existing function cleanly exposes a per-event detection
  timestamp (only a bar/minute index), state that and specify the fallback (converting via the
  session-calendar minute grid Phase 8/10e already use) rather than inventing a new one. Commit.

- [ ] **T1 — No computation.** §1 above is the pre-registered threshold table, derived entirely from
  the already-committed `t5_costed_markouts.json` — this task is a no-op placeholder confirming that
  re-derivation was not needed and nothing here required a tick pass. State that explicitly in the
  commit message rather than skipping the task silently.

- [ ] **T2 — Construct the ISO-share variable** [gated on T0]
  On the 50 dev-tier `primary` events only. Definition, stated precisely before computing:
  `iso_share(event) = SUM(size WHERE 14 IN conditions, t <= detection_time + 5min) / SUM(size, t <=
  detection_time + 5min)`, window starting at the event's T=0 session open (confirm this start
  bound against Phase 8's own convention in T0 — do not assume it silently). Report per-event
  `iso_share`, the raw numerator/denominator (n prints, n ISO-flagged prints), and coverage (what
  fraction of the 50 events have at least 1 print in the window — a thin or empty window is a
  legitimate outcome to report, not to paper over). Chart 01.

  - [ ] T2a — Report the `iso_share` distribution's shape (it is very likely right-skewed and
    possibly zero-inflated — most events will have few or no ISO prints in a 5-minute window; state
    the actual shape rather than assuming one).

- [ ] **T3 — Does ISO share separate continuation from fade? All four controls required.**
  Join T2's per-event `iso_share` to the markout values already computed in
  `results/phase_8/artifacts/a102_detection_markout_grid.parquet` at latency=5, for horizons
  det+15/det+30/det+60/t0_close/t1_close/t3_close (§1's table). Split events into groups by
  `iso_share` (see T3c for the boundary rule) and report each group's median markout per horizon,
  against the required-separation table in §1.

  - [ ] T3a — **Negative control.** Repeat the identical split-and-compare procedure using a
    placebo variable expected to carry no signal (e.g., parity of the event's ticker's first
    character, or a fixed pseudo-random assignment seeded independently of any real data). Report
    that the placebo shows no material separation — if it does, the procedure itself is suspect and
    that is reported before any ISO-share number is trusted.
  - [ ] T3b — **Positive control.** Run the same procedure on candidate (a)'s own
    `participation_rate` decile split (`results/impact_by_participation/artifacts/t2_participation.json`)
    against this phase's markout grid (not (a)'s effective-spread measure) — a known real, if small,
    effect on this exact cohort. Confirm the pipeline detects *something* at that known scale before
    trusting a null on ISO share.
  - [ ] T3c — **Null-parameter sweep, and blindness.** The high/low `iso_share` split boundary is
    swept across at least 5 quantile cut points (e.g., median, and the 30/40/60/70th percentiles),
    not chosen once. **The boundary is never selected by which cut maximizes markout separation** —
    state this rule explicitly and confirm the reported result does not depend on having picked a
    favorable cut. Report the full sweep, not just one point.
  - [ ] T3d — **Sustained, not momentary.** Per the hold-length framing (§0), report whether any
    real separation found **grows or persists** across det+15 → t3_close, or whether it appears only
    at short horizons (which would read as entry-timing, already closed by D24, and would be
    reported as such rather than claimed as a hold-length finding).
  Chart 02.

- [ ] **T4 — Compare against §1's threshold, and the full-tier promotion gate**
  State plainly, per horizon: does the high-ISO-share group's conditional median clear +70.98 bp
  (§1's primary criterion)? What is the raw separation, and how does it compare to candidate (a)'s
  20.75 bp reference scale (§1's secondary criterion)? No interpretation of what this means for D5's
  successor question or for `what_would_change_a_decision.md` §4's "run nothing" gate — that is
  Cooper's call (Evidence Standard). **STOP HERE.** Do not run T5 or any full-tier query. Post
  T0–T4 for review.

- [ ] **T5 — Full-tier confirmation** [BLOCKED until Cooper approves promotion after T4]
  Re-run T2/T3's per-event read across the full ~15,337-candidate-event universe
  (`results/phase_10e/artifacts/t1_candidate_entries.parquet`'s event list), each requiring a raw
  per-event parquet read (no DuckDB shortcut exists for `conditions` — flag the wall-clock cost of
  ~15,337 × 2 file reads before running, since this is a real, if bounded, expense unlike candidate
  (a)'s T5 which reused an already-materialized cache).

- [ ] **T6 — Charts, digest, report**
  `digest.json` per §12 and `REPORT.md` per §11, plus the cross-phase copy at
  `results/reports/iso_share_hold_length_report.md`. Every claim cites its chart. Commit; working
  tree clean.

---

## Escalation Criteria

Stop and post results only for `HARD STOP` rows. `LOG` rows continue and are recorded in `digest.json`.

| # | Condition | Threshold | Tier | Action |
|---|---|---|---|---|
| 1 | Working tree dirty at T0 | any | HARD STOP | Commit, post results, await instruction |
| 2 | Any pass over full-tier `filtered_trades`/`filtered_quotes`, or full-tier per-event reads, before T4's Cooper approval | any | HARD STOP | Commit, post results, await instruction |
| 3 | Write to `results/phase_8/`, `results/phase_10e/`, `results/phase_11/`, `results/impact_by_participation/`, or `src/` | any | HARD STOP | Commit, post results, await instruction |
| 4 | A spine numeric column (D4) enters any computed quantity | any | HARD STOP | Commit, post results, await instruction |
| 5 | A short-side or fade *execution* construct specified or implemented (D5) | any | HARD STOP | Commit, post results, await instruction |
| 6 | T2's `iso_share` definition or window changes after T3 has computed against it | any | HARD STOP | Redefine and rerun; do not patch results in place |
| 7 | A per-group `n < 100` in a headline split (min_cell_n convention, `config/phase_11.json`) | `n < 100` | LOG | Continue; note in `surprises` |
| 8 | T3's negative control (T3a) shows material separation on the placebo variable | separation ≥ smallest required-separation value in §1 (133.9 bp) | HARD STOP | The procedure is suspect before any ISO-share number is trusted — stop and report |
| 9 | T3's positive control (T3b) fails to detect candidate (a)'s known small effect at its known scale | detected separation < 10 bp (half of candidate (a)'s smallest measured decile-pair gap) | HARD STOP | The pipeline may be tuned deaf (Control Standard, "blindness") — stop and report before trusting any null |
| 10 | The `iso_share` window (T0/T2) has coverage below half the dev sample (fewer than 25 of 50 events with ≥1 print in window) | `coverage < 0.50` | LOG | Continue; report the thin-coverage caveat prominently in T2/T3 |
| 11 | T4 shows no horizon clears §1's threshold at any swept cut point | all horizons fail | LOG | Report; **do not invoke `what_would_change_a_decision.md` §4 here** — that needs this result read together with candidate (a)'s, which is Cooper's synthesis, not this phase's |
| 12 | Write outside `results/iso_share_hold_length/`, `research/iso_share_hold_length/`, `prompts/`, `config/iso_share_hold_length.json`, `docs/Open-Items-Register.md`, `docs/Claude-Code-Operating-Plan.md` | any | HARD STOP | Commit, post results, await instruction |

If multiple `HARD STOP` rows trigger at once, report in table order.

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `results/iso_share_hold_length/charts/01_iso_share_distribution.html` | What does the per-event `iso_share` distribution look like, and how much mass is zero/near-zero? | histogram (log-y if zero-inflated), coverage annotation, n | n events, n with ≥1 print in window | All mass at exactly 0 with no variation to split on |
| 02 | `results/iso_share_hold_length/charts/02_markout_by_iso_group_and_horizon.html` | Does the high/low `iso_share` split separate markout, and does any separation grow with horizon? | x=horizon (det+15…t3_close, ordered), y=median markout bp, one line per split group, negative/positive control lines overlaid, §1's required-separation threshold marked per horizon | n per group per horizon | Real, placebo, and positive-control lines are indistinguishable, or the real line does not move with horizon |

Standard chart rules apply (Plotly, standalone HTML, one per file, n per bucket, no smoothing,
outliers shown not clipped, caption states sample/filters/config hash).

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/iso_share_hold_length.md` | This prompt, committed first | [x] |
| `config/iso_share_hold_length.json` | Entry latency, horizon list, cost constant (read from `config/phase_10e.json`, not re-chosen), quantile-sweep cut points, dev-sample pointer | [ ] |
| `research/iso_share_hold_length/{t0_audit,t2_iso_share,t3_separation,t4_compare}.py` | Task scripts | [ ] |
| `research/iso_share_hold_length/chart_{01,02}_*.py` | Chart scripts | [ ] |
| `results/iso_share_hold_length/artifacts/t0_audit.json` | T0 — reused-function citation and window definition | [ ] |
| `results/iso_share_hold_length/artifacts/t2_iso_share.{json,parquet}` | T2 — per-event `iso_share`, dev tier | [ ] |
| `results/iso_share_hold_length/artifacts/t3_separation.json` | T3 — full sweep, both controls, sustained-vs-momentary read | [ ] |
| `results/iso_share_hold_length/artifacts/t4_compare.json` | T4 — comparison against §1's thresholds | [ ] |
| `results/iso_share_hold_length/charts/01_iso_share_distribution.html` | Chart 01 | [ ] |
| `results/iso_share_hold_length/charts/02_markout_by_iso_group_and_horizon.html` | Chart 02 | [ ] |
| `results/iso_share_hold_length/REPORT.md` | The deliverable | [ ] |
| `results/reports/iso_share_hold_length_report.md` | Cross-phase copy | [ ] |
| `results/iso_share_hold_length/digest.json` | Machine-readable return path | [ ] |
| `docs/Open-Items-Register.md` | Candidate (b) entry, closed either way, with §4's two-candidate synthesis flagged as Cooper's open call | [ ] |
| `docs/Claude-Code-Operating-Plan.md` | Append-only note against row 18/19's price/size channel | [ ] |

T5's outputs are not listed — blocked pending the T4 gate.

---

## Verification

Every headline number carries: the exact script/function that produced it, row counts in and out of
every filter step, a one-line reproduction command, and the config hash — per
`docs/Agent_Prompt_Standard.md` §10, and per its field note, the config hash covers the `iso_share`
window definition and the cut-point list, not only computational parameters. A number without a
reproduction path is treated as not produced.

---

## Reporting

On completion of T0–T4, post:
1. T0's reused-function citation and confirmed window definition
2. §1's threshold table (already in this prompt — confirm no re-derivation was needed)
3. T2's `iso_share` distribution and coverage
4. T3's full sweep table, both controls' results, and the sustained-vs-momentary read
5. T4's comparison against threshold, horizon by horizon, no interpretation
6. Escalation check table, all 12 rows
7. Output file table with status filled in

**No recommendation. No claim about D5's successor question or about
`what_would_change_a_decision.md` §4 — those are stated as data and left for Cooper to read,
alongside candidate (a)'s already-closed result.**

---

## Approval Gate

**Gate Mode: async.** T0–T4 may run without a live check-in (dev-tier, read-only against frozen
artifacts and the dev sample, no table writes) — this mirrors candidate (a)'s own Approval Gate, and
this prompt itself continues the same reviewed gate document (`what_would_change_a_decision.md`)
candidate (a) was run under, rather than opening a fresh, unreviewed line of work. **T4 is a hard
stop by construction.** Escalation rows 8 and 9 (control failures) are the two conditions that block
even inside the async gate — a failed negative or positive control means the T0–T3 numbers
themselves are not yet trustworthy, and reporting them further would defeat the point of running the
controls at all. Full-tier promotion (T5) requires Cooper's explicit review of T0–T4 first.
