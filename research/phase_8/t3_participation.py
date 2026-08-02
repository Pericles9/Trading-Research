"""
Phase 8 T3 - participation baseline construction + pre-registered selection
rule + cross-sectional quintiles.

Scan-free (event_minute_bars_v2 only). For each event and clock anchor tau:
  v0(tau)      = cumulative T0 extended-day volume, minute_index 0..tau_mi
  b_clock(tau) = median over offsets {-1,-2,-3} of cumulative vol 0..tau_mi
  b_session    = median over {-1,-2,-3} of full extended-session volume
  logrv_clock(tau)   = log((v0+1)/(b_clock+1))
  logrv_session(tau) = log((v0+1)/(b_session+1))

Selection rule (frozen in config, applied per anchor before any markout): if
b_clock(tau) is zero or undefined for >20% of D1, that anchor uses
logrv_session; otherwise logrv_clock. Choice on undefined rate alone.

Buckets: cross-sectional quintile (1..5) of the selected logrv at each anchor
across D1 (excl. no_baseline). Only the rank is used.

Flag: no_baseline = event with NO T-1/T-2/T-3 trades in v2 (b_session
undefined). Carried, never pooled. Escalation row 5 if share > 5%.

The t0_close anchor uses the full extended day (minute_index<=959) as its
cumulative window, so v0=total T0 volume and b_clock == b_session there.
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from src.data.paths import resolve_duckdb_path

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
CONFIG = "config/phase_8.json"
OUT_JSON = "results/phase_8/artifacts/t3_participation.json"
OUT_PARQUET = "results/phase_8/artifacts/t3_participation.parquet"
BASE_OFFSETS = [-1, -2, -3]
UNDEF_THRESHOLD = 0.20
N_QUINTILES = 5


def main():
    with open(CONFIG) as f:
        cfg = json.load(f)
    anchors = cfg["clock_anchors"]["anchors"]
    # anchor minute for cumulative window; t0_close -> full extended day (959)
    anchor_mi = {a["name"]: (959 if a["minute_index"] is None else a["minute_index"]) for a in anchors}
    anchor_names = [a["name"] for a in anchors]

    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")
    d1 = pd.read_parquet(D1_PATH)
    con.register("d1", d1)
    con.execute("CREATE TEMP TABLE d1k AS SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mp FROM d1")

    thresholds = sorted(set(anchor_mi.values()))
    # COALESCE the filtered sums to 0: a (event,offset) group only exists when
    # that session has bars, so "no bars at/before minute m" means the cumulative
    # volume up to m on that session is a genuine 0 (it traded that day, just not
    # yet), not undefined. Undefined is reserved for a session with no bars at all
    # (no row here) -> handled as no_baseline downstream.
    filt_cols = ",\n".join(
        [f"COALESCE(SUM(b.volume) FILTER (b.minute_index <= {m}), 0) AS cv_{m}" for m in thresholds]
    )
    per = con.execute(f"""
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp, b.session_offset,
               SUM(b.volume) AS totvol,
               {filt_cols}
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical
                AND ROUND(b.momentum_pct,2)=d1k.mp
        WHERE b.session_offset IN (-3,-2,-1,0)
        GROUP BY 1,2,3,4
    """).fetchdf()
    for c in per.columns:
        if c.startswith("cv_") or c == "totvol":
            per[c] = per[c].astype("float64")
    per["event_date_canonical"] = pd.to_datetime(per["event_date_canonical"])
    d1["event_date_canonical"] = pd.to_datetime(d1["event_date_canonical"])

    key = ["ticker", "event_date_canonical", "mp"]
    base = per[per.session_offset.isin(BASE_OFFSETS)]
    t0 = per[per.session_offset == 0]

    # b_session: median over baseline offsets of full-session volume
    b_session = base.groupby(key)["totvol"].median().rename("b_session")
    n_base_offsets = base.groupby(key)["session_offset"].nunique().rename("n_base_offsets")

    out = d1.assign(mp=d1["momentum_pct"].round(2))[key].drop_duplicates().merge(
        b_session, on=key, how="left").merge(n_base_offsets, on=key, how="left")
    out["n_base_offsets"] = out["n_base_offsets"].fillna(0).astype(int)
    out["participation_class"] = np.where(out["n_base_offsets"] == 0, "no_baseline", "ok")

    # per-anchor v0, b_clock, logrv, selection, quintiles
    decisions = {}
    t0_idx = t0.set_index(key)
    base_g = base.groupby(key)
    for name in anchor_names:
        m = anchor_mi[name]
        col = f"cv_{m}"
        v0 = t0_idx[col].rename(f"v0_{name}")
        b_clock = base_g[col].median().rename(f"bclock_{name}")
        out = out.merge(v0, on=key, how="left").merge(b_clock, on=key, how="left")

        undef_or_zero = out[f"bclock_{name}"].isna() | (out[f"bclock_{name}"] == 0)
        undef_rate = float(undef_or_zero.mean())
        form = "logrv_session" if undef_rate > UNDEF_THRESHOLD else "logrv_clock"

        v0v = out[f"v0_{name}"].fillna(0.0)
        if form == "logrv_clock":
            denom = out[f"bclock_{name}"]
        else:
            denom = out["b_session"]
        logrv = np.log((v0v + 1.0) / (denom + 1.0))
        # undefined where the selected denom is NaN (no_baseline) -> NaN logrv
        logrv = np.where(denom.isna(), np.nan, logrv)
        out[f"logrv_{name}"] = logrv

        # quintiles across D1 (excl. no_baseline / NaN logrv). Rank-based so a
        # point mass in the selected logrv (e.g. many zero-premarket events at
        # 0900) cannot collapse bins or drop events - every event gets a rank
        # bucket, 5 balanced groups ("only the rank is used", T3b). Ties split
        # deterministically by first occurrence.
        mask = out["participation_class"].eq("ok") & pd.notna(out[f"logrv_{name}"])
        q = pd.Series(np.nan, index=out.index)
        ranks = out.loc[mask, f"logrv_{name}"].rank(method="first")
        q.loc[mask] = pd.qcut(ranks, N_QUINTILES,
                              labels=list(range(1, N_QUINTILES + 1))).astype(float)
        out[f"pq_{name}"] = q
        n_tied_at_mode = int(out.loc[mask, f"logrv_{name}"].round(9).value_counts().iloc[0])

        bounds = out.loc[mask, f"logrv_{name}"].quantile([0, .2, .4, .6, .8, 1.0]).tolist()
        per_q_n = out.loc[mask, f"pq_{name}"].value_counts().sort_index().to_dict()
        decisions[name] = {
            "anchor_minute_index": m,
            "bclock_undefined_or_zero_rate": undef_rate,
            "form_selected": form,
            "reason": f"undefined_or_zero rate {undef_rate:.4f} {'>' if undef_rate>UNDEF_THRESHOLD else '<='} {UNDEF_THRESHOLD}",
            "quintile_bounds_selected_logrv": [float(x) for x in bounds],
            "per_quintile_n": {str(int(k)): int(v) for k, v in per_q_n.items()},
            "quintile_method": "rank-based (method='first' ties), 5 balanced buckets",
            "largest_tied_logrv_mass": n_tied_at_mode,
        }

    out.to_parquet(OUT_PARQUET, index=False)

    n_d1 = len(out)
    n_no_base = int((out.participation_class == "no_baseline").sum())
    no_base_share = n_no_base / n_d1

    summary = {
        "phase": "8", "task": "T3",
        "source": "research/phase_8/t3_participation.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "n_d1": n_d1,
        "no_baseline_n": n_no_base,
        "no_baseline_share": no_base_share,
        "escalation_row_5_threshold": 0.05,
        "escalation_row_5_triggered": no_base_share > 0.05,
        "base_offsets": BASE_OFFSETS,
        "undefined_threshold": UNDEF_THRESHOLD,
        "n_quintiles": N_QUINTILES,
        "decisions_log": decisions,
        "artifact": OUT_PARQUET,
        "t0_close_note": "t0_close cumulative window = full extended day (mi<=959); b_clock==b_session there.",
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "decisions_log"}, indent=2, default=str))
    print("\nper-anchor decisions:")
    for name, d in decisions.items():
        print(f"  {name:9s} mi={d['anchor_minute_index']:>3} undef={d['bclock_undefined_or_zero_rate']:.3f} -> {d['form_selected']}  q_n={d['per_quintile_n']}")
    if summary["escalation_row_5_triggered"]:
        print("\n*** ESCALATION ROW 5 TRIGGERED (no_baseline > 5%) - HARD STOP ***")


if __name__ == "__main__":
    main()
