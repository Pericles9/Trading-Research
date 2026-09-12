#!/usr/bin/env python
"""
The paired control for D23, and it is the statistic the decision rests on.

THE PROBLEM IT SOLVES. The centred arm contributes matched onsets on 45 events and the
causal arm on 19. Comparing -0.204 kernel widths against +1.515 across two different
populations does not establish that the KERNEL caused the reversal -- the 19 could simply
be events where the field happens to lead under any kernel.

WHAT MAKES THE TEST POSSIBLE. The 19 causal contributors turn out to be a strict SUBSET of
the centred 45, so the comparison can be run WITHIN EVENT: same event, same anchor, same
ladder, same debounce, same tolerance rule, same window -- only the kernel differs. That is
a paired design, and it is the only version of this comparison that excludes the population
explanation.

Two things are reported and both matter:
  1. the paired difference (causal - centred) per event, with a signed-rank and a sign test
  2. whether the 19 are a special subpopulation, by comparing the CENTRED arm's own result
     on those 19 against the centred arm's result on its other 26

Usage: .venv/Scripts/python.exe research/scale_field/t1_paired_control.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapter  # noqa: E402
from adapter import rel  # noqa: E402

OUT = "results/scale_field/artifacts/t1_paired_control.json"


def per_event(path):
    on = pd.read_parquet(rel(path))
    on = on[on["orientation"] == "burst"]
    g = on.groupby("event_id")
    return pd.DataFrame({"n_onsets": g.size(),
                         "med_lead_s": g["lead_s"].median(),
                         "med_lead_u": g["lead_in_s_units"].median()})


def summarise(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    pos, neg = int((v > 0).sum()), int((v < 0).sum())
    return {"n": int(v.size), "n_positive": pos, "n_negative": neg,
            "median": float(np.median(v)),
            "q25": float(np.quantile(v, .25)), "q75": float(np.quantile(v, .75)),
            "sign_test_p": (float(stats.binomtest(pos, pos + neg, 0.5).pvalue)
                            if pos + neg else None),
            "wilcoxon_p": (float(stats.wilcoxon(v).pvalue) if v.size >= 6 else None)}


def main() -> int:
    A = "results/scale_field/artifacts/"
    cen = per_event(A + "t1_lead_time_onsets.parquet")
    cau = per_event(A + "t1_lead_time_onsets_onesided.parquet")
    shared = sorted(set(cen.index) & set(cau.index))
    only_cen = sorted(set(cen.index) - set(cau.index))

    c, o = cen.loc[shared, "med_lead_u"], cau.loc[shared, "med_lead_u"]
    diff = (o - c).to_numpy()

    # robustness: drop the single largest contributor on the causal side
    biggest = cau["n_onsets"].idxmax()
    keep = [e for e in shared if e != biggest]

    out = {
        "task": "D23 paired control -- is the reversal the kernel or the population?",
        "config_hash": adapter.config_hash(),
        "design": ("The causal arm's contributing events are a strict subset of the "
                   "centred arm's, so the two arms are compared WITHIN EVENT. Same event, "
                   "anchor, ladder, debounce, tolerance rule and window; only the kernel "
                   "differs. Statistic = the per-event median signed lead in units of s."),
        "populations": {
            "centred_contributing": int(len(cen)),
            "causal_contributing": int(len(cau)),
            "shared": int(len(shared)),
            "causal_is_strict_subset_of_centred": bool(set(cau.index) <= set(cen.index)),
        },
        "on_the_shared_events": {
            "centred": summarise(c), "causal": summarise(o),
        },
        "paired_difference_causal_minus_centred": summarise(diff),
        "robustness_drop_largest_causal_contributor": {
            "dropped_event": str(biggest),
            "n_onsets_dropped": int(cau.loc[biggest, "n_onsets"]),
            "share_of_causal_onsets": float(cau.loc[biggest, "n_onsets"]
                                            / cau["n_onsets"].sum()),
            "causal": summarise(cau.loc[keep, "med_lead_u"]),
            "paired_difference": summarise(
                (cau.loc[keep, "med_lead_u"] - cen.loc[keep, "med_lead_u"]).to_numpy()),
        },
        "are_the_shared_events_special": {
            "what": ("If the 19 were events where the field leads under any kernel, the "
                     "CENTRED arm would already show a lead on them. It does not, and its "
                     "result on them is indistinguishable from its result on its other 26."),
            "centred_on_shared": summarise(c),
            "centred_on_its_other_events": summarise(cen.loc[only_cen, "med_lead_u"]),
            "mann_whitney_p": float(stats.mannwhitneyu(
                c.to_numpy(), cen.loc[only_cen, "med_lead_u"].to_numpy()).pvalue),
        },
        "reads": ("A positive paired difference that a sign test and a signed-rank test "
                  "both separate from zero, on events where the centred arm shows no lead "
                  "and is not distinguishable from the rest of its own population, is the "
                  "kernel and not the population."),
        "source": "research/scale_field/t1_paired_control.py:main",
        "reproduce": ".venv/Scripts/python.exe research/scale_field/t1_paired_control.py",
    }
    with open(rel(OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    p = out["populations"]; sh = out["on_the_shared_events"]
    pd_ = out["paired_difference_causal_minus_centred"]
    sp = out["are_the_shared_events_special"]
    print(f"centred contributing {p['centred_contributing']}, causal "
          f"{p['causal_contributing']}, shared {p['shared']}; "
          f"strict subset: {p['causal_is_strict_subset_of_centred']}")
    print(f"  on the shared {p['shared']}:")
    print(f"    centred  {sh['centred']['n_positive']}/{sh['centred']['n']} lead, "
          f"median {sh['centred']['median']:+.3f} s-units")
    print(f"    causal   {sh['causal']['n_positive']}/{sh['causal']['n']} lead, "
          f"median {sh['causal']['median']:+.3f} s-units")
    print(f"  paired difference: median {pd_['median']:+.3f} s-units, "
          f"{pd_['n_positive']}/{pd_['n']} positive, "
          f"sign p={pd_['sign_test_p']:.3e}, Wilcoxon p={pd_['wilcoxon_p']:.3e}")
    r = out["robustness_drop_largest_causal_contributor"]
    print(f"  dropping {r['dropped_event']} ({r['share_of_causal_onsets']:.0%} of onsets): "
          f"causal {r['causal']['n_positive']}/{r['causal']['n']} lead, paired "
          f"{r['paired_difference']['n_positive']}/{r['paired_difference']['n']} positive")
    print(f"  are the shared events special? centred on them "
          f"{sp['centred_on_shared']['median']:+.3f} vs "
          f"{sp['centred_on_its_other_events']['median']:+.3f} on its other "
          f"{sp['centred_on_its_other_events']['n']}, Mann-Whitney p="
          f"{sp['mann_whitney_p']:.3f}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
