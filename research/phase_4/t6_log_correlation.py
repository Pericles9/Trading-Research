"""
Phase 4 T6 - collection-log correlation (descriptive only).

Parses data/collection_scripts/collection_log.txt (Confirmed provenance)
for quote-fetch failures, errors, retries, or skips attributable to
specific events, and matches against the 386 quotes-gap cohort (the
population T3 located and T4/T5 bitmapped and classified - "the
quotes-gap population from T3" per the prompt).

The log has three kinds of per-event anchors, in order of specificity:
  - "Processing {ticker} ({event_date}): Window {start} to {end}" -
    unambiguous per-event attempt record (keyed by ticker+event_date+window)
  - "No quotes collected for {ticker} in window [{dates...}]" - explicit
    whole-window quotes failure, matched by ticker + exact window bounds
  - "No quotes found for {ticker} on {date}" / "Saved quotes for {ticker}
    {date} (N records)" - per-session evidence, matched by ticker + date
    falling inside this event's expected T-3..T+3 range

Session-level log lines are NOT uniquely attributable to one event when a
ticker has overlapping event windows (the same session date can appear
in more than one event's window) - matches are therefore descriptive
correlation, not proof of cause, per the prompt's explicit "no causal
language" instruction.

log_evidence categories (per event):
  explicit_failure    - an explicit quotes-failure log line falls in
                         this event's window (whole-window or per-session)
  mentioned_no_failure - the ticker/event appears in the log (processing
                         record, saved trades/quotes, or "no trades found")
                         within this event's window, but no quotes-failure
                         evidence
  not_mentioned        - nothing in the log ties to this ticker/window at all
"""
import json
import re
from collections import defaultdict

import pandas as pd

LOG_PATH = "data/collection_scripts/collection_log.txt"
CLASSIFICATION_PARQUET = "results/phase_4/artifacts/classification.parquet"
OUT_PARQUET = "results/phase_4/artifacts/log_correlation.parquet"
OUT_SUMMARY = "results/phase_4/artifacts/log_correlation_summary.json"

RE_PROCESSING = re.compile(r"Processing (\S+) \((\d{4}-\d{2}-\d{2})\): Window (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})")
RE_SAVED = re.compile(r"Saved (trades|quotes) for (\S+) (\d{4}-\d{2}-\d{2}) \((\d+) records\)")
RE_NOT_FOUND = re.compile(r"No (trades|quotes) found for (\S+) on (\d{4}-\d{2}-\d{2})")
RE_NO_QUOTES_WINDOW = re.compile(r"No quotes collected for (\S+) in window \[(.*?)\]")
RE_SKIPPING_INVALID = re.compile(r"Skipping (\S+): Invalid date None")


def parse_log():
    processing = defaultdict(list)          # ticker -> [(event_date, window_start, window_end, line)]
    saved = defaultdict(list)                # (kind, ticker) -> [(date, n, line)]
    not_found = defaultdict(list)            # (kind, ticker) -> [(date, line)]
    no_quotes_window = defaultdict(list)     # ticker -> [(window_dates:list[str], line)]
    n_skipping = 0
    n_lines = 0
    n_generic_error = 0
    n_retry = 0

    with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
        for line in f:
            n_lines += 1
            line = line.rstrip("\n")
            m = RE_PROCESSING.search(line)
            if m:
                ticker, ed, ws, we = m.groups()
                processing[ticker].append((ed, ws, we, line))
                continue
            m = RE_SAVED.search(line)
            if m:
                kind, ticker, d, n = m.groups()
                saved[(kind, ticker)].append((d, int(n), line))
                continue
            m = RE_NOT_FOUND.search(line)
            if m:
                kind, ticker, d = m.groups()
                not_found[(kind, ticker)].append((d, line))
                continue
            m = RE_NO_QUOTES_WINDOW.search(line)
            if m:
                ticker, dates_str = m.groups()
                dates = re.findall(r"\d{4}-\d{2}-\d{2}", dates_str)
                no_quotes_window[ticker].append((dates, line))
                continue
            if RE_SKIPPING_INVALID.search(line):
                n_skipping += 1
                continue
            if "Worker exception" in line or "Exception during fetch" in line or "Error checking dates" in line:
                n_generic_error += 1
                continue
            if "Retrying" in line:
                n_retry += 1

    return {
        "n_lines": n_lines,
        "processing": processing, "saved": saved, "not_found": not_found,
        "no_quotes_window": no_quotes_window,
        "n_skipping_invalid_date": n_skipping,
        "n_generic_error_lines": n_generic_error,
        "n_retry_lines": n_retry,
    }


def main():
    print(f"parsing {LOG_PATH}...")
    log = parse_log()
    print(f"{log['n_lines']} lines parsed; "
          f"{sum(len(v) for v in log['processing'].values())} processing records, "
          f"{sum(len(v) for v in log['no_quotes_window'].values())} no-quotes-window records, "
          f"{log['n_generic_error_lines']} generic error lines, {log['n_retry_lines']} retry lines, "
          f"{log['n_skipping_invalid_date']} skip-invalid-date lines")

    cohort = pd.read_parquet(CLASSIFICATION_PARQUET)
    print(f"quotes-gap cohort (from T3/T4/T5): {len(cohort)}")

    records = []
    for _, row in cohort.iterrows():
        ticker = row["ticker"]
        event_day = pd.Timestamp(row["event_day"]).date()
        exp_m3 = pd.Timestamp(row["expected_t_minus_3"]).date() if pd.notna(row["expected_t_minus_3"]) else None
        # reconstruct expected_t_plus_3 isn't stored on classification.parquet directly under that name;
        # use bitmap length/window instead - but window end was captured in quotes_bitmaps.parquet already,
        # so re-derive from the processing record windows or fall back to event_day if unknown
        evidence = "not_mentioned"
        matched_lines = []

        # 1. processing record for this exact event
        proc_matches = [p for p in log["processing"].get(ticker, []) if p[0] == str(event_day)]
        window_start = window_end = None
        if proc_matches:
            window_start, window_end = proc_matches[0][1], proc_matches[0][2]
            matched_lines.append(proc_matches[0][3])
            evidence = "mentioned_no_failure"

        # window bounds fallback: use exp_m3..(event_day) at minimum if no processing record
        lo = window_start or (str(exp_m3) if exp_m3 else str(event_day))
        hi = window_end  # may be None; per-session checks below don't strictly need hi

        # 2. whole-window explicit quotes failure
        for dates, line in log["no_quotes_window"].get(ticker, []):
            if not dates:
                continue
            if dates[0] == lo and (hi is None or dates[-1] == hi):
                evidence = "explicit_failure"
                matched_lines.append(line)

        # 3. per-session explicit "no quotes found" within this event's window
        if window_start and window_end:
            for d, line in log["not_found"].get(("quotes", ticker), []):
                if window_start <= d <= window_end:
                    evidence = "explicit_failure"
                    matched_lines.append(line)
            # positive/other mentions strengthen "mentioned_no_failure" if not already explicit_failure
            for d, n, line in log["saved"].get(("quotes", ticker), []):
                if window_start <= d <= window_end:
                    matched_lines.append(line)
                    if evidence == "not_mentioned":
                        evidence = "mentioned_no_failure"
            for d, n, line in log["saved"].get(("trades", ticker), []):
                if window_start <= d <= window_end:
                    if evidence == "not_mentioned":
                        evidence = "mentioned_no_failure"
            for d, line in log["not_found"].get(("trades", ticker), []):
                if window_start <= d <= window_end:
                    if evidence == "not_mentioned":
                        evidence = "mentioned_no_failure"

        records.append({
            "ticker": ticker, "event_day": row["event_day"], "label": row["label"],
            "log_evidence": evidence,
            "n_matched_lines": len(matched_lines),
            "matched_lines_sample": matched_lines[:5],
            "has_processing_record": bool(proc_matches),
        })

    df = pd.DataFrame(records)
    df.to_parquet(OUT_PARQUET, index=False)

    evidence_counts = df["log_evidence"].value_counts().to_dict()
    evidence_by_label = df.groupby(["label", "log_evidence"]).size().unstack(fill_value=0).to_dict(orient="index")

    examples = {}
    for ev in ("explicit_failure", "mentioned_no_failure", "not_mentioned"):
        sub = df[df["log_evidence"] == ev]
        examples[ev] = sub.head(3)[["ticker", "event_day", "matched_lines_sample"]].to_dict(orient="records")

    summary = {
        "phase": "4", "task": "T6",
        "note": "Descriptive only. No causal language. Session-level log lines are not uniquely attributable when a ticker has overlapping event windows.",
        "n_cohort": len(df),
        "log_stats": {
            "n_lines": log["n_lines"],
            "n_processing_records": sum(len(v) for v in log["processing"].values()),
            "n_no_quotes_window_records": sum(len(v) for v in log["no_quotes_window"].values()),
            "n_generic_error_lines": log["n_generic_error_lines"],
            "n_retry_lines": log["n_retry_lines"],
            "n_skipping_invalid_date_lines": log["n_skipping_invalid_date"],
        },
        "log_evidence_counts": {str(k): int(v) for k, v in evidence_counts.items()},
        "log_evidence_counts_pct": {str(k): round(100 * int(v) / len(df), 2) for k, v in evidence_counts.items()},
        "log_evidence_by_label": {str(k): {str(k2): int(v2) for k2, v2 in v.items()} for k, v in evidence_by_label.items()},
        "examples": examples,
        "source": "research/phase_4/t6_log_correlation.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "examples"}, indent=2, default=str))


if __name__ == "__main__":
    main()
