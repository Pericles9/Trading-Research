"""
Build F1, F1-T3h (Amendment F1-A1 SS3): the blast-radius count.

From the filing index F1-T3 builds anyway, free: count in-scope companies/events where a
genuine restatement was accepted after the event's fin_ vintage (the vendor financials
record F1-T5 would ASOF-join at t0). Decides escalation row 1c against the threshold
Cooper set 2026-09-12 (10%, config/fundamentals_f1.json cooper_pending.blast_radius_threshold_row1c)
-- small means fin_superseded_later as a flag stays adequate and F1-T4f stays optional;
at or above means F1-T4f (the companyfacts-based fin_ rebuild) becomes mandatory.

Signal used: 8-K Item 4.02 ("Non-Reliance on Previously Issued Financial Statements")
ONLY -- not 10-K/A or 10-Q/A form type. Checked directly, not assumed: F1-T0's own
identification-method note found most 10-K/A/10-Q/A filings in this universe are
administrative Part-III-only amendments, and a direct metadata check here (isXBRL /
isInlineXBRL on CLRB's own filing history, the same company F1-T0f/g used) confirms these
flags do NOT separate genuine restatements from administrative ones -- CLRB's confirmed
Part-III-only 2021 10-K/A has isXBRL=1 same as its confirmed genuine 2024 restatement, and
one 10-K/A even shows isXBRL=0. Classifying 10-K/A/10-Q/A by metadata alone would be a
silent, unverified resolution of exactly the ambiguity F1-T0's note exists to flag, so this
task does not do it -- 8-K Item 4.02 stands alone as the reliable signal, matching F1-T0's
finding exactly. Raw 10-K/A/10-Q/A-after-vintage counts are reported separately, unclassified,
never folded into the primary blast-radius share.

No upper time bound on "after the vintage" -- reads item402_filings_full_history.parquet
(F1-T3, built from the FULL per-CIK submissions pull before the -30d/+5d window truncation)
so a restatement any time up to the archive's own fetch date (2026-09-12) is caught, not
just one inside the companion-table window built for a different purpose.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t3h_blast_radius.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

import duckdb
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

FETCH_DATE_MASSIVE = "2026-09-12"
FIN_RAW_ROOT = f"data/raw/fundamentals/massive/{FETCH_DATE_MASSIVE}/financials"
ITEM402_PATH = f"{C.ART}/item402_filings_full_history.parquet"
OUT_PATH = f"{C.ART}/t3h_blast_radius_summary.json"


def load_item402() -> pd.DataFrame:
    if os.path.exists(ITEM402_PATH):
        return pd.read_parquet(ITEM402_PATH)
    # Fallback: recompute from the cached per-CIK submissions parts F1-T3's pull wrote,
    # for a run where t3_filing_index.py's older pre-item402 version already completed.
    frames = []
    for p in glob.glob(f"{C.ART}/_t3_parts/*.parquet"):
        frames.append(pd.read_parquet(p))
    filings = pd.concat(frames, ignore_index=True)
    filings["accepted_ns"] = pd.to_datetime(
        filings["acceptanceDateTime"], utc=True, errors="coerce"
    ).astype("int64")
    filings.loc[filings["acceptanceDateTime"].isna() | (filings["acceptanceDateTime"] == ""), "accepted_ns"] = pd.NA
    filings["accepted_ns"] = filings["accepted_ns"].astype("Int64")
    item402 = filings[
        (filings["form"] == "8-K") & filings["items"].astype(str).str.contains("4.02", na=False)
    ].dropna(subset=["accepted_ns"]).drop_duplicates(subset=["cik", "accessionNumber"])
    item402 = item402.rename(columns={"accessionNumber": "accession", "filingDate": "filing_date"})
    item402 = item402[["cik", "accession", "accepted_ns", "filing_date"]]
    item402.to_parquet(ITEM402_PATH, index=False)
    return item402


def load_fin_vintages(ciks: set[str]) -> pd.DataFrame:
    rows = []
    for cik in ciks:
        path = f"{FIN_RAW_ROOT}/{cik}.json"
        if not os.path.exists(path):
            continue
        with open(path) as f:
            records = json.load(f)
        for r in records:
            rows.append({
                "cik": cik,
                "filing_date": r.get("filing_date"),
                "acceptance_datetime": r.get("acceptance_datetime"),
                "fiscal_year": r.get("fiscal_year"),
                "fiscal_period": r.get("fiscal_period"),
                "timeframe": r.get("timeframe"),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["accepted_ns"] = pd.to_datetime(df["acceptance_datetime"], utc=True, errors="coerce").astype("int64")
    df.loc[df["acceptance_datetime"].isna(), "accepted_ns"] = pd.NA
    df["accepted_ns"] = df["accepted_ns"].astype("Int64")
    return df.dropna(subset=["accepted_ns"])


def main():
    cfg = C.load_cfg()
    threshold = cfg["cooper_pending"]["blast_radius_threshold_row1c"]

    t0_spine = pd.read_parquet(f"{C.ART}/t0_spine.parquet")
    identity = pd.read_parquet(f"{C.ART}/ticker_identity.parquet")[["event_id", "cik"]]
    events = t0_spine[["event_id", "event_date_canonical", "t0_ns"]].merge(identity, on="event_id", how="left")
    events["year"] = events["event_date_canonical"].str[:4]
    assert len(events) == C.TARGET_ROW_COUNT

    resolved_ciks = set(events["cik"].dropna().unique())
    fin = load_fin_vintages(resolved_ciks)
    item402 = load_item402()

    con = duckdb.connect()
    con.register("events", events)
    con.register("fin", fin)
    vintage = con.execute("""
        SELECT e.event_id, e.year, e.cik,
               f.accepted_ns AS fin_accepted_ns, f.fiscal_year AS fin_fiscal_year,
               f.fiscal_period AS fin_fiscal_period
        FROM events e
        ASOF LEFT JOIN fin f
          ON e.cik = f.cik AND f.accepted_ns < e.t0_ns
    """).df()

    con.register("vintage", vintage)
    con.register("item402", item402)
    hit = con.execute("""
        SELECT v.event_id, bool_or(i.accepted_ns IS NOT NULL) AS restated_after_vintage
        FROM vintage v
        LEFT JOIN item402 i
          ON v.cik = i.cik AND v.fin_accepted_ns IS NOT NULL AND i.accepted_ns > v.fin_accepted_ns
        GROUP BY v.event_id
    """).df()

    vintage = vintage.merge(hit, on="event_id", how="left")
    vintage["restated_after_vintage"] = vintage["restated_after_vintage"].fillna(False)
    vintage["has_fin_vintage"] = vintage["fin_accepted_ns"].notna()

    n_total = len(vintage)
    n_with_vintage = int(vintage["has_fin_vintage"].sum())
    n_no_vintage = n_total - n_with_vintage
    n_restated = int(vintage["restated_after_vintage"].sum())
    share_of_universe = n_restated / n_total
    share_of_measurable = n_restated / n_with_vintage if n_with_vintage else float("nan")

    by_year = (vintage.groupby("year")
               .agg(n=("event_id", "size"), n_restated=("restated_after_vintage", "sum"))
               .reset_index())
    by_year["share"] = by_year["n_restated"] / by_year["n"]

    # unclassified auxiliary: raw 10-K/A / 10-Q/A after vintage, NOT folded into the primary share
    filings_full = None
    part_files = __import__("glob").glob(f"{C.ART}/_t3_parts/*.parquet")
    if part_files:
        pf = pd.concat([pd.read_parquet(p) for p in part_files], ignore_index=True)
        pf["accepted_ns"] = pd.to_datetime(pf["acceptanceDateTime"], utc=True, errors="coerce").astype("int64")
        pf.loc[pf["acceptanceDateTime"].isna(), "accepted_ns"] = pd.NA
        pf["accepted_ns"] = pf["accepted_ns"].astype("Int64")
        amend = pf[pf["form"].isin(["10-K/A", "10-Q/A"])].dropna(subset=["accepted_ns"])
        con.register("amend", amend.rename(columns={"accessionNumber": "accession"}))
        amend_hit = con.execute("""
            SELECT v.event_id, bool_or(a.accepted_ns IS NOT NULL) AS amend_after_vintage
            FROM vintage v
            LEFT JOIN amend a
              ON v.cik = a.cik AND v.fin_accepted_ns IS NOT NULL AND a.accepted_ns > v.fin_accepted_ns
            GROUP BY v.event_id
        """).df()
        n_amend_after = int(amend_hit["amend_after_vintage"].fillna(False).sum())
    else:
        n_amend_after = None

    fires = share_of_universe >= threshold
    summary = {
        "n_total_events": n_total,
        "n_with_fin_vintage": n_with_vintage,
        "n_no_fin_vintage": n_no_vintage,
        "n_restated_after_vintage_item402_only": n_restated,
        "share_of_universe_20951": share_of_universe,
        "share_of_measurable_with_vintage": share_of_measurable,
        "cooper_threshold_row1c": threshold,
        "escalation_row_1c_fires": bool(fires),
        "by_year": by_year.to_dict(orient="records"),
        "auxiliary_unclassified_10ka_10qa_after_vintage": n_amend_after,
        "auxiliary_note": (
            "10-K/A/10-Q/A after the fin_ vintage, NOT restricted to item 4.02, NOT classified "
            "administrative-vs-genuine (isXBRL/isInlineXBRL checked directly on CLRB's own history "
            "and confirmed NOT a reliable classifier -- see this script's docstring). Reported for "
            "transparency only; never folded into the primary blast-radius share above."
        ),
        "method_note": (
            "Signal = 8-K Item 4.02 only, matching F1-T0's own established finding that this is the "
            "reliable genuine-restatement marker in this universe. fin_ vintage = ASOF nearest vendor "
            "financials record strictly before t0, per CIK, from the F1-T2 raw archive."
        ),
        "config_hash": C.cfg_hash(),
    }
    C.write_json(OUT_PATH, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "by_year"}, indent=2, default=str))
    print("by_year:")
    print(by_year.to_string(index=False))
    if fires:
        print(f"\n*** ESCALATION ROW 1c FIRES ({share_of_universe:.2%} >= {threshold:.0%}) -- "
              "F1-T4f becomes MANDATORY. ***")
    else:
        print(f"\nescalation row 1c does not fire ({share_of_universe:.2%} < {threshold:.0%}) -- "
              "F1-T4f stays optional.")


if __name__ == "__main__":
    main()
