"""
Shape atlas S1, T4 -- run-up shapes and how they lead into post-tau shapes (section 5). Exploratory,
hindsight used by design; nothing here is a tested result.

Run-up descriptors come from T1 (gap_share, u_launch, height, drawdown, pushes, duration) with
a2_ignition from b2. Declared descriptive classes, first match wins: gap (gap_share >= 0.8), late spike
(u_launch >= 0.8), grind (neither); an event whose run-up is unavailable and is not a gap is its own class,
named by the reason. Run-up data clusters come from T3 (view runup).

The transition table: run-up type -> post-tau type, counts and row shares, overall and by segment, for
  declared classes -> theory types (N = 100)
  declared classes -> post clusters (each method, each k)
  run-up clusters (each method, each k) -> theory types

Writes artifacts/s1_runup_classes.parquet, t4_transitions.parquet, t4_runup_descriptors.parquet,
t4_summary.json.

Usage: .venv/Scripts/python.exe research/shape_atlas_s1/t4_runup.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1common as S  # noqa: E402

DESC = ["gap_share", "runup_u_launch", "runup_height_s", "runup_max_drawdown_s", "runup_pushes", "runup_minutes", "runup_shares",
        "runup_n_prints"]


def declared(ev: pd.DataFrame, cfg: dict) -> pd.Series:
    dc = cfg["runup"]["declared_classes"]
    thr_gap = float(dc["gap"].split(">=")[1])
    thr_late = float(dc["late_spike"].split(">=")[1])
    avail = ev["runup_available"].fillna(False).astype(bool)
    out = np.where(ev["gap_share"] >= thr_gap, "gap",
                   np.where(avail & (ev["runup_u_launch"] >= thr_late), "late_spike",
                            np.where(avail, "grind", "runup_unavailable:" + ev["runup_reason"].fillna("unknown").astype(str))))
    return pd.Series(out, index=ev.index)


def table(df: pd.DataFrame, a: str, b: str, labels: dict) -> list[dict]:
    rows = []
    for seg, g in [("all", df)] + list(df.groupby("tau_anchor_segment")):
        ct = g.groupby([a, b]).size()
        tot = g.groupby(a).size()
        for (x, y), n in ct.items():
            rows.append({**labels, "segment": seg, "runup_type": str(x), "post_type": str(y), "n": int(n),
                         "row_n": int(tot[x]), "row_share": n / tot[x]})
    return rows


def main() -> int:
    cfg = S.load_cfg()
    ev = pd.read_parquet(S.art("s1_events.parquet"))
    at = pd.read_parquet(S.src("attention"), columns=["event_id", "a2_ignition"])
    ev = ev.merge(at, on="event_id", how="left")
    ev["runup_class"] = declared(ev, cfg)
    cls = ev[["event_id", "runup_class", "gap_share", "runup_available", "runup_reason", "runup_thin", "a2_ignition"] + DESC[1:]].copy()
    cls["config_hash"] = S.cfg_hash()
    cls.to_parquet(S.art("s1_runup_classes.parquet"), index=False)

    tt = pd.read_parquet(S.art("s1_theory_types.parquet"))
    tt = tt[tt["N"] == 100].set_index("event_id")
    ev["theory_type"] = tt.loc[ev["event_id"], "theory_type"].fillna(tt.loc[ev["event_id"], "type_state"]).to_numpy()
    rows = table(ev, "runup_class", "theory_type", {"runup_typing": "declared", "runup_k": None, "post_typing": "theory", "post_k": None})
    pa = pd.read_parquet(S.art("t3_post_assignments.parquet"))
    ra = pd.read_parquet(S.art("t3_runup_assignments.parquet"))
    base = ev[["event_id", "runup_class", "theory_type", "tau_anchor_segment"]]
    for (method, k), g in pa.groupby(["method", "k"]):
        m = base.merge(g[["event_id", "label"]], on="event_id", how="left")
        m["label"] = m["label"].map(lambda v: f"{method}{k}:{int(v)}" if pd.notna(v) else "not_clustered")
        rows += table(m, "runup_class", "label", {"runup_typing": "declared", "runup_k": None, "post_typing": method, "post_k": int(k)})
    for (method, k), g in ra.groupby(["method", "k"]):
        m = base.merge(g[["event_id", "label"]], on="event_id", how="left")
        m["label"] = m["label"].map(lambda v: f"{method}{k}:{int(v)}" if pd.notna(v) else "not_clustered")
        rows += table(m, "label", "theory_type", {"runup_typing": method, "runup_k": int(k), "post_typing": "theory", "post_k": None})
    tr = pd.DataFrame(rows)
    tr["config_hash"] = S.cfg_hash()
    tr.to_parquet(S.art("t4_transitions.parquet"), index=False)

    qs = np.linspace(0, 1, 41)
    drows = []
    for c, g in ev.groupby("runup_class"):
        for dsc in DESC + ["a2_ignition"]:
            v = pd.to_numeric(g[dsc], errors="coerce").dropna()
            drows.append({"runup_class": c, "descriptor": dsc, "n": int(v.size),
                          **{f"q{int(q * 1000):04d}": (float(np.quantile(v, q)) if v.size else None) for q in qs}})
    ds = pd.DataFrame(drows)
    ds["config_hash"] = S.cfg_hash()
    ds.to_parquet(S.art("t4_runup_descriptors.parquet"), index=False)
    main_tbl = tr[(tr["runup_typing"] == "declared") & (tr["post_typing"] == "theory")]
    S.write_json("t4_summary.json", {
        "config_hash": S.cfg_hash(), "events": int(len(ev)),
        "runup_classes": ev["runup_class"].value_counts().to_dict(),
        "runup_classes_by_segment": ev.groupby("tau_anchor_segment")["runup_class"].value_counts().rename("n").reset_index().to_dict("records"),
        "transition_declared_to_theory_all": main_tbl[main_tbl["segment"] == "all"][["runup_type", "post_type", "n", "row_n", "row_share"]].to_dict("records"),
    })
    print(ev["runup_class"].value_counts().to_string())
    print(main_tbl[main_tbl["segment"] == "all"].pivot(index="runup_type", columns="post_type", values="row_share").round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
