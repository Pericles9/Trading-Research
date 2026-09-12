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
- Float endpoint (`/stocks/vX/float`): archived at F1-T2c for orientation only. **Banned from
  `event_fundamentals` or any downstream table by D27.**
- **Pull executed 2026-09-12** (`research/fundamentals_f1/t2_massive_pull.py`): all 2,935 distinct
  resolved CIKs from F1-T1, across 8 working endpoints. Raw archive:
  `data/raw/fundamentals/massive/2026-09-12/<source>/<key>.json`, one file per (source, key), key =
  CIK (zero-padded 10-digit string) for every source including the five that are actually queried by
  ticker — the *file name* is always the CIK so all 8 sources join back to `ticker_identity.parquet`
  the same way; only the outbound API request differs. Every file is a JSON array (possibly empty —
  empty means "queried, vendor returned zero records for this CIK," not a fetch failure); manifest and
  checksums at `data/raw/fundamentals/massive/2026-09-12/fetch_manifest.json`. Integrity spot-check
  (`n=5` random files per source plus full-population size/zero-length scan, all 8 sources, 2026-09-12):
  zero malformed-JSON files, zero non-list top-level payloads, sizes consistent with the endpoint's
  expected record volume. Total archive: 23,480 files, 2.17 GB.

  `ratios` was named in the work order but no endpoint exists at any plausible path (4 tested, all
  404) — **not_found**, recorded in the manifest, not substituted or guessed further (F1-T2a).

  | source | endpoint | keyed by | source_of_record | n CIKs | total records | notes |
  |---|---|---|---|---|---|---|
  | `financials` | `/vX/reference/financials` | `cik` | **false** (D-pending / F1-T0f Outcome A) | 2,935 | 111,459 | bundles 4 statements per filing period, see below. 719/2,935 files empty (no financials filed under that CIK in vendor's coverage window — smallest/newest names). |
  | `ticker_details` | `/v3/reference/tickers` | `cik` | true | 2,935 | 3,110 | reference/identity record, not a time series |
  | `splits` | `/v3/reference/splits` | ticker | true | 2,935 | 2,554 | 1,587/2,935 empty (no splits in history — expected for most names) |
  | `dividends` | `/v3/reference/dividends` | ticker | true | 2,935 | 35,356 | 2,040/2,935 empty (no dividend history — expected, most of this universe is non-dividend-paying momentum names) |
  | `short_interest` | `/stocks/v1/short-interest` | ticker | true | 2,935 | 440,244 | biweekly settlement-date series; 0 empty files |
  | `short_volume` | `/stocks/v1/short-volume` | ticker | true | 2,935 | 1,776,508 | daily series; 0 empty files; largest source on disk (940 MB) |
  | `float` | `/stocks/vX/float` | ticker | **false (D27, archive-only, never a join key)** | 2,935 | 2,671 | single point-in-time record per ticker where available; 264/2,935 empty |
  | `ticker_events` | `/vX/reference/tickers/{ticker}/events` | ticker (path segment) | true | 2,935 | 2,655 | path-based, not query-param; usually 0-1 event per CIK (ticker-change history) |

  **Per-source field schema** (from a live sample, `0000001750` = AAR Corp / AIR, 2026-09-12):

  - **`financials`** — top level: `cik`, `company_name`, `tickers` (list), `sic`, `fiscal_year`,
    `fiscal_period` (e.g. `TTM`, `Q1`, `FY`), `timeframe`, `start_date`, `end_date`, `filing_date`,
    `acceptance_datetime`, `source_filing_url`, `source_filing_file_url`, `financials` (nested dict).
    `financials.income_statement`, `.balance_sheet`, `.cash_flow_statement`, `.comprehensive_income`
    are each `{field_name: {value, unit, label, order}}` — GAAP-labeled line items (e.g.
    `net_income_loss`, `revenues`, `basic_average_shares`, `accounts_payable`, `net_cash_flow`), not
    raw XBRL tags. One vintage per filing period per the F1-T0f/g finding above — point-in-time, not
    the restated value, and `source_of_record=false` in the manifest (companyfacts cross-check harness
    per Amendment F1-A1 §4; may still populate `fin_` directly under F1-T0f's Outcome A).
  - **`ticker_details`** — `ticker`, `name`, `cik`, `market`, `locale`, `primary_exchange`, `type`
    (e.g. `CS`), `active` (bool), `currency_name`, `composite_figi`, `share_class_figi`,
    `last_updated_utc`. Point-in-time reference snapshot only — this pull did not use the `date=`
    as-of parameter (that's F1-T1's job, already done); this archive is orientation/cross-check.
  - **`splits`** — `id`, `ticker`, `execution_date`, `split_from`, `split_to`.
  - **`dividends`** — `id`, `ticker`, `cash_amount`, `currency`, `dividend_type`, `frequency`,
    `declaration_date`, `ex_dividend_date`, `record_date`, `pay_date`.
  - **`short_interest`** — `ticker`, `settlement_date`, `short_interest`, `avg_daily_volume`,
    `days_to_cover`. Biweekly (FINRA settlement schedule).
  - **`short_volume`** — `ticker`, `date`, `total_volume`, `short_volume`, `short_volume_ratio`,
    `exempt_volume`, `non_exempt_volume`, plus per-venue breakdowns (`nyse_short_volume`,
    `nasdaq_carteret_short_volume`, `nasdaq_chicago_short_volume`, `adf_short_volume`, and each
    venue's `_exempt` counterpart). Daily.
  - **`float`** — `ticker`, `free_float`, `free_float_percent`, `effective_date`. Single record per
    ticker where available — not a time series. D27: archive-only, never joined into
    `event_fundamentals`.
  - **`ticker_events`** — `cik`, `name`, `composite_figi`, `events` (list of
    `{type, date, <type>: {...}}`, e.g. `{"type": "ticker_change", "date": ..., "ticker_change":
    {"ticker": "AIR"}}`).

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
