# Fundamental exploration E1 — descriptive baseline — REPORT

**Branch:** `explore/fundamental-e1` · **Config hash:** `042eac1aebb5`
**Status:** complete (T0–T7 run, this is T8). **Not a phase, not a finding.** No decision, no
hypothesis test, no pass/fail. Descriptive only — no fundamental column touches an outcome variable
anywhere in this document. Per the brief's own §6, this report is documentation: any partition tested
later against an outcome is either declared in writing before this report is read, or labelled
exploratory when it is tested.

Full task list, scope line, and variable definitions: `prompts/fundamental_exploration_e1.md`.

---

## T0 — Join and assert membership

`research/fundamental_exploration/t0_join_and_assert.py`. `event_fundamentals` (20,951 rows) joined
to the canonical spine. All three checks pass: row count exactly 20,951, `event_id` unique, and set
equality against `momentum_events_canonical WHERE in_scope = TRUE` in both directions — checked
against `results/phase_5/artifacts/quotes_bitmaps_all.parquet` (D15's materialization of that exact
population, not a live view scan, per `fundamentals_f1`'s own precedent for why). 0 events on either
side of the set difference. Detection price (`research/fundamental_exploration/t0b_detection_price.py`,
reconstructing F1-T6's `t6_context.parquet` locally since that gitignored intermediate isn't present
on this checkout — reuses `t6_prep_context.py`'s own tiering logic and `first_trade_price()` function)
joins cleanly to all 20,951 events, 0 missing, 0 null.

---

## T1 — Univariate distributions

`research/fundamental_exploration/t1_univariate_fundamentals.py` and `t1_univariate_tape.py`. Eight
charts, `results/fundamental_exploration/charts/t1_univariate/`.

- **`01_shares_outstanding.html`.** Raw and split-corrected `shs_shares_outstanding`, log-x
  histograms; `shs_lag_ns` (staleness, days, log-x); `shs_quality` category counts. 16,099/20,951
  (76.9%) events carry a share count. 54 events carry `shs_shares_outstanding == 0.0` exactly —
  disclosed in-panel as "not applicable" on the raw histogram (can't log-transform 0) and folded into
  "unavailable" on the corrected histogram (a corrected value can't be derived from a zero input).
- **`02_split_history.html`.** `spl_n_splits_365d` (count histogram), `spl_reverse_split_365d` (bar),
  `spl_last_split_ratio` (log-x histogram, nearest split before t0, unbounded lookback — a wider
  population than the 365-day window at left), `spl_quality` (bar). 12,178 events (58.1%) show
  `spl_n_splits_365d == 0` — a confirmed zero, not the same as `spl_quality == 'unavailable'` (see T2).
- **`03_short_interest.html`.** `si_shares_short`, `si_lag_ns` (log-x), `si_quality` (bar).
- **`04_filing_counts_and_quality.html`.** `flg_n_filings_24h`, `flg_n_filings_72h`, `flg_quality`
  (bar). `flg_last_form` and `flg_lag_ns` are charted in `t5_filing_landscape/` instead of here — not
  duplicated.
- **`05_detection_price_and_year.html`.** `detection_price` (log-x histogram), event counts by year
  (2020: 3,439 · 2021: 1,932 · 2022: 2,279 · 2023: 3,021 · 2024: 5,092 · 2025: 5,188).
- **`06_event_volume.html`.** Event volume in shares and in notional USD, regular session, log-x.
- **`07_prints_and_intertrade.html`.** `print_count_at_t0` (same 60-second bucket as t0, any
  session), `print_count_session` (regular session), median inter-trade interval within the regular
  session (seconds, log-x). All three defined for all 20,951 events — zero nulls.
- **`08_session_and_ticker.html`.** `t0_session` counts (regular 16,242 / 77.5% · pre-market 4,630 /
  22.1% · after-hours 79 / 0.4%) and a histogram of events-per-ticker (5,188 distinct tickers).

---

## T2 — Coverage as a variable, not a filter

`research/fundamental_exploration/t2_coverage.py`, chart `t2_coverage/01_coverage_by_year.html`.
Coverage share (`{group}_quality != 'unavailable'`) per group (`flg`, `shs`, `si`, `spl`; `fin_`
excluded per §1) by year.

The brief's own mandated check: SEC-sourced groups (`flg`, `shs`) must not show the 2022–23 vendor
coverage cliff. They don't — `flg` drops 1.7 points and `shs` 1.4 points in 2022–23 versus the other
years' mean, both well under the vendor-sourced groups' own drops (`si` 2.1 points, `spl` 6.6 points).
`sec_shows_cliff_defect` is `false`.

**Found in the process:** `spl_quality` (`research/fundamentals_f1/t5_assemble.py:180-181`) defaults
to `"unavailable"` and only flips to `"observed"` when a split is actually found in the 365-day
window — so a confirmed zero-splits event and a genuinely unresolved one are both labelled
`"unavailable"`. Cross-tabbed against `identity_quality`: 11,971 of the 12,219 `spl_quality ==
'unavailable'` rows (98.0%) carry a resolved CIK, meaning most of that 58.3% "unavailable" share is
very likely a real, observed zero rather than a true data gap. Not corrected in `event_fundamentals`
itself — Build F1 is a closed, separately-verified build; this exploration reads it, it doesn't edit
it.

---

## T3 — Shares outstanding × detection price, two-way

`research/fundamental_exploration/t3_shares_x_price.py`, chart
`t3_shares_x_price/01_two_way_counts.html`. Event counts by shares-outstanding decile × detection-price
decile, raw and split-corrected side by side (no market cap constructed — this is a count table, not a
product). 4,852 events with no shares-outstanding data sit in their own `no_shs_data` row, never
dropped. 1,734 events had their own raw value rescaled by `spl_last_split_ratio` (their filing predated
the nearest pre-t0 split); 12,085 events show a *different decile label* between the two tables — the
chart caption spells out why that number is much larger than 1,734: independently-recomputed decile
edges move when even a minority of values are rescaled, relabelling events that did not themselves
change. The 54 zero-share-count events land in the raw table's `S0` (as filed) and in the corrected
table's `no_shs_data` (a corrected value can't be derived from a zero).

---

## T4 — Fundamentals against volume

`research/fundamental_exploration/t4_fundamentals_vs_volume.py`, charts
`t4_fundamentals_vs_volume/01_volume_by_shs_decile.html` and `02_turnover_lower_bound_by_shs_decile.html`.
Small multiples — rows = event year, columns = detection-price decile, x-axis within each panel =
shares-outstanding decile — matching `research/phase_13/chart_common.py`'s established layout for this
exact cross-cut shape. 585 (year, price-decile, shs-decile) cells; 200 fall below the
`min_cell_n_display_floor` (20) and render as thin/empty boxes, not hidden ones.

Turnover (`volume_shares / shs_shares_outstanding_corrected`) is labelled on the y-axis itself as a
lower bound, ordinal ranking only, never a level. **A second share-count problem, found here:**
beyond the exact-zero case (T1/T3), sorting the corrected column's smallest nonzero values turns up 1,
1, 1, 12, 12, 17, 100 (×9), 1000 (×6), 1440 (×9) — implausible totals for real, actively-traded
companies (one event, `LAES_2024-01-11_79.99`, trades ~79.0M shares against a filed count of 100).
Unlike the exact-zero case there is no clean gap in the distribution separating these from legitimate
small microcap counts, so this is carried as a diagnostic only (`shs_share_count_suspect`,
`< 100,000` shares, a stated round threshold, never a filter or an exclusion) — 146 events across the
population, reported per cell. It is what pulls a cell's *mean* turnover far above its *median*; the
box plot's median/IQR are far less affected and are the more reliable read.

---

## T5 — Filing proximity landscape

`research/fundamental_exploration/t5_filing_landscape.py`, three charts in
`t5_filing_landscape/`. `flg_quality` splits cleanly three ways here (`t3_filing_index.py:237-239`,
no zero/unavailable conflation of the kind T2 found in `spl_quality`): 20,683 observed (98.7%), 20
`no_filings_in_window`, 248 unavailable (identity-unresolved — the same 248 as T2's crosstab).

- **`01_form_mix.html`.** Nearest prior filing's form type, `flg_quality == 'observed'` only. Top
  five: 8-K (5,389), 6-K (4,357, foreign private issuers), Form 4 (2,414, insider transactions), 10-Q
  (1,319), SC 13G/A (503).
- **`02_lag_distribution.html`.** Days from the nearest prior filing to t0, log10 x-axis. p10 = 0.32
  days, median = 5.64 days, p90 = 32.73 days, max = 393.0 days.
- **`03_dilution_rate_heatmap.html`.** `flg_dilution_form_before_t0` rate by year × detection-price
  decile, computed over `flg_quality != 'unavailable'`, each cell reporting its own n and excluded
  `'unavailable'` count. 1 of 60 cells falls below the display floor.

---

## T6 — Reverse-split cohort

`research/fundamental_exploration/t6_reverse_split_cohort.py`, two charts in
`t6_reverse_split_cohort/`. `spl_reverse_split_365d` (`bool_or(ratio<1)` in the 365 days before t0,
filled `False` when no split matches) is always defined — no zero/unavailable conflation to work
around, unlike `spl_quality`. True cohort n = 4,122; False cohort n = 16,829.

Rather than re-rendering every T1–T5/T7 chart twice, this produces the comparison itself across the
variables already established as informative:

- **`01_key_distributions.html`.** Detection price, shares outstanding (corrected), event volume,
  turnover (lower bound), and days-since-filing — box-from-summary-stats per cohort, with a jittered,
  subsampled (n ≤ 5,000 per cohort per metric, seed 42, exact counts in the artifact JSON) raw-point
  strip behind each box so the extreme tail from the share-count-suspect events (101 in the True
  cohort, 45 in the False cohort) is visible rather than only implied by a mean.
- **`02_coverage_and_dilution_rate.html`.** Per-group coverage and dilution-flag rate, both cohorts
  side by side.

---

## T7 — Collinearity map

`research/fundamental_exploration/t7_collinearity.py`, chart
`t7_collinearity/01_spearman_heatmap.html`. Spearman rank correlation across 11 numeric/boolean
fundamental variables (booleans coerced 0/1, shares outstanding split-corrected) plus
`detection_price`, pairwise-n shown in every cell's hover (coverage ranges from 8,732 for
`spl_last_split_ratio` to 20,951 for the always-populated columns). All 66 pairs clear the display
floor.

Every `|ρ|` against `detection_price` is ≤ 0.155: `flg_n_filings_24h` (0.154) and `flg_n_filings_72h`
(0.147) are the largest in magnitude, followed by `flg_lag_ns` (−0.144), `si_shares_short` (0.110),
`shs_lag_ns` (−0.097), `spl_last_split_ratio` (0.076); `shs_shares_outstanding_corrected` (0.007) and
`flg_dilution_form_before_t0` (0.005) are the smallest. Categorical quality enums are not in this
numeric matrix — `config.collinearity.categorical_association` (Cramér's V) was not run.

---

## Scope boundary, restated from the brief

This report does not construct market cap, float, or any derived ratio beyond T4's ordinal turnover;
does not touch `fin_`; does not use the vendor float endpoint; does not put any fundamental column
against any outcome; does not filter the population on coverage; and produces no finding. The
crossings that would need DF-6's sentence first — shares-outstanding decile against net expectancy,
dilution flag against continuation, reverse-split cohort against excursion, short interest against the
bear leg — are listed in the brief's §5 and are not run here.
