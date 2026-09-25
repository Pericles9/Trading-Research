> **Filing note (Claude Code, 2026-09-25).** Filed verbatim as pasted, on branch
> `explore/attention-excursion-b2` (cut from `explore/attention-excursion-b1` at `99431b8`). Config:
> `config/attention_excursion_b2.json`; code: `research/attention_excursion_b2/`; outputs:
> `results/attention_excursion/b2/`.

# Attention and the excursion — Brief 2: full-D1 build, competition check, step zero

**Date:** 2026-09-25 · **Type:** build plus one **unconditional** read. **Not a phase.** Puts no attention
measure against any excursion component anywhere.
**Design of record:** `prompts/attention_excursion.md` (Part I) and Brief 1 with Amendments 1–3, all in
the repo. Everything load-bearing is restated here.
**Branch:** `explore/attention-excursion-b2`, cut from `explore/attention-excursion-b1` at `99431b8`.
**Outputs:** `results/attention_excursion/b2/` (artifacts, charts in per-task subfolders, REPORT.md plus
its copy in `results/reports/`). **Config** `config/attention_excursion_b2.json`, committed before any
run. It carries Brief 1's frozen config (hash `658071fbe27f`) unchanged except for the items in §1, each
listed as a diff.
**Ends at a HARD STOP (T6)** after the step-zero report.

---

## 0. Brief 1 closes

Brief 1 is **accepted at its T7 stop** (Cooper, 2026-09-25). The instruments pass all seven controls
against simulated references. The anchoring change moved 53 previously valid rungs off the open.
Its three open items are ruled in §1 and carried here, not back into Brief 1. They matter only at full
scale, and re-running Brief 1 on 49 dev dates would add nothing.

## 1. Rulings on Brief 1's open items, and the only config changes

**R1 — `from_nothing` (my explanation in Amendment 3 A3.0 was wrong for most of them).** 220 of the 227
are sub-second windows where the tape simply runs out of trades, not an empty premarket half. They were
invalid under the counting-noise stop anyway. Two changes:

- **Rung generation stops where no rung can be valid.** Rungs are generated down to the first k where
  the event's own segment-average trade rate predicts fewer than 17 collapsed trades in the half-window.
  Below that, the ≥ 17 stop cannot pass, so nothing is computed. Derived from the stop itself.
- **`from_nothing` at the coarse end is a real state and gets a label.** Carry `a2_ignition = TRUE` when
  rung 0 or rung 1 is `from_nothing`: silence in the older half of the segment, trading in the recent
  half. It is a **label only**, with no prediction attached. Report its count.

**R2 — the competition control, re-matched on the population, not the same name.** Matching a live name
to itself cannot work at short ages: τ_j sits inside its own time bin, so whenever the bin is no wider
than W, every candidate moment is within ±W of τ_j. The matched set then leans toward names that
crossed long ago. Revised:

> **Baseline cell** = (year, session segment, liveness L, window W, age octave), where age is the live
> name's time since its own τ, binned on the same base-2 octaves used elsewhere. **Baseline moments**
> = every live name, at moments on the 1-minute grid with no D1 crossing within ±W, pooled across names
> and dates in that year. For each (crossing j, live name i) pair: **excess = observed log-ratio − the
> baseline cell's median.** Cells with fewer than 20 baseline moments are shown, labelled, and not read.

Report the excess distribution per (L, W), with n, plus the baseline cell counts. Same-name matching
from Amendment 3 is retired.

**R3 — the segment rule applies to the competition windows too.** A pair, crossing or baseline, is
valid only if **[τ − W, τ + W] lies inside one session segment and contains no auction minute**
(09:30:00–09:31:00, 16:00:00–16:01:00). That is the same rule as Amendment 3 A3.1, and it was missing
here: 8,191 of 15,623 crossing pairs at L = rest, W = 60 spanned a boundary on the dev dates. Invalid
pairs are labelled `window_crosses_segment` and excluded on both sides. Report the share lost per cell.

**R4 — facet bins in absolute units** (Cooper, 2026-09-24: no percentile sets any bin edge). Price tier
= detection price in **< $1 · $1–3 · $3–10 · ≥ $10**. The $1 edge is structural: below it the minimum
tick is $0.0001, above it $0.01 (Rule 612). Every other continuous facet uses log-spaced absolute bins,
declared in config. The detection-price **decile** facet used in earlier work is retired here.

**R5 — the retired column.** Drop `open_adjacent_0930` from every b2 artifact. Brief 1's T4 file keeps
it as the as-run record.

## 2. Standing constraints

D4 tick-derived only, `momentum_pct` resolves folder paths only · D5 long-only · D14 offline, Plotly
inlined · D19 bp and cents · A12 flag carried, flagged events their own row · D38 slices, dev sample (50)
and sidecar (6) quarantined from every slice but **built** like any other event · flag and carry, never
drop · `unavailable` / zero / censored kept distinct · every membership and coverage claim asserted in
code · every REPORT.md number read from an artifact by code · named paths staged · dark theme.

## 3. Tasks

### T0 — Freeze and population

Assert: D1 = 15,763; τ available = 15,519 (from Brief 1 T2, not recomputed); slices as committed in
`results/attention_excursion/b1/slices.parquet`. The config diff against Brief 1's frozen config
contains exactly the items in §1 and nothing else, asserted by a script comparing the two files.

### T1 — Excursion vector, all of D1

Brief 1's T4 code, unchanged: equal-volume buckets at N ∈ {50, 100, 200}, bucket VWAP, `σ_path` =
realised variance of bucket log returns, earliest-peak tie rule, edge classes (`rise_censored`,
`no_rise`, `peak_tied`, `halt_in_path` by the regular-hours ≥ 300 s rule plus labels, `thin_path` < 250
prints), `jump_share`, bp and cents twins. Session end = event-day 20:00 ET.

### T2 — Attention axes, all of D1

**Everything at or before τ, with the causality assertion in every function.**

- **A1 turnover:** shares 04:00 → τ ÷ `shs_shares_outstanding_corrected`. `shs_asof_ns < τ` asserted per
  event. Carry `shs_lag_ns`, `shs_quality`, suspect flag, dilution flag.
- **A2 acceleration:** segment-anchored (04:00 / 09:31 / 16:01), each rung judged on its own, rung
  generation per R1, `a2_ignition` per R1, the auction-minute class, count and kernel versions.
- **A3 catalyst:** filing accepted within 24 h before τ; hours since the last filing; last form.
- **Absolute level measures — new, needed by the threshold suite.** Per valid rung window: collapsed
  trade rate (trades per minute), dollar flow ($ per minute), share volume rate. Also the pre-τ collapsed
  print count since the segment start. These are plain counts and sums divided by time. No baseline, no
  ratio to the stock's own history.
- **Cross-sectional:** live sets across all D1 at L ∈ {15 min, 60 min, rest of session}; `live_n`;
  `flow_share_k` and `accel_rank_k` over the new crosser's rung windows; each live name's `move_at` and
  age.

### T3 — Competition check, all of D1 (R2, R3)

Mechanism only, reads no excursion. Output: per (L, W) cell, the excess distribution with n; the
baseline cell counts; the share of pairs lost to R3. Defined cells as in Amendment 2 A2.5 (W < L).
Faceted by year and segment.

### T4 — Step zero: the unconditional excursion vector

**The first read of the outcome, and deliberately the only one in this brief. No attention measure,
catalyst or cross-sectional quantity appears in any T4 chart or table.**

For each rung N, across all of D1 with τ and a vector, and by slice, year, segment, price tier (R4),
`tau_close_sensitive`, A12 flag, `jump_share` band and edge class:

- **`u_peak` histogram with the simulated discrete free-walk reference drawn at that N** (Brief 1
  `t6_references.json`, same construction). **This is the picture that tests the theory's premise:** mass
  piled at both ends is what no drift looks like; an interior hump is a rise-then-fall.
- **ECDFs of `rise_s`, `fall_s`, `dip_before_peak_s`, `terminal_s`**, each with its simulated no-drift
  reference.
- **`rise_bp` and `rise_cents` against the round-trip cost** (70.98 bp flat, 2.512 ¢ per share): the
  share of events whose full rise exceeds one round trip, per price tier. This is the unconditional
  version of the necessary-condition cost gate (Part I, I.5b).
- **A gallery:** 72 events drawn with a fixed seed, stratified by year × segment, each strip showing the
  bucketed path with τ, peak and end marked. One chart with an event selector.

Edge classes are always shown as their own rows. Nothing is pooled across rungs.

### T5 — Report

`REPORT.md` describes the pictures. **No interpretation, no findings section.** It opens with the
escalation table and the II.5 checks, then T1–T4 in order, then the column dictionary (§5).

### T6 — HARD STOP

Commit, push, post: escalation table, T1/T2 coverage, the competition excess table, and the step-zero
headline numbers per rung (median `u_peak`, `rise_s` against reference, cost-clearing share by price
tier). Cooper reads step zero before anything else is written. Part I's kill condition 1 (the
rise-then-fall does not show in the aggregate) is his call, from these pictures.

## 4. Escalation

| row | criterion | tier |
|---|---|---|
| 1 | excursion vector available on fewer than 95% of events with τ | HARD STOP |
| 2 | any causality assertion fires | HARD STOP |
| 3 | any segment assertion fires (a rung half, or a competition window, spans a segment boundary or contains an auction minute) | HARD STOP |
| 4 | the config diff contains anything outside §1 | HARD STOP |
| 5 | `shs_asof_ns ≥ τ` for any event | LOG, per event |
| 6 | thin paths above 10% of D1 | LOG |
| 7 | halt-flagged paths above 40% of D1 | LOG |
| 8 | baseline cells below 20 moments hold more than 25% of competition pairs in any (L, W) | LOG |

## 5. Column dictionary — for the threshold suite

The report ends with a generated table of every column in the b2 artifacts: name, type, units, and
whether it is pre-τ (attention), post-τ (excursion), or a facet. The threshold suite reads from this, so
it must be generated from the artifacts, not typed. Include the Amendment 3 renames (`H_s` from the
segment start, `H_0400_s`, `a2_state`, `a2_anchor_ns`, `tau_anchor_segment`, `tau_in_auction_minute`,
`win_lo_ns`, `win_mid_ns`, nullable A2 counts) and the new absolute level measures.

## 6. What this brief does not do

- Put any attention, catalyst or cross-sectional quantity against any excursion component, in any
  chart, table or summary.
- Set any threshold, or use any percentile for a bin edge or default.
- Build the threshold suite. That comes after Cooper reads step zero.
- Pull news or touch the network.
- Use the participation gate, relative volume, `momentum_pct` in a computation, the vendor float, or
  financial statements.

## 7. Verification — executable

D1 = 15,763; τ = 15,519; slices partition D1; dev and sidecar quarantined · `tau_ns` int64 in every
artifact (Brief 1 found it drifting to float64 twice) · causality assertion exercised by a test that
feeds a post-τ print and requires the raise · segment assertion exercised by a test that feeds a
straddling window and requires the raise · bucket volume conservation · config diff script · every
report number read from artifacts.
