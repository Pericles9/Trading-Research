# Unconditional universe scan — scope and feasibility

**Type:** scoping pass. **No scan was executed. No measurement was produced. Nothing was fitted.**
**Date:** 2026-08-31 · **Spec:** `prompts/universe_scan_scoping.md` · **Branch:** `scope/universe-scan`
**Authorised by:** Cooper, handoff resolutions §5, 2026-08-31.

**Audience is a fresh session with no context.** Everything needed to act on this is below or in the four
JSON artifacts beside it.

**What this pass is for.** `docs/Open-Items-Register.md` records the archive-vs-live universe mismatch as
a near-front blocker, upgraded by D5 consequence (c) on 2026-08-03 and unscheduled ever since. It
multiplies every conditional result in the programme: under D5's gate-then-trade design the detector's
fire-rate in the wild is a direct PnL term, not a caveat. **This pass does not fix that.** It establishes
what fixing it would take, so the work can be scheduled against a real cost.

**No route is proposed. No rate is estimated. The disposition is Cooper's.**

---

## 1. The two population definitions

### 1.1 The intended live screen — pinned, with citations

Artifact: `screen_definition.json`.

| element | value | citation |
|---|---|---|
| gap threshold | `0.30` (decimal) | `scanner-epg-momentum/live/strategy.json:25` |
| intraday evaluation frequency | **20 s poll** | `scanner-epg-momentum/live/strategy.json:26` |
| admission rule | `todaysChangePerc >= gap_threshold × 100` **AND** common stock on XNYS/XNAS (`TickerClassifier`) | `scanner-epg-momentum/live/CLAUDE.md:143`, `:268` |
| unit conversion | Polygon `todaysChangePerc` is in **percent** units (30.0 = 30%); the config stores 0.30 decimal | `scanner-epg-momentum/live/build_log.md:262` |
| sessions included | **all hours**; no quartile gate, all Q1–Q4 admitted | `scanner-epg-momentum/live/strategy.json:29`, `live/CLAUDE.md:143` |
| universe pre-filter | common stock on XNYS/XNAS only | `scanner-epg-momentum/live/CLAUDE.md:143`, `:268` |
| programme-level statement | "real-time ≥30% from previous close, pre- and post-market inclusive" | `docs/Universe-Decisions.md:321`; `docs/Open-Items-Register.md:34`; `docs/Mom-DB-Strategy-Research-Program.md:345` |

The screen is more precisely specified than the register's one-line summary suggests: it has a **20-second
poll interval** and an explicit **instrument pre-filter**, neither of which appears in the open item.

### 1.2 The archive selection function — read, not assumed

Artifact: `archive_selection.json`. Risk row 2 recorded this as *"open, script unread."* It is now read.

**The headline is that the q05 power-law filter does not select on momentum at all.**
`data/collection_scripts/filter_events_power_law.py` (86 lines) selects on **volume, conditional on
momentum**:

1. Reads two upstream scan files and concatenates them (lines 8–9).
2. Requires `momentum_pct > 0` and `event_volume > 0` (lines 27–29).
3. Fits a **quantile regression at q = 0.05** of `log10(event_volume)` on `log10(momentum_pct)`, trained
   on events at or below the 99.5th percentile of momentum (lines 35–36, 42–43).
4. **Keeps events whose actual log-volume exceeds that fitted line** (line 62).

Momentum enters only as the regressor. **The ≥X% momentum threshold is upstream, in the scan files, and
the producer of those files is not in this repo** — it was searched for across the checkout and not
found. So risk row 2 is only **half-closed** by this pass: the volume filter is now fully specified, the
momentum screen behind it is still unread.

---

## 2. Why the two cannot be reconciled from disk — three properties, one of them new

| # | property | consequence |
|---|---|---|
| **P1** | **The threshold is population-dependent.** It is a quantile line *fitted over the pooled 2020–2025 population* (lines 42–43). | Membership is **not a property of an event**. It depends on every other event in the file. |
| **P2** | It selects on `event_volume` — a **D4-quarantined spine column**. D4 Amendment A9.2 extends that quarantine to pre-ingestion scan inputs, prospectively. | The universe's own selection function ran on a column now barred from computation. Recorded, not actionable — A9.2 is prospective and the universe is frozen. |
| **P3** | `event_volume` is a **completed-session aggregate**. | Unknowable at any intraday decision time. |

**P1 is stronger than what the open item currently says.** The register words the problem as *"the
archive's selection variable is only knowable after the session ends."* That understates it. The
threshold does not exist until the **entire multi-year population is assembled**, so no real-time screen
can reproduce archive membership *even in principle* — not because the information arrives late, but
because the criterion is defined over a population that does not exist at decision time.

**On the extended-hours question T2 asks specifically:** the script never touches session boundaries. It
consumes `momentum_pct` as given and uses it only as a regressor, so it neither introduces nor corrects
the RTH scoping. Per CLAUDE.md's D4 note, `momentum_pct` "inherits the vendor's RTH-scoped,
adjusted-basis high forever." **The RTH scoping therefore enters upstream, in the scan files** — and
confirming exactly where requires the producer that is not in this repo. **Open.**

---

## 3. `daily/` breadth audit — breadth only

Artifact: `daily_breadth_audit.json`. Risk row 5 recorded this as an open audit item.

| quantity | value |
|---|---|
| files on disk | 1,848 (one per ticker, `{TICKER}_daily.parquet`) |
| files carrying rows | 1,836 — **12 are empty** |
| distinct tickers | 1,836 |
| total rows | 144,026 |
| **date range** | **2024-12-02 → 2025-04-01** |
| **distinct sessions** | **82** |
| rows per ticker | min 3, median 82, max 82 |
| tickers spanning the full range | 1,695 (92.3%) |
| busiest session | 2025-03-31, 1,787 tickers |

**Breadth is wide; depth is not.** 1,836 tickers is a real cross-section and 92% of them span the whole
window — but the window is **82 sessions in a single four-month block.**

**The span any route would have to cover** (stated as a coverage fact about the on-disk resource, per
T3's instruction to say what a comparison would *require* — no population comparison is drawn):

| quantity | value |
|---|---|
| archive in-scope events | 20,951 |
| archive distinct tickers | 2,930 |
| archive date range | 2020-01-03 → 2025-10-31 |
| archive distinct sessions | 1,465 |
| **`daily/` sessions as a share of archive sessions** | **5.6%** |
| archive events inside the `daily/` window | 2,165 (**10.3%**) |
| archive tickers inside the `daily/` window | 904 |

**What a comparison would require, and this audit did not establish:**

1. Daily bars for the **whole market**, not only the 1,836 tickers already on disk. **Whether those
   1,836 are a market-wide set or themselves a selected one is not established by this audit** — and
   establishing it is part of the work, not a preliminary to it.
2. Coverage of 2020-01-03 → 2025-10-31, against the 82 sessions present.
3. A stated rule for what "previous close" means on each session — ambiguity **A1** below, unresolved.

**Not done here:** no control set was constructed, no population was compared, and no false-positive
rate — bounded or otherwise — was estimated.

---

## 4. Ambiguities found, recorded rather than resolved

Per escalation row 6, an ambiguity resolved by inference is a hard stop. Two are genuinely open; two
were resolved by reading a source and are recorded for completeness.

| id | severity | ambiguity | status |
|---|---|---|---|
| **A1** | **HIGH** | **The reference price of the screen is not established by any committed source in this checkout.** The docs say "≥30% from previous close"; the implementation tests Polygon's `todaysChangePerc`. No committed file states what that field is referenced to, nor whether its numerator uses the last extended-hours trade or the last RTH trade. | **OPEN.** Settling it needs an external field definition; **D14 bars the fetch.** |
| **A2** | MEDIUM | Which strategy defines the intended live universe. `live/strategy.json:6` sets `active_strategy = "scanner_vwap"`; `docs/Research-Library-Map.md:293` describes the repo as "EPG rising edge + gap ≥ 30%". | **OPEN.** |
| A3 | LOW | Whether a TOD midday exclusion (11:30–13:30 ET) filters admission. | **Resolved by citation, not inference:** it does **not**. `scanner-epg-momentum/live/CLAUDE.md:286-291` lists it under *"Phase H — Do Not Implement Without Explicit Approval."* |
| A4 | LOW | Two strategy configs exist. Which carries admission? | **Resolved by citation:** `backtest/config/strategy.json` contains no `gap_threshold`, `poll_interval_s` or `active_strategy` key. `live/strategy.json` is the only source. |

**A1 is the one that matters**, and it bites exactly where this pass exists to look. The screen is
specified as pre/post inclusive. If `todaysChangePerc`'s numerator is RTH-scoped, then **the live screen
does not fire on the extended-hours moves it is meant to fire on**, and the live-vs-archive gap is
different *in kind* from the one currently recorded — both sides would be RTH-scoped, and the mismatch
would be about population assembly rather than about session coverage.

---

## 5. Routes to an unconditional population, and what each would cost

Artifact: `routes_and_costs.json`. **No route is proposed, recommended, or characterised as best,
cheapest or obvious** (escalation row 9). Costs are order-of-magnitude from the programme's own measured
throughput: the `daily/` glob scan measured here at **11.6 s** for 1,836 files / 144,026 rows, and the
scale-space causal run at **~6.6 s per event-window** for 78 events over ±1,260 s of tape each.

| id | route | on disk? | what it establishes | what it does **not** | offline-blocked |
|---|---|---|---|---|---|
| **R1** | Universe-wide daily bar source | **No** — `daily/` is 5.6% of sessions | Daily-resolution admission counts across the archive span | **Anything intraday or extended-hours.** A daily bar cannot express a 20 s poll admitting at all hours — it answers a different question | **Yes** |
| **R2** | Intraday scan replay | **No** — `filtered/` holds only tickers that already passed; Phase 8 A10.2d confirmed rejected candidates are absent | The **only** route that reproduces the screen as specified, and so the only one that yields a fire-rate rather than a proxy | Nothing further — but it is conditional on **A1** being settled first | **Yes** |
| **R3** | Flanking-day pseudo-controls | **Yes**, subject to `flag_window_calendar_bug` per damaged offset | A **within-ticker** contrast on adjacent sessions | **The cross-ticker rate**, which is what risk rows 3/4/9 are about. Every ticker here is already selected | **No** |
| **R4** | A bound, not a rate, from the 82-session window | **Partially** — bars yes, market-wide claim no | For 5.6% of archive sessions, at daily resolution, a bound on the ratio | A rate; anything intraday; the other 94.4% of sessions. And if the 1,836 are a selected set, the bound is not a bound | **No** for the arithmetic, **yes** for the audit it depends on |

**Failure modes, one per route, because each is the specific way that route gets over-read:**

- **R1** — substituting a daily close-to-close move for the live screen's intraday, pre/post-inclusive
  trigger, and reporting the result as the live rate.
- **R2** — running the replay on the tickers that are on disk. That reproduces the archive, not the
  market, and would return a fire rate near 1 **by construction**.
- **R3** — reporting a within-ticker rate as if it were the live screen's fire rate.
- **R4** — treating a four-month, daily-resolution bound as the programme-wide false-positive rate.
  This is the cheapest route and therefore the one most likely to be over-read.

**Cost summary:**

| id | passes | wall time | storage | blocked by D14 |
|---|---|---|---|---|
| R1 | 1 external pass, order 10⁷ rows | minutes — the scan is not the cost | 1–3 GB | yes |
| R2 | 1 whole-market intraday pass; order 10¹¹–10¹² rows for the full span | 3–4 orders of magnitude more ticker-sessions than the 6.6 s/event-window measured | 10–100 TB full span; ~1 TB per quarter | yes |
| R3 | 0 new external passes | tens of hours single-threaded over 20,951 events; less on a cohort | negligible | no |
| R4 | 1 pass over `daily/`, measured at 11.6 s | minutes; the market-wide-set audit is the real work | negligible | partially |

**Sequencing facts** — ordering, not a proposal:

- **A1 gates R2.** A replay reproduces a screen, and the screen is not fully defined without its
  reference price.
- **The market-wide-set audit gates R4**, and R4 does not perform it.
- **R1 and R2 are both offline-blocked.** Neither can start under D14 without an external acquisition,
  which is a procurement decision rather than a research one.
- **R3 is the only route that can start today** — stated as a fact about blockers, and noting that R3
  also answers a different question from the one being scoped.

**The bound described by R4 was not computed.** Escalation row 4 bars this pass from producing it.

---

## 6. Questions this pass could not answer, and why

1. **What `todaysChangePerc` is referenced to**, and whether its numerator includes extended-hours
   trades (A1). Needs an external field definition; **D14 bars the fetch.**
2. **Where the ≥X% momentum threshold is actually applied.** The producer of
   `full_2020_2024_momentum_scan_20251122_000515.parquet` and `momentum_scan_2025.parquet` is not in this
   checkout, so the archive's own momentum screen remains unread. **Risk row 2 is half-closed, not
   closed.**
3. **Whether `data/daily`'s 1,836 tickers are a market-wide set or a selected one.** T3 measured breadth;
   it did not establish provenance, and R4's validity turns on it.
4. **Which strategy defines the intended live universe** for research purposes (A2).
5. **The size of the rejected-candidate population.** Phase 8 A10.2d established it is absent from
   `data/filtered/`, and **no route above recovers it from disk.**

---

## 7. A defect found while reading, outside this pass's remit to fix

**`data/collection_scripts/filter_events_power_law.py` carries live `D:\` hardcodes** — line 7 sets
`base_dir` to a path on D:, and lines 78 and 83 **write** a parquet and a CSV there.

CLAUDE.md's hard data rule is *"NEVER write to D:. Confirmed failing hardware, migrated off 2026-07-12,"*
and it enumerates the files carrying live `D:\` hardcodes with the instruction that they never be
executed until a remediation phase clears them. **This file is not on that list.** The list is therefore
incomplete, and the file omitted from it is one that **writes**.

Reported, not fixed — modifying it is outside this pass's write allowlist. It was not executed.

---

## 8. Escalation check — all 10 rows

| # | Condition | Observed | Pass |
|---|---|---|---|
| 1 | Working tree dirty at T1 | clean | ✅ |
| 2 | Any pass over `filtered_trades` / `filtered_quotes` | 0 | ✅ |
| 3 | Any write to a table, or any new materialization | 0 | ✅ |
| 4 | Any estimate of the live false-positive rate, bounded or hedged | none; R4's bound described, **not computed** | ✅ |
| 5 | A screen or filter element stated without a file-and-line citation | none — 7 elements, all cited | ✅ |
| 6 | An ambiguity resolved by inference rather than recorded | none; A1/A2 left open, A3/A4 resolved **by citation** | ✅ |
| 7 | A control set constructed, or populations compared | none — breadth only | ✅ |
| 8 | Any external fetch attempted | none | ✅ |
| 9 | A route recommended, or characterised as best / cheapest / obvious | none | ✅ |
| 10 | Write outside `results/scope_universe_scan/`, `prompts/`, `docs/Open-Items-Register.md` | none | ✅ |

---

## 9. Prose authored by the agent, quoted in full

Per the `redirect_d5` precedent, so Cooper reviews the words rather than inferring them from a diff.
Everything in §§1–8 above is agent-authored except the quoted citations. The three judgements that go
beyond transcription, stated plainly so they can be rejected individually:

> **(a)** "P1 is stronger than what the open item currently says." The register words the archive's
> problem as a timing one — the selection variable is knowable only after the session ends. Reading the
> script, the threshold is a quantile line fitted over the pooled multi-year population, so membership
> depends on events that had not happened yet. I have described this as a difference in kind rather than
> degree. **That is my characterisation, not the script's.**

> **(b)** "Risk row 2 is half-closed, not closed." The row asked for the q05 filter's exact mechanics.
> Those are now fully specified. I have judged that the row should nonetheless stay open, because the
> filter turned out not to contain the momentum screen the row was implicitly about. **Whether that
> counts as closing the row as written is Cooper's call.**

> **(c)** "R4 is the cheapest route and therefore the one most likely to be over-read." Cost is measured;
> the inference that cheapness invites over-reading is mine. It is stated as a failure mode rather than
> as a reason to avoid the route, and row 9 bars me from the latter in any case.

No other sentence above carries a judgement the artifacts do not.

---

## 10. Output files

| File | Description | Status |
|---|---|---|
| `prompts/universe_scan_scoping.md` | The prompt, committed on `master` before this branch was cut | ✅ |
| `results/scope_universe_scan/screen_definition.json` | T1 — 7 elements with citations, 4 ambiguities | ✅ |
| `results/scope_universe_scan/archive_selection.json` | T2 — the q05 filter's actual mechanics, 8 steps, 3 properties | ✅ |
| `results/scope_universe_scan/daily_breadth_audit.json` | T3 — tickers, date range, completeness | ✅ |
| `results/scope_universe_scan/routes_and_costs.json` | T4 + T5 — 4 routes, costs, sequencing facts | ✅ |
| `results/scope_universe_scan/REPORT.md` | This file | ✅ |
| `docs/Open-Items-Register.md` | Risk rows 2, 3, 4, 5, 9 annotated | ✅ |

**No `digest.json`** — §11 does not apply to a scoping pass. **No charts** — T3 yielded no chart that
carried information beyond the table in §3.

---

## 11. Approval gate

This pass gates nothing and unblocks nothing on its own. It exists so the scan can be **scheduled against
a real cost**. Cooper reads this and decides whether, when, and by which route.
