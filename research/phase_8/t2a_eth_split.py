"""
Phase 8 T2a - ETH-dominant split of the extended-day opportunity-decay
curve (primary, tick anchor, 516-clock).

Scan-free. Reuses 6b's frozen per-minute realized-fraction artifact
(opportunity_decay_primary_per_minute.parquet) and the flag_eth_dominant_t0
annotation from momentum_events_canonical (stage t8, tick-derived, NOT
D4-quarantined). Pools median + IQR of realized_move_fraction per minute_index
for the two flag groups. Chart split only - never a markout bucket (T5c).

Population: the primary decay population (defined realized_move_fraction, i.e.
has_t_minus_1_rth=TRUE and denom>0), matching 6b chart 04.
"""
from __future__ import annotations

import json

import duckdb
import pandas as pd

from src.data.paths import resolve_duckdb_path

PER_MIN = "results/phase_6b/artifacts/opportunity_decay_primary_per_minute.parquet"
D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
OUT_JSON = "results/phase_8/artifacts/t2_eth_split.json"
OUT_PARQUET = "results/phase_8/artifacts/t2_eth_split_curves.parquet"


def main():
    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")

    # flag per D1 event from the canonical view (t8). flag_eth_dominant_t0 is
    # populated for all rows (TRUE for 736, FALSE otherwise); D1 = in_scope & file1.
    flag = con.execute("""
        SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mp,
               flag_eth_dominant_t0
        FROM momentum_events_canonical
        WHERE in_scope = TRUE AND source_file = 'file1'
    """).fetchdf()
    n_true = int(flag["flag_eth_dominant_t0"].sum())
    n_false = int((~flag["flag_eth_dominant_t0"]).sum())
    print(f"flag TRUE={n_true}  FALSE={n_false}  total={len(flag)}")

    d1 = pd.read_parquet(D1_PATH)
    assert len(flag) == len(d1) == 15763, f"D1 mismatch: flag {len(flag)} d1 {len(d1)}"

    con.register("flag", flag)
    con.execute("CREATE TEMP TABLE fk AS SELECT * FROM flag")

    curves = con.execute(f"""
        WITH pm AS (
            SELECT p.minute_index, fk.flag_eth_dominant_t0 AS eth, p.realized_move_fraction AS rf
            FROM read_parquet('{PER_MIN}') p
            JOIN fk ON p.ticker=fk.ticker AND p.event_date_canonical=fk.event_date_canonical
                   AND ROUND(p.momentum_pct,2)=fk.mp
            WHERE p.realized_move_fraction IS NOT NULL
        )
        SELECT minute_index, eth,
               COUNT(*) AS n,
               median(rf) AS med,
               quantile_cont(rf, 0.25) AS q25,
               quantile_cont(rf, 0.75) AS q75
        FROM pm
        GROUP BY 1,2 ORDER BY 1,2
    """).fetchdf()
    curves.to_parquet(OUT_PARQUET, index=False)

    # per-group distinct-event n (primary decay population)
    grp_n = con.execute(f"""
        SELECT fk.flag_eth_dominant_t0 AS eth,
               COUNT(DISTINCT (p.ticker||p.event_date_canonical||p.momentum_pct)) AS n_events
        FROM read_parquet('{PER_MIN}') p
        JOIN fk ON p.ticker=fk.ticker AND p.event_date_canonical=fk.event_date_canonical
               AND ROUND(p.momentum_pct,2)=fk.mp
        WHERE p.realized_move_fraction IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """).fetchdf()
    n_events = {bool(r.eth): int(r.n_events) for r in grp_n.itertuples()}

    def crossing(eth_val: bool) -> float:
        c = curves[(curves.eth == eth_val)].sort_values("minute_index")
        hit = c[c["med"] >= 0.5]
        return float(hit["minute_index"].iloc[0]) if len(hit) else None

    summary = {
        "phase": "8", "task": "T2a",
        "source": "research/phase_8/t2a_eth_split.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "flag_source": "momentum_events_canonical (stage t8) flag_eth_dominant_t0",
        "flag_counts_d1": {"true": n_true, "false": n_false, "total": len(flag)},
        "decay_population_events": {"eth_true": n_events.get(True), "eth_false": n_events.get(False)},
        "population_note": "primary decay population = defined realized_move_fraction (has_t_minus_1_rth=TRUE, denom>0), matches 6b chart 04",
        "median_crossing_0p5_minute_since_0400": {
            "eth_true": crossing(True), "eth_false": crossing(False),
            "pooled_all_6b_reference": 516,
        },
        "curves_artifact": OUT_PARQUET,
        "role_note": "chart split only (chart 02); flag_eth_dominant_t0 is NEVER a markout bucket (T5c)",
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
