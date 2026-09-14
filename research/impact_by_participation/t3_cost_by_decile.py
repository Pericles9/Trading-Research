"""T3 -- realised effective spread by participation decile, dev tier, T=0 only.

Reuses research/phase_11/stage_b_pipeline.py's build_cache() verbatim (the same function
T5a used for dev-tier timing) to get the per-print Lee & Ready classification and
contemporaneous midpoint -- imported, not reimplemented. build_cache's own temp table `_t2`
(ticker, event_date, segment, minute_index, sip_timestamp, price, size, mid, sign_quote, sgn)
is queried directly after the call, since DuckDB temp tables persist on the connection.

Effective spread here is 2*|price-mid|/mid (T8's eff_frac formula, research/phase_11/t8_impact.py)
-- direction-agnostic, so it does NOT actually need the Lee & Ready sign. Reused anyway because
build_cache computes it as a side effect of the same pass and there is no cheaper path to a
contemporaneous mid than the one that pass already builds; the sign column is carried in the
per-print output for completeness (T8a's classified/unclassifiable framing) but effective
spread itself is computed from |price - mid| alone.

Scope note: build_cache's _labelled() restricts to `et_ts::DATE = event_date`, i.e. T=0 only --
matching T1's closest cell (also on the event day by construction) and Phase 11's own Stage B
scope ("T=0 session only"). T2's participation deciles were computed across every session_offset
in event_minute_bars_v2; this task's join naturally keeps only the T=0 side of that.

Usage: .venv/Scripts/python.exe -m research.impact_by_participation.t3_cost_by_decile
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "phase_11"))

import numpy as np
import pandas as pd
from common import connect, primary_events, session_bounds  # noqa: E402
from stage_b_pipeline import build_cache  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"
CELL = {"latency_minutes": 1, "horizon_minutes": 60}


def main() -> int:
    con = connect()
    ev = primary_events(con)
    dates = con.execute(
        "SELECT DISTINCT et(sip_timestamp)::DATE d FROM mom.filtered_quotes_dev_v4 "
        "WHERE dev_cohort='primary'").df()["d"]
    con.register("sb_df", session_bounds(dates))
    con.execute("CREATE TABLE sb AS SELECT * FROM sb_df")

    # build_cache's _labelled() requires _bounds (ticker, event_date, mp2, lo_ns, hi_ns) --
    # created inline in research/phase_11/t5b_pass.py's per-batch loop, but never factored
    # into a shared helper, so t5a_dev_timing.py's identical call would hit the same missing
    # table. Reconstructed here from ev (primary_events) rather than re-deriving the SQL.
    ev["mp2"] = ev["momentum_pct"].round(2)
    con.register("batch_df", ev[["ticker", "event_date", "mp2"]])
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _bounds AS
        SELECT ticker, event_date, mp2,
               epoch_ns((event_date::DATE + TIME '04:00:00') AT TIME ZONE 'America/New_York') AS lo_ns,
               epoch_ns((event_date::DATE + TIME '20:00:00') AT TIME ZONE 'America/New_York') AS hi_ns
        FROM batch_df
    """)

    print("running build_cache on filtered_quotes_dev_v4/filtered_trades_dev_v4 "
          "(dev_cohort='primary') -- reused from research/phase_11/stage_b_pipeline.py...")
    secs = build_cache(con, "mom.filtered_quotes_dev_v4", "mom.filtered_trades_dev_v4",
                       "dev_cohort='primary'", out_table="_dummy_t3_cache")
    print(f"  build_cache wall {secs:.1f}s")

    prints = con.execute("""
        SELECT ticker, event_date, segment, minute_index, sip_timestamp, price, size, mid, sgn
        FROM _t2 WHERE mid IS NOT NULL
    """).df()
    n_prints_with_mid = len(prints)
    prints["eff_frac"] = 2.0 * (prints["price"] - prints["mid"]).abs() / prints["mid"]
    prints["eff_bp"] = prints["eff_frac"] * 10000.0
    prints["eff_cents"] = prints["eff_frac"] * prints["mid"] * 100.0

    t2 = pd.read_parquet(ARTIFACTS / "t2_participation.parquet",
                         columns=["ticker", "event_date", "session_offset", "minute_index",
                                  "sip_timestamp", "size", "decile", "participation_rate"])
    t2_t0 = t2[t2.session_offset == 0].drop(columns="session_offset")

    # Join on the print's own sip_timestamp (and size, as a second discriminant against the
    # rare same-bar same-timestamp ties Phase 11's own T4c audit already documents) rather
    # than (ticker, event_date, minute_index) alone -- that alone is bar-level, not print-
    # level, and produced a many-to-many cartesian blowup (6.1e9 rows, 45.6 GiB) on the
    # first attempt.
    joined_raw = prints.merge(
        t2_t0, on=["ticker", "event_date", "minute_index", "sip_timestamp", "size"],
        how="inner")
    n_joined_raw = len(joined_raw)
    # Even (ticker, event_date, minute_index, sip_timestamp, size) is not perfectly unique --
    # a small residual over-match (~1-2%) survives, consistent with Phase 11's own T4c tie
    # audit (same-timestamp trades that also share a size). sequence_number would break these
    # (T4c: "never inverts... breaks all tied rows uniquely") but is not carried through _t2,
    # so it is not threaded through here. Deduplicated defensively rather than silently
    # inflating decile counts: keep first per print-side row.
    joined = joined_raw.drop_duplicates(
        subset=["ticker", "event_date", "minute_index", "sip_timestamp", "price", "size"],
        keep="first")
    n_joined = len(joined)

    rows = []
    for dec, sub in joined.groupby("decile"):
        rows.append({
            "decile": int(dec), "n": int(len(sub)),
            "eff_bp_p25": float(sub.eff_bp.quantile(.25)),
            "eff_bp_p50": float(sub.eff_bp.median()),
            "eff_bp_p75": float(sub.eff_bp.quantile(.75)),
            "eff_cents_p25": float(sub.eff_cents.quantile(.25)),
            "eff_cents_p50": float(sub.eff_cents.median()),
            "eff_cents_p75": float(sub.eff_cents.quantile(.75)),
            "participation_rate_min": float(sub.participation_rate.min()),
            "participation_rate_max": float(sub.participation_rate.max()),
        })
    by_decile = pd.DataFrame(rows).sort_values("decile")
    monotonic_decreasing = bool((by_decile.eff_bp_p50.diff().dropna() <= 0).all())
    monotonic_increasing = bool((by_decile.eff_bp_p50.diff().dropna() >= 0).all())

    out = {
        "task": "T3", "phase": "impact_by_participation",
        "cell": CELL, "cell_note": "effective spread is not itself horizon-conditioned; "
            "restricted to T=0 prints to match T1's cell being on the event day.",
        "effective_spread_definition": "2*|price-mid|/mid (T8's eff_frac, direction-agnostic; "
            "Lee & Ready sign carried but not required for this magnitude measure)",
        "build_cache_wall_seconds": round(secs, 1),
        "n_prints_with_contemporaneous_mid": int(n_prints_with_mid),
        "n_joined_raw_before_dedup": int(n_joined_raw),
        "n_joined_to_a_participation_decile": int(n_joined),
        "join_rate": float(n_joined / n_prints_with_mid) if n_prints_with_mid else None,
        "dedup_note": "joined_raw exceeded n_prints_with_mid by "
            f"{n_joined_raw - n_prints_with_mid:,} rows ({(n_joined_raw/n_prints_with_mid - 1):.2%}) "
            "before dedup -- a small residual tie population on "
            "(ticker, event_date, minute_index, sip_timestamp, size), consistent with Phase "
            "11's T4c tie audit. Deduplicated on the print's own (price, size) added; "
            "sequence_number would resolve these fully but is not carried through _t2.",
        "by_decile": by_decile.to_dict("records"),
        "monotonic_decreasing_in_participation": monotonic_decreasing,
        "monotonic_increasing_in_participation": monotonic_increasing,
        "baseline_round_trip_bp_for_reference": 70.98,
        "source": "research/impact_by_participation/t3_cost_by_decile.py:main",
        "reproduce": ".venv/Scripts/python.exe -m research.impact_by_participation.t3_cost_by_decile",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joined.to_parquet(ARTIFACTS / "t3_cost_by_decile_prints.parquet", index=False)
    (ARTIFACTS / "t3_cost_by_decile.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"T3: {n_prints_with_mid:,} T=0 prints with a contemporaneous mid, "
          f"{n_joined:,} joined to a participation decile ({out['join_rate']:.2%})")
    print(by_decile.to_string(index=False))
    print(f"T3: monotonic decreasing in participation? {monotonic_decreasing}   "
          f"monotonic increasing? {monotonic_increasing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
