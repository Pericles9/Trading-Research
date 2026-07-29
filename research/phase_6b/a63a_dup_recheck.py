"""
Phase 6b A6.3a - targeted EXACT duplicate-print recheck (row 7 follow-up).

The full pass's HLL approx dup counter (build_minute_bars_v2.py) flagged 9
events with an approx strict-dup rate > 5% (the coarse tripwire). HLL is
noisy per-event (~2% on the clean dev tier), so a coarse flag needs an exact
confirmation. This does that EXACTLY, but scoped to the flagged events only,
so it stays feasible (the exact COUNT(DISTINCT) that was infeasible over the
whole table is trivial over a handful of events).

IMPORTANT - scan cost: filtered_trades has no index, so even an event-scoped
filter scans the whole table once. This recheck therefore costs one extra
filtered_trades scan per invocation. It is a diagnostic follow-up to an
escalation, run once, NOT part of the measurement pipeline's 1-pass budget;
the numbers it produced are captured in results/phase_6b/artifacts/
a63a_dup_recheck.json and it is not re-run.

Exact strict key: (ticker, event_date, ROUND(momentum_pct,2), sip_timestamp,
price, size, sequence_number) - identical to the pass's strict key and to
Phase 6c's A8/T3'' key. n_exact_dups = total rows - distinct strict keys.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
DUP_ARTIFACT = "results/phase_6b/artifacts/t3_dup_prints_v2.parquet"
OUT = "results/phase_6b/artifacts/a63a_dup_recheck.json"
# Exact-check the row-7 coarse-flag population (approx > 5%). A broader >2% audit was
# attempted but abandoned - it costs an additional full filtered_trades scan (no index) and
# the 2-5% band is dominated by HLL noise anyway (dev-tier max noise ~2.16%). Characterizing
# real duplication below 5% is a scope decision for Cooper, not resolved here.
COARSE_FLAG = 0.05   # the row-7 tripwire
APPROX_BAND = COARSE_FLAG


def exact_recheck(con, keys_df):
    con.register("recheck_keys", keys_df[["ticker", "event_date_canonical", "m"]])
    return con.execute("""
        WITH ft AS (
            SELECT t.ticker, t.event_date, ROUND(t.momentum_pct,2) AS m,
                   t.sip_timestamp, t.price, t.size, t.sequence_number
            FROM filtered_trades t
            JOIN recheck_keys f ON t.ticker=f.ticker AND t.event_date=f.event_date_canonical
                               AND ROUND(t.momentum_pct,2)=f.m
        ),
        strict AS (
            SELECT ticker, event_date, m, sip_timestamp, price, size, sequence_number, COUNT(*) AS c
            FROM ft GROUP BY 1,2,3,4,5,6,7
        )
        SELECT ticker, event_date, m,
               SUM(c) AS n_prints,
               SUM(c) - COUNT(*) AS n_exact_strict_dups,
               (SUM(c) - COUNT(*))::DOUBLE / SUM(c) AS exact_strict_dup_rate
        FROM strict GROUP BY 1,2,3 ORDER BY exact_strict_dup_rate DESC
    """).fetchdf()


def main():
    dp = pd.read_parquet(DUP_ARTIFACT)
    band = dp[dp["dup_strict_rate_approx"] > APPROX_BAND].copy()
    band["event_date_canonical"] = pd.to_datetime(band["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    band["m"] = band["momentum_pct"].round(2)
    print(f"events above {APPROX_BAND:.0%} approx (exact-checked): {len(band)}")

    con = duckdb.connect(DB_PATH, read_only=True)
    exact = exact_recheck(con, band)
    con.close()

    real = exact[exact["n_exact_strict_dups"] > 0].copy()
    artifact = exact[exact["n_exact_strict_dups"] == 0].copy()
    over_coarse = band[band["dup_strict_rate_approx"] > COARSE_FLAG]

    out = {
        "phase": "6b", "task": "A6.3a dup recheck (row 7 follow-up)",
        "trigger": f"HLL approx flagged {len(over_coarse)} events > {COARSE_FLAG:.0%} (row 7 coarse tripwire)",
        "method": "exact strict-key COUNT(*)-COUNT(DISTINCT) scoped to flagged events (one extra filtered_trades scan, run once)",
        "approx_band_exact_checked": APPROX_BAND,
        "n_events_exact_checked": len(band),
        "n_events_real_duplication": len(real),
        "n_events_hll_artifact_zero_exact": len(artifact),
        "total_exact_strict_dup_rows": int(exact["n_exact_strict_dups"].sum()),
        "real_duplication_events": real.to_dict(orient="records"),
        "hll_artifact_events": artifact[["ticker", "event_date", "m", "n_prints"]].to_dict(orient="records"),
        "finding": (
            "Genuine exact-duplicate prints exist in filtered_trades for the real_duplication_events - "
            "identical rows on (ticker, event_date, momentum_pct, sip_timestamp, price, size, sequence_number). "
            "These are ingestion duplicates. Duplicate prints inflate volume/n_trades for these events but do "
            "NOT alter the price path (a duplicate has the same price at the same timestamp), so the opportunity-"
            "decay (price-anchored) measurement is unaffected for them; volume-based measures (concentration, "
            "min-window, segment shares) are inflated for these events only. Previously undetected: Phase 6c's "
            "exact dup check was dev-tier only (56 events, none of these) - A8.2's full-pass requirement surfaced it."
        ),
        "scope_caveat": (
            f"Only events with approx rate > {APPROX_BAND:.0%} were exact-checked. Real duplication BELOW that "
            "sits under the HLL per-event noise floor and cannot be distinguished from noise without a broader "
            "exact audit (which would cost additional full scans). So this count is a lower bound on affected events."
        ),
        "source": "research/phase_6b/a63a_dup_recheck.py:main",
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in out.items() if k not in ("real_duplication_events", "hll_artifact_events")}, indent=2))
    print("\nreal duplication:")
    print(real.to_string())


if __name__ == "__main__":
    main()
