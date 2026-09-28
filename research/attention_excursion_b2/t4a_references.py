"""
Brief 2, T4a -- the no-drift reference for step zero, at each rung N: Brief 1's simulated discrete free
walk (amendment_2.step_zero_reference_line), regenerated with Brief 1's construction and seed
(research/attention_excursion_b1/t6a_references.py, amendment_2.references) so that every component is
kept, not only the summaries Brief 1 stored.

The loop below is t6a_references.main's, draw for draw -- the same RNG sequence (bridge, free walk and
positive paths are all drawn, in the same order), the same instruments.components. Its summaries must
equal Brief 1's committed t6_references.json exactly; the script asserts that before writing anything.

Writes artifacts/t4a_reference_free_walk.parquet (N x draw: u_peak, i_peak, rise_s, fall_s,
dip_before_peak_s, terminal_s) and artifacts/t4a_references.json (the reproduction check).

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/t4a_references.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402

I = B.I
KEEP = ["u_peak", "i_peak", "rise_s", "fall_s", "dip_before_peak_s", "terminal_s"]


def main() -> int:
    cfg = B.load_cfg()
    a2 = cfg["amendment_2"]["references"]
    M, seed, inj = a2["paths_per_N"], a2["seed"], a2["injection"]
    b1ref = json.load(open(B.b1_art("t6_references.json"), encoding="utf-8"))
    rng = np.random.default_rng(seed)
    frames, check = [], {}
    for N in cfg["t4_excursion"]["bucket_ladder"]:
        u = np.arange(N + 1) / N
        d_inc = np.diff(I.drift_curve(u, inj["peak_u"], inj["rise"], inj["fall"]))
        res = {"bridge": [], "free_walk": [], "positive": []}
        fw_rows = []
        for _ in range(M):
            z = rng.standard_normal(N)
            sp0 = math.sqrt(float(np.sum(z * z)))
            dm = rng.permutation(z - z.mean())
            fw = rng.standard_normal(N)
            for key, steps in (("bridge", dm), ("free_walk", fw), ("positive", dm + d_inc * sp0)):
                c = I.components(np.r_[0.0, np.cumsum(steps)])
                res[key].append((c["i_peak"], c["rise_s"], c["fall_s"], c["u_peak"]))
                if key == "free_walk":
                    fw_rows.append([c[k] for k in KEEP])
        mism = []
        for key, rows in res.items():
            a = np.array(rows, dtype=float)
            ip = a[:, 0].astype(int)
            mine = {"n": int(len(a)), "mean_rise_s": float(a[:, 1].mean()), "median_rise_s": float(np.median(a[:, 1])),
                    "mean_fall_s": float(a[:, 2].mean()), "median_fall_s": float(np.median(a[:, 2])),
                    "median_u_peak": float(np.median(a[:, 3])), "mean_u_peak": float(a[:, 3].mean()),
                    "u_peak_counts": np.bincount(ip, minlength=N + 1).tolist()}
            ref = b1ref["by_N"][str(N)][key]
            mism += [f"{key}.{k}" for k in mine if mine[k] != ref[k]]
        assert not mism, f"N={N}: regenerated references differ from Brief 1's t6_references.json: {mism}"
        check[str(N)] = {"paths": M, "fields_compared": 8 * 3, "identical": True}
        df = pd.DataFrame(fw_rows, columns=KEEP)
        df.insert(0, "draw", np.arange(M))
        df.insert(0, "N", N)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["config_hash"] = B.cfg_hash()
    out.to_parquet(B.art("t4a_reference_free_walk.parquet"), index=False)
    B.write_json("t4a_references.json", {
        "config_hash": B.cfg_hash(), "construction": "research/attention_excursion_b1/t6a_references.py, draw for draw",
        "paths_per_N": M, "seed": seed, "reproduces_brief1_t6_references": check,
        "free_walk_medians": {str(N): {k: float(g[k].median()) for k in KEEP if k != "i_peak"} for N, g in out.groupby("N")}})
    print(check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
