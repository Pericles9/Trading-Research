# Phase 13 — Fundamental Partition Test — REPORT

**Branch:** `phase/13` · **Config hash:** `b15ff5a2e0d0` · **Gate mode:** sync-required
**Status:** **CLOSED, 2026-09-14 — as read, uncorrected. See the banner immediately below
before reading any number in this report.**

> ## CLOSURE BANNER, 2026-09-14 — read this before any number below
>
> **T4 (tick-level confirmation, Cooper-triggered 2026-09-14, targeting T3b) found a real,
> quantified, one-directional look-ahead bias in every headline number in this report.**
> `research/phase_13/t1_build_p0.py`'s window selection
> (`minute_index <= t0_minute_index + h`) always includes the full final minute bucket,
> whose clock-time end lands up to 60 seconds past the intended `t0 + h minutes` mark.
> Population median excess: **59.14 seconds** (73% of events use a minute-bucket-constructed
> `t0`, so the offset into that final minute is under 1 second for most of the population —
> not a random ~30s average). As a share of the labeled horizon, median excess is **19.7% at
> 5 min, 6.6% at 15 min, 3.3% at 30 min, 1.6% at 60 min.** Confirmed directly: on 50 dev-tier
> events, tick-derived and bar-derived MFE cost-multiple disagreed one-directionally
> (bar-derived value never smaller) in 36% of events at 5 min, 14% at 15/30/60 min. Full
> diagnosis: `research/phase_13/t4b_lookahead_diagnosis.py`,
> `results/phase_13/artifacts/t4b_lookahead_diagnosis.json`.
>
> **Every number below except T1's coverage stats is affected** (coverage asks whether a bar
> exists at all, not the window's exact length — unaffected). This reaches T1 (P0 itself), T2
> (the price-decile control arm), and T3a/b/c (all three fundamental splits) — every MFE/MAE
> figure in this document runs slightly rich, worst at the shortest horizon.
>
> **Cooper's decision, 2026-09-14: close as read, uncorrected.** No rebuild was authorized.
> Per `CLAUDE.md`'s Escalation rule, this is the "wait for instruction" outcome, not silence —
> instruction was given, and it was not to spend the compute on a full T1-T3 rebuild. This is
> a defensible close, not a shortcut: Phase 13 was already explicitly **"exploratory, no kill
> condition"** (Cooper's own 2026-09-13 amendment, see below) — no decision or threshold ever
> hinged on these exact numbers being unbiased, only on the general shape of the
> distributions, which a bias worst at 19.7% of the shortest horizon and shrinking to 1.6% by
> 60 min is unlikely to reverse for the largest separations reported (T3b's ~3x population
> gap, for instance). **Every number in this report should be read as biased slightly toward
> larger MFE/MAE than the true tick-level value, worse at short horizons, and no split
> comparison here should be treated as more precise than that.** Full record:
> `docs/Universe-Decisions.md` D37.

This phase executes D32 Amendment A1: it partitions the universe on three pre-`t0`
fundamental observables against a newly built population-scale outcome (P0), with
detection-price decile as the competing explanation (arm zero). **Per Cooper's
2026-09-13 amendment, this report contains no pass/fail declaration on any split** — no
kill condition was evaluated, T3b/T3c ran undirected, and T3a's pre-registered direction
is reported as a comparison point, not a verdict. See `prompts/phase_13.md`'s amendment
note for the full account of that departure from D25/D26's standing caution.

---

## 1. T0 — Branch, config

`phase/13` cut from `master` after PR #5 (`build/fundamentals-f1`) merged.
`config/phase_13.json` committed before any run: entry reference `t0`, horizon grid
5/15/30/60 min, per-event cost-unit source `event_quote_metrics_v1`, split directions
(T3a pre-registered, T3b/T3c undirected), `kill_condition.enabled: false`, cross-cuts by
event year × `detection_price_decile` with a `min_cell_n_log_threshold` of 200.

`prompts/phase_13.md` itself was drafted and approved in the same session but never
written to disk — caught by `tools/verify_cited_paths.py` before it could compound,
reconstructed and committed separately (see §6, Surprises).

## 2. T1 — P0: the population-scale outcome

Per event, MFE/MAE from `t0` at 5/15/30/60 min in units of that event's own round-trip
cost (`2 × tw_spread_bp`, `event_quote_metrics_v1`). Built as one bulk join across
`event_minute_bars_v2` (46M rows) rather than per-event point queries, after a
diagnostic query showed the per-event approach was pathologically slow on that table.

**Coverage — Chart `01_p0_coverage.html`.**

| | n | share |
|---|---|---|
| Minute-bar coverage, population | 15,763 / 20,951 | 75.2% |
| Round-trip-cost coverage, population | 14,864 / 20,951 | 70.9% |
| Minute-bar coverage, 2020–2024 | 15,763 / 15,763 | 100.0% |
| Minute-bar coverage, 2025 | 0 / 5,188 | 0.0% |

Escalation row 5 (LOG) fires: population coverage 75.2% < 80%. Read by year rather than
as one number, this is a **hard temporal cutoff**, not a scattered gap:
`event_minute_bars_v2` and `event_quote_metrics_v1` simply have no 2025 rows yet.
2020–2024's coverage sums to exactly 15,763 — Build F1's own
`a102_detection_anchors.parquet` row count.

## 3. T2 — Arm zero: detection-price-decile control

**Chart `02_arm_zero_price_decile.html`.** No fundamental data. Decile 0 (cheapest)
shows the highest median MFE cost-multiple at every horizon (1.43x at 5 min rising to
2.66x at 60 min, n=1,400); decile 9 (most expensive) is lower at every horizon (0.95x →
2.03x, n=1,589). The pattern across the middle deciles is not monotonic. This is the
baseline every fundamental split below is read against — a split whose cells simply
track price decile is not telling us anything fundamentals-specific.

## 4. T3 — Fundamental partitions

Three splits, each cross-cut by event year and detection-price decile (60 cells each,
6 years × 10 deciles). 344/356/472 of ~560 (year × decile × side) cells fall below
`config.cross_cuts.min_cell_n_log_threshold` (200) — flagged per-cell in the charts
(escalation row 7, LOG), not hidden by coarsening the cut.

**Quality gating, applied before any split was built:** `flg_dilution_form_before_t0`
and `spl_reverse_split_365d` both default to `False` when their own quality column
reads `unavailable` — confirmed by direct crosstab, not assumed. Splitting on the raw
boolean would fold "we don't know" into the "no" side. Both splits are gated to
quality-known rows only:

| Split | Excluded (unavailable) | Share |
|---|---|---|
| T3a `flg_dilution_form_before_t0` | 248 / 20,951 | 1.2% |
| T3c `spl_reverse_split_365d` | 12,219 / 20,951 | 58.3% |
| T3b share turnover (undefined value) | 8,980 / 20,951 | 42.9% |

### T3a — `flg_dilution_form_before_t0`. Chart `03_flg_dilution_split.html`.

Pre-registered by the architect's signed-off proposal: dilution-filing events were
expected to show worse continuation and a faster flip. **Population-aggregate reading
(no cross-cut) at 15 min:**

| | n | median MFE cost-mult | median MAE cost-mult |
|---|---|---|---|
| No filing | 13,656 | 1.53 | 1.95 |
| Filing before `t0` | 1,155 | 2.00 | 2.20 |

Both MFE and MAE are higher for the filing group at every horizon (5/15/30/60 min),
not just one — the population aggregate runs opposite the pre-registered MFE direction,
and the two legs move together rather than one worsening at the other's expense. Stated
as a population-level observation only; charts 03's year × decile cross-cut shows this
is not uniform across cells. No kill condition exists to fail; this is not a finding
about which side is "better," only a description of what the distributions show.

### T3b — Share turnover (split-adjusted). Chart `04_shs_turnover_split.html`.

Undirected (Cooper's amendment, "no pre reg"). Turnover = event-day tick volume /
`shs_shares_outstanding`, split-adjusted via `spl_last_split_ratio` when a split falls
between the share count's as-of date and `t0` (1,741/20,951 events needed the
adjustment). Split at the population median among the 11,971 events with a defined
value.

| | n | median MFE cost-mult (15 min) |
|---|---|---|
| Below median turnover | 5,587 | 0.91 |
| Above median turnover | 5,852 | 2.67 |

The largest population-aggregate separation of the three splits — roughly 3x — at
every horizon checked. Reported as a distribution; see chart 04 for the full
year × decile picture, where the separation is not uniform.

### T3c — `spl_reverse_split_365d`. Chart `05_spl_reverse_split.html`.

Undirected, same basis as T3b.

| | n | median MFE cost-mult (15 min) |
|---|---|---|
| No reverse split in trailing 365d | 3,263 | 1.60 |
| Reverse split in trailing 365d | 2,599 | 1.70 |

The smallest population-aggregate separation of the three splits — close to
indistinguishable at every horizon checked.

### Chart `06_all_splits_summary.html`

All three splits' two sides plus arm zero's ten deciles, one look, same y-axis scale,
horizon and metric togglable, no reference line, no shading, no ranking — built to let
Cooper compare without any category being visually marked a winner.

## 5. Escalation check

| # | Condition | Tier | Observed | Fired? |
|---|---|---|---|---|
| 1 | Working tree dirty / data-root bypass | HARD STOP | clean throughout | No |
| 2 | Any output states a split's result as a verdict | HARD STOP | 0 (2 false-hits corrected during drafting, see §6) | No |
| 3 | A single cell singled out as "the finding" | HARD STOP | none | No |
| 4 | Fundamental column used as a computed-outcome input | HARD STOP | 0 (verified) | No |
| 5 | Coverage by horizon < 80% | LOG | 75.2% | **Yes** |
| 6 | `_quality='unavailable'` folded into a boolean split unguarded | HARD STOP | 0 (gated, verified) | No |
| 7 | Cross-cut cell below `min_cell_n_log_threshold` | LOG | 344/356/472 cells | **Yes** |
| 8 | Spine numeric column reaches a computation | HARD STOP | 0 (verified) | No |
| 9 | Write outside the phase's allowed paths | HARD STOP | none | No |
| 10 | *(added retroactively, T4, 2026-09-14)* A reported outcome variable's window carries a look-ahead defect | HARD STOP | T1's window selection always includes up to 60s past the labeled horizon; confirmed by tick-level test | **Yes — see §10** |

## 6. Surprises (full list in `digest.json`)

- `prompts/phase_13.md` was approved in-session but never committed at T0 — caught by
  `tools/verify_cited_paths.py`, reconstructed and committed as its own commit before
  T3 could compound the gap.
- T3's first draft cross-cut by price **tercile**, an unrequested deviation from
  `config.cross_cuts` (which specifies the same decile T2 uses). Caught by re-reading
  the frozen config before building the Chart Contract; reverted.
- The Verification Block's no-pass-fail-language check initially flagged two real hits
  on its first run against actual chart text ("not a pass/fail line," "not to declare
  ... a winner") — an adjacency-anchored negation regex missed both. Widened and
  re-verified; this also caught two similar false-hits in `digest.json`'s own prose
  during drafting.

## 7. Verification Block

`research/phase_13/verify_partition_test.py`, 7 checks, all pass: P0 row count and
per-horizon coverage recomputed directly; every split's cross-cut cell counts conserve
against an independently-recomputed covered population; no spine numeric column reaches
any computation (D4); no fundamental column appears among P0's outcome columns
(D32/A1); no chart or artifact declares a pass/fail/kill-condition verdict; every
artifact's `config_hash` matches; `kill_condition.enabled` confirmed `false`.

## 8. Output files

| File | Status |
|---|---|
| `prompts/phase_13.md`, `config/phase_13.json` | committed |
| `research/phase_13/{common,t1_build_p0,t2_arm_zero,t3_partitions,verify_partition_test}.py` | committed |
| `research/phase_13/{chart_common,chart_01..chart_06}.py` | committed |
| `results/phase_13/artifacts/{p0_coverage_summary,t2_arm_zero_summary,t3_partition_summary}.json` | committed |
| `results/phase_13/artifacts/p0_outcome.parquet` | gitignored, regenerable |
| `results/phase_13/charts/01–06*.{html,png}` | committed |
| `results/phase_13/{digest.json, REPORT.md}` | committed |
| `results/reports/phase_13_report.md` | committed (copy) |
| `research/phase_13/{t4_tick_confirm,t4b_lookahead_diagnosis}.py` | committed (T4, §10) |
| `results/phase_13/artifacts/t4b_lookahead_diagnosis.json` | committed (T4, §10) |
| `results/phase_13/artifacts/t4_tick_confirmation.json` | not committed, test-scale byproduct only (§10) |

## 9. Approval Gate

**Gate Mode: sync-required.** Do not begin T4 (tick-level confirmation) or any
follow-on phase until Cooper has reviewed the charts and this report, and either names
a specific cross-cut worth confirming at tick level or closes the phase as read. Per
`prompts/phase_13.md`'s Approval Gate: this phase's own completion does not require T4.

## 10. T4 and closure (2026-09-14)

Cooper triggered T4a, targeting T3b (share turnover) for tick-level confirmation.
`research/phase_13/t4_tick_confirm.py` ran on the 50-event dev sample per two-tier
discipline (full-population T4a was never run — see below). It surfaced a defect, not
a confirmation: bar-derived and tick-derived MFE cost-multiple disagreed
one-directionally (bar-derived value never smaller than tick-derived) in 36% of events
at the 5-minute horizon, 14% at 15/30/60 minutes. Traced directly
(`research/phase_13/t4b_lookahead_diagnosis.py`) to `t1_build_p0.py`'s window
selection: `minute_index <= t0_minute_index + h` always includes the full final minute
bucket, whose clock-time end lands up to 60 seconds past the intended `t0 + h minutes`
mark. Population median excess is 59.14 seconds — essentially the full minute — because
73% of events (per D33's minute_a102 t0 tier) construct `t0_ns` as the start of a
minute bucket, so the offset into that final minute is under 1 second for most of the
population, not a random draw averaging ~30s. As a share of the labeled horizon, this
is a median 19.7% excess window at 5 min, 6.6% at 15 min, 3.3% at 30 min, 1.6% at 60
min.

**This is a HARD STOP per Escalation** (it is a look-ahead defect reaching a reported
outcome — the same class of thing rows 2/4/8 exist to catch, even though no single
numbered row in §5's table was written to name this specific mechanism). Per
`CLAUDE.md`'s Escalation rule, nothing already committed at T0–T5 was touched to fix
it: the diagnosis script and its output are committed; `t1_build_p0.py` was not
patched; T4a's own full-population run (the tick-vs-bar comparison and a corrected
re-run of T3b) was not executed, since running it against known-biased P0 data would
just produce a second set of numbers needing the same correction. The 50-event test
artifact (`t4_tick_confirmation.json`) is deliberately not committed — it is a
test-scale byproduct, not a deliverable.

**Cooper's decision, 2026-09-14: close as read, uncorrected.** No fix, no rebuild.
Every number in §§2–4 above is confirmed biased toward larger MFE/MAE than the true
tick-level value, worst at the shortest horizon (5 min) and smallest at the longest
(60 min) — see the closure banner at the top of this report for the full statement of
what that does and does not mean for reading this phase's distributions. Recorded as
`docs/Universe-Decisions.md` D37. This phase is now closed; no further task in
`prompts/phase_13.md` runs against it.
