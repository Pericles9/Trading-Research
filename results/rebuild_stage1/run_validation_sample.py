"""
T4 validation driver -- Trades Rebuild Stage 1.

Runs collect_massive_data_v2.collect_one_event against the fixed 30-event sample
(Group A: known-truncated high-volume; Group B: random low/mid-volume, seed=42;
Group C: random no-quotes-file events, seed=42), audits each output with
auditdb.py's unchanged schema-fingerprint/granularity logic, and checks every
T4/T5 escalation criterion incrementally after each event -- not batched at the
end -- so a rate-limit or truncation signal stops the run rather than being
averaged away across 30 events.

Group A is processed sequentially, one event at a time, ahead of B/C: it carries
the highest per-event volume and is the most likely place to observe rate
limiting, so isolating it event-by-event keeps 429/auth telemetry attributable
and keeps concurrent load on the API low while validating the riskiest cases
first. Groups B/C (low/thin volume) run with the same MAX_WORKERS=4 concurrency
as the original collector, not raised.
"""

import os
import sys
import json
import time
import duckdb
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
import collect_massive_data_v2 as collector

# Inlined verbatim from auditdb.py (not imported -- auditdb.py pulls in tqdm at
# module level, which isn't installed for the system python used to run the
# live collector; these three functions have no tqdm dependency themselves).

def get_schema_fingerprint(con, parquet_path):
    try:
        rows = con.execute(
            'SELECT name, type FROM parquet_schema(?) ORDER BY name', [parquet_path]
        ).fetchall()
        return tuple((r[0], r[1]) for r in rows)
    except Exception as e:
        return (("__ERROR__", str(e)),)


def pick_timestamp_column(fingerprint_cols):
    names = [c[0] for c in fingerprint_cols]
    for candidate in ("sip_timestamp", "participant_timestamp", "trf_timestamp", "timestamp"):
        if candidate in names:
            return candidate
    return None


def detect_unit_and_check_granularity(con, parquet_path, ts_col):
    row = con.execute(
        f'''
        SELECT
            COUNT(*) AS n_trades,
            COUNT(DISTINCT "{ts_col}") AS n_unique_ts,
            MIN("{ts_col}") AS min_ts,
            MAX("{ts_col}") AS max_ts
        FROM read_parquet(?)
        ''',
        [parquet_path],
    ).fetchone()
    n_trades, n_unique_ts, min_ts, max_ts = row

    if n_trades == 0 or min_ts is None:
        return {"n_trades": 0, "n_unique_ts": 0, "unit_guess": None,
                "pct_whole_second": None, "min_ts": None, "max_ts": None}

    mag = abs(max_ts)
    if mag > 1e17:
        unit, divisor = "ns", 1_000_000_000
    elif mag > 1e14:
        unit, divisor = "us", 1_000_000
    elif mag > 1e11:
        unit, divisor = "ms", 1_000
    else:
        unit, divisor = "s", 1

    if unit == "s":
        pct_whole_second = 1.0
    else:
        whole_count = con.execute(
            f'SELECT COUNT(*) FROM read_parquet(?) WHERE CAST("{ts_col}" AS BIGINT) % {divisor} = 0',
            [parquet_path],
        ).fetchone()[0]
        pct_whole_second = whole_count / n_trades

    return {
        "n_trades": n_trades,
        "n_unique_ts": n_unique_ts,
        "unit_guess": unit,
        "pct_whole_second": pct_whole_second,
        "min_ts": min_ts,
        "max_ts": max_ts,
    }

RESULTS_DIR = r"D:\Trading Research\results\rebuild_stage1"
VALIDATION_AUDIT_CSV = os.path.join(RESULTS_DIR, "validation_audit.csv")
GROUP_A_CSV = os.path.join(RESULTS_DIR, "group_a_count_comparison.csv")

GROUP_A = [
    ("AMC", "2021-01-27"), ("OCGN", "2021-02-08"), ("GME", "2021-01-27"), ("PHUN", "2021-10-22"),
    ("GME", "2021-01-25"), ("KODK", "2020-07-29"), ("HTZ", "2020-10-16"), ("SCKT", "2021-02-16"),
    ("VERU", "2022-04-11"), ("OCGN", "2020-12-23"),
]
GROUP_A_OLD_COUNTS = {
    ("AMC", "2021-01-27"): {"legacy": 384997, "current": 6696486},
    ("OCGN", "2021-02-08"): {"legacy": 357000, "current": 3361742},
    ("GME", "2021-01-27"): {"legacy": 393997, "current": 3151694},
    ("PHUN", "2021-10-22"): {"legacy": 404000, "current": 2671951},
    ("GME", "2021-01-25"): {"legacy": 392997, "current": 2140745},
    ("KODK", "2020-07-29"): {"legacy": 389997, "current": 1663618},
    ("HTZ", "2020-10-16"): {"legacy": 392997, "current": 1486613},
    ("SCKT", "2021-02-16"): {"legacy": 431000, "current": 1478830},
    ("VERU", "2022-04-11"): {"legacy": 388000, "current": 1441872},
    ("OCGN", "2020-12-23"): {"legacy": 466000, "current": 1428771},
}
GROUP_B = [
    ("LRMR", "2021-05-12"), ("MARPS", "2025-06-16"), ("NMFC", "2020-03-24"), ("BNRG", "2023-04-10"),
    ("EGHT", "2020-12-10"), ("GRNT", "2022-10-26"), ("BYFC", "2021-07-08"), ("ARTW", "2020-06-17"),
    ("IDAI", "2024-05-23"), ("RGC", "2025-05-29"),
]
GROUP_C = [
    ("AHTpI", "2020-11-09"), ("PMTpB", "2020-03-25"), ("ALMU", "2024-05-14"), ("MITTpC", "2020-04-07"),
    ("IONQ.WS", "2022-05-17"), ("IONQ.WS", "2021-11-17"), ("NLYpI", "2020-03-26"),
    ("AMPX.WS", "2025-07-09"), ("BKKT.WS", "2021-10-29"), ("RBOT.WS", "2021-10-29"),
]

PCT_WHOLE_SECOND_HARD_STOP = 0.01
WALLCLOCK_CAP_SECONDS = 2 * 60 * 60


class Escalation(Exception):
    pass


def audit_and_record(ticker, date_str, group_label, status, detail, elapsed, rl_hit, ae_hit):
    record = {
        "group": group_label, "ticker": ticker, "date": date_str,
        "collector_status": status, "collector_detail": str(detail),
        "elapsed_sec": round(elapsed, 2), "rate_limit_hit": rl_hit, "auth_error_hit": ae_hit,
        "schema_fingerprint": None, "timestamp_col_used": None,
        "n_trades": None, "pct_whole_second": None, "unit_guess": None,
    }
    if status == "written":
        path = os.path.join(collector.OUTPUT_DIR, f"{ticker}_{date_str}_trades.parquet")
        con = duckdb.connect()
        fingerprint = get_schema_fingerprint(con, path)
        ts_col = pick_timestamp_column(fingerprint)
        record["schema_fingerprint"] = json.dumps(fingerprint)
        record["timestamp_col_used"] = ts_col
        if ts_col:
            stats = detect_unit_and_check_granularity(con, path, ts_col)
            record["n_trades"] = stats.get("n_trades")
            record["pct_whole_second"] = stats.get("pct_whole_second")
            record["unit_guess"] = stats.get("unit_guess")
    return record


def check_escalations(record, start_time):
    if record["rate_limit_hit"]:
        raise Escalation(f"429 rate-limit hit during {record['ticker']} {record['date']} "
                          f"(retried automatically by the T2 fix, but per spec this still "
                          f"halts validation for review). Elapsed so far: "
                          f"{time.time() - start_time:.1f}s.")
    if record["auth_error_hit"]:
        raise Escalation(f"401/403 auth error hit during {record['ticker']} {record['date']}.")
    if record["collector_status"] == "failed":
        pass  # per-event validation failure, tallied in go/no-go, not itself an unhandled exception
    pct = record["pct_whole_second"]
    if pct is not None and pct >= PCT_WHOLE_SECOND_HARD_STOP:
        raise Escalation(f"{record['ticker']} {record['date']} pct_whole_second={pct:.4f} "
                          f">= {PCT_WHOLE_SECOND_HARD_STOP:.0%} threshold. "
                          f"schema_fingerprint={record['schema_fingerprint']}")
    if record["group"] == "A":
        old = GROUP_A_OLD_COUNTS[(record["ticker"], record["date"])]
        best_old = max(old["legacy"], old["current"])
        new = record["n_trades"]
        if new is None or new < best_old:
            raise Escalation(f"{record['ticker']} {record['date']}: new count "
                              f"{new} < best old count {best_old} "
                              f"(legacy={old['legacy']}, current={old['current']}).")
    if time.time() - start_time > WALLCLOCK_CAP_SECONDS:
        raise Escalation(f"Wall-clock time exceeded {WALLCLOCK_CAP_SECONDS/3600:.1f}h "
                          f"after {record['ticker']} {record['date']}.")


def run_one(ticker, date_str, group_label):
    t0 = time.time()
    rl_before = collector.RATE_LIMIT_HITS
    ae_before = collector.AUTH_ERROR_HITS
    try:
        status, detail = collector.collect_one_event(ticker, date_str)
    except Exception as e:
        status, detail = "failed", f"UNHANDLED: {e!r}"
    elapsed = time.time() - t0
    rl_hit = collector.RATE_LIMIT_HITS > rl_before
    ae_hit = collector.AUTH_ERROR_HITS > ae_before
    return audit_and_record(ticker, date_str, group_label, status, detail, elapsed, rl_hit, ae_hit)


def main():
    start_time = time.time()
    all_records = []

    print(f"=== Group A ({len(GROUP_A)} events, sequential) ===")
    for ticker, date_str in GROUP_A:
        print(f"  {ticker} {date_str} ...")
        rec = run_one(ticker, date_str, "A")
        all_records.append(rec)
        print(f"    -> {rec['collector_status']} n_trades={rec['n_trades']} "
              f"pct_whole_second={rec['pct_whole_second']} elapsed={rec['elapsed_sec']}s")
        try:
            check_escalations(rec, start_time)
        except Escalation as e:
            _finish(all_records, escalated=True, reason=str(e))
            return

    print(f"\n=== Group B ({len(GROUP_B)} events, concurrency={collector.MAX_WORKERS}) ===")
    with ThreadPoolExecutor(max_workers=collector.MAX_WORKERS) as ex:
        futures = {ex.submit(run_one, t, d, "B"): (t, d) for t, d in GROUP_B}
        for fut in as_completed(futures):
            rec = fut.result()
            all_records.append(rec)
            print(f"  {rec['ticker']} {rec['date']} -> {rec['collector_status']} "
                  f"n_trades={rec['n_trades']} pct_whole_second={rec['pct_whole_second']}")
            try:
                check_escalations(rec, start_time)
            except Escalation as e:
                _finish(all_records, escalated=True, reason=str(e))
                return

    print(f"\n=== Group C ({len(GROUP_C)} events, concurrency={collector.MAX_WORKERS}) ===")
    with ThreadPoolExecutor(max_workers=collector.MAX_WORKERS) as ex:
        futures = {ex.submit(run_one, t, d, "C"): (t, d) for t, d in GROUP_C}
        for fut in as_completed(futures):
            rec = fut.result()
            all_records.append(rec)
            print(f"  {rec['ticker']} {rec['date']} -> {rec['collector_status']} "
                  f"n_trades={rec['n_trades']} pct_whole_second={rec['pct_whole_second']}")
            try:
                check_escalations(rec, start_time)
            except Escalation as e:
                _finish(all_records, escalated=True, reason=str(e))
                return

    _finish(all_records, escalated=False, reason=None, start_time=start_time)


def _finish(records, escalated, reason, start_time=None):
    df = pd.DataFrame(records)
    df.to_csv(VALIDATION_AUDIT_CSV, index=False)

    rows = []
    for (ticker, date_str), old in GROUP_A_OLD_COUNTS.items():
        rec = next((r for r in records if r["ticker"] == ticker and r["date"] == date_str), None)
        new = rec["n_trades"] if rec else None
        best_old = max(old["legacy"], old["current"])
        verdict = "no data (not yet run)" if rec is None else (
            "PASS (meets/exceeds best prior)" if (new is not None and new >= best_old)
            else "FAIL (below best prior)"
        )
        rows.append({"ticker": ticker, "date": date_str, "old_legacy": old["legacy"],
                      "old_current": old["current"], "new_count": new, "verdict": verdict})
    pd.DataFrame(rows).to_csv(GROUP_A_CSV, index=False)

    print(f"\nWrote {len(df)} rows to {VALIDATION_AUDIT_CSV}")
    print(f"Wrote {len(rows)} rows to {GROUP_A_CSV}")

    if escalated:
        print("\n=== ESCALATION: T4 gate failed ===")
        print(f"  {reason}")
        print(f"Partial results: {len(records)}/30 events completed before stop.")
        print("No recommendations -- awaiting instruction.")
    else:
        print(f"\nAll 30 events completed. Total wall-clock: {time.time() - start_time:.1f}s")


if __name__ == "__main__":
    main()
