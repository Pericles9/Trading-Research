"""
E2-T6 scatter/strip chart data prep: persists per-event raw values (not the cell
aggregates e2_t6_fundamentals_vs_duration.py's own main() writes) for the continuous
fundamentals (shares outstanding, filing lag) and categorical splits (dilution flag,
reverse-split flag, si_quality) against duration_min, plus detection_price
(continuous), censored, and year. Reuses build_frame() from that module and SPLITS
from e2_t5_fundamentals_vs_momentum.py (same source that module itself imports)
verbatim -- no logic re-derived here.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t6_scatter_data.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402
from research.fundamental_exploration.e2_t5_fundamentals_vs_momentum import SPLITS  # noqa: E402
from research.fundamental_exploration.e2_t6_fundamentals_vs_duration import build_frame  # noqa: E402


def main() -> int:
    df = build_frame()
    out = df[[
        "event_id", "year", "duration_min", "censored", "detection_price", "detection_price_decile",
        "shs_shares_outstanding_corrected", "flg_lag_days",
    ]].copy()
    out["split_dilution"] = SPLITS["flg_dilution_form_before_t0"](df)
    out["split_reverse_split"] = SPLITS["spl_reverse_split_365d"](df)
    out["split_si_quality"] = SPLITS["si_quality"](df)
    path = f"{C.ART_E2}/e2_t6_scatter_events.parquet"
    out.to_parquet(path, index=False)
    print(f"wrote {path} rows={len(out):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
