"""
E1-T3: shares-outstanding x detection-price, two-way. Event counts by
shares-outstanding decile x detection-price decile -- a table, not a product (no market
cap is constructed, per SS1).

Per SS1's caveat, both the raw (as-filed) and split-corrected shares-outstanding deciles
are reported side by side -- this cohort does contain reverse splits (T2's spl_quality
crosstab already shows spl_quality=='observed' for 8,732 events), so the "no reverse
split in this cohort" shortcut does not apply; the correction
(common.add_corrected_shares_outstanding) is used instead.

shs_shares_outstanding is only ~77% covered (shs_quality != 'unavailable') -- per SS4,
the population is not filtered on this. Events with no shares-outstanding figure get no
decile and are reported as their own explicit row/column, never dropped silently.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t3_shares_x_price.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

N_DECILES = C.load_cfg()["deciles"]["n"]


def decile_col(s: pd.Series) -> pd.Series:
    return pd.qcut(s, N_DECILES, labels=False, duplicates="drop")


def main() -> int:
    df = pd.read_parquet(f"{C.ART}/e1_joined.parquet")
    df = C.add_corrected_shares_outstanding(df)

    df["shs_decile_raw"] = decile_col(df["shs_shares_outstanding"])
    df["shs_decile_corrected"] = decile_col(df["shs_shares_outstanding_corrected"])

    def two_way(shs_decile_col: str) -> pd.DataFrame:
        tab = pd.crosstab(
            df[shs_decile_col].map(lambda d: f"S{int(d)}" if pd.notna(d) else "no_shs_data"),
            df["detection_price_decile"].map(lambda d: f"D{int(d)}" if pd.notna(d) else "no_price_data"),
        )
        return tab

    raw_table = two_way("shs_decile_raw")
    corrected_table = two_way("shs_decile_corrected")
    raw_table.to_parquet(f"{C.ART}/t3_two_way_raw.parquet")
    corrected_table.to_parquet(f"{C.ART}/t3_two_way_corrected.parquet")

    n_corrected = int(df["shs_correction_applied"].sum())
    decile_shift = int((df["shs_decile_raw"] != df["shs_decile_corrected"]).sum())

    summary = {
        "task": "E1-T3 shares-outstanding x detection-price, two-way",
        "config_hash": C.cfg_hash(),
        "n_total": len(df),
        "n_with_shs_data": int(df["shs_shares_outstanding"].notna().sum()),
        "n_no_shs_data": int(df["shs_shares_outstanding"].isna().sum()),
        "n_shs_zero_artifact": int(df["shs_zero_artifact"].sum()),
        "n_shs_zero_artifact_note": "shs_shares_outstanding==0.0 exactly (found while building E1-T4, "
            "not a real value for any of these companies) -- these land in the RAW table's S0 (lowest) "
            "decile as filed, but are excluded from the CORRECTED table (shs_shares_outstanding_corrected "
            "is NaN for them, so they fall into corrected's no_shs_data row instead).",
        "n_with_price_data": int(df["detection_price"].notna().sum()),
        "n_split_correction_applied": n_corrected,
        "n_correction_applied_note": "events where the shares-outstanding filing predated the "
            "nearest pre-t0 split, so the raw count needed rescaling by spl_last_split_ratio",
        "n_events_changing_decile_after_correction": decile_shift,
        "raw_table_shape": list(raw_table.shape),
        "corrected_table_shape": list(corrected_table.shape),
    }
    C.write_json(f"{C.ART}/t3_shares_x_price_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
