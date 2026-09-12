# Fundamentals sources — Build F1

Companion to `prompts/fundamentals_f1.md`. Tracked copy of record for `data/raw/fundamentals/` and
`data/fundamentals/`'s provenance, per the same `docs/data/` convention as `docs/data/Schema.md`
(`/data/` is wholly gitignored; this file is where the record lives).

## Status

**Amendment F1-A1 (2026-09-12) resolved the F1-T0 stop. F1-T1/F1-T2 unblocked; `fin_` may proceed from
the vendor as originally planned.** Timeline:

1. Pre-flight (D14 Amendment A1, D27–D33) and `t0_spine.parquet` (F1-PF5) built and verified, 2026-09-11.
2. **F1-T0** found exactly one vendor record per period (zero duplicates across two companies' complete
   history) but did not establish *which* vintage that record is — escalation row 1 fired, correctly, on
   an incomplete question.
3. **Amendment F1-A1** named the gap and specified the disambiguating tests.
4. **F1-T0f/F1-T0g** (2026-09-12) resolved it: CLRB's vendor `NetIncomeLoss` for FY2023 (-37,983,496,
   `filing_date=2024-03-27`) matches its **original** 10-K exactly, not its restated 10-K/A
   (-42,770,610, filed 2024-10-29). **The vendor is point-in-time — it is frozen at first-filed and
   never updated when a restatement lands.** Separately, SEC `companyfacts` is confirmed genuinely
   multi-vintage (5 observations across 5 accession numbers for the same period, 2 distinct values).
   Escalation row 1a fires: **not a stop, a simplification** — the full `companyfacts`/XBRL
   element-mapping rebuild is not mandatory before `fin_` can be built; it remains available for the
   `fin_superseded_later` flag and as a cross-check harness. Full record:
   `results/fundamentals_f1/artifacts/t0f_t0g_disambiguation_summary.json`,
   `research/fundamentals_f1/t0f_t0g_disambiguation.py`.

**Identification method, worth restating as a standing note (Amendment F1-A1 §0):** searching for any
10-K/A or 10-Q/A in this universe mostly surfaces **administrative, Part-III-only amendments** filed
~1 month after the original — adding exec-comp disclosure that would otherwise need a proxy statement,
touching no financial-statement value. **An 8-K Item 4.02 ("Non-Reliance on Previously Issued Financial
Statements") is the signal that actually means a genuine restatement.** Any future search for restated
companies in this universe should search Item 4.02 first, not form type alone.

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
