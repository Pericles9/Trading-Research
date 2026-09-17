"""
Build F1, F1-T5 prep: flatten the F1-T2 vendor raw archive (financials, short_interest,
splits -- already on disk, no network call) into three companion tables the ASOF joins in
t5_assemble.py read. Offline; D14 applies normally, no exception needed.

`financials_vintages` is the companion table §4 already names ("one row per (cik, period,
filing), per the F1-T0 outcome"). `accession` is not a top-level field in the vendor's
financials records -- extracted from `source_filing_url`
(".../sec/filings/{accession}"), the only place it appears; checked against a sample before
trusting it (matches the accession-number format exactly, dashes included).

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t5_prep_flatten.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

MASSIVE_DATE = "2026-09-12"
FIN_ROOT = f"{C.RAW_ROOT}/massive/{MASSIVE_DATE}/financials"
SI_ROOT = f"{C.RAW_ROOT}/massive/{MASSIVE_DATE}/short_interest"
SPLITS_ROOT = f"{C.RAW_ROOT}/massive/{MASSIVE_DATE}/splits"

ACCN_RE = re.compile(r"(\d{10}-\d{2}-\d{6})")

LINE_ITEMS = {
    "revenue": ("income_statement", "revenues"),
    "net_income": ("income_statement", "net_income_loss"),
    "cash_and_equivalents": ("balance_sheet", "cash"),
    "total_assets": ("balance_sheet", "assets"),
    "total_liabilities": ("balance_sheet", "liabilities"),
    "stockholders_equity": ("balance_sheet", "equity_attributable_to_parent"),
    "operating_cash_flow": ("cash_flow_statement", "net_cash_flow_from_operating_activities"),
    "shares_basic": ("income_statement", "basic_average_shares"),
    "shares_diluted": ("income_statement", "diluted_average_shares"),
}


def flatten_financials() -> pd.DataFrame:
    rows = []
    for path in glob.glob(f"{FIN_ROOT}/*.json"):
        cik = os.path.basename(path).replace(".json", "")
        with open(path) as f:
            records = json.load(f)
        for r in records:
            m = ACCN_RE.search(r.get("source_filing_url", "") or "")
            accession = m.group(1) if m else None
            fin = r.get("financials", {})
            row = {
                "cik": cik, "accession": accession,
                "acceptance_datetime": r.get("acceptance_datetime"),
                "filing_date": r.get("filing_date"),
                "start_date": r.get("start_date"), "end_date": r.get("end_date"),
                "fiscal_year": r.get("fiscal_year"), "fiscal_period": r.get("fiscal_period"),
                "timeframe": r.get("timeframe"),
            }
            for out_col, (section, field) in LINE_ITEMS.items():
                v = fin.get(section, {}).get(field, {})
                row[out_col] = v.get("value") if isinstance(v, dict) else None
            rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["accepted_ns"] = pd.to_datetime(df["acceptance_datetime"], utc=True, errors="coerce").astype("int64")
    df.loc[df["acceptance_datetime"].isna(), "accepted_ns"] = pd.NA
    df["accepted_ns"] = df["accepted_ns"].astype("Int64")
    return df.dropna(subset=["accepted_ns"]).drop_duplicates(subset=["cik", "accession"])


def flatten_short_interest() -> pd.DataFrame:
    rows = []
    for path in glob.glob(f"{SI_ROOT}/*.json"):
        cik = os.path.basename(path).replace(".json", "")
        with open(path) as f:
            records = json.load(f)
        for r in records:
            rows.append({
                "cik": cik, "ticker": r.get("ticker"),
                "settlement_date": r.get("settlement_date"),
                "shares_short": r.get("short_interest"),
                "avg_daily_volume": r.get("avg_daily_volume"),
                "days_to_cover": r.get("days_to_cover"),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["asof_ns"] = pd.to_datetime(df["settlement_date"], utc=True, errors="coerce").astype("int64")
    df.loc[df["settlement_date"].isna(), "asof_ns"] = pd.NA
    df["asof_ns"] = df["asof_ns"].astype("Int64")
    return df.dropna(subset=["asof_ns"]).drop_duplicates(subset=["cik", "settlement_date"])


def flatten_splits() -> pd.DataFrame:
    rows = []
    for path in glob.glob(f"{SPLITS_ROOT}/*.json"):
        cik = os.path.basename(path).replace(".json", "")
        with open(path) as f:
            records = json.load(f)
        for r in records:
            rows.append({
                "cik": cik, "execution_date": r.get("execution_date"),
                "split_from": r.get("split_from"), "split_to": r.get("split_to"),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ratio"] = df["split_to"] / df["split_from"]
    df["split_ns"] = pd.to_datetime(df["execution_date"], utc=True, errors="coerce").astype("int64")
    df.loc[df["execution_date"].isna(), "split_ns"] = pd.NA
    df["split_ns"] = df["split_ns"].astype("Int64")
    return df.dropna(subset=["split_ns"]).drop_duplicates(subset=["cik", "execution_date"])


def main():
    fin = flatten_financials()
    fin.to_parquet(f"{C.ART}/financials_vintages.parquet", index=False)
    print(f"financials_vintages: {len(fin)} rows, {fin['cik'].nunique()} CIKs, "
          f"{fin['accession'].isna().sum()} rows with unresolved accession from source_filing_url")

    si = flatten_short_interest()
    si.to_parquet(f"{C.ART}/short_interest_flat.parquet", index=False)
    print(f"short_interest_flat: {len(si)} rows, {si['cik'].nunique()} CIKs")

    spl = flatten_splits()
    spl.to_parquet(f"{C.ART}/splits_flat.parquet", index=False)
    print(f"splits_flat: {len(spl)} rows, {spl['cik'].nunique()} CIKs")


if __name__ == "__main__":
    main()
