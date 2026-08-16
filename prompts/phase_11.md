# Phase 11 — Instrument Validation and the Cost Stack on the Detection Cell

**Date:** 2026-08-15
**Baseline:** `phase-10b-closed` — Phase 10b closed as a recorded negative result; no burst timescale established (D11, D12, D13). Phase 9 retracement and axis-separation results stand. Phase 8 detection anchor (`det_anchor`, 1.30× tick, n = 15,369) stands and is reused frozen (D7).
**Objective:** Establish whether `filtered_quotes` supports effective-spread measurement in this universe at all, and — only if it does — measure the round-trip cost of a detection-anchored long entry against the capture available above the detection price.
**Primary success metric:** A round-trip-cost-to-capture ratio with its full distribution, per latency × participation quintile × detection segment × era, at 1× / 1.5× / 2× cost — **or** a recorded finding that BBO-derived cost is not measurable on this archive, with the evidence that establishes it.

---

## Context & Constraints

**Why this phase exists.** Only ≈33.6% of the excursion sits above the detection price, 60.99% of events are already below the detection price by `t0_close`, ~20% have runway ≈ 0, and the median name trades near $3. The cost stack is what decides whether anything is left. It requires no burst timescale (D10, D13) and is measurable today.

**The burst/quiet half of this row is dead.** D11 and D13 removed the burst-scale anchor. Every bucket in this phase is participation quintile, detection segment, latency, or era. **Do not construct a burst/quiet split, do not re-anchor to a burst scale, and do not reopen intensity estimation, envelope fitting, thresholding, two-state segmentation, or Hawkes calibration** — all closed by D6, D8, D9, D11.

**The instrument has never been validated.** `docs/Mom-DB-Strategy-Research-Program.md` §9 states that the audit chain covered quote quality. It did not. The Operating Plan's original row 5 (*Quote quality* — crossed/locked rates, stale-quote runs, quote-to-trade ratios, spread distributions event day vs. T−3) was re-scoped during execution; the phase that ran as Phase 5 was *Window Flags & Canonical Spine Finalization*. Phase 4 was a quotes-side **coverage** census — do the files exist, do sessions join — not a quality characterization. No phase has computed a spread as a finding. **Stage A of this phase closes that gap and gates Stage B.**

**What is established about `filtered_quotes`, from the repo and from a source-file sample supplied by Cooper 2026-08-15 — and what is not:**

- DB columns are `ask_exchange, ask_price, ask_size, bid_exchange, bid_price, bid_size, participant_timestamp, sequence_number, sip_timestamp, tape` (`config/phase_1c.json` → `db_table_columns_quotes`).
- **`conditions` and `indicators` are present in the source parquet and absent from the DB table.** `src/data/ingest.py` drops LIST-typed columns at ingest (`PARQUET_LIST_INTERNAL_NAMES`), a deliberate choice made when `results/quotes_fix/column_usage_scope.csv` recorded them as unused downstream. They are the fields a withdrawn-quote filter needs. In the sampled rows `conditions` is populated (`[1, 81]`) and **`indicators` is null**. Whether `indicators` is null throughout is a measurement, not an assumption — T1c settles it. **Nothing is re-ingested in this phase.**
- **The sample shows a row with `bid_exchange = 12` and `ask_exchange = 11`.** A single-venue feed cannot produce that. The working reading is therefore **consolidated best-quote records, not per-venue quotes**, and T1a's job is to confirm and quantify that reading across the dev cohort rather than to discover it. If T1a contradicts it, escalation row 3 fires.
- **Timestamps are nanoseconds since the Unix epoch, UTC**, stored as strings in the source. In the sampled rows `participant_timestamp` precedes `sip_timestamp` by roughly 0.5–0.6 ms. Both clocks are available on both tables, they are not the same clock, and **T3 sweeps the alignment on both** rather than assuming one.
- **Storage order is not established.** In the two sampled rows both `sip_timestamp` and `sequence_number` decrease. Two rows are not evidence that the file is unsorted — they may not be adjacent — but the phase does not rely on the question either way: **every query orders explicitly, and escalation row 19 fires on any computation that depends on storage order.** T1b measures it.

**Prior art carried in — the environment is offline (D14), so cite from here rather than fetching:**

- **Holden & Jacobsen (2014)**, *Liquidity Measurement Problems in Fast, Competitive Markets: Expensive and Cheap Solutions*, Journal of Finance 69:1747–1785. Distortion in spread, trade-location and price-impact measures comes from withdrawn quotes, coarse timestamps, and cancelled quotes; the recommended treatment is to delete economically nonsensical quote states and adjust for withdrawn quotes. Our timestamps are nanosecond, so that leg does not apply. The nonsensical-state census in T2 and the exclusion rule proposed at the T4 gate are this paper's recommendation applied here.
- **Lee & Ready (1991)** quote rule with tick-rule fallback, for aggressor classification in T7. **The 5-second lag rule is not applied.** On nanosecond data the contemporaneous or near-contemporaneous quote signs best, and signing accuracy falls sharply across a lag band matching the trades-to-quotes file synchronization offset. That is the basis for T3.
- **Ellis, Michaely & O'Hara (2000)** and **Odders-White (2000)** on classification-rule accuracy and the unclassifiable share. The unclassifiable share is reported as its own row, never dropped.
- **Bartlett & McCrary (2017)** on SIP-versus-direct-feed staleness. This archive is SIP-sourced. Staleness relative to direct feeds is a **permanent, unfixable limitation of the data**, stated in the report, not something this phase corrects.

**Standing constraints that bind here** — see `CLAUDE.md`: spine join through `momentum_events_canonical` where `in_scope = TRUE`; D4 tick-derived only, no spine numeric on any computation path; any quote-derived statistic filters on `quotes_ingested = TRUE` and reports the n excluded; long-only (D5) — do not specify, implement, or measure any short-side or fade variant, and do not implement SSR or borrow logic; two-tier execution; DuckDB SQL, never materialize `filtered_trades` (4.95B rows) or `filtered_quotes` (3.8B rows) into a dataframe.

**Pass budget.** Stage A: zero full-table passes — dev v4 only (`filtered_trades_dev_v4` / `filtered_quotes_dev_v4`, frozen Phase 5a, never rebuilt; **50 primary events on both sides, plus 6 trades-side and 3 quotes-side sidecar events** — Amendment 1 A1-7 correction; the sidecar is never pooled and Stage A runs on the 50 primary only). Stage B: **exactly one** budgeted full pass over `filtered_quotes` joined to `filtered_trades`, materializing the reusable cache in T5. A second full pass is escalation row 12.

**Description only.** No recommendations. No characterisation of any result as good, promising, weak, or disappointing. No exclusion rule is *adopted* by the agent — T2 and T3 produce the evidence, the rule is set at the T4 gate by Cooper.

---

## Tasks

**Do not begin T1 until T0 is committed and posted.**

### T0 — State, satisfiability, branch

- [ ] **T0a — Verify state, assert nothing.** Report from `git` and the filesystem rather than from this prompt: current branch; tip of `main`; whether `phase-10b-closed` exists; `status` of `results/phase_10b/digest.json`; whether the working tree is clean; presence and row counts of `filtered_trades_dev_v4`, `filtered_quotes_dev_v4`; presence of `results/phase_8/artifacts/a102_detection_anchors.parquet` and `results/phase_9/artifacts/t1_cross_session_flags.parquet`. **Hard stop if the working tree is dirty.** Read-only; commit nothing in this task.

- [ ] **T0b — Satisfiability audit of the escalation table.** *(New standing requirement, from the Phase 10b close-out — two of three amendments there introduced an unreachable required outcome.)* Before any computation, check every escalation row below and report a table: row, the task that measures it, whether the quantity it names is actually produced by that task, whether the threshold is reachable given the ranges and grids configured, and whether it contradicts any other row. **Hard stop on any row that fails any of the four checks.** Post the table. Do not proceed to fix a defective row — post and wait.
  - [ ] T0b1 — Repeat this audit against the amended set before executing **any** amendment to this prompt.

- [ ] **T0c** — Cut `phase/11` from `main`. Commit `prompts/phase_11.md` and `config/phase_11.json` before any other work.

---

### STAGE A — Is the instrument usable? *(dev v4 only, zero full passes)*

- [ ] **T1 — What `filtered_quotes` actually contains**
  Establish from the data, not from assumption. The phase cannot compute a midpoint until this is answered.
  - [ ] T1a — **Confirm the consolidated best-quote reading.** Per event: count of distinct `bid_exchange`, distinct `ask_exchange`, and the **share of rows where `bid_exchange ≠ ask_exchange`**. Report the distribution across the 50 primary events, not a pooled share, and split by segment — a two-sided share that collapses to ~0 in premarket while holding in RTH is a different fact about the feed than a uniform one. Also report the per-event exchange-frequency table on each side; a consolidated best-quote feed should show many venues, weighted toward the primary listing venue.
  - [ ] T1b — **Timestamp semantics.** For `sip_timestamp` and `participant_timestamp` separately: null share, coverage, and **resolution measured per event from the smallest non-zero gap** — the same method Phase 10 v1 used on trades (median 80.5 ns, min 49 ns, max 8,388 ns). Do not assume a resolution.
    - [ ] T1b-i — Confirm the epoch and timezone: that both fields are nanoseconds since the Unix epoch in UTC, by checking that per-event session boundaries land where the XNYS calendar says they should (pinned `pandas_market_calendars==5.4.0` / `exchange_calendars==4.13.2`). State the check, not the assumption.
    - [ ] T1b-ii — **Monotonicity in storage order versus sorted order.** Report, per event: share of consecutive rows in file order where `sip_timestamp` decreases; same for `participant_timestamp`; same for `sequence_number`; and whether the three orderings agree with each other. This determines nothing about the method — every query sorts explicitly regardless — but an unsorted archive is a fact every future phase needs.
    - [ ] T1b-iii — Distribution of `sip_timestamp − participant_timestamp` per event, by segment. This is the reporting latency between the two clocks and it sets expectations for T3.
    - [ ] T1b-iv — State which timestamp every downstream task uses, and why, in one sentence each.
  - [ ] T1c — **The dropped columns, and whether they are usable.** Read the source `quotes.parquet` for the 50 primary dev events **read-only**. No re-ingest, no write to the data root, no change to `src/`.
    - [ ] T1c-i — `indicators`: null share per event, and the value-frequency table where non-null. Cooper's sample shows null on both rows; whether that holds archive-wide decides whether the National Best Bid and Offer indicator route exists at all.
    - [ ] T1c-ii — `conditions`: value-frequency table of the individual codes and of the observed code **combinations** (the sample carries `[1, 81]`). Report as opaque integers. Do not guess at meanings.
    - [ ] T1c-iii — **Search for a condition-code dictionary already on disk** — `data/metadata/`, `data/collection_scripts/`, `data/Schema.md`, `docs/`, and the two read-only sibling repos. The environment is offline (D14), so a vendor code table cannot be fetched. Report what was found and where. **If no dictionary is on disk, that is not a stop:** the codes stay opaque, the withdrawn-quote filter is not buildable in this phase, and the item is recorded in `docs/Open-Items-Register.md` with the exact codes observed so a future phase starts from the census rather than repeating it.
    - [ ] T1c-iv — Report whether the null/populated pattern of either column differs between the event day and the T−1 / T−3 baseline sessions, and across eras. A field that is populated in 2024 and null in 2020 is a collection-era artifact and must not be treated as a market fact.
  - [ ] T1d — Chart 01. Commit.

- [ ] **T2 — Economically nonsensical state census** *(Holden & Jacobsen)*
  Per event, T=0, split premarket / RTH / post, and against the T−1 and T−3 baseline sessions. **No cleaning is applied — this is a census.**
  - [ ] T2a — Share of rows **and** share of clock time in each state: crossed (`bid > ask`), locked (`bid = ask`), null or zero `bid_price`/`ask_price`, zero `bid_size` or `ask_size`, `bid_price ≤ 0`.
  - [ ] T2b — **Run-length distribution** of each state in clock time. A 2% row share concentrated in one 40-minute run and a 2% share scattered across the session are different facts.
  - [ ] T2c — **Stale top-of-book runs:** time the best bid and offer sit unchanged while trades print through them. Distribution of run length, and the share of T=0 trades that occur inside a stale run.
  - [ ] T2d — Quote-to-trade ratio and inter-quote interval distribution, by segment, event day vs. baseline.
  - [ ] T2e — **Quoted spread distribution, event day vs. T−1 and T−3**, in both basis points and cents, by segment. This is the §4.1 compression claim's first look; state what the chart shows and nothing more.
  - [ ] T2f — Charts 02, 03. Commit.

- [ ] **T3 — Trade–quote alignment sweep** *(the control gate — this phase's known-answer test)*
  For each T=0 trade in the dev primary cohort, ASOF-join to the quote prevailing at `trade_time + δ` for every δ in `config.alignment_offsets` (spanning −1 s to +1 s, log-spaced through µs and ms, including exactly 0).
  - [ ] T3a — Per δ, report: share of trades priced **at or inside** the quoted spread; share exactly at bid; share exactly at ask; share outside the spread on each side; share with no prevailing quote. Report per event, then the distribution across events — not a pooled number.
  - [ ] T3a-i — **Run the whole sweep twice: once on the `sip_timestamp` basis (both tables), once on `participant_timestamp` (both tables).** T1b-iii established these clocks differ by roughly half a millisecond in the sampled rows, which is inside the sweep's resolution. Report both curves on the same axes. If one basis peaks materially closer to δ = 0 than the other, that is the basis Stage B uses, and the choice is Cooper's at the T4 gate, not the agent's.
  - [ ] T3b — **Pre-registered reading rule.** The agent states which row the curve matches and nothing further.

    | Observation | Meaning |
    |---|---|
    | Maximum at δ = 0 or immediately before it, decaying smoothly either side | The two tables are aligned; the contemporaneous quote is the reference midpoint |
    | Maximum at a materially non-zero δ, consistent in sign across events | The tables carry a **synchronization offset**; the reference midpoint is the quote at that offset, and the offset is itself a finding about the archive |
    | Curve flat across the whole sweep | The quotes carry no information about trade prices in this universe; **effective spread is not measurable and Stage B does not run** |
    | Curve differs in shape between premarket and RTH | Segment-specific offsets; report both, do not pool |
  - [ ] T3c — Repeat the sweep on the T−3 baseline session for the same events. An offset present on the event day but absent on the baseline is a load-related artifact, not a clock artifact.
  - [ ] T3d — Chart 04. Commit.

- [ ] **T4 — STAGE A GATE — hard stop, post, wait**
  Commit. Post charts 01–04, the T1–T3 tables, and the escalation check. **Do not begin T5.**
  Cooper decides, from the charts: (a) whether BBO-derived cost is measurable at all in this universe; (b) which quote states are excluded and which are carried; (c) which alignment offset is the reference; (d) which population Stage B runs on. **The agent proposes no exclusion rule and no offset.** If (a) is negative, the phase closes here as a recorded finding and that finding is first-order for the whole program.

---

### STAGE B — The cost stack *(only after the T4 gate; one budgeted full pass)*

- [ ] **T5 — Materialize the quote-metrics cache**
  - [ ] T5a — **Dev-tier timing and extrapolation first.** Run the full Stage B pipeline on dev v4, report wall time, and extrapolate to the detection universe using per-event print counts as the scaling variable. If the extrapolation exceeds `config.runtime_ceiling_seconds`, **hard stop and post** — do not silently reduce the cohort, the grid, or the ladder.
  - [ ] T5b — One pass, event-partitioned (never one monolithic join), materializing `event_quote_metrics_v1`: per event × offset × session-minute × segment — time-weighted quoted spread (bp and cents), time-weighted midpoint, `n_quotes`, nonsensical-state time shares, signed volume, `Σ size`, `Σ |p − m| · size`, `Σ size` among classified trades, and the unclassifiable count. Everything downstream reads this cache; phases 12–19 reuse it rather than rescanning.
  - [ ] T5c — Integrity: row count, distinct events, duplicate `(event, offset, minute)` keys = 0, `minute_index` in range, per-offset coverage table. Commit.

- [ ] **T6 — Effective spread at the detection anchor**
  `det_anchor` is **reused frozen** from `results/phase_8/artifacts/a102_detection_anchors.parquet` (D7). It is not re-derived. Detection universe n = 15,369, less the `quotes_ingested = FALSE` population, reported as its own row.
  - [ ] T6a — Effective spread `= 2 · |p − m| / m` at the T4-selected offset, measured at `det + latency` for latency ∈ {0, 1, 5, 15, 30} minutes. **Latency 0 is a physical impossibility and is labelled as the upper bound on every chart and in every table** (Phase 8 / D7 convention).
  - [ ] T6b — Reported in **basis points, in cents, and as a share of the detection price**. The cents figure is not optional — on a $3 median name it is the number that decides the phase.
  - [ ] T6c — Bucketed by participation quintile (`pq_rth_open`, reused frozen from `results/phase_8/artifacts/t3_participation.parquet` — **not** `a102_detection_anchors.parquet`, Amendment 1 A1-7 correction; do not re-derive), detection segment, and era. Cells with n < 100 hatched and carrying no claim.
  - [ ] T6d — Full distribution per cell, never the median alone. Chart 05. Commit.

- [ ] **T7 — Round-trip cost against available capture** *(the headline)*
  - [ ] T7a — Per event, per latency: entry cost = half effective spread paid crossing at `det + latency`; exit cost = half effective spread paid crossing at exit. Exits are the Phase 9 fixed-horizon grid holds (5, 15, 30, 60, 120 min) and `t0_close`. Round-trip cost in log terms.
  - [ ] T7b — Two capture denominators, both reported, never blended:
        **(i) perfect-foresight ceiling** `log(H / p_det)`, `H = day_high_ext`, frozen from 6b/Phase 8 — the unreachable upper bound;
        **(ii) realized capture** at the matching fixed horizon from the Phase 9 T4 grid — the honest one.
  - [ ] T7c — **The ratio is computed per event, then distributed. Never a ratio of medians.** Report the distribution of `round_trip_cost / capture` per cell, at **1×, 1.5×, 2× cost** per the research program §7.3.
  - [ ] T7d — Share of events where round-trip cost **exceeds** realized capture outright, per cell, with n.
  - [ ] T7e — Carry the Phase 9 flags: `flag_cross_session_extreme` (D4/A12 — the `H − p_det` denominator spans no session boundary, but `H` does; report with and without), `flag_possible_row_cap`, `flag_has_dup_prints`. Own rows, never pooled.
  - [ ] T7f — **Stale-price zero atom.** Phase 9 found 34 of 450 grid cells whose median is fixed by an exact-zero point mass at short holds and high latency in premarket. Flag every cell in that state here and ring it on the chart; no claim rests on one. Charts 06, 07. Commit.

- [ ] **T8 — Impact by participation** *(the §4.1 compression claim)*
  - [ ] T8a — Aggressor classification: quote rule at the T4-selected offset, tick-rule fallback, **unclassifiable share reported as its own row and never dropped**. Cite Lee & Ready (1991); state that the 5-second rule is not applied and why.
  - [ ] T8b — Effective spread vs. participation quintile, and Δmid per unit signed volume over fixed clock windows from `config.impact_windows`. **Distributions, not fitted coefficients.** No regression, no fitted impact exponent — that is not this phase.
  - [ ] T8c — Split by detection segment. **No burst/quiet split** (D11, D13). Chart 08. Commit.

- [ ] **T9 — Charts, digest, report.** `digest.json` per §11 and `REPORT.md` per §10, plus the cross-phase copy at `results/reports/phase_11_report.md` (standing rule, `CLAUDE.md`). Every claim cites its chart. Commit; working tree clean.

---

## Escalation Criteria

Stop, commit, post observed values and charts, await instruction. **Table order is priority order.** Do not adjust a parameter to make a criterion pass.

Thresholds marked `[Cooper]` are set before execution and are not the agent's to propose or to fill.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 0 | Cooper's review of the charts against the tape contradicts the numeric result | judgment | Hard stop — overrides every row below in either direction |
| 1 | Working tree dirty at T0a | any | Hard stop |
| 2 | T0b satisfiability audit fails on any row | any | Hard stop — post, do not repair |
| 3 | T1 cannot establish whether `filtered_quotes` is consolidated or per-venue | any | Hard stop — no midpoint is defined until this is answered |
| 4 | T1b: `sip_timestamp` null or non-monotonic share, per event | `[Cooper]` | Hard stop |
| 5 | T2: combined nonsensical-state **time** share on the T=0 RTH segment, per event | `[Cooper]` | Hard stop — BBO features unusable on that population |
| 6 | T3: alignment curve matches the flat row of the reading rule | any | Hard stop — Stage B does not run |
| 7 | T3: peak offset differs between premarket and RTH by more than one sweep rung | any | Not a stop — report both, do not pool |
| 8 | Any effective spread computed before the T4 gate is passed | any | Hard stop |
| 9 | T5a runtime extrapolation exceeds `config.runtime_ceiling_seconds` | as configured | Hard stop — do not reduce cohort or grid |
| 10 | T6: `quotes_ingested = FALSE` share of the detection universe | `[Cooper]` | Hard stop — the measurable population is not the detection universe |
| 11 | T7: median `round_trip_cost / realized_capture` on the **RTH detection cell at latency 5 min, hold 30 min**, at 1× cost | `[Cooper — the kill threshold, set before T5 runs]` | Hard stop — post and wait |
| 12 | More than one full pass over `filtered_quotes` | > 1 | Hard stop |
| 13 | Any spine numeric column on a computation path (D4) | any | Hard stop |
| 14 | Any write to the data root, DuckDB main tables, `momentum_events_canonical`, or `src/` | any | Hard stop |
| 15 | Any burst/quiet split, intensity estimation, envelope fit, thresholding, two-state segmentation, or Hawkes calibration | any | Hard stop — closed by D6/D8/D9/D11 |
| 16 | Any short-side, fade, SSR, or borrow logic specified or measured | any | Hard stop — D5 |
| 17 | Any exclusion rule or alignment offset adopted by the agent rather than set at the T4 gate | any | Hard stop |
| 18 | Any REPORT.md statement characterising a result beyond which pre-registered reading-rule row it matches | any | Hard stop before posting |
| 19 | Any computation whose result depends on parquet storage order rather than an explicit `ORDER BY` or ASOF key | any | Hard stop — regardless of what T1b-ii observed |
| 20 | T1c-iii finds no condition-code dictionary on disk | any | **Not a stop** — codes stay opaque, no withdrawn-quote filter is built, census recorded to `docs/Open-Items-Register.md` |
| 21 | T1c-iv: `indicators` or `conditions` null pattern differs materially across eras | `[Cooper]` | **Not a stop** — report as a collection-era artifact; no era-conditional claim rests on either field |
| 22 | Any interpretation of a specific `conditions` code value without a dictionary found in T1c-iii | any | Hard stop — do not infer code meanings from the values themselves |

---

## Chart Contract

Standard chart rules apply (Agent Prompt Standard §9): Plotly, standalone HTML, one chart per file, n per bucket always, distribution not centre, outliers shown never clipped, log scale where multiplicative, caption carries sample + filters + config hash. Kaleido-verified before commit.

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_quote_table_identity.html` | Is `filtered_quotes` consolidated best-quote data, and are the dropped columns usable? | Panel A — per event: x = share of rows with `bid_exchange ≠ ask_exchange`, y = count of distinct exchanges seen; strip + marginal ECDF; premarket/RTH facets. Panel B — `indicators` null share per event, by era. Panel C — `conditions` code-combination frequency, codes as opaque integers | n events per panel; n rows per code combination | Panel A: all events at share ≈ 0 with one exchange each — per-venue data, and every midpoint in this phase needs a best-quote reconstruction first. Panel B: null everywhere — the indicator route is closed. Panel C: one code combination on ~100% of rows — the field carries no discriminating information |
| 02 | `charts/02_nonsensical_state_census.html` | How much of the session is in an unusable quote state, and is it clustered? | Facet per state (crossed/locked/null/zero-size); x = time share, y = max run length (log); point per event; colour = segment | n events per facet | Time shares near zero across all states and all segments — the tape is cleaner than expected and the exclusion question is moot |
| 03 | `charts/03_spread_event_vs_baseline.html` | Does the spread compress on the event day, and in cents or only in basis points? | Two panels (bp, cents); x = day offset (−3, −1, 0), y = time-weighted quoted spread (log); violin + strip; RTH/premarket facets | Per-violin n | Violins fully overlapping across offsets — no event-day spread effect, and §4.1's compression claim is unsupported at session grain |
| 04 | `charts/04_alignment_sweep.html` | Are the trades and quotes tables time-aligned, and on which clock? | x = lag δ (symlog, µs→s), y = share of trades at-or-inside the quoted spread; one faint line per event + pooled median; **two colours, one per timestamp basis (`sip_timestamp`, `participant_timestamp`)**; vertical rule at δ = 0; premarket/RTH facets | n events, n trades per facet and basis | Flat across the sweep on both bases (quotes carry no information — Stage B does not run), or a peak far from zero (the tables are offset), or the two bases peaking in opposite directions with neither near zero (neither clock is a usable reference) |
| 05 | `charts/05_effective_spread_at_detection.html` | What does it cost to cross at detection? | Facet rows = latency, cols = era; x = participation quintile, y = effective spread; twin axes bp and cents; violin + strip; cells n<100 hatched; latency 0 marked as impossible upper bound | Per-cell n above each violin | Uniform across quintiles and latencies — participation carries no cost information |
| 06 | `charts/06_cost_vs_capture.html` | Does the round trip cost more than the trade captures? | x = `round_trip_cost / realized_capture` (log), ECDF, one line per latency; facet by detection segment; vertical rule at 1.0; 1×/1.5×/2× cost as three line styles | n per line | ECDFs sitting entirely right of 1.0 at every latency — cost exceeds capture everywhere and the thesis is dead on the RTH cell |
| 07 | `charts/07_cost_capture_grid.html` | Where, if anywhere, does the ratio clear? | Heatmap: rows = hold, cols = latency; facet by segment × era; colour = median ratio; cells n<100 hatched; zero-atom cells ringed per Phase 9 | Per-cell n printed | Uniform colour — no cell separates, and no latency or hold choice changes the answer |
| 08 | `charts/08_impact_by_participation.html` | Does impact per unit signed volume rise or fall with participation? | x = participation quintile, y = Δmid per unit signed volume; violin + strip; facet by impact window and detection segment; unclassifiable share annotated per cell | Per-cell n and unclassifiable share | Violins centred on zero and fully overlapping — signed volume carries no impact information at this grain |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_11.md`, `config/phase_11.json` | This prompt and its config, committed before any run | [ ] |
| `results/phase_11/artifacts/t0b_satisfiability_audit.json` | Escalation-row audit, all 23 rows, four checks each | [ ] |
| `results/phase_11/artifacts/t1_quote_table_identity.json` | Consolidated-vs-per-venue evidence, timestamp semantics, source-file column presence | [ ] |
| `results/phase_11/artifacts/t2_state_census.{parquet,json}` | Nonsensical-state shares, run lengths, stale runs, quote-to-trade, spread by offset | [ ] |
| `results/phase_11/artifacts/t3_alignment_sweep.{parquet,json}` | Per-event per-δ inside-spread shares, event day and T−3 | [ ] |
| DuckDB table `event_quote_metrics_v1` | Per event × offset × minute × segment quote and cost aggregates (Stage B cache) | [ ] |
| `results/phase_11/artifacts/t5_cache_integrity.json` | Row counts, duplicate-key check, per-offset coverage, wall time | [ ] |
| `results/phase_11/artifacts/t6_effective_spread.{parquet,json}` | Effective spread by latency × quintile × segment × era, bp and cents | [ ] |
| `results/phase_11/artifacts/t7_cost_vs_capture.{parquet,json}` | Per-event ratios, both denominators, three cost multiples, flag rows | [ ] |
| `results/phase_11/artifacts/t8_impact.{parquet,json}` | Impact distributions, classification shares | [ ] |
| `results/phase_11/charts/01–08*.html` (+ `.png`) | Per Chart Contract, kaleido-verified | [ ] |
| `results/phase_11/{digest.json, REPORT.md}` | Per §10/§11 | [ ] |
| `results/reports/phase_11_report.md` | Cross-phase copy (standing rule) | [ ] |
| `docs/Universe-Decisions.md` | Any decision taken at the T4 gate, appended verbatim, append-only | [ ] |
| `docs/Open-Items-Register.md` | Condition-code dictionary (present or absent, with the observed code census); `indicators` usability; withdrawn-quote filter recoverability from source parquet; SIP-vs-direct-feed staleness as a permanent data limitation; storage-order finding from T1b-ii | [ ] |
| `docs/Research-Library-Map.md` | Phase 11 prompts, configs, artifacts, charts, prior-art entries | [ ] |

Parquet artifacts are gitignored and regenerable per the standard §12; JSON summaries, digest, report and charts are committed.

---

## Reporting

On completion, post, in this order:

1. T0b satisfiability audit table — all rows, four checks each
2. State table (T0a) — observed, not asserted
3. T1 identity table — consolidated vs. per-venue evidence, timestamp semantics, dropped-column presence
4. T2 census tables — state shares and run lengths, by segment and day offset, with n per row
5. T3 alignment table + **which pre-registered reading-rule row the curve matches, and nothing further**
6. *(Stage A stops here at the T4 gate.)*
7. T5 cache integrity + wall time and the extrapolation that authorised the pass
8. T6 effective-spread table — bp and cents, per cell, with n
9. **T7 cost-versus-capture table — the headline — per cell, both denominators, three cost multiples, with n, plus the share of events where cost exceeds capture**
10. T8 impact table + unclassifiable share per cell
11. Escalation check table — all 23 rows, observed against threshold, pass/fail
12. Verification block per §10 — every headline number with source, n, and reproduce command
13. Filter waterfall — detection universe → `quotes_ingested` → post-exclusion population → per-cell n
14. Output file table with status
15. Commit list

Every claim cites its chart. **No recommendations. No exclusion rule adopted. No operating point proposed. No result characterised as good, promising, weak, or disappointing.** The agent describes the picture; the read is Cooper's.

---

## Approval Gate

Two gates.

**T4 is a hard gate inside the phase.** Stage B does not begin until Cooper has reviewed charts 01–04 and set: the exclusion rule, the alignment offset, the Stage B population, and the row-11 kill threshold. Nothing in Stage B is authorised before that.

**Do not tag, do not merge, and do not begin Phase 12 scoping until Cooper has reviewed charts 05–08 and given explicit approval.** On approval, tag `phase-11-approved` and fast-forward `main`.

**Chart 06 is the gate. Chart 04 decides whether chart 06 can exist at all.** Both reads are Cooper's, not the agent's.
