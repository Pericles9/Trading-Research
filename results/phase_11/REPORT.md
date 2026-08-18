# Phase 11 — Instrument Validation and the Cost Stack on the Detection Cell

**Config hash:** `98723f27b96c` · **Passes spent:** 1 · **Rows enumerated:** 34

Governing spec: Amendment 1 over v1 (Cooper 2026-08-15), as further amended by Amendment 2 (Cooper 2026-08-16, T4 gate). A 25-row v2 rewrite was circulated 2026-08-15, interrupted, and discarded; one v2 element was imported by explicit decision - T2a's hard/degraded state split.

---

## Stage A — is the instrument usable?

**T1 — identity.** CONFIRMED consolidated best-quote, not per-venue.
RTH median 13 distinct bid venues, share of rows with `bid_exchange != ask_exchange`
median 0.884 (min 0.618), 0 single-venue events, 0 null-exchange rows, n = 50 events.
`sip_timestamp` null-or-zero = 0 on all three denominators. Resolution: min 49 ns,
median 80 ns. Epoch and timezone confirmed against XNYS — quotes/minute step from
2,808 to 12,835 at the open minute and fall from 6,949 to 878 at the close, 0 rows on
non-session dates. Chart 01.

`indicators` is populated on 6,274,517 of 7,061,655 source rows (88.85%), not null —
contradicting the two-row sample the prompt carried in. No condition-code dictionary
exists on disk, so the codes stay opaque (row 20, not a stop). The source parquet is
stored reverse-chronological: `sip_timestamp` decreases across 99.97% of consecutive
file rows at the median event, on all 50 events.

**T2 — state census.** Row 5: `state_hard_unusable` clock-time share on the T=0 RTH
segment, median across 50 events = 1.31e-08
(1.3e-08, i.e. zero to 6 dp), threshold 0.25 — DOES NOT FIRE. The three-way
partition sums to 1.0 to 0.0 deviation. Charts 02, 03.

**T2e / T2e-i — quoted spread and implied price.** RTH median time-weighted quoted
spread 165.0 -> 127.6 -> 83.9 bp across T-3 / T-1 / T=0 (-49.1%); the same cells in
cents 3.64 -> 3.43 -> 3.79 (+4.1%). Median per-event implied price $2.505 -> $2.820 ->
$3.796 (+51.5%). n = 50 at every point. The basis-point figure falls; the cents figure
does not; the implied price rises. Chart 03.

**T3 — alignment.** The curve matches **pre-registered reading-rule row 1**: maximum at
δ = 0 or immediately before it, decaying smoothly either side — the two tables are
aligned and the contemporaneous quote is the reference midpoint. Stated on both
timestamp bases, both sessions, both segments. Chart 04.

---

## Stage B — the cost stack

**Filter waterfall.** Detection universe 15,369 →
`quotes_ingested` 15,252 → excluded
117 (0.7613%),
row 10 threshold 20% — DOES NOT FIRE. Coverage read from the Phase 4/5 materializations (D15).

**T7 — cost against capture.**

> Effective spread measures the cost of the average print, not the cost of a specific order. Depth, queue position and fill probability are not measured in this phase.

Named cell (`fixed_horizon`, RTH, latency 5 min, hold 30 min), n = 10,544:

| cost multiple | median ratio |
|---|---|
| 1× (the sole row-11 trigger) | **0.1608** |
| 1.5× (equal prominence, A2-5) | **0.2412** |
| 2× | 0.3216 |

Share of events where round-trip cost exceeds realized capture outright:
**12.64%**. Kill threshold
0.5 — row 11 **DOES NOT FIRE**.

**Pre-registered reading rule (T7e-i):** Realized capture <= 0 for more than half the cell - the denominator is non-positive for the majority; the ratio is undefined on that population and is reported as a share, not a ratio

Of the 10,544 rows in the named cell, 3,363 have a
defined ratio; realized capture is non-positive on
52.86% of the cell, and the median ratio above is
computed only on the complement. Median round-trip cost in the named cell is
70.98 bp and 2.512 cents
(D19: both units, never one alone). Charts 06, 07.

**T6 — effective spread at the detection anchor.** RTH, at the T4-selected offset
(δ = 0, sip basis, D16), size-weighted per bar:

| latency | n | bp | cents | share of detection price |
|---|---|---|---|---|
| 0 (impossible upper bound) | 10,408 | 97.07 | 3.060 | 0.956% |
| 1 | 10,292 | 90.29 | 2.803 | 0.904% |
| 5 | 10,087 | 75.80 | 2.385 | 0.757% |
| 15 | 9,669 | 65.69 | 2.096 | 0.656% |
| 30 | 9,384 | 60.50 | 1.958 | 0.605% |

Latency 0 is a physical impossibility and is the upper bound, not an operating point
(Phase 8 / D7). Premarket and post are in the artifact and on chart 05; the decision
rests on the RTH cell alone (D18). Chart 05.

**T8 — impact and classification.** Overall unclassifiable share
5.9818%,
reported per cell and never dropped. Distributions only — no regression and no fitted
impact exponent. Charts 08, 09.

**T4c — tie dependence (escalation row 30, FIRED).**
On 643 of 317,225 bars that feed det_price_lat* or the Phase 9 entry/exit prices (0.203%), the extremum sip_timestamp is shared by two or more prints that differ in price, so first_price/last_price is arbitrary among the tied set. The bounded ambiguity on those bars is p50 14.332 bp / 1.0 cents, p95 123.047 bp / 18.9 cents, max 676.409 bp / 162.0 cents. det_minute itself is tie-immune - it is MIN(minute_index) FILTER over MAX(price) - so the detection MINUTE is unaffected; only the PRICE attached to it on those bars is ambiguous.
Cooper accepted option (a) on 2026-08-18: proceed carrying this as a stated caveat, with
no frozen artifact rebuilt (row 32 respected).

---

## Escalation check

| row | quantity | observed | threshold | verdict |
|---|---|---|---|---|
| 1 | working tree dirty at T0a | dirty, then clean | any | fired once, resolved |
| 2 | T0c audit failure | fired on the pass-budget contradiction, resolved by option (ii) | any | resolved |
| 3 | consolidated vs per-venue | established | any | does not fire |
| 4a | sip null-or-zero | 0.0 | > 1% | does not fire |
| 5 | hard_unusable RTH median | 0.000000 | > 0.25 | does not fire |
| 6 | alignment curve flat | peak−min 0.1902 | any | does not fire |
| 7 | premarket vs RTH peak rung | 7 rungs | any | fired, not a stop |
| 10 | quotes_ingested FALSE | 0.7613% | > 20% | does not fire |
| 11 | kill threshold, named cell 1× | 0.1608 | ≥ 0.50 | does not fire |
| 20 | condition-code dictionary | none on disk | any | fired, not a stop |
| 21 | era null-pattern gap | 6.21 pp | > 20 pp | does not fire |
| 24 | cache required columns | none missing | any | does not fire |
| 25 | ordering class (b)/(c) | 0 of 15 | any | does not fire |
| 26 | pass exceeds ceiling | projected 8.10 h vs 6.00 h | > ceiling | **fired**, one-off exception accepted |
| 30 | tie price error p95 | **123.047 bp** | > 25 bp | **fired**, option (a) accepted |
| 31 | aggregate-function class (b)/(c) | 0 of 5 | any | does not fire |

---

## Deviations on record

- Tick rule is the SIMPLE TICK TEST (immediately preceding trade price), not Lee & Ready's walk-back to the last differing price. Conservative: it can only raise the unclassifiable share, which is reported per cell and never dropped.
- Charts 05 and 09 ship as stacked bp/cents panels, not twin axes (A3-1, Phase 9 chart 06 precedent).
- T6e participant-basis robustness is DEV-TIER only - a full-tier recompute would need a second pass, which escalation row 12 forbids.
- T5a's dev-tier extrapolation (2,271 s) did not predict the full-tier pass. Dev v4 is a small dedicated table and never exercised the query plan the full tier takes.

---

## Verification

Every number above is reproducible from the committed artifacts in
`results/phase_11/artifacts/` at the config hash printed at the top.
