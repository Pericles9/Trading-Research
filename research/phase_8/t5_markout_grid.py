"""
Phase 8 T5 (A10.1-T3) - markout grid.

Scan-free. Forward SIGNED log return log(p_horizon / p_anchor) from each
anchor to each horizon (long convention; sign kept; NEVER abs). All prices
are tick-derived last-trade-at/before from t4_anchors.parquet.

Grids:
  clock (T5a): anchor x participation_quintile x horizon x era
  rung  (T5b): rung x crossing_time_bin x horizon x era (participation constant
               by construction, not a bucket)

Bucketing variables (T5c) are all knowable at the anchor timestamp:
participation quintile (T3, from pre-anchor volume), crossing-time bin (the
crossing minute), era (the date). PROHIBITED and not used: momentum_pct/deciles,
realized-fraction-at-anchor, day-high quantities, flag_eth_dominant_t0 as a bucket.

Flagged populations (T5d) carried as their own labelled rows, never merged into
quintiles: no_baseline (20), has_t_minus_1_rth=FALSE (36), denom_nonpositive (5),
flag_has_dup_prints (7), flag_possible_row_cap (8, A10.1c-ii). Union excluded
from both grids; each reported separately at the flagship.

Flagship = anchor rth_open -> horizon t0_close (neutral reference: universally
defined session-start decision point; a reporting convention, not a markout-based
selection - escalation row 10 respected).

09:00 column carries its own n=14,023 (has_premarket_print=TRUE); the 1,740
has_premarket_print=FALSE are absent at 0900 only, present elsewhere (A10.1a).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
T4_PATH = "results/phase_8/artifacts/t4_anchors.parquet"
T3_PATH = "results/phase_8/artifacts/t3_participation.parquet"
A101_PATH = "results/phase_8/artifacts/a101_labels.parquet"
ANCHOR6B = "results/phase_6b/artifacts/opportunity_decay_primary.parquet"
DUP6B = "results/phase_6b/artifacts/event_index_v2.parquet"
OUT_GRID = "results/phase_8/artifacts/t5_markout_grid.parquet"
OUT_JSON = "results/phase_8/artifacts/t5_markout_summary.json"
KEY = ["ticker", "event_date_canonical", "mp"]
ERA_BOUNDARY = pd.Timestamp("2022-01-01")
CLOCK_ANCHORS = ["0900", "rth_open", "open+5", "open+15", "open+30", "open+60", "open+120", "t0_close"]
RUNGS = ["rung_1x", "rung_2x", "rung_5x", "rung_10x"]
HORIZONS = ["anchor+30", "anchor+60", "t0_close", "t1_close", "t3_close"]
FLAGSHIP_ANCHOR, FLAGSHIP_HORIZON = "rth_open", "t0_close"


def _norm(df):
    df["event_date_canonical"] = pd.to_datetime(df["event_date_canonical"])
    return df


def _iqr(s):
    s = s.dropna()
    return [float(s.quantile(0.25)), float(s.quantile(0.75))] if len(s) else [None, None]


def _cell(s):
    s = s.dropna()
    return {"n": int(len(s)), "median": (float(s.median()) if len(s) else None), "iqr": _iqr(s)}


def main():
    d1 = _norm(pd.read_parquet(D1_PATH)); d1["mp"] = d1["momentum_pct"].round(2)
    d1 = d1[KEY].drop_duplicates()
    d1["era"] = np.where(d1["event_date_canonical"] < ERA_BOUNDARY, "era_2020_2021", "era_2022_2024")

    grid = _norm(pd.read_parquet(T4_PATH))
    # markout where both anchor and horizon defined and prices positive
    ok = (~grid["anchor_undefined"]) & (~grid["horizon_undefined"]) \
         & grid["anchor_price"].gt(0) & grid["horizon_price"].gt(0)
    grid["markout"] = np.where(ok, np.log(grid["horizon_price"] / grid["anchor_price"]), np.nan)

    # participation quintile per clock anchor (melt pq_*)
    t3 = _norm(pd.read_parquet(T3_PATH))
    pqcols = [c for c in t3.columns if c.startswith("pq_")]
    pq = t3.melt(id_vars=KEY, value_vars=pqcols, var_name="anchor_name", value_name="pq")
    pq["anchor_name"] = pq["anchor_name"].str.replace("pq_", "", regex=False)

    # flags / labels
    a101 = _norm(pd.read_parquet(A101_PATH))
    anc6b = _norm(pd.read_parquet(ANCHOR6B)); anc6b["mp"] = anc6b["momentum_pct"].round(2)
    dup6b = _norm(pd.read_parquet(DUP6B)); dup6b["mp"] = dup6b["momentum_pct"].round(2)

    no_baseline = set(map(tuple, t3.loc[t3.participation_class == "no_baseline", KEY].values))
    htm1_false = set(map(tuple, anc6b.loc[~anc6b.has_t_minus_1_rth.astype(bool), KEY].values))
    denom_np = set(map(tuple, anc6b.loc[anc6b.denom_nonpositive.astype(bool), KEY].values))
    dup7 = set(map(tuple, dup6b.loc[dup6b.flag_has_dup_prints.astype(bool), KEY].values))
    rowcap8 = set(map(tuple, a101.loc[a101.flag_possible_row_cap.astype(bool), KEY].values))
    flagged_union = no_baseline | htm1_false | denom_np | dup7 | rowcap8
    print(f"flagged counts: no_baseline={len(no_baseline)} htm1F={len(htm1_false)} "
          f"denom_np={len(denom_np)} dup7={len(dup7)} rowcap8={len(rowcap8)} union={len(flagged_union)}")

    def keytup(df):
        return list(zip(df["ticker"], df["event_date_canonical"], df["mp"]))

    grid = grid.merge(d1[KEY + ["era"]], on=KEY, how="left")
    grid = grid.merge(pq, on=KEY + ["anchor_name"], how="left")
    grid = grid.merge(a101[KEY + ["has_premarket_print", "flag_possible_row_cap"]], on=KEY, how="left")
    grid["ktup"] = keytup(grid)
    grid["in_flagged_union"] = grid["ktup"].isin(flagged_union)
    grid["is_dup7"] = grid["ktup"].isin(dup7)
    grid["is_rowcap8"] = grid["ktup"].isin(rowcap8)
    grid = grid.drop(columns=["ktup"])

    grid.to_parquet(OUT_GRID, index=False)

    # ---------- T5a clock grid ----------
    clock = grid[(grid.anchor_kind == "clock") & grid.markout.notna() & (~grid.in_flagged_union) & grid.pq.notna()]
    clock_summary = []
    for a in CLOCK_ANCHORS:
        for h in HORIZONS:
            for era in ["era_2020_2021", "era_2022_2024"]:
                for q in [1, 2, 3, 4, 5]:
                    s = clock[(clock.anchor_name == a) & (clock.horizon_name == h)
                              & (clock.era == era) & (clock.pq == q)]["markout"]
                    c = _cell(s)
                    c.update({"anchor": a, "horizon": h, "era": era, "participation_quintile": q,
                              "thin": c["n"] < 100})
                    clock_summary.append(c)

    # ---------- T5b rung grid ----------
    rung = grid[(grid.anchor_kind == "rung") & grid.markout.notna() & (~grid.in_flagged_union)]
    rung_bins = ["premarket (04:00-09:30)", "open-10:30", "10:30-12:00", "12:00-14:00", "14:00-16:00", "post (16:00-20:00)"]
    rung_summary = []
    for r in RUNGS:
        for h in HORIZONS:
            for era in ["era_2020_2021", "era_2022_2024"]:
                for b in rung_bins:
                    s = rung[(rung.anchor_name == r) & (rung.horizon_name == h)
                             & (rung.era == era) & (rung.crossing_bin == b)]["markout"]
                    c = _cell(s)
                    c.update({"rung": r, "horizon": h, "era": era, "crossing_bin": b,
                              "thin": c["n"] < 100})
                    rung_summary.append(c)

    # ---------- flagship + flagged-population rows ----------
    fs = grid[(grid.anchor_name == FLAGSHIP_ANCHOR) & (grid.horizon_name == FLAGSHIP_HORIZON) & grid.markout.notna()]
    flagship_clean = fs[~fs.in_flagged_union]["markout"]
    flagship_all = fs["markout"]
    flagship_wo_rowcap = fs[~fs.is_rowcap8]["markout"]
    flagship_wo_dup = fs[~fs.is_dup7]["markout"]

    def flagged_row(name, ktset):
        s = fs[fs.set_index(KEY).index.isin(ktset)]["markout"] if False else \
            fs[list(map(lambda t: t in ktset, zip(fs.ticker, fs.event_date_canonical, fs.mp)))]["markout"]
        return {"population": name, **_cell(s)}

    flagged_rows = [
        flagged_row("no_baseline", no_baseline),
        flagged_row("has_t_minus_1_rth_FALSE", htm1_false),
        flagged_row("denom_nonpositive", denom_np),
        flagged_row("flag_has_dup_prints", dup7),
        flagged_row("flag_possible_row_cap", rowcap8),
    ]

    # ---------- A10.1a-iii: rth_open markout by has_premarket_print ----------
    ro = grid[(grid.anchor_name == "rth_open") & (grid.horizon_name == FLAGSHIP_HORIZON) & grid.markout.notna()]
    pm_split = {}
    for era in ["era_2020_2021", "era_2022_2024"]:
        for val, lab in [(True, "has_premarket_print_TRUE"), (False, "has_premarket_print_FALSE")]:
            s = ro[(ro.era == era) & (ro.has_premarket_print == val)]["markout"]
            pm_split[f"{era}|{lab}"] = _cell(s)

    summary = {
        "phase": "8", "task": "T5 (A10.1-T3)",
        "source": "research/phase_8/t5_markout_grid.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "markout_definition": "signed log return log(p_horizon/p_anchor), sign kept",
        "flagship": {"anchor": FLAGSHIP_ANCHOR, "horizon": FLAGSHIP_HORIZON,
                     "reference_note": "neutral session-start reference; NOT selected on markouts (row 10)"},
        "flagged_union_n": len(flagged_union),
        "clock_grid": clock_summary,
        "rung_grid": rung_summary,
        "flagship_sensitivity_t0close": {
            "clean_excl_flagged": _cell(flagship_clean),
            "all_incl_flagged": _cell(flagship_all),
            "without_8_row_cap": _cell(flagship_wo_rowcap),
            "without_7_dup_prints": _cell(flagship_wo_dup),
        },
        "flagged_population_rows_at_flagship": flagged_rows,
        "rth_open_by_has_premarket_print_t0close": pm_split,
        "artifact": OUT_GRID,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # console: flagship quintile x era table
    print("\nFLAGSHIP rth_open -> t0_close, median markout by quintile x era (n):")
    for era in ["era_2020_2021", "era_2022_2024"]:
        row = []
        for q in [1, 2, 3, 4, 5]:
            c = next(x for x in clock_summary if x["anchor"] == "rth_open" and x["horizon"] == "t0_close"
                     and x["era"] == era and x["participation_quintile"] == q)
            row.append(f"Q{q}:{c['median']:+.3f}(n={c['n']})" if c['median'] is not None else f"Q{q}:NA")
        print(f"  {era}: " + "  ".join(row))
    print("\nflagship sensitivity (t0_close pooled median):")
    for k, v in summary["flagship_sensitivity_t0close"].items():
        print(f"  {k}: median {v['median']} n={v['n']}")
    print("\nrth_open -> t0_close by has_premarket_print:")
    for k, v in pm_split.items():
        print(f"  {k}: median {v['median']} n={v['n']}")


if __name__ == "__main__":
    main()
