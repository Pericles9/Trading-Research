"""
Phase 1c T5 - resolve the 8 unknown-cause flag_missing_event_day events
using their diagnostic fetches (already run as part of T4's manifest
execution - target_type=diagnostic_unknown, both sides fetched).

Vendor returns trades for the event day -> reclassify zero_trades_cause to
collection_failure, pair joins the heal set (T6 will ingest it like any
other healed pair).
Vendor confirms zero trades -> confirmed_zero_event_day_trades=TRUE,
permanently out of scope, cause closed. Annotate (not gate on) whether
vendor quotes exist that day - a halt-signature indicator only.
"""
import json

import pandas as pd

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

MANIFEST = CFG["paths"]["heal_manifest"]
FETCH_STATE = "results/phase_1c/artifacts/fetch_state.parquet"
OUT_RESOLUTION = "results/phase_1c/artifacts/t5_unknowns_resolution.parquet"
OUT_SUMMARY = "results/phase_1c/artifacts/t5_unknowns_summary.json"


def main():
    manifest = pd.read_parquet(MANIFEST)
    state = pd.read_parquet(FETCH_STATE)

    diag = manifest[manifest["target_type"] == "diagnostic_unknown"][["ticker", "session", "event_key"]].drop_duplicates()
    assert len(diag) == 8, f"expected 8 diagnostic_unknown pairs, found {len(diag)}"

    trades_state = state[state["side"] == "trades"]
    quotes_state = state[state["side"] == "quotes"]

    rows = []
    for _, d in diag.iterrows():
        t_row = trades_state[(trades_state["ticker"] == d["ticker"]) & (trades_state["session"] == d["session"])]
        q_row = quotes_state[(quotes_state["ticker"] == d["ticker"]) & (quotes_state["session"] == d["session"])]
        t_status = t_row.iloc[0]["status"] if len(t_row) else "not_fetched"
        t_n = int(t_row.iloc[0]["n_records"]) if len(t_row) else None
        q_status = q_row.iloc[0]["status"] if len(q_row) else "not_fetched"
        q_n = int(q_row.iloc[0]["n_records"]) if len(q_row) else None

        if t_status == "fetched" and t_n and t_n > 0:
            resolution = "collection_failure"
            joins_heal_set = True
            confirmed_zero = False
        elif t_status == "empty":
            resolution = "confirmed_zero_event_day_trades"
            joins_heal_set = False
            confirmed_zero = True
        else:
            resolution = f"unresolved (trades fetch status={t_status})"
            joins_heal_set = False
            confirmed_zero = False

        rows.append({
            "event_key": d["event_key"], "ticker": d["ticker"], "session": d["session"],
            "trades_fetch_status": t_status, "n_trades_fetched": t_n,
            "quotes_fetch_status": q_status, "n_quotes_fetched": q_n,
            "possible_full_day_halt_signature": (q_n or 0) > 0 and (t_n or 0) == 0,
            "resolution": resolution, "joins_heal_set": joins_heal_set,
            "confirmed_zero_event_day_trades": confirmed_zero,
        })

    resolution_df = pd.DataFrame(rows)
    resolution_df.to_parquet(OUT_RESOLUTION, index=False)

    summary = {
        "phase": "1c", "task": "T5",
        "n_events": len(resolution_df),
        "n_collection_failure": int((resolution_df["resolution"] == "collection_failure").sum()),
        "n_confirmed_zero": int(resolution_df["confirmed_zero_event_day_trades"].sum()),
        "n_unresolved": int(resolution_df["resolution"].str.startswith("unresolved").sum()),
        "rows": resolution_df.to_dict("records"),
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if summary["n_unresolved"] > 0:
        raise SystemExit("T5: unresolved diagnostic pairs remain (fetch not yet run or failed) - not a phase escalation, but T5 cannot close until T4 has fetched these 8 pairs.")


if __name__ == "__main__":
    main()
