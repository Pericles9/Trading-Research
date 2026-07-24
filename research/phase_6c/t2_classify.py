"""
Phase 6c T2 - per-residual classification. Diagnosis only: reads
event_minute_bars_dev_v2 (already-materialized dev-tier table - read-only
query, not a full-table pass over filtered_trades) for coverage evidence,
plus the already-committed A6.1 artifact and the Phase 5a sidecar draw
table for bitmap patterns. No writes to phase_6b's tables/artifacts.
"""
import json

import duckdb
import numpy as np
import pandas as pd

PHASE_6C_CONFIG = "config/phase_6c.json"
A61_ARTIFACT = "results/phase_6b/artifacts/a61_basis_confirmation_rerun.json"
DB_PATH = "data/duckdb/main.duckdb"
DEV_BARS_TABLE = "event_minute_bars_dev_v2"
OUT_JSON = "results/phase_6c/artifacts/t2_residual_classification.json"

SIDECAR_PATTERNS = {
    "SLXN": "0011111|0011111", "APLD": "1111111|0000000", "ACET": "0111111|0111111",
    "RBC": "0001111|0001111", "NUKK": "0111111|0000000", "PSIX": "0011111|0000000",
}

RESIDUALS = ["SCLX", "VEEE", "NEPH", "ZENA", "ACET", "NUKK", "PSIX"]
PRIMARY_RESIDUALS = ["SCLX", "VEEE", "NEPH", "ZENA"]
SIDECAR_RESIDUALS = ["ACET", "NUKK", "PSIX"]


def event_coverage_stats(con, table, cohort_events: pd.DataFrame) -> pd.DataFrame:
    """Per event (T=0): RTH bar count, longest intra-RTH gap (minutes), ETH-vs-RTH row share."""
    rows = []
    for row in cohort_events.itertuples(index=False):
        d = pd.Timestamp(row.event_date_canonical)
        bars = con.execute(f"""
            SELECT segment, minute_index, n_trades
            FROM {table}
            WHERE ticker = ? AND event_date_canonical = ? AND ROUND(momentum_pct, 2) = ROUND(?, 2) AND session_offset = 0
            ORDER BY minute_index
        """, [row.ticker, d.date(), row.momentum_pct]).fetchdf()
        if bars.empty:
            continue
        rth = bars[bars["segment"] == "rth"].sort_values("minute_index")
        rth_bar_count = len(rth)
        if len(rth) >= 2:
            gaps = rth["minute_index"].diff().dropna()
            longest_gap = float(gaps.max()) - 1.0 if len(gaps) else 0.0
        else:
            longest_gap = 0.0
        total_trades = bars["n_trades"].sum()
        rth_trades = rth["n_trades"].sum()
        eth_share = 1.0 - (rth_trades / total_trades if total_trades else np.nan)
        rows.append({
            "ticker": row.ticker, "event_date_canonical": str(d.date()), "momentum_pct": row.momentum_pct,
            "rth_bar_count": rth_bar_count, "longest_intra_rth_gap_minutes": max(longest_gap, 0.0),
            "eth_vs_rth_row_share": eth_share,
            "first_print_minute": int(bars["minute_index"].min()), "last_print_minute": int(bars["minute_index"].max()),
        })
    return pd.DataFrame(rows)


def classify(event_row: dict, cfg: dict) -> tuple[str, dict]:
    rules = cfg["classification_rules"]
    r1p, r2p = event_row["r1p"], event_row["r2p"]
    rel_diff = abs(r1p - r2p) / r2p if (r1p is not None and r2p is not None and r2p) else None
    internal_rel = (r2p - r1p) / r1p if (r1p is not None and r2p is not None and r1p) else None

    mat = cfg["classification_rules"]["materiality_threshold_for_gap_evidence"]
    med = event_row["primary_median"]
    gap_evidence = []
    if event_row["rth_bar_count"] is not None and med["rth_bar_count"] and event_row["rth_bar_count"] < med["rth_bar_count"] * (1 - mat):
        gap_evidence.append(f"rth_bar_count {event_row['rth_bar_count']} < {1-mat:.0%} of primary median {med['rth_bar_count']:.0f}")
    if event_row["longest_intra_rth_gap_minutes"] is not None and med["longest_intra_rth_gap_minutes"] is not None and event_row["longest_intra_rth_gap_minutes"] > med["longest_intra_rth_gap_minutes"] * (1 + mat):
        gap_evidence.append(f"longest_intra_rth_gap {event_row['longest_intra_rth_gap_minutes']:.0f}m > {1+mat:.0%} of primary median {med['longest_intra_rth_gap_minutes']:.1f}m")
    if event_row["eth_vs_rth_row_share"] is not None and med["eth_vs_rth_row_share"] is not None and event_row["eth_vs_rth_row_share"] > med["eth_vs_rth_row_share"] * (1 + mat):
        gap_evidence.append(f"eth_vs_rth_row_share {event_row['eth_vs_rth_row_share']:.3f} > {1+mat:.0%} of primary median {med['eth_vs_rth_row_share']:.3f}")

    vendor_high_exceeds = event_row["spine_high_coalesced"] > event_row["day_high_rth"]

    if internal_rel is not None and internal_rel > 0.10 and vendor_high_exceeds and gap_evidence:
        return "coverage_gap", {"rel_diff": rel_diff, "internal_rel_r2_vs_r1": internal_rel, "vendor_high_exceeds_our_high": vendor_high_exceeds, "gap_evidence": gap_evidence}

    if rel_diff is not None and 0.02 <= rel_diff <= 0.07 and internal_rel is not None and abs(internal_rel) <= 0.10 and not (vendor_high_exceeds and gap_evidence):
        return "band_margin", {"rel_diff": rel_diff, "internal_rel_r2_vs_r1": internal_rel, "vendor_high_exceeds_our_high": vendor_high_exceeds, "gap_evidence": gap_evidence}

    return "unexplained", {"rel_diff": rel_diff, "internal_rel_r2_vs_r1": internal_rel, "vendor_high_exceeds_our_high": vendor_high_exceeds, "gap_evidence": gap_evidence}


def main():
    with open(PHASE_6C_CONFIG) as f:
        cfg = json.load(f)

    with open(A61_ARTIFACT) as f:
        a61 = json.load(f)
    full = pd.DataFrame(a61["full_table"])
    full["event_date_canonical"] = pd.to_datetime(full["event_date_canonical"])

    con = duckdb.connect(DB_PATH, read_only=True)
    primary_events = full[full["dev_cohort"] == "primary"][["ticker", "event_date_canonical", "momentum_pct"]]
    primary_cov = event_coverage_stats(con, DEV_BARS_TABLE, primary_events)
    primary_median = {
        "rth_bar_count": float(primary_cov["rth_bar_count"].median()),
        "longest_intra_rth_gap_minutes": float(primary_cov["longest_intra_rth_gap_minutes"].median()),
        "eth_vs_rth_row_share": float(primary_cov["eth_vs_rth_row_share"].median()),
    }
    print(f"primary-cohort medians: {primary_median}")

    residual_events = full[full["ticker"].isin(RESIDUALS)][["ticker", "event_date_canonical", "momentum_pct"]]
    residual_cov = event_coverage_stats(con, DEV_BARS_TABLE, residual_events)
    con.close()

    results = []
    for t in RESIDUALS:
        row = full[full["ticker"] == t].iloc[0]
        cov = residual_cov[residual_cov["ticker"] == t]
        cov_row = cov.iloc[0].to_dict() if len(cov) else {"rth_bar_count": None, "longest_intra_rth_gap_minutes": None, "eth_vs_rth_row_share": None, "first_print_minute": None, "last_print_minute": None}
        event_row = {
            "ticker": t, "cohort": "sidecar" if t in SIDECAR_RESIDUALS else "primary",
            "sidecar_pattern": SIDECAR_PATTERNS.get(t),
            "r1p": row["r1p"], "r2p": row["r2p"],
            "spine_high_coalesced": row["spine_high_coalesced"], "day_high_rth": row["day_high_rth"],
            "rth_bar_count": cov_row["rth_bar_count"], "longest_intra_rth_gap_minutes": cov_row["longest_intra_rth_gap_minutes"],
            "eth_vs_rth_row_share": cov_row["eth_vs_rth_row_share"],
            "first_print_minute": cov_row["first_print_minute"], "last_print_minute": cov_row["last_print_minute"],
            "primary_median": primary_median,
        }
        label, evidence = classify(event_row, cfg)
        results.append({**{k: v for k, v in event_row.items() if k != "primary_median"}, "classification": label, "evidence": evidence})
        print(f"{t} ({event_row['cohort']}): {label} - {evidence}")

    n_unexplained = sum(1 for r in results if r["classification"] == "unexplained")
    summary = {
        "phase": "6c", "task": "T2",
        "primary_cohort_medians": primary_median,
        "classifications": results,
        "n_band_margin": sum(1 for r in results if r["classification"] == "band_margin"),
        "n_coverage_gap": sum(1 for r in results if r["classification"] == "coverage_gap"),
        "n_unexplained": n_unexplained,
        "escalation_row1_triggered": n_unexplained > 0,
        "source": "research/phase_6c/t2_classify.py:main",
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "classifications"}, indent=2, default=str))

    if n_unexplained > 0:
        print(f"\n*** ESCALATION row 1: {n_unexplained} unexplained residual(s) - stop before T3 ***")


if __name__ == "__main__":
    main()
