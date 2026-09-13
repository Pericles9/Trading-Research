"""
Phase 13, T3: fundamental partitions, within-year, within-price-decile, exploratory.

Three splits. Per Cooper's 2026-09-13 amendment: T3a keeps the direction the signed-off
proposal pre-registered; T3b/T3c run undirected. No kill condition anywhere -- this
script reports distributions and never declares a split as having "cleared,"
"passed," or being "the finding." (Escalation rows 2/3, prompts/phase_13.md SS5.)

Cross-cuts follow config.cross_cuts exactly: nested within event year (coverage is
collinear with the vendor calendar cliff, F1-T6c) and within the full price DECILE
T2 already established as arm zero's control -- not a coarser tercile. A cell below
config.cross_cuts.min_cell_n_log_threshold (200) is flagged, not silently reported
as if it had the same statistical weight as a well-populated cell.

T3b (share turnover) construction: event-day tick volume (event_minute_bars_v2,
session_offset=0, all segments) / split-adjusted shares outstanding. Split-adjustment:
shs_shares_outstanding is corrected by spl_last_split_ratio when spl_last_split_ns
falls strictly between shs_asof_ns and t0_ns (a split happened after the share count
was stated but before the event) -- both already-guaranteed-ordered columns from
Build F1's own Verification Block, not re-derived from raw splits history.

Usage: .venv/Scripts/python.exe research/phase_13/t3_partitions.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.phase_13 import common as C  # noqa: E402

HORIZONS = [5, 15, 30, 60]
OUT_PATH = f"{C.ART}/t3_partition_summary.json"


def describe(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.median()), "p75": float(s.quantile(0.75)), "p90": float(s.quantile(0.90)),
        "mean": float(s.mean()),
    }


def build_turnover(ef: pd.DataFrame) -> pd.Series:
    con = C.connect(read_only=True)
    keys = pd.read_parquet("results/fundamentals_f1/artifacts/ticker_identity.parquet",
                            columns=["event_id", "ticker", "event_date_canonical", "momentum_pct"])
    con.register("keys", keys)
    vol = con.execute("""
        SELECT k.event_id, SUM(b.volume) AS event_day_volume
        FROM keys k
        JOIN main_db.event_minute_bars_v2 b
          ON k.ticker = b.ticker AND k.event_date_canonical = b.event_date_canonical
          AND k.momentum_pct = b.momentum_pct AND b.session_offset = 0
        GROUP BY k.event_id
    """).df()
    df = ef[["event_id", "shs_shares_outstanding", "shs_asof_ns",
             "spl_last_split_ratio", "spl_last_split_ns"]].merge(vol, on="event_id", how="left")
    split_after_shs = (
        df["spl_last_split_ns"].notna() & df["shs_asof_ns"].notna()
        & (df["spl_last_split_ns"] > df["shs_asof_ns"])
    )
    adjusted_shares = df["shs_shares_outstanding"].where(
        ~split_after_shs, df["shs_shares_outstanding"] * df["spl_last_split_ratio"]
    )
    turnover = df["event_day_volume"] / adjusted_shares
    print(f"share turnover: {split_after_shs.sum()} events needed split-adjustment; "
          f"{turnover.notna().sum()}/{len(df)} events have a defined turnover value")
    return pd.Series(turnover.values, index=df["event_id"].values, name="turnover")


def cross_cut(df: pd.DataFrame, split_col: str, horizon: int, min_cell_n: int) -> list[dict]:
    rows = []
    for (year, decile), g in df.groupby(["event_year", "detection_price_decile"], observed=True):
        for split_val, gg in g.groupby(split_col, observed=True, dropna=True):
            mfe = describe(gg[f"mfe_cost_mult_{horizon}"])
            mae = describe(gg[f"mae_cost_mult_{horizon}"])
            rows.append({
                "year": year, "price_decile": int(decile), "split_value": bool(split_val),
                "mfe_cost_mult": mfe,
                "mae_cost_mult": mae,
                "below_min_cell_n": mfe.get("n", 0) < min_cell_n,
            })
    return rows


SPLITS = {
    "t3a_flg_dilution_form_before_t0": "flg_dilution_form_before_t0",
    "t3b_high_turnover_above_median": "t3b_high_turnover",
    "t3c_spl_reverse_split_365d": "spl_reverse_split_365d",
}


def build_df() -> tuple[pd.DataFrame, dict]:
    """Rebuilds T3's merged, gated dataframe. Shared by main() and the Verification
    Block so the verify step re-derives the same object, not just re-parses its JSON."""
    ef = pd.read_parquet(f"{C.FUNDAMENTALS_ROOT}/event_fundamentals.parquet")
    p0 = pd.read_parquet(f"{C.ART}/p0_outcome.parquet")
    ctx = pd.read_parquet("results/fundamentals_f1/artifacts/t6_context.parquet",
                           columns=["event_id", "detection_price_decile"])

    turnover = build_turnover(ef)
    median_turnover = turnover.median()
    t3b_high = (turnover > median_turnover).astype(object).rename("t3b_high_turnover")
    t3b_high[turnover.isna()] = None  # undefined turnover is unknown, not "below median"

    # flg_/spl_ boolean columns default to False when quality is 'unavailable' -- confirmed by
    # direct crosstab: flg_quality='unavailable' (248 rows) and spl_quality='unavailable'
    # (12,219 rows, 58% of the population) both carry flag=False with zero exceptions. Folding
    # "we don't know" into the "no dilution"/"no reverse split" bucket would make T3a/T3c splits
    # on unknown coverage, not on the fundamental. Gate each split to its own quality-known rows;
    # excluded events are reported, not silently dropped.
    flg_known = ef["flg_quality"].isin(["observed", "no_filings_in_window"])
    spl_known = ef["spl_quality"] == "observed"
    ef_gated = ef[["event_id", "flg_dilution_form_before_t0", "spl_reverse_split_365d"]].astype(
        {"flg_dilution_form_before_t0": object, "spl_reverse_split_365d": object}
    )
    ef_gated.loc[~flg_known, "flg_dilution_form_before_t0"] = None
    ef_gated.loc[~spl_known, "spl_reverse_split_365d"] = None

    df = p0.merge(ctx, on="event_id", how="left")
    df = df.merge(ef_gated, on="event_id", how="left")
    df = df.merge(t3b_high, left_on="event_id", right_index=True, how="left")
    df["event_year"] = df["event_id"].str.extract(r"_(\d{4})-\d{2}-\d{2}_")[0]

    meta = {
        "median_turnover": float(median_turnover),
        "n_excluded_flg": int((~flg_known).sum()),
        "n_excluded_spl": int((~spl_known).sum()),
        "n_excluded_turnover": int(turnover.isna().sum()),
    }
    return df, meta


def main():
    df, meta = build_df()
    cfg = C.load_cfg()
    min_cell_n = cfg["cross_cuts"]["min_cell_n_log_threshold"]
    splits = SPLITS

    summary = {
        "median_turnover_used_for_t3b_split": meta["median_turnover"],
        "n_total": len(df),
        "quality_gating": {
            "t3a_excluded_unknown_flg_quality": meta["n_excluded_flg"],
            "t3c_excluded_unknown_spl_quality": meta["n_excluded_spl"],
            "t3b_excluded_undefined_turnover": meta["n_excluded_turnover"],
            "note": "flg_/spl_ boolean columns default False when quality is 'unavailable' -- "
                    "those rows are excluded from that split entirely (set to unknown), not "
                    "counted as the 'no' side.",
        },
        "splits": {},
        "note": "Exploratory, no kill condition, no pass/fail declaration -- per Cooper's 2026-09-13 "
                "amendment. T3a's direction was pre-registered upstream (worse continuation with a "
                "dilution filing); T3b/T3c are undirected, both tails reported without comment.",
        "config_hash": C.cfg_hash(),
    }
    n_sparse_cells = {}
    for name, col in splits.items():
        summary["splits"][name] = {
            f"horizon_{h}": cross_cut(df, col, h, min_cell_n) for h in HORIZONS
        }
        vc = df[col].value_counts(dropna=False).to_dict()
        summary["splits"][name]["overall_value_counts"] = {str(k): int(v) for k, v in vc.items()}
        n_sparse_cells[name] = sum(
            1 for h in HORIZONS for r in summary["splits"][name][f"horizon_{h}"] if r["below_min_cell_n"]
        )
    summary["quality_gating"]["n_cells_below_min_cell_n_by_split"] = n_sparse_cells
    summary["quality_gating"]["min_cell_n_log_threshold"] = min_cell_n

    C.write_json(OUT_PATH, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "splits"}, indent=2))
    for name in splits:
        print(f"\n{name}: {summary['splits'][name]['overall_value_counts']}")


if __name__ == "__main__":
    main()
