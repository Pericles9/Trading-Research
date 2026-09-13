"""
Build F1, F1-T5: assemble `event_fundamentals`. Offline -- D14 applies normally, every input
here is an already-archived, already-flattened companion table (F1-T2/F1-T3/F1-T4 outputs,
t5_prep_flatten.py), no network call.

Every group's ASOF join uses DuckDB's native ASOF JOIN on a strict `<` inequality (never
`<=`) against `t0_ns`, per escalation row 3 -- a `*_accepted_ns`/`*_asof_ns` at or after
`t0_ns` is a hard-stop bug, not a data-quality state, and the Verification Block
(verify_event_fundamentals.py, F1-T5d) asserts this directly rather than trusting the join
logic.

fin_ group (Amendment F1-A1, F1-T0f Outcome A): `fin_source = vendor_archive` is the primary
and (since F1-T3h's blast radius did not clear Cooper's mandatory-rebuild threshold -- see
t3h_blast_radius_summary.json) the *only* path built here; F1-T4f's companyfacts element
mapping stays optional and unbuilt, per Amendment F1-A1 SS9's own conditional. `fin_n_vintages`
is 1 for every vendor-sourced row -- F1-T0 already confirmed zero duplicate vendor records
per period, so there is exactly one known-as-of-t0 vintage by construction, not an assumption.
`fin_superseded_later` reuses the identical 8-K-Item-4.02-after-vintage check F1-T3h computes
at the aggregate level, applied per row here.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t5_assemble.py
"""
from __future__ import annotations

import json
import os
import sys

import duckdb
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

OUT_PATH = f"{C.NORMALIZED_ROOT}/event_fundamentals.parquet"
SUMMARY_PATH = f"{C.ART}/t5_assemble_summary.json"


def to_midnight_utc_ns(date_series: pd.Series) -> pd.Series:
    ns = pd.to_datetime(date_series, utc=True, errors="coerce").astype("int64")
    ns = ns.where(date_series.notna(), pd.NA)
    return ns.astype("Int64")


def build() -> pd.DataFrame:
    """Pure build, no disk write -- separated so verify_event_fundamentals.py (F1-T5d) can
    call this twice and assert byte-identical output (SS5's determinism check) without a
    subprocess round-trip."""
    cfg = C.load_cfg()
    filed_stale_days = cfg["cooper_pending"]["filed_stale_days"]

    t0_spine = pd.read_parquet(f"{C.ART}/t0_spine.parquet")
    identity = pd.read_parquet(f"{C.ART}/ticker_identity.parquet")[["event_id", "cik", "identity_quality", "ticker"]]
    base = t0_spine[["event_id", "event_date_canonical", "t0_ns", "t0_source"]].merge(
        identity, on="event_id", how="left"
    )
    assert len(base) == C.TARGET_ROW_COUNT, f"base spine has {len(base)} rows, expected {C.TARGET_ROW_COUNT}"

    con = duckdb.connect()
    con.register("events", base)

    # ---- flg_ group: already fully built by F1-T3c/e ----
    flg = pd.read_parquet(f"{C.ART}/event_filing_proximity.parquet")
    out = base.merge(flg, on="event_id", how="left")

    # ---- shs_ group: nearest observation with BOTH accepted_ns < t0_ns AND asof_ns < t0_ns.
    # NOT a plain ASOF join on accepted_ns alone -- checked directly (2026-09-12) after SS5's
    # verification block caught 5 rows with shs_asof_ns >= t0_ns despite shs_accepted_ns < t0_ns.
    # Confirmed against the raw companyfacts record (not a join bug): a dei:EntityCommonStock-
    # SharesOutstanding cover-page "as of" date can genuinely postdate its own filing's SEC
    # acceptance timestamp (MDRR's 0001104659-20-037784: end=2020-03-31, filed=2020-03-24) --
    # a real source-data quirk, not corruption. DuckDB's ASOF JOIN supports exactly one
    # inequality column, so a plain window-function nearest-match replaces it here, filtering
    # candidates on BOTH conditions before ranking by accepted_ns.
    shs_obs = pd.read_parquet(f"{C.ART}/shares_outstanding_observations.parquet")
    shs_obs = shs_obs.dropna(subset=["accepted_ns"]).copy()  # can't confirm strict ordering without a real timestamp
    shs_obs["asof_ns"] = to_midnight_utc_ns(shs_obs["asof_date"])
    con.register("shs_obs", shs_obs)
    shs = con.execute("""
        WITH candidates AS (
            SELECT e.event_id, s.shares, s.asof_ns, s.accepted_ns, s.source_form, s.accession,
                   ROW_NUMBER() OVER (PARTITION BY e.event_id ORDER BY s.accepted_ns DESC) AS rn
            FROM events e
            JOIN shs_obs s ON e.cik = s.cik AND s.accepted_ns < e.t0_ns AND s.asof_ns < e.t0_ns
        )
        SELECT e.event_id,
               c.shares AS shs_shares_outstanding, c.asof_ns AS shs_asof_ns,
               c.accepted_ns AS shs_accepted_ns, c.source_form AS shs_source_form,
               c.accession AS shs_accession
        FROM events e
        LEFT JOIN candidates c ON e.event_id = c.event_id AND c.rn = 1
    """).df()
    out = out.merge(shs, on="event_id", how="left")
    out["shs_lag_ns"] = out["t0_ns"] - out["shs_asof_ns"]
    lag_days = out["shs_lag_ns"] / 1e9 / 86400.0
    out["shs_quality"] = "unavailable"
    has_shs = out["shs_shares_outstanding"].notna()
    out.loc[has_shs & (lag_days <= filed_stale_days), "shs_quality"] = "filed_exact"
    out.loc[has_shs & (lag_days > filed_stale_days), "shs_quality"] = "filed_stale"

    # ---- fin_ group: ASOF join on financials_vintages; fin_superseded_later via item402 ----
    fin_v = pd.read_parquet(f"{C.ART}/financials_vintages.parquet")
    con.register("fin_v", fin_v)
    fin = con.execute("""
        SELECT e.event_id, e.cik,
               f.accession AS fin_accession, f.accepted_ns AS fin_accepted_ns,
               f.end_date AS fin_period_end, f.fiscal_year AS fin_fiscal_year,
               f.fiscal_period AS fin_fiscal_period_raw, f.timeframe AS fin_timeframe_raw,
               f.revenue AS fin_revenue, f.net_income AS fin_net_income,
               f.cash_and_equivalents AS fin_cash_and_equivalents,
               f.total_assets AS fin_total_assets, f.total_liabilities AS fin_total_liabilities,
               f.stockholders_equity AS fin_stockholders_equity,
               f.operating_cash_flow AS fin_operating_cash_flow,
               f.shares_basic AS fin_shares_basic, f.shares_diluted AS fin_shares_diluted
        FROM events e
        ASOF LEFT JOIN fin_v f ON e.cik = f.cik AND f.accepted_ns < e.t0_ns
    """).df()

    timeframe_map = {"quarterly": "quarterly", "annual": "annual", "ttm": "trailing_twelve_months"}
    fin["fin_timeframe"] = fin["fin_timeframe_raw"].map(timeframe_map)
    fp_map = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "FY": None, "TTM": None}
    fin["fin_fiscal_quarter"] = fin["fin_fiscal_period_raw"].map(fp_map).astype("Int8")

    item402 = pd.read_parquet(f"{C.ART}/item402_filings_full_history.parquet")
    con.register("item402_2", item402)
    con.register("fin2", fin)
    superseded = con.execute("""
        SELECT f.event_id, bool_or(i.accepted_ns IS NOT NULL) AS fin_superseded_later
        FROM fin2 f
        LEFT JOIN item402_2 i ON f.cik = i.cik AND f.fin_accepted_ns IS NOT NULL AND i.accepted_ns > f.fin_accepted_ns
        GROUP BY f.event_id
    """).df()
    fin = fin.merge(superseded, on="event_id", how="left")
    fin["fin_superseded_later"] = fin["fin_superseded_later"].fillna(False)

    fin["fin_source"] = "vendor_archive"
    fin.loc[fin["fin_accepted_ns"].isna(), "fin_source"] = "unavailable"
    fin["fin_n_vintages"] = (fin["fin_accepted_ns"].notna()).astype("int16")  # 1 known vintage as-of t0, or 0
    fin["fin_lag_ns"] = out["t0_ns"] - to_midnight_utc_ns(fin["fin_period_end"])
    fin["fin_quality"] = "unavailable"
    has_fin = fin["fin_accepted_ns"].notna()
    fin.loc[has_fin & ~fin["fin_superseded_later"], "fin_quality"] = "as_filed"
    fin.loc[has_fin & fin["fin_superseded_later"], "fin_quality"] = "as_filed_superseded_later"
    fin = fin.drop(columns=["cik", "fin_fiscal_period_raw", "fin_timeframe_raw"])
    out = out.merge(fin, on="event_id", how="left")

    # ---- si_ group: ASOF join on short_interest_flat ----
    si_flat = pd.read_parquet(f"{C.ART}/short_interest_flat.parquet")
    con.register("si_flat", si_flat)
    si = con.execute("""
        SELECT e.event_id, s.shares_short AS si_shares_short,
               s.settlement_date AS si_settlement_date, s.asof_ns AS si_asof_ns
        FROM events e
        ASOF LEFT JOIN si_flat s ON e.cik = s.cik AND s.asof_ns < e.t0_ns
    """).df()
    out = out.merge(si, on="event_id", how="left")
    out["si_lag_ns"] = out["t0_ns"] - out["si_asof_ns"]
    out["si_quality"] = "unavailable"
    out.loc[out["si_shares_short"].notna(), "si_quality"] = "observed"

    # ---- spl_ group: nearest split (ASOF) + count/reverse-flag in preceding 365d ----
    spl_flat = pd.read_parquet(f"{C.ART}/splits_flat.parquet")
    con.register("spl_flat", spl_flat)
    ns_365d = 365 * 86400 * 1_000_000_000
    spl_nearest = con.execute("""
        SELECT e.event_id, s.ratio AS spl_last_split_ratio, s.split_ns AS spl_last_split_ns
        FROM events e
        ASOF LEFT JOIN spl_flat s ON e.cik = s.cik AND s.split_ns < e.t0_ns
    """).df()
    spl_window = con.execute(f"""
        SELECT e.event_id,
               count(s.split_ns) AS spl_n_splits_365d,
               bool_or(s.ratio < 1) AS spl_reverse_split_365d
        FROM events e
        LEFT JOIN spl_flat s ON e.cik = s.cik AND s.split_ns >= e.t0_ns - {ns_365d} AND s.split_ns < e.t0_ns
        GROUP BY e.event_id
    """).df()
    spl = spl_nearest.merge(spl_window, on="event_id", how="left")
    spl["spl_reverse_split_365d"] = spl["spl_reverse_split_365d"].fillna(False)
    spl["spl_quality"] = "unavailable"
    spl.loc[spl["spl_last_split_ratio"].notna() | (spl["spl_n_splits_365d"] > 0), "spl_quality"] = "observed"
    out = out.merge(spl, on="event_id", how="left")

    # ---- final column selection, matching schema order in prompts/fundamentals_f1.md SS4 ----
    cols = [
        "event_id", "ticker", "cik", "t0_ns", "t0_source", "identity_quality",
        "flg_last_form", "flg_last_accepted_ns", "flg_last_accession", "flg_lag_ns",
        "flg_n_filings_24h", "flg_n_filings_72h", "flg_dilution_form_before_t0", "flg_quality",
        "shs_shares_outstanding", "shs_asof_ns", "shs_accepted_ns", "shs_lag_ns",
        "shs_source_form", "shs_accession", "shs_quality",
        "fin_source", "fin_accession", "fin_accepted_ns", "fin_period_end", "fin_fiscal_year",
        "fin_fiscal_quarter", "fin_timeframe", "fin_lag_ns", "fin_quality", "fin_n_vintages",
        "fin_superseded_later", "fin_revenue", "fin_net_income", "fin_cash_and_equivalents",
        "fin_total_assets", "fin_total_liabilities", "fin_stockholders_equity",
        "fin_operating_cash_flow", "fin_shares_basic", "fin_shares_diluted",
        "si_shares_short", "si_settlement_date", "si_asof_ns", "si_lag_ns", "si_quality",
        "spl_n_splits_365d", "spl_reverse_split_365d", "spl_last_split_ratio",
        "spl_last_split_ns", "spl_quality",
    ]
    out = out[cols].reset_index(drop=True)
    assert len(out) == C.TARGET_ROW_COUNT
    assert out["event_id"].is_unique
    return out


def main():
    out = build()

    os.makedirs(C.NORMALIZED_ROOT, exist_ok=True)
    out.to_parquet(OUT_PATH, index=False)

    summary = {
        "rows": len(out),
        "quality_counts": {
            g: out[f"{g}_quality"].value_counts().to_dict()
            for g in ["identity", "flg", "shs", "fin", "si", "spl"]
            if f"{g}_quality" in out.columns or g == "identity"
        },
        "config_hash": C.cfg_hash(),
    }
    summary["quality_counts"]["identity"] = out["identity_quality"].value_counts().to_dict()
    C.write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
