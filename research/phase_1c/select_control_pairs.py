"""
Phase 1c T3-R3 (Amendment 1) - select 20 control (ticker, session) pairs:
15 stratified across years x event-day trade-count terciles (as the
original T3 design), plus 5 targeted pairs drawn from sessions where the
archive contains non-null values in an optional field (config's
optional_fields, derived in T3-R1) - directly testing the conditional-
emission hypothesis the amendment is built on.

Population for both pools: in-scope-eligible (present in event_flags.parquet),
healthy (neither flag_missing_event_day nor flag_window_calendar_bug),
trades_ingested=TRUE - events this phase asserts are already correctly and
completely archived.
"""
import json

import duckdb
import numpy as np
import pandas as pd

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

EVENT_FLAGS = CFG["paths"]["event_flags"]
FOLDER_INV = CFG["paths"]["folder_inventory_v2"]
DB_PATH = CFG["paths"]["momentum_events_db"]
OUT_PATH = "results/phase_1c/artifacts/control_pairs.parquet"
CTRL_CFG = CFG["control_fetch"]
OPTIONAL_TRADES = CFG["optional_fields"]["trades"]


def healthy_population(con):
    flags = con.execute(f"SELECT * FROM read_parquet('{EVENT_FLAGS}')").fetchdf()
    inv = con.execute(
        f"SELECT ticker, date AS event_date_canonical, folder_name, momentum_str, "
        f"trades_ingested, quotes_ingested FROM read_parquet('{FOLDER_INV}')"
    ).fetchdf()
    healthy = flags[
        ~flags["flag_missing_event_day"].fillna(False)
        & ~flags["flag_window_calendar_bug"].fillna(False)
        & (flags["n_trades_event_day"].fillna(0) > 0)
    ].copy()
    healthy = healthy.merge(inv, on=["ticker", "event_date_canonical"], how="inner")
    healthy = healthy[healthy["trades_ingested"] == True]  # noqa: E712
    healthy["year"] = pd.to_datetime(healthy["event_date_canonical"]).dt.year
    return healthy


def select_stratified(healthy, n_target, rng):
    healthy = healthy.copy()
    healthy["trade_count_tercile"] = pd.qcut(healthy["n_trades_event_day"], 3, labels=["low", "mid", "high"])
    cells = healthy.groupby(["year", "trade_count_tercile"], observed=True)
    picks = []
    for _, group in cells:
        if len(group) == 0:
            continue
        idx = rng.integers(0, len(group))
        picks.append(group.iloc[idx])
    picked = pd.DataFrame(picks)
    if len(picked) > n_target:
        keep_idx = rng.choice(len(picked), size=n_target, replace=False)
        picked = picked.iloc[sorted(keep_idx)]
    elif len(picked) < n_target:
        remaining = healthy[~healthy.index.isin(picked.index)]
        extra_n = n_target - len(picked)
        extra_idx = rng.choice(len(remaining), size=min(extra_n, len(remaining)), replace=False)
        picked = pd.concat([picked, remaining.iloc[extra_idx]], ignore_index=True)
    return picked.reset_index(drop=True)


def select_targeted(con, healthy, optional_fields, n_target, rng):
    """Pairs whose archive trades rows contain non-null values in an
    optional field - tests that the vendor still conditionally emits it
    for sessions where it should be present."""
    if not optional_fields:
        return pd.DataFrame(columns=list(healthy.columns) + ["targeted_optional_field", "archive_non_null_count"])

    per_field_n = max(1, n_target // len(optional_fields))
    picks = []
    remaining_budget = n_target
    for field in optional_fields:
        if remaining_budget <= 0:
            break
        take_n = min(per_field_n, remaining_budget)
        candidates = con.execute(
            f"SELECT ticker, event_date, COUNT(*) AS n_non_null "
            f"FROM filtered_trades WHERE {field} IS NOT NULL "
            f"AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = event_date "
            f"GROUP BY ticker, event_date ORDER BY ticker, event_date"
        ).fetchdf()
        candidates["event_date_str"] = candidates["event_date"].astype(str)
        merged = healthy.merge(
            candidates[["ticker", "event_date_str", "n_non_null"]],
            left_on=["ticker", "event_date_canonical"], right_on=["ticker", "event_date_str"], how="inner",
        )
        if merged.empty:
            continue
        take_n = min(take_n, len(merged))
        idx = rng.choice(len(merged), size=take_n, replace=False)
        sel = merged.iloc[idx].copy()
        sel["targeted_optional_field"] = field
        sel["archive_non_null_count"] = sel["n_non_null"]
        picks.append(sel.drop(columns=["n_non_null", "event_date_str"]))
        remaining_budget -= take_n

    if not picks:
        return pd.DataFrame(columns=list(healthy.columns) + ["targeted_optional_field", "archive_non_null_count"])
    return pd.concat(picks, ignore_index=True)


def main():
    con = duckdb.connect(database=DB_PATH, read_only=True)
    healthy = healthy_population(con)

    rng = np.random.default_rng(CTRL_CFG["seed"])
    stratified = select_stratified(healthy, CTRL_CFG["n_stratified_pairs"], rng)
    stratified["pool"] = "stratified"
    stratified["targeted_optional_field"] = None
    stratified["archive_non_null_count"] = None

    targeted = select_targeted(con, healthy, OPTIONAL_TRADES, CTRL_CFG["n_targeted_optional_field_pairs"], rng)
    targeted["pool"] = "targeted_optional_field"

    con.close()

    combined = pd.concat([stratified, targeted], ignore_index=True)
    out_cols = ["ticker", "event_date_canonical", "folder_name", "momentum_str", "year",
                "n_trades_event_day", "trades_ingested", "quotes_ingested",
                "pool", "targeted_optional_field", "archive_non_null_count"]
    for c in out_cols:
        if c not in combined.columns:
            combined[c] = None
    combined[out_cols].to_parquet(OUT_PATH, index=False)

    print(f"Selected {len(combined)} control pairs ({len(stratified)} stratified + {len(targeted)} targeted)")
    print(combined[out_cols].to_string())


if __name__ == "__main__":
    main()
