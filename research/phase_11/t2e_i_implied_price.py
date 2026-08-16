"""T2e-i - implied-price decomposition (Amendment 2 A2-6, execution step 1).

Retrospective on committed Stage A output. No new computation over tick data.

A quoted spread expressed in basis points and in cents carries the price between
them:  spread_bp = 10000 * spread_dollars / mid  =>  mid = 100 * spread_cents / spread_bp.

Description only. States that bp falls while cents does not, and that implied
price rises. No characterisation of what that is good or bad for.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

A = "results/phase_11/artifacts/"
SEGS = ["premarket", "rth", "post"]
OFFS = [-3, -1, 0]


def main() -> None:
    d = pd.read_parquet(A + "t2e_quoted_spread.parquet")
    d["cents"] = d.tw_spread_dollars * 100.0
    # Per-event implied price, then the median - avoids the ratio-of-medians trap.
    d["implied_price"] = 100.0 * d.cents / d.tw_spread_bp

    out = {
        "task": "T2e-i", "phase": "11", "date": "2026-08-16",
        "authority": "prompts/phase_11_amendment_2.md A2-6 (D19)",
        "nature": "Retrospective on committed Stage A output. No new computation over "
                  "tick data, no pass spent.",
        "arithmetic": {
            "identity": "spread_bp = 10000 * spread_dollars / mid",
            "rearranged": "mid = 10000 * spread_dollars / spread_bp = 100 * spread_cents "
                          "/ spread_bp",
            "worked_example_rth_t0": "100 * 3.79 cents / 83.92 bp = $4.52",
            "worked_example_rth_tm3": "100 * 3.64 cents / 165.01 bp = $2.21",
        },
        "per_segment": {},
    }

    for seg in SEGS:
        s = d[d.segment == seg]
        rows = {}
        for off in OFFS:
            x = s[s.day_offset == off]
            med_bp = float(x.tw_spread_bp.median())
            med_cents = float(x.cents.median())
            rows[f"T{off}"] = {
                "n_events": int(len(x)),
                "median_spread_bp": round(med_bp, 2),
                "median_spread_cents": round(med_cents, 2),
                "implied_price_from_medians": round(100.0 * med_cents / med_bp, 3),
                "median_of_per_event_implied_price": round(
                    float(x.implied_price.median()), 3),
            }
        b0, b3 = rows["T0"]["median_spread_bp"], rows["T-3"]["median_spread_bp"]
        c0, c3 = rows["T0"]["median_spread_cents"], rows["T-3"]["median_spread_cents"]
        p0, p3 = (rows["T0"]["median_of_per_event_implied_price"],
                  rows["T-3"]["median_of_per_event_implied_price"])
        rows["change_T-3_to_T0"] = {
            "spread_bp_pct": round(100.0 * (b0 - b3) / b3, 1),
            "spread_cents_pct": round(100.0 * (c0 - c3) / c3, 1),
            "implied_price_pct": round(100.0 * (p0 - p3) / p3, 1),
        }
        out["per_segment"][seg] = rows

    out["two_estimators_note"] = (
        "Two implied-price columns are reported. 'implied_price_from_medians' divides the "
        "median cents figure by the median bp figure - this is the arithmetic A2-6 shows, "
        "and it is a ratio of medians. 'median_of_per_event_implied_price' computes the "
        "price per event first and then takes the median, which is the estimator the "
        "'ratio computed per event, then distributed' rule prefers. Both are given so the "
        "difference between them is visible rather than hidden.")

    r = out["per_segment"]["rth"]
    out["what_the_numbers_show"] = (
        f"RTH: median quoted spread goes {r['T-3']['median_spread_bp']} -> "
        f"{r['T-1']['median_spread_bp']} -> {r['T0']['median_spread_bp']} bp across "
        f"T-3 / T-1 / T=0 ({r['change_T-3_to_T0']['spread_bp_pct']}%), while the same "
        f"cells in cents go {r['T-3']['median_spread_cents']} -> "
        f"{r['T-1']['median_spread_cents']} -> {r['T0']['median_spread_cents']} "
        f"({r['change_T-3_to_T0']['spread_cents_pct']}%). Median per-event implied price "
        f"goes ${r['T-3']['median_of_per_event_implied_price']} -> "
        f"${r['T-1']['median_of_per_event_implied_price']} -> "
        f"${r['T0']['median_of_per_event_implied_price']} "
        f"({r['change_T-3_to_T0']['implied_price_pct']}%). n = 50 events at every point. "
        f"The basis-point figure falls; the cents figure does not; the implied price "
        f"rises.")

    pathlib.Path(A + "t2e_i_implied_price.json").write_text(json.dumps(out, indent=2))
    print("wrote t2e_i_implied_price.json\n")
    for seg in SEGS:
        r = out["per_segment"][seg]
        print(f"-- {seg}")
        for k in ["T-3", "T-1", "T0"]:
            v = r[k]
            print(f"   {k:4s} n={v['n_events']:2d}  bp={v['median_spread_bp']:>8.2f}  "
                  f"cents={v['median_spread_cents']:>7.2f}  "
                  f"implied ${v['implied_price_from_medians']:>7.3f} (from medians)  "
                  f"${v['median_of_per_event_implied_price']:>7.3f} (per-event median)")
        ch = r["change_T-3_to_T0"]
        print(f"   T-3->T0: bp {ch['spread_bp_pct']:+.1f}%  cents "
              f"{ch['spread_cents_pct']:+.1f}%  implied price "
              f"{ch['implied_price_pct']:+.1f}%")


if __name__ == "__main__":
    main()
