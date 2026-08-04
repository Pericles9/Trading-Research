"""
Phase 10 T1 -- cohort construction.

Spine: dev v4 primary (50, frozen from Phase 5a, never redrawn).
Sidecar: dev v4 sidecar (6, carried, NEVER pooled).
Extension: 50 events, 5 per T=0-print-count decile, seed 42 -- so the cohort
spans the range of session activity rather than clustering at one intensity.

Stratification is T=0 print count, not momentum_pct: momentum_pct is the axis
dev v4 primary was already drawn on (a completed-day PRICE-move stratifier),
so reusing it would sample the same axis twice and leave session activity
uncontrolled. T=0 print count IS session activity, is tick-derived from
event_minute_bars_v2 (D4-clean), and spans four orders of magnitude across D1.

Reads: event_minute_bars_v2 (45.9M rows, aggregated) and
momentum_events_canonical. ZERO reads of filtered_trades / filtered_quotes.

Usage: python research/phase_10/t1_cohort.py
"""
from __future__ import annotations

import os
import sys

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    COHORT_KEY, NON_POOLED_GROUPS, config_hash, load_config, rel, write_json,
)

OUT_MANIFEST = "t1_cohort_manifest.parquet"
OUT_SUMMARY = "t1_cohort_summary.json"
OUT_POOL = "t1_stratification_pool.parquet"


def load_spine(con, cfg) -> tuple[pd.DataFrame, pd.DataFrame]:
    """D1 canonical rows + per-offset tick print counts, both keyed 3-part."""
    con.execute("SET enable_progress_bar=false")
    canon = con.execute(
        """
        SELECT ticker, event_date_canonical, ROUND(momentum_pct, 2) AS momentum_pct,
               source_file, in_scope, clean_window, trades_ingested, quotes_ingested,
               coverage_class, trades_full_window, quotes_full_window,
               flag_eth_dominant_t0, t0_eth_row_share, repaired_1c,
               flag_window_calendar_bug, flag_missing_event_day,
               trades_bitmap, quotes_bitmap
        FROM momentum_events_canonical
        """
    ).fetchdf()
    canon["event_date_canonical"] = canon["event_date_canonical"].astype(str)

    bars = con.execute(
        """
        SELECT ticker, CAST(event_date_canonical AS VARCHAR) AS event_date_canonical,
               ROUND(momentum_pct, 2) AS momentum_pct, session_offset,
               SUM(n_trades) AS n_prints
        FROM event_minute_bars_v2
        GROUP BY 1, 2, 3, 4
        """
    ).fetchdf()
    return canon, bars


def build_pool(canon: pd.DataFrame, bars: pd.DataFrame, cfg) -> pd.DataFrame:
    """D1 events with their T=0 in-window print count and its decile."""
    t0 = bars[bars["session_offset"] == 0][COHORT_KEY + ["n_prints"]].rename(
        columns={"n_prints": "t0_print_count"}
    )
    d1 = canon[(canon["in_scope"]) & (canon["source_file"] == "file1")]
    pool = d1.merge(t0, on=COHORT_KEY, how="left")
    pool["t0_print_count"] = pool["t0_print_count"].fillna(0).astype("int64")

    # Deterministic order BEFORE ranking. rank(method="first") breaks ties by row
    # position, and the row order of a SELECT with no ORDER BY is not stable across
    # runs -- so without this sort, tied t0_print_count values land in different
    # deciles on different runs, the per-decile eligible pools differ, and the
    # "seeded" draw silently returns a different cohort. That happened: an earlier
    # run drew DPRO 2024-04-01 and IMTE 2023-10-27, a later one did not.
    pool = pool.sort_values(COHORT_KEY, kind="mergesort").reset_index(drop=True)

    n_str = cfg["stratification"]["n_strata"]
    pool["t0_print_decile"] = pd.qcut(
        pool["t0_print_count"].rank(method="first"), n_str, labels=False
    ).astype(int)
    return pool


def draw_extension(pool: pd.DataFrame, excluded: pd.DataFrame, cfg) -> pd.DataFrame:
    """Seeded per-stratum draw, deterministic under a fixed sort."""
    ext_cfg = cfg["cohort"]["extension"]
    seed, per = ext_cfg["seed"], ext_cfg["per_stratum"]

    key = excluded.set_index(COHORT_KEY).index
    eligible = pool[
        pool["clean_window"].fillna(False)
        & pool["trades_ingested"].fillna(False)
        & ~pool.set_index(COHORT_KEY).index.isin(key)
    ].copy()

    picks, stratum_sizes = [], {}
    for d in sorted(eligible["t0_print_decile"].unique()):
        sub = eligible[eligible["t0_print_decile"] == d].sort_values(
            COHORT_KEY, kind="mergesort"
        ).reset_index(drop=True)
        stratum_sizes[int(d)] = int(len(sub))
        rng = np.random.default_rng(seed + int(d))
        take = min(per, len(sub))
        idx = rng.choice(len(sub), size=take, replace=False)
        picks.append(sub.iloc[np.sort(idx)])
    out = pd.concat(picks, ignore_index=True)
    out.attrs["stratum_sizes"] = stratum_sizes
    return out


def attach_flags(cohort: pd.DataFrame, cfg) -> pd.DataFrame:
    """Join the three cross-phase flags that live in phase artifacts, never
    re-derive them (CLAUDE.md standing exceptions to A9.3)."""
    cohort = cohort.copy()

    cap_path = rel(cfg["paths"]["row_cap_labels"])
    cap = pd.read_parquet(cap_path).rename(columns={"mp": "momentum_pct"})
    cap["event_date_canonical"] = cap["event_date_canonical"].astype(str)
    cap["momentum_pct"] = cap["momentum_pct"].round(2)
    cap_col = "flag_possible_row_cap"
    cohort = cohort.merge(cap[COHORT_KEY + [cap_col]], on=COHORT_KEY, how="left")
    cohort[cap_col] = cohort[cap_col].fillna(False).astype(bool)

    idx_path = rel(cfg["paths"]["event_index_v2"])
    if os.path.exists(idx_path):
        ev = pd.read_parquet(idx_path)
        ev["event_date_canonical"] = ev["event_date_canonical"].astype(str)
        ev["momentum_pct"] = ev["momentum_pct"].round(2)
        dup_col = "flag_has_dup_prints"
        if dup_col in ev.columns:
            cohort = cohort.merge(ev[COHORT_KEY + [dup_col]], on=COHORT_KEY, how="left")
            cohort[dup_col] = cohort[dup_col].fillna(False).astype(bool)
    return cohort


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    os.makedirs(out_dir, exist_ok=True)

    primary = pd.read_parquet(rel(cfg["cohort"]["primary_spine"]["source"]))
    sidecar = pd.read_parquet(rel(cfg["cohort"]["sidecar"]["source"]))
    for d in (primary, sidecar):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
        d["momentum_pct"] = d["momentum_pct"].round(2)

    con = duckdb.connect(rel(cfg["paths"]["duckdb"]), read_only=True)
    canon, bars = load_spine(con, cfg)
    con.close()

    pool = build_pool(canon, bars, cfg)
    pool.to_parquet(os.path.join(out_dir, OUT_POOL), index=False)

    dev_all = pd.concat([primary[COHORT_KEY], sidecar[COHORT_KEY]], ignore_index=True)
    ext = draw_extension(pool, dev_all, cfg)
    stratum_sizes = ext.attrs["stratum_sizes"]

    # Reproducibility: the draw must be invariant to the ROW ORDER the pool arrives
    # in, not merely repeatable against one in-memory pool object. Rebuilding the
    # decile from a shuffled copy is the test that actually catches an unordered-SQL
    # dependency; comparing two draws off the same object does not.
    shuffled = build_pool(
        canon.sample(frac=1.0, random_state=7).reset_index(drop=True),
        bars.sample(frac=1.0, random_state=8).reset_index(drop=True), cfg,
    )
    ext2 = draw_extension(shuffled, dev_all, cfg)
    repro_ok = bool(
        ext[COHORT_KEY].reset_index(drop=True).equals(ext2[COHORT_KEY].reset_index(drop=True))
    )

    # row-cap census: every D1 event carrying flag_possible_row_cap, carried and
    # never pooled. See config.cohort.row_cap_census.why_added.
    cap = pd.read_parquet(rel(cfg["paths"]["row_cap_labels"])).rename(columns={"mp": "momentum_pct"})
    cap["event_date_canonical"] = cap["event_date_canonical"].astype(str)
    cap["momentum_pct"] = cap["momentum_pct"].round(2)
    cap_ids = cap.loc[cap["flag_possible_row_cap"], COHORT_KEY]
    cap_ids = cap_ids.merge(pool[COHORT_KEY], on=COHORT_KEY, how="inner")
    drawn = pd.concat([primary[COHORT_KEY], ext[COHORT_KEY], sidecar[COHORT_KEY]], ignore_index=True)
    cap_new = cap_ids[~cap_ids.set_index(COHORT_KEY).index.isin(drawn.set_index(COHORT_KEY).index)]
    n_cap_overlap = int(len(cap_ids) - len(cap_new))

    frames = [
        primary[COHORT_KEY].assign(cohort_group="dev_v4_primary"),
        ext[COHORT_KEY].assign(cohort_group="activity_extension"),
        sidecar[COHORT_KEY].assign(cohort_group="dev_v4_sidecar"),
        cap_new[COHORT_KEY].assign(cohort_group="row_cap_census"),
    ]
    cohort = pd.concat(frames, ignore_index=True)

    # ---- escalation row 2: join to canonical WHERE in_scope = TRUE
    in_scope = canon[canon["in_scope"] == True]  # noqa: E712
    joined = cohort.merge(in_scope, on=COHORT_KEY, how="left", indicator=True)
    n_matched = int((joined["_merge"] == "both").sum())
    shortfall = int(len(cohort) - n_matched)
    unmatched = joined.loc[joined["_merge"] != "both", COHORT_KEY].to_dict("records")

    cohort = joined.drop(columns=["_merge"])
    t0c = pool[COHORT_KEY + ["t0_print_count", "t0_print_decile"]]
    cohort = cohort.merge(t0c, on=COHORT_KEY, how="left")
    cohort = attach_flags(cohort, cfg)
    cohort["config_hash"] = chash
    cohort["seed"] = cfg["cohort"]["seed"]

    cohort.to_parquet(os.path.join(out_dir, OUT_MANIFEST), index=False)

    ext_full = cohort[cohort["cohort_group"] == "activity_extension"]
    summary = {
        "phase": "10", "task": "T1", "config_hash": chash,
        "cohort_n_total": int(len(cohort)),
        "cohort_by_group": cohort["cohort_group"].value_counts().to_dict(),
        "analysis_cohort_n": int((~cohort["cohort_group"].isin(NON_POOLED_GROUPS)).sum()),
        "analysis_cohort_note": "dev_v4_primary + activity_extension. dev_v4_sidecar and row_cap_census are carried and labeled but NEVER pooled.",
        "stratification": {
            "variable": cfg["stratification"]["variable"],
            "n_strata": cfg["stratification"]["n_strata"],
            "eligible_pool_n": int(sum(stratum_sizes.values())),
            "stratum_pool_sizes": stratum_sizes,
            "stratum_draw_counts": ext_full["t0_print_decile"].value_counts().sort_index().to_dict(),
            "seed": cfg["cohort"]["extension"]["seed"],
        },
        "reproducibility_check": {"pass": repro_ok, "method": "rebuild the decile from a row-shuffled canonical + bars, redraw with the same seed, require zero differing rows -- tests order-independence, not just repeatability"},
        "row_cap_census": {
            "n_flagged_in_d1": int(cap["flag_possible_row_cap"].sum()),
            "n_in_d1_pool": int(len(cap_ids)),
            "n_added": int(len(cap_new)),
            "n_already_drawn": n_cap_overlap,
            "membership": "census of every D1 flag_possible_row_cap event; never pooled",
        },
        "canonical_join": {
            "rule": "inner join to momentum_events_canonical WHERE in_scope = TRUE",
            "n_cohort": int(len(cohort)), "n_matched": n_matched,
            "shortfall": shortfall, "unmatched": unmatched,
            "escalation_row_2_triggered": shortfall > 0,
        },
        "t0_print_count_by_group": {
            g: {
                "n": int(len(sub)),
                "min": int(sub["t0_print_count"].min()),
                "q25": float(sub["t0_print_count"].quantile(0.25)),
                "median": float(sub["t0_print_count"].median()),
                "q75": float(sub["t0_print_count"].quantile(0.75)),
                "max": int(sub["t0_print_count"].max()),
            }
            for g, sub in cohort.groupby("cohort_group")
        },
        "flags_in_cohort": {
            "flag_possible_row_cap": int(cohort["flag_possible_row_cap"].sum()),
            "flag_possible_row_cap_events": cohort.loc[
                cohort["flag_possible_row_cap"], COHORT_KEY + ["cohort_group", "t0_print_count"]
            ].to_dict("records"),
            "flag_has_dup_prints": int(cohort.get("flag_has_dup_prints", pd.Series(dtype=bool)).sum()),
            "flag_eth_dominant_t0": int(cohort["flag_eth_dominant_t0"].fillna(False).sum()),
            "clean_window_false": int((~cohort["clean_window"].fillna(False)).sum()),
        },
        "artifact": f"{cfg['paths']['out_artifacts']}{OUT_MANIFEST}",
        "source": "research/phase_10/t1_cohort.py:main",
    }
    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    print(f"cohort: {len(cohort)} events  {summary['cohort_by_group']}")
    print(f"canonical in_scope join: matched {n_matched}/{len(cohort)}  shortfall {shortfall}")
    print(f"reproducibility: {repro_ok}")
    print(f"row-cap flagged in cohort: {summary['flags_in_cohort']['flag_possible_row_cap']}")
    if shortfall > 0:
        print("ESCALATION ROW 2 TRIGGERED", unmatched)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
