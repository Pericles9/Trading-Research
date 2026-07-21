"""
Phase 3 Amendment 1, A1-T3a - descriptive v2 vs v3 dev sample overlap.

Not a pass/fail check - description only. Cross-references coverage_class
directly from results/phase_2/artifacts/coverage_class.parquet (same
source T1/T2 used), not the live view, since no escalation-relevant
guard applies here.
"""
import json

import pandas as pd

OUT_PATH = "results/phase_3/artifacts/dev_sample_v3_vs_v2.json"


def load_manifest(path):
    with open(path) as f:
        m = json.load(f)
    df = pd.DataFrame(m["events"])
    df["date"] = pd.to_datetime(df["date"])
    df["mom_2dp"] = df["momentum_pct"].round(2)
    return df


def main():
    v2 = load_manifest("config/dev_sample_v2.json")
    v3 = load_manifest("config/dev_sample_v3.json")

    cc = pd.read_parquet("results/phase_2/artifacts/coverage_class.parquet")
    cc["event_date_canonical"] = pd.to_datetime(cc["event_date_canonical"])
    cc["mom_2dp"] = cc["momentum_pct"].round(2)
    cc_lookup = cc.set_index(["ticker", "event_date_canonical", "mom_2dp"])[["coverage_class", "quotes_full_window"]]

    v2_keys = set(zip(v2["ticker"], v2["date"], v2["mom_2dp"]))
    v3_keys = set(zip(v3["ticker"], v3["date"], v3["mom_2dp"]))

    v2["coverage_class"] = [
        cc_lookup.loc[k, "coverage_class"] if k in cc_lookup.index else None
        for k in zip(v2["ticker"], v2["date"], v2["mom_2dp"])
    ]

    v2_full_window = v2[v2["coverage_class"] == "full_window"]
    v2_full_window_keys = set(zip(v2_full_window["ticker"], v2_full_window["date"], v2_full_window["mom_2dp"]))

    both = v2_keys & v3_keys
    dropped = v2_keys - v3_keys
    new_draws = v3_keys - v2_keys
    full_window_reappear = v2_full_window_keys & v3_keys

    def keys_to_records(keys, src_df):
        sub = src_df[[tuple(x) in keys for x in zip(src_df["ticker"], src_df["date"], src_df["mom_2dp"])]]
        return sub[["ticker", "date", "momentum_pct", "decile"]].assign(date=sub["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")

    out = {
        "phase": "3", "amendment": "1", "task": "A1-T3a",
        "note": "Descriptive only - not a pass/fail check.",
        "n_v2": len(v2), "n_v3": len(v3),
        "n_v2_full_window": len(v2_full_window),
        "n_v2_full_window_reappearing_in_v3": len(full_window_reappear),
        "n_both_v2_and_v3": len(both),
        "n_dropped_from_v2": len(dropped),
        "n_new_draws_in_v3": len(new_draws),
        "dropped_events": keys_to_records(dropped, v2),
        "new_draw_events": keys_to_records(new_draws, v3),
        "both_events": keys_to_records(both, v2),
        "source": "research/phase_3/a1_t3a_v3_vs_v2_overlap.py:main",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in out.items() if not k.endswith("_events")}, indent=2, default=str))
    print(f"\ndropped ({len(dropped)}):")
    for r in out["dropped_events"]:
        print(f"  {r['ticker']} {r['date']} decile={r['decile']}")
    print(f"\nnew draws ({len(new_draws)}):")
    for r in out["new_draw_events"]:
        print(f"  {r['ticker']} {r['date']} decile={r['decile']}")


if __name__ == "__main__":
    main()
