# Attention and the excursion — Brief 1 — HARD STOP at T2 (escalation row 4)

**Date:** 2026-09-23 · **Branch:** `explore/attention-excursion-b1`, cut from
`explore/participation-exit-overlay` · **Brief:** `prompts/attention_excursion_b1.md` (Part II) ·
**Config:** `config/attention_excursion_b1.json`, committed in `dec1d70` before any run, hash
`148f44d2165d`.

**Status: stopped.** Escalation row 4 fired on the full-D1 T2 run. Per the brief and CLAUDE.md, nothing
after T2 was run: no T3 profile, no excursion vector, no attention axis, no competition check, no
control. The stop is posted below with the criterion, the observed value, and how the observed value
breaks down. Nothing has been fixed or re-tuned since the stop.

**The brief arrived truncated** at 50,000 characters. It ends partway through escalation row 6 ("thin
paths above 20% of th"), so escalation rows 6 onward and all of Part III (the E2 units fix) were never
received. The filed copy says so.

---

## 1. The stop

| row | criterion | observed | tier | state |
|---|---|---|---|---|
| 1 | `tau_available` below 90% of D1 | **15,632 of 15,763 = 99.17%** | HARD STOP | not fired |
| **4** | `tau_exact − tau_proxy` outside [−1, 61] s for more than 2% of D1 | **2,774 of 15,763 = 17.60%** (18.10% of the 15,322 comparable) | **HARD STOP** | **FIRED** |
| 2 | any T6 control fails | — | HARD STOP | not reached |
| 3 | any print after τ reaches an attention quantity | — | HARD STOP | not reached |
| 5 | `shs_asof_ns ≥ tau_ns` | — | LOG | not reached |
| 6 | "thin paths above 20% of th…" | — | tier never received | not reached |

Code path: `research/attention_excursion_b1/t1_t2_prior_close_tau.py` (the tick pass) →
`t1_t2_summary.py` → `artifacts/t1_t2_summary.json` `escalation.row_4`. Per-event list (not averaged, as
T2 asks): `artifacts/t2_proxy_outside_band.parquet`.

### What the 2,774 are made of

The proxy (v1's `t5_d1_candidate_moments.parquet`) is not just a coarser clock. It also uses a
**different prior close**: the last regular-hours minute bar's `last_price`. T1 replaced that with the
closing-auction print, which is what the brief asks for. To separate the two, the same pass also
computed τ against the minute-bar close (`tau_mb`). That holds the prior close fixed at the proxy's
own, so only the print-versus-minute-stamp difference remains:

| comparison | n | inside [−1, 61] s | outside |
|---|---|---|---|
| `tau_mb − tau_proxy` — same close as the proxy; stamp difference only | 15,313 | 15,090 (98.5%) | **223 (1.5%)** |
| `tau_exact − tau_proxy` — exact close, D1 comparable | 15,322 | 12,548 | **2,774 (18.1%)** |
| … where the exact close **equals** the minute-bar close | 5,012 | 4,943 | **69 (1.4%)** |
| … where the exact close **differs** from the minute-bar close | 10,310 | 7,605 | **2,705 (26.2%)** |

Attribution of the 2,774, by rule (`cause` column in the per-event artifact):

| cause | n |
|---|---|
| prior-close change: τ under the minute-bar close sits inside the band, τ under the exact close does not | **2,551** |
| spike guard: the guard skipped a print the proxy's minute high included | 188 |
| other | 35 |

- **Every prior-close-caused shift goes the direction the threshold predicts.** A lower exact close
  moves τ earlier and a higher one moves it later, in 2,551 of 2,551.
- **The shifts are large when they occur.** Among the 2,774, |Δ| has median 202 s, p75 951 s and p90
  4,821 s. The largest is 43,199 s, about 12 h.
- **By direction:** 1,273 fall below the band (exact τ earlier) and 1,501 fall above it.
- **By year**, the outside share is 17.9% (2020), 13.9% (2021), 20.4% (2022), 18.9% (2023) and 18.4%
  (2024). The effect runs across all five years, not one.

**What the observed value says, stated without a remedy.** On the stamp difference alone, the proxy and
the exact rule agree (1.5%, under the 2% threshold). They disagree because the two prior closes
disagree. The brief expected "0–60 s for nearly all events", which assumed the only difference was the
stamp. On 10,310 of 15,322 events the prior close itself moved, and a move of tens of bp in the +30%
level shifts the first crossing print by minutes to hours on a tape hovering near the line.

→ `charts/attention_excursion/b1/t2/01_tau_exact_minus_proxy_ecdf.html`: ECDF of Δ on an asinh axis,
with every value drawn. Four series: all comparable; exact close equal to the minute-bar close; exact
close different; and the fixed-close decomposition. The shaded band is [−1, 61] s.

---

## 2. What ran

### T0a — population (`t0_population.py` → `artifacts/t0_population.json`)

D1 asserted at **15,763** against `results/phase_5a/artifacts/sampling_frame.parquet`: all rows are
`file1`, `(ticker, date)` is unique, and every event resolves to exactly one folder. The 50 dev events
(`config/dev_sample_v3.json`) and the 6 `dev_v4_sidecar` events are all inside D1 and disjoint from each
other. CLAUDE.md's index verifier (`tools/verify_claude_md_indices.py`) printed **ALL INDICES CLEAN**
(exit 0) before any work.

### T0b — slices (`results/attention_excursion/b1/slices.parquet`, one row per D1 event)

| slice | dates | before quarantine | after quarantine | first-seen tickers | distinct tickers |
|---|---|---|---|---|---|
| development | 2020-01-01 → 2022-12-31 | **7,650** | 7,620 | 7,620 (100% by construction) | 1,911 |
| selection | 2023-01-01 → 2024-07-22 | **5,409** | 5,389 | 1,792 (33.3%) | 1,418 |
| final | 2024-07-23 → 2024-12-31 | **2,704** | 2,698 | 448 (16.6%) | 1,049 |
| dev_quarantine | any | — | 56 | — | — |

- **Before quarantine:** 7,650 / 5,409 / 2,704, exactly the brief's expected counts.
- **Quarantine by date:** 25 + 5 events from development, 20 + 0 from selection, 5 + 1 from final (dev +
  sidecar in each).
- **Assertions passed:** the slices partition D1 exactly, and every dev and sidecar event sits in
  `dev_quarantine` and nowhere else.

### T0c — D38

- Appended verbatim to `docs/Universe-Decisions.md`.
- The `CLAUDE.md` index now carries D38, and the next-free pointer is D39. Both changes landed in
  `dec1d70`.
- D38 was confirmed free on this branch, `origin/master`, both `origin/explore/fundamental-e*` branches
  and `origin/claude/attention-and-the-excursion-v3`.

**Not changed:** CLAUDE.md's Standing-methodology line "Ticker-blocked splits — no ticker on both
sides" still states the rule without D38's exception. The brief asked only for the index update.

### T1 — exact prior close (`artifacts/t1_prior_close.parquet`)

**Rule (config `t1_prior_close`).** On the prior XNYS session, the price is the largest-size print
carrying condition code 8 or 15 (the Amendment 6 override). Ties go to code 8 first, then to the latest
timestamp. When no such print exists, the rule falls back to the last print inside the calendar's
regular-hours bounds. Repair siblings are read.

| source | n |
|---|---|
| auction print {8, 15} | 15,576 |
| fallback — last RTH print (auction print absent) | **146** |
| unavailable — no prints on the prior session date | 34 |
| unavailable — prints, but none in regular hours | 7 |
| **coverage** | **15,722 of 15,763 (99.74%)** |

Unavailable events by year: 4 in 2020, 5 in 2021, 9 in 2022, 8 in 2023 and 15 in 2024. They are
carried with `prior_close_available = FALSE`.

**|exact − minute-bar close|, bp**, n = 15,721:

| statistic | value |
|---|---|
| p25 | 0 |
| median | 25.5 |
| p75 | 93.5 |
| p95 | 345 |
| p99 | 730 |
| max | 30,265 |
| exactly equal | 5,065 |
| > 100 bp | 3,689 |
| > 500 bp | 389 |

The signed difference is centred on 0: p05 −241, p95 +197.

**Why the two closes differ.** The minute-bar build segments on the timestamp rule alone. Closing
auction prints land a median 0.28 s after the bell (p95 24.8 s, the late tail from official-close
reports), so they fall outside every RTH bar. The minute-bar close is therefore the last *continuous*
print, never the cross.

→ `charts/attention_excursion/b1/t1/01_prior_close_exact_vs_minute_bar.html`

**A defect in the T1 rule, found reading the census after the stop, recorded and not fixed.** The
config justifies "largest size" as a way to select the listing venue's auction without hard-coding an
exchange id. A 150-session survey supported that. On all of D1 it does not hold:

- The chosen print came from **exchange 11 on 3,913 events**, of which 3,145 also had a code-8 cross on
  record.
- On **2,599** of those events the chosen price is exchange 11's own official close, not the listing
  venue's code-8 cross. This happens when exchange 11's print is the larger of the two, e.g. LMFA
  2021-10-15: 5,000 shares at $3.4301 against the cross at $3.44.
- A further 10 events differ at exchange 12.

**This does not produce the stop.** Where the chosen print *is* the code-8 cross, the outside-band share
is still **19.1% (2,423 of 12,671)**. The code-8 price itself differs from the minute-bar close by a
median of 38.3 bp (p75 110 bp).

### T2 — exact τ, all of D1 (`artifacts/t2_tau.parquet`, `tau_ns` int64)

**Rule (config `t2_tau`).** τ is the first print at or after 04:00 ET, in `(sip_timestamp,
sequence_number)` order, with price ≥ 1.30 × the exact prior close, excluding spike-guard failures. The
search stops at 20:00 ET.

**Availability and placement**

| quantity | value |
|---|---|
| τ available | **15,632 (99.17%)** |
| never crosses | 90 |
| prior close unavailable | 41 |
| segment (Amendment 6 `assign_segment` on the τ print's own codes) | RTH 11,036 · premarket 4,590 · post 6 |
| A12 `flag_cross_session_extreme` (`tm1_t0`) | flagged on **886** of the 15,632; missing on 0 |

**Condition codes on the τ print**

| codes | n |
|---|---|
| none | 4,854 |
| [37] odd lot | 2,877 |
| [14, 41] | 1,800 |
| [12, 37] | 1,203 |

Codes 12, 14 and 41 are not resolved in this repo and are not interpreted here. The full top-12 list is
in the JSON.

**Spike guard** (3% deviation from both neighbours, neighbours agreeing within 3%)

| quantity | value |
|---|---|
| τ moved by the guard | **590** events |
| move size | median 19.3 s, p75 219 s, p95 7,509 s, max 37,622 s |
| events with at least one print skipped | 623 |
| crosses without the guard, never with it | 33 |

The brief calls the guard "the exit overlay's construction" but states a 3% neighbour agreement. The
overlay's code used 1.5%, which would change τ on **148** events. The brief's 3% is what ran.

→ `charts/attention_excursion/b1/t2/02_spike_guard_moves.html`

**Carried per event:** `tau_price`, `tau_level`, `tau_codes`, `tau_session_segment`, `sec_from_0400`,
`sec_from_0930`, `shares_0400_to_tau`, `n_prints_0400_to_tau` (the I.6a speed facet), `tau_move_at`,
the A12 flag, the no-guard τ, the overlay-guard τ, `tau_mb`, and every proxy difference.

---

## 3. Not run

| task | state |
|---|---|
| T3 open-adjacent boundary | `t3_open_boundary.py` written before the stop and **never executed**; no profile, no proposed boundary |
| T4 excursion vector | `instruments.py` (buckets, components, both A2 ladders) written before the stop and **exercised only on synthetic input**; no event vector built |
| T5 / T5b attention axes and competition check | not written |
| T6 four controls | not run. The two criteria the config records as expected to fail by arithmetic (the negative-excursion bridge; the positive-acceleration coarser-rung clause) are therefore **untested predictions**, not results |
| T7 | this document replaces it at the stop; the only charts are the T1 and T2 charts above |

---

## 4. What the stop leaves for Cooper

Recorded as open decisions, not recommendations:

1. **Row 4 as written against what it was meant to catch.** The proxy disagrees with the exact rule
   because T1 changed the prior close (26.2% outside where the closes differ). The stamp difference
   alone stays inside the band (1.5%). Does row 4 stand as a stop on the prior-close change itself, or
   was it scoped to the stamp difference?
2. **The T1 tie-break.** On 2,599 events, largest size picked exchange 11's official close over the
   listing venue's code-8 cross. Should T1 be re-specified, for example as the code-8 cross with a
   code-15 fallback? Either way, row 4 still fires on the evidence above (19.1% where the chosen print is
   the cross).
3. **Whether T3 onward proceeds.**

Also outstanding, carried from before this brief:

- **Missing text:** escalation rows 6 onward and all of Part III were never received.
- **A false claim in an earlier report:** the participation-overlay report and its library-map entry
  say E2's brief and code "were never committed". They exist on `origin/explore/fundamental-e2` (and
  master via PR #13). This bears on Part III.

**Charts follow the brief's letter this time:** dark theme, top-level `charts/attention_excursion/b1/`
with a subfolder per task. R0 moved its charts under `results/` and used a light theme; that was a
recorded deviation, and this brief repeated the instruction.

---

## 5. Files

| path | what |
|---|---|
| `prompts/attention_excursion_b1.md` | the combined brief, verbatim, with a truncation filing note |
| `config/attention_excursion_b1.json` | every declared rule and pre-registered prediction (committed before any run) |
| `research/attention_excursion_b1/common.py` | population, folder index, tick reader (repair siblings, one schema), session clock, spike guard; reuses `assign_segment`, `collapse_tol`, `field_exact`, E1's share correction and the overlay's halt labels |
| `research/attention_excursion_b1/t0_population.py` | T0a, T0b |
| `research/attention_excursion_b1/t1_t2_prior_close_tau.py` | T1 + T2 tick pass, 10 workers, 1,332 s over 15,763 folders |
| `research/attention_excursion_b1/t1_t2_summary.py` | T1/T2 summaries, rows 1 and 4 |
| `research/attention_excursion_b1/charts_t2.py` | the three stop charts |
| `research/attention_excursion_b1/t3_open_boundary.py` | written, **not executed** |
| `research/attention_excursion_b1/instruments.py` | written, synthetic-checked only, **not executed on events** |
| `results/attention_excursion/b1/slices.parquet` | T0b |
| `results/attention_excursion/b1/artifacts/` | `t0_population.json`, `t1_t2_pass.parquet` (raw pass), `t1_prior_close.parquet`, `t2_tau.parquet`, `t2_proxy_outside_band.parquet`, `t1_t2_summary.json` |
| `charts/attention_excursion/b1/t1/`, `t2/` | 3 charts |
| `docs/Universe-Decisions.md`, `CLAUDE.md` | D38, pointer D39 |
