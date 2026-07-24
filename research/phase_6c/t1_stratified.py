"""
Phase 6c T1 - stratified recomputation of A6.1's three criteria, split
by dev v4 cohort (primary vs. sidecar vs. pooled). Reads only the
already-committed results/phase_6b/artifacts/a61_basis_confirmation_rerun.json
full_table - no re-measurement, same band (2%) and threshold (90%).
"""
import json

import pandas as pd

PHASE_6C_CONFIG = "config/phase_6c.json"
A61_ARTIFACT = "results/phase_6b/artifacts/a61_basis_confirmation_rerun.json"
OUT_JSON = "results/phase_6c/artifacts/t1_stratified_criteria.json"


def criteria_for_stratum(df: pd.DataFrame, band_pct: float, threshold_pct: float, dup_tickers_global: list[str]) -> dict:
    both = df[df["r1p"].notna() & df["r2p"].notna()].copy()
    both["rel_diff"] = (both["r1p"] - both["r2p"]).abs() / both["r2p"]
    n_both = len(both)
    n_agree = int((both["rel_diff"] < band_pct / 100.0).sum())
    pct_agree = 100.0 * n_agree / n_both if n_both else None
    c1_pass = (pct_agree is not None) and pct_agree >= threshold_pct

    # criterion 2: only meaningful for tickers repeated *within this stratum*
    tickers_in_stratum = df["ticker"].value_counts()
    dup_here = tickers_in_stratum[tickers_in_stratum > 1].index.tolist()
    stability = []
    c2_pass = True
    for t in dup_here:
        sub = df[df["ticker"] == t]
        r_vals = pd.concat([sub["r1p"], sub["r2p"]]).dropna()
        stable = bool(r_vals.max() / r_vals.min() < 1.10) if len(r_vals) >= 2 else None
        if stable is False:
            c2_pass = False
        stability.append({"ticker": t, "stable_within_10pct": stable})
    if not dup_here:
        c2_pass = None

    flagged = df[df["denom_nonpositive_t0_rth"] == True]  # noqa: E712
    unflagged = df[df["denom_nonpositive_t0_rth"] == False]  # noqa: E712
    flagged_factor = pd.concat([flagged["r1p"], flagged["r2p"]]).dropna()
    unflagged_factor = pd.concat([unflagged["r1p"], unflagged["r2p"]]).dropna()
    pct_flagged_gt1 = 100.0 * (flagged_factor > 1.05).sum() / len(flagged_factor) if len(flagged_factor) else None
    c3_pass = bool(pct_flagged_gt1 is None or pct_flagged_gt1 >= 90.0)  # vacuously true if no flagged events in stratum

    n_no_ratio = int(df["r1p"].isna().sum() | df["r2p"].isna().sum())
    undefined_events = df[df["r1p"].isna() | df["r2p"].isna()][["ticker", "event_date_canonical"]].to_dict(orient="records")

    return {
        "n_events": len(df),
        "criterion_1": {"n_both_defined": n_both, "n_agree": n_agree, "pct_agree": round(pct_agree, 2) if pct_agree is not None else None, "pass": c1_pass},
        "criterion_2": {"dup_tickers_in_stratum": dup_here, "detail": stability, "pass": c2_pass},
        "criterion_3": {"n_flagged": len(flagged), "pct_flagged_gt1_05": round(pct_flagged_gt1, 2) if pct_flagged_gt1 is not None else None, "pass": c3_pass},
        "n_undefined_ratio_events": n_no_ratio,
        "undefined_ratio_events": undefined_events,
    }


def main():
    with open(PHASE_6C_CONFIG) as f:
        cfg = json.load(f)
    band_pct = cfg["criteria"]["band_width_pct"]
    threshold_pct = cfg["criteria"]["stratified_threshold_pct"]

    with open(A61_ARTIFACT) as f:
        a61 = json.load(f)
    df = pd.DataFrame(a61["full_table"])

    primary = df[df["dev_cohort"] == "primary"]
    sidecar = df[df["dev_cohort"] == "flagged_sidecar"]
    dup_tickers_global = a61["criterion_2_per_ticker_stability"]["duplicate_tickers"]

    result = {
        "phase": "6c", "task": "T1",
        "band_width_pct": band_pct, "threshold_pct": threshold_pct,
        "primary": criteria_for_stratum(primary, band_pct, threshold_pct, dup_tickers_global),
        "sidecar": criteria_for_stratum(sidecar, band_pct, threshold_pct, dup_tickers_global),
        "pooled": criteria_for_stratum(df, band_pct, threshold_pct, dup_tickers_global),
        "escalation_row2_triggered": None,
        "source": "research/phase_6c/t1_stratified.py:main",
    }
    result["escalation_row2_triggered"] = (result["primary"]["criterion_1"]["pct_agree"] or 0) < threshold_pct

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))

    if result["escalation_row2_triggered"]:
        print(f"\n*** ESCALATION row 2: primary-cohort criterion 1 = {result['primary']['criterion_1']['pct_agree']}% < {threshold_pct}% - HARD STOP ***")


if __name__ == "__main__":
    main()
