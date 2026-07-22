---
tags:
  - type/proposal
  - domain/strategy
  - project/scanner-epg-momentum
  - status/proposal
created: 2026-07-07
updated: 2026-07-08
version: 2
depends_on: Noise_Problem.md
decision_owner: Cooper
changelog: "v2 — folded in event taxonomy (EVQ-0 headline), causal-clock per-class drift curves, pooled-statistics ban, exit-reopen rule, and the tape-classifier endgame architecture"
---

# EVQ — Event-Quality Selection (Strategy Proposal, v2)

**Thesis:** In this event class, edge lives at the **selection level** (which events to trade), not the timing level. Every timing attempt across three research programs failed or reshaped risk without adding expectancy. The pooled entry drift is ~+0.9% gross — but the pool is a heterogeneous blend of archetypes, and +0.9% pooled is fully consistent with one event class at +4% and mongrels at zero. **The program is to find that class.** EVQ trades the same scanner universe with a deliberately dumb execution layer and puts the entire research budget into selection: a **toll gate**, an **event taxonomy** built from fundamental ground truth, and — as the endgame — a **tape-only classifier** that detects event class live from price/volume/quote alone.

Expected magnitude if it works: +1–3% net per trade on the selected class, ~50–80 trades/yr, capacity-capped by construction. Losing stretches expected. Account-growing money, not a business — the moat and the ceiling are the same illiquidity.

---

## 1. Endgame architecture (three stages, one goal)

The standing goal — *differentiate true catalysts from false jumps purely from technical data* — survives as the endgame. It requires ground truth first:

1. **Label offline (EVQ-0):** the fundamental/filing record labels every historical event with its class, once. Fundamentals are the *labeling apparatus*, not (primarily) a live input.
2. **Learn the shadow (EVQ-1/2):** dilution and catalysts cast microstructure shadows — an armed ATM is relentless offer-side replenishment; a genuine catalyst is sustained imbalance with spread compression. A technical classifier trains against the fundamental labels. Constraint from the EXIT_D autopsy: **side-agnostic quote features only** (depth replenishment, quoted-size dynamics, spread behavior) — trade-sign features are known to degrade live.
3. **Trade the tape (EVQ-4+):** live system runs technical-only; fundamentals remain as offline validation and drift monitoring.

## 2. Event taxonomy (EVQ-0 headline deliverable)

Provisional classes (Cooper finalizes at EVQ-0 review); each label derived from PIT fundamental data:

| Class | Defining evidence |
|---|---|
| True catalyst | FDA/clinical, contract, M&A, earnings shock — verifiable wire item, no active dilution machinery |
| Dilution pump | Active ATM / fresh S-3 / recent 424B5; offering prices into the move |
| Fake volume spike / artifact | No catalyst on record; anomalous prints; likely paint or sympathy noise |
| Meme / large-cap sympathy day | Mid/large-cap on sector-wide event (the AAL-2020-06-05 type) — not the archetype |
| Multi-day runner continuation | Day ≥2 of an active event with prior structural confirmation |

Every SEB entry and every catalog event gets exactly one label plus a confidence flag. Unlabelable events are their own class, not silently pooled.

## 3. Analysis standards (binding on all EVQ phases)

1. **Pooled-statistics ban** (Noise_Problem.md §6.5): once labels exist, all reported statistics are per-class with per-class n. Pooled numbers only as explicitly labeled blends.
2. **Two clocks, both causal:** wall-clock/event-time for anything an exit rule will consume (the only clock available at trade time); **sigma-time or tick-time** for structural analysis, so a ten-minute $0.80 arc and an all-day $22 grind aren't averaged across tempos. Event-duration-normalized clocks are hindsight and are banned from anything live-facing.
3. **No raw-MFE / threshold-touch metrics** (Noise_Problem.md §6.1–6.2). Targets: realized net PnL of the frozen exit per event (primary); vol-normalized excess magnitude (diagnostic).
4. **Per-entry-vol noise benchmark accompanies every excursion statistic.** Any per-class claim of structure ships with its zero-edge prediction next to it.

## 4. Component disposition

| Component | Status | Reason |
|---|---|---|
| Scanner + event catalog machinery | **Keep** | Universe definition; extend through 2026 (EVQ-3) |
| ParticipationGate λ_V | **Repurposed** | Dead as timing; legitimate as liquidity/tradability qualifier at hit |
| Trail exit B0+R1+R3 (vwap-σ) | **Keep, frozen** | Best shape-preserver found; one g-grid extension below 0.5 on tune-era data only, then frozen — subject to the reopen rule (§6) |
| Conservative fill model | **Build (EVQ-1)** | Stop-through fills at next print; halt-straddling stops fill at reopen; entry marketable at hit |
| Percent-of-equity risk framework | **Keep (live plan)** | No hardcoded dollars |
| EXIT_MFE | **Deferred** | Shape-only upside per F4; revisit with live data or on §6 trigger |
| EPG timing entry, Hawkes side-signals, EXIT_D, SF-as-timing, backtest LULD tuning | **Dead** | Convergent failures; EXIT_D noise live (side-classification transfer) |
| Fixed TP/SL brackets | **Dead (pooled)** | F5; conditionally reopenable per §6 only |
| Runner rate / raw MFE metrics; pooled stats post-labeling | **Banned** | F1/F6; §3.1 |

## 5. Layer 1 — Toll gate

Gate on the toll directly; price is the belt.

**Primary spec (frozen at EVQ-2):** NBBO spread at hit ≤ ~40 bps · price ≥ $5 · RTH · λ_V ≥ floor (set in EVQ-1 from tune-era data). One pre-declared fallback (relaxed spread ceiling). Nothing else.

Supporting data (post-hoc, hypothesis-grade): ≥$5 cell = 407 entries (~81/yr), mean hold-to-EOD +2.23% vs 0.00% below $5; drift monotone across price buckets; estimated round-trip toll ~0.3–0.6% at ≥$10 vs ~1.5–4% sub-$2. Year-noisy (2023 = −1.65% inside the cell). Note the ≥$5 cell overlaps the meme/sympathy class — the taxonomy will disentangle whether the price gradient is toll, class composition, or both.

## 6. Per-class drift curves and the exit-reopen rule (pre-registered)

EVQ-1 produces **μ(t | class)** — full-resolution mean cumulative-return curves in event time from paths.parquet, per taxonomy class, each with its noise benchmark, on both causal clocks.

**Reopen rule, written in advance:** if a class exhibits a drift ridge with a **genuine sign flip** (mean drift turns negative at a stable point in event time or sigma-time, robust across tune-era years), then exit design **reopens for that class only** — scheduled exits and TP geometries become admissible there, developed on tune-era data and confirmed only in the EVQ-3 one-shot. If no class shows a flip (pooled evidence to date: fast +0.34% pop, no negative mean phase, +0.71% accruing after minute 5 via the right tail), the trail stays frozen and the TP stays dead. This converts the "catalyst events pop then fade" hypothesis into a falsifiable, one-shot-tested claim instead of a standing debate.

## 7. Layer 2 — Fundamental data (labeling apparatus + exclusion filter)

Exclusion-first: features that identify a good short identify a forbidden long. All PIT-keyed.

| Feature | Source | PIT key / trap |
|---|---|---|
| Shares outstanding, mkt cap | Polygon ticker details (`date` param) | Validate vs. filings for delisted microcaps |
| Short interest, days-to-cover | Polygon Short Interest API (FINRA bi-monthly) | Key on **dissemination date**, never settlement |
| Daily short volume ratio | Polygon Short Volume API | Off-exchange only; sentiment proxy |
| Dilution flags: S-3 shelf, ATM, recent 424B5, warrants | Polygon SEC filings endpoints + EDGAR full-text/submissions (free) | Knowability = EDGAR **acceptance datetime** |
| True float | Derived from 10-K/10-Q cover pages (FMP cross-check) | Float changes intraday during offerings |
| Borrow availability / fee | IBKR shortstock file (live); iBorrowDesk history | Retail-broker view — the relevant one |
| Catalyst class | Polygon news (historical); classify wire text | Wire timestamp = knowability; Benzinga pack only if free tier shows signal |
| Structural history | Own catalog: serial-gapper count, prior fades, stratum, heat | Already built |
| Halt history | Nasdaq/NYSE halt logs (free) | LULD websocket covers forward only |

## 8. Data budget and validation protocol

**Everything 2020–2024 is development data** (all partitions consumed — see Noise_Problem.md §7). Clean assets: (a) **2025-01 → mid-2026 catalog extension** — never scanned, swept, or eyeballed; (b) forward paper.

1. Label history (EVQ-0). Develop on 2020–2024 with temporal CV; look at anything, admit it's in-sample.
2. **Freeze one primary spec + one fallback** at EVQ-2: toll gate + class whitelist/exclusions + trail params (+ any §6-triggered class-specific exit) + sizing rule. Written to file before step 3.
3. Build the 2025–26 extension; compute labels for it using only PIT data; run the frozen spec **once**, net of costs, conservative fills, reported per-class.
4. Pass → paper (EVQ-4). Fail → program ends.

## 9. Phase plan

| Phase | Content | Gate |
|---|---|---|
| **EVQ-0** | **Event taxonomy**: PIT fundamental store, every historical event labeled; catalog audit (incl. entry_price outliers) | Cooper reviews taxonomy + label quality — **approval gate** |
| **EVQ-1** | Fill/cost model; per-class μ(t) curves on both clocks w/ noise benchmarks; λ_V floor; trail g-extension (tune-era only); per-class association study; first-cut tape features vs labels (side-agnostic) | Escalate if cost model kills the ≥$5 cell outright, or if §6 reopen rule triggers |
| **EVQ-2** | Spec freeze: primary + fallback, thresholds Cooper-set, written to file | **Approval gate** |
| **EVQ-3** | Catalog extension 2025-01 → present; single confirmatory run, per-class reporting | **Approval gate**; results as-is, no smoothing |
| **EVQ-4** | Paper trading under percent-equity risk; live tape-classifier development against frozen labels; log NBBO at entry/exit, borrow state, all gate inputs | Standard live gates |

**Escalation stops:** any post-freeze modification; any second look at 2025–26 data; any raw-MFE/runner-rate metric or post-label pooled statistic in an agent report.

## 10. Decision criteria (open — Cooper sets numbers at EVQ-2)

Proposed defaults: **Pass** = net PF ≥ 1.3 on 2025–26 for the frozen spec with bootstrap 5% CI floor > 1.0, net EV ≥ 1.5× modeled toll, ≥ ~60 qualifying events/yr. **Kill** = neither spec clears → the long side of this event class has no reachable edge at this cost structure; program ends (convergent-failure rule: no third spec). Frequency floor ~1.5 events/week.

## 11. What this proposal is not

Not a claim that the edge exists. It is the cheapest well-formed experiment that can settle whether it does — and, via the taxonomy, *where* it lives if it does: one labeled dataset, one frozen spec, one untouched sample, one shot. Honest prior: the toll gate clears in some corner, the unconditional game stays dead, and the per-class split is the coin-flip worth paying to observe.
