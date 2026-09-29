"""
Shape classifier S2 -- the seven charts (brief section 8). Dark theme, plotly.js inlined (D14), n on every panel.
Each file is one page with linked <select>s (the S1 atlas pattern); every selector combination is a precomputed
figure keyed by the selector values, so the page logic is only a lookup and Plotly.react.

  t4/auc_by_time.html     AUC with 95% ticker-bootstrap intervals, type x decision time, one line per model;
                          read (primary / secondary), class weight, fold (each, or the mean with the fold range), label rung
  t4/lift_by_time.html    top-10% lift, same layout
  t4/calibration.html     predicted vs observed per type, n per bin; model, decision time, fold (or pooled)
  t4/confusion.html       argmax type vs true type, counts and row shares; model, decision time, read, fold (or summed)
  t6/forward_returns.html top-decile events vs all primary test events, 21 quantiles of the net return, per type;
                          model, decision time, horizon, entry latency, unit (bp / cents)
  t7/importance.html      permutation importance share per input, M3, per type; decision time, fold (or mean)
  t5/controls.html        negative control (mean of 3 folds x 10 shuffles, with the single-shuffle range) and the two
                          positive controls, per type x decision time

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/charts.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from plotly.offline import get_plotlyjs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

BG, FG, GRID, PANEL = "#111418", "#e6e6e6", "#2a2f36", "#1d2229"
PAL = {"M0": "#9aa4b2", "M1": "#ffd43b", "M2": "#4ea1ff", "M3": "#ff6b6b", "M4": "#7ed957", "all": "#9aa4b2", "top": "#ffb347"}
MODELS = [("M0", "none"), ("M1", "none"), ("M2", "none"), ("M2", "balanced"), ("M3", "none"), ("M3", "balanced"), ("M4", "none"), ("M4", "balanced")]
TL = [S.TIME_LABEL[t] for t in S.TIMES]
HDR = ("S2 exploratory modelling build; test = ticker-blocked, time-ordered folds (2022 / 2023 / 2024). "
       "Label = S1 theory type at N = 100 (hindsight by definition).")


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 5)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def grid_layout(nr: int, nc: int, titles: list[str], h: int = 820, xtitle: str = "", ytitle: str = "", extra: dict | None = None) -> dict:
    lay = {"paper_bgcolor": BG, "plot_bgcolor": BG, "font": {"color": FG, "size": 12}, "height": h, "margin": {"l": 60, "r": 20, "t": 90, "b": 60},
           "showlegend": True, "legend": {"orientation": "h", "y": 1.07, "x": 0, "bgcolor": "rgba(0,0,0,0)"}, "annotations": []}
    gx, gy = 0.05, 0.1
    w, hh = (1 - gx * (nc - 1)) / nc, (1 - gy * (nr - 1)) / nr
    for i in range(nr * nc):
        r, c = divmod(i, nc)
        k = "" if i == 0 else str(i + 1)
        x0, y1 = c * (w + gx), 1 - r * (hh + gy)
        lay[f"xaxis{k}"] = {"domain": [x0, x0 + w], "anchor": f"y{k}", "gridcolor": GRID, "zeroline": False, "title": {"text": xtitle}}
        lay[f"yaxis{k}"] = {"domain": [y1 - hh, y1], "anchor": f"x{k}", "gridcolor": GRID, "zeroline": False, "title": {"text": ytitle if c == 0 else ""}}
        if i < len(titles):
            lay["annotations"].append({"text": titles[i], "x": x0 + w / 2, "y": y1 + 0.01, "xref": "paper", "yref": "paper",
                                       "showarrow": False, "xanchor": "center", "yanchor": "bottom", "font": {"size": 12}})
    if extra:
        for k, v in extra.items():
            if isinstance(v, dict) and k in lay:
                lay[k].update(v)
            else:
                lay[k] = v
    return lay


def ax(i: int) -> tuple[str, str]:
    k = "" if i == 0 else str(i + 1)
    return f"x{k}", f"y{k}"


def page(task: str, name: str, title: str, note: str, selectors: list[tuple[str, str, list[tuple[str, str]]]], figs: dict) -> None:
    sel_html = "".join(f'<label>{lab} <select id="{sid}">' + "".join(f'<option value="{v}">{t}</option>' for v, t in opts) + "</select></label>"
                       for sid, lab, opts in selectors)
    ids = json.dumps([s[0] for s in selectors])
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
<script>{get_plotlyjs()}</script>
<style>body{{background:{BG};color:{FG};font-family:Segoe UI,Helvetica,Arial,sans-serif;margin:16px}}
h1{{font-size:20px;margin:4px 0}} .note{{color:#9aa4b2;font-size:12px;max-width:1400px}} label{{margin-right:14px;font-size:13px}}
select{{background:{PANEL};color:{FG};border:1px solid #3a414b;padding:3px 6px;border-radius:4px}} #missing{{color:#ffb347}}</style></head>
<body><h1>{title}</h1><div class="note">{HDR}<br>{note}</div><div style="margin:10px 0">{sel_html}</div><div id="missing"></div><div id="fig"></div>
<script>
const FIGS = {json.dumps(clean(figs), separators=(",", ":"))};
const IDS = {ids};
function draw() {{
  const key = IDS.map(i => document.getElementById(i).value).join("|");
  const f = FIGS[key];
  document.getElementById("missing").textContent = f ? "" : "no data for this combination (" + key + ")";
  if (f) Plotly.react("fig", f.data, f.layout, {{responsive: true, displaylogo: false}});
}}
IDS.forEach(i => document.getElementById(i).addEventListener("change", draw));
draw();
</script></body></html>"""
    with open(S.chart_path(task, name), "w", encoding="utf-8") as fh:
        fh.write(html)


# ====================================================================== AUC and lift by time
def by_time(metric: str) -> None:
    src = pd.read_parquet(S.art("t4_auc.parquet" if metric == "auc" else "t4_lift.parquet"))
    if metric == "lift":
        src["label_N"] = 100
        src["ci_lo"] = np.nan
        src["ci_hi"] = np.nan
        src = src.rename(columns={"lift": "auc"})
    figs = {}
    for read in ("primary", "secondary"):
        for cw in ("none", "balanced"):
            for fold in ("mean", "1", "2", "3"):
                for N in ((100, 50, 200) if metric == "auc" else (100,)):
                    d = src[(src["read"] == read) & (src["label_N"] == N)]
                    data, titles = [], []
                    for i, t in enumerate(S.TYPES):
                        xa, ya = ax(i)
                        dt = d[d["type"] == t]
                        n_note = []
                        for mdl, mcw in MODELS:
                            if mcw != cw and mdl not in ("M0", "M1"):
                                continue
                            g = dt[(dt["model"] == mdl) & (dt["cw"] == mcw)]
                            if g.empty:
                                continue
                            if fold == "mean":
                                a = g.groupby("time").agg(y=("auc", "mean"), lo=("auc", "min"), hi=("auc", "max"), n=("n_type", "sum"),
                                                          rd=("read_ok", "sum")).reindex(S.TIMES)
                                err = {"type": "data", "symmetric": False, "array": (a["hi"] - a["y"]).tolist(), "arrayminus": (a["y"] - a["lo"]).tolist(),
                                       "color": PAL[mdl], "thickness": 1}
                                txt = [f"{S.TIME_LABEL[k]}: mean {y:.3f} (fold range {lo:.3f}-{hi:.3f}); n_type over folds {n:.0f}; folds read {r:.0f}/3"
                                       if np.isfinite(y) else "" for k, y, lo, hi, n, r in zip(S.TIMES, a["y"], a["lo"], a["hi"], a["n"], a["rd"])]
                                sym = ["circle" if (r == 3) else "circle-open" for r in a["rd"].fillna(0)]
                            else:
                                a = g[g["fold"] == int(fold)].set_index("time").reindex(S.TIMES)
                                err = {"type": "data", "symmetric": False, "array": (a["ci_hi"] - a["auc"]).tolist(), "arrayminus": (a["auc"] - a["ci_lo"]).tolist(),
                                       "color": PAL[mdl], "thickness": 1}
                                a["y"] = a["auc"]
                                txt = [f"{S.TIME_LABEL[k]}: {y:.3f} [{lo:.3f}, {hi:.3f}]; n {n:.0f}, n_type {nt:.0f}{'' if ok else ' -- row 5: not read'}"
                                       if np.isfinite(y) else "" for k, y, lo, hi, n, nt, ok in zip(S.TIMES, a["y"], a["ci_lo"], a["ci_hi"], a["n"], a["n_type"], a["read_ok"].fillna(True))]
                                sym = ["circle" if ok else "circle-open" for ok in a["read_ok"].fillna(True)]
                                if mdl == "M0":
                                    n_note = [f"{S.TIME_LABEL[k]} n={int(n)}/{int(nt)}" for k, n, nt in zip(S.TIMES, a["n"].fillna(0), a["n_type"].fillna(0)) if n]
                            data.append({"type": "scatter", "mode": "lines+markers", "x": TL, "y": a["y"].tolist(), "name": f"{mdl}" + (f" ({mcw})" if mdl in ("M2", "M3", "M4") else ""),
                                         "legendgroup": mdl, "showlegend": i == 0, "line": {"color": PAL[mdl], "width": 2 if mdl in ("M2", "M3", "M4") else 1},
                                         "marker": {"symbol": sym, "size": 7}, "error_y": err if metric == "auc" or fold == "mean" else {"visible": False},
                                         "text": txt, "hoverinfo": "text+name", "xaxis": xa, "yaxis": ya})
                        ref = 0.5 if metric == "auc" else 1.0
                        data.append({"type": "scatter", "mode": "lines", "x": [TL[0], TL[-1]], "y": [ref, ref], "line": {"color": "#555", "dash": "dot", "width": 1},
                                     "showlegend": False, "hoverinfo": "skip", "xaxis": xa, "yaxis": ya})
                        nt = dt[(dt["model"] == "M0") & (dt["time"] == "tau")]
                        ntot = nt["n"].sum() if fold == "mean" else nt[nt["fold"] == int(fold)]["n"].sum()
                        ntyp = nt["n_type"].sum() if fold == "mean" else nt[nt["fold"] == int(fold)]["n_type"].sum()
                        titles.append(f"{S.TYPE_LABEL[t]} -- at τ n={int(ntot)}, n_type={int(ntyp)}" + (" (3 folds)" if fold == "mean" else f" (fold {fold})"))
                    ylab = "AUC (one type vs rest)" if metric == "auc" else "top-10% lift"
                    lay = grid_layout(2, 3, titles, xtitle="decision time", ytitle=ylab)
                    lay["title"] = {"text": f"{'AUC' if metric == 'auc' else 'Top-10% lift'} by decision time -- {read} read, class weight {cw}, "
                                            f"{'mean of 3 folds (bars = fold range)' if fold == 'mean' else 'fold ' + fold + (' (bars = 95% ticker bootstrap)' if metric == 'auc' else '')}"
                                            + (f", label N = {N}" if metric == "auc" else ""), "x": 0.01}
                    figs[f"{read}|{cw}|{fold}|{N}"] = {"data": data, "layout": lay}
    sel = [("read", "read", [("primary", "primary (tickers unseen in training)"), ("secondary", "secondary (all test events)")]),
           ("cw", "class weight (M2-M4)", [("none", "none"), ("balanced", "balanced")]),
           ("fold", "fold", [("mean", "mean of 3 folds"), ("1", "fold 1 (test 2022)"), ("2", "fold 2 (test 2023)"), ("3", "fold 3 (test 2024)")]),
           ("N", "label rung", [("100", "N = 100 (fitted)"), ("50", "N = 50 (secondary label)"), ("200", "N = 200 (secondary label)")] if metric == "auc" else [("100", "N = 100")])]
    note = ("Hollow markers: escalation row 5 -- fewer than 20 events of the type in that fold's primary set at that decision time (shown, not read). "
            "M1 runs at τ only; M4 after τ only. Volume checkpoints are scored on the events that reached them (n per point in the hover).")
    page("t4", f"{metric}_by_time.html", "AUC by decision time" if metric == "auc" else "Top-10% lift by decision time", note, sel, figs)


# ====================================================================== calibration
def calibration() -> None:
    cal = pd.read_parquet(S.art("t4_calibration.parquet"))
    cal = cal[cal["read"] == "primary"]
    figs = {}
    for mdl, cw in MODELS:
        for t in S.TIMES:
            g0 = cal[(cal["model"] == mdl) & (cal["cw"] == cw) & (cal["time"] == t)]
            if g0.empty:
                continue
            for fold in ("pooled", "1", "2", "3"):
                data, titles = [], []
                for i, ty in enumerate(S.TYPES):
                    xa, ya = ax(i)
                    g = g0[g0["type"] == ty]
                    if fold == "pooled":
                        g = g.assign(sp=g["mean_pred"] * g["n"], so=g["obs_freq"] * g["n"]).groupby("bin_lo").agg(n=("n", "sum"), sp=("sp", "sum"), so=("so", "sum")).reset_index()
                        g["mean_pred"], g["obs_freq"] = g["sp"] / g["n"], g["so"] / g["n"]
                    else:
                        g = g[g["fold"] == int(fold)]
                    g = g[g["n"] > 0]
                    data.append({"type": "scatter", "mode": "markers+text", "x": g["mean_pred"].tolist(), "y": g["obs_freq"].tolist(),
                                 "text": [f"n={int(n)}" for n in g["n"]], "textposition": "top center", "textfont": {"size": 9},
                                 "marker": {"size": (4 + 2 * np.log1p(g["n"])).tolist(), "color": PAL[mdl]}, "showlegend": False,
                                 "hovertext": [f"bin [{lo:.2f}, ): mean predicted {p:.3f}, observed {o:.3f}, n {int(n)}" for lo, p, o, n in zip(g["bin_lo"], g["mean_pred"], g["obs_freq"], g["n"])],
                                 "hoverinfo": "text", "xaxis": xa, "yaxis": ya})
                    mx = float(max(0.05, np.nanmax(np.r_[g["mean_pred"], g["obs_freq"]]) if len(g) else 0.05))
                    data.append({"type": "scatter", "mode": "lines", "x": [0, mx], "y": [0, mx], "line": {"color": "#555", "dash": "dot"}, "showlegend": False,
                                 "hoverinfo": "skip", "xaxis": xa, "yaxis": ya})
                    titles.append(f"{S.TYPE_LABEL[ty]} -- n={int(g['n'].sum())}")
                lay = grid_layout(2, 3, titles, xtitle="mean predicted probability", ytitle="observed frequency")
                lay["title"] = {"text": f"Calibration -- {mdl} ({cw}), {S.TIME_LABEL[t]}, primary read, {'3 folds pooled' if fold == 'pooled' else 'fold ' + fold}", "x": 0.01}
                figs[f"{mdl}:{cw}|{t}|{fold}"] = {"data": data, "layout": lay}
    sel = [("m", "model", [(f"{m}:{c}", f"{m} ({c})") for m, c in MODELS]), ("t", "decision time", [(t, S.TIME_LABEL[t]) for t in S.TIMES]),
           ("f", "fold", [("pooled", "3 folds pooled"), ("1", "fold 1"), ("2", "fold 2"), ("3", "fold 3")])]
    page("t4", "calibration.html", "Calibration", "Bins: " + ", ".join(str(x) for x in S.load_cfg()["scores"]["calibration_edges"]) + ". Marker size grows with n; n printed per bin.", sel, figs)


# ====================================================================== confusion
def confusion() -> None:
    cf = pd.read_parquet(S.art("t4_confusion.parquet"))
    figs = {}
    for mdl, cw in MODELS:
        for t in S.TIMES:
            for read in ("primary", "secondary"):
                g0 = cf[(cf["model"] == mdl) & (cf["cw"] == cw) & (cf["time"] == t) & (cf["read"] == read)]
                if g0.empty:
                    continue
                for fold in ("sum", "1", "2", "3"):
                    g = g0 if fold == "sum" else g0[g0["fold"] == int(fold)]
                    m = g.pivot_table(index="true", columns="pred", values="n", aggfunc="sum").reindex(index=S.TYPES, columns=S.TYPES).fillna(0)
                    rs = m.div(m.sum(axis=1).replace(0, np.nan), axis=0)
                    txt = [[f"{int(m.iloc[i, j])}<br>{rs.iloc[i, j]:.0%}" if np.isfinite(rs.iloc[i, j]) else "0" for j in range(6)] for i in range(6)]
                    data = [{"type": "heatmap", "z": rs.values.tolist(), "x": [S.TYPE_LABEL[x] for x in S.TYPES], "y": [f"{S.TYPE_LABEL[x]} (n={int(m.loc[x].sum())})" for x in S.TYPES],
                             "text": txt, "texttemplate": "%{text}", "colorscale": "Blues", "zmin": 0, "zmax": 1, "colorbar": {"title": {"text": "row share"}}}]
                    lay = {"paper_bgcolor": BG, "plot_bgcolor": BG, "font": {"color": FG}, "height": 620, "margin": {"l": 170, "r": 40, "t": 80, "b": 80},
                           "title": {"text": f"Confusion at the most probable type -- {mdl} ({cw}), {S.TIME_LABEL[t]}, {read}, {'3 folds summed' if fold == 'sum' else 'fold ' + fold}; n={int(m.values.sum())}", "x": 0.01},
                           "xaxis": {"title": {"text": "predicted (argmax)"}}, "yaxis": {"title": {"text": "true type (S1, N = 100)"}, "autorange": "reversed"}}
                    figs[f"{mdl}:{cw}|{t}|{read}|{fold}"] = {"data": data, "layout": lay}
    sel = [("m", "model", [(f"{m}:{c}", f"{m} ({c})") for m, c in MODELS]), ("t", "decision time", [(t, S.TIME_LABEL[t]) for t in S.TIMES]),
           ("r", "read", [("primary", "primary"), ("secondary", "secondary")]), ("f", "fold", [("sum", "3 folds summed"), ("1", "fold 1"), ("2", "fold 2"), ("3", "fold 3")])]
    page("t4", "confusion.html", "Confusion tables", "Cell text: count and row share. Rows = true type with n.", sel, figs)


# ====================================================================== forward returns
def forward_returns() -> None:
    fw = pd.read_parquet(S.art("t6_forward.parquet"))
    qx = np.linspace(0, 100, 21).tolist()
    figs = {}
    HOR = [("h10", "+10 min"), ("h30", "+30 min"), ("h60", "+60 min"), ("to2000", "to 20:00")]
    LAT = [("lat0", "next print after d (zero latency, upper bound)"), ("lat1s", "first print >= d + 1 s"), ("lat5s", "first print >= d + 5 s")]
    for mdl, cw in MODELS[1:]:
        for t in S.TIMES:
            ft = fw[(fw["time"] == t)]
            top0 = ft[(ft["model"] == mdl) & (ft["cw"] == cw) & (ft["set"] == "top_decile")]
            if top0.empty:
                continue
            for h, _ in HOR:
                for ln, _ in LAT:
                    for unit in ("bp", "cents"):
                        al = ft[(ft["set"] == "all") & (ft["horizon"] == h) & (ft["latency"] == ln) & (ft["unit"] == unit)].iloc[0]
                        data, titles = [], []
                        for i, ty in enumerate(S.TYPES):
                            xa, ya = ax(i)
                            tp = top0[(top0["type"] == ty) & (top0["horizon"] == h) & (top0["latency"] == ln) & (top0["unit"] == unit)]
                            for lab, row, col in (("all primary test events", al, PAL["all"]), ("top decile for this type", tp.iloc[0] if len(tp) else None, PAL["top"])):
                                if row is None or row["q"] is None:
                                    continue
                                data.append({"type": "scatter", "mode": "lines", "x": qx, "y": list(row["q"]), "name": lab, "legendgroup": lab, "showlegend": i == 0,
                                             "line": {"color": col, "width": 2}, "xaxis": xa, "yaxis": ya,
                                             "hovertemplate": f"{lab}: %{{x:.0f}}th pct = %{{y:.1f}} {unit}<br>n_ok {int(row['n_ok'])} of {int(row['n_rows'])}; median {row['median']:.1f}; mean {row['mean']:.1f}<extra></extra>"})
                            data.append({"type": "scatter", "mode": "lines", "x": [0, 100], "y": [0, 0], "line": {"color": "#555", "dash": "dot", "width": 1},
                                         "showlegend": False, "hoverinfo": "skip", "xaxis": xa, "yaxis": ya})
                            r = tp.iloc[0] if len(tp) else None
                            titles.append(f"{S.TYPE_LABEL[ty]} -- top n_ok={int(r['n_ok']) if r is not None else 0} (med {r['median']:.0f}) vs all n_ok={int(al['n_ok'])} (med {al['median']:.0f})"
                                          if r is not None and r["n_ok"] else f"{S.TYPE_LABEL[ty]} -- no top-decile rows")
                        lay = grid_layout(2, 3, titles, h=860, xtitle="quantile (%)", ytitle=f"net return ({unit})")
                        lay["title"] = {"text": f"Forward return from {S.TIME_LABEL[t]}, {dict(HOR)[h]}, {dict(LAT)[ln]} -- {mdl} ({cw}) top decile vs all; net of "
                                                f"{'70.98 bp' if unit == 'bp' else '2.512 c/share'}; long only; primary test events, 3 folds pooled", "x": 0.01, "font": {"size": 13}}
                        figs[f"{mdl}:{cw}|{t}|{h}|{ln}|{unit}"] = {"data": data, "layout": lay}
    sel = [("m", "model", [(f"{m}:{c}", f"{m} ({c})") for m, c in MODELS[1:]]), ("t", "decision time", [(t, S.TIME_LABEL[t]) for t in S.TIMES]),
           ("h", "horizon", HOR), ("l", "entry", LAT), ("u", "unit", [("bp", "bp (net 70.98)"), ("cents", "cents/share (net 2.512)")])]
    page("t6", "forward_returns.html", "Forward returns: top predicted decile vs all", "Each curve is the quantile function (21 points, min to max, nothing clipped) of the net return. "
         "n_ok excludes rows with no entry print before 20:00, a horizon past 20:00, or no print inside the horizon (counts in the T6 artifact).", sel, figs)


# ====================================================================== importance
def importance() -> None:
    imp = pd.read_parquet(S.art("t7_importance.parquet"))
    figs = {}
    for t in S.TIMES:
        it = imp[imp["time"] == t]
        for fold in ("mean", "1", "2", "3"):
            g0 = it if fold == "mean" else it[it["fold"] == int(fold)]
            data, titles = [], []
            for i, ty in enumerate(S.TYPES):
                xa, ya = ax(i)
                g = g0[g0["type"] == ty].groupby("input").agg(share=("share", "mean"), drop=("mean_drop", "mean"), base=("base_auc", "mean"), nt=("n_type", "sum")).reset_index()
                g = g.sort_values("share", ascending=False).head(12).iloc[::-1]
                data.append({"type": "bar", "orientation": "h", "x": g["share"].tolist(), "y": g["input"].tolist(), "marker": {"color": ["#ff6b6b" if s > 0.5 else "#4ea1ff" for s in g["share"]]},
                             "showlegend": False, "xaxis": xa, "yaxis": ya, "hovertext": [f"{n}: share {s:.2f}, mean AUC drop {d:.4f}" for n, s, d in zip(g["input"], g["share"], g["drop"])],
                             "hoverinfo": "text"})
                data.append({"type": "scatter", "mode": "lines", "x": [0.5, 0.5], "y": [g["input"].iloc[0], g["input"].iloc[-1]] if len(g) else [0, 1],
                             "line": {"color": "#ffb347", "dash": "dot"}, "showlegend": False, "hoverinfo": "skip", "xaxis": xa, "yaxis": ya})
                nt = int(g0[g0["type"] == ty].drop_duplicates(["fold"])["n_type"].sum())
                base = g0[g0["type"] == ty].drop_duplicates(["fold"])["base_auc"].mean()
                titles.append(f"{S.TYPE_LABEL[ty]} -- M3 AUC {base:.3f}, n_type={nt}")
            lay = grid_layout(2, 3, titles, h=900, xtitle="share of the type's importance")
            for k in lay:
                if k.startswith("yaxis"):
                    lay[k]["tickfont"] = {"size": 9}
            lay["title"] = {"text": f"Permutation importance (M3, none), {S.TIME_LABEL[t]}, primary read, {'mean of 3 folds' if fold == 'mean' else 'fold ' + fold} -- top 12 inputs; "
                                    "dotted line = row 4 (0.5)", "x": 0.01}
            figs[f"{t}|{fold}"] = {"data": data, "layout": lay}
    sel = [("t", "decision time", [(t, S.TIME_LABEL[t]) for t in S.TIMES]), ("f", "fold", [("mean", "mean of 3 folds"), ("1", "fold 1"), ("2", "fold 2"), ("3", "fold 3")])]
    page("t7", "importance.html", "Permutation importance", "Share = the input's mean AUC drop over 5 permutations / the sum of the positive mean drops for that type. Red bars exceed 0.5 (row 4).", sel, figs)


# ====================================================================== controls
def controls() -> None:
    gate = pd.read_parquet(S.art("t5_negative_gate.parquet"))
    pos = pd.read_parquet(S.art("t5_positive.parquet"))
    figs = {}
    for mdl, cw in MODELS[1:]:
        g0 = gate[(gate["model"] == mdl) & (gate["cw"] == cw)]
        if g0.empty:
            continue
        data, titles = [], []
        for i, ty in enumerate(S.TYPES):
            xa, ya = ax(i)
            g = g0[g0["type"] == ty].set_index("time").reindex(S.TIMES)
            data.append({"type": "scatter", "mode": "markers", "x": TL, "y": g["mean_auc"].tolist(), "name": "mean of 3 folds x 10 shuffles (row 2 reads this)",
                         "legendgroup": "m", "showlegend": i == 0, "marker": {"color": PAL[mdl], "size": 8},
                         "error_y": {"type": "data", "symmetric": False, "array": (g["max_auc"] - g["mean_auc"]).tolist(), "arrayminus": (g["mean_auc"] - g["min_auc"]).tolist(),
                                     "color": "#777", "thickness": 1},
                         "text": [f"mean {m:.3f}; single-shuffle range {lo:.3f}-{hi:.3f}; draws {int(n)}; single draws outside band {int(o)}" if np.isfinite(m) else ""
                                  for m, lo, hi, n, o in zip(g["mean_auc"], g["min_auc"], g["max_auc"], g["draws"].fillna(0), g["single_outside"].fillna(0))],
                         "hoverinfo": "text", "xaxis": xa, "yaxis": ya})
            for yv in (0.45, 0.55):
                data.append({"type": "scatter", "mode": "lines", "x": [TL[0], TL[-1]], "y": [yv, yv], "line": {"color": "#ffb347", "dash": "dot", "width": 1},
                             "showlegend": False, "hoverinfo": "skip", "xaxis": xa, "yaxis": ya})
            titles.append(f"{S.TYPE_LABEL[ty]} -- negative control")
        lay = grid_layout(2, 3, titles, xtitle="decision time", ytitle="AUC, labels shuffled")
        lay["title"] = {"text": f"Negative control -- {mdl} ({cw}); dots = mean of 30 per-fold primary AUCs; bars = single-shuffle range; band = row 2", "x": 0.01}
        figs[f"neg|{mdl}:{cw}"] = {"data": data, "layout": lay}
    for leak in ("rules", "terminal_log"):
        for mdl, cw in [m for m in MODELS if m[0] in ("M2", "M3")]:
            g0 = pos[(pos["leak"] == leak) & (pos["model"] == mdl) & (pos["cw"] == cw)]
            data, titles = [], []
            for i, ty in enumerate(S.TYPES):
                xa, ya = ax(i)
                for f in S.FOLDS:
                    g = g0[(g0["type"] == ty) & (g0["fold"] == f)].set_index("time").reindex(S.TIMES)
                    data.append({"type": "scatter", "mode": "lines+markers", "x": TL, "y": g["auc"].tolist(), "name": f"fold {f}", "legendgroup": f"f{f}", "showlegend": i == 0,
                                 "line": {"color": ["#4ea1ff", "#7ed957", "#ff6b6b"][f - 1]}, "xaxis": xa, "yaxis": ya,
                                 "text": [f"AUC {a:.4f}; n {int(n)}, n_type {int(nt)}" if np.isfinite(a) else "" for a, n, nt in zip(g["auc"], g["n"].fillna(0), g["n_type"].fillna(0))],
                                 "hoverinfo": "text+name"})
                if leak == "rules":
                    data.append({"type": "scatter", "mode": "lines", "x": [TL[0], TL[-1]], "y": [0.95, 0.95], "line": {"color": "#ffb347", "dash": "dot"},
                                 "showlegend": False, "hoverinfo": "skip", "xaxis": xa, "yaxis": ya})
                titles.append(f"{S.TYPE_LABEL[ty]} -- min AUC {g0[g0['type'] == ty]['auc'].min():.3f}")
            lay = grid_layout(2, 3, titles, xtitle="decision time", ytitle="AUC with the leak added")
            lab = "rule inputs (rise_pct, fall_pct, u_peak) -- gated by row 3 at 0.95" if leak == "rules" else "terminal_log (the brief's construction) -- reported, ungated"
            lay["title"] = {"text": f"Positive control, {lab} -- {mdl} ({cw}), primary read", "x": 0.01}
            figs[f"pos_{leak}|{mdl}:{cw}"] = {"data": data, "layout": lay}
    opts_ctrl = [("neg", "negative (labels shuffled)"), ("pos_rules", "positive: rule inputs (gated)"), ("pos_terminal_log", "positive: terminal_log (ungated)")]
    sel = [("c", "control", opts_ctrl), ("m", "model", [(f"{m}:{c}", f"{m} ({c})") for m, c in MODELS[1:]])]
    page("t5", "controls.html", "Controls", "Negative: 10 label shuffles per fold at the real run's settings (Cooper R5). Positive: M2 and M3 only (M1 and M4 take no input list) (Cooper R4). "
         "M1 has no positive control; M4 appears under the negative control only.", sel, figs)


def main() -> int:
    by_time("auc")
    by_time("lift")
    calibration()
    confusion()
    forward_returns()
    importance()
    controls()
    for t, n in (("t4", "auc_by_time.html"), ("t4", "lift_by_time.html"), ("t4", "calibration.html"), ("t4", "confusion.html"),
                 ("t6", "forward_returns.html"), ("t7", "importance.html"), ("t5", "controls.html")):
        p = S.chart_path(t, n)
        print(f"{t}/{n}: {os.path.getsize(p) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
