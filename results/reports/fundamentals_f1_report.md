# Build F1 — Fundamental Data & Float Layer: Coverage Report

**Date:** 2026-09-12 · **Branch:** `build/fundamentals-f1` · **Config hash:** `4eebcb303820`
**Type:** data-layer build, not a research phase. No finding, no hypothesis test. This report is the
digest required by `prompts/fundamentals_f1.md` §7, in that section's exact order. **No interpretation
beyond what each item states directly — Cooper decides what any of this means for downstream work.**

---

## 1. F1-T0 outcome

The vendor's financial-statement endpoint is **point-in-time, frozen at first-filed**: CLRB's FY2023
`NetIncomeLoss` matches its original 10-K exactly (-37,983,496) and not its later 10-K/A restatement
(-42,770,610) — **Outcome A**, confirmed 2026-09-12 (`t0f_t0g_disambiguation_summary.json`).

## 2. Identity resolution

20,951 events resolved: **97.32% `resolved_exact`** (20,390), **1.49% `resolved_ambiguous`** (313,
across 37 tickers), **1.18% `unresolved`** (248). Escalation row 2 (>5% not-exact) **does not fire**
(2.68%). Chart: `results/fundamentals_f1/charts/t1_identity_quality_by_year.html`.

## 3. Row counts and set equality

`event_fundamentals` has exactly **20,951 rows**, `event_id` unique. Set equality against
`quotes_bitmaps_all.parquet`'s materialization (not a live view scan): **exact match, 0 only-in-universe,
0 only-in-table**, verified by `research/fundamentals_f1/verify_event_fundamentals.py`.

## 4. t0-tiering breakdown

`nanosecond_poll1`=110, `minute_a102`=15,259, `first_trade_fallback`=5,582, `unavailable`=0. Sum =
20,951. **F1-T3f's poll-boundary question is answerable only for the `nanosecond_poll1` tier** (110
events) — the other two tiers do not carry instantaneous-crossing precision (D33).

## 5. Coverage by group

**Distribution before aggregate** — every cross-cut below is counts per cell
(`results/fundamentals_f1/charts/t6_coverage_surface.html`, `t6_coverage_report.json`), not a bare share.

| group | source | n covered | share | escalation |
|---|---|---|---|---|
| `flg` | SEC filing index | 20,703 | 98.8% | — |
| `shs` | SEC cover-page shares | 16,099 | 76.8% | row 5 floor 70% — **does not fire** |
| `fin` | Vendor financials | 8,303 | 39.6% | — |
| `si` | Vendor short interest | 20,377 | 97.3% | — |
| `spl` | Vendor splits | 8,732 | 41.7% | — |

**Cross-cuts** (full tables in `t6_coverage_report.json`):

- **By year** — `fin_` coverage: 2020=5.2%, 2021=2.4%, 2022=4.6%, 2023=48.4%, 2024=65.8%, 2025=60.9%.
  A cliff, not a gradient, between 2022 and 2023.
- **By detection-price decile** (tick-derived, not D4-restricted — see §4 of `docs/data/fundamentals_sources.md`) —
  `fin_` coverage: decile 0 (cheapest) 51.6%, decile 9 (priciest) 37.5%.
- **By delisted status** — `fin_` coverage: `active`=39.7%, `unknown`=39.1% (near-identical).
- **By exchange** — in `t6_coverage_report.json`, not reproduced here (many exchange values, small n
  in several cells).

**Is coverage missing at random (F1-T6c)? No — but not for the reason the task's own framing
anticipated.** The dominant driver is **year** (a vendor historical-backfill boundary around
2022–2023), not company quality: the delisted-status proxy shows almost no gap, and the price-decile
gradient runs opposite to the "thin/shell names have worse data" expectation. This universe's `fin_`
gap reads as a vendor coverage-depth limit for small/thin momentum names, not a survivorship pattern
concentrated in bad companies specifically.

## 6. Lag distribution per group

Not the mean — the distribution. `results/fundamentals_f1/charts/t6_lag_distributions.html`
(log10-day histograms, all 5 groups, n/median/p90 annotated per panel) and
`results/fundamentals_f1/charts/t3_filing_proximity.html` (the `flg_` lag panel specifically, plus
form-type mix of the nearest prior filing).

## 7. Vendor-vs-SEC share-count disagreement (F1-T4d)

**Reported, not reconciled.** 6,940 events carry both the SEC cover-page count (`shs_shares_outstanding`)
and the vendor's period-average count (`fin_shares_basic`) — different concepts by construction, so
disagreement is expected, not necessarily an error. Ratio (SEC ÷ vendor): median **1.03**, IQR
1.00–1.26 (the bulk agrees closely); the tail is extreme — p99 = 1,040×, max = 13.4M×. 45.7% of events
agree within 5%, 66.0% within 20%. The extreme tail is not clipped or investigated further, per this
task's own instruction to report rather than fix. `results/fundamentals_f1/artifacts/t4d_share_count_disagreement.json`.

## 8. F1-T3f poll-boundary count

**Zero.** No filing was accepted between the instantaneous threshold crossing and the 60-second poll
boundary, across all 110 `nanosecond_poll1`-tier events. Escalation row 6 does not fire; the question
is closed for this tier only (see §4 above for the other two tiers' inapplicability).

## 9. Verification Block (§5), each assertion individually

All 9 pass, on the corrected table (three real defects found and fixed during F1-T5d — see
`prompts/fundamentals_f1.md`'s F1-T5d entry for the full account: a verification-script date-formatting
bug, a genuine `shs_asof_ns` hard-stop traced to a real SEC source-data quirk and fixed at the join
level, a stale `fin_quality` enum in config, and a `COUNT(*)`-over-`LEFT JOIN` bug found in two places —
`spl_n_splits_365d` and the already-committed `flg_n_filings_72h` — both fixed):

| # | assertion | result |
|---|---|---|
| 1 | exactly 20,951 rows, `event_id` unique | PASS |
| 2 | `event_id` set equals the universe materialization exactly | PASS |
| 3 | t0-tier counts sum to 20,951; `nanosecond_poll1` = 110 | PASS |
| 4 | zero `*_accepted_ns`/`*_asof_ns`/`*_last_split_ns` ≥ `t0_ns` | PASS |
| 5 | every quality column matches its declared enum | PASS |
| 6 | no output column shares a name with (or transforms) a spine numeric | PASS |
| 7 | every non-null group value has non-null provenance | PASS |
| 8 | every raw archive file matches its recorded checksum | PASS |
| 9 | the event layer rebuilds byte-identically from the normalized layer | PASS |

## 10. Companion scoping note

`claude/fundamental_data_float_scoping_note.md`, referenced by the original work order draft, does not
exist in this checkout. This build proceeded on the work order's own inline numbers, per that draft's
own stated fallback (`prompts/fundamentals_f1.md`'s reconciliation note, 2026-09-11).

---

## What this build deliberately did not do

Per `prompts/fundamentals_f1.md` §8: no float (shares outstanding only), no vendor float endpoint
(D27), no derived ratios, no fundamental-vs-outcome computation (D32), and the two Cooper-gated
thresholds (`filed_stale_days`, `shs_quality_coverage_floor`) plus the blast-radius threshold
(escalation row 1c) were set by Cooper before the runs they gate, not defaulted. F1-T4f (the
`companyfacts`-based `fin_` rebuild) stayed optional and was not built — F1-T3h's blast radius (3.70%)
did not clear the mandatory threshold (10%).

**Float tiers 2 and 3 are out of scope for this build** and are scoped against this report, not
against ambition fixed in advance, per §3's own instruction.

## Self-caught corrections during this build (full account in commit history)

- F1-T2's `fetch_manifest.json` claimed per-file checksums that were never actually persisted (computed,
  discarded). Fixed prospectively and retroactively.
- `t0_assemble.py`'s `FILTERED_ROOT` was a cwd-relative literal, silently fragile across git worktrees.
  Fixed to route through `resolve_data_root()`; re-ran and reproduced identical tier counts.
- Two `COUNT(*)`-over-`LEFT JOIN` bugs (one in already-committed F1-T3 output, one caught before its
  first commit in F1-T5) inflated every zero-match count by exactly 1. Both fixed.
- A genuine SEC source-data quirk (a cover-page "as of" date postdating its own filing's acceptance
  timestamp) was traced to its root cause before being handled at the join level, not patched around.

## Companion artifacts

- Config: `config/fundamentals_f1.json` (hash `4eebcb303820`)
- Event table: `data/fundamentals/event_fundamentals.parquet` (gitignored, regenerable)
- Normalized companion tables: `results/fundamentals_f1/artifacts/{sec_filings,event_filings_window,
  shares_outstanding_observations,financials_vintages,short_interest_flat,splits_flat,t0_spine,
  ticker_identity}.parquet` (all gitignored, regenerable from committed config + code)
- Summaries (tracked): every `*_summary.json` and `*_report.json` under `results/fundamentals_f1/artifacts/`
- Charts (tracked): `results/fundamentals_f1/charts/*.html`
