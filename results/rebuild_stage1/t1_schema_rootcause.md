# T1 — Schema-Loss Root Cause

**Test event:** AAME, 2021-02-05 (low-volume, cheap single-page test)
**Call:** `GET https://api.massive.com/v3/trades/AAME?timestamp=2021-02-05&limit=5&sort=timestamp&apiKey=...`
**HTTP status:** 200

## Raw API response (before any DataFrame/parquet conversion)

Top-level keys: `results`, `status`, `request_id`, `next_url`

First raw trade record, verbatim:

```json
{
  "conditions": [12],
  "exchange": 11,
  "id": "99051",
  "participant_timestamp": 1612573194816174592,
  "price": 4.66,
  "sequence_number": 7767423,
  "sip_timestamp": 1612573194816539038,
  "size": 300,
  "tape": 3,
  "decimal_size": "300.0"
}
```

**Finding: the raw API response includes `sip_timestamp`, `participant_timestamp`,
`sequence_number`, `tape`, `id` — all present, all genuine nanosecond-epoch magnitude
(19-digit integers, e.g. `sip_timestamp=1612573194816539038` ≈ Feb 5 2021 correctly).
`trf_id`/`trf_timestamp` are absent on this record, which is expected — Massive/Polygon
only populates those for TRF-reported trades, and `exchange=11` here isn't one.**

This is the T1a branch: **the defect is not in the API call.** Per spec, proceed to T2.

## Where the schema loss actually happens (further tracing beyond T1's minimum bar)

`collect_massive_data.py`'s DataFrame/save logic (lines 202–217) was checked directly:

```python
df_t = pd.DataFrame(all_trades)
if 'participant_timestamp' in df_t.columns:
     df_t['participant_timestamp'] = pd.to_numeric(df_t['participant_timestamp'])
if 'sip_timestamp' in df_t.columns:
     df_t['sip_timestamp'] = pd.to_numeric(df_t['sip_timestamp'])
df_t.to_parquet(trades_final_path)
```

**No column dropping or renaming occurs here.** `pd.DataFrame(all_trades)` from a list of
raw API dicts carries every key through as a column, and `to_parquet` writes all of them.

This was cross-checked against real prior output: `collect_massive_data.py` writes to
`data/filtered/{TICKER}_{DATE}_{MOM}/trades.parquet` (its `OUTPUT_DIR` + per-row folder
naming — a **different, nested layout** than the flat `data/trade_data/high_momentum`
corpus that Phase V0.0 audited). A random sample of 6 files under `data/filtered/`,
spanning 2023–2024 dates, **all** carry the full rich schema: `sip_timestamp`,
`participant_timestamp`, `sequence_number`, `tape`, `trf_id`, `trf_timestamp`, `id` —
genuinely intact, no whole-second corruption signature.

The corrupted "reduced schema" found in `high_momentum` (columns: `conditions`,
`datetime`, `exchange`, `price`, `schema`, `size`, `timestamp`) doesn't share column
*names* with the raw API response at all — the API never returns fields called
`timestamp` or `datetime`. This, combined with `data/filtered/` (this collector's actual
output target) showing clean schema throughout, is strong evidence that **the schema-loss
defect is not in `collect_massive_data.py` as currently written — it was introduced by a
separate downstream process** that reformats/renames columns into the reduced schema
found in `high_momentum`, consistent with Phase V0.0's 2025-11-24/25 bulk-rewrite finding.
That downstream process has not been identified; no other collector script exists in the
repo (`data/collection_scripts/` was searched in full).

One nuance worth flagging: Phase V0.0 classified `element`/`list`/`__index_level_0__`
columns as "malformed_exploded" (implying breakage). In the clean `data/filtered/` sample,
`element`/`list` appear on **every** good/rich-schema file — they may be a normal artifact
of how this pipeline explodes list-typed fields (e.g. `conditions`), not corruption by
themselves. `__index_level_0__` (a raw pandas index leak) is the more likely genuine
defect signature within that bucket. Not re-litigated further here — noted for whoever
picks up remediation of the `high_momentum` corpus's malformed_exploded files specifically.

## Side finding (not in scope of T1's decision, reported per "state plainly")

`data/filtered/` already contains 17,357 `trades.parquet` files (and matching
`quotes.parquet`) with intact rich schema, for a ticker+date universe that has not been
compared against the 19,347 events in `high_momentum`. Whether these overlap, and whether
any overlap could reduce Stage 2's live-API re-pull burden, is a question for Cooper — not
assumed or acted on here.

## Conclusion

T1a confirmed. Proceeding to T2 (pagination fix).
