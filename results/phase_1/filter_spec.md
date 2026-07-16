# Filter Spec — `filter_events_power_law.py`

**Phase:** 1 (Filter Forensics) — T1
**Script:** `data/collection_scripts/filter_events_power_law.py` (87 lines, read end to end)
**Status:** Never executed. This spec is a static read plus read-only empirical checks against the parquet files it names, run separately in `research/phase_1/` (see T1c below for methodology on the one item the script itself doesn't answer).

All line numbers refer to `data/collection_scripts/filter_events_power_law.py`.

---

## T1a — Inputs

The script reads exactly two files (`filter_events_power_law.py:7-9`):

| Var | Script literal path | Resolved on E: today | Exists | Rows | Cols |
|---|---|---|---|---|---|
| `file1` | `d:\Mom. DB started 11-21-25\data\momentum_events\full_2020_2024_momentum_scan_20251122_000515.parquet` (`:7-8`) | `data/momentum_events/full_2020_2024_momentum_scan_20251122_000515.parquet` | Yes | 18,660 | 9 |
| `file2` | `...\data\momentum_events\momentum_scan_2025.parquet` (`:7,9`) | `data/momentum_events/momentum_scan_2025.parquet` | Yes | 5,950 | 15 |

Full column lists and per-file cleaning stats: `artifacts/scan_input_inventory.json`.

The script's own `base_dir` (`:7`) is a `D:\` literal — this file is **not** on CLAUDE.md's list of known D:\-hardcoded scripts. It doesn't matter operationally (the script is never executed, per this phase's constraints, and both source files resolve unambiguously by filename under `data/momentum_events/` on E:), but it's a gap in that inventory worth flagging.

Loading (`:14,19`): plain `pd.read_parquet`, no filtering at load time. `df1`'s `volume` column is renamed to `event_volume` if present (`:15-16`) — the **only** schema-reconciliation step the script performs between the two files. The two frames are then concatenated with `pd.concat([df1, df2], ignore_index=True)` (`:22`), which is a column-union concat: any column present in one frame and absent in the other is filled with `NaN` for the rows from the frame that lacks it.

`file2` has **no `date` column** — it has `event_date` instead (see table above / inventory JSON). The script never renames or reconciles `event_date` into `date` the way it does `volume`→`event_volume`. This is the origin of the NULL-date rows; see T1d below and `artifacts/null_date_forensics.json` (T3).

Other `data/momentum_events/` contents at time of read: only the four files listed in the inventory JSON. No other `filtered_events_*.parquet` variants exist.

---

## T1b — The fit

- **Dependent variable:** `log_vol` = `log10(event_volume)` (`:32`, `:56`)
- **Regressor:** `log_mom` = `log10(momentum_pct)` (`:31`)
- **Functional form:** simple linear quantile regression, `log_vol ~ log_mom` (`:42`), i.e. a log-log power-law line: `log10(volume) = β0 + β1 · log10(momentum_pct)`, equivalently `volume ∝ momentum_pct^β1`.
- **Log-space handling:** both variables are `log10`-transformed before fitting (`:31-32`). Rows with `momentum_pct <= 0` or `event_volume <= 0` are dropped first (`:28-29`) because the log requires positive inputs — comment at `:29` confirms this is the reason, not an independent business rule.
- **Quantile mechanics:** `statsmodels.formula.api.quantreg` (`:4`, `:42`), fit at `q=0.05` (`:43`). This is a **conditional 5th-percentile line**: for a given `log_mom`, the fitted line estimates the volume level below which only 5% of the *training* population's volume falls.
- **Pre-filters before fitting:**
  - `dropna(subset=['momentum_pct', 'event_volume'])` (`:27`)
  - `event_volume > 0` (`:28`)
  - `momentum_pct > 0` (`:29`)
  - **Training-set-only** cutoff: rows with `momentum_pct` above its own 99.5th percentile are excluded from the *fit* (not from the final kept set) — `:34-36`, comment: "cutoff 99.5% outliers to match visualization." The fitted line is estimated on this trimmed training set, then applied to the *full* cleaned set (`:49-56`) including the excluded top-0.5% momentum outliers.
  - No price, exchange, or listing screens anywhere in the script. No volume floor beyond `>0`. No dollar-volume or market-cap filter.
- **Library:** `statsmodels.formula.api.quantreg` (`:4`), i.e. statsmodels' `QuantReg` via formula interface.

---

## T1c — The `momentum_pct` formula

**`filter_events_power_law.py` does not compute `momentum_pct`.** It is read as a pre-existing column from both `file1` and `file2` (`:27,29,31` — only ever consumed, never assigned). Tracing it further upstream: `data/collection_scripts/collect_massive_data.py` also only *reads* `row.momentum_pct` (to format folder names, `:128`) — it doesn't compute it either. No script present anywhere in `data/collection_scripts/` (`collect_massive_data.py`, `collection_log.txt`, `filter_events_power_law.py`, `inspect_parquet_columns.py`, `test_trades.py`) generates the momentum scan files themselves. **The generating scanner script is not in this repository.**

Given that, the formula was tested empirically against `file1` (which carries `prev_close`, `open`, `high`, `close`, `momentum_pct`, `price_move`) rather than left as a bare unknown:

| Candidate formula | corr(momentum_pct, candidate) | n |
|---|---|---|
| `(high − prev_close) / prev_close × 100` | **0.9997** | 18,658 |
| `(close − prev_close) / prev_close × 100` | 0.9842 | 18,658 |
| `(open − prev_close) / prev_close × 100` (gap at open) | 0.9792 | 18,658 |
| `(high − open) / open × 100` | 0.0823 | 18,658 |

`price_move == high − prev_close` exactly (within 1¢) for 18,421 / 18,660 rows (98.7%). Row-level spot check (`AA`, 2020-03-24): `prev_close=5.67, high=7.48 → (7.48−5.67)/5.67×100 = 31.92`, matching the stored `momentum_pct=31.92` exactly. Restricting to `prev_close > $0.20` (excluding penny-stock rounding blowups), `momentum_pct = (high−prev_close)/prev_close×100` matches within 0.05 for 16,494 / 18,640 rows (88.5%); most of the residual gap is consistent with cent-level rounding on low-priced names, not formula mismatch.

**Conclusion:** `momentum_pct` is a **prior-close-to-intraday-high** measure — `(high − prev_close) / prev_close × 100` — not gap-at-open, not close-to-close. `price_move` is its dollar-equivalent, `high − prev_close`. This is empirical (best-fit against data), not code-confirmed, because the generating script is absent from the repo. Flagged as such.

---

## T1d — Keep rule, output columns, and the NULL-date mechanism

**Keep rule** (`:56, 62`): for every row in the cleaned full set (`calc_df` — both files, positive momentum/volume, `NaN`-dropped, **including** the top-0.5%-momentum rows excluded from training), predict `log_vol_threshold` from the fitted q=0.05 line, then keep the row **iff its actual `log_vol` exceeds that threshold** — i.e., keep rows whose volume is *above* the 5th-percentile-conditional-on-momentum line. This is a **volume-floor filter conditional on momentum**, not a filter that isolates the momentum extreme tail: at any fixed momentum level it discards roughly the bottom 5% by volume and keeps the rest. (`min_volume_threshold = 10**log_vol_threshold` is retained per row, `:65`.)

Net effect: 24,501 cleaned rows in (18,551 from file1 + 5,950 from file2, post `:27-29` cleaning) → 23,268 kept (`:69`), 1,233 dropped (5.03%) — consistent with a ~5% conditional rejection rate applied near-uniformly across momentum levels.

**Output columns** (`:75-76`): `output_cols = [c for c in full_df.columns if c in kept_df.columns] + ['min_volume_threshold']`. Since `kept_df` is derived from a `.copy()` of the concatenated `full_df`, this resolves to essentially the full union of both input schemas plus `min_volume_threshold` — 21 columns total, exactly matching `momentum_events`' 21 columns (see `artifacts/scan_input_inventory.json`).

**Exactly how `date` is populated, and the NULL-date mechanism:** `date` is one of the columns carried straight through from `file1` (`:8`, column list in inventory JSON). `file1` has a `date` column; `file2` does not — `file2` has `event_date` instead. The `pd.concat` at `:22` is a column-union concat with no reconciliation between `date` and `event_date` (contrast with the explicit `volume`→`event_volume` rename at `:15-16`, which *is* schema reconciliation, just not applied to the date field). Consequence: **every row sourced from `file2` gets `date = NaN`** by construction — not a bug in a conditional branch, but a structural gap in the script's column-alignment logic. Nothing between `:22` and the final write (`:78`) touches `date` or backfills it from `event_date`.

This is confirmed against `momentum_events` directly (read-only DuckDB query, T3 preview):

| | rows | `event_date` populated |
|---|---|---|
| `date IS NULL` | 5,911 | 5,911 / 5,911 (100%) |
| `date IS NOT NULL` | 17,357 | 0 / 17,357 (0%) |

The partition is perfect and disjoint — every NULL-`date` row has `event_date`, every dated row lacks `event_date`. This is decisive: **NULL dates are exactly the file2-sourced rows that survived the q05 filter.** Full evidence and origin classification in `artifacts/null_date_forensics.json` (T3) — flagged here because T1d asks whether any code path can emit a NULL date, and the answer is yes, structurally, for one entire input source.

(5,950 raw `file2` rows → 5,911 land in the final NULL-date set; the remaining 39 were dropped by the q05 filter, `:62`, same as any other row.)

---

## T1e — Hardcoded parameter table

Every literal in the script that changes its output:

| Line(s) | Literal | Effect |
|---|---|---|
| `:7` | `base_dir = r"d:\Mom. DB started 11-21-25\data\momentum_events"` | Selects which two files are read (by filename) |
| `:8` | `"full_2020_2024_momentum_scan_20251122_000515.parquet"` | file1 identity |
| `:9` | `"momentum_scan_2025.parquet"` | file2 identity |
| `:10` | `"filtered_events_power_law_q05.parquet"` | Output filename |
| `:15-16` | `if 'volume' in df1.columns: rename to 'event_volume'` | The only cross-file schema reconciliation performed; does not cover `date`/`event_date` |
| `:27` | `dropna(subset=['momentum_pct', 'event_volume'])` | Row-eligibility filter |
| `:28` | `event_volume > 0` | Row-eligibility filter |
| `:29` | `momentum_pct > 0` | Row-eligibility filter (comment: required for log) |
| `:31-32` | `log10` transform on `momentum_pct` and `event_volume` | Defines the model's variable space |
| `:35` | `quantile(0.995)` | Training-set upper trim (top 0.5% momentum excluded from *fit only*) |
| `:42` | formula `'log_vol ~ log_mom'` | Model specification (dependent ~ regressor) |
| `:43` | `q=0.05` | Quantile level — defines the boundary line and its ~5% conditional rejection rate |
| `:62` | `log_vol > log_vol_threshold` | The keep/drop decision |
| `:75` | `output_cols` construction | Which columns survive to `momentum_events` |
| `:78, 83` | `.to_parquet(...)`, `.to_csv(...)` | Output format/location |

---

## Summary (for report §1–2)

- Fit: `log10(event_volume) ~ log10(momentum_pct)`, quantile regression, `q=0.05`, trained on rows ≤ 99.5th-percentile `momentum_pct`, applied to all cleaned rows.
- Keep rule: actual `log10(volume)` above the fitted 5th-percentile line — a **volume floor conditional on momentum**, not a momentum-extremity filter.
- `momentum_pct` (empirically, not code-confirmed — generating script absent): `(high − prev_close) / prev_close × 100`.
- NULL dates are structural: `file2` never had a `date` column, and the script's only schema-reconciliation step (`:15-16`) doesn't cover it. See T3 for the full classification.
