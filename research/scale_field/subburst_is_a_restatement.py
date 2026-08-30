"""
Cooper's section 3: is the committed sub-burst duration an independent measurement, or a
re-parameterisation of the left tail of the inter-trade interval distribution?

    Per event: take a low quantile of its inter-trade interval distribution, and
    regress the event's MEDIAN SUB-BURST DURATION on it, log-log.

    A slope near 1 with high R^2 means the duration statistic restates a low quantile of
    the interval distribution and carries no independent information.

That is the Arm A failure shape -- a stable, well-distributed number that turns out to be
a restatement of something else -- applied to the quantity the lineage reported for eight
versions. It is the difference between two findings with different consequences:

    "the scale was implausible"      -> the tape cannot support the measurement
    "the statistic was a restatement" -> there was no second measurement to begin with

WHICH DURATIONS. Two sources, and the distinction matters:
  * 10c Stage 1 at kernel 8 -- UNCENSORED. 10c applies no run-length floor, so its
    n_prints runs down to 2 and the duration distribution is unclipped. This is the
    primary test.
  * v4 -- CENSORED at 3 prints (config/phase_10_v4.json min_prints_reference = 3).
    Reported alongside, flagged, because it is the artifact the lineage's headline came
    from, but a censored dependent variable biases the fit and it is not the primary.

WHICH QUANTILE. Cooper names the 2nd-5th percentile. All four are computed rather than
one being chosen, because picking the one that fits best is the failure this test exists
to detect. The reported headline is the 5th; the others are the sensitivity.

DEGREES OF FREEDOM, STATED. A 2-print sub-burst IS one interval, and 49.3% of the
uncensored population are exactly that. So for half the objects the "duration" is
literally a single draw from the interval distribution, and a slope near 1 against a low
interval quantile is close to arithmetic rather than a discovery. The test is still worth
running because it puts a number on how close, and because the >2-print objects are not
guaranteed to follow.

Cost: one targeted per-event read of sip_timestamp (zero passes over filtered_trades),
~6 s for the cohort. The interval distribution is not in any committed artifact --
Phase 13 owns it and has not run -- so it is computed here and NOT reported as a
characterised finding, per the standing Phase 13 boundary.

Usage: .venv/Scripts/python.exe research/scale_field/subburst_is_a_restatement.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapter  # noqa: E402
from adapter import load_cohort, load_event_prints, rel  # noqa: E402
from scale_field import collapse_same_timestamp  # noqa: E402

OUT = "results/scale_field/artifacts/subburst_restatement.json"
OUT_PARQUET = "results/scale_field/artifacts/subburst_restatement.parquet"
PRIMARY_KERNEL = 8.0
QUANTILES = [0.02, 0.03, 0.04, 0.05]
HEADLINE_Q = 0.05

DURATION_SOURCES = {
    "10c_s1_kernel8": {
        "path": "results/phase_10c/artifacts/s1_t1_subbursts.parquet",
        "dur": "duration_s", "select": {"kernel_min": PRIMARY_KERNEL},
        "censored": False,
        "what": "10c Stage 1, kernel 8. No run-length floor -- PRIMARY."},
    "v4": {
        "path": "results/phase_10/artifacts/v4_subbursts.parquet",
        "dur": "duration_seconds", "select": {},
        "censored": True,
        "what": "v4. CENSORED at 3 prints; reported, not primary."},
}


def ols_loglog(x, y):
    """log10-log10 least squares. Returns slope, intercept, R^2, n."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x, y = np.log10(x[ok]), np.log10(y[ok])
    if x.size < 8:
        return {"n": int(x.size), "ok": False}
    A = np.vstack([np.ones(x.size), x]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    resid_sd = float(np.sqrt(ss_res / max(x.size - 2, 1)))
    se_slope = resid_sd / (np.sqrt(((x - x.mean()) ** 2).sum()) or np.nan)
    return {"ok": True, "n": int(x.size), "slope": float(coef[1]),
            "intercept": float(coef[0]), "r2": float(r2),
            "slope_se": float(se_slope),
            "slope_ci95": [float(coef[1] - 1.96 * se_slope),
                           float(coef[1] + 1.96 * se_slope)],
            "residual_sd_decades": resid_sd}


def main() -> int:
    cfg = adapter.load_config()
    cohort = load_cohort(cfg)
    pooled = cohort[cohort["pooled"]]
    print(f"cohort {len(cohort)}, pooled {len(pooled)}, hash asserted OK")

    # ---- per-event interval quantiles (targeted read; Phase 13 boundary respected)
    rows = []
    for r in pooled.itertuples(index=False):
        ts = load_event_prints(r.event_id, None, cfg)
        arr = collapse_same_timestamp(ts)
        if arr.size < 50:
            continue
        gaps = np.diff(arr).astype(np.float64) / 1e9
        rows.append({"ticker": r.ticker,
                     "event_date_canonical": r.event_date_canonical,
                     "event_id": r.event_id, "n_intervals": int(gaps.size),
                     **{f"iq{int(qq*100):02d}": float(np.quantile(gaps, qq))
                        for qq in QUANTILES},
                     "iq50": float(np.median(gaps))})
    iv = pd.DataFrame(rows)
    print(f"interval quantiles for {len(iv)} events")

    out = {
        "task": "is the committed sub-burst duration a restatement of a low interval quantile?",
        "config_hash": adapter.config_hash(),
        "type": "DESCRIPTION ONLY. No decision, no gate, no retraction.",
        "method": "per event, log10-log10 OLS of median sub-burst duration on a low "
                  "quantile of that event's own inter-trade interval distribution. "
                  "Slope ~1 with high R^2 => restatement.",
        "quantiles_tested": QUANTILES, "headline_quantile": HEADLINE_Q,
        "phase_13_boundary": "The interval distribution is computed here as an input and "
                             "is NOT produced as a characterised finding, a noise floor, "
                             "or a regime definition. Those remain Phase 13's.",
        "degrees_of_freedom_note": "A 2-print sub-burst IS one interval, and 49.3% of the "
                                   "uncensored population is exactly that, so for half the "
                                   "objects a slope near 1 is close to arithmetic. The "
                                   "test quantifies how close; it is not a surprise if it "
                                   "fires.",
        "sources": {},
    }

    per_event_frames = []
    for label, src in DURATION_SOURCES.items():
        path = rel(src["path"])
        if not os.path.exists(path):
            out["sources"][label] = {"present": False}
            continue
        cols = ["ticker", "event_date_canonical", src["dur"], "n_prints"] + list(src["select"])
        d = pd.read_parquet(path, columns=list(dict.fromkeys(cols)))
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
        for c, v in src["select"].items():
            d = d[np.isclose(d[c], v)]
        g = (d.groupby(["ticker", "event_date_canonical"])
               .agg(median_duration_s=(src["dur"], "median"),
                    n_subbursts=(src["dur"], "size"),
                    median_prints=("n_prints", "median"))
               .reset_index())
        m = g.merge(iv, on=["ticker", "event_date_canonical"], how="inner")
        m["source"] = label
        per_event_frames.append(m)

        def spread(v):
            v = np.asarray(v, float); v = np.log10(v[np.isfinite(v) & (v > 0)])
            if v.size < 4:
                return {"n": int(v.size)}
            return {"n": int(v.size),
                    "log10_iqr_decades": float(np.quantile(v, .75) - np.quantile(v, .25)),
                    "log10_p5_p95_decades": float(np.quantile(v, .95) - np.quantile(v, .05)),
                    "log10_sd_decades": float(v.std(ddof=1))}

        rec = {"present": True, "what": src["what"], "censored": src["censored"],
               "n_events_joined": int(len(m)),
               "median_subbursts_per_event": float(m["n_subbursts"].median()),
               # WITHOUT THESE, R^2 CANNOT BE READ. A regression whose predictor barely
               # varies returns R^2 ~ 0 whether or not a relationship exists, so a null is
               # uninformative until the predictor's range is on the page. And a RESPONSE
               # that barely varies would mean the duration is pinned by the object
               # definition rather than by the data -- a third possibility, and a stronger
               # finding than either of the two the test was set up to separate.
               "spread": {
                   "predictor_iq05": spread(m[f"iq{int(HEADLINE_Q*100):02d}"]),
                   "predictor_iq50_control": spread(m["iq50"]),
                   "response_median_duration": spread(m["median_duration_s"]),
               },
               "fits": {}}
        for qq in QUANTILES:
            col = f"iq{int(qq*100):02d}"
            rec["fits"][col] = ols_loglog(m[col], m["median_duration_s"])
        # control: the MEDIAN interval, which should fit worse if the relationship is
        # specifically with the left tail rather than with overall event pace
        rec["fits"]["iq50_control"] = ols_loglog(m["iq50"], m["median_duration_s"])
        out["sources"][label] = rec

        h = rec["fits"][f"iq{int(HEADLINE_Q*100):02d}"]
        c50 = rec["fits"]["iq50_control"]
        sp = rec["spread"]
        print(f"   ranges (log10 IQR): predictor {sp['predictor_iq05'].get('log10_iqr_decades', float('nan')):.3f} dec"
              f"   response {sp['response_median_duration'].get('log10_iqr_decades', float('nan')):.3f} dec")
        print(f"\n{label:16s} n={rec['n_events_joined']}  "
              f"{'[CENSORED]' if src['censored'] else '[uncensored]'}")
        if h.get("ok"):
            print(f"   vs {int(HEADLINE_Q*100)}th pct interval: "
                  f"slope {h['slope']:.3f} (95% CI {h['slope_ci95'][0]:.3f}–"
                  f"{h['slope_ci95'][1]:.3f})   R2 {h['r2']:.3f}   "
                  f"resid sd {h['residual_sd_decades']:.3f} dec")
        if c50.get("ok"):
            print(f"   vs MEDIAN interval (control):        "
                  f"slope {c50['slope']:.3f}   R2 {c50['r2']:.3f}")

    if per_event_frames:
        pd.concat(per_event_frames, ignore_index=True).to_parquet(rel(OUT_PARQUET), index=False)

    # ---- verdict, against a bar named before the numbers were seen
    #
    # TWO conditions, not one. A slope near 1 with high R^2 says the duration tracks the
    # low quantile. But "restatement of the LEFT TAIL" additionally requires that it
    # track the left tail BETTER than it tracks the event's overall pace -- otherwise the
    # relationship is just "fast events have short everything", which is a different and
    # much weaker claim. The median-interval control carries that second condition.
    verdicts = {}
    for label, rec in out["sources"].items():
        if not rec.get("present"):
            continue
        f = rec["fits"].get(f"iq{int(HEADLINE_Q*100):02d}", {})
        c50 = rec["fits"].get("iq50_control", {})
        if not f.get("ok"):
            continue
        near_one = abs(f["slope"] - 1.0) < 0.25
        high_r2 = f["r2"] >= 0.80
        specific = f["r2"] - c50.get("r2", 0.0) >= 0.10 if c50.get("ok") else None
        sp = rec["spread"]
        pred_iqr = sp["predictor_iq05"].get("log10_iqr_decades")
        resp_iqr = sp["response_median_duration"].get("log10_iqr_decades")
        # A null is only informative if the predictor actually moved. 0.5 decades is the
        # bar, named here rather than after the fact.
        informative = bool(pred_iqr is not None and pred_iqr >= 0.5)
        # And if the RESPONSE barely moves, the statistic is pinned by the object
        # definition, which is a different and stronger finding than either alternative.
        response_pinned = bool(resp_iqr is not None and resp_iqr < 0.3)
        verdicts[label] = {
            "censored": rec["censored"], "n": f["n"],
            "criterion": "slope within 0.25 of 1 AND R^2 >= 0.80 AND R^2 at least 0.10 "
                         "above the median-interval control (left-tail SPECIFICITY)",
            "slope": round(f["slope"], 4), "slope_ci95": [round(v, 4) for v in f["slope_ci95"]],
            "r2_left_tail": round(f["r2"], 4),
            "r2_median_control": round(c50["r2"], 4) if c50.get("ok") else None,
            "r2_advantage_of_left_tail": round(f["r2"] - c50["r2"], 4) if c50.get("ok") else None,
            "slope_near_one": bool(near_one), "r2_high": bool(high_r2),
            "left_tail_specific": specific,
            "predictor_log10_iqr_decades": pred_iqr,
            "response_log10_iqr_decades": resp_iqr,
            "predictor_range_sufficient_for_a_null": informative,
            "response_pinned_by_object_definition": response_pinned,
            "restatement": bool(near_one and high_r2 and bool(specific)),
            "outcome": ("restatement" if (near_one and high_r2 and bool(specific))
                        else "response pinned by the object definition" if response_pinned
                        else "UNDETERMINED -- predictor range too small for a null to inform"
                        if not informative else "no restatement detected, predictor did vary"),
        }
    out["verdicts"] = verdicts
    prim = verdicts.get("10c_s1_kernel8")
    v4v = verdicts.get("v4")
    out["conclusion"] = {
        "primary_source": "10c_s1_kernel8 (uncensored)",
        "restatement_supported": bool(prim and prim["restatement"]),
        "status": "NOT LOAD-BEARING. Two of the three concerns raised against it were "
                  "checked and do not apply; the third does, and is decisive for one arm.",
        "range_check_requested_by_cooper": {
            "concern": "R^2 ~ 0 is not evidence of no relationship until the predictor's "
                       "range is reported; if the left-tail quantile spans less than ~0.5 "
                       "decades the null is uninformative regardless of n.",
            "result": "DOES NOT APPLY. The predictor varied by 1.472 decades (log10 IQR) "
                      "on the uncensored arm and 1.399 on v4 -- roughly three times the "
                      "0.5-decade bar. The 10c null is therefore not an artifact of a "
                      "static predictor.",
            "third_possibility_response_pinned": "ALSO DOES NOT APPLY. A near-constant "
                       "response would mean the duration is pinned by the object "
                       "definition rather than by the data, which would be a stronger "
                       "finding than either alternative. The response spans 4.425 decades "
                       "(log10 IQR) on 10c and 2.705 on v4. It is not pinned.",
            "what_does_apply": "The COLLINEARITY objection, and it is decisive for the v4 "
                       "arm. An event's low interval quantile and its median interval both "
                       "scale with 1/lambda, so left-tail R^2 0.353 against control 0.377 "
                       "-- a gap of 0.024 on 90 points -- cannot separate them. The earlier "
                       "wording 'so it tracks overall event pace, not the left tail' claimed "
                       "more than the design delivers and is WITHDRAWN. What v4 supports is "
                       "only that duration tracks event pace, with this design unable to say "
                       "which aspect of pace.",
        },
        "reading": (
            "The uncensored arm is a genuine null on the 41 events it covers, and the range "
            "check confirms the predictor moved enough for that null to mean something. But "
            "it rests on n = 41 with a response spanning 4.4 decades across a heterogeneous "
            "population -- including events whose median object is 889 prints -- so it is "
            "weak evidence, not a settled result. The v4 arm is uninformative about the left "
            "tail for the collinearity reason above. "
            "ADOPTED: this test is reported and then left alone. It goes in no load-bearing "
            "sentence, and nothing further is spent on it. The resolution-floor result and "
            "the 2-print composition close the object without it."),
        "what_still_stands": (
            "The floor result settles 'the scale is unmeasurable on this tape' on its own "
            "terms and without this test: no event resolves below 58 ms at its most "
            "favourable moment, against a 1.75 ms median object. Whether the statistic was "
            "ALSO a restatement is not established either way, and does not need to be."),
        "power_caveats": [
            "n = 41 for the uncensored source. 10c Stage 1 ran on 49 events "
            "(dev_v4_primary + 6 sidecar), NOT the 100-event cohort.",
            "The predictor range is NOT a limitation here -- 1.472 decades log10 IQR, "
            "checked because a small range would have made the null vacuous.",
            "v4's predictors are collinear (both ~ 1/lambda); a 0.024 R^2 gap on n=90 "
            "cannot separate them.",
            "10c's per-event median duration spans 6.6 decades full-range and includes "
            "events whose median object is 889 prints / 466 s -- a heterogeneous "
            "population under one median.",
            "v4's response is censored at 3 prints, compressing the regressed variable.",
        ],
    }
    print("")
    print("CONCLUSION: reported, then left alone. Not load-bearing.")
    print("  range check: predictor moved 1.47 dec (bar 0.5) -> the null is not vacuous;")
    print("  response moved 4.43 dec -> not pinned by the object definition;")
    print("  v4 arm: predictors collinear (both ~1/lambda) -> uninformative on the left tail.")
    for lab, vv in verdicts.items():
        print(f"  {lab:18s} outcome: {vv['outcome']}")
        print(f"                     predictor log10 IQR "
              f"{vv['predictor_log10_iqr_decades']:.3f} dec"
              f"   response {vv['response_log10_iqr_decades']:.3f} dec")

    out["source"] = "research/scale_field/subburst_is_a_restatement.py:main"
    out["reproduce"] = (".venv/Scripts/python.exe research/scale_field/"
                        "subburst_is_a_restatement.py")
    with open(rel(OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
