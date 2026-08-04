"""
Phase 9 T4 - axis separation grid.

Phase 8 §19 confounded detection time-of-day with holding period, and its
latency claim confounded latency with holding period: a later entry on a fixed
EXIT is a shorter hold, so "latency costs nothing" and "holding longer costs
nothing" were the same measurement. This rebuilds the grid with holding period
as an explicit independent axis.

T4a fixed-horizon grid: entry = det + latency, exit = entry + hold.
     latency in {0,1,5,15,30} x hold in {5,15,30,60,120} x det_bin x era.
     Hold length is held constant along the latency axis, so the two are
     separated. Cells with n < 100 are marked thin and carry no claim
     (escalation row 11 - the chart hatches them).

T4b fixed-exit grid: entry = det + latency, exit = t0_close. This is the only
     axis where latency is unconfounded by hold length, and it is the one that
     is NOT a clean latency measurement in the other direction - the hold
     shortens as latency grows. Both readings are reported; the full
     distribution per latency ships, not just the median.

T4c n attrition across the latency axis is reported per cell, so a change in a
     statistic can be separated from a change in sample composition.

All prices are last trade at/before the target minute on T0 (the Phase 8
convention), from event_minute_bars_v2 via ASOF. Entry prices are recomputed
here and cross-checked against Phase 8's frozen det_price_lat* columns before
anything is read off the grid.

det+0 is a physical impossibility and is carried only as the upper bound of
the ladder; it is labelled as such on every chart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.phase_9 import common as C

OUT_PARQUET = f"{C.ART}/t4_axis_grid.parquet"
OUT_JSON = f"{C.ART}/t4_axis_summary.json"
THIN_N = 100
DET_BINS = ["premarket", "0930-1000", "1000-1100", "1100-1300", "after_1300"]


def main():
    cfg = C.load_cfg()
    lats = cfg["latencies"]
    holds = cfg["hold_minutes"]
    tlo, thi = cfg["trim_ratio_bounds"]

    con = C.connect()
    d1 = C.d1_frame()
    wide = C.closes_wide(con, d1)          # also creates temp p9bars
    det = C.detection_anchors()
    det["mp"] = det["mp"].round(2)

    uni = det[~det["det_undefined"].astype(bool)].copy()
    uni = uni.merge(wide[C.KEY + ["last_mi_t0", "close_t0"]], on=C.KEY, how="left")
    uni["era"] = C.era_of(uni["event_date_canonical"])
    n_uni = len(uni)
    print(f"detection universe: {n_uni:,}")

    # ---------- targets: entries and exits on T0 ----------
    tr = []
    for lat in lats:
        base = uni[C.KEY].copy()
        base["latency"] = lat
        base["hold"] = -1                       # -1 marks the entry row
        base["target_minute"] = uni["det_minute"].values + lat
        tr.append(base)
        for hold in holds:
            b = uni[C.KEY].copy()
            b["latency"] = lat
            b["hold"] = hold
            b["target_minute"] = uni["det_minute"].values + lat + hold
            tr.append(b)
    T = pd.concat(tr, ignore_index=True)
    T["session_offset"] = 0
    con.register("targets", T)

    priced = con.execute("""
        SELECT t.ticker, t.event_date_canonical, t.mp, t.latency, t.hold,
               t.target_minute, b.last_price AS price
        FROM targets t
        ASOF LEFT JOIN p9bars b
          ON t.ticker = b.ticker AND t.event_date_canonical = b.event_date_canonical
         AND t.mp = b.mp AND t.session_offset = b.session_offset
         AND t.target_minute >= b.minute_index
    """).fetchdf()
    priced["event_date_canonical"] = pd.to_datetime(priced["event_date_canonical"])
    print(f"priced targets: {len(priced):,}")

    entries = priced[priced.hold == -1][C.KEY + ["latency", "target_minute", "price"]].rename(
        columns={"price": "entry_price", "target_minute": "entry_minute"})
    exits = priced[priced.hold != -1][C.KEY + ["latency", "hold", "target_minute", "price"]].rename(
        columns={"price": "exit_price", "target_minute": "exit_minute"})

    # ---------- cross-check entries against Phase 8 frozen det_price_lat* ----------
    cc = {}
    for lat in lats:
        col = f"det_price_lat{lat}"
        if col not in uni.columns:
            continue
        m = entries[entries.latency == lat].merge(uni[C.KEY + [col, "last_mi_t0"]], on=C.KEY, how="left")
        d = (m["entry_price"] - m[col]).abs()
        cc[f"lat{lat}"] = {"n": int(d.notna().sum()),
                           "max_abs_diff": (float(d.max()) if d.notna().any() else None),
                           "n_diff_gt_1e_9": int((d > 1e-9).sum())}
    print("entry cross-check vs Phase 8 det_price_lat*: "
          + ", ".join(f"{k} max|d|={v['max_abs_diff']:.2e} bad={v['n_diff_gt_1e_9']}" for k, v in cc.items()))

    # ---------- fixed-horizon grid ----------
    G = exits.merge(entries, on=C.KEY + ["latency"], how="left").merge(
        uni[C.KEY + ["era", "det_bin", "det_segment", "det_minute", "last_mi_t0", "close_t0"]],
        on=C.KEY, how="left")
    G["entry_undefined"] = G["entry_price"].isna() | ~G["entry_price"].gt(0) | \
                           G["entry_minute"].gt(G["last_mi_t0"])
    G["exit_undefined"] = G["exit_price"].isna() | ~G["exit_price"].gt(0) | \
                          G["exit_minute"].gt(G["last_mi_t0"])
    G["markout"] = np.where(~G["entry_undefined"] & ~G["exit_undefined"],
                            np.log(G["exit_price"] / G["entry_price"]), np.nan)
    G["grid"] = "fixed_horizon"

    # ---------- fixed-exit grid (exit = t0_close) ----------
    E = entries.merge(uni[C.KEY + ["era", "det_bin", "det_segment", "det_minute",
                                   "last_mi_t0", "close_t0"]], on=C.KEY, how="left")
    E["hold"] = np.nan
    E["exit_minute"] = E["last_mi_t0"]
    E["exit_price"] = E["close_t0"]
    E["entry_undefined"] = E["entry_price"].isna() | ~E["entry_price"].gt(0) | \
                           E["entry_minute"].gt(E["last_mi_t0"])
    E["exit_undefined"] = E["exit_price"].isna() | ~E["exit_price"].gt(0)
    E["markout"] = np.where(~E["entry_undefined"] & ~E["exit_undefined"],
                            np.log(E["exit_price"] / E["entry_price"]), np.nan)
    E["grid"] = "fixed_exit"
    E["effective_hold_minutes"] = E["exit_minute"] - E["entry_minute"]

    cols = ["grid", "latency", "hold", "entry_minute", "exit_minute", "entry_price",
            "exit_price", "entry_undefined", "exit_undefined", "markout",
            "era", "det_bin", "det_segment", "det_minute"]
    A = pd.concat([G[C.KEY + cols], E[C.KEY + cols + ["effective_hold_minutes"]]], ignore_index=True)
    A.to_parquet(OUT_PARQUET, index=False)
    print(f"wrote {OUT_PARQUET}  ({len(A):,} rows)")

    def cell(s):
        st = C.cell_stats(s)
        tm, tn = C.trimmed_mean_simple(s, tlo, thi)
        st["trimmed_mean_simple"] = tm
        st["n_trimmed"] = tn
        st["thin"] = st["n"] < THIN_N
        # Stale-price atom. Prices are last-trade-at/before, so when no print
        # lands between entry and exit the markout is EXACTLY 0 by construction
        # rather than by measurement - a point mass at zero, not a density.
        # The median is decided by that atom whenever the atom straddles the
        # 50th percentile, which needs nowhere near a 50% zero share: a cell
        # that is 49.6% negative / 4.6% zero / 45.8% positive reports median
        # exactly 0.0 off a 4.6% atom. Flag that condition, not the raw share.
        ss = pd.Series(s).dropna()
        if not len(ss):
            st["share_exact_zero"] = None
            st["median_on_zero_atom"] = False
            return st
        z = float((ss == 0).mean())
        below = float((ss < 0).mean())
        st["share_exact_zero"] = z
        st["share_below_zero"] = below
        st["median_on_zero_atom"] = bool(below < 0.5 <= below + z)
        return st

    # ---------- T4a cells ----------
    cells = []
    for lat in lats:
        for hold in holds:
            for db in DET_BINS:
                for era in C.ERAS + ["pooled"]:
                    s = G[(G.latency == lat) & (G.hold == hold) & (G.det_bin == db)]
                    if era != "pooled":
                        s = s[s.era == era]
                    c = cell(s["markout"])
                    c.update({"latency": lat, "hold": hold, "det_bin": db, "era": era})
                    cells.append(c)
            for era in C.ERAS + ["pooled"]:
                s = G[(G.latency == lat) & (G.hold == hold)]
                if era != "pooled":
                    s = s[s.era == era]
                c = cell(s["markout"])
                c.update({"latency": lat, "hold": hold, "det_bin": "ALL", "era": era})
                cells.append(c)

    thin_cells = [c for c in cells if c["thin"]]
    stale_cells = [c for c in cells if c.get("median_on_zero_atom")]

    # ---------- T4b fixed-exit ----------
    fixed_exit = {}
    for lat in lats:
        s = E[E.latency == lat]
        c = cell(s["markout"])
        eh = s.loc[s["markout"].notna(), "effective_hold_minutes"]
        c["median_effective_hold_minutes"] = (float(eh.median()) if len(eh) else None)
        c["n_entry_undefined"] = int(s["entry_undefined"].sum())
        fixed_exit[f"lat{lat}"] = c
    fixed_exit_by_bin = {}
    for db in DET_BINS:
        for lat in lats:
            s = E[(E.latency == lat) & (E.det_bin == db)]
            c = cell(s["markout"])
            c["n_entry_undefined"] = int(s["entry_undefined"].sum())
            fixed_exit_by_bin[f"{db}|lat{lat}"] = c

    # ---------- T4c attrition ----------
    attrition = {"fixed_exit": {}, "fixed_horizon": {}}
    base_n = None
    for lat in lats:
        n = int(E.loc[E.latency == lat, "markout"].notna().sum())
        base_n = base_n if base_n is not None else n
        attrition["fixed_exit"][f"lat{lat}"] = {
            "n_defined": n, "n_universe": n_uni,
            "n_lost_vs_lat0": base_n - n,
            "share_lost_vs_lat0": (base_n - n) / base_n if base_n else None,
            "n_entry_undefined": int(E.loc[E.latency == lat, "entry_undefined"].sum())}
    for hold in holds:
        b = None
        for lat in lats:
            n = int(G.loc[(G.latency == lat) & (G.hold == hold), "markout"].notna().sum())
            b = b if b is not None else n
            attrition["fixed_horizon"][f"hold{hold}|lat{lat}"] = {
                "n_defined": n, "n_lost_vs_lat0": b - n,
                "share_lost_vs_lat0": (b - n) / b if b else None}

    waterfall = [
        {"step": "D1 -> detection universe", "rows_in": len(d1), "rows_out": n_uni,
         "dropped": len(d1) - n_uni, "why": "det_undefined (the 394, Phase 8 A10.3)"},
        {"step": "fixed-horizon cells: entry and exit both on T0 and defined",
         "rows_in": int(len(G)), "rows_out": int(G["markout"].notna().sum()),
         "dropped": int(G["markout"].isna().sum()),
         "why": "entry or exit minute past the last T0 print (det+latency+hold runs off the session end); carried, never imputed"},
        {"step": "fixed-exit cells: entry defined, exit = t0_close",
         "rows_in": int(len(E)), "rows_out": int(E["markout"].notna().sum()),
         "dropped": int(E["markout"].isna().sum()),
         "why": "det+latency past the last T0 print"},
    ]

    summary = {
        "phase": "9", "task": "T4",
        "source": "research/phase_9/t4_axis_grid.py:main",
        "repro": "python -m research.phase_9.t4_axis_grid",
        "config_hash": C.cfg_hash(),
        "scan_free": True, "tables_touched": ["event_minute_bars_v2"],
        "spine_numeric_reads": 0,
        "n_detection_universe": n_uni,
        "latencies": lats, "holds": holds,
        "latency_note": "det+0 is a physical impossibility, carried only as the ladder's upper bound",
        "thin_cell_n": THIN_N,
        "n_thin_cells": len(thin_cells),
        "thin_cells": thin_cells,
        "escalation_row_11": {
            "condition": "any T4 cell with n < 100 presented without hatching",
            "n_thin_cells": len(thin_cells),
            "handling": "every thin cell carries thin=TRUE in this artifact and is hatched in chart 05; no claim is stated from one",
            "triggered": False},
        "stale_price_diagnostic": {
            "definition": "share of a cell's markouts exactly equal to 0, i.e. no print landed between entry and exit so the last-trade-at/before price is the same bar at both ends",
            "why": "the zero atom decides the median whenever it straddles the 50th percentile, which needs nowhere near a 50% zero share; such a median is fixed by print density, not by measurement",
            "n_cells_with_median_on_zero_atom": len(stale_cells),
            "n_cells_total": len(cells),
            "cells_with_median_on_zero_atom": stale_cells,
        },
        "entry_crosscheck_vs_phase8": cc,
        "fixed_horizon_cells": cells,
        "fixed_exit": fixed_exit,
        "fixed_exit_by_det_bin": fixed_exit_by_bin,
        "attrition": attrition,
        "confound_note": ("fixed-exit latency is the only axis where latency is unconfounded by hold "
                          "LENGTH-as-a-separate-factor, but its hold SHRINKS as latency grows; the "
                          "fixed-horizon grid holds hold constant instead. Both are reported."),
        "filter_waterfall": waterfall,
        "artifacts": [OUT_PARQUET],
    }
    C.write_json(summary, OUT_JSON)

    # ---------------- console ----------------
    print("\nT4b FIXED-EXIT (exit = t0_close): median markout by latency")
    print(f"{'latency':>8s} {'n':>7s} {'median':>10s} {'trim mean simple':>18s} {'med hold (min)':>15s} {'n lost vs L0':>13s}")
    for lat in lats:
        c = fixed_exit[f"lat{lat}"]
        a = attrition["fixed_exit"][f"lat{lat}"]
        tms = "n/a" if c["trimmed_mean_simple"] is None else f"{c['trimmed_mean_simple']:+.4%}"
        print(f"{('det+'+str(lat)):>8s} {c['n']:7,d} {c['median']:+10.5f} {tms:>18s} "
              f"{c['median_effective_hold_minutes']:15.0f} {a['n_lost_vs_lat0']:13,d}")

    print("\nT4a FIXED-HORIZON: median markout, det_bin x latency, per hold (era pooled)")
    for hold in holds:
        print(f"\n  hold = {hold} min")
        print("    " + f"{'latency':>8s}" + "".join(f"{db:>16s}" for db in DET_BINS))
        for lat in lats:
            row = f"    {('det+'+str(lat)):>8s}"
            for db in DET_BINS:
                c = next(x for x in cells if x["latency"] == lat and x["hold"] == hold
                         and x["det_bin"] == db and x["era"] == "pooled")
                if c["n"] == 0:
                    row += f"{'--':>16s}"
                else:
                    tag = "*" if c["thin"] else " "
                    row += f"{c['median']:+.4f}{tag}(n={c['n']:,})".rjust(16)
            print(row)
    print(f"\n  * = thin cell (n < {THIN_N}); hatched in chart 05, no claim stated from it")
    print(f"  thin cells: {len(thin_cells)} of {len(cells)}")

    print("\nSTALE-PRICE share (markout exactly 0: no print between entry and exit), "
          "det_bin x latency, hold=5, era pooled:")
    print("    " + f"{'latency':>8s}" + "".join(f"{db:>14s}" for db in DET_BINS))
    for lat in lats:
        row = f"    {('det+'+str(lat)):>8s}"
        for db in DET_BINS:
            c = next(x for x in cells if x["latency"] == lat and x["hold"] == 5
                     and x["det_bin"] == db and x["era"] == "pooled")
            z = c["share_exact_zero"]
            row += (f"{z:13.1%}" + ("!" if c["median_on_zero_atom"] else " ")) if z is not None else f"{'--':>14s}"
        print(row)
    print("  ! = the zero atom straddles the median, so that cell median is fixed by print density, not measured")
    print(f"  cells with median on the zero atom: {len(stale_cells)} of {len(cells)}")


if __name__ == "__main__":
    main()
