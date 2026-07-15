---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/complete
created: 2026-07-11
---

# Momentum Event Curation — Validation Report

Read-only. No live file was touched, no ingestion was run. All outputs are in
`results/momentum_curation/`.

## T1 — Curation script located

`data/collection_scripts/filter_events_power_law.py`. Reads
`full_2020_2024_momentum_scan_20251122_000515.parquet` and
`momentum_scan_2025.parquet`, concatenates them, fits a quantile regression
(q=0.05) of `log10(event_volume)` on `log10(momentum_pct)` using the ≤99.5th
momentum-percentile subset as training data, then keeps events whose actual
volume exceeds the fitted 5th-percentile threshold line for their momentum
level. Output: `filtered_events_power_law_q05.parquet` (+ a redundant `.csv`
export).

## T2 — Validation by reproduction: two runs, opposite results

**Run A — script as-is, against the current on-disk scan files, no
exclusions:** reproduces `filtered_events_power_law_q05.parquet`
**exactly** — same 19,170 unique `(ticker, date)` pairs, same 23,268 rows,
0 additions, 0 omissions.

**Run B — same script, with the 7,252 recovered events explicitly excluded
from the candidate pool before fitting (the literal T2 instruction):** does
**not** reproduce the existing file — 22,122 kept vs. 23,268 existing, and
the fitted regression coefficients differ meaningfully (slope 0.981 vs.
0.585, intercept 2.252 vs. 2.126). Excluding the recovered events changes
both the training-set composition and the resulting threshold line, which
then changes which of the *remaining* (non-recovered) events pass — this is
exactly the "shifting threshold" mechanism flagged as a risk in this task's
own baseline, just triggered by the wrong hypothesis (see below).

**Conclusion: Run A is the correct reproduction.** The existing curated file
was already generated against a candidate pool that included all 7,252
recovered events.

## This overturns the task's baseline premise

The baseline stated `filtered_events_power_law_q05.parquet` "predates this
project's data-recovery work and is missing exactly 7,252 events... unknown
whether those events would pass the underlying curation criteria if
evaluated today." That assumption doesn't hold, checked directly rather than
taken on faith:

- The curation script's inputs are the two raw **scan candidate** files, not
  `filtered/`'s actual collected corpus. "Recovery" in this project meant
  successfully collecting/verifying trade data for candidates that were
  *already* on those scan lists — it never added new candidate rows to
  `momentum_scan_2025.parquet` or `full_2020_2024_momentum_scan_*.parquet`.
  Those files are unchanged since Nov 2025; this project only ever *read*
  `momentum_pct` from them, never wrote to them.
- `filtered_events_power_law_q05.parquet`'s mtime (2026-01-19) is after both
  scan files existed (Nov 2025) — so by the time curation ran, all 7,252
  recovered-event candidates were already present in its input pool and were
  already evaluated.
- The curation has already rendered a verdict on all 7,252: **zero of them
  passed** (checked directly against Run A's kept set — 0 / 5,902 of the
  2025-migrated events, 0 / 47 of the 2025-blocked events, 0 / 1,303 of the
  `minute/trades` 2020–2024 events). Not "unknown" — evaluated and rejected,
  every one.

## Escalation check

| Condition | Result |
|---|---|
| T2 fails to reproduce the existing file | Run A: no (reproduces exactly). Run B: yes, but Run B was the wrong reconstruction of "original universe" — resolved by Run A, not a genuine escalation |
| Curation script not found | Found |
| Unhandled exception | None |
