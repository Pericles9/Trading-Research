"""
Phase 1c T3 - select 20 control (ticker, session) pairs that already exist,
correctly, in the archive. Stratified across years 2020-2025 and across
event-day trade-count terciles (computed over the healthy population),
seed from config. Event days only, both sides fetched where quote coverage
exists. Population: in-scope-eligible (common/common_adr, not
bad-denominator, not trades_mom_outlier - i.e. present in event_flags.parquet)
AND healthy (neither flag_missing_event_day nor flag_window_calendar_bug) AND
trades_ingested=TRUE - these are events this phase asserts are already
correctly and completely archived, the trust-gate's reference population.
"""
import json

import duckdb
import numpy as np
import pandas as pd

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

EVENT_FLAGS = CFG["paths"]["event_flags"]
FOLDER_INV = CFG["paths"]["folder_inventory_v2"]
OUT_PATH = "results/phase_1c/artifacts/control_pairs.parquet"
CTRL_CFG = CFG["control_fetch"]


def main():
    con = duckdb.connect(read_only=False)
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

    healthy["trade_count_tercile"] = pd.qcut(
        healthy["n_trades_event_day"], 3, labels=["low", "mid", "high"]
    )

    rng = np.random.default_rng(CTRL_CFG["seed"])
    cells = healthy.groupby(["year", "trade_count_tercile"], observed=True)
    picks = []
    for _, group in cells:
        if len(group) == 0:
            continue
        idx = rng.integers(0, len(group))
        picks.append(group.iloc[idx])

    picked = pd.DataFrame(picks)
    n_target = CTRL_CFG["n_pairs"]
    if len(picked) > n_target:
        keep_idx = rng.choice(len(picked), size=n_target, replace=False)
        picked = picked.iloc[sorted(keep_idx)]
    elif len(picked) < n_target:
        remaining = healthy[~healthy.index.isin(picked.index)]
        extra_n = n_target - len(picked)
        extra_idx = rng.choice(len(remaining), size=min(extra_n, len(remaining)), replace=False)
        picked = pd.concat([picked, remaining.iloc[extra_idx]], ignore_index=True)

    picked = picked.reset_index(drop=True)
    out_cols = ["ticker", "event_date_canonical", "folder_name", "momentum_str",
                "year", "trade_count_tercile", "n_trades_event_day",
                "trades_ingested", "quotes_ingested"]
    picked[out_cols].to_parquet(OUT_PATH, index=False)

    print(f"Selected {len(picked)} control pairs")
    print(picked[["ticker", "event_date_canonical", "year", "trade_count_tercile", "n_trades_event_day", "quotes_ingested"]].to_string())


if __name__ == "__main__":
    main()
