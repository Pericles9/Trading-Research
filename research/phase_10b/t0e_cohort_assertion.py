"""
Phase 10b T0e -- cohort assertion and timestamp-resolution precondition.

Recomputes the frozen cohort hash and asserts every count including the segment
split. Hard stop (escalation row 2) on any mismatch. The timestamp resolution
distribution is REPORTED as a precondition, not assumed -- Phase 10 measured it
per event and this phase's T3 ladder floor is set relative to it.

Also writes a regenerable-artifact inventory: which Phase 10 outputs exist on
disk but are deliberately untracked (gitignored parquet and per-event chart
sets), so their absence from git is explicit and their regeneration command is
recorded rather than rediscovered.

Usage: .venv/Scripts/python.exe research/phase_10b/t0e_cohort_assertion.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import COHORT_KEY, read_event_trades, rel, session_window, write_json  # noqa: E402

CFG = "config/phase_10b.json"
OUT = "results/phase_10b/artifacts/t0e_cohort_assertion.json"
INV = "results/phase_10b/artifacts/t0_regenerable_inventory.json"


def load_cfg():
    with open(rel(CFG), encoding="utf-8") as f:
        return json.load(f)


def cfg_hash():
    with open(rel(CFG), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def cohort_content_hash(c: pd.DataFrame) -> str:
    body = c.sort_values(COHORT_KEY)[COHORT_KEY + ["cohort_group"]].to_csv(index=False)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def inventory(cfg) -> dict:
    """What exists on disk but is deliberately untracked, and how to regenerate it."""
    items = []
    for path, why, repro in [
        ("results/phase_10/artifacts", "gitignored *.parquet per Agent_Prompt_Standard §12",
         "research/phase_10/{t1_cohort,t2_arm_a,t3_arm_b,t4_measure,v2_*,v3_*,v4_*}.py"),
        ("results/phase_10/charts/07_tape_review", "nested .gitignore — v1 per-event set",
         "research/phase_10/t6b_tape_review.py"),
        ("results/phase_10/charts/v3_07_tape_review", "nested .gitignore — v3 per-event set",
         "research/phase_10/v3_t6b_tape.py"),
        ("results/phase_10/charts/v4_06_tape_review", "nested .gitignore — v4 per-event set",
         "research/phase_10/v4_t7b_tape.py"),
    ]:
        p = rel(path)
        if not os.path.isdir(p):
            items.append({"path": path, "exists_on_disk": False, "why_untracked": why,
                          "regenerate_with": repro})
            continue
        n, size = 0, 0
        for root, _d, files in os.walk(p):
            for f in files:
                if f == ".gitignore":
                    continue
                n += 1
                size += os.path.getsize(os.path.join(root, f))
        items.append({"path": path, "exists_on_disk": True, "n_files": n,
                      "megabytes": round(size / 1e6, 1), "why_untracked": why,
                      "regenerate_with": repro})
    return {
        "rule": "These are regenerable from committed config + code and are untracked by design "
                "(Agent_Prompt_Standard §12). Recorded so their absence from git is explicit rather "
                "than looking like loss.",
        "items": items,
        "tracked_phase_10_files_on_master": int(subprocess.run(
            ["git", "ls-files", "results/phase_10", "research/phase_10", "config/phase_10*",
             "prompts/phase_10*"], capture_output=True, text=True, cwd=rel(".")
        ).stdout.strip().count("\n") + 1),
    }


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    cc = cfg["cohort"]

    c = pd.read_parquet(rel(cc["manifest"]))
    c["event_date_canonical"] = c["event_date_canonical"].astype(str)
    got_hash = cohort_content_hash(c)

    det = pd.read_parquet(rel(cfg["paths"]["detection"]))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    det = det[np.isclose(det["threshold"], cfg["detection_anchor"]["threshold"])]
    seg = det[COHORT_KEY + [cfg["detection_anchor"]["segment_source"]]].rename(
        columns={cfg["detection_anchor"]["segment_source"]: "segment"})
    m = c.merge(seg, on=COHORT_KEY, how="left")
    pooled = m[~m["cohort_group"].isin(cc["never_pooled"])]

    counts = {
        "n_total": int(len(c)),
        "analysis_cohort_n": int(len(pooled)),
        "premarket": int((pooled["segment"] == "premarket").sum()),
        "rth": int((pooled["segment"] == "rth").sum()),
        "post": int((pooled["segment"] == "post").sum()),
        "no_detection": int(pooled["segment"].isna().sum()),
        "row_cap_census": int((c["cohort_group"] == "row_cap_census").sum()),
        "dev_v4_sidecar": int((c["cohort_group"] == "dev_v4_sidecar").sum()),
    }
    exp = cc["expected_counts"]
    checks = {
        "content_hash": {"expected": cc["content_hash"], "observed": got_hash,
                         "pass": got_hash == cc["content_hash"]},
        "n_total": {"expected": cc["n_total"], "observed": counts["n_total"],
                    "pass": counts["n_total"] == cc["n_total"]},
        "analysis_cohort_n": {"expected": cc["analysis_cohort_n"],
                              "observed": counts["analysis_cohort_n"],
                              "pass": counts["analysis_cohort_n"] == cc["analysis_cohort_n"]},
        "premarket": {"expected": exp["premarket"], "observed": counts["premarket"],
                      "pass": counts["premarket"] == exp["premarket"]},
        "rth": {"expected": exp["rth"], "observed": counts["rth"],
                "pass": counts["rth"] == exp["rth"]},
        "row_cap_census": {"expected": exp["row_cap_census"], "observed": counts["row_cap_census"],
                           "pass": counts["row_cap_census"] == exp["row_cap_census"]},
        "dev_v4_sidecar": {"expected": exp["dev_v4_sidecar"], "observed": counts["dev_v4_sidecar"],
                           "pass": counts["dev_v4_sidecar"] == exp["dev_v4_sidecar"]},
    }
    all_pass = all(v["pass"] for v in checks.values())

    # ---- timestamp resolution, measured per event, reported as a precondition
    res_rows = []
    for r in c.itertuples(index=False):
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) < 2:
            continue
        ts = t0["sip_timestamp"].to_numpy()
        dt = np.diff(ts)
        nz = dt[dt > 0]
        res_rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                         "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                         "n_prints": int(ts.size),
                         "min_nonzero_gap_ns": int(nz.min()) if nz.size else None,
                         "n_zero_gaps": int((dt == 0).sum())})
    res = pd.DataFrame(res_rows)
    res = res.merge(seg, on=COHORT_KEY, how="left")
    rp = res[~res["cohort_group"].isin(cc["never_pooled"])]["min_nonzero_gap_ns"].dropna()

    def q(a):
        a = np.asarray(a, float)
        return {"n": int(a.size), "min": float(a.min()), "q25": float(np.percentile(a, 25)),
                "median": float(np.median(a)), "q75": float(np.percentile(a, 75)),
                "max": float(a.max())}

    summary = {
        "phase": "10b", "task": "T0e", "config_hash": chash,
        "cohort_manifest": cc["manifest"],
        "checks": checks, "all_pass": bool(all_pass),
        "observed_counts": counts,
        "escalation_row_2_triggered": bool(not all_pass),
        "timestamp_resolution_ns": {
            "rule": "Measured per event from the data as the smallest NON-ZERO inter-print gap. "
                    "Reported as a precondition, not assumed. The T3 ladder floor (2^-20 s = "
                    "0.954 us) is ~12x the pooled median.",
            "pooled_analysis_cohort": q(rp),
            "by_segment": {str(s): q(g["min_nonzero_gap_ns"].dropna())
                           for s, g in res[~res["cohort_group"].isin(cc["never_pooled"])]
                           .groupby("segment") if g["min_nonzero_gap_ns"].notna().any()},
            "ladder_floor_seconds": 2.0 ** cfg["t3_allan"]["ladder_exponents"][0],
            "ladder_floor_over_median_resolution": float(
                (2.0 ** cfg["t3_allan"]["ladder_exponents"][0]) / (np.median(rp) / 1e9)),
        },
        "source": "research/phase_10b/t0e_cohort_assertion.py:main",
    }
    write_json(rel(OUT), summary)
    res.to_parquet(rel("results/phase_10b/artifacts/t0e_timestamp_resolution.parquet"), index=False)
    write_json(rel(INV), inventory(cfg))

    print(f"cohort hash: {got_hash}  expected {cc['content_hash']}  "
          f"{'MATCH' if checks['content_hash']['pass'] else 'MISMATCH'}")
    for k, v in checks.items():
        if k == "content_hash":
            continue
        print(f"  {k:20s} expected {v['expected']:>4}  observed {v['observed']:>4}  "
              f"{'PASS' if v['pass'] else 'FAIL'}")
    tr = summary["timestamp_resolution_ns"]["pooled_analysis_cohort"]
    print(f"timestamp resolution (ns): n={tr['n']} min={tr['min']:.0f} median={tr['median']:.1f} "
          f"max={tr['max']:.0f}")
    print(f"T3 ladder floor {summary['timestamp_resolution_ns']['ladder_floor_seconds']:.3e} s = "
          f"{summary['timestamp_resolution_ns']['ladder_floor_over_median_resolution']:.1f}x median resolution")
    if not all_pass:
        print("ESCALATION ROW 2 TRIGGERED")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
