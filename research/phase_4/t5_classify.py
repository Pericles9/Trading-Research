"""
Phase 4 T5 - root-cause classification of the 386 quotes-cohort.

Same label vocabulary as Phase 3 (backward_missing, forward_missing,
calendar_residue, both_sides, archive_edge, unclassified) but a changed
precedence design, per the phase prompt's approval-gate discussion:

  Phase 3's precedence intercepted on calendar_residue FIRST (flag_
  window_calendar_bug OR repaired_1c), which produced a label coarser
  than the true bitmap-shape cause for 21 of 35 calendar_residue events
  - the flag says "this event's window has calendar-bug damage" but
  doesn't say which offsets are actually missing or in what pattern.
  The quotes side starts clean (no known prior calendar-bug remediation
  applied to quotes_full_window), so this phase does NOT intercept on
  those flags. Primary "label" is bitmap-first:

    1. archive_edge   - expected_t_minus_3 or expected_t_plus_3 falls
                         outside the observed file1 filtered_quotes
                         session-date range (still a structural, not a
                         flag-based, condition - unaffected by the
                         calendar_residue critique, so kept in its
                         original precedence position)
    2. forward_missing - all missing offsets >= +1
    3. backward_missing - all missing offsets <= -1
    4. both_sides       - missing offsets on both sides of T=0
    5. unclassified      - none of the above (should be empty by
                          construction, same as Phase 3)

  repaired_1c and flag_window_calendar_bug are carried as separate
  boolean ANNOTATION columns - informative, but they do not intercept
  or override the bitmap-derived label.

For cross-phase comparability, `label_p3_precedence` is ALSO computed,
applying Phase 3's exact original rule (calendar_residue intercepts
first) side by side with the new `label` column.

Reuses T4's cached full actual-quotes-sessions result
(_actual_quotes_sessions_cache.parquet) - no second full-table scan of
filtered_quotes, per the phase's single-full-table-pass commitment.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
PHASE_4_CONFIG = "config/phase_4.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
BITMAP_PARQUET = "results/phase_4/artifacts/quotes_bitmaps.parquet"
CACHE_PARQUET = "results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet"
OUT_PARQUET = "results/phase_4/artifacts/classification.parquet"
OUT_SUMMARY = "results/phase_4/artifacts/classification_summary.json"


def all_inscope_events(con, prev_close_floor, mom_sanity_cap):
    sql = f"""
    WITH canonical AS (
        SELECT
            me.ticker,
            COALESCE(me.date, me.event_date) AS event_date_canonical,
            me.momentum_pct,
            CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2' END AS source_file,
            ic.class AS instrument_class,
            (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
            ef.flag_trades_mom_outlier AS flag_trades_mom_outlier,
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day,
            COALESCE(ef.flag_window_calendar_bug, FALSE) AS flag_window_calendar_bug,
            COALESCE(ef.repaired_1c, FALSE) AS repaired_1c
        FROM momentum_events me
        LEFT JOIN read_parquet('{CLASSIFICATION_PATH}') ic ON me.ticker = ic.ticker
        LEFT JOIN read_parquet('{EVENT_FLAGS_PATH}') ef
          ON me.ticker = ef.ticker
         AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
    ),
    scoped AS (
        SELECT *,
            (instrument_class IN ('common', 'common_adr')
             AND NOT flag_bad_denominator
             AND NOT COALESCE(flag_trades_mom_outlier, FALSE)
             AND NOT flag_missing_event_day) AS in_scope
        FROM canonical
    )
    SELECT ticker, event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp, source_file,
           flag_window_calendar_bug, repaired_1c
    FROM scoped WHERE in_scope
    """
    return con.execute(sql).fetchdf()


def main():
    with open(PHASE_1B_CONFIG) as f:
        cfg1b = json.load(f)
    prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]

    with open(PHASE_4_CONFIG) as f:
        cfg4 = json.load(f)
    unclass_max_pct = cfg4["escalation_thresholds"]["unclassified_remainder_max_pct"]

    con = duckdb.connect(DB_PATH, read_only=True)
    events = all_inscope_events(con, prev_close_floor, mom_sanity_cap)
    con.close()
    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    print(f"all in-scope events (lightweight replica, for flags + source_file): {len(events)}")

    bmp = pd.read_parquet(BITMAP_PARQUET)
    n_cohort = len(bmp)
    print(f"bitmapped cohort (from T4): {n_cohort}")

    cache = pd.read_parquet(CACHE_PARQUET)
    cache["mom_2dp"] = cache["mom_2dp"].round(2)

    # --- file1 observed quotes session-date range (archive_edge rule) ---
    # ticker+event_date is sufficient here (mom_2dp already folded into the cache's own join key)
    events_file1_keys = set(zip(events.loc[events["source_file"] == "file1", "ticker"],
                                 events.loc[events["source_file"] == "file1", "event_date_canonical"]))
    cache_key_no_mom = list(zip(cache["ticker"], cache["event_date_canonical"]))
    cache["is_file1"] = [k in events_file1_keys for k in cache_key_no_mom]
    file1_min = cache.loc[cache["is_file1"], "session_date"].min()
    file1_max = cache.loc[cache["is_file1"], "session_date"].max()
    print(f"file1 observed quotes session-date range: {file1_min.date()} .. {file1_max.date()}")

    # --- per-ticker last-seen / first-seen quotes session date across ALL in-scope events ---
    ticker_max_date = cache.groupby("ticker")["session_date"].max()
    ticker_min_date = cache.groupby("ticker")["session_date"].min()

    # --- flags per cohort event (annotations, not label-determining) ---
    events_idx = events.set_index(["ticker", "event_date_canonical"])

    def get_flags(ticker, event_day):
        try:
            row = events_idx.loc[(ticker, event_day)]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            return bool(row["flag_window_calendar_bug"]), bool(row["repaired_1c"])
        except KeyError:
            return False, False

    records = []
    for _, row in bmp.iterrows():
        ticker, d, mom = row["ticker"], row["event_day"], row["momentum_pct"]
        missing_offsets = list(row["missing_offsets"])
        bitmap = row["bitmap"]
        exp_m3, exp_p3 = row["expected_t_minus_3"], row["expected_t_plus_3"]

        archive_edge = bool((pd.notna(exp_m3) and exp_m3 < file1_min) or (pd.notna(exp_p3) and exp_p3 > file1_max))

        flag_cal_bug, repaired = get_flags(ticker, d)

        # --- bitmap-first label (this phase's primary classification) ---
        if archive_edge:
            label = "archive_edge"
        elif missing_offsets and all(k >= 1 for k in missing_offsets):
            label = "forward_missing"
        elif missing_offsets and all(k <= -1 for k in missing_offsets):
            label = "backward_missing"
        elif missing_offsets:
            label = "both_sides"
        else:
            label = "unclassified"  # structurally unexpected - cohort member with no missing offsets

        # --- Phase 3 exact-precedence crosswalk label ---
        if flag_cal_bug or repaired:
            label_p3 = "calendar_residue"
        elif archive_edge:
            label_p3 = "archive_edge"
        elif missing_offsets and all(k >= 1 for k in missing_offsets):
            label_p3 = "forward_missing"
        elif missing_offsets and all(k <= -1 for k in missing_offsets):
            label_p3 = "backward_missing"
        elif missing_offsets:
            label_p3 = "both_sides"
        else:
            label_p3 = "unclassified"

        records.append({
            "ticker": ticker, "event_day": d, "momentum_pct": mom,
            "bitmap": bitmap, "missing_offsets": missing_offsets, "n_missing": row["n_missing"],
            "label": label, "label_p3_precedence": label_p3,
            "flag_window_calendar_bug": flag_cal_bug, "repaired_1c": repaired, "archive_edge": archive_edge,
            "expected_t_minus_3": exp_m3,
        })

    df = pd.DataFrame(records)

    # --- T5a: weak signatures (same definitions as Phase 3 T3a / A1-T4), on the bitmap-first label ---
    fwd = df[df["label"] == "forward_missing"].copy()
    fwd["ticker_last_seen"] = fwd["ticker"].map(ticker_max_date)
    fwd["is_last_seen_signature"] = fwd["event_day"] == fwd["ticker_last_seen"]
    n_fwd = len(fwd)
    n_fwd_signature = int(fwd["is_last_seen_signature"].sum())
    df["is_last_seen_signature"] = False
    if len(fwd):
        df.loc[df["label"] == "forward_missing", "is_last_seen_signature"] = fwd.set_index(fwd.index)["is_last_seen_signature"]

    bwd = df[df["label"] == "backward_missing"].copy()
    bwd["ticker_first_seen"] = bwd["ticker"].map(ticker_min_date)
    bwd["weak_listing_signature"] = bwd["ticker_first_seen"] > bwd["expected_t_minus_3"]
    n_bwd = len(bwd)
    n_bwd_signature = int(bwd["weak_listing_signature"].sum())
    df["weak_listing_signature"] = False
    if len(bwd):
        df.loc[df["label"] == "backward_missing", "weak_listing_signature"] = bwd.set_index(bwd.index)["weak_listing_signature"]

    df.to_parquet(OUT_PARQUET, index=False)

    # --- cross-tabs ---
    label_counts = df["label"].value_counts().to_dict()
    label_p3_counts = df["label_p3_precedence"].value_counts().to_dict()
    bitmap_by_label = {label: sub["bitmap"].value_counts().head(3).to_dict() for label, sub in df.groupby("label")}
    df["year"] = df["event_day"].dt.year
    label_by_year = df.groupby(["year", "label"]).size().unstack(fill_value=0).to_dict(orient="index")

    # --- crosswalk: label (bitmap-first) x label_p3_precedence ---
    crosswalk = pd.crosstab(df["label"], df["label_p3_precedence"])

    n_unclassified = label_counts.get("unclassified", 0)
    unclassified_pct = n_unclassified / n_cohort if n_cohort else 0.0

    summary = {
        "phase": "4", "task": "T5",
        "n_cohort": n_cohort,
        "file1_observed_quotes_session_date_range": {"min": str(file1_min.date()), "max": str(file1_max.date())},
        "label_counts": {str(k): int(v) for k, v in label_counts.items()},
        "label_counts_pct_of_cohort": {str(k): round(100 * int(v) / n_cohort, 2) for k, v in label_counts.items()},
        "label_p3_precedence_counts": {str(k): int(v) for k, v in label_p3_counts.items()},
        "label_p3_precedence_counts_pct_of_cohort": {str(k): round(100 * int(v) / n_cohort, 2) for k, v in label_p3_counts.items()},
        "label_vs_label_p3_precedence_crosswalk": {str(i): {str(c): int(v) for c, v in row.items()} for i, row in crosswalk.iterrows()},
        "bitmap_top3_by_label": bitmap_by_label,
        "label_by_year": {str(k): {str(k2): int(v2) for k2, v2 in v.items()} for k, v in label_by_year.items()},
        "t5a_forward_missing_signature": {
            "n_forward_missing": n_fwd,
            "n_is_last_seen_signature": n_fwd_signature,
            "note": "weak within-archive delisting signature - same definition as Phase 3 T3a, applied quotes-side. Not proof of delisting; within-archive only.",
        },
        "t5a_backward_missing_signature": {
            "n_backward_missing": n_bwd,
            "n_weak_listing_signature": n_bwd_signature,
            "note": "weak within-archive listing signature - same definition as Phase 3 A1-T4, applied quotes-side. Not proof of late listing; within-archive only, external reference data out of scope.",
        },
        "precedence_design_note": (
            "Bitmap-first: label intercepts only on archive_edge (structural, unaffected by the "
            "calendar_residue critique) then falls through to forward_missing/backward_missing/"
            "both_sides purely off the missing-offset pattern. flag_window_calendar_bug and "
            "repaired_1c are carried as annotation columns only and do not appear as a 'calendar_residue' "
            "label in the primary `label` column - see label_p3_precedence for the Phase-3-equivalent rule."
        ),
        "escalation_check_row4": {
            "condition": "unclassified label count > 30% of 386",
            "threshold_pct": 100 * unclass_max_pct,
            "observed_n": n_unclassified,
            "observed_pct": round(100 * unclassified_pct, 2),
            "triggered": unclassified_pct > unclass_max_pct,
        },
        "source": "research/phase_4/t5_classify.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("label_by_year", "bitmap_top3_by_label")}, indent=2, default=str))

    if summary["escalation_check_row4"]["triggered"]:
        print("\n*** ESCALATION row 4: unclassified > 30% of 386 - see bitmap pattern table ***")


if __name__ == "__main__":
    main()
