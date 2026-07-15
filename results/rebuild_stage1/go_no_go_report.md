# Trades Rebuild Stage 1 — Go/No-Go Validation Report

**Date:** 2026-07-10
**Result: ESCALATED.** 10 of 30 planned validation events were run before a T4 hard-stop
criterion fired. Groups B and C were never attempted. Per the escalation protocol: no
recommendation is made here on whether Stage 2 should proceed — the raw findings below,
including the follow-up investigation into the specific trigger, are for Cooper's review.

---

## 1. T1 — Schema-loss root cause

Full detail in `t1_schema_rootcause.md`. Summary: the raw Massive API response for a
live test call (AAME, 2021-02-05) includes `sip_timestamp`, `participant_timestamp`,
`sequence_number`, `tape`, `id` at genuine nanosecond precision. **The defect is not in
the API.** `collect_massive_data.py`'s current DataFrame/parquet-write code does not drop
or rename any columns, and a sample of its actual prior output
(`data/filtered/*/trades.parquet`) confirms full rich schema is already preserved there.
The schema-loss corruption found in `high_momentum` (Phase V0.0) does not share column
*names* with the raw API at all (`timestamp`/`datetime` vs. `sip_timestamp`/etc.) — it was
introduced by a separate downstream process, not identified, consistent with the
2025-11-24/25 bulk-rewrite finding. No fix was needed in the collector for this defect;
`collect_massive_data_v2.py` performs no column selection anywhere, by design, so it
cannot silently reintroduce schema loss.

## 2. T2 — Pagination fix

`fetch_all_pages`'s `status_forcelist=[500, 502, 503, 504]` excludes 429. A 429 mid-pull
fell through to the generic `!= 200` branch, which logged an error and returned whatever
had accumulated so far — indistinguishable from a complete, successful pull. Under
concurrent load against high-volume tickers (millions of trades/day, 20–130+ sequential
pages), this is a plausible mechanism for Group A's truncations.

Fix, in `collect_massive_data_v2.py`:
- `429` added to the `Retry` adapter's `status_forcelist` (automatic backoff retry).
- The manual pagination loop now retries 429 explicitly (respecting `Retry-After` if
  present) instead of treating it as terminal.
- Any exit that isn't genuine end-of-data (absence of `next_url`) now raises
  `PaginationIncompleteError` instead of returning a partial list — a truncated pull can
  no longer be written to disk looking identical to a complete one.
- Telemetry (`RATE_LIMIT_HITS`, `AUTH_ERROR_HITS`) added so the validation driver can
  detect a 429/auth event even when the retry succeeds, per the escalation table's intent
  that any such event should surface for review rather than be silently absorbed.

No other retry/timeout/backoff values or `MAX_WORKERS` were changed.

## 3. Validation audit — 10 of 30 events run (Group A only; B and C not started)

| Ticker | Date | n_trades | pct_whole_second | schema has sip_timestamp/participant_timestamp | elapsed (s) |
|---|---|---|---|---|---|
| AMC | 2021-01-27 | 6,696,489 | 2.99e-07 | yes | 302.9 |
| OCGN | 2021-02-08 | 3,361,742 | 0.0 | yes | 145.0 |
| GME | 2021-01-27 | 3,151,697 | 3.17e-07 | yes | 142.9 |
| PHUN | 2021-10-22 | 2,671,951 | 0.0 | yes | 117.4 |
| GME | 2021-01-25 | 2,140,748 | 0.0 | yes | 95.4 |
| KODK | 2020-07-29 | 1,663,621 | 6.01e-07 | yes | 72.9 |
| HTZ | 2020-10-16 | 1,486,616 | 0.0 | yes | 64.2 |
| SCKT | 2021-02-16 | 1,478,830 | 0.0 | yes | 65.8 |
| VERU | 2022-04-11 | 1,441,872 | 0.0 | yes | 60.9 |
| OCGN | 2020-12-23 | 1,343,977 | 0.0 | yes | 55.7 |

Full detail (including complete schema fingerprints) in `validation_audit.csv`. All 10
files carry the full rich schema; `pct_whole_second` is effectively zero for every file
(the nonzero values are 1–2 trades out of millions landing on a whole second by pure
chance — not a corruption signature). No file approached the 1% hard-stop threshold.

No 429 or 401/403 was recorded on any of the 10 events (`RATE_LIMIT_HITS` /
`AUTH_ERROR_HITS` telemetry stayed at 0 throughout). Total Group A wall-clock: ~1,123s
(~18.7 min), well inside the 2-hour cap.

## 4. Group A count comparison

| Ticker | Date | Old legacy | Old current | New (v2) | Verdict |
|---|---|---|---|---|---|
| AMC | 2021-01-27 | 384,997 | 6,696,486 | 6,696,489 | PASS (+3) |
| OCGN | 2021-02-08 | 357,000 | 3,361,742 | 3,361,742 | PASS (exact) |
| GME | 2021-01-27 | 393,997 | 3,151,694 | 3,151,697 | PASS (+3) |
| PHUN | 2021-10-22 | 404,000 | 2,671,951 | 2,671,951 | PASS (exact) |
| GME | 2021-01-25 | 392,997 | 2,140,745 | 2,140,748 | PASS (+3) |
| KODK | 2020-07-29 | 389,997 | 1,663,618 | 1,663,621 | PASS (+3) |
| HTZ | 2020-10-16 | 392,997 | 1,486,613 | 1,486,616 | PASS (+3) |
| SCKT | 2021-02-16 | 431,000 | 1,478,830 | 1,478,830 | PASS (exact) |
| VERU | 2022-04-11 | 388,000 | 1,441,872 | 1,441,872 | PASS (exact) |
| OCGN | 2020-12-23 | 466,000 | 1,428,771 | 1,343,977 | **FAIL (-84,794, -5.9%)** |

Full detail in `group_a_count_comparison.csv`.

Five events show a consistent **+3** delta over the old "current" count (AMC, GME×2,
KODK, HTZ) — plausibly late consolidated-tape corrections between the original pull and
now, or a minor boundary artifact; magnitude is negligible (≤0.0002% of each file) and
not investigated further here.

### Follow-up investigation on the OCGN 2020-12-23 escalation trigger (raw data, no conclusion drawn)

The escalation criterion fired exactly as specified. Before reporting, the two files were
compared directly (read-only, `high_momentum` untouched):

- **Old `current` file** (`data/trade_data/high_momentum/OCGN_2020-12-23_trades.parquet`):
  schema is `__index_level_0__`, `condition_codes`, `conditions`, `datetime`, `element`,
  `exchange`, `list`, `price`, `schema`, `size`, `timestamp` — **the malformed_exploded
  schema variant Phase V0.0 flagged**, not the rich schema. 1,428,771 rows, but only
  **42,764 distinct `datetime` values** — each distinct timestamp repeats ~33x on average.
- **New `v2` file**: full rich schema (`sip_timestamp`, `participant_timestamp`,
  `sequence_number`, `tape`, `trf_id`, `trf_timestamp`, `id`). 1,343,977 rows, **1,343,977
  distinct `sip_timestamp` values** — zero duplication.

Raw data only, no conclusion: the old baseline this criterion compared against is itself
one of the schema-corrupted files this whole rebuild exists to fix, with a duplication
pattern consistent with the file's malformed schema. Whether that changes how this
specific escalation should be weighed is not decided here.

## 5. Escalation check table

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| Raw API response missing sip_timestamp/participant_timestamp | any missing | none missing | PASS |
| Any validation file `pct_whole_second` >= 1% | >= 1% | max observed 6.01e-07 | PASS |
| Group A new count < max(old legacy, old current) | any | **OCGN 2020-12-23: 1,343,977 < 1,428,771** | **FAIL — hard stop** |
| Unhandled exception during the run | > 0 | 0 | PASS |
| 429 / auth error during validation | > 0 | 0 | PASS |
| Wall-clock for the sample | > 2h | ~1,123s (Group A only; B/C not run) | PASS |

## 6. Explicit count

**10 of 30 events were attempted. Of those 10, 9 passed all criteria; 1 (OCGN
2020-12-23) failed the count-comparison criterion, triggering the hard stop. Groups B (10
events) and C (10 events) were never run.**

No go/no-go recommendation is made — that determination, and whether the OCGN finding
above changes how the triggering criterion should be interpreted, is Cooper's call.
