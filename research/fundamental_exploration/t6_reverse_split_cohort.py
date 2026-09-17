"""
E1-T6: reverse-split cohort. Everything above (T1-T5, T7), split by
spl_reverse_split_365d -- one flag, no construction, per the brief. Read literally as
"re-render every prior chart twice" this would just double the file count without
adding a comparison; instead this produces the comparison itself, cohort vs cohort, for
the variables T1-T5/T7 already established as the interesting ones: detection price,
shares outstanding, event volume, turnover, dilution rate, and per-group coverage.

spl_reverse_split_365d (bool_or(ratio<1) within 365d before t0, filled False when no
split matches, research/fundamentals_f1/t5_assemble.py:173/179) is a clean boolean,
always defined -- unlike spl_quality (E1-T2's finding), there is no zero/unavailable
conflation to work around here.

**A second, broader share-count problem, found here.** The exact-shs_shares_outstanding
==0.0 fix (common.py) only catches a literal zero. Sorting the corrected column's
smallest nonzero values turns up 1, 1, 1, 12, 12, 17, 100 (x9), 1000 (x6), 1440 (x9) --
implausible totals for real, actively-traded companies (one of them, LAES, trades ~79M
shares against a filed count of 100). There is no clean gap in the distribution
separating these from genuinely small legitimate microcap counts, so -- unlike the
exact-zero case -- this is reported as a diagnostic (n below a stated round threshold,
plus the concrete worst offenders), NOT excluded from any computation. Turnover's mean
is the statistic this actually distorts (up to 790,351x for one event); median/IQR are
far more robust and are what the chart's box already foregrounds. Raw (subsampled,
disclosed) points are added behind each box below so the tail is visible, not just
implied by a mean.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t6_reverse_split_cohort.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

GROUPS = ["flg", "shs", "si", "spl"]
STRIP_CAP = C.load_cfg()["subsampling"]["strip_overlay_cap"]
STRIP_SEED = C.load_cfg()["subsampling"]["seed"]


def stats(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)), "mean": float(s.mean()), "max": float(s.max()), "min": float(s.min()),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.quantile(0.50)), "p75": float(s.quantile(0.75)),
        "p90": float(s.quantile(0.90)),
    }


def subsample_raw(s: pd.Series) -> list[float]:
    s = s.dropna()
    if len(s) > STRIP_CAP:
        s = s.sample(STRIP_CAP, random_state=STRIP_SEED)
    return s.astype(float).tolist()


def main() -> int:
    df = pd.read_parquet(f"{C.ART}/e1_joined.parquet")
    tape = pd.read_parquet(f"{C.ART}/tape_metrics.parquet")
    df = df.merge(tape, on="event_id", how="left")
    df = C.add_corrected_shares_outstanding(df)
    df = C.add_identity_fields(df)
    df["turnover_lower_bound"] = df["volume_shares"] / df["shs_shares_outstanding_corrected"]

    cohorts = {"reverse_split_365d_true": df[df["spl_reverse_split_365d"]],
               "reverse_split_365d_false": df[~df["spl_reverse_split_365d"]]}

    raw_samples = {"detection_price": {}, "shs_shares_outstanding_corrected": {},
                   "volume_shares": {}, "turnover_lower_bound": {}}
    result = {}
    for name, cdf in cohorts.items():
        cdf = cdf.copy()
        cdf["flg_lag_ns_days"] = cdf["flg_lag_ns"] / 86_400e9
        result[name] = {
            "n": len(cdf),
            "detection_price": stats(cdf["detection_price"]),
            "shs_shares_outstanding_corrected": stats(cdf["shs_shares_outstanding_corrected"]),
            "volume_shares": stats(cdf["volume_shares"]),
            "turnover_lower_bound": stats(cdf["turnover_lower_bound"]),
            "flg_lag_ns_days": stats(cdf["flg_lag_ns_days"]),
            "dilution_rate": {
                "n": int((cdf["flg_quality"] != "unavailable").sum()),
                "rate": float(cdf.loc[cdf["flg_quality"] != "unavailable", "flg_dilution_form_before_t0"].mean())
                if (cdf["flg_quality"] != "unavailable").sum() else None,
            },
            "coverage": {
                g: float((cdf[f"{g}_quality"] != "unavailable").mean()) for g in GROUPS
            },
            "n_shs_share_count_suspect": int(cdf["shs_share_count_suspect"].sum()),
        }
        for metric in raw_samples:
            raw_samples[metric][name] = subsample_raw(cdf[metric])

    worst_offenders = df.dropna(subset=["turnover_lower_bound"]).nlargest(
        8, "turnover_lower_bound"
    )[["event_id", "volume_shares", "shs_shares_outstanding", "shs_quality", "turnover_lower_bound"]]

    C.write_json(f"{C.ART}/t6_reverse_split_cohort.json", {
        "task": "E1-T6 reverse-split cohort comparison",
        "config_hash": C.cfg_hash(),
        "n_total": len(df),
        "cohorts": result,
        "share_count_suspect_note": {
            "threshold": C.SHARE_COUNT_SUSPECT_THRESHOLD,
            "threshold_note": "descriptive diagnostic only, never a filter -- see module docstring. "
                "No clean gap separates these from legitimate small microcap counts; this is a round, "
                "stated cutoff, not a data-driven boundary.",
            "n_total_below_threshold": int(df["shs_share_count_suspect"].sum()),
            "worst_offenders": worst_offenders.to_dict("records"),
        },
        "raw_samples_note": f"subsampled at n<={STRIP_CAP} per cohort per metric (seed={STRIP_SEED}) "
                            "for the chart's strip overlay -- full n is in each metric's own stats block above.",
        "raw_samples": raw_samples,
    })
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
