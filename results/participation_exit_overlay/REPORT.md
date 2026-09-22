# Participation / exit overlay — does the first window close inside live participation? — REPORT

**Branch:** `explore/participation-exit-overlay` · **Config hash:** `b1db4f659320`
**Status: complete.** T1–T4 ran, six charts. No rebuild recommendation — that call is Cooper's off
these numbers, per the brief.

Brief: `prompts/participation_exit_overlay.md`.

**Headline: the mismatch is real, and closing it is worse.** EPG exits while participation is still
live in **76.2%** of events, median **2.2 hours** before participation actually decays. But swapping
the window-close exit for a participation-tracking exit — same entry, same single round trip —
**loses more money**: gross median falls from **−0.9 bp to −264.6 bp**, and every net figure moves
the same direction. The counter-case the brief asked to be given a fair chance wins.

---

## Population

**903 of 15,763 D1 events = 5.7%**, val split 2023-11-17 → 2024-07-22. Reused, not rebuilt: v1-T0's
tick-exact gap-gate reconstruction (queued entries, next-tick fills, validated 6/6), with v2-T1's
snapped int64 `tau_ns`. Not a measurement over D1.

## E2 reuse — partial, and why

`B_e` is reused **verbatim** from `results/fundamental_exploration/e2/artifacts/e2_t2a_baseline.parquet`
— mean dollar volume per 10-minute RTH block over the available prior sessions, the same construction
v0-T0 verified (`total_baseline_dollar_volume / B_e` = `n_baseline_sessions × 39`).

**E2's window artifact is not reusable as an exit and was rebuilt.** Checked before building on it:

| check | result |
|---|---|
| `window_end_ts` before the EPG entry `τ` | **443 of 903 (49.1%)** — an exit cannot precede its entry |
| `duration_min == 0` | **40.75%** — participation "ends" at `t0` itself |
| `window_end_ts − τ` maximum | **433,365 s = 5.0 days** — not censored at the session end the brief attributes to E2 |
| `censored` column | **`False` on all 15,742 rows** |

E2's brief, config and code were never committed — only its artifacts — so the declared `C`, the
volume basis, and the censoring rule cannot be read from the repository. **`participation_onset` and
`participation_end` were rebuilt here** from `event_minute_bars_v2` under the rule the brief states,
with censoring at the event-day extended session end applied structurally (the minute series is
restricted to `session_offset = 0`, which is what enforces it). `C` is **declared here** at 10 minutes
with a {5, 10, 20} sensitivity ladder — the brief's instruction to carry E2's value could not be
honoured because that value is unrecoverable.

## An unanticipated data-quality defect, found and fixed mid-run

Exit prices are tick-exact: the last print at or before the exit timestamp, from the event's own
`trades.parquet`, recomputed on one basis for both arms and cross-checked against v1's own recorded
fill price. That cross-check caught something the brief did not anticipate.

**AMC 2024-05-14**: entry and v1's recorded exit both **$6.63**; the naive lookup priced the exit at
**$11.48** — a single 4-share print carrying condition codes `[32, 37]` (37 = odd lot, confirmed in
this repo's `docs/data/condition_indicator_code_reference.md`; **32 is not resolved in this repo and
its meaning is not asserted here**), sandwiched between two $6.63 prints microseconds apart. Before a
fix, 154 of 903 exits (17%) differed from v1's recorded price by >1%, 19 by >5%, **3 by >20%**.

Odd lots are **44% of all trades** in this archive (checked on this event alone: 1,514,946 of
3,472,949), so excluding them outright would be a large, uncited methodology change incomparable with
v0/v1/v2's raw next-tick fills, which apply no condition filter at all. Instead: a **spike guard**,
declared for this task only, not claimed as an established repo convention — a picked print is
replaced by walking back to the nearest non-spike print only if it deviates from *both* its immediate
neighbours by more than 3% *and* those neighbours agree with each other (the V-shaped signature of an
isolated bad print reverting immediately, as opposed to a genuine fast move, which does not revert).

**10 Exit-A and 9 Exit-B prices were replaced.** AMC now reads exactly $6.63 = $6.63. After the fix,
mismatches >5% fall to 14 and >20% to **1** (NTRP 2024-03-14, a real fast move confirmed by inspection,
not a reverting spike — left as a residual, not chased further). The effect on every headline median
below is under 2 bp; the fix matters for individual-event accuracy and for not letting one wild print
corrupt a tail statistic, not for the direction of the finding.

---

## T1 — participation onset and end

`t1_participation.py` · 49.5 s · rule: trailing 10-minute **sum** of minute dollar volume (the
quantity dimensionally comparable to `B_e`, itself a per-10-minute figure — a per-minute average
would be 10× too small), crossing 3×`B_e` and holding for `C = 10` consecutive minutes.

| | n | share |
|---|---|---|
| bars available | 903 | 100% |
| onset found | 893 | 98.9% |
| **onset censored** | 10 | 1.1% |
| end found | 782 | 86.6% |
| **end censored** | 121 | 13.4% |

**Participation is almost always already live at `t0`.** 71.0% of events have trailing volume ≥3×`B_e`
*at* `t0` itself (median ratio 3.42×), which is why onset pins near `t0`+1 minute for most events — a
consequence of `t0` being the detection anchor where the burst is already underway, not a rule
artifact.

**Causal confirmation, applied structurally.** The rule requires a crossing to hold for `C` minutes,
so the earliest instant it is *knowable* is `C` minutes after the crossing began. Exit B is
timestamped at that **confirmed** instant, never at the crossing's start — using the start would let
the exit use `C` minutes of information that had not happened yet, exactly the lookahead class this
programme has spent three prior builds removing. Before this was wired in, 70 of 903 candidate Exit-B
holds computed as **negative length**; after, zero, and zero exits were clamped against their own
entry.

## T2 — the timing overlay

`t2_overlay.py` · four timestamps per event on one clock, seconds from `t0`.

| mark | p5 | p25 | **median** | p75 | p95 |
|---|---|---|---|---|---|
| onset | 40 | 57 | **60** | 60 | 11,016 |
| τ (EPG entry) | 9 | 52 | **411** | 1,617 | 14,701 |
| window close (EPG exit) | 63 | 703 | **1,378** | 2,678 | 14,966 |
| participation end | 59 | 1,680 | **9,269** | 26,324 | 46,599 |

### HEADLINE — `window_close − participation_end` (seconds)

| | value |
|---|---|
| n defined (uncensored) | 782 |
| p25 / **median** / p75 | −24,738 / **−7,802** / −203 |
| **share negative** | **76.2%** |
| censored (participation never decays) | **121 (13.4%)**, excluded from this statistic by construction, reported separately |

**Three of every four events have EPG closing the position while participation is still live**, by a
median of **2.2 hours**. Adding the censored 13.4% — where participation never decays inside the
session at all — the share of events where the window-close exit is *not* tracking participation
decay is **79.4%** (596 uncensored-negative + 121 censored = 717 of 903).

### `τ − participation_onset` (seconds) — the entry side is fine

| | value |
|---|---|
| median | **+296** |
| share negative (EPG enters *before* onset) | **35.4%** |

EPG enters a median of ~5 minutes *after* participation arrives — a small lag, not a mismatch. The
problem is entirely on the exit side.

### Facets

| facet | headline median (sec) | reading |
|---|---|---|
| `n_baseline_sessions` | 3-session cell: −8,095 (n=775); 1- and 2-session cells below the display floor (n=1, n=6) | population is overwhelmingly 3-session; thin-baseline facets uninformative here |
| **session segment** | pre-market **−6,919** (n=509, 69.9% negative); RTH **−8,370** (n=272, **88.2% negative**) | the mismatch is *worse* in regular hours |
| detection-price decile | ranges −15,956 (decile 2) to **−2,149** (decile 9, cheapest→priciest) | narrows at higher prices but stays negative in every decile |
| entry gap × segment | pre-market median +306 (33.7% negative); RTH median +258 (39.1% negative) | consistent across segments — entry timing is not the lever anywhere |

---

## T3 — the counterfactual exit, which decides the rebuild

`t3_counterfactual_exit.py` · one round trip per arm; Exit A and Exit B priced on the identical tick
basis (spike-guarded), so nothing is compared across bases.

### Uncensored, like-for-like pair (n = 775) — all figures in basis points

| | **A · window close** | **B · participation decay** |
|---|---|---|
| gross median | **−0.9** | **−264.6** |
| gross mean | 79.0 | −329.3 |
| net median, flat cost | −71.9 | −335.5 |
| net median, per-share cost | −244.5 | −547.1 |
| win rate, gross | **44.5%** | **40.5%** |
| win rate, net (flat) | 39.9% | 38.3% |
| median hold | 565 s | **11,148 s** (3.1 h) |

**Exit B loses on every column.** Gross median falls 264 bp further, gross mean flips from positive
to negative, and win rate drops nearly 4 points — for a hold **20× longer**. The single round trip is
amortised over far more exposure and the amortisation does not pay: this is not a cost story, it is a
direction story.

### The full distribution

| arm | p1 | p5 | p25 | **p50** | p75 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| A window close | −2,459 | −1,366 | −545 | **−1** | 447 | 2,170 | 4,615 |
| B participation decay | −5,370 | −3,833 | −1,370 | **−265** | 663 | 3,001 | 5,487 |

B is worse across the whole distribution, not just at the median — wider on the downside (p1 −5,370
vs −2,459) and only marginally better in the extreme right tail (p99 5,487 vs 4,615, not enough to
offset the rest).

### Censored class — reported separately, not pooled (n = 128, 14.2%)

| | A · window close | B · session-end horizon |
|---|---|---|
| gross median | 0.0 | **+1,702.5** |
| win rate | 46.9% | **64.8%** |
| median hold | 1,025 s | **42,575 s** (11.8 h) |

**The censored class inverts the finding**, and it is exactly the group where participation runs so
hot it never confirms a 10-minute decay inside the session. Held to the session-end horizon these
events are strongly positive. But this is **not** a tradeable intraday result — an 11.8-hour hold is
an overnight-class position under D5, a different risk than anything else in this report, and it is
labelled as such rather than blended into the headline pair.

### Markout in the gap — what EPG leaves on the table, or avoids

Price change from window close to the participation-decay exit, all 903 priced events:

| | value |
|---|---|
| median | **−106.9 bp** |
| mean | +201.5 bp |
| share positive | 45.7% |

Median negative, mean positive — right-skewed, consistent with the counterfactual result: on the
typical event EPG's early exit **avoided** further downside (median favours A), but a smaller share of
events run hard enough afterward to pull the mean the other way. Chart 04 shows the full shape.

### By detection-price decile and by `move_at` decile

Full tables in `artifacts/t3_counterfactual_exit.json`; both are below the display floor of 20 in no
decile. The `move_at`-decile cut is the one that tests directly whether the deeper-entry penalty
found in v2-T3 and R0-T0c2 survives a participation-tracking exit:

| move_at decile | 0 (least moved) | 5 | 7 | **9 (most moved)** |
|---|---|---|---|---|
| A gross median | +0.9 | 0.0 | −387.6 | **−378.6** |
| B gross median | +124.8 | −71.4 | −1,085.9 | **−3,066.9** |
| B win rate | 52.5% | 48.1% | 25.0% | **8.3%** |

**It does not survive — it gets worse.** At low `move_at`, B is competitive with or beats A (decile 0:
+124.8 vs +0.9). By decile 9 — the deepest entries — B collapses to −3,067 bp with an **8.3% win
rate**, against A's already-poor −379 bp. The deeper-entry penalty T3 (of the v2 run) and R0-T0c2 both
found on other trade definitions is not just present under a participation exit, it is **amplified** by
holding longer into a position that was already too deep at entry.

### Halt exposure

| | coverage | Exit A | Exit B |
|---|---|---|---|
| exact labels (LULD-V3c) | 73 of 903 (8.1%) | 0.0% span a labelled halt | **6.85%** span a labelled halt |
| gap proxy, >60 s inter-trade gap | full 903 | 3.5% of holds | **67.7%** of holds |

**Both measures point the same direction and the gap proxy's scale is stark**: extending the hold
from window-close to participation-decay raises the share of holds crossing at least one large
inter-trade gap from 3.5% to 67.7%. The exact-label figure (0% → 6.85%) is on only 8.1% of the
population and is a lower bound; the proxy is a gap measurement, not a halt classifier, and is
labelled as a limitation on the Exit B result rather than a confirmed halt count. Both are consistent
with the programme's standing finding that exit timing dominates halt exposure and that a longer hold
increases it.

---

## Charts

`results/participation_exit_overlay/charts/` · standalone Plotly HTML, one per file, Plotly inline
(offline, D14), light theme per E1's precedent.

- **`01_event_timeline_strip.html`** — the four timestamps per event, sorted by the headline gap.
  Where the orange window-close dot sits left of the red participation-end dot is the mismatch,
  directly.
- **`02_gap_distributions_ecdf.html`** — both gap ECDFs. Red (headline) crosses zero far left of 0.5;
  blue (entry) sits close to it.
- **`03_exit_a_vs_b_ecdf.html`** — the decision chart. A and B markout ECDFs, both cost bars drawn.
- **`04_markout_in_the_gap.html`** — the histogram behind the median/mean split above.
- **`05_by_detection_price_decile.html`**, **`06_by_move_at_decile.html`** — A vs B medians by decile,
  n annotated per bucket.

---

## What this settles

Per the brief's own framing:

> **Mismatch real, Exit B worse.** EPG's early exit is doing real work by stepping out before the
> flip. The mismatch is structural and closing it is still wrong. The qualification layer's problem
> is elsewhere.

That is the outcome measured here. The overlay confirms the mismatch (76.2% negative, median 2.2
hours) — but the counterfactual, run with a fair chance for Exit B to win, shows closing it costs
money: gross median −0.9 → −264.6 bp, win rate 44.5% → 40.5%, and the effect is **worst exactly where
T3 (v2) and R0-T0c2 already found the damage concentrates** — deep `move_at` entries, where B's win
rate falls to 8.3%.

**This does not identify where the qualification layer's problem is** — only that it is not the
exit's failure to track participation. That question is open.

---

## Constraints held

`move_at` is the only move measure — `momentum_pct` enters no threshold, score or slice. D4: every
quantity tick- or bar-derived from D4-clean sources; `event_minute_bars_v2` is Phase 6b's tick
aggregate (D5 A11, reuse needs no citation); no spine numeric column enters any computed quantity. D5:
long-only, no short or fade variant; the censored class's session-end hold is explicitly labelled as a
different risk rather than folded into the intraday result. D19: every cost figure in both bp and
cents. E2 DE-2: `baseline_thin` flagged and carried (7 of 903). E2 DE-3: censored events are their own
class throughout, no mean taken across censored and uncensored. Coverage flagged and carried at every
step: 10 onset-censored, 121 end-censored, 128 Exit-B-censored, 19 spike-guard replacements, 1 residual
large price mismatch (NTRP 2024-03-14) left unresolved and disclosed.

**Reproducibility gap, unchanged from v0/v1/v2:** `B_e` is from
`results/fundamental_exploration/e2/artifacts/`, still uncommitted.
