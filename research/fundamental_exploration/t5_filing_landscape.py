"""
E1-T5: filing proximity landscape. Form-type mix of the nearest prior filing,
time-since-filing distribution, dilution-flag rate by year and by detection-price
decile. Descriptive only -- no continuation measure, no outcome crossing.

flg_quality (research/fundamentals_f1/t3_filing_index.py:237-239) is already a clean
three-way split -- "observed" (cik resolved, a nearest filing found), "no_filings_in_window"
(cik resolved, no filing found in SEC's daily-index date range, 2020-01-01 on), "unavailable"
(no cik at all). Unlike spl_quality (E1-T2), this one does not conflate a real zero with a
true gap -- so the dilution rate below is computed over quality != 'unavailable' (both
"observed" and "no_filings_in_window" are informative), and each denominator is reported
alongside its excluded 'unavailable' share, never silently.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t5_filing_landscape.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

MIN_CELL_N = C.load_cfg()["min_cell_n_display_floor"]


def main() -> int:
    joined = pd.read_parquet(f"{C.ART}/e1_joined.parquet")
    joined = C.add_identity_fields(joined)

    # 1. form-type mix of the nearest prior filing (flg_quality == 'observed' only --
    # flg_last_form is NaN by construction otherwise).
    observed = joined[joined["flg_quality"] == "observed"]
    form_mix = observed["flg_last_form"].value_counts().reset_index()
    form_mix.columns = ["flg_last_form", "n"]
    form_mix.to_parquet(f"{C.ART}/t5_form_mix.parquet", index=False)

    # 2. time-since-filing (flg_lag_ns -> days), observed only.
    lag_days = (observed["flg_lag_ns"] / 86_400e9).rename("flg_lag_days")
    lag_days.to_frame().to_parquet(f"{C.ART}/t5_lag_days.parquet", index=False)

    # 3. dilution-flag rate by year x detection_price_decile, over flg_quality != 'unavailable'.
    informative = joined[joined["flg_quality"] != "unavailable"].copy()
    grp = informative.groupby(["year", "detection_price_decile"], observed=True)
    rate_table = grp["flg_dilution_form_before_t0"].agg(["mean", "count"]).reset_index()
    rate_table.columns = ["year", "detection_price_decile", "dilution_rate", "n"]
    rate_table["display_suppressed"] = rate_table["n"] < MIN_CELL_N

    # excluded-unavailable share per (year, decile) cell, reported alongside the rate.
    n_total_by_cell = joined.groupby(["year", "detection_price_decile"], observed=True).size()
    n_unavail_by_cell = joined[joined["flg_quality"] == "unavailable"].groupby(
        ["year", "detection_price_decile"], observed=True
    ).size()
    rate_table = rate_table.set_index(["year", "detection_price_decile"])
    rate_table["n_total_cell"] = n_total_by_cell
    rate_table["n_unavailable_cell"] = n_unavail_by_cell.reindex(n_total_by_cell.index).fillna(0).astype(int)
    rate_table = rate_table.reset_index()
    rate_table.to_parquet(f"{C.ART}/t5_dilution_rate_by_year_decile.parquet", index=False)

    summary = {
        "task": "E1-T5 filing proximity landscape",
        "config_hash": C.cfg_hash(),
        "n_total": len(joined),
        "n_observed": int((joined["flg_quality"] == "observed").sum()),
        "n_no_filings_in_window": int((joined["flg_quality"] == "no_filings_in_window").sum()),
        "n_unavailable": int((joined["flg_quality"] == "unavailable").sum()),
        "top_5_forms": form_mix.head(5).to_dict("records"),
        "flg_lag_days_summary": {
            "n": int(lag_days.notna().sum()),
            "p10": float(lag_days.quantile(0.10)), "p50": float(lag_days.quantile(0.50)),
            "p90": float(lag_days.quantile(0.90)), "max": float(lag_days.max()),
        },
        "min_cell_n_display_floor": MIN_CELL_N,
        "n_cells_suppressed": int(rate_table["display_suppressed"].sum()),
        "n_cells_total": len(rate_table),
    }
    C.write_json(f"{C.ART}/t5_filing_landscape_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
