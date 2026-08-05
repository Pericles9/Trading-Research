<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
tags:
  - type/research
  - domain/microstructure
  - status/awaiting-approval
created: 2026-08-04
phase: 10
config_hash: 6753cbe9
---

# Phase 10 — Burst Decomposition

**Branch:** `phase/10` · **Baseline:** `phase-9-approved` (`7909d66`) · **config_hash:** `6753cbe9`
**Status:** complete, awaiting Cooper review. No escalation fired. No pre-registered failure criterion fired.

This report is **description only**. It does not select an arm, propose a latency budget, or
characterise any result as good, weak, promising or disappointing. Chart 07 is the gate and the
arm selection is Cooper's; chart 06 is where the burst-relative budget is read, by Cooper.

---

## 1. Tick surface (T0d)

Every tick read in this phase is a targeted per-event parquet read of
`data/filtered/{TICKER}_{DATE}_{MOM}/trades.parquet` unioned with any `trades_repair_1c.parquet`
sibling. **Zero passes were made over `filtered_trades` or `filtered_quotes`.**

The substitution is licensed by proof, not assumption:

| Read-path equivalence check | Observed |
|---|---|
| Events checked (all dev v4) | 56 |
| Events where disk read == `filtered_trades_dev_v4` | **56 / 56** |
| Total rows, disk | **9,638,361** |
| Total rows, `filtered_trades_dev_v4` | **9,638,361** |
| Disagreements | 0 |

`filtered_trades_dev_v4` was itself materialized from `filtered_trades` by an inner join on the
3-part key (`research/phase_5a/t5_materialize_dev_v4.py`), so exact agreement means the folder read
*is* the `filtered_trades` content for that event.

A second check confirms this phase's D3 extended-day clock matches Phase 6b's: the folder read's
T=0 in-window print count equals `event_minute_bars_v2`'s on **114 / 114** cohort events, max
absolute difference **0**.

### Per-population tick surface, n = 114 events

| Population | n events | T=0 prints (min / q25 / median / q75 / max) | All 3 flanking sessions present | clean_window | repair sibling | row-cap flagged |
|---|---:|---|---:|---:|---:|---:|
| **pooled analysis cohort** | **100** | 296 / 3,410 / **25,204** / 78,241 / 831,614 | 100 | 100 | 11 | 0 |
| dev_v4_primary | 50 | 518 / 1,754 / 26,163 / 63,831 / 831,614 | 50 | 50 | — | 0 |
| activity_extension | 50 | 296 / 5,229 / 22,208 / 92,924 / 687,554 | 50 | 50 | — | 0 |
| row_cap_census (never pooled) | 8 | 50,000 / 87,500 / 100,000 / 100,000 / 200,000 | 8 | 8 | — | 8 |
| dev_v4_sidecar (never pooled) | 6 | 43 / 75 / 830 / 5,399 / 10,267 | 1 | 0 | — | 0 |

- Every analysis-cohort event has T=0 prints, all three flanking sessions, both feeds ingested, and
  `clean_window = TRUE`. The 6 not-clean-window events are exactly the dev v4 sidecar.
- 3 analysis-cohort events carry `flag_eth_dominant_t0`. Annotation only — no measurement excludes them.
- 0 analysis-cohort events carry `flag_has_dup_prints`.
- **8,197,948** cohort prints fall outside the extended-day `[04:00, 20:00)` window across the four
  sessions read and are excluded from segmentation by the D3 clock.
- Read runtime 12s total, max 1.0s/event against a 180s ceiling.

Source: `results/phase_10/artifacts/t0_tick_surface.json`.

> **Ordering note.** T0d depends on the T1 cohort and therefore ran after T1, not before it.

---

## 2. Cohort (T1)

| Group | n | Membership | Pooled? |
|---|---:|---|---|
| `dev_v4_primary` | 50 | Frozen from Phase 5a, seed 42, never redrawn | **yes** |
| `activity_extension` | 50 | 5 per T=0-print-count decile, seed 42 | **yes** |
| `row_cap_census` | 8 | Census of every D1 `flag_possible_row_cap` event | **never** |
| `dev_v4_sidecar` | 6 | Frozen from Phase 5a, deliberately degraded archive | **never** |
| **Total** | **114** | — | pooled analysis cohort = **100** |

**Escalation row 2 — canonical join.** Inner join to `momentum_events_canonical` with
`in_scope = TRUE`: **114 matched / 114 cohort, shortfall 0.**

**Stratification.** `t0_print_count` decile from `event_minute_bars_v2` (`session_offset = 0`),
not `momentum_pct`. `momentum_pct` is a completed-day *price*-move stratifier and is the axis dev v4
primary was already drawn on; reusing it would sample one axis twice and leave session activity
uncontrolled. T=0 print count is session activity, is tick-derived (D4-clean), and spans four orders
of magnitude across D1 (p01 135, median 21,585, p99 834,612, max 4,856,965). Eligible pool 15,299
events; all ten decile pools 1,411–1,553; exactly 5 drawn per decile.

**Reproducibility.** The draw is invariant to the row order its input arrives in — verified by
rebuilding the decile from a row-shuffled canonical and bars table and re-drawing: 0 differing rows.
This check replaced a weaker one; see §9.

**`row_cap_census`.** The seeded extension draw returned 0 of the 8 D1 row-cap events (8 / 15,763 —
a 100-event draw catches one about 5% of the time), so the prompt's requirement that flagged events
be "carried, labeled, and reported as their own row throughout" had nothing to report on. All 8 were
added at T1, **before any measurement ran**, as a never-pooled census — the same construction the dev
v4 sidecar already uses. It cannot move a headline number because it is never pooled, and the seeded
draw is unchanged. The 8: ANY 2021-09-02, AMIX 2024-07-19, APLD 2024-09-05, BBBY 2022-08-08,
ARBB 2023-12-26, ARBB 2024-02-13, BCAB 2022-08-10, APRE 2021-06-16.

Source: `results/phase_10/artifacts/t1_cohort_summary.json`, `t1_cohort_manifest.parquet`.

---

## 3. Burst count, duration, spacing (T4a)

Reported side by side, **never pooled across arms**. Chart 01, 02, 03.

### Burst count per event

| Arm | Population | n events | min | q25 | **median** | q75 | max | single-burst | zero-burst |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **A** | pooled analysis cohort | 100 | 1 | 15.0 | **98.5** | 264.5 | 1,912 | 1 | 0 |
| A | dev_v4_primary | 50 | 2 | 13.0 | 105.0 | 257.5 | 1,912 | 0 | 0 |
| A | activity_extension | 50 | 1 | 19.3 | 78.5 | 261.3 | 1,598 | 1 | 0 |
| A | row_cap_census | 8 | 123 | 163.3 | 395.0 | 464.3 | 527 | 0 | 0 |
| A | dev_v4_sidecar | 6 | 1 | 1.5 | 8.0 | 27.3 | 54 | 2 | 0 |
| **B** | pooled analysis cohort | 100 | 0 | 15.8 | **25.0** | 32.0 | 60 | 0 | 1 |
| B | dev_v4_primary | 50 | 4 | 16.0 | 26.0 | 31.8 | 60 | 0 | 0 |
| B | activity_extension | 50 | 0 | 13.0 | 25.0 | 31.8 | 52 | 0 | 1 |
| B | row_cap_census | 8 | 1 | 3.5 | 5.5 | 8.3 | 16 | 1 | 0 |
| B | dev_v4_sidecar | 6 | 1 | 5.3 | 12.5 | 17.5 | 37 | 1 | 0 |

The single zero-burst event under Arm B is AMTD 2022-08-05 (98,009 T=0 prints, `activity_extension`).
Arm A's single-burst events are INR 2020-01-07 (296 prints) plus two sidecar events.
Chart: [`01_burst_count.html`](charts/01_burst_count.html).

### Burst duration (seconds)

| Arm | Population | n bursts | min | q25 | **median** | q75 | max |
|---|---|---:|---:|---:|---:|---:|---:|
| **A** | pooled analysis cohort | 22,438 | 0.000 | 0.272 | **2.390** | 10.741 | 9,434.6 |
| A | row_cap_census | 2,688 | 0.000 | 0.448 | 2.532 | 7.964 | 1,403.2 |
| A | dev_v4_sidecar | 104 | 0.002 | 8.473 | 45.527 | 199.250 | 2,481.4 |
| **B** | pooled analysis cohort | 2,408 | 0.000 | 80.751 | **176.093** | 452.156 | 53,001 |
| B | row_cap_census | 51 | 35.019 | 108.695 | 388.169 | 3,131.010 | 27,139 |
| B | dev_v4_sidecar | 85 | 1.253 | 32.818 | 103.538 | 198.171 | 23,219 |

Arm B's minimum dwell floor is 60s, drawn as a vertical rule on chart 02. Arm A has no duration
floor by construction — `gamma·ln(n)` is the only thing preventing single-gap state flips.
Chart: [`02_burst_duration.html`](charts/02_burst_duration.html).

### Inter-burst spacing (seconds)

| Arm | Population | n gaps | min | q25 | **median** | q75 | max |
|---|---|---:|---:|---:|---:|---:|---:|
| **A** | pooled analysis cohort | 22,338 | 1.091 | 9.802 | **23.076** | 60.121 | 14,498 |
| A | row_cap_census | 2,680 | 1.488 | 7.608 | 14.575 | 30.059 | 12,783 |
| A | dev_v4_sidecar | 98 | 56.054 | 208.822 | 367.786 | 916.290 | 11,117 |
| **B** | pooled analysis cohort | 2,309 | 120.092 | 219.431 | **387.526** | 922.473 | 31,043 |
| B | row_cap_census | 43 | 124.213 | 195.598 | 360.557 | 778.593 | 7,162 |
| B | dev_v4_sidecar | 79 | 149.081 | 297.233 | 632.058 | 2,015.640 | 13,123 |

Arm B's merge-gap tolerance is 120s and is drawn on chart 03; the observed Arm B minimum spacing is
120.092s, i.e. the tolerance is binding at the left edge by construction and the distribution extends
more than two decades beyond it. Single-burst and zero-burst events contribute no spacing value and
are counted in the chart caption rather than dropped.
Chart: [`03_burst_spacing.html`](charts/03_burst_spacing.html).

---

## 4. Share of the session move carried per burst (T4b)

**Denominator definition:** session move = *last in-window T=0 print price − first in-window T=0
print price*, both tick-derived from `filtered/` prints. Undefined only where that difference is
exactly 0. Shares are **signed and unclipped** — a share above 1 or below 0 is a real feature of a
session that overshoots and retraces, not an error.

This is the one **session-scale anchor** used in the phase. D5 requires any session-relative anchor be
named and justified in the prompt before use; the prompt names it at T4b. It is used only as this
denominator and anchors no horizon measurement — T4c and T4d are both burst-relative.

**D4 Amendment A12 is not engaged.** Both numerator and denominator sit inside the single T=0
session, so no price basis crosses a session boundary. Arm B's baseline uses flanking-session
*counts* only, never flanking prices.

| Arm | Population | n bursts | undefined denominator | q25 | median | q75 | min | max |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | pooled analysis cohort | 22,438 | **0** | −0.014 | 0.000 | 0.015 | −18.882 | 32.364 |
| A | row_cap_census | 2,688 | 0 | −0.014 | −0.000 | 0.017 | −1.367 | 1.167 |
| A | dev_v4_sidecar | 104 | 0 | −0.116 | 0.016 | 0.281 | −1.677 | 2.204 |
| **B** | pooled analysis cohort | 2,408 | **0** | −0.038 | 0.000 | 0.068 | −34.941 | 63.194 |
| B | row_cap_census | 51 | 0 | −0.050 | 0.007 | 0.210 | −0.637 | 1.864 |
| B | dev_v4_sidecar | 85 | 0 | −0.011 | 0.015 | 0.094 | −0.952 | 1.066 |

No event in the cohort has an undefined session-move denominator, under either arm.

### Ordered by |move| within each event

| Arm | Rank | n events | q25 | **median** | q75 |
|---|---|---:|---:|---:|---:|
| **A** | 1st largest burst | 100 | 0.124 | **0.306** | 0.707 |
| A | 2nd | 99 | −0.276 | 0.163 | 0.383 |
| A | 3rd | 97 | −0.210 | 0.121 | 0.233 |
| **B** | 1st largest burst | 99 | 0.223 | **0.399** | 0.832 |
| B | 2nd | 99 | −0.280 | 0.133 | 0.333 |
| B | 3rd | 99 | −0.219 | 0.117 | 0.238 |

### Session coverage by bursts, pooled analysis cohort (median across events)

| Arm | share of session **seconds** in bursts | share of session **prints** | share of session **volume** |
|---|---:|---:|---:|
| A | 0.140 | 0.816 | 0.822 |
| B | 0.331 | 0.913 | 0.923 |

Chart: [`04_burst_move_share.html`](charts/04_burst_move_share.html).

---

## 5. Burst-relative concentration and time-to-extreme (T4c, T4d)

Anchored at **burst start**, which is also burst confirmation — the moment each rule first calls the
burst. No separate confirmation lag is modelled. A burst shorter than grid point *t* contributes its
terminal value at every later *t*; both n bursts and n still-open are reported per grid point.

### Median cumulative share of the burst's own move / volume, from burst start

| t since burst start | Arm A move (p25 / **p50** / p75) | Arm A volume p50 | Arm A n still open | Arm B move (p25 / **p50** / p75) | Arm B volume p50 | Arm B n still open |
|---|---|---:|---:|---|---:|---:|
| 0.1 s | 0.000 / **0.077** / 1.000 | 0.213 | 18,566 | 0.000 / **0.000** / −0.000 | 0.026 | 2,406 |
| 0.5 s | 0.000 / **0.390** / 1.000 | 0.386 | 15,800 | 0.000 / **0.000** / 0.000 | 0.028 | 2,406 |
| 1 s | 0.000 / **0.673** / 1.000 | 0.551 | 14,254 | 0.000 / **0.000** / 0.000 | 0.030 | 2,404 |
| 5 s | 0.665 / **1.000** / 1.000 | 1.000 | 8,312 | −0.000 / **0.000** / 0.035 | 0.048 | 2,394 |
| 30 s | 1.000 / **1.000** / 1.000 | 1.000 | 2,896 | −0.000 / **0.014** / 0.857 | 0.223 | 2,234 |
| 60 s | 1.000 / **1.000** / 1.000 | 1.000 | 1,707 | −0.000 / **0.323** / 1.000 | 0.362 | 2,004 |
| 300 s | 1.000 / **1.000** / 1.000 | 1.000 | 434 | 1.000 / **1.000** / 1.000 | 1.000 | 843 |
| 1800 s | 1.000 / **1.000** / 1.000 | 1.000 | 52 | 1.000 / **1.000** / 1.000 | 1.000 | 174 |

n bursts at every grid point: Arm A 22,438; Arm B 2,407.

### Time from burst start to that burst's own high (seconds)

Long-only per D5 — the high is the relevant extreme; the low is not measured and no fade quantity
is produced.

| Arm | Population | n bursts | min | q25 | **median** | q75 | max |
|---|---|---:|---:|---:|---:|---:|---:|
| **A** | pooled analysis cohort | 22,438 | 0.000 | 0.000 | **0.117** | 2.587 | 3,748.1 |
| A | row_cap_census | 2,688 | 0.000 | 0.000 | 0.157 | 2.111 | 889.0 |
| A | dev_v4_sidecar | 104 | 0.000 | 0.015 | 1.892 | 28.080 | 2,362.6 |
| **B** | pooled analysis cohort | 2,408 | 0.000 | 0.000 | **36.263** | 169.291 | 34,450 |
| B | row_cap_census | 51 | 0.000 | 23.999 | 81.271 | 490.657 | 14,466 |
| B | dev_v4_sidecar | 85 | 0.000 | 0.000 | 17.929 | 80.977 | 15,314 |

Under both arms the q25 is 0.000 s — at least a quarter of bursts take their high on the burst's
first print. Chart: [`06_burst_relative_concentration.html`](charts/06_burst_relative_concentration.html).

---

## 6. Cross-arm agreement (T5b)

Measure: **interval Jaccard** on the union of each arm's burst intervals — seconds in the
intersection over seconds in the union, per event. Same measure as the T5a perturbation test.
Chosen because the downstream use of this phase is burst-relative anchoring, so what matters is
whether the same *regions* of the session get labeled; burst-count agreement is reported alongside
but is not the failure-row-3 statistic.

| Quantity | Observed | n |
|---|---|---:|
| Interval Jaccard, Arm A vs Arm B | min 0.000 · q25 0.213 · **median 0.307** · q75 0.403 · max 0.764 · mean 0.320 | 100 events |
| Events with identical burst count | **0 / 100** | 100 |
| Spearman correlation, Arm A count vs Arm B count | **−0.216** | 100 |
| Events where Arm A returns more bursts | 67 | 100 |
| Events where Arm B returns more bursts | 33 | 100 |
| Events where exactly one arm returned no bursts | 1 | 100 |

Chart: [`05_arm_agreement.html`](charts/05_arm_agreement.html).

---

## 7. Pre-registered failure criteria (T5c)

Evaluated on the pooled analysis cohort (n = 100). Thresholds fixed in `config/phase_10.json`
before the run. **Pass/fail only; nothing further is stated about these results.**

| # | Failure mode | Arm | Observed | Threshold | Result |
|---|---|---|---|---|---|
| **0** | Cooper rejects the segmentation on visual review of chart 07 against the tape | both | — | Cooper's judgment | **not evaluated by the agent** |
| 1 | Degenerate to session flag | A | 0.000 | ≤ 0.20 | **PASS** |
| 1 | Degenerate to session flag | B | 0.000 | ≤ 0.20 | **PASS** |
| 2 | Fragmentation at the floor (median duration) | A | 2.390 s | > 75.0 s | **n/a** |
| 2 | Fragmentation at the floor (median duration) | B | 176.093 s | > 75.0 s | **PASS** |
| 3 | Parameter instability (median Jaccard vs reference) | A | 0.774 | ≥ 0.50 | **PASS** |
| 3 | Parameter instability (median Jaccard vs reference) | B | 0.931 | ≥ 0.50 | **PASS** |
| 4 | No structure (modal share / IQR) | A | modal share 0.04, IQR 249.5 | ≤ 0.60 / ≥ 1.0 | **PASS** |
| 4 | No structure (modal share / IQR) | B | modal share 0.05, IQR 16.25 | ≤ 0.60 / ≥ 1.0 | **PASS** |

**Row 2 is `n/a` for Arm A by pre-registration, not by exception.** The criterion is "the rule
re-emitting its own parameter"; Arm A has no minimum-dwell parameter to re-emit. `config.failure_criteria.row_2`
was written with `applies_to = ["arm_b"]`, `reported_for = ["arm_a", "arm_b"]` before the run, so
Arm A's value is reported but not evaluated.

**No criterion fired.** Per the prompt: *a pass on rows 1–4 does not constitute acceptance.* Row 0
is the operative criterion and it is Cooper's.

### T5a — parameter sensitivity detail

| Arm | Non-reference cells | Comparisons | Jaccard min | q25 | **median** | q75 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 8 (s × gamma) | 800 | 0.213 | 0.676 | **0.774** | 0.846 | 1.000 |
| B | 23 (on × off × dwell) | 2,300 | 0.000 | 0.838 | **0.931** | 0.986 | 1.000 |

3 Arm B parameter combinations were skipped for violating the `off < on` constraint.

---

## 8. Escalation check — all 11 rows

| # | Condition | Observed | Result |
|---|---|---|---|
| 1 | Tag `phase-9-approved` absent | Present, `7909d66`; `master` at exactly that commit | **PASS** |
| 2 | Cohort join to canonical `in_scope = TRUE` shortfall | 114 matched / 114, shortfall **0** | **PASS** |
| 3 | Read of a D4-quarantined spine numeric on a computation path | **0**. Every computed quantity is tick-derived from `filtered/` prints. `momentum_pct` appears only as a folder-name component and manifest carry-through; it enters no computation and is not a stratification variable | **PASS** |
| 4 | Full-table pass over `filtered_trades` / `filtered_quotes` | **0 scans.** All tick reads are per-event parquet; equivalence proved on 56/56 dev v4 events, 9,638,361 rows | **PASS** |
| 5 | Runtime ceiling breached | Arm A 82s total / 7.58s max per event (ceilings 3,600s / 120s); Arm B 14s / 0.08s; tick read 1.0s max (ceiling 180s) | **PASS** |
| 6 | Per-event chart set exceeds config cap | 80 selected, cap 80 | **PASS** |
| 7 | Write outside `prompts/`, `config/`, `research/phase_10/`, `results/phase_10/` | **0.** The chart-07 gitignore is a nested file inside `results/phase_10/charts/07_tape_review/`, specifically so the repo-root `.gitignore` is not touched | **PASS** |
| 8 | Inter-trade interval distribution produced as a reported finding | **0.** Inter-trade time appears only as chart 07's diagnostic display axis and as Arm A's likelihood input. No interval distribution, noise floor, or burst-vs-quiet regime is defined — Phase 13's deliverable | **PASS** |
| 9 | Output described as detector / entry signal / operating point / latency budget | **0** | **PASS** |
| 10 | Arm, parameter set or burst definition selected or described as preferable | **0** | **PASS** |
| 11 | Offline changepoint detection or Hawkes-intensity methods run | **0** | **PASS** |

---

## 9. Two defects found and fixed mid-phase

Both were silent, and both are recorded here because they generalise beyond this phase.

**(a) The cohort draw was not reproducible as first written.** The stratification decile came from
`rank(method="first")` over a DataFrame whose row order was the row order of a `SELECT` with no
`ORDER BY`. Tied `t0_print_count` values therefore landed in different deciles on different runs, the
per-decile eligible pools differed, and the "seeded" draw returned different events — an earlier run
drew DPRO 2024-04-01 and IMTE 2023-10-27, a later one did not. The in-run reproducibility check did
not catch it because it compared two draws off the *same* in-memory pool object. Fixed by sorting the
pool before ranking; the check now rebuilds the decile from row-shuffled inputs, so it tests
order-independence rather than repeatability. All downstream tasks were re-run against the corrected
cohort — which then reproduced the original figures exactly. **Any phase drawing a stratified sample
in pandas off an unordered SQL read has this exposure.**

**(b) A defaulted `getattr` turned a schema gap into a quiet method downgrade.** Arm B read
`trades_bitmap` via `getattr(row, "trades_bitmap", None)`, and the column had never been selected into
the cohort manifest — so all 114 events silently used the print-presence fallback while the config
documented the bitmap rule. The column is now selected, and a missing *column* raises rather than
falling back (a per-event NULL still legitimately falls back). Arm B was re-run; the bitmap rule is
now in force on 114/114 events.

One display defect was also corrected: chart 07's panel 2 drew Arm B's rate measure as `60/rate`,
which is undefined where the rate is exactly zero and was being plotted as `60/1e-9`, putting
~10¹⁰-second spikes on a log axis and destroying the panel's y-range. Zero rate now breaks the line.

---

## 10. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---:|---|---|
| Read-path equivalence rows | 9,638,361 (56/56 agree) | 56 events | `research/phase_10/t0d_tick_surface.py:read_path_equivalence` | `.venv/Scripts/python.exe research/phase_10/t0d_tick_surface.py` |
| Clock cross-check mismatches vs `event_minute_bars_v2` | 0 (max abs diff 0) | 114 events | `research/phase_10/t0d_tick_surface.py:main` | same as above |
| Cohort canonical join matched | 114 / 114, shortfall 0 | 114 events | `research/phase_10/t1_cohort.py:main` | `.venv/Scripts/python.exe research/phase_10/t1_cohort.py` |
| Arm A burst count, median | 98.5 (IQR 15.0–264.5) | 100 events | `research/phase_10/t4_measure.py:main` | `.venv/Scripts/python.exe research/phase_10/t4_measure.py` |
| Arm B burst count, median | 25.0 (IQR 15.75–32.0) | 100 events | `research/phase_10/t4_measure.py:main` | same as above |
| Arm A burst duration, median | 2.390 s | 22,438 bursts | `research/phase_10/t4_measure.py:main` | same as above |
| Arm B burst duration, median | 176.093 s | 2,408 bursts | `research/phase_10/t4_measure.py:main` | same as above |
| Arm A spacing, median | 23.076 s | 22,338 gaps | `research/phase_10/t4_measure.py:main` | same as above |
| Arm B spacing, median | 387.526 s | 2,309 gaps | `research/phase_10/t4_measure.py:main` | same as above |
| Arm A largest-burst move share, median | 0.306 | 100 events | `research/phase_10/t4_measure.py:main` | same as above |
| Arm B largest-burst move share, median | 0.399 | 99 events | `research/phase_10/t4_measure.py:main` | same as above |
| Arm A move share at t = 1 s | 0.673 | 22,438 bursts | `research/phase_10/t4_measure.py:main` | same as above |
| Arm B move share at t = 60 s | 0.323 | 2,407 bursts | `research/phase_10/t4_measure.py:main` | same as above |
| Arm A time-to-burst-high, median | 0.117 s | 22,438 bursts | `research/phase_10/t4_measure.py:main` | same as above |
| Arm B time-to-burst-high, median | 36.263 s | 2,408 bursts | `research/phase_10/t4_measure.py:main` | same as above |
| Cross-arm interval Jaccard, median | 0.307 | 100 events | `research/phase_10/t5_sensitivity.py:main` | `.venv/Scripts/python.exe research/phase_10/t5_sensitivity.py` |
| Arm A sensitivity Jaccard, median | 0.774 | 800 comparisons | `research/phase_10/t5_sensitivity.py:main` | same as above |
| Arm B sensitivity Jaccard, median | 0.931 | 2,300 comparisons | `research/phase_10/t5_sensitivity.py:main` | same as above |
| Arm A implementation correctness | Viterbi == brute force over all 2⁵ paths, 200 trials | 200 trials | `research/phase_10/kleinberg.py:_selftest` | `.venv/Scripts/python.exe research/phase_10/kleinberg.py` |
| Arm B implementation correctness | dense region recovered as one burst, bounds within ±2 min, >90% of its prints | synthetic | `research/phase_10/arm_b.py:_selftest` | `.venv/Scripts/python.exe research/phase_10/arm_b.py` |

### Filter waterfall — Arm B candidate funnel, reference point, all 114 events

| Step | Bursts in | Bursts out | Dropped | Why |
|---|---:|---:|---:|---|
| Hysteresis threshold | — | 8,085 | — | z ≥ ln(4) on, z < ln(2) off |
| Merge gaps < 120 s | 8,085 | 4,146 | 3,939 merged | a real burst split by one sub-threshold grid point is not destroyed by the floor |
| Drop duration < 60 s | 4,146 | 2,544 | 1,602 | minimum dwell |
| Drop bursts containing no print | 2,544 | 2,544 | 0 | — |

### Cohort waterfall

| Step | Rows in | Rows out | Why |
|---|---:|---:|---|
| `momentum_events_canonical` | 20,951 | 20,951 | all rows |
| `in_scope = TRUE AND source_file = 'file1'` (D1) | 20,951 | 15,763 | D1 analysis universe |
| `clean_window AND trades_ingested`, minus dev v4 | 15,763 | 15,299 | extension eligibility (Arm B needs T-3..T-1 coverage) |
| 5 per T=0-print-count decile, seed 42 | 15,299 | 50 | `activity_extension` |
| + dev v4 primary / sidecar / row-cap census | 50 | 114 | full cohort |
| − never-pooled groups | 114 | **100** | pooled analysis cohort |

---

## 11. Output files

| File | Status |
|---|---|
| `prompts/phase_10.md` | committed, first commit on the branch |
| `config/phase_10.json` | committed before any run; two documented in-phase amendments (§2 row-cap census, §9 grid resolution) |
| `results/phase_10/artifacts/t0_tick_surface.json` | written, committed |
| `results/phase_10/artifacts/t0_tick_surface.parquet` | written (gitignored, regenerable) |
| `results/phase_10/artifacts/t1_cohort_manifest.parquet` | written (gitignored, regenerable) |
| `results/phase_10/artifacts/t1_cohort_summary.json` | written, committed |
| `results/phase_10/artifacts/t1_stratification_pool.parquet` | written (gitignored, regenerable) |
| `results/phase_10/artifacts/t2_bursts_arm_a.parquet` | written (gitignored, regenerable) — 311,590 rows across 9 param sets |
| `results/phase_10/artifacts/t2_arm_a_events.parquet`, `t2_arm_a_summary.json` | written; summary committed |
| `results/phase_10/artifacts/t3_bursts_arm_b.parquet` | written (gitignored, regenerable) — 66,833 rows across 24 param sets |
| `results/phase_10/artifacts/t3_arm_b_events.parquet`, `t3_arm_b_summary.json` | written; summary committed |
| `results/phase_10/artifacts/t4_burst_measurements.parquet`, `t4_event_measurements.parquet`, `t4_concentration_curves.parquet` | written (gitignored, regenerable) |
| `results/phase_10/artifacts/t4_burst_measurements.json` | written, committed |
| `results/phase_10/artifacts/t5_overlap_pairs.parquet` | written (gitignored, regenerable) |
| `results/phase_10/artifacts/t5_sensitivity.json` | written, committed |
| `results/phase_10/charts/01–06*.html` + `.png` | written, committed, **kaleido-verified 6/6** |
| `results/phase_10/charts/07_tape_review/` | 80 charts + full-cohort index, 446 MB, untracked via nested `.gitignore` |
| `results/phase_10/digest.json`, `REPORT.md` | written, committed |

Chart 07 selection: all 50 `dev_v4_primary`, all 6 `dev_v4_sidecar`, all 8 `row_cap_census`, plus 16
`activity_extension` (5 lowest / 5 highest Arm A burst count, 6 seeded random middle) = 80, exactly
the config cap. 13 events are subsampled in the **top panel only**; both arms' intervals are always
drawn from the full-resolution segmentation and the bottom panel's envelope is computed from every
print. The sortable index at `charts/07_tape_review/index.html` covers **all 114** cohort events,
charted or not, per Agent_Prompt_Standard §7.

---

## 12. Commits

| SHA | Task |
|---|---|
| `1ab1218` | T0b — commit the phase prompt before any other work |
| `2b2900f` | T0c — config committed before any run |
| `0ceadb2` | T1 — cohort construction, Arm A implementation, shared plumbing |
| `6d16a81` | T0d — tick surface + read-path equivalence proof |
| `1e2b887` | T2 — Arm A run |
| `871fbd6` | T3 — Arm B run |
| `769e12d` | T4 — burst-level measurements |
| `0a1f1d1` | T5 — sensitivity, cross-arm agreement, failure criteria |
| `845459f` | T6a — charts 01–06 |
| `24d80c9` | T1/T3 fix — order-independent draw; stop masking a missing bitmap column |
| `c9f23a4` | T6b — chart 07 tape review set + full-cohort index |
| _(this commit)_ | T7 — digest and report |

---

## 13. Held for Cooper — one standing rule this phase's allowlist blocks

`CLAUDE.md` requires: *"Any phase that adds, moves, or removes repo files updates
`docs/Research-Library-Map.md` in the same phase."* Phase 10 adds 11 files under `research/phase_10/`,
`config/phase_10.json`, `prompts/phase_10.md`, and the `results/phase_10/` tree, so the rule applies.

**It was not done, deliberately.** `docs/` is outside this prompt's write allowlist, and escalation
row 7 makes any write outside `prompts/`, `config/`, `research/phase_10/`, `results/phase_10/` a hard
stop. The standing rule and the phase prompt's allowlist are in direct conflict here. Rather than
pick one silently, the write is held: the library-map entry for Phase 10 is **outstanding** and needs
either a one-line authorization to write `docs/Research-Library-Map.md`, or folding into the merge
commit at the approval gate. The same tension will recur in every future phase whose prompt carries a
`results/`-scoped allowlist.

### Working-tree items not authored by this phase

`git status` is not empty at phase end. Three items, none written by Phase 10, all left untouched
because they sit outside the allowlist:

| Item | State | Note |
|---|---|---|
| `.gitignore` | modified | Trailing-newline removal only; present in the working tree before `phase/10` was cut |
| `prompts/phase_9` | untracked | Stray extensionless duplicate of `prompts/phase_9.md`, missing that file's T0 escalation appendix. Present before this phase |
| `.claude/skills/reuse-before-build/` | untracked | Not authored by this phase |

All Phase 10 commits used explicit-path `git add`, so none of these were swept into the branch.

---

## Approval gate

Not tagged, not merged. Phase 11 scoping not begun.

**Chart 07 is the gate** — [`charts/07_tape_review/index.html`](charts/07_tape_review/index.html).
**Chart 06** is where the burst-relative budget is read. Both reads are Cooper's.

On approval: tag `phase-10-approved`.
