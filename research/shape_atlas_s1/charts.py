"""
Shape atlas S1 -- the six charts (section 7). Exploratory, hindsight used by design; nothing here is a
tested result. Dark theme, Plotly inlined (D14), one file per chart with selectors, n on every panel.

  atlas.html            pick a view, typing, k and type -> centroid with IQR band and null centroid,
                        24-path gallery, money distributions, every descriptor's distribution vs all
                        events (a page built on the inlined plotly.js, since four linked selectors are
                        beyond Plotly's own dropdowns)
  null_comparison.html  FPC spectra, BIC improvement and silhouette across k, real vs null, per view
  stability.html        matched-centroid correlations across the two periods (as written and
                        ticker-blocked), type-share agreement, co-assignment distributions
  theory_types.html     theory-type shares, real vs null, by facet and rung
  transitions.html      run-up type -> post-tau type, row shares with counts
  joint_peak_rise.html  u_peak x rise_s density, real vs each event's own null, and the difference

Usage: .venv/Scripts/python.exe research/shape_atlas_s1/charts.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1common as S  # noqa: E402

BG, FG, GRID = "#111418", "#e6e6e6", "#2a2f36"
PAL = ["#4ea1ff", "#ffb347", "#7ed957", "#ff6b6b", "#c792ea", "#9aa4b2", "#f78fb3", "#63e6be", "#ffd43b", "#a5d8ff"]
HDR = "exploratory, hindsight used by design; nothing here is a tested result"
VIEWS = ("post", "whole_day", "runup")


def lay(fig, title, h=700):
    fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, height=h, font=dict(color=FG, size=12),
                      title=dict(text=title, x=0.01), legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=60, r=30, t=120, b=60))
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def selector(fig, views):
    """views: [(label, [trace indices], title)]."""
    n = len(fig.data)
    fig.update_layout(updatemenus=[dict(buttons=[dict(label=lab, method="update",
                                                      args=[{"visible": [i in set(ix) for i in range(n)]}, {"title.text": t}])
                                                 for lab, ix, t in views],
                                        direction="down", x=1.0, xanchor="right", y=1.12, yanchor="top", bgcolor="#1d2229", font=dict(color=FG))])
    first = set(views[0][1])
    for i in range(n):
        fig.data[i].visible = i in first
    fig.update_layout(title=dict(text=views[0][2]))


def save(fig, name):
    fig.write_html(S.chart_path(name), include_plotlyjs=True)


# ====================================================================== null comparison
def null_comparison():
    fig = make_subplots(rows=2, cols=2, subplot_titles=("FPC variance share (first 20)", "GMM BIC improvement over k = 1",
                                                        "silhouette (paths, 5,000 sampled)", "adjusted Rand, GMM vs k-means"))
    views = []
    for v in VIEWS:
        a = len(fig.data)
        sp = pd.read_parquet(S.art(f"t3_{v}_spectrum.parquet"))
        st = pd.read_parquet(S.art(f"t3_{v}_stats.parquet"))
        n = int(st[st["dataset"] == "real"]["n"].iloc[0])
        for ds, g in sp.groupby("dataset"):
            real = ds == "real"
            fig.add_trace(go.Scatter(x=g["component"], y=g["var_share"], mode="lines+markers" if real else "lines",
                                     line=dict(color=PAL[0] if real else PAL[5], width=3 if real else 1), name=f"{ds} spectrum",
                                     showlegend=real or ds == "null0"), row=1, col=1)
        for ds, g in st.groupby("dataset"):
            real = ds == "real"
            col = dict(color=PAL[1] if real else PAL[5], width=3 if real else 1)
            fig.add_trace(go.Scatter(x=g["k"], y=g["gmm_bic_improvement"], mode="lines+markers", line=col, name=f"{ds} BIC gain",
                                     showlegend=real or ds == "null0"), row=1, col=2)
            fig.add_trace(go.Scatter(x=g["k"], y=g["gmm_silhouette"], mode="lines+markers", line=dict(color=PAL[2] if real else PAL[5], width=col["width"]),
                                     name=f"{ds} GMM silhouette", showlegend=real or ds == "null0"), row=2, col=1)
            fig.add_trace(go.Scatter(x=g["k"], y=g["kmeans_silhouette"], mode="lines+markers",
                                     line=dict(color=PAL[3] if real else PAL[5], width=col["width"], dash="dot"),
                                     name=f"{ds} k-means silhouette", showlegend=real or ds == "null0"), row=2, col=1)
            fig.add_trace(go.Scatter(x=g["k"], y=g["ari_gmm_kmeans"], mode="lines+markers", line=dict(color=PAL[4] if real else PAL[5], width=col["width"]),
                                     name=f"{ds} ARI", showlegend=real or ds == "null0"), row=2, col=2)
        views.append((v, list(range(a, len(fig.data))),
                      f"S1 null comparison -- {v} view, n = {n:,} events; thick = real, thin grey = each of 5 null replicates (one own-return "
                      f"draw per event)<br><sup>{HDR}. Structure exists only where the real curve sits beyond every null replicate.</sup>"))
    selector(fig, views)
    lay(fig, views[0][2], h=820)
    save(fig, "null_comparison.html")


# ====================================================================== stability
def stability():
    fig = make_subplots(rows=2, cols=2, subplot_titles=("matched centroid correlation by k (each cluster a dot)",
                                                        "assigned share vs refit share (each cluster a dot)",
                                                        "adjusted Rand, assigned vs refit labels", "co-assignment rate (50 ticker bootstraps)"))
    views = []
    for v in VIEWS:
        a = len(fig.data)
        s = pd.read_parquet(S.art(f"t3_{v}_stability.parquet"))
        co = pd.read_parquet(S.art(f"t3_{v}_coassign.parquet"))
        i = 0
        for (method, variant, direction), g in s.groupby(["method", "variant", "direction"]):
            name = f"{method} · {variant} · {direction}"
            off = {"A->B": -0.15, "B->A": 0.15}[direction] + (0.05 if variant == "ticker_blocked" else 0)
            fig.add_trace(go.Scatter(x=g["k"] + off, y=g["centroid_corr"], mode="markers", marker=dict(color=PAL[i % 10], size=6,
                                     symbol="circle" if method == "gmm" else "diamond"), name=name,
                                     customdata=np.c_[g["n_fit"], g["n_other"]],
                                     hovertemplate="k=%{x:.0f}: corr %{y:.3f} (n fit %{customdata[0]:,}, n other %{customdata[1]:,})<extra></extra>"),
                          row=1, col=1)
            fig.add_trace(go.Scatter(x=g["share_refit_matched"], y=g["share_assigned"], mode="markers", marker=dict(color=PAL[i % 10], size=5),
                                     name=name, showlegend=False), row=1, col=2)
            ar = g.drop_duplicates("k")
            fig.add_trace(go.Scatter(x=ar["k"], y=ar["ari_assigned_vs_refit"], mode="lines+markers", line=dict(color=PAL[i % 10]), name=name,
                                     showlegend=False), row=2, col=1)
            i += 1
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=GRID, dash="dash"), showlegend=False), row=1, col=2)
        for j, (method, g) in enumerate(co.groupby("method")):
            q = g.groupby("k")["co_assignment_rate"].quantile([0.0, 0.25, 0.5, 0.75, 1.0]).unstack()      # whiskers at min and max
            fig.add_trace(go.Box(x=[str(k) for k in q.index], q1=q[0.25], median=q[0.5], q3=q[0.75], lowerfence=q[0.0], upperfence=q[1.0],
                                 name=f"{method} co-assignment (n={g['event_id'].nunique():,} events per k; whiskers min-max)",
                                 marker_color=PAL[j], offsetgroup=method), row=2, col=2)
        fig.add_hline(y=0.9, line=dict(color=PAL[3], dash="dash"), row=1, col=1)
        views.append((v, list(range(a, len(fig.data))),
                      f"S1 stability -- {v} view: fit on 2020-22 vs 2023-24, both directions, tickers repeating and ticker-blocked; "
                      f"50 ticker bootstraps<br><sup>{HDR}. Dashed line at 0.9 = the atlas's 'reproduces' cut.</sup>"))
    fig.update_layout(boxmode="group")
    selector(fig, views)
    lay(fig, views[0][2], h=860)
    save(fig, "stability.html")


# ====================================================================== theory types
def theory_types():
    sh = pd.read_parquet(S.art("t2_theory_shares.parquet"))
    fig = go.Figure()
    views = []
    for (N, facet, level), g in sh.groupby(["N", "facet", "level"], sort=False):
        a = len(fig.data)
        g = g.set_index("type").loc[S.TYPES]
        n = int(g["n_events"].iloc[0])
        fig.add_trace(go.Bar(x=S.TYPES, y=g["real_share"], name=f"real (n={n:,})", marker_color=PAL[0],
                             text=[f"{s:.1%} (n={int(c):,})" for s, c in zip(g["real_share"], g["n_type"])], textposition="outside"))
        fig.add_trace(go.Bar(x=S.TYPES, y=g["null_share"], name="each event's own null (200 draws)", marker_color=PAL[5],
                             text=[f"{s:.1%}" for s in g["null_share"]], textposition="outside"))
        views.append((f"N={N} · {facet}: {level}", [a, a + 1],
                      f"S1 theory types, N = {N}, {facet} = {level}, n = {n:,} typed events: real share vs the share noise alone "
                      f"produces<br><sup>{HDR}. Rules declared in section 3, first match wins, on the event's own null percentiles.</sup>"))
    fig.update_layout(barmode="group")
    selector(fig, views)
    lay(fig, views[0][2], h=640)
    fig.update_yaxes(title="share of typed events", tickformat=".0%")
    save(fig, "theory_types.html")


# ====================================================================== transitions
def transitions():
    tr = pd.read_parquet(S.art("t4_transitions.parquet"))
    fig = go.Figure()
    views = []
    keys = ["runup_typing", "runup_k", "post_typing", "post_k", "segment"]
    for key, g in tr.groupby(keys, dropna=False, sort=False):
        rt, rk, pt, pk, seg = key
        piv = g.pivot(index="runup_type", columns="post_type", values="row_share").fillna(0)
        cnt = g.pivot(index="runup_type", columns="post_type", values="n").fillna(0).astype(int)
        rown = g.drop_duplicates("runup_type").set_index("runup_type")["row_n"].reindex(piv.index)
        a = len(fig.data)
        fig.add_trace(go.Heatmap(z=piv.values, x=list(piv.columns), y=[f"{r} (n={int(n):,})" for r, n in zip(piv.index, rown)],
                                 text=[[f"{v:.0%}<br>{c:,}" for v, c in zip(rv, rc)] for rv, rc in zip(piv.values, cnt.values)],
                                 texttemplate="%{text}", colorscale="Blues", zmin=0, zmax=1, colorbar=dict(title="row share")))
        lab = f"{rt}{'' if pd.isna(rk) else int(rk)} -> {pt}{'' if pd.isna(pk) else int(pk)} · {seg}"
        views.append((lab, [a], f"S1 transitions -- run-up type ({rt}{'' if pd.isna(rk) else ', k=' + str(int(rk))}) -> post-tau type "
                                f"({pt}{'' if pd.isna(pk) else ', k=' + str(int(pk))}), segment {seg}: row shares with counts<br><sup>{HDR}</sup>"))
    selector(fig, views)
    lay(fig, views[0][2], h=700)
    save(fig, "transitions.html")


# ====================================================================== joint peak x rise
def joint_peak_rise():
    ev = pd.read_parquet(S.art("s1_events.parquet"))
    nh = pd.read_parquet(S.art("s1_null_joint_hist.parquet"))
    cfg = S.load_cfg()
    U = np.linspace(0, 1, 21)
    RE = np.array([float(x) for x in cfg["joint_peak_rise"]["rise_s_edges"][:-1]] + [np.inf])
    rl = [f"{RE[j]:g}-{RE[j + 1]:g}" if np.isfinite(RE[j + 1]) else f">={RE[j]:g}" for j in range(len(RE) - 1)]
    ul = [f"{U[i]:.2f}" for i in range(20)]
    fig = make_subplots(rows=1, cols=3, subplot_titles=("real events", "each event's own null (200 draws, events weighted equally)",
                                                        "real minus null"), shared_yaxes=True)
    views = []
    for N in (50, 100, 200):
        for y in [str(v) for v in sorted(ev["year"].unique())] + ["all"]:
            g = ev[ev[f"post{N}_null_ok"].fillna(False).astype(bool)]
            if y != "all":
                g = g[g["year"].astype(str) == y]
            h, _, _ = np.histogram2d(g[f"post{N}_u_peak"], np.clip(g[f"post{N}_rise_s"], 0, None), bins=[U, RE])
            real = h / max(1, len(g))
            nn = nh[(nh["N"] == N) & (nh["year"] == y)].sort_values(["u_lo", "r_lo"])
            null = nn["null_events_weight"].to_numpy().reshape(20, len(RE) - 1) / max(1, int(nn["events"].iloc[0]))
            a = len(fig.data)
            for c, z, cs in ((1, real, "Blues"), (2, null, "Blues"), (3, real - null, "RdBu")):
                fig.add_trace(go.Heatmap(z=z.T, x=ul, y=rl, colorscale=cs, zmid=0 if c == 3 else None, showscale=c == 3,
                                         text=np.round(z.T * 100, 2), hovertemplate="u_peak %{x}, rise_s %{y}: %{text}%<extra></extra>"),
                              row=1, col=c)
            views.append((f"N={N} · {y}", list(range(a, len(fig.data))),
                          f"S1 joint peak position x rise size, N = {N}, {y}, n = {len(g):,} events: share of events per cell<br>"
                          f"<sup>{HDR}. The picture that started this brief; absolute bins declared in config.</sup>"))
    selector(fig, views)
    lay(fig, views[0][2], h=640)
    fig.update_xaxes(title="u_peak (0.05 bins)")
    fig.update_yaxes(title="rise_s", row=1, col=1)
    save(fig, "joint_peak_rise.html")


# ====================================================================== atlas (page on the inlined plotly.js)
ATLAS_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>Shape atlas S1</title>
<style>
:root{--bg:#111418;--fg:#e6e6e6;--mut:#9aa4b2;--grid:#2a2f36;--card:#171b21}
body{background:var(--bg);color:var(--fg);font:13px/1.4 system-ui,Segoe UI,sans-serif;margin:0 16px 40px}
h1{font-size:18px;margin:14px 0 2px} .sub{color:var(--mut);margin-bottom:10px}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--grid)}
select{background:#1d2229;color:var(--fg);border:1px solid var(--grid);padding:4px 6px;border-radius:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px}
.card{background:var(--card);border:1px solid var(--grid);border-radius:6px;padding:4px}
table{border-collapse:collapse;width:100%;font-size:12px} td,th{border-bottom:1px solid var(--grid);padding:3px 6px;text-align:right}
th:first-child,td:first-child{text-align:left} h2{font-size:15px;margin:18px 0 6px}
</style></head><body>
<h1>Shape atlas S1</h1><div class="sub">__HDR__ · config __HASH__ · n shown on every panel</div>
<div class="bar"><label>view <select id="v"></select></label><label>typing <select id="t"></select></label>
<label>k <select id="k"></select></label><label>type <select id="y"></select></label><span id="n" class="sub"></span></div>
<h2>Centroid path (resampled, sigma_path units) with pointwise IQR band and the null centroid</h2><div id="cen" style="height:380px"></div>
<h2>Gallery: 12 nearest the centroid, 12 at random (actual N = 100 bucketed path, bp from the view's start)</h2><div id="gal" style="height:900px"></div>
<h2>Vector and money (post-tau, N = 100)</h2><div id="money"></div>
<h2>Everything else: this type (colour) vs all events (grey), quantile functions or level shares, with n</h2><div id="desc" class="grid"></div>
<script>__PLOTLY__</script>
<script>
const D = __DATA__;
const L = {paper_bgcolor:'#111418',plot_bgcolor:'#111418',font:{color:'#e6e6e6',size:11},margin:{l:45,r:10,t:28,b:30}};
const AX = {gridcolor:'#2a2f36',zeroline:false};
const $ = id => document.getElementById(id);
const by = {}; D.entries.forEach(e => { const key = [e.view,e.typing,e.k===null?'':e.k].join('|'); (by[key] = by[key] || []).push(e); });
function opts(el, vals, keep){ const cur = el.value; el.innerHTML = vals.map(v=>`<option value="${v}">${v}</option>`).join(''); if(keep && vals.includes(cur)) el.value = cur; }
function refresh(level){
  const views = [...new Set(D.entries.map(e=>e.view))]; if(level<=0) opts($('v'), views, true);
  const v = $('v').value; const typings = [...new Set(D.entries.filter(e=>e.view===v).map(e=>e.typing))];
  if(level<=1) opts($('t'), typings, true); const t = $('t').value;
  const ks = [...new Set(D.entries.filter(e=>e.view===v && e.typing===t).map(e=>e.k===null?'':e.k))];
  if(level<=2) opts($('k'), ks, true); $('k').disabled = ks.length===1 && ks[0]==='';
  const k = $('k').value; const es = by[[v,t,k].join('|')] || [];
  if(level<=3) opts($('y'), es.map(e=>e.type), true);
  const e = es.find(x=>x.type===$('y').value); if(e) draw(e);
}
function q(o){ return o && o.q && o.q.length ? o.q : null; }
function draw(e){
  $('n').textContent = `n = ${e.n.toLocaleString()} events (${e.n_with_path.toLocaleString()} with a path in this view)`;
  const u = [...Array(D.G).keys()].map(g=>(g+1)/D.G);
  if(e.centroid){
    Plotly.react('cen', [
      {x:u,y:e.centroid.p75,mode:'lines',line:{width:0},showlegend:false,hoverinfo:'skip'},
      {x:u,y:e.centroid.p25,mode:'lines',line:{width:0},fill:'tonexty',fillcolor:'rgba(78,161,255,0.25)',name:'IQR of members'},
      {x:u,y:e.centroid.mean,mode:'lines',line:{color:'#4ea1ff',width:3},name:`mean path (n=${e.n_with_path})`},
      {x:u,y:e.centroid.null,mode:'lines',line:{color:'#e6e6e6',dash:'dot'},name:'null centroid (members, null draw 0)'}],
      {...L,xaxis:{...AX,title:'u (volume clock of the view)'},yaxis:{...AX,title:'height / sigma_path'},legend:{orientation:'h'}});
  } else Plotly.purge('cen');
  const G = e.gallery || []; const tr = []; const lay = {...L,showlegend:false,annotations:[]}; const cols = 6, rows = 4;
  G.forEach((g,i)=>{ const r = Math.floor(i/cols), c = i%cols; const ax = i===0?'':String(i+1);
    const x0 = c/cols+0.01, x1 = (c+1)/cols-0.01, y1 = 1-r/rows-0.04, y0 = 1-(r+1)/rows+0.03;
    lay['xaxis'+ax] = {...AX,domain:[x0,x1],anchor:'y'+ax,showticklabels:false};
    lay['yaxis'+ax] = {...AX,domain:[y0,y1],anchor:'x'+ax,tickfont:{size:9}};
    const xs = g.y_bp.map((_,j)=>j/(g.y_bp.length-1));
    tr.push({x:xs,y:g.y_bp,xaxis:'x'+ax,yaxis:'y'+ax,mode:'lines',line:{color:g.kind==='nearest'?'#4ea1ff':'#ffb347',width:1.2}});
    const ip = Math.round(g.u_peak*(g.y_bp.length-1));
    tr.push({x:[g.u_peak],y:[g.y_bp[ip]],xaxis:'x'+ax,yaxis:'y'+ax,mode:'markers',marker:{symbol:'triangle-up',size:8,color:'#7ed957'}});
    tr.push({x:[1],y:[g.y_bp[g.y_bp.length-1]],xaxis:'x'+ax,yaxis:'y'+ax,mode:'markers',marker:{symbol:'square',size:6,color:'#e6e6e6'}});
    tr.push({x:[g.tau_u,g.tau_u],y:[Math.min(...g.y_bp),Math.max(...g.y_bp)],xaxis:'x'+ax,yaxis:'y'+ax,mode:'lines',line:{color:'#ff6b6b',dash:'dot',width:1}});
    lay.annotations.push({text:`${g.ticker} ${g.date} (${g.kind})`,x:(x0+x1)/2,y:y1+0.005,xref:'paper',yref:'paper',showarrow:false,font:{size:10,color:'#9aa4b2'}});
  });
  if(G.length) Plotly.react('gal', tr, lay); else Plotly.purge('gal');
  const QI = [2,10,20,30,38];
  let h = '<table><tr><th>quantity</th><th>n</th><th>p5</th><th>p25</th><th>median</th><th>p75</th><th>p95</th><th>all events: median (n)</th></tr>';
  D.money.forEach(m=>{ const o = q(e.money[m]); const a = q(D.all_events[m]);
    h += `<tr><td>${m}</td><td>${e.money[m].n.toLocaleString()}</td>` + QI.map(i=>`<td>${o?o[i].toPrecision(4):'—'}</td>`).join('') +
         `<td>${a?a[20].toPrecision(4):'—'} (${D.all_events[m].n.toLocaleString()})</td></tr>`; });
  $('money').innerHTML = h + '</table>';
  const box = $('desc'); box.innerHTML = '';
  Object.entries(D.groups).forEach(([grp, cols])=>cols.forEach(c=>{
    const div = document.createElement('div'); div.className='card'; div.style.height='210px'; box.appendChild(div);
    const o = e.desc[c], a = D.all_events[c];
    const tr2 = [];
    if(q(a)) tr2.push({x:D.quantiles,y:a.q,mode:'lines',line:{color:'#9aa4b2'},name:`all (n=${a.n})`});
    if(q(o)) tr2.push({x:D.quantiles,y:o.q,mode:'lines',line:{color:'#4ea1ff',width:2},name:`type (n=${o.n})`});
    Plotly.newPlot(div, tr2, {...L,title:{text:`${grp}: ${c} (n=${o.n.toLocaleString()})`,font:{size:11}},showlegend:false,
      xaxis:{...AX,title:'quantile'},yaxis:{...AX,type:(q(a)&&Math.min(...a.q)>0&&Math.max(...a.q)/Math.min(...a.q)>100)?'log':'linear'}},{displayModeBar:false});
  }));
  Object.entries(D.cat_groups).forEach(([grp, cols])=>cols.forEach(c=>{
    const div = document.createElement('div'); div.className='card'; div.style.height='210px'; box.appendChild(div);
    const o = e.cat[c], a = D.all_events[c];
    const levs = Object.keys(a.levels).slice(0,12);
    Plotly.newPlot(div, [
      {x:levs,y:levs.map(l=>(a.levels[l]||0)/a.n),type:'bar',marker:{color:'#9aa4b2'},name:'all'},
      {x:levs,y:levs.map(l=>(o.levels[l]||0)/Math.max(1,o.n)),type:'bar',marker:{color:'#4ea1ff'},name:'type'}],
      {...L,title:{text:`${grp}: ${c} (n=${o.n.toLocaleString()})`,font:{size:11}},showlegend:false,barmode:'group',
       xaxis:{...AX,tickfont:{size:8}},yaxis:{...AX,tickformat:'.0%'}},{displayModeBar:false});
  }));
}
['v','t','k','y'].forEach((id,i)=>$(id).addEventListener('change',()=>refresh(i+1)));
refresh(0);
</script></body></html>"""


def atlas():
    data = S.art("t5_atlas.json").read_text(encoding="utf-8")
    js = (S.REPO / ".venv/Lib/site-packages/plotly/package_data/plotly.min.js").read_text(encoding="utf-8")
    html = ATLAS_HTML.replace("__HDR__", HDR).replace("__HASH__", S.cfg_hash()).replace("__DATA__", data)
    html = html.replace("<script>__PLOTLY__</script>", "<script>" + js + "</script>")           # last: the bundle is never searched
    S.chart_path("atlas.html").write_text(html, encoding="utf-8")


def main() -> int:
    which = sys.argv[1:] or ["null_comparison", "stability", "theory_types", "transitions", "joint_peak_rise", "atlas"]
    for w in which:
        globals()[w]()
        print(w, "written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
