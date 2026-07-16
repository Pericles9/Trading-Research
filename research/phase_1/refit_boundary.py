"""
Phase 1 T2 - read-only re-implementation of filter_events_power_law.py.

Mirrors the original script's logic exactly (including its structural
date/event_date gap, per filter_spec.md T1d) to derive a comparable kept
set, then diffs it against the committed `momentum_events` table.

Never writes to data/momentum_events/. Never executes the original script.
Reads config/phase_1.json. Writes results/phase_1/artifacts/refit_comparison.json.
"""
import json
import hashlib
import duckdb
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

CONFIG_PATH = "config/phase_1.json"
OUT_PATH = "results/phase_1/artifacts/refit_comparison.json"
DB_PATH = "data/duckdb/main.duckdb"


def config_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def main():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    file1, file2 = cfg["candidate_scan_inputs"]

    df1 = pd.read_parquet(file1)
    if "volume" in df1.columns:
        df1 = df1.rename(columns={"volume": "event_volume"})
    df2 = pd.read_parquet(file2)

    full_df = pd.concat([df1, df2], ignore_index=True)

    calc_df = full_df.copy()
    calc_df = calc_df.dropna(subset=["momentum_pct", "event_volume"])
    calc_df = calc_df[calc_df["event_volume"] > 0]
    calc_df = calc_df[calc_df["momentum_pct"] > 0]

    calc_df["log_mom"] = np.log10(calc_df["momentum_pct"])
    calc_df["log_vol"] = np.log10(calc_df["event_volume"])

    upper_bound = calc_df["momentum_pct"].quantile(0.995)
    train_df = calc_df[calc_df["momentum_pct"] <= upper_bound].copy()

    mod = smf.quantreg("log_vol ~ log_mom", train_df)
    res = mod.fit(q=0.05)

    calc_df["log_vol_threshold"] = res.predict(calc_df[["log_mom"]])
    kept_df = calc_df[calc_df["log_vol"] > calc_df["log_vol_threshold"]].copy()

    # Coalesced join key: date is structurally NULL for every file2-sourced
    # row (see filter_spec.md T1d). To compare full coverage, not just the
    # file1 subset, the key coalesces date with event_date.
    kept_df["join_date"] = kept_df["date"].fillna(kept_df.get("event_date"))
    kept_df["join_mom"] = kept_df["momentum_pct"].round(2)
    derived_keys = set(
        zip(kept_df["ticker"], kept_df["join_date"], kept_df["join_mom"])
    )

    con = duckdb.connect(database=DB_PATH, read_only=True)
    db_rows = con.execute(
        """
        SELECT ticker, COALESCE(date, event_date) AS join_date,
               ROUND(momentum_pct, 2) AS join_mom
        FROM momentum_events
        """
    ).fetchall()
    con.close()
    db_keys = set(db_rows)

    both = derived_keys & db_keys
    only_derived = derived_keys - db_keys
    only_db = db_keys - derived_keys

    result = {
        "phase": "1",
        "task": "T2",
        "config_hash": config_hash(CONFIG_PATH),
        "methodology": {
            "join_key": "(ticker, COALESCE(date, event_date), ROUND(momentum_pct, 2))",
            "why_coalesced": "date is structurally NULL for every file2-sourced row "
            "(filter_spec.md T1d). Coalescing with event_date is the only way to "
            "compare full coverage rather than just the file1 subset.",
        },
        "row_counts": {
            "raw_concat": len(full_df),
            "cleaned_calc_df": len(calc_df),
            "training_set_le_995pct": len(train_df),
            "re_derived_kept": len(kept_df),
            "momentum_events_table": len(db_keys),
        },
        "quantreg_params": {k: float(v) for k, v in res.params.items()},
        "overlap": {
            "n_both": len(both),
            "n_only_re_derived": len(only_derived),
            "n_only_momentum_events": len(only_db),
            "re_derived_in_db_pct": round(100 * len(both) / len(derived_keys), 4)
            if derived_keys
            else None,
            "db_in_re_derived_pct": round(100 * len(both) / len(db_keys), 4)
            if db_keys
            else None,
        },
        "overlap_threshold_config": cfg["overlap_threshold"],
    }

    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
