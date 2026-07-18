"""
Phase 1b T5 - bivariate outlier flag (trades x momentum).

Fit population: instrument_class IN ('common','common_adr'),
flag_bad_denominator=FALSE, trades_ingested=TRUE (Amendment 2: keys on
trades side only). Quantile regression q=0.995 of log(momentum_pct) on
log(n_trades_event_day), upper tail - same machinery as Phase 1's q05
filter.

n_trades_event_day is NOT "any row tagged with this event's anchor
date" - filtered_trades.event_date is a per-FOLDER tag applied to every
row across the full T-3..T+3 window (confirmed: GTN.A_2024-11-14's
folder has trades spanning 2024-11-08 through 2024-11-19, all tagged
event_date=2024-11-14). n_trades_event_day counts only rows whose
OWN trade timestamp falls on the event's calendar day, derived from
sip_timestamp (ns epoch, UTC). NYSE regular+extended hours (04:00-20:00
ET) map to UTC same-calendar-day for all but a sliver near UTC
midnight; a plain UTC date cast is treated as good enough for this
coarse day-level count, not a precision microstructure measure.
"""
import json

import duckdb
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

CONFIG_PATH = "config/phase_1b.json"
DB_PATH = "data/duckdb/main.duckdb"
OUT_EVENT_FLAGS = "results/phase_1b/artifacts/event_flags.parquet"
OUT_SUMMARY = "results/phase_1b/artifacts/bivariate_outlier_flag_summary.json"


def main():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    q_outlier = cfg["outlier_flags"]["q_outlier"]

    con = duckdb.connect(database=DB_PATH, read_only=False)

    # Fit population: query momentum_events_canonical directly (t2 stage
    # active - has instrument_class, flag_bad_denominator, trades_ingested).
    pop = con.execute(
        """
        SELECT ticker, event_date_canonical, momentum_pct
        FROM momentum_events_canonical
        WHERE instrument_class IN ('common', 'common_adr')
          AND NOT flag_bad_denominator
          AND trades_ingested
        """
    ).fetchdf()
    print(f"fit population (pre n_trades_event_day join): {len(pop)}")

    # n_trades_event_day: single-pass aggregation over filtered_trades,
    # true trading-day match (not just the folder's anchor-date tag).
    print("computing n_trades_event_day over filtered_trades (full scan, one pass)...")
    day_counts = con.execute(
        """
        SELECT ticker, event_date, ROUND(momentum_pct, 2) AS mom_2dp, COUNT(*) AS n_trades_event_day
        FROM filtered_trades
        WHERE CAST(TO_TIMESTAMP(sip_timestamp / 1e9) AS DATE) = event_date
        GROUP BY 1, 2, 3
        """
    ).fetchdf()
    print(f"day_counts rows: {len(day_counts)}")

    pop["mom_2dp"] = pop["momentum_pct"].round(2)
    pop["event_date_str"] = pop["event_date_canonical"].astype(str)
    day_counts["event_date_str"] = day_counts["event_date"].astype(str)

    merged = pop.merge(
        day_counts[["ticker", "event_date_str", "mom_2dp", "n_trades_event_day"]],
        on=["ticker", "event_date_str", "mom_2dp"], how="left",
    )
    merged["n_trades_event_day"] = merged["n_trades_event_day"].fillna(0).astype(int)

    # T5b - zero event-day trades
    zero_trades = merged[merged["n_trades_event_day"] == 0].copy()
    n_zero = len(zero_trades)

    # Fit population for the quantile regression excludes zero-trade events
    # (log(0) undefined) - consistent with Phase 1's q05 fit, which dropped
    # non-positive values before fitting, not silently.
    fit_df = merged[merged["n_trades_event_day"] > 0].copy()
    fit_df["log_mom"] = np.log(fit_df["momentum_pct"])
    fit_df["log_trades"] = np.log(fit_df["n_trades_event_day"])

    mod = smf.quantreg("log_mom ~ log_trades", fit_df)
    res = mod.fit(q=q_outlier)
    fit_df["log_mom_threshold"] = res.predict(fit_df[["log_trades"]])
    fit_df["flag_trades_mom_outlier"] = fit_df["log_mom"] > fit_df["log_mom_threshold"]

    n_flagged = int(fit_df["flag_trades_mom_outlier"].sum())
    n_fit_pop = len(fit_df)
    flagged_pct = 100 * n_flagged / n_fit_pop if n_fit_pop else 0.0

    # Assemble event_flags.parquet: full merged population (incl. zero-trade
    # events, flag_trades_mom_outlier=NULL for those - undefined by the fit)
    merged = merged.merge(
        fit_df[["ticker", "event_date_str", "mom_2dp", "flag_trades_mom_outlier"]],
        on=["ticker", "event_date_str", "mom_2dp"], how="left",
    )
    merged["flag_zero_event_day_trades"] = merged["n_trades_event_day"] == 0
    merged["event_date_canonical"] = merged["event_date_canonical"]

    out_cols = ["ticker", "event_date_canonical", "momentum_pct", "n_trades_event_day",
                "flag_trades_mom_outlier", "flag_zero_event_day_trades"]
    merged[out_cols].to_parquet(OUT_EVENT_FLAGS, index=False)

    summary = {
        "phase": "1b",
        "task": "T5",
        "q_outlier": q_outlier,
        "quantreg_params": {k: float(v) for k, v in res.params.items()},
        "t5a_bivariate_flag": {
            "n_fit_population": n_fit_pop,
            "n_flagged": n_flagged,
            "flagged_pct": round(flagged_pct, 4),
            "design_expectation_pct": 0.5,
            "escalation_threshold_pct": 1.5,
            "escalation_triggered": flagged_pct > 1.5,
        },
        "t5b_zero_event_day_trades": {
            "n_zero_trades_events": n_zero,
            "escalation_threshold": 50,
            "escalation_triggered": n_zero > 50,
            "events": zero_trades[["ticker", "event_date_canonical", "momentum_pct"]].to_dict(orient="records") if n_zero <= 200 else f"{n_zero} rows, see event_flags.parquet",
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
