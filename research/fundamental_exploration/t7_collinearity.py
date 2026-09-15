"""
E1-T7: collinearity map. Association among the fundamental variables, and each of them
against detection price -- how much of the fundamental layer is a price split wearing
different clothes, for the cost of one pass, before anything is built on top of it.

Spearman rank correlation (config.collinearity.continuous_method) over the numeric/
boolean fundamental variables plus detection_price. Booleans (flg_dilution_form_before_t0,
spl_reverse_split_365d) are coerced to 0/1 -- standard and defensible for a rank
correlation. shs_shares_outstanding uses the split-corrected figure
(common.add_corrected_shares_outstanding), per SS1's caveat. Quality enums (flg_quality
etc.) are categorical, not included in this numeric matrix -- association with those
would need a different measure (config.collinearity.categorical_association = cramers_v)
and isn't run here; noted as a gap, not silently skipped.

pandas .corr() uses pairwise-complete observations by default, and coverage varies
sharply across these columns (spl_last_split_ratio ~8% covered vs detection_price 100%)
-- so an n-per-cell matrix is computed alongside the correlation matrix, per the Evidence
Standard ("never post a number without n").

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t7_collinearity.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

VARIABLES = [
    "shs_shares_outstanding_corrected", "shs_lag_ns",
    "flg_lag_ns", "flg_n_filings_24h", "flg_n_filings_72h", "flg_dilution_form_before_t0_num",
    "spl_n_splits_365d", "spl_reverse_split_365d_num", "spl_last_split_ratio",
    "si_shares_short", "si_lag_ns",
    "detection_price",
]


def main() -> int:
    df = pd.read_parquet(f"{C.ART}/e1_joined.parquet")
    df = C.add_corrected_shares_outstanding(df)
    df["flg_dilution_form_before_t0_num"] = df["flg_dilution_form_before_t0"].astype("Int64")
    df["spl_reverse_split_365d_num"] = df["spl_reverse_split_365d"].astype("Int64")

    sub = df[VARIABLES].apply(pd.to_numeric, errors="coerce")

    corr = sub.corr(method="spearman")
    n_pairs = pd.DataFrame(
        [[int(sub[[a, b]].dropna().shape[0]) for b in VARIABLES] for a in VARIABLES],
        index=VARIABLES, columns=VARIABLES,
    )

    corr.to_parquet(f"{C.ART}/t7_spearman_corr.parquet")
    n_pairs.to_parquet(f"{C.ART}/t7_spearman_n.parquet")

    # flag pairs with n below the display floor -- reported, not hidden.
    floor = C.load_cfg()["min_cell_n_display_floor"]
    thin_pairs = [
        {"a": a, "b": b, "n": int(n_pairs.loc[a, b])}
        for a in VARIABLES for b in VARIABLES
        if a < b and n_pairs.loc[a, b] < floor
    ]

    # detection_price row specifically, sorted by |rho| -- "is the fundamental layer
    # mostly restating price" is the point of this task.
    price_row = corr["detection_price"].drop("detection_price").sort_values(
        key=lambda s: s.abs(), ascending=False
    )

    summary = {
        "task": "E1-T7 collinearity map",
        "config_hash": C.cfg_hash(),
        "variables": VARIABLES,
        "n_total": len(df),
        "gap_note": "categorical quality enums (flg_quality, shs_quality, si_quality, spl_quality) "
                    "are not in this numeric Spearman matrix -- a categorical-association measure "
                    "(config.collinearity.categorical_association = cramers_v) was not run here.",
        "n_shs_zero_artifact_excluded": int(df["shs_zero_artifact"].sum()),
        "n_shs_zero_artifact_note": "shs_shares_outstanding==0.0 exactly (E1-T4 finding) is set to NaN in "
            "shs_shares_outstanding_corrected by common.py -- excluded here via pairwise dropna, not "
            "included as a real low value.",
        "spearman_vs_detection_price": {k: float(v) for k, v in price_row.items()},
        "n_vs_detection_price": {k: int(n_pairs.loc[k, "detection_price"]) for k in price_row.index},
        "thin_pairs_below_display_floor": thin_pairs,
        "min_cell_n_display_floor": floor,
    }
    C.write_json(f"{C.ART}/t7_collinearity_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
