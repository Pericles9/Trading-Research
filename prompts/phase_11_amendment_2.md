# Phase 11 — Amendment 2

**Date:** 2026-08-16
**Amends:** `prompts/phase_11.md`, as amended by `prompts/phase_11_amendment_1.md`
**Trigger:** T4 gate reached. Stage A complete and clean at `1cda8bc` — 24-row audit passed with 0 failures, zero passes spent, no effective spread computed, no rule adopted by the agent.
**Effect:** Records the T4 gate decisions, authorises Stage B **conditional on T4b below**, and carries four additions arising from Stage A evidence.

**Re-audit required.** T0c re-runs the four-check satisfiability audit against the amended set — now **29 rows** — and against the amended config, before any Stage B task begins.

---

## A2-0 — T4 GATE: Stage B authorised, conditionally

BBO-derived cost **is** measurable in this universe. Consolidated best-quote confirmed (88.4% two-sided rows, 13 median RTH venues, 0 single-venue events). Zero null `sip_timestamp` on all three denominators. Resolution independently reproducing the Phase 10 v1 trades-side 49 / 80.5 ns. Session boundaries landing on the exact XNYS open and close minute. Alignment on pre-registered reading-rule row 1 at 0.9805 (RTH, T=0, sip).

**Authorisation is conditional on T4b clearing.** No Stage B task begins until it does.

### The qualifier that travels with every Stage B number

T2c: the prevailing best quote at a T=0 RTH trade has median age **1,372.6 ms**; **54.1%** of trades print more than 1 s after the last BBO change, **6.7%** more than 60 s. Quote-to-trade falls to 0.75. **This universe's top of book is wide and slow, not wide and fast.**

This does not contradict the 0.9805 at-or-inside figure — a stale quote wide enough to bracket the trade still counts as inside. It means the midpoint is a weak proxy for fair value at the instant of the print, and the error is two-sided: staleness inflates `|p − m|` during fast moves, while half-effective-spread understates the cost of getting **size** done against a book that is not refreshing.

> **Standing qualifier, required verbatim in REPORT.md §T7 and in the caption of charts 05, 06 and 07:** *Effective spread measures the cost of the average print, not the cost of a specific order. Depth, queue position and fill probability are not measured in this phase.*

Recorded to `docs/Open-Items-Register.md`: depth and queue-position measurement is unaddressed; the cost stack is a lower bound on execution cost.

---

## A2-1 — T4b: Reverse-chronological latent-error audit *(new gate task)*

T1c-v established the source parquet is stored **reverse chronological** — `sip_timestamp` decreasing across 99.97% of consecutive file rows at the median event, on all 50 events. Handled here, because every Phase 11 query orders explicitly.

**The exposure is not here.** Phase 11 reuses Phase 8's `det_anchor` and Phase 9's fixed-horizon grid **frozen**. If any code path that produced them took head-of-file rows as session start, or used `LIMIT` without `ORDER BY`, Phase 11 inherits the error silently and the headline is built on it. This is the D4 failure shape — a quantity trusted for several phases before its basis was checked.

> - [ ] **T4b — Ordering-assumption audit.** Read-only, code only, no data touched, no pass spent.
>   - [ ] T4b-i — Across `src/` and every prior phase's committed code, enumerate: `LIMIT` without a governing `ORDER BY`; `head(`/`.first(`/`[0]`/`FETCH FIRST` applied to parquet or table reads; any use of `read_parquet` where row order is treated as chronological; any `first_value`/`last_value` without an explicit window ordering.
>   - [ ] T4b-ii — For each hit, classify: **(a)** cannot affect an artifact Phase 11 reuses frozen; **(b)** could affect one; **(c)** does affect one. Name the artifact and the line.
>   - [ ] T4b-iii — Report the table. **Any class (b) or (c) hit is escalation row 25 — hard stop.** Class (a) hits are recorded to the register and do not block.

Estimated cost: under an hour, no compute.

---

## A2-2 — Instrument reference convention *(D16)*

> **D16.** For Phase 11 and all subsequent quote-derived work: the reference midpoint is the **contemporaneous consolidated best quote at δ = 0 on the `sip_timestamp` basis**, with `sequence_number` as the secondary ASOF key. A single basis is used across all segments.

**Offset — δ = 0, not the +100 µs peak.** The peak sits **0.0003** above δ=0 in at-or-inside share, while the measured between-segment peak instability is **7 rungs**. Selecting +100 µs would fit a signal two orders of magnitude below the noise already measured. δ=0 is contemporaneous, defensible without appeal to a fitted value, and requires no later justification.

**Basis — `sip`, single, whole phase.** Differences are marginal in both directions (sip higher in RTH 0.9808 vs 0.9779; participant higher in premarket). **Segment is a headline reporting axis**, so switching basis by segment would place a measurement artifact directly on the axis being compared across. `sip` wins in RTH, the cell row 11 names.

> - [ ] **T6e (new) — Participant-basis robustness line.** Recompute the T6 effective-spread medians on the `participant_timestamp` basis, premarket and RTH, and report as a single robustness table. **Not primary, not charted, no claim rests on it.**

**Tie handling.** `sequence_number` never inverts under the sip sort on any event and breaks all 58,465 tied-sip rows uniquely. Use it; do not fall back to arbitrary order on ties.

---

## A2-3 — Exclusion rule *(D17)*

> **D17.** A quote row is **excluded** if crossed (`bid > ask`), price null or ≤ 0, one side missing, or `bid_size`/`ask_size` null or zero. **Locked quotes are carried.** No event is excluded on quote-quality grounds.

**Locked is carried** because it is a real transient state with a genuine zero spread; dropping it biases measured spread upward.

**This choice is not load-bearing and no further effort is spent on it.** RTH `state_hard_unusable` median is exactly 0.000000, p95 0.0073; `one_side_miss` and `null_price` occur in zero of 150 T=0 cells.

**No event exclusion — instead, a covariate.** The dirtiest event reaches 12.8% unusable time. Excluding events on a quality metric is post-hoc selection.

> - [ ] **T5b addition** — carry `unusable_time_share` per event × segment into `event_quote_metrics_v1`.
> - [ ] **T7g (new)** — report the T7 headline with and without the 3 events above 1% unusable share, and state whether the headline moves. Description only.

---

## A2-4 — Stage B population *(D18)*

> **D18.** Stage B computes all 15,369 detection-universe events and reports all three segments. **The viability decision rests on the RTH cell alone.** Premarket and post are reported and charted; no kill/clear decision is taken from them.

`quotes_ingested = FALSE` excluded per D15, count reported as its own row in the filter waterfall. No staleness-based event exclusion.

The RTH-only decision cell was already justified on sign in Phase 9. Stage A adds a second, independent justification: **premarket median quoted spread 760.3 bp with 62.3% of trades on quotes older than 1 s and 30.7% older than 60 s; post 250.6 bp and 75.3% / 44.3%.** Both are reported; neither carries the decision.

---

## A2-5 — Kill threshold and the cost-multiple columns

**`config.kill_threshold = 0.50` confirmed** — row 11, RTH, latency 5, hold 30, at 1× cost, n = 10,607. The trigger is unchanged.

**Pre-registered before the run, so it cannot be read as post-hoc:** given the staleness picture in A2-0, the **1.5× column is expected to be the more honest read of realised cost**, because adverse selection, slippage past the touch on size, and fees all sit outside the effective-spread measurement.

> The 1× column remains the sole trigger for row 11. The 1.5× column is reported with **equal prominence** in every table and on every chart. REPORT.md records that this expectation was set at the T4 gate, before Stage B ran. It is a statement about which column to read, **not** a prediction about the result, and it does not license any evaluative sentence — row 18 applies unchanged.

---

## A2-6 — Basis points versus cents *(D19)*

Stage A T2e, RTH median time-weighted quoted spread: **165.0 → 127.6 → 83.9 bp** across T−3 / T−1 / T=0, a 49% fall. In cents over the same points: **3.64 → 3.43 → 3.79**, a 4% *rise*.

Backing out the implied price from each bp/cents pair: **≈ $2.21 at T−3, ≈ $4.52 at T=0.** Price roughly doubled. **The basis-point compression is the denominator growing.** The absolute spread is flat to slightly wider on the event day.

Two consequences, both structural:

1. Because detection fires after a ~30% move, **the bp spread at detection is mechanically compressed relative to the baseline session.** A cost estimate built from a baseline-session spread overstates detection-time cost in bp.
2. **A baseline-session spread is therefore not a valid proxy for detection-time cost**, in either unit, and must not be used as one.

> **D19.** Every spread and cost quantity in this program is reported in **both basis points and cents**. Neither unit is reported alone. No baseline-session (T−1, T−3) spread is used as a proxy for detection-time cost.

> - [ ] **T2e-i (new, retrospective on committed Stage A output)** — add the implied-price decomposition to REPORT.md: median implied price at T−3, T−1, T=0 per segment, derived from the bp/cents pair, with the arithmetic shown. Description only — state that bp falls while cents does not, and that implied price rises. **No characterisation of what that is good or bad for.**

---

## A2-7 — Impact windows *(config edit, before T5b)*

> `config.impact_windows = [1s, 5s, 30s, 60s]`. **No window shorter than 1 s.**

With trade-weighted BBO age at an RTH median of 1,372.6 ms, any sub-second window is dominated by exact-zero Δmid and attenuates toward zero — the same zero-atom pathology Phase 9 hit at short holds and high latency, which fixed the median in 34 of 450 grid cells. Setting this before the pass avoids discovering it after.

New escalation row 23.

---

## A2-8 — Staleness covariate in the cache *(T5b addition)*

Nearly free during a pass already being paid for; expensive to retrofit. **The retrofit-versus-carry decision is the exact shape of the mistake that produced D4.**

> - [ ] **T5b addition** — per event × minute × segment, carry into `event_quote_metrics_v1`: `bbo_age_at_trade_p50`, `bbo_age_at_trade_p95`, `trade_share_age_gt_1s`, `trade_share_age_gt_60s`, `n_bbo_changes`.

> - [ ] **T6f (new) — Staleness confound test.** Effective spread against `bbo_age_at_trade_p50`, within participation quintile, RTH. This is the diagnostic that tests whether the headline effective spread is measuring cost or measuring staleness. **Chart 09.** Distribution, not a fitted slope.

New escalation row 24 guards the cache columns.

---

## A2-9 — Watchdog carve-out, bounded

The agent-authored carve-out is accepted in principle and **bounded**. As written it was an unbounded exemption for one query.

> `config.query_watchdog_seconds` applies to every query in the phase **except the single budgeted T5b pass**, which is instead bounded by `config.runtime_ceiling_seconds = 21600`. **The ceiling is that query's watchdog.** No query anywhere in the phase is unbounded.

`runtime_ceiling_seconds = 21600` accepted. T5a's dev-tier extrapolation remains the primary protection; the ceiling is the backstop.

New escalation row 26.

---

## A2-10 — Housekeeping from the three Stage A flags

- **Row 2 wording** — update to name **T0c**, the post-rename audit task. Editorial; no logic change.
- **Row 4a segment scope** — fix to `T=0 RTH segment, per event`. All three denominators returned exactly 0, so the ambiguity was moot; close it anyway.
- **`indicators`** — populated on 88.85% of source rows, but 99.77% carry a single code and no dictionary exists on disk. **Available and uninterpretable.** Not used in Phase 11. Recorded to the register with the full census so a future phase starts from it. Row 22 continues to bar inferring meaning from values.

> **Correction on record.** The original prompt asserted, from a two-row sample, that `indicators` was likely null archive-wide and the withdrawn-quote route probably closed. That was wrong on the fact and right on the consequence, for the wrong reason. The route is open and unusable.

---

## A2-11 — New escalation rows

| # | Condition | Threshold | Action |
|---|---|---|---|
| 23 | Any impact window shorter than 1 s | any | Hard stop |
| 24 | `event_quote_metrics_v1` missing any A2-8 staleness column at T5c integrity check | any | Hard stop before T6 — do not proceed and retrofit later |
| 25 | T4b finds a class (b) or (c) ordering assumption in a code path producing an artifact Phase 11 reuses frozen | any | Hard stop — Stage B unauthorised until resolved |
| 26 | Any query exempted from `query_watchdog_seconds` other than the T5b pass, **or** T5b exceeding `runtime_ceiling_seconds` | any | Hard stop |
| 27 | Any report sentence using a T−1 or T−3 spread as a proxy for detection-time cost, or reporting a spread or cost in one unit alone | any | Hard stop before posting — D19 |
| 28 | Any Stage B task begun before T4b has cleared | any | Hard stop |
| 29 | The standing qualifier in A2-0 absent from REPORT.md §T7 or from the caption of charts 05, 06, 07 | any | Hard stop before posting |

---

## A2-12 — Chart Contract addition

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 09 | `charts/09_spread_vs_staleness.html` | Is the measured effective spread cost, or is it staleness? | x = `bbo_age_at_trade_p50` (log, ms), y = effective spread (twin axes bp and cents); point per event × minute cell; facet by participation quintile; RTH only; LOESS-free — distribution and binned medians with n per bin | n cells per facet, n per bin | Effective spread rising monotonically with quote age across every quintile — the headline is substantially a staleness artifact and T7's numerator does not mean what it says |

Charts 05, 06 and 07 gain the A2-0 standing qualifier in their captions.

---

## A2-13 — Amended output files

| File | Change |
|---|---|
| `results/phase_11/artifacts/t4b_ordering_audit.json` | **New** — enumeration, classification, artifact/line names |
| `results/phase_11/artifacts/t6_effective_spread.{parquet,json}` | Adds T6e participant robustness table, T6f staleness-confound table |
| `results/phase_11/artifacts/t7_cost_vs_capture.{parquet,json}` | Adds T7g with/without-dirty-events comparison |
| DuckDB `event_quote_metrics_v1` | Adds 5 staleness columns + `unusable_time_share` |
| `results/phase_11/charts/09_spread_vs_staleness.html` | **New** |
| `docs/Universe-Decisions.md` | D16, D17, D18, D19 appended verbatim |
| `docs/Open-Items-Register.md` | Depth/queue unmeasured; `indicators` available-and-uninterpretable with full census; class (a) ordering hits from T4b; canonical-view materialization (carried from A1) |

---

## Execution order on adoption

1. **T0c** — re-audit, 29 rows × 4 checks, against the amended config. Hard stop on any failure.
2. **T4b** — ordering audit. Hard stop on any class (b) or (c) hit.
3. **T2e-i** — implied-price decomposition appended to the Stage A report. No new computation.
4. **T5a** — dev-tier timing and extrapolation. Hard stop above the ceiling; do not reduce cohort or grid.
5. **T5b** — the single budgeted pass.
6. **T6 → T7 → T8 → T9.**

No further Cooper gate until T9, unless a row fires.
