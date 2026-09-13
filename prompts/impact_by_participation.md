# Impact by participation — the closing test on D24/D25

**Date:** 2026-09-11
**Type:** measurement phase. Not a numbered Operating Plan row — a targeted follow-on scoped by
`claude/what_would_change_a_decision.md` §2(a), written after D26 closed the timing channel and
asked what could still change a decision in the price/size channel.
**Branch:** `impact-by-participation`, cut from `phase/10e`, not `master`. **`origin/master` is 52
commits behind `phase/10e` as of this prompt** — its latest commit is D22, with D23 through D26 and
everything this prompt cites (D24, D25, `docs/Claude-Code-Operating-Plan.md`'s current row 11/13-17
annotations, `docs/Open-Items-Register.md`'s current entries) unmerged. Branching from `master` per
the generic convention would silently drop all of it. Flagged to Cooper separately — whether
`phase/10e` (or another branch) is overdue for a PR into `master` is outside this prompt's scope.
**Governing scope note:** every quantity here is price/size-channel work. **Not barred by D4**
(tick-derived), **not barred by D26** (D26 closes timing only). **Long-only, D5** — no short-side
variant is specified, implemented, or measured.
**Standard:** `docs/Agent_Prompt_Standard.md` **v1.3** conventions (Cooper-authored task list, single-
tier escalation table). **Not v1.4** — the live file's "Plan Authorship" / async-gate / two-tier-
escalation content is a draft that CLAUDE.md's Pointers section still does not point at, and no
prompt in this repo uses `Gate Mode` or `HARD STOP`/`LOG` tiers yet. Section numbers below follow
CLAUDE.md's citation: §9 Chart Contract, §10 Verification Block, §11 Digest Contract, §12 Git
Discipline.

---

## 0. Why this exists, and the gate it has to pass

`claude/what_would_change_a_decision.md` states the rule this whole document exists to serve:
**a phase runs only if a named decision, a threshold derived in advance, and both outcomes being
informative all hold at once.** Held against that gate:

- **Decision it moves:** **D24 and D25** (`docs/Universe-Decisions.md`). Both rest on a round-trip
  cost of **70.98 bp** (Phase 11 T7, `results/phase_11/artifacts/t7_cost_vs_capture.json`) treated
  as exogenous and flat — never conditioned on how the trade itself is worked.
- **Threshold:** derived from the gap D25 measured, not chosen (§1 below states it exactly).
- **Both outcomes informative:** if realised cost at achievable participation clears the threshold,
  D24/D25's barrier arithmetic reopens. If it does not, "costs bind, assumed" becomes "costs bind,
  measured" and D24/D25 close **final rather than provisional** — which is real information, not a
  null result to shrug off.

**What this phase is not.** It is not candidate (b) (ISO share as a hold-length variable) — that
candidate's threshold depends on this one and is explicitly sequenced after it
(`what_would_change_a_decision.md` §3). It is not a re-run of Phase 11 — Phase 11 is closed
(`docs/Claude-Code-Operating-Plan.md` row 11) and its frozen artifacts are read-only inputs here,
never rebuilt.

---

## 1. The pre-registered threshold, derived here so it is not chosen mid-run

**The closest cell.** Phase 10e Arm 1's 90-cell barrier grid (`results/phase_10e/artifacts/t4_gate.json`
→ `grid_summary_print_weighted`) has its closest-to-breakeven gap at **latency 1 min, horizon 60 min,
profit_k = 3, stop_m = 2, optimistic bound**: `p_clear = 0.3885` against `p_breakeven = 0.6000`, gap
**−0.2115** (the report's own headline, `results/phase_10e/REPORT.md:100-102`, rounds this to
"−0.210 / 21 percentage points" — the two are the same cell, minor rounding only).

**The barrier construction is cost-parameterised, exactly.** `research/phase_10e/t2_excursion.py:60-63,155-156`:
profit barrier `= profit_k × round_trip_bp`, stop barrier `= stop_m × round_trip_bp`, with
`round_trip_bp` read from `cfg["cost"]["round_trip_bp"]` — currently **70.98**. Because `p_breakeven
= (stop_m+1)/(profit_k+stop_m)` depends only on the **ratio** `profit_k : stop_m` and not on
`round_trip_bp`, holding `profit_k = 3, stop_m = 2` fixed and lowering `round_trip_bp` **shrinks both
barriers in absolute bp without moving `p_breakeven` off 0.6000.** Narrower absolute barriers are
easier for the same underlying price paths to touch before expiry, so `p_clear` should rise as
`round_trip_bp` falls — **by how much is not assumed, it is task T1's first measurement**, using
`results/phase_10e/artifacts/t2_excursion.parquet`'s per-event `mfe_h60` / `mae_h60` columns (already
materialized, no new tick pass) re-classified against a swept `round_trip_bp` rather than the fixed
70.98.

**The threshold, stated as a criterion rather than a number, because the number is T1's output:**
**the `round_trip_bp` at which the closest cell's optimistic `p_clear` reaches 0.6000.** T1 computes
it exactly. If T3's achievable-cost measurement clears that number, the gap closes; if not, it
doesn't, and both outcomes are reported without interpretation (Evidence Standard).

**What "participation" means here, and what it does not.** Phase 8's `pq_rth_open`
(`results/phase_8/artifacts/t3_participation.parquet`) is a **pre-open price-discovery-timing**
quintile — how much of the eventual move happened before the RTH open — **not** an execution
participation rate. Phase 11 T7 states plainly: *"Depth, queue position and fill probability are not
measured in this phase"* (`results/phase_11/REPORT.md:52`). **No trade-size-relative-to-concurrent-
volume variable exists anywhere in this checkout as of this prompt.** T0 confirms that rather than
assuming it either way.

---

## Context & Constraints

- Two-tier execution (`CLAUDE.md`): **T0–T2 run dev-tier only** (`dev_events` /
  `filtered_trades_dev` / `filtered_quotes_dev`, config `config/dev_sample_v3.json`). **No full-tier
  pass is authorised in this prompt** — T4 states the promotion criterion and stops for a Cooper gate
  before any full-tier query runs.
- DuckDB SQL over pandas. Never materialize `filtered_trades` (4.9B rows) or `filtered_quotes` (3.8B
  rows) into a dataframe, dev or full tier.
- D4: no spine numeric column (`prev_close`, `open`, `high`, `low`, `close`, `event_*`,
  `event_volume`, ...) enters any computed quantity. All measured quantities come from
  `filtered_trades` / `filtered_quotes` or their frozen derivatives
  (`event_quote_metrics_v1`, `t2_excursion.parquet`, `t4_gate.json`).
- Long-only (D5). No short-side, no SSR, no borrow logic.
- Universe membership: inner join to `momentum_events_canonical WHERE in_scope = TRUE` on every new
  query against `filtered_trades`/`filtered_quotes`.
- `results/phase_11/artifacts/`, `results/phase_8/artifacts/`, `results/phase_10e/artifacts/` are
  **read-only inputs.** Nothing in `results/phase_11/`, `results/phase_8/`, `results/phase_10e/`, or
  `src/` is written or rebuilt by this phase.
- Reuse before build (per the skill of that name): `research/phase_10e/t4_gate.py`'s touch-
  classification logic and `research/phase_11/t8_impact.py`'s Lee & Ready classification are reused,
  not reimplemented, wherever the task calls for the same computation at a different parameter.

---

## Tasks

- [ ] **T0 — Audit: does a participation-rate variable already exist?**
  Grep `research/phase_8/`, `research/phase_11/`, `data/Schema.md` / `docs/data/Schema.md`, and
  `docs/Research-Library-Map.md` for any trade-size-relative-to-concurrent-volume construct (POV,
  "participation rate", ADV ratio, order-size percentile against a volume reference). Report what
  exists and what does not, cited to file and line. **If something already answers this, T2 is
  rescoped to reuse it rather than build it — record that rather than building a duplicate.**
  Commit.

- [ ] **T1 — Derive the exact threshold**
  Read `results/phase_10e/artifacts/t2_excursion.parquet`'s `mfe_h60` / `mae_h60` columns for the
  latency-1/horizon-60 cell (D19: report the threshold in both bp and cents). Reusing
  `research/phase_10e/t4_gate.py`'s optimistic/pessimistic touch-classification exactly (import, do
  not reimplement — cite the function), sweep `round_trip_bp` downward from 70.98 holding
  `profit_k=3, stop_m=2` fixed, and report the `round_trip_bp*` at which optimistic `p_clear` first
  reaches 0.6000 (and, separately, where pessimistic does). If no swept value in a sensible range
  (e.g. down to 5 bp) reaches it, report that finding — a threshold with no achievable value in a
  plausible cost range is itself informative and is reported as such. Chart 01. Commit.

- [ ] **T2 — Construct the participation-rate variable** [gated on T0]
  On the dev sample only. Define, per trade print in `filtered_trades_dev`: participation rate =
  print size ÷ total trades-side volume in the same `{ticker, event, minute}` bar (the grain
  `event_quote_metrics_v1` already carries, so the denominator is a re-aggregation of what's cached,
  not a new pass over raw quotes). State the definition precisely — including how it handles the
  print's own size in its own denominator — before computing it, so the construction is auditable
  rather than incidental. Decile the result. Report the decile boundaries with n per decile. Chart 02.
  Commit.

  - [ ] T2a — If T0 found an existing variable, this task reads and deciles it instead. State which
    branch was taken.

- [ ] **T3 — Realised effective spread and impact by participation decile** [dev tier]
  Reusing `research/phase_11/t8_impact.py`'s Lee & Ready classification (delta = 0, sip basis, tick-
  rule fallback — the same rule, not a re-derivation) and its `eff_frac` construction, recompute
  effective spread (bp and cents, D19) **at the latency-1/horizon-60 cell specifically** (matching
  T1's cell, not a different one), grouped by T2's participation decile instead of `pq_rth_open`.
  Report the full distribution per decile (median, IQR, n) — not the mean alone (Evidence Standard).
  Chart 03.

  - [ ] T3a — Report whether the relationship is monotonic in participation, and state explicitly if
    it is not (a U-shape or other non-monotone pattern is a finding, not an error — see the caveat
    below).

- [ ] **T4 — Compare against T1's threshold, and the full-tier promotion gate**
  Compare T3's per-decile round-trip cost against T1's `round_trip_bp*`. **State plainly which
  deciles clear it and which do not, with n per decile — no interpretation of what this means for
  the strategy** (Evidence Standard; that is Cooper's call). **STOP HERE.** Do not run T5 or any
  full-tier query. Post T0–T4 for review. Full-tier promotion (re-running T2/T3 against
  `filtered_trades`/`filtered_quotes` proper) requires an explicit Cooper go-ahead and a frozen,
  committed config, per the two-tier rule.

- [ ] **T5 — Close the loop** [BLOCKED until Cooper approves promotion after T4]
  Using the full-tier achievable cost at the best-clearing decile from T3 (re-run full-tier), recompute
  `p_clear` at the closest cell via T1's same swept-`round_trip_bp` machinery. Report the resulting
  gap. This is the number that actually moves D24/D25 — everything before it is groundwork.

- [ ] **T6 — Charts, digest, report**
  `digest.json` per §11 and `REPORT.md` per §10, plus the cross-phase copy at
  `results/reports/impact_by_participation_report.md`. Every claim cites its chart. Commit; working
  tree clean.

**A caveat worth stating before any number arrives, because it nearly wasn't stated last time**
(`docs/Universe-Decisions.md` D26, root-cause note): **a monotonic "impact falls as participation
falls" relationship is not assumed here.** Phase 11 T8's own `pq_rth_open`-bucketed effective spread
is U-shaped, not monotonic (`results/phase_11/artifacts/t8_impact.parquet`: 65.5 / 48.4 / 48.3 / 50.1
/ 69.3 bp across its five buckets) — a different variable than T2's, but the shape is a reminder that
this repo's cost surfaces have not been monotonic where checked, and T3a exists to report the actual
shape rather than a slope.

---

## Escalation Criteria

| # | Condition | Action |
|---|---|---|
| 1 | Working tree dirty at T0 | Hard stop |
| 2 | Any pass over full-tier `filtered_trades` / `filtered_quotes` before T4's explicit Cooper approval | Hard stop |
| 3 | Any write to `results/phase_8/`, `results/phase_10e/`, `results/phase_11/`, or `src/` | Hard stop |
| 4 | A spine numeric column (D4) enters any computed quantity | Hard stop |
| 5 | A short-side or fade construct specified or implemented (D5) | Hard stop |
| 6 | T2's participation-rate definition changed after T3 has already been computed against it | Hard stop — redefine and rerun, do not patch results in place |
| 7 | Per-decile `n < 100` in a headline decile (min_cell_n, `config/phase_11.json`) | Report the decile as hatched; continue — not a stop |
| 8 | T1 finds no `round_trip_bp*` in [5, 70.98] that closes the gap | Report as a finding; continue to T2/T3 anyway — a known-unreachable threshold is still worth comparing achievable cost against, and is itself informative |
| 9 | T4's comparison shows achievable cost at or above 70.98 bp at every decile | Report; **do not propose or draft candidate (b) here** — that is a program-level "run nothing" question per `what_would_change_a_decision.md` §4, and it needs (b)'s own threshold computed independently, which this phase does not do |
| 10 | Write outside `results/impact_by_participation/`, `research/impact_by_participation/`, `prompts/`, `config/impact_by_participation.json`, `docs/Open-Items-Register.md` | Hard stop |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `results/impact_by_participation/charts/01_threshold_sweep.html` | At what `round_trip_bp` does the closest cell's `p_clear` reach breakeven? | x=`round_trip_bp` (log if the sweep spans a decade), y=`p_clear` (optimistic + pessimistic lines), breakeven line at 0.6000, both bounds shown | n at each swept point (same n throughout — the underlying events don't change, only the barrier) | No swept value approaches 0.6000; the curve is flat or moves the wrong way |
| 02 | `results/impact_by_participation/charts/02_participation_deciles.html` | What does the participation-rate distribution look like, and are the deciles balanced? | histogram of participation rate, decile boundaries marked, n per decile annotated | n per decile | Deciles are wildly unbalanced (a few deciles hold nearly all the mass) |
| 03 | `results/impact_by_participation/charts/03_cost_by_participation.html` | Does realised round-trip cost fall as participation falls? | x=participation decile, y=effective spread bp (violin + strip, not just median), n per decile, T1's threshold line overlaid | n per decile | No decile clears the threshold line; distributions overlap heavily across deciles with no separation |

Standard chart rules apply (Plotly, standalone HTML, one per file, n per bucket, log axes where
multiplicative, no smoothing, outliers shown not clipped, caption states sample/filters/config hash).

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/impact_by_participation.md` | This prompt, committed first | [x] |
| `config/impact_by_participation.json` | Barrier cell, sweep range, participation-rate definition, dev-sample pointer — committed before T1 runs | [ ] |
| `results/impact_by_participation/artifacts/t1_threshold.json` | T1 — swept `round_trip_bp*` and its derivation | [ ] |
| `results/impact_by_participation/artifacts/t0_audit.json` | T0 — what exists, what doesn't, cited | [ ] |
| `results/impact_by_participation/artifacts/t2_participation.parquet` | T2 — per-print participation rate, dev tier | [ ] |
| `results/impact_by_participation/artifacts/t3_cost_by_decile.{json,parquet}` | T3 — effective spread by decile, dev tier | [ ] |
| `results/impact_by_participation/charts/01_threshold_sweep.html` | Chart 01 | [ ] |
| `results/impact_by_participation/charts/02_participation_deciles.html` | Chart 02 | [ ] |
| `results/impact_by_participation/charts/03_cost_by_participation.html` | Chart 03 | [ ] |
| `results/impact_by_participation/REPORT.md` | The deliverable | [ ] |
| `results/reports/impact_by_participation_report.md` | Cross-phase copy | [ ] |
| `results/impact_by_participation/digest.json` | Machine-readable return path | [ ] |
| `docs/Open-Items-Register.md` | The wrong-partition entry annotated with T4's result either way | [ ] |
| `docs/Claude-Code-Operating-Plan.md` | Append-only note recording this pass against row 18/19's price/size channel | [ ] |

T5's outputs are not listed — they are blocked pending the T4 gate and will be specified when that
approval lands.

---

## Verification

Every headline number in the report carries: the exact script/function that produced it, row counts
in and out of every filter step, a one-line reproduction command, and the config hash — per
`docs/Agent_Prompt_Standard.md` §10. A number without a reproduction path is treated as not produced.

---

## Reporting

On completion of T0–T4, post:
1. T0's audit finding (exists / does not exist, cited)
2. T1's threshold sweep table and `round_trip_bp*`
3. T2's participation-decile boundaries and n
4. T3's cost-by-decile table, full distribution, not medians alone
5. T4's comparison against threshold, decile by decile, no interpretation
6. Escalation check table, all 10 rows
7. Output file table with status filled in

**No recommendation. No claim about what this means for D24/D25 — that comparison is stated as data
and left for Cooper to read.**

---

## Approval Gate

**T0–T4 may run without a live check-in** (dev-tier, read-only against frozen artifacts and the dev
sample, no table writes). **T4 is a hard stop by construction** (escalation is silent on it because
the task itself says stop) — full-tier promotion and T5 require Cooper's explicit review of T0–T4's
results first. This prompt itself — the threshold derivation in §1, the participation-rate
definition in T2, and the dev-tier scope — is posted for Cooper's review before T0 begins, per this
programme's standing practice of a design review before a phase that could reopen a closed decision
starts spending compute.
