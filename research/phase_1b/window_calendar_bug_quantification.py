"""
Phase 1b T5-R3 - blast-radius quantification of the window-calendar bug.

For every in-scope event, replicates collect_massive_data.py's
get_trading_window() logic exactly (federal-business-day stepping) and
compares it against the true XNYS session sequence around the event's
anchor date. Two damage types:
  - missing_session: a true XNYS session within T-3..T+3 that the legacy
    federal-business-day stepping skipped (because it fell on a Set A
    "phantom holiday") - that session was never collected, and the
    legacy window extended one session further out (T-4/T+4) to
    compensate, since date_range(start,end,freq=us_bd) always yields the
    same *count* of business-day positions.
  - short_window: a legacy-stepped position that lands on a Set B
    "phantom session" date (XNYS closed) - the collector fetched that
    date but the market was shut, so that slot is structurally empty
    (one fewer real trading day than intended).
"""
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

EVENT_FLAGS = "results/phase_1b/artifacts/event_flags.parquet"
CLASSIFICATION = "results/phase_1b/artifacts/instrument_classification.parquet"
CALENDAR_MISMATCH = "results/phase_1b/artifacts/t5r1_calendar_mismatch.json"
DB_PATH = "data/duckdb/main.duckdb"
OUT_PARQUET = "results/phase_1b/artifacts/window_damage.parquet"
OUT_SUMMARY = "results/phase_1b/artifacts/t5r3_window_damage_summary.json"

START, END = "2019-12-01", "2026-01-15"  # padded beyond the event range for T-3/T+3 lookups at the edges


def legacy_window(center_date: pd.Timestamp, us_bd) -> list[pd.Timestamp]:
    start_date = center_date - 3 * us_bd
    end_date = center_date + 3 * us_bd
    return list(pd.date_range(start_date, end_date, freq=us_bd))


def main():
    with open(CALENDAR_MISMATCH) as f:
        cm = json.load(f)
    set_a = set(pd.Timestamp(d) for d in cm["set_a_phantom_holidays"]["dates"])
    set_b = set(pd.Timestamp(d) for d in cm["set_b_phantom_sessions"]["dates"])

    fed_cal = USFederalHolidayCalendar()
    us_bd = CustomBusinessDay(calendar=fed_cal)

    xnys = mcal.get_calendar("XNYS")
    xnys_sessions = pd.DatetimeIndex(xnys.schedule(start_date=START, end_date=END).index).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}

    con = duckdb.connect(read_only=False)
    flags = con.execute(f"SELECT * FROM read_parquet('{EVENT_FLAGS}')").fetchdf()
    cls = con.execute(f"SELECT ticker, class AS instrument_class FROM read_parquet('{CLASSIFICATION}')").fetchdf()
    df = flags.merge(cls, on="ticker", how="left")

    in_scope = df[
        df["instrument_class"].isin(["common", "common_adr"])
        & ~df["flag_missing_event_day"].fillna(False)
    ].copy()
    # flag_bad_denominator lives on the raw table / view, not event_flags - pull it in
    con_db = duckdb.connect(database=DB_PATH, read_only=True)
    bad_denom = con_db.execute(
        "SELECT ticker, COALESCE(date, event_date) AS event_date_canonical, "
        "(prev_close < 0.01 OR momentum_pct >= 10000) AS flag_bad_denominator FROM momentum_events"
    ).fetchdf()
    con_db.close()
    bad_denom["event_date_str"] = bad_denom["event_date_canonical"].astype(str)
    in_scope["event_date_str"] = in_scope["event_date_canonical"].astype(str)
    in_scope = in_scope.merge(bad_denom[["ticker", "event_date_str", "flag_bad_denominator"]], on=["ticker", "event_date_str"], how="left")
    in_scope = in_scope[
        ~in_scope["flag_bad_denominator"].fillna(False)
        & ~in_scope["flag_trades_mom_outlier"].fillna(False)
    ]
    n_in_scope = len(in_scope)
    print(f"in-scope population for T5-R3: {n_in_scope}")

    offsets = [-3, -2, -1, 1, 2, 3]
    results = []
    anchor_on_set_a = []  # distinct anomaly - anchor date itself in Set A but has trades
    for _, row in in_scope.iterrows():
        d = pd.Timestamp(row["event_date_canonical"])
        if d not in session_pos:
            continue  # shouldn't happen for in-scope events, but guard
        i0 = session_pos[d]
        true_window = {k: xnys_sessions[i0 + k] for k in offsets}
        legacy_dates_list = legacy_window(d, us_bd)

        if d in set_a:
            # Anchor date itself is a phantom holiday - get_trading_window's
            # date_range never includes a non-business-day center, so the
            # 7-slot legacy/true offset mapping this loop relies on doesn't
            # apply. These events have trades on the anchor day (else they'd
            # be flag_missing_event_day), unlike the 142-event pattern -
            # a distinct anomaly, recorded separately, not offset-mapped.
            anchor_on_set_a.append({"ticker": row["ticker"], "event_date_canonical": str(d.date())})
            results.append({
                "ticker": row["ticker"], "event_date_canonical": str(d.date()),
                "damaged_offsets": {"0": "anchor_on_set_a"},
            })
            continue

        legacy_dates = set(legacy_dates_list)
        sorted_legacy = sorted(legacy_dates)
        damaged_offsets = {}
        for k in offsets:
            missing = true_window[k] not in legacy_dates
            idx = offsets.index(k) if offsets.index(k) < 3 else offsets.index(k) + 1
            legacy_approx = sorted_legacy[idx] if idx < len(sorted_legacy) else None
            short = legacy_approx in set_b if legacy_approx is not None else False
            if missing:
                damaged_offsets[str(k)] = "missing_session"
            elif short:
                damaged_offsets[str(k)] = "short_window"

        if damaged_offsets:
            results.append({
                "ticker": row["ticker"], "event_date_canonical": str(d.date()),
                "damaged_offsets": damaged_offsets,
            })

    n_flagged = len(results)
    flagged_pct = 100 * n_flagged / n_in_scope if n_in_scope else 0.0

    offset_counts: dict[str, dict[str, int]] = {str(k): {"missing_session": 0, "short_window": 0} for k in offsets}
    for r in results:
        for off, dtype in r["damaged_offsets"].items():
            if off == "0":
                continue  # anchor_on_set_a - distinct anomaly, tracked separately below
            offset_counts[off][dtype] += 1

    damage_type_totals = {"missing_session": 0, "short_window": 0}
    for off in offset_counts.values():
        damage_type_totals["missing_session"] += off["missing_session"]
        damage_type_totals["short_window"] += off["short_window"]

    flagged_df = pd.DataFrame(results)
    if not flagged_df.empty:
        flagged_df["event_date_canonical"] = pd.to_datetime(flagged_df["event_date_canonical"])
        flagged_df["damaged_offsets_json"] = flagged_df["damaged_offsets"].apply(json.dumps)
        flagged_df[["ticker", "event_date_canonical", "damaged_offsets_json"]].to_parquet(OUT_PARQUET, index=False)

    # Corroboration check: the "extra outer session" prediction only applies
    # to missing_session damage AT the outer offsets (-3 or +3) - a Set A
    # date there forces the legacy stepping one session further out. Damage
    # at inner offsets, or missing_session caused by a Set B date consuming a
    # step without extending reach (e.g. Good Friday mid-window), doesn't
    # predict an extra T-4/T+4 session - sampling those would test the wrong
    # thing. Filtered to outer-offset missing_session cases only.
    con2 = duckdb.connect(database=DB_PATH, read_only=True)

    def has_outer_missing(j):
        d = json.loads(j)
        return d.get("-3") == "missing_session" or d.get("3") == "missing_session"

    outer_missing_mask = flagged_df["damaged_offsets_json"].apply(has_outer_missing) if not flagged_df.empty else pd.Series(dtype=bool)
    sample = flagged_df[outer_missing_mask].head(20) if not flagged_df.empty else pd.DataFrame()
    corroboration = []
    for _, r in sample.iterrows():
        ticker, d = r["ticker"], pd.Timestamp(r["event_date_canonical"])
        i0 = session_pos[d]
        t4_before = xnys_sessions[i0 - 4]
        t4_after = xnys_sessions[i0 + 4]
        damaged = json.loads(r["damaged_offsets_json"])
        # find folder name via momentum_pct
        mom = con2.execute(
            "SELECT momentum_pct FROM momentum_events WHERE ticker=? AND (date=? OR event_date=?) LIMIT 1",
            [ticker, str(d.date()), str(d.date())],
        ).fetchone()
        mom_str = f"{mom[0]:.2f}" if mom else None
        folder = f"data/filtered/{ticker}_{d.date()}_{mom_str}" if mom_str else None
        has_t4_before = has_t4_after = None
        if folder:
            try:
                cnt_before = duckdb.sql(
                    f"SELECT COUNT(*) FROM read_parquet('{folder}/trades.parquet') "
                    f"WHERE CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = DATE '{t4_before.date()}'"
                ).fetchone()[0]
                has_t4_before = cnt_before > 0
            except Exception:
                pass
            try:
                cnt_after = duckdb.sql(
                    f"SELECT COUNT(*) FROM read_parquet('{folder}/trades.parquet') "
                    f"WHERE CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = DATE '{t4_after.date()}'"
                ).fetchone()[0]
                has_t4_after = cnt_after > 0
            except Exception:
                pass
        relevant_confirmed = (
            (has_t4_before if damaged.get("-3") == "missing_session" else True)
            and (has_t4_after if damaged.get("3") == "missing_session" else True)
        )
        corroboration.append({
            "ticker": ticker, "event_date": str(d.date()), "damaged_offsets": damaged,
            "t4_before_date": str(t4_before.date()), "has_t4_before_session": has_t4_before,
            "t4_after_date": str(t4_after.date()), "has_t4_after_session": has_t4_after,
            "relevant_side_confirmed": relevant_confirmed,
        })
    con2.close()
    n_corroborated = sum(1 for c in corroboration if c["relevant_side_confirmed"])

    # Consolidate flag_window_calendar_bug into event_flags.parquet so the
    # canonical view's t6-stage join picks it up alongside the other flags.
    # Drop any stale columns from a prior run of this script for idempotency.
    flags = con.execute(f"SELECT * FROM read_parquet('{EVENT_FLAGS}')").fetchdf()
    flags = flags.drop(columns=["flag_window_calendar_bug", "window_damage_offsets_json"], errors="ignore")
    flags["event_date_str"] = flags["event_date_canonical"].astype(str)
    if not flagged_df.empty:
        damage_lookup = flagged_df[["ticker", "event_date_canonical", "damaged_offsets_json"]].copy()
        damage_lookup["event_date_str"] = damage_lookup["event_date_canonical"].astype(str)
        flags = flags.merge(
            damage_lookup[["ticker", "event_date_str", "damaged_offsets_json"]]
            .rename(columns={"damaged_offsets_json": "window_damage_offsets_json"}),
            on=["ticker", "event_date_str"], how="left",
        )
    else:
        flags["window_damage_offsets_json"] = None
    flags["flag_window_calendar_bug"] = flags["window_damage_offsets_json"].notna()
    flags_out_cols = ["ticker", "event_date_canonical", "momentum_pct", "n_trades_event_day",
                       "flag_trades_mom_outlier", "flag_zero_event_day_trades",
                       "zero_trades_cause", "flag_missing_event_day", "scope_pending_repair",
                       "flag_window_calendar_bug", "window_damage_offsets_json"]
    flags[flags_out_cols].to_parquet(EVENT_FLAGS, index=False)
    print(f"event_flags.parquet updated: {int(flags['flag_window_calendar_bug'].sum())} flag_window_calendar_bug=TRUE")

    summary = {
        "phase": "1b", "task": "T5-R3",
        "n_in_scope_population": n_in_scope,
        "n_flagged_window_calendar_bug": n_flagged,
        "flagged_pct_of_in_scope": round(flagged_pct, 4),
        "escalation_threshold_n": 3000,
        "escalation_triggered": n_flagged > 3000,
        "damage_by_offset": offset_counts,
        "damage_type_totals": damage_type_totals,
        "corroboration_sample": {
            "n_sampled": len(corroboration),
            "n_corroborated": n_corroborated,
            "note": "Sample restricted to missing_session damage at the outer offsets "
            "(-3 or +3) specifically - the only cases where the extra-outer-session "
            "prediction applies. Damage at inner offsets, or missing_session caused by "
            "a Set B date consuming a legacy step without extending window reach (e.g. "
            "Good Friday mid-window), doesn't predict a T-4/T+4 session.",
            "rows": corroboration,
        },
        "surprises": {
            "anchor_on_set_a": {
                "n": len(anchor_on_set_a),
                "description": "In-scope events whose anchor date itself falls in Set A "
                "(e.g. Columbus Day 2025-10-13) but which - unlike the 142-event "
                "flag_missing_event_day pattern - DO have trades on the anchor day. The "
                "get_trading_window(D) date_range never includes D itself when D is not a "
                "valid business day per the federal calendar, so the offset-mapping logic "
                "used for the rest of this quantification does not apply cleanly to these "
                "events. Flagged flag_window_calendar_bug=TRUE with damaged_offsets={'0': "
                "'anchor_on_set_a'} rather than a T-3..T+3 offset breakdown. Not "
                "root-caused further - out of Amendment 3's defined scope (quantify the "
                "already-diagnosed mechanism, not investigate new ones).",
                "events": anchor_on_set_a,
            },
        },
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
