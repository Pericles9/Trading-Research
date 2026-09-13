"""
Build F1, F1-T6: coverage report. Gate -- stop, tag, post. Offline, no network call.

Per the Chart Contract, distribution comes before aggregate everywhere below: every
cross-cut is reported as counts per cell, never a bare percentage.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t6_coverage_report.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

GROUPS = ["flg", "shs", "fin", "si", "spl"]
OUT_JSON = f"{C.ART}/t6_coverage_report.json"


def covered(df: pd.DataFrame, group: str) -> pd.Series:
    return df[f"{group}_quality"] != "unavailable"


def cross_cut(df: pd.DataFrame, by: str) -> dict:
    out = {}
    for group in GROUPS:
        cov = covered(df, group)
        tab = df.groupby(by, observed=True).apply(
            lambda g: pd.Series({"n": len(g), "n_covered": int(covered(g, group).sum())}),
            include_groups=False,
        )
        tab["share_covered"] = tab["n_covered"] / tab["n"]
        out[group] = tab.reset_index().to_dict(orient="records")
    return out


def main():
    ef = pd.read_parquet(f"{C.NORMALIZED_ROOT}/event_fundamentals.parquet")
    ctx = pd.read_parquet(f"{C.ART}/t6_context.parquet")
    df = ef.merge(ctx, on="event_id", how="left", suffixes=("", "_ctx"))
    df["year"] = df["event_id"].str.extract(r"_(\d{4})-\d{2}-\d{2}_")[0]

    n_total = len(df)
    overall = {g: {"n_covered": int(covered(df, g).sum()), "share": float(covered(df, g).mean())} for g in GROUPS}

    by_year = cross_cut(df, "year")
    by_decile = cross_cut(df, "detection_price_decile")
    by_delisted = cross_cut(df, "delisted_status")
    by_exchange = cross_cut(df, "primary_exchange")

    # F1-T6c: is coverage missing at random? Compare fin_ coverage in the cheapest price decile
    # (0, lowest) vs the most expensive (9, highest) and delisted vs active, as the direct test.
    fin_cov_by_decile = {r["detection_price_decile"]: r["share_covered"] for r in by_decile["fin"]}
    fin_cov_by_delisted = {r["delisted_status"]: r["share_covered"] for r in by_delisted["fin"]}
    mar_test = {
        "fin_coverage_cheapest_decile_0": fin_cov_by_decile.get(0.0),
        "fin_coverage_priciest_decile_9": fin_cov_by_decile.get(9.0),
        "fin_coverage_active": fin_cov_by_delisted.get("active"),
        "fin_coverage_delisted": fin_cov_by_delisted.get("delisted"),
        "missing_at_random_plausible": None,  # stated in prose below, not silently inferred as a bool
    }

    report = {
        "n_total_events": n_total,
        "overall_coverage": overall,
        "by_year": by_year,
        "by_detection_price_decile": by_decile,
        "by_delisted_status": by_delisted,
        "by_exchange": by_exchange,
        "missing_at_random_check": mar_test,
        "config_hash": C.cfg_hash(),
    }
    C.write_json(OUT_JSON, report)
    print(json.dumps({"n_total_events": n_total, "overall_coverage": overall, "missing_at_random_check": mar_test},
                      indent=2, default=str))
    print("\nfin_ coverage by year:")
    for r in by_year["fin"]:
        print(f"  {r['year']}: n={r['n']}, covered={r['n_covered']} ({r['share_covered']:.1%})")
    print("\nfin_ coverage by delisted status:")
    for r in by_delisted["fin"]:
        print(f"  {r['delisted_status']}: n={r['n']}, covered={r['n_covered']} ({r['share_covered']:.1%})")


if __name__ == "__main__":
    main()
