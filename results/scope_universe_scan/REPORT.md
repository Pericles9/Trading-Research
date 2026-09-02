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

---

## 12. Follow-up, 2026-08-31 — `daily/` provenance settled, and R4 does not survive it

Cooper's read §5 proposed the deciding test: *"the ticker count per session, distributed. A market-wide
daily pull has a stable count near the listed-universe size and moves only with listings and delistings.
A selected pull varies with whatever selected it."* Run, plus one follow-up. Artifact:
`daily_provenance.json`.

**Per-session count — stable, and drifting with the calendar rather than with activity.**

| quantity | value |
|---|---|
| sessions | 82 |
| min / median / max | 1,706 / 1,758 / 1,787 |
| mean ± sd | 1,756.4 ± 18.1 |
| **coefficient of variation** | **1.03%** |
| range ÷ median | 4.6% |
| **corr(session index, count)** | **+0.891** |

The count is flat to ~1% and what movement there is is **monotone in time**, not in market activity — the
signature of a roster growing with net listings. **So it is not activity-selected.**

**But that test cannot separate a market-wide pull from any other stable roster, including one derived
from the archive.** Ticker overlap settles it, and it changes the answer:

| quantity | value |
|---|---|
| `daily/` tickers | 1,836 |
| **absent from the archive entirely** | **995 — 54.2%** |
| examples absent | `A`, `AAPL`, `AAON`, `AAT`, plus ETFs (`AADR`, `AAPD`), warrants (`AAM.WS`), units (`AAM.U`) |
| **archive tickers in the same window that `daily/` does NOT hold** | **688 of 904 — 76.1%** |

**Verdict.** Not activity-selected. **Not** derived from the archive — 54% of its names never appear
there, and large caps like `AAPL` would never enter a micro-cap momentum archive. But **not market-wide
either**: 1,836 is well below the US listed common-stock universe and the roster mixes ETFs, warrants and
units. It is a stable, independent, broad pull that is **not the market**.

**The deciding number is the last row.** `daily/` holds only **216 of the 904** archive tickers present in
its own window. A resource meant to bound how often a screen fires on names the archive does *not* contain
cannot do that while omitting **three quarters of the names the archive does contain** over the same
dates.

**Correction to §5's route table:** **R4 was conditioned on `daily/` being establishable as market-wide.
It is not, so R4 as written does not produce a bound.** What it could still produce is a statement about a
stable 1,836-name roster over four months — a different and much weaker object. The routes table should be
read with that correction; nothing else in §5 changes.

---

## 13. Follow-up, 2026-09-01 — the selection variable's session scope

Cooper's read §4. Artifacts: `basis_test.json`, `basis_test_stage2.json`, `basis_test.parquet`.
Code: `research/scope_universe_scan/basis_test.py`, `basis_test_stage2.py`.

### 13.1 What could not be tested, stated first

The read asks for **the screen's field** — Polygon's `todaysChangePerc` — to be compared against tick data
computed two ways. **That field is not stored anywhere in this checkout.** It cannot be tested here at
all, and claiming otherwise would be the fabrication class named on 2026-08-31.

What *is* testable is the **archive half** of the same question, and it turns out to be worth doing on its
own account. CLAUDE.md carries a standing qualifier on every premarket/extended-hours finding in the
programme:

> `momentum_pct` "inherits the vendor's RTH-scoped, adjusted-basis high forever, so every
> premarket/extended-hours finding is conditional on that selection boundary"

**Asserted 2026-07-24, never verified against tick data.** Below it is.

### 13.2 Stage 1 — how much an RTH-scoped boundary costs (within-session, A12 does not apply)

Seeded sample of 400 in-scope events with `trades_ingested`; **301** returned tick highs in at least one
segment. Highs are tick-derived from `filtered/` prints. No previous close is needed, so no cross-session
ratio is formed.

**Where the T=0 extended-session high actually sits:**

| segment | n | share |
|---|---|---|
| RTH | 205 | **68.1%** |
| post | 48 | 15.9% |
| premarket | 48 | 15.9% |
| **outside RTH** | **96** | **31.9%** |

**By how much an RTH-only high understates the session high** (`session_high / rth_high`, n = 301):

| | |
|---|---|
| share > 1 | **31.9%** |
| share > 1.05 | 21.6% |
| median | 1.000 |
| q90 / q95 / q99 | 1.127 / 1.242 / **1.593** |
| max | **2.385** |

**Roughly a third of these events reach their session high outside regular hours**, and the tail is large
— at q99 the extended high is 59% above the RTH high, and one event reaches 2.39×. Notably the miss is
**not** a premarket story: post-session highs are exactly as common (15.9% each).

### 13.3 Stage 2 — which high does `momentum_pct` track? (cross-session, **A12 applies**)

`momentum_pct = (H − P)/P`, so `H = P·(1 + momentum_pct/100)`. `P` is the tick-derived T−1 close taken
from `price_earlier` on the `tm1_t0` pair of `results/phase_9/artifacts/t1_cross_session_flags.parquet`
— a committed artifact, reused rather than rebuilt, **which also carries the A12 flag this comparison
needs**. The implied `H` is compared in log distance against the tick RTH high and the tick
extended-session high.

**A12 is in force here**: `P` is T−1 and `H` is T=0, so every ratio spans a session boundary and
denominators count. Untrimmed is primary; the flagged set is reported as its own row and never dropped.

95 of 301 events are **discriminating** (extended high exceeds RTH high by >0.1%); on the other 206 the
two candidates coincide and the test is uninformative by construction.

| set | n | closer to **RTH** high | closer to extended high | median implied/RTH | median implied/extended |
|---|---|---|---|---|---|
| **untrimmed (primary)** | **95** | **64.2%** | 35.8% | **1.0138** | 0.9517 |
| A12-flagged removed | 83 | 60.2% | 39.8% | 1.0152 | 0.9734 |
| A12-flagged only | 12 | **91.7%** | 8.3% | 1.0025 | 0.8564 |

**Reading: the evidence supports the standing claim, and does not clinch it.** The implied high sits
within **1.4%** of the RTH high against **4.8%** from the extended high — RTH wins by roughly 3.5× in log
distance, and the majority verdict is RTH in every cut. So `momentum_pct` behaving as an RTH-scoped
quantity is the better-supported reading, and the qualifier CLAUDE.md attaches to every extended-hours
finding stands.

**But 35.8% land closer to the extended high, and that dispersion is not explained here.** Three
candidates, none eliminated: our tick T−1 close may not be the vendor's previous close (RTH close vs
extended close); our tick max may not be the vendor's official high; and **D4's adjustment-basis
inconsistency bites this ratio directly** — `implied_H` and the tick highs can sit on different bases for
the same ticker, which is exactly the AMC defect. The first two are settleable; the third is D4, and it is
not settleable from disk.

**A12 earned its keep visibly.** The flagged subset behaves differently from the rest — 91.7% RTH against
60.2% — which is precisely the divergence A12 exists to stop being averaged away silently.

### 13.4 What this changes

- The standing qualifier on extended-hours findings is **supported by measurement** rather than asserted,
  for the first time since 2026-07-24.
- Its cost is now a number: an RTH-scoped selection variable does not see the session high on **31.9%** of
  events, and understates it by more than 5% on **21.6%**.
- It is **not** a premarket-only boundary. Post-session highs are equally common (15.9% each), and the
  register's framing of the gap as a premarket issue is narrower than the data.
- It does **not** settle what the live screen's field does. That remains open item A1, and D14 bars the
  fetch that would close it.

---

## 14. Follow-up, 2026-08-31 — the selection audit under A13, and a hard stop

D4 Amendment **A13** granted. Artifact: `selection_audit.json`. Code:
`research/scope_universe_scan/selection_audit.py`. **A13(a) honoured: no per-event artifact and no spine
numeric column under any name — JSON aggregates only, no parquet.**

### 14.1 HARD STOP — the vintage-churn test cannot be run, and it is the data, not the rule

`momentum_events` carries **`min_volume_threshold`** — the column
`filter_events_power_law.py` writes onto its **own output** (line 65).

| check | result |
|---|---|
| rows | 23,268 |
| null threshold | **0** |
| **above the line** | **23,268** |
| **below the line** | **0** |
| any other table holding a rejected event | **none** |

**The spine IS the filter's survivors.** A `q = 0.05` quantile line cannot be refit from the ~95% of the
population that lies above it — the 5th percentile of the survivors is not the 5th percentile of the
original — and **all three arms** of the design need the rejected mass. It is not on disk.

This is Phase 8 A10.2d's finding one level up: rejected candidates are absent from `data/filtered/`, and
they are absent from the **spine** too.

### 14.2 The selection function, recovered exactly

    log10(min_volume_threshold) = 2.126137 + 0.584556 · log10(momentum_pct)

**R² = 1.0000000000, max |residual| = 3.6e−15 decades.** Machine precision, so the threshold column is
provably the fitted line evaluated per event, and the function that was actually applied is now pinned.
A13(a) names fitted coefficients as a permitted output.

### 14.3 Residual spread — reported first, per Cooper's ordering

`margin = log10(event_volume) − log10(min_volume_threshold)`, **censored at zero** (survivors only), so
the observed spread understates the true one.

| quantity | decades |
|---|---|
| q01 / q05 / q10 | 0.222 / 0.814 / 1.276 |
| **median** | **2.967** |
| q90 / q99 | 4.360 / 5.073 |
| observed sd (censored) | 1.145 |
| **uncensored σ estimate** | **1.737** |
| per-quantile σ spread (max/min) | 2.03 — so the residual is **not** normal |

The censoring point is known exactly — the line *is* the 5th percentile by construction — so σ is
estimated by matching each observed quantile against a normal truncated at its own 5th percentile. The
2.03× disagreement across quantiles is the departure from normality, reported rather than smoothed.

**σ̂ = 1.74 decades sits above the top row of the read's table** (which ran to 1.5). At the AMC anchor
that is `0.283 / 1.737 = 0.163` standard deviations — below the most conservative row.

### 14.4 Basis perturbation — measured, and it is small

A per-ticker volume factor is an **additive shift in `log10(event_volume)`**, moving a point vertically
against the line. For a shift δ, the survivors a −δ shift pushes below the line are those with
`margin < δ`.

| δ (decades) | factor | pushed below | n |
|---|---|---|---|
| 0.05 | 1.12× | 0.27% | 62 |
| 0.15 | 1.41× | 0.68% | 158 |
| **0.283** | **1.92× — AMC anchor** | **1.44%** | **335** |
| 0.50 | 3.16× | 2.70% | 629 |
| 1.00 | 10.0× | 6.77% | 1,575 |
| 1.50 | 31.6× | 12.90% | 3,002 |

**One-sided, and therefore a lower bound.** It counts survivors a −δ shift would exclude. Events below
the line that a +δ shift would **promote** are invisible, because they are not on disk. Total basis churn
is larger by an unmeasurable amount.

### 14.5 Why both numbers come out small — the geometry

| | |
|---|---|
| threshold at momentum 30% / 42.86% / 100% | 976 / **1,203** / 1,974 shares |
| median survivor `event_volume` | **1,202,800** shares |
| **median volume ÷ its own threshold** | **926×** |
| **survivors within 2× of their threshold** | **1.51%** |

**The q05 line is an extraordinarily permissive constraint on the surviving population.** The median
survivor trades nearly a thousand times its own threshold, and fewer than one in sixty sits within a
factor of two of exclusion. That is why a 1.92× basis error moves only 1.44%, and it is the same geometry
that would make a modest vintage-refit coefficient shift move very few **survivors**.

**The read's conditional resolves the other way.** It expected basis churn "in double figures" if the
residual spread came back below ~0.6 decades. It came back at **1.74**, and basis churn at the AMC anchor
is **1.44%**. So the two effects are **not** the same order, and had the lookahead arm been runnable its
number would not have been swamped.

### 14.6 What is settled and what is not

- **Settled:** the selection function, exactly. Basis sensitivity of *surviving* membership — small,
  1.44% at the AMC anchor, lower bound. The residual spread, 1.74 decades uncensored.
- **Not settled, and not settleable from disk:** the lookahead. Its magnitude is unmeasurable because the
  population it would be measured against does not exist here.
- **The asymmetry that remains.** Everything above concerns events we can see, all of which are
  survivors. The uncertainty lives entirely on the side that is missing: events *below* the line, which a
  different vintage or a basis shift could have promoted. For those, nothing in this checkout constrains
  anything.
- **Consequence for the correction the read proposed.** A point-in-time refit was to be the byproduct
  that repaired the universe. **It cannot be produced.** A13(b) — the sentence a corrected population
  would have had to carry — has nothing to attach to, and the register should record the lookahead as
  *unmeasurable from disk* rather than as *pending measurement*.

