# Fundamentals sources — Build F1

Companion to `prompts/fundamentals_f1.md`. Tracked copy of record for `data/raw/fundamentals/` and
`data/fundamentals/`'s provenance, per the same `docs/data/` convention as `docs/data/Schema.md`
(`/data/` is wholly gitignored; this file is where the record lives).

## Status

**STOPPED at F1-T0 (2026-09-11), escalation row 1 fired.** Pre-flight (D14 Amendment A1, D27–D33) and
`t0_spine.parquet` (F1-PF5) are built and verified. F1-T0's restatement gate test found Massive's
financials endpoint is **not point-in-time**: two independent universe companies with a confirmed SEC
restatement event (AGAE, a 10-K/A; CLRB, a genuine 8-K Item 4.02 non-reliance event) both show zero
duplicate `(start_date, end_date, timeframe)` records across their complete history, and CLRB's FY2023
record queried with `filing_date.lt` set before its restatement 8-K returns byte-identical output to an
unfiltered query. There is no earlier vintage for `filing_date` to gate to. Full record:
`results/fundamentals_f1/artifacts/t0_restatement_test_summary.json`,
`research/fundamentals_f1/t0_restatement_test.py`.

**Consequence: F1-T1 through F1-T6 do not run as originally scoped.** Per `prompts/fundamentals_f1.md`
§3's own outcome table, the `fin_` group cannot be assembled from Massive's financials endpoint without
look-ahead bias — every stored value would silently carry whatever the *latest* restatement says, not
what was knowable at `t0`. The SEC route (raw XBRL per accepted filing, already the plan for `shs_` and
`flg_`) becomes the source of record for `fin_` too. **This needs a work-order amendment from Cooper
before F1-T2 or any later task runs** — not a workaround chosen here.

Source schemas below are filled in as F1-T2 (Massive, once amended) and F1-T3 (SEC EDGAR) actually
run.

## Identity key

`event_id = f"{ticker}_{event_date_canonical}_{momentum_pct:.2f}"` — reused verbatim from
`research/phase_10/common.py:215`. No second convention for the same concept exists in this build.

## t0 anchor (D33)

Tiered construction — see `docs/Universe-Decisions.md` D33 for the full reasoning and
`config/fundamentals_f1.json`'s `t0_spine` block for the exact artifact paths and thresholds:

1. `det_ns_poll1` from `results/phase_10/artifacts/v2_r13_detection.parquet`, threshold 1.3 (matching
   `config/phase_10_v4.json`'s own pin for this artifact) — 114 rows at that threshold, 110 with an
   actual crossing (4 are `never_crosses = TRUE`).
2. `a102_detection_anchors.parquet`'s `det_minute`, resolved back to that bar's `first_trade_ts` in
   `event_minute_bars_v2` (not reconstructed via calendar arithmetic) — 15,763 rows total, 15,369
   with a defined `det_minute` (matching D15's own "detection-universe" count exactly), 15,259
   actually used after tier 1 claims its 110.
3. First regular-session (09:30–16:00 ET) trade of `event_date_canonical`, read directly from each
   event's own `data/filtered/{TICKER}_{DATE}_{MOM:.2f}/` folder — 5,582 events.

**Run and verified** (`results/fundamentals_f1/artifacts/t0_assemble_summary.json`, F1-PF5,
2026-09-11): `nanosecond_poll1`=110, `minute_a102`=15,259, `first_trade_fallback`=5,582,
`unavailable`=0. Sum = 20,951, exactly the universe.

## Massive vendor pull (F1-T2)

- Credential: `.secrets/polygon_api_key.txt`, read via `research/fundamentals_f1/common.py:load_massive_api_key()`.
  Never hardcoded, printed, or logged. **Not** the pattern in
  `data/collection_scripts/collect_massive_data.py`, which embeds a live key in plaintext — that file
  is not reused or referenced by this build.
- Network authorization: `docs/Universe-Decisions.md` D14 Amendment A1, scoped to this task only.
- Per-source schema: **filled in at F1-T2e**, once the pull actually runs.
- Float endpoint (`/stocks/vX/float`): archived at F1-T2c for orientation only. **Banned from
  `event_fundamentals` or any downstream table by D27.**

## SEC EDGAR pull (F1-T3, F1-T4)

- Network authorization: D14 Amendment A1, scoped to this task only.
- User-Agent: **PENDING** — set in `config/fundamentals_f1.json`'s `sec_edgar.user_agent` before F1-T3
  runs. SEC requires a descriptive User-Agent with a real contact address on every request.
- Per-source schema: **filled in at F1-T3/F1-T4**, once the pull actually runs.

## Declared dilution form set (F1-T3e)

**PENDING finalization** — starting set in `config/fundamentals_f1.json`'s `dilution_form_set` block
(the 424B family, S-1/S-3 and their amendments, 8-A registrations, 8-K Item 3.02). Confirmed here, not
left as an inline literal in code, per the work order's own requirement. Finalize before F1-T3e runs.

## Cooper-set thresholds (F1-T4 gate)

Neither has been set yet. **F1-T4 does not run until both are recorded here with Cooper's actual
values** — the placeholders in `config/fundamentals_f1.json` are suggestions, not defaults to adopt
silently:

- `filed_stale_days` — placeholder 45. Governs `shs_quality`'s `filed_exact` vs. `filed_stale` split.
- `shs_quality_coverage_floor` — placeholder 0.70. Escalation row 5 in `prompts/fundamentals_f1.md` §6.

## Vendor-vs-SEC share count disagreement (F1-T4d)

**Filled in once F1-T4 runs.** Reported, not reconciled — a systematic disagreement is itself a finding
about the sources.
