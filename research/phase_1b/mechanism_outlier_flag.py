"""
Phase 1b T3 - mechanism outlier flag.

flag_bad_denominator = (prev_close < prev_close_floor) OR (momentum_pct >= mom_sanity_cap),
thresholds from config/phase_1b.json. Computed directly against momentum_events
(not through momentum_events_canonical) - this flag only depends on raw
prev_close/momentum_pct, and going through the view would re-trigger its
filtered_trades join for no benefit.
"""
import json

import duckdb

CONFIG_PATH = "config/phase_1b.json"
DB_PATH = "data/duckdb/main.duckdb"
OUT_SUMMARY = "results/phase_1b/artifacts/mechanism_outlier_flag_summary.json"


def main():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    prev_close_floor = cfg["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg["outlier_flags"]["mom_sanity_cap"]

    con = duckdb.connect(database=DB_PATH, read_only=True)

    counts = con.execute(
        f"""
        SELECT
            CASE WHEN date IS NOT NULL THEN 'file1' WHEN event_date IS NOT NULL THEN 'file2' END AS source_file,
            COUNT(*) AS n_total,
            SUM(CASE WHEN prev_close < {prev_close_floor} OR momentum_pct >= {mom_sanity_cap} THEN 1 ELSE 0 END) AS n_flagged
        FROM momentum_events
        GROUP BY 1
        """
    ).fetchdf()

    top10 = con.execute(
        f"""
        SELECT ticker, COALESCE(date, event_date) AS event_date_canonical, prev_close, momentum_pct
        FROM momentum_events
        WHERE prev_close < {prev_close_floor} OR momentum_pct >= {mom_sanity_cap}
        ORDER BY momentum_pct DESC
        LIMIT 10
        """
    ).fetchdf()

    caught_538m = con.execute(
        f"""
        SELECT COUNT(*) FROM momentum_events
        WHERE momentum_pct = 53799900.0
          AND (prev_close < {prev_close_floor} OR momentum_pct >= {mom_sanity_cap})
        """
    ).fetchone()[0]

    n_total_flagged = int(counts["n_flagged"].sum())
    n_total = int(counts["n_total"].sum())

    summary = {
        "phase": "1b",
        "task": "T3",
        "thresholds": {"prev_close_floor": prev_close_floor, "mom_sanity_cap": mom_sanity_cap},
        "n_total_flagged": n_total_flagged,
        "n_total_flagged_pct": round(100 * n_total_flagged / n_total, 4),
        "by_source_file": {
            row["source_file"]: {"n_total": int(row["n_total"]), "n_flagged": int(row["n_flagged"])}
            for _, row in counts.iterrows()
        },
        "top_10_flagged_rows": top10.to_dict(orient="records"),
        "t3a_538m_row_check": {
            "momentum_pct": 53799900.0,
            "caught_by_rule": caught_538m == 1,
            "n_matching_rows": int(caught_538m),
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if caught_538m != 1:
        raise SystemExit("ESCALATION: 53,799,900% row not caught by flag_bad_denominator rule")


if __name__ == "__main__":
    main()
