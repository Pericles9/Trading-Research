"""
Chop regime C1, T5b -- which values make the T5 blindness control's NaN / inf pattern mismatches. Diagnosis at the stop;
fixes nothing.

Rebuilds every event that t5_blindness.parquet lists with a mismatch, at x1, x10 and x0.1 (trade and quote prices), and
writes each moment-level or rung-level value whose NaN / inf state differs between x1 and the rescaled build.

Writes artifacts/t5b_blindness_detail.parquet.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t5b_blindness_detail.py
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c1common as C  # noqa: E402
import measures as M  # noqa: E402

_spec = importlib.util.spec_from_file_location("c1_t5_controls", os.path.join(HERE, "t5_controls.py"))   # S2 has its own t5_controls
T5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T5)


def main() -> int:
    cfg = C.load_cfg()
    bl = pd.read_parquet(C.art("t5_blindness.parquet"))
    bad = bl[(bl["x10_nan_pattern_mismatches"] > 0) | (bl["x0.1_nan_pattern_mismatches"] > 0)]["event_id"]
    pop = C.quarantine(C.load_population()).set_index("event_id")
    rows = []
    for eid in bad:
        rec = dict(pop.loc[eid].to_dict(), event_id=eid)
        date = rec["event_date_canonical"]
        tr, q = C.B1.read_trades(eid, with_conditions=False), C.read_quotes(eid)

        def run(f):
            t2, q2 = dict(tr), dict(q)
            t2["px"], q2["bid"], q2["ask"] = tr["px"] * f, q["bid"] * f, q["ask"] * f
            o = M.build_event(rec, cfg, 1.0, [], tape=C.Tape(eid, date, tr=t2), quotes=q2, with_hindsight=False)
            return pd.DataFrame(o["rows"]).set_index("j"), pd.DataFrame(o["sf_rungs"])

        a, asf = run(1.0)
        for f in cfg["controls"]["blindness"]["factors"]:
            b, bsf = run(f)
            for level, cols, x0, x1 in (("moment", T5.INVARIANT, a, b.reindex(a.index)), ("rung", T5.INV_SF, asf, bsf)):
                for c in cols:
                    if c not in x0:
                        continue
                    u, w = x0[c].astype(float).to_numpy(), x1[c].astype(float).to_numpy()
                    m = (np.isnan(u) != np.isnan(w)) | (np.isinf(u) != np.isinf(w))
                    for i in np.flatnonzero(m):
                        rows.append({"event_id": eid, "factor": f, "level": level, "column": c,
                                     "j": int(x0.index[i]) if level == "moment" else int(x0["j"].iloc[i]),
                                     "k": None if level == "moment" else int(x0["k"].iloc[i]), "value_x1": float(u[i]), "value_rescaled": float(w[i])})
    out = pd.DataFrame(rows)
    out["config_hash"] = C.cfg_hash()
    out.to_parquet(C.art("t5b_blindness_detail.parquet"), index=False)
    print(out.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
