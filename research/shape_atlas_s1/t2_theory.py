"""
Shape atlas S1, T2 -- the theory types (section 3), declared before the run. Exploratory, hindsight used
by design; nothing here is a tested result.

Assigned from the post-tau vector at N = 100 (and, to show how much the rung moves the assignment, at
N = 50 and 200) by the config's rules, first match wins, on the event's own null percentiles
(rise_pct, fall_pct from T1). Beside every real share goes the share that noise alone produces: each
event's 200 null draws typed by the same rules (T1), averaged over events.

Writes artifacts/s1_theory_types.parquet (event x rung), t2_theory_shares.parquet (facet x level x rung x
type: real n and share, null share), t2_summary.json.

Usage: .venv/Scripts/python.exe research/shape_atlas_s1/t2_theory.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1common as S  # noqa: E402


def main() -> int:
    cfg = S.load_cfg()
    ev = pd.read_parquet(S.art("s1_events.parquet"))
    rows = []
    for N in (50, 100, 200):
        ok = ev[f"post{N}_null_ok"].fillna(False).astype(bool)
        t = S.theory_type(ev[f"post{N}_rise_pct"], ev[f"post{N}_fall_pct"], ev[f"post{N}_u_peak"])
        t = np.where(ok, t, None)
        rows.append(pd.DataFrame({"event_id": ev["event_id"], "N": N, "theory_type": t,
                                  "type_state": np.where(ok, "typed", np.where(ev[f"post{N}_available"].fillna(False).astype(bool),
                                                                              "sigma_zero_or_no_null", "no_vector"))}))
    tt = pd.concat(rows, ignore_index=True)
    tt["config_hash"] = S.cfg_hash()
    tt.to_parquet(S.art("s1_theory_types.parquet"), index=False)

    wide = ev[["event_id", "year", "tau_anchor_segment", "price_tier"]].copy()
    for N in (50, 100, 200):
        wide[f"type{N}"] = tt[tt["N"] == N].set_index("event_id").loc[wide["event_id"], "theory_type"].to_numpy()
        for ty in S.TYPES:
            wide[f"null{N}_{ty}"] = ev[f"post{N}_null_share_{ty}"].to_numpy()
    out = []
    for N in (50, 100, 200):
        typed = wide[wide[f"type{N}"].notna()]
        facets = [("all", "all", typed)] + [(f, str(lev), g) for f in ("year", "tau_anchor_segment", "price_tier")
                                            for lev, g in typed.groupby(f)]
        for facet, lev, g in facets:
            n = len(g)
            for ty in S.TYPES:
                k = int((g[f"type{N}"] == ty).sum())
                out.append({"N": N, "facet": facet, "level": lev, "type": ty, "n_events": n, "n_type": k,
                            "real_share": k / n if n else None, "null_share": float(g[f"null{N}_{ty}"].mean()) if n else None})
    sh = pd.DataFrame(out)
    sh["real_minus_null"] = sh["real_share"] - sh["null_share"]
    sh["config_hash"] = S.cfg_hash()
    sh.to_parquet(S.art("t2_theory_shares.parquet"), index=False)

    agree = {}
    w = wide.dropna(subset=["type50", "type100", "type200"])
    for a, b in ((50, 100), (100, 200), (50, 200)):
        agree[f"N={a} vs N={b}"] = {"n": int(len(w)), "same_type_share": float((w[f"type{a}"] == w[f"type{b}"]).mean())}
    allr = sh[(sh["facet"] == "all")]
    S.write_json("t2_summary.json", {
        "config_hash": S.cfg_hash(), "rules": cfg["theory_types"]["rules"],
        "typed_events": {int(N): int((tt[(tt["N"] == N)]["type_state"] == "typed").sum()) for N in (50, 100, 200)},
        "type_state": {int(N): tt[tt["N"] == N]["type_state"].value_counts().to_dict() for N in (50, 100, 200)},
        "shares_all": {f"N={int(r.N)}|{r.type}": {"n": int(r.n_type), "of": int(r.n_events), "real": r.real_share, "null": r.null_share}
                       for r in allr.itertuples()},
        "rung_agreement": agree,
    })
    print(allr[["N", "type", "n_type", "real_share", "null_share"]].to_string())
    print(agree)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
