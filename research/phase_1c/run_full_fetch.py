"""
Phase 1c T4 - execute the heal manifest.

Fetches each distinct (ticker, session, side) exactly once (the manifest
has multiple event_key rows sharing a pair where flanking windows of
nearby events overlap - 1,966 manifest rows / 1,809 distinct pairs per
T1a), then marks every manifest row referencing that pair with the
outcome. Resumable: pairs already marked fetched/empty/failed-exhausted
in a prior run are skipped on re-run.

T4a: Set A event-day (target_type=event_day) fetches returning zero trades
> 5% of 142 -> hard stop (auth/parameter bug presumption).
T4b: unresolved vendor-side failures (errors, not empties) > 2% of all
distinct pairs -> escalate.
"""
import json
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_pair as fp  # noqa: E402

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

MANIFEST = CFG["paths"]["heal_manifest"]
OUT_SUMMARY = "results/phase_1c/artifacts/t4_fetch_run_summary.json"
FETCH_STATE = "results/phase_1c/artifacts/fetch_state.parquet"
THRESHOLDS = CFG["escalation_thresholds"]


def build_work_items(manifest: pd.DataFrame) -> pd.DataFrame:
    """One row per distinct (ticker, session, side) actually needing a fetch."""
    trades_items = manifest[manifest["fetch_trades"]][["ticker", "session"]].drop_duplicates().assign(side="trades")
    quotes_items = manifest[manifest["fetch_quotes"]][["ticker", "session"]].drop_duplicates().assign(side="quotes")
    return pd.concat([trades_items, quotes_items], ignore_index=True).drop_duplicates()


def main():
    manifest = pd.read_parquet(MANIFEST)
    work = build_work_items(manifest)

    if Path(FETCH_STATE).exists():
        state = pd.read_parquet(FETCH_STATE)
    else:
        state = pd.DataFrame(columns=["ticker", "session", "side", "status", "n_records", "error", "attempt_count"])

    done_keys = set(zip(state["ticker"], state["session"], state["side"])) if not state.empty else set()
    todo = work[~work.apply(lambda r: (r["ticker"], r["session"], r["side"]) in done_keys, axis=1)]
    print(f"work items: {len(work)} total, {len(done_keys)} already resolved, {len(todo)} to fetch")

    api_key = fp.load_api_key()
    session = requests.Session()
    new_rows = []

    for i, (_, item) in enumerate(todo.iterrows()):
        ticker, session_date, side = item["ticker"], item["session"], item["side"]
        try:
            result = fp.fetch_and_stage(session, ticker, session_date, side, api_key)
            new_rows.append({
                "ticker": ticker, "session": session_date, "side": side,
                "status": result["status"], "n_records": result["n_records"], "error": None, "attempt_count": 1,
            })
        except fp.AuthError as e:
            print(f"AUTH ERROR - stopping run: {e}")
            break
        except Exception as e:
            new_rows.append({
                "ticker": ticker, "session": session_date, "side": side,
                "status": "failed", "n_records": 0, "error": str(e), "attempt_count": 1,
            })
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(todo)} fetched...")
            checkpoint = pd.concat([state, pd.DataFrame(new_rows)], ignore_index=True)
            checkpoint.to_parquet(FETCH_STATE, index=False)

    if new_rows:
        state = pd.concat([state, pd.DataFrame(new_rows)], ignore_index=True)
    state.to_parquet(FETCH_STATE, index=False)

    # T4a: Set A event-day zero-trades check
    event_day_pairs = manifest[manifest["target_type"] == "event_day"][["ticker", "session"]].drop_duplicates()
    event_day_state = state.merge(event_day_pairs, on=["ticker", "session"]).query("side == 'trades'")
    n_event_day = len(event_day_pairs)
    n_event_day_zero = int((event_day_state["status"] == "empty").sum())
    t4a_pct = 100 * n_event_day_zero / n_event_day if n_event_day else 0.0
    t4a_triggered = t4a_pct > THRESHOLDS["set_a_event_day_zero_trades_pct_max"]

    # T4b: unresolved failures
    n_total_pairs = len(work)
    n_failed = int((state["status"] == "failed").sum())
    t4b_pct = 100 * n_failed / n_total_pairs if n_total_pairs else 0.0
    t4b_triggered = t4b_pct > THRESHOLDS["unresolved_vendor_failure_pct_max"]

    summary = {
        "phase": "1c", "task": "T4",
        "n_distinct_pairs": n_total_pairs,
        "n_fetched": int((state["status"] == "fetched").sum()),
        "n_empty": int((state["status"] == "empty").sum()),
        "n_failed": n_failed,
        "t4a_set_a_event_day_zero_trades": {
            "n_event_day_pairs": n_event_day, "n_zero_trades": n_event_day_zero,
            "pct": round(t4a_pct, 2), "threshold_pct": THRESHOLDS["set_a_event_day_zero_trades_pct_max"],
            "triggered": t4a_triggered,
        },
        "t4b_unresolved_failures": {
            "n_failed": n_failed, "pct": round(t4b_pct, 2),
            "threshold_pct": THRESHOLDS["unresolved_vendor_failure_pct_max"], "triggered": t4b_triggered,
        },
        "failed_pairs_detail": state[state["status"] == "failed"][["ticker", "session", "side", "error"]].to_dict("records"),
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if t4a_triggered or t4b_triggered:
        raise SystemExit("T4 escalation triggered - see summary. Hard stop per phase prompt.")


if __name__ == "__main__":
    main()
