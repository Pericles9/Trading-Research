"""
Phase 1b T1 - instrument classification.

Classifies every distinct ticker in momentum_events UNION folder_inventory
(date-valid folders only) using the priority rule set from prompts/phase_1b.md,
first match wins. Cross-checks against the advisory symbol-properties source
(never load-bearing).
"""
import json
import re

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
FOLDER_INVENTORY = "results/phase_0c/artifacts/folder_inventory.parquet"
ADVISORY_CSV = "data/symbol-properties/symbol-properties-database.csv"
OUT_PARQUET = "results/phase_1b/artifacts/instrument_classification.parquet"
OUT_SUMMARY = "results/phase_1b/artifacts/instrument_classification_summary.json"

SUSPECT_CLASSES = {"warrant_suspect", "unit_suspect", "right_suspect"}


def classify(ticker: str):
    segments = ticker.split(".")
    if "WS" in segments:
        return "warrant", 1
    if re.match(r"^[A-Z]+p[A-Z]?$", ticker):
        return "preferred", 2
    if ticker.endswith(".U"):
        return "unit", 3
    if ticker.endswith(".R"):
        return "right", 4
    if ticker.endswith(".A") or ticker.endswith(".B") or ticker.endswith(".C"):
        return "common_class_share", 5
    if re.match(r"^[A-Z]{5}$", ticker):
        if ticker.endswith("W"):
            return "warrant_suspect", 6
        if ticker.endswith("U"):
            return "unit_suspect", 7
        if ticker.endswith("R"):
            return "right_suspect", 8
    return "common", 9


def load_advisory():
    """Parse the advisory CSV's usable rows: market,symbol,type,... Comments
    (#) and blank lines are noise; [*] rows are wildcards, not per-symbol."""
    rows = []
    with open(ADVISORY_CSV, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("market,"):
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            market, symbol, sym_type = parts[0], parts[1], parts[2]
            if symbol == "[*]":
                continue  # wildcard, not a per-symbol row
            rows.append((market, symbol, sym_type))
    return pd.DataFrame(rows, columns=["market", "symbol", "type"])


def main():
    con_db = duckdb.connect(database=DB_PATH, read_only=True)
    me_tickers = set(con_db.execute("SELECT DISTINCT ticker FROM momentum_events").fetchdf()["ticker"])
    con_db.close()

    con = duckdb.connect(read_only=False)
    folder_tickers = set(
        con.execute(
            f"SELECT DISTINCT ticker FROM read_parquet('{FOLDER_INVENTORY}') WHERE date_is_none = FALSE"
        ).fetchdf()["ticker"]
    )
    union_tickers = sorted(me_tickers | folder_tickers)

    advisory = load_advisory()
    advisory_by_symbol = advisory.groupby("symbol")["type"].apply(lambda s: sorted(set(s))).to_dict()

    records = []
    for ticker in union_tickers:
        cls, rule_hit = classify(ticker)
        adv_types = advisory_by_symbol.get(ticker)
        if adv_types is None:
            resolved_by = None
            sp_class = None
            agrees = None
        else:
            resolved_by = "symbol_properties_advisory"
            sp_class = ",".join(adv_types)
            agrees = None  # advisory has no common/preferred/warrant taxonomy - see summary note

        records.append(
            {
                "ticker": ticker,
                "class": cls,
                "rule_hit": rule_hit,
                "in_momentum_events": ticker in me_tickers,
                "folder_only": ticker not in me_tickers,
                "resolved_by": resolved_by,
                "symbol_properties_class": sp_class,
                "agrees": agrees,
            }
        )

    df = pd.DataFrame(records)

    # Suspect resolution: advisory has zero per-ticker equity coverage (confirmed
    # T0 investigation), so no suspect ticker can be resolved by it. Every
    # suspect-class ticker stays *_suspect and goes on the escalation list.
    suspect_mask = df["class"].isin(SUSPECT_CLASSES)
    n_suspect = int(suspect_mask.sum())
    n_distinct = len(union_tickers)
    suspect_pct = n_suspect / n_distinct

    advisory_matches = df["resolved_by"].notna().sum()

    df.to_parquet(OUT_PARQUET, index=False)

    counts_table = (
        df.assign(source=df["folder_only"].map({True: "folder_only", False: "momentum_events"}))
        .groupby(["class", "source"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["momentum_events", "folder_only"], fill_value=0)
    )

    summary = {
        "phase": "1b",
        "task": "T1",
        "n_distinct_tickers": n_distinct,
        "n_momentum_events_tickers": len(me_tickers),
        "n_folder_tickers": len(folder_tickers),
        "n_folder_only_tickers": len(folder_tickers - me_tickers),
        "classification_counts_by_class_and_source": {
            cls: {"momentum_events": int(row["momentum_events"]), "folder_only": int(row["folder_only"])}
            for cls, row in counts_table.iterrows()
        },
        "advisory_cross_check": {
            "source": ADVISORY_CSV,
            "n_usable_symbol_rows_in_advisory_file": len(advisory),
            "n_tickers_matched_in_advisory": int(advisory_matches),
            "finding": "The advisory file is a generic broker contract-spec reference "
            "(futures/forex/crypto/CFDs) with a single wildcard 'usa,[*],equity' row "
            "covering all US equities generically. It contains zero per-ticker rows "
            "for any symbol in this universe (confirmed: 0/{} matched). It cannot "
            "resolve any suspect-class ticker or provide a disagreement rate against "
            "non-suspect classes - there is nothing in it to agree or disagree with "
            "per ticker.".format(n_distinct),
            "disagreement_rate_non_suspect": None,
            "disagreement_rate_note": "Undefined - zero overlapping tickers to compare.",
        },
        "suspect_classes": {
            "n_suspect": n_suspect,
            "pct_of_distinct_tickers": round(100 * suspect_pct, 4),
            "escalation_threshold_pct": 2.0,
            "escalation_triggered": suspect_pct > 0.02,
            "tickers": sorted(df.loc[suspect_mask, "ticker"].tolist()),
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
