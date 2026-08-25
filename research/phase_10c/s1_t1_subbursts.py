"""
Phase 10c Stage 1, T1 -- sub-burst extraction across the nine (variant x kernel) cells.

DESIGN NOTE, stated rather than left implicit: the sub-burst extraction itself (tie
collapse, D1 aggregation, centered clock-time local median, histogram, envelope-boundary
threshold, sub-burst runs) is a function of (event, kernel) ONLY. Nothing in T1.1-T1.4's
math reads the threshold variant -- the variant only determines (a) which segment
(evening/premarket/rth/unlabelled) an event is stratified into for reporting, via
assign_segment() on that variant's own anchor, and (b) where the anchor sits for
anchor-relative reporting (T3). Recomputing the identical interval sequence, local
median and threshold three times under three variant labels would be pure duplication,
not three independent measurements. So this script computes each event's sub-bursts
ONCE PER KERNEL (56 x 3 = 168 computations, not 504), then cross-joins the result onto
each variant's own segment/anchor labelling to produce the nine reported cells. Every
number in every cell is what independent per-variant computation would have produced
-- the recomputation would be identical -- this only avoids doing it three times.

T1a  per event/cell: threshold (or label), void, peak count, sub-burst count
T1b  per sub-burst: start, end, duration, print count, share of the event's price move
T1c  label population report, per cell, per segment, with n stated

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t1_subbursts.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_prominences

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import common as p10  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
ET = "America/New_York"
VARIANTS = [1.25, 1.30, 1.35]
KERNELS = [2.0, 8.0, 32.0]
KEY = ["ticker", "event_date_canonical"]

# Anchor print condition codes from Amendment 4/6's discriminant test (nearest-match
# lookup already run -- not re-queried here). BMR is INCLUDED for provenance/parity
# with that test's own 4-anchor list but is DEAD for this script: BMR's cohort_group
# is 'activity_extension' (results/phase_10/artifacts/t1_cohort_manifest.parquet),
# not dev_v4_primary/dev_v4_sidecar, so it never appears in c10c.load_dev_sample()
# and this dict entry never matches. Discovered running this script (T1's waterfall
# initially looked short one 'evening' event vs. the 3 the amendments described) --
# Amendment 4-6's own condition-code census ("114-event cohort") was computed over
# t1_cohort_manifest.parquet WITHOUT restricting to the 56-event dev sample, silently
# mixing in 58 activity_extension/row_cap_census events. The TRUE dev-sample-scoped
# evening population at threshold 1.35 is 2 (OST, CELH) -- ACET has no anchor at 1.35
# and BMR was never a dev-sample event. Does not change the {8,15} code-set decision
# (BMR's own codes {12,37} carry neither code either way) but the population named
# throughout Amendment 4-6 ("114-event cohort") was not the Stage-1 dev sample and
# that was never stated. Flagged to docs/Open-Items-Register.md, not corrected
# retroactively in the tagged/closed amendment artifacts.
ANCHOR_CODES = {"ACET": {8, 9, 41}, "OST": {14, 12, 41}, "CELH": {12}, "BMR": {12, 37}}


def peaks_poisson(cnt):
    pk, _ = find_peaks(cnt)
    if pk.size == 0:
        return pk, np.zeros(0)
    prom = peak_prominences(cnt, pk)[0]
    keep = prom > np.sqrt(np.maximum(cnt[pk], 1))
    return pk[keep], prom[keep]


def envelope_boundary(centers, dens, pks):
    """A2.7.D17 -- argmax void across ALL troughs. Void ranks, never gates (D13)."""
    best = None
    for a, b in zip(pks[:-1], pks[1:]):
        if b - a < 2:
            continue
        seg = dens[a + 1:b]
        t = a + 1 + int(np.argmin(seg))
        den = np.sqrt(dens[a] * dens[b])
        if den <= 0:
            continue
        v = float(1.0 - dens[t] / den)
        if best is None or v > best["void"]:
            best = {"idx": int(t), "loc": float(centers[t]), "void": v,
                    "peak_l": int(a), "peak_r": int(b)}
    return best


def variant_segment(det_row, cal):
    """assign_segment() on ONE variant's own anchor, with the auction override applied
    via the known anchor codes. Returns (segment_or_None, det_ns_or_nan)."""
    if det_row is None or pd.isna(det_row.get("det_ns_poll0")):
        return None, np.nan
    det_ns = int(det_row["det_ns_poll0"])
    a = pd.Timestamp(det_ns, unit="ns", tz="UTC").tz_convert(ET)
    sess = cal.date_to_session(pd.Timestamp(det_row["event_date_canonical"]), direction="previous")
    opn = cal.session_open(sess).tz_convert(ET)
    close = cal.session_close(sess).tz_convert(ET)
    codes = ANCHOR_CODES.get(det_row["ticker"])
    return c10c.assign_segment(a, codes, opn, close), det_ns


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    F = float(c10c.class_m(cfg)["D4_median_precision_factor"])

    dev = c10c.load_dev_sample(cfg)
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)

    t0 = time.perf_counter()
    cell_rows, sb_rows = [], []
    wf = {"events_in_dev_sample": int(len(dev)), "events_with_prints": 0,
          "prints_raw": 0, "prints_tie_collapsed": 0, "prints_after_D1": 0,
          "intervals": 0, "kernel_cell_computations": 0, "subbursts_total": 0}

    for i, r in enumerate(dev.itertuples(index=False), 1):
        d = p10.read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                  offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        wf["events_with_prints"] += 1
        raw_ts = s0["sip_timestamp"].to_numpy()
        raw_px = s0["price"].to_numpy(dtype=np.float64)
        wf["prints_raw"] += int(raw_ts.size)

        # -------- tie collapse then D1 aggregation, carrying VWAP (variant/kernel independent)
        uniq, inv = np.unique(raw_ts, return_inverse=True)
        wf["prints_tie_collapsed"] += int(uniq.size)
        sz = s0["size"].to_numpy(dtype=np.float64)
        wsum = np.bincount(inv, weights=raw_px * sz, minlength=uniq.size)
        ssum = np.bincount(inv, weights=sz, minlength=uniq.size)
        px_u = np.where(ssum > 0, wsum / np.maximum(ssum, 1e-12),
                        np.bincount(inv, weights=raw_px, minlength=uniq.size)
                        / np.maximum(np.bincount(inv, minlength=uniq.size), 1))
        d1_us = float(c10c.class_m(cfg)["D1_sweep_floor_us"])
        agg_ts, _ = c10c.sweep_aggregate(uniq, d1_us)
        gi = np.searchsorted(uniq, agg_ts)
        bnd = np.append(gi, uniq.size)
        grp = np.repeat(np.arange(agg_ts.size), np.diff(bnd))
        gw = np.bincount(grp, weights=px_u[:uniq.size] * ssum, minlength=agg_ts.size)
        gs = np.bincount(grp, weights=ssum, minlength=agg_ts.size)
        agg_px = np.where(gs > 0, gw / np.maximum(gs, 1e-12), px_u[gi])
        wf["prints_after_D1"] += int(agg_ts.size)
        if agg_ts.size < 20:
            continue

        dt_s = np.diff(agg_ts).astype(np.float64) / 1e9
        keep = dt_s > 0
        li = np.log10(dt_s[keep])
        mid = ((agg_ts[:-1].astype(np.float64) + agg_ts[1:].astype(np.float64)) / 2.0)[keep]
        wf["intervals"] += int(li.size)
        b = c10c.session_bounds(r.event_date_canonical)
        if b is None:
            continue
        sigma = float(np.std(li, ddof=1))
        floor = c10c.median_se_min_count(sigma, F)

        edges = np.array([b["start_ns"], b["rth_open_ns"], b["rth_close_ns"], b["end_ns"]],
                         dtype=np.float64)
        seg_i = np.clip(np.searchsorted(edges, mid, "right") - 1, 0, len(edges) - 2)

        # -------- per-variant context: segment + anchor, computed once per event
        var_ctx = {}
        for v in VARIANTS:
            row = det[(det.ticker == r.ticker) & (det.event_date_canonical
                      == r.event_date_canonical) & (np.isclose(det.threshold, v))]
            seg, det_ns = variant_segment(row.iloc[0].to_dict() if len(row) else None, cal)
            var_ctx[v] = {"segment": seg, "det_ns": det_ns}

        key = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
               "cohort_group": r.cohort_group, "is_sidecar": bool(r.is_sidecar)}
        tot_move = float(np.abs(np.diff(agg_px)).sum())

        # -------- per-kernel sub-burst computation (variant-independent)
        for k_min in KERNELS:
            wf["kernel_cell_computations"] += 1
            half = k_min * 60.0 * 1e9 / 2.0
            lo = np.maximum(mid - half, edges[seg_i])
            hi = np.minimum(mid + half, edges[seg_i + 1])
            clipped = (mid - half < edges[seg_i]) | (mid + half > edges[seg_i + 1])

            ser = pd.Series(li, index=pd.to_datetime(mid.astype("int64"), unit="ns"))
            loc_med = np.full(li.size, np.nan)
            wcount = np.zeros(li.size)
            win = f"{int(k_min)}min"
            for _bi in np.unique(seg_i):
                m_ = seg_i == _bi
                sub = ser[m_]
                if sub.size == 0:
                    continue
                _roll = sub.rolling(win, center=True, min_periods=1)
                loc_med[m_] = _roll.median().to_numpy()
                wcount[m_] = _roll.count().to_numpy()

            ok = wcount >= floor if np.isfinite(floor) else np.zeros(li.size, bool)
            base = {**key, "kernel_min": k_min, "sigma_log10": sigma,
                    "derived_floor": float(floor), "n_intervals": int(li.size),
                    "clipped_fraction": float(clipped.mean()),
                    "insufficient_context_fraction": float((~ok).mean())}

            if ok.sum() < 50:
                cell_rows.append({**base, "label": "insufficient_context",
                                  "threshold_norm": np.nan, "void": np.nan,
                                  "n_peaks": 0, "n_subbursts": 0})
                continue

            norm = li - loc_med
            nv = norm[ok & np.isfinite(norm)]
            e_lo, e_hi = np.floor(nv.min() * 10) / 10, np.ceil(nv.max() * 10) / 10 + 0.1
            bins = np.arange(e_lo, e_hi, 0.1)
            cnt, _ = np.histogram(nv, bins=bins)
            centers = (bins[:-1] + bins[1:]) / 2.0
            dens = cnt / (cnt.sum() * 0.1)
            pks, _ = peaks_poisson(cnt)
            env = envelope_boundary(centers, dens, pks) if pks.size >= 2 else None
            if env is None:
                cell_rows.append({**base, "label": "no_threshold", "threshold_norm": np.nan,
                                  "void": np.nan, "n_peaks": int(pks.size), "n_subbursts": 0})
                continue

            thr = env["loc"]
            below = [p for p in pks if centers[p] <= thr]
            silent = bool(len(below) >= 2 and max(below, key=lambda q: dens[q]) != below[0])
            inb = ok & np.isfinite(norm) & (norm < thr)
            idx = np.flatnonzero(inb)
            runs = np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1) if idx.size else []
            in_move = 0.0
            for run in runs:
                t_s, t_e = agg_ts[run[0]], agg_ts[run[-1] + 1]
                p_s, p_e = agg_px[run[0]], agg_px[run[-1] + 1]
                mv = float(abs(p_e - p_s))
                in_move += mv
                sb_rows.append({**key, "kernel_min": k_min, "n_intervals": int(run.size),
                                "n_prints": int(run.size + 1),
                                "start_ns": int(t_s), "end_ns": int(t_e),
                                "duration_s": float((t_e - t_s) / 1e9), "abs_move": mv,
                                "move_share": (mv / tot_move) if tot_move > 0 else np.nan})
            wf["subbursts_total"] += len(runs)
            cell_rows.append({**base, "label": "ok", "threshold_norm": float(thr),
                              "void": env["void"], "n_peaks": int(pks.size),
                              "n_subbursts": len(runs), "silent_selection": silent,
                              "move_share_in_subbursts": (in_move / tot_move)
                              if tot_move > 0 else np.nan})

        if i % 10 == 0:
            print(f"  {i}/{len(dev)} ({time.perf_counter()-t0:.0f}s)", flush=True)

    cells = pd.DataFrame(cell_rows)
    sb = pd.DataFrame(sb_rows)

    # -------- cross-join kernel-level results onto each variant's segment/anchor context
    rows_v = []
    for i, r in enumerate(dev.itertuples(index=False)):
        for v in VARIANTS:
            row = det[(det.ticker == r.ticker) & (det.event_date_canonical
                      == r.event_date_canonical) & (np.isclose(det.threshold, v))]
            seg, det_ns = variant_segment(row.iloc[0].to_dict() if len(row) else None, cal)
            rows_v.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                           "threshold": v, "segment": seg, "det_ns": det_ns})
    ctx = pd.DataFrame(rows_v)
    ctx_full = ctx.merge(cells, on=["ticker", "event_date_canonical"], how="left")

    assert ctx_full.groupby(["ticker", "event_date_canonical", "threshold"]).kernel_min.nunique() \
        .eq(len(KERNELS)).all(), "every event/variant must carry all 3 kernels"
    assert set(ctx_full.threshold.unique()) == set(VARIANTS), "no variant dropped at load"

    ctx_full.to_parquet(rel(f"{ART}/s1_t1_cells.parquet"), index=False)
    sb.to_parquet(rel(f"{ART}/s1_t1_subbursts.parquet"), index=False)
    wf["timing_seconds"] = round(time.perf_counter() - t0, 1)
    wf["config_hash"] = chash
    wf["design_note"] = ("sub-burst extraction computed once per (event, kernel) -- 56x3=168 -- "
                         "then cross-joined onto each of 3 variants' own segment/anchor context "
                         "to form the 9 reported cells. See module docstring.")
    c10c.write_json(rel(f"{ART}/s1_t1_waterfall.json"), wf)

    print(f"\nwaterfall: {wf}")
    print(f"\nlabel counts (per event/kernel, variant-independent):")
    print(cells.groupby("kernel_min").label.value_counts().unstack(fill_value=0))
    print(f"\nlabel counts by (variant, kernel, segment), n stated:")
    t1c = (ctx_full.groupby(["threshold", "kernel_min", "segment"], dropna=False)
           .label.value_counts().rename("n").reset_index())
    t1c.to_parquet(rel(f"{ART}/s1_t1c_label_population.parquet"), index=False)
    for (v, k), g in t1c.groupby(["threshold", "kernel_min"]):
        print(f"  thr={v} kernel={k}min:")
        for _, rr in g.iterrows():
            print(f"    segment={rr.segment!s:12s} label={rr.label:22s} n={rr.n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
