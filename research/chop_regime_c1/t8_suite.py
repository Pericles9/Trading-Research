"""
Chop regime C1, T8 -- the tuning suite: one self-contained HTML page (plotly.js inlined, D14), the per-moment table and
the gallery strips embedded as typed arrays (suitedata), filtering in the browser. Brief section 7 with Amendment 1.

The page filters a table the pipeline measured. The only arithmetic it does on embedded values: the filter itself; the
chop label (MFE < c x the round trip at t); net = gross - the round trip at t; cents = bp x entry price / 100; cost_noise at
the other rungs of each ladder = the embedded rung x sqrt(h0 / h) (asserted exact in suite_table); weighted counts, shares,
ECDFs and medians; the noise band and the ticker bootstrap (on a button press). Nothing optimises, ranks or suggests a
threshold; slider ranges run from the embedded minimum to the maximum; every default filters nothing.

Build-time assertions (brief section 12; escalation rows 8 and 9): every row in the development slice; no A12 column; no
hindsight column among the conditions or the override; no percentile or rank column; the row count equals the embedded
sample; the decoded arrays equal the encoded ones; the file within the size budget.

Writes results/chop_regime/c1/suite/chop_suite.html and artifacts/t8_summary.json.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t8_suite.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402
import suite_table as ST  # noqa: E402
import suitedata as SD  # noqa: E402

CFG = C.load_cfg()
STACK = {"bp": 70.98, "c": 2.512}

CONDS = [
    {"key": "c_trade_rate", "label": "trade_rate", "unit": "collapsed trades / min, finest rate rung", "group": "presence", "dir": "<", "log": True},
    {"key": "c_dollar_flow", "label": "dollar_flow", "unit": "$ / min, finest rate rung", "group": "presence", "dir": "<", "log": True},
    {"key": "c_spread_bp", "label": "spread_bp_t", "unit": "bp of the midpoint, at t", "group": "presence", "dir": ">", "log": True, "ref": STACK["bp"], "ref_label": "Phase 11 stack 70.98 bp"},
    {"key": "c_spread_c", "label": "spread_c_t", "unit": "cents, at t", "group": "presence", "dir": ">", "log": True, "ref": STACK["c"], "ref_label": "Phase 11 stack 2.512 ¢"},
    {"key": "c_quote_age", "label": "quote_age_s", "unit": "s since the best bid / offer changed", "group": "presence", "dir": ">", "log": True},
    {"key": "c_depth_ask", "label": "depth_ask_usd", "unit": "$ displayed at the ask (presence, not capacity)", "group": "presence", "dir": "<", "log": True},
    {"key": "cost_noise", "label": "cost_noise_h", "unit": "round trip at t / own noise over h (pick h)", "group": "presence", "dir": ">", "log": True, "ref": 1.0, "ref_label": "1: one round trip = one typical move"},
    {"key": "c_turnover_rate", "label": "turnover_rate", "unit": "shares / shares outstanding / min (F1 denominator; D41)", "group": "relative", "dir": "<", "log": True},
    {"key": "c_n_eff", "label": "n_eff", "unit": "effective independent orders, finest rate rung", "group": "relative", "dir": "<", "log": True},
    {"key": "c_top3", "label": "top3_share", "unit": "share of window volume in the 3 largest orders", "group": "relative", "dir": ">", "log": False},
    {"key": "c_move_per_trade", "label": "move_per_trade", "unit": "bp per collapsed trade", "group": "relative", "dir": ">", "log": True},
    {"key": "er", "label": "er", "unit": "efficiency ratio 0-1, primary price; chosen rung or every valid rung", "group": "scale_free", "dir": "<", "log": False},
]
OVERRIDES = [
    {"key": "o_leg_s", "label": "leg_s ≥", "dir": ">=", "log": False, "unit": "own-noise units"},
    {"key": "o_giveback", "label": "giveback ≤", "dir": "<=", "log": False, "unit": "0 = at the high, 1 = all given back"},
    {"key": "o_act_ratio", "label": "act_ratio ≥", "dir": ">=", "log": True, "unit": "finest-rung rate / segment rate"},
]


def clean(o):
    """JSON-safe copy: NaN -> null, +-inf -> +-1e308 (the encoded arrays are strings and pass through untouched)."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        x = float(o)
        return None if np.isnan(x) else (1e308 if x == np.inf else (-1e308 if x == -np.inf else x))
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def main() -> int:
    t0 = time.perf_counter()
    pop = C.load_population()
    t5, t6, t7 = C.read_json("t5_summary.json"), C.read_json("t6_summary.json"), C.read_json("t7_summary.json")
    smp = pd.read_parquet(C.art("t7_sample.parquet"))
    emb = set(smp.loc[smp["embedded"], "event_id"])
    years = sorted(C.dev_slice(pop)["year"].unique())
    m = pd.concat([pd.read_parquet(C.art(f"t6_moments_{y}.parquet")) for y in years], ignore_index=True)
    m = m[m["event_id"].isin(emb)].merge(pd.read_parquet(C.art("t7_flags.parquet"))[["moment_uid", "g1", "g2", "g3"]], on="moment_uid", how="left")
    auction_mm = int(m.loc[m["segment"].isin(["auction_open", "auction_close"]), "weight"].sum())
    scale_n = ST.check_cost_noise_scaling(m)
    sf = pd.concat([pd.read_parquet(C.art(f"t6_sf_rungs_{y}.parquet"), columns=["moment_uid", "event_id", "k", "er"]) for y in years], ignore_index=True)
    sf = sf[sf["event_id"].isin(emb)]
    tab, evt = ST.build(m, pop, sf)
    nrows = tab.pop("_rows")["n"]
    mm = m[m["segment"].isin(C.SEGS)]
    assert nrows == len(mm), "row count differs from the embedded sample's non-auction moments"
    for k, e in tab.items():                                                        # round trip
        assert SD.decode(e).size == nrows, f"{k} decodes to the wrong length"
    for k, c in {**ST.CONDITION_SOURCES, **ST.OVERRIDE_SOURCES}.items():
        assert not any(z in c.lower() for z in ST.FORBIDDEN)
    assert not any(any(z in k.lower() for z in ST.FORBIDDEN) for k in tab), "a forbidden column is embedded"

    # strips: row index of each pooled moment in the table
    mm_sorted = mm.assign(_e=mm["event_id"].map({e: i for i, e in enumerate(sorted(mm["event_id"].unique()))})).sort_values(["_e", "j"]).reset_index(drop=True)
    row_of = pd.Series(np.arange(len(mm_sorted)), index=mm_sorted["moment_uid"])
    pools = pd.read_parquet(C.art("t7_pools.parquet"))
    strips = list(np.load(C.REPO / C.OUT / "cache" / "t7_strips.npy", allow_pickle=True))
    smeta, cat = [], {k: [] for k in ("pt", "pp", "qt", "qb", "qa", "vb")}
    off = {k: 0 for k in cat}
    mrow = mm_sorted.set_index("moment_uid")
    for s in strips:
        u = s["moment_uid"]
        r = mrow.loc[u]
        rec = {"row": int(row_of[u]), "pools": sorted(pools.loc[pools["moment_uid"] == u, "pool"].tolist()), "lo_s": s["lo_s"], "hi_s": s["hi_s"], "n_prints": s["n_prints"]}
        for k in cat:
            rec[k] = [off[k], off[k] + int(s[k].size)]
            off[k] += int(s[k].size)
            cat[k].append(s[k])
        t = int(r["t_ns"])
        rec["leg"] = None if pd.isna(r["leg_high_ns"]) else {"lo_t": (int(r["leg_low_ns"]) - t) / 1e9, "lo_p": float(r["leg_low_px"]), "hi_t": (int(r["leg_high_ns"]) - t) / 1e9,
                                                             "hi_p": float(r["leg_high_px"])}
        smeta.append(rec)
    sarr = {k: SD.encode(np.concatenate(v) if v else np.zeros(0, np.float32), "f4") for k, v in cat.items()}

    bands = pd.read_parquet(C.art("t6b_null_bands.parquet"))
    removed = t5["escalation"]["row3b_removed"]
    er_removed = "er" in removed
    sweep = t5["sweep"]
    data_hash = hashlib.sha256(json.dumps({k: v["b"][:64] + str(v["n"]) for k, v in tab.items()}, sort_keys=True).encode()).hexdigest()[:12]
    s7 = t7["sample"]
    meta = {
        "header": CFG["suite"]["header"], "config_hash": C.cfg_hash(), "data_hash": data_hash, "sample_fraction": s7["fraction"],
        "events_embedded": s7["events_embedded"], "events_dev": s7["events"], "moments_embedded": int(nrows), "auction_moment_minutes": auction_mm,
        "row5": s7["row5_fires"], "row6": t6["row6_fires"], "row6_share": t6["row6_no_scale_free_rung_share"],
        "row7_events": int((~C.dev_slice(pop)["quotes_ingested"]).sum()), "removed": removed, "er_removed": er_removed,
        "bucket_dependent": {k: v["bucket_dependent"] for k, v in sweep.items()},
        "segs": list(C.SEGS), "horizons": C.HORIZONS, "wall": C.WALL, "vol": C.VOL, "types": ST.TYPES, "tiers": ST.TIERS, "tau_segs": ST.TAU_SEGS,
        "stack": STACK, "c_default": CFG["suite"]["viewing"]["c_default"], "h_default": CFG["suite"]["viewing"]["horizon_default"],
        "noise_band": CFG["suite"]["noise_band"], "bootstrap_B": CFG["suite"]["ticker_bootstrap"]["B"], "readability": CFG["suite"]["readability_line"],
        "near_k": 12, "gallery_label": CFG["galleries"]["label"], "pools": t7["pools"],
        "g_rules": {"G1": "n_eff ≤ 5 and top3_share ≥ 0.6 at the finest rate rung",
                    "G2": "turnover_t < 1%, dollar_flow ≥ $20,000/min at the finest rate rung, and er inside its cell's null 5–95% band at every valid rung 1–4",
                    "G3": "leg_s ≥ 2, 0.1 ≤ giveback ≤ 0.6, and in hindsight the price in (t, t + 60 min] beats the leg high by ≥ the spread at t and ≥ 1 own-noise unit"},
    }
    D = {"meta": meta, "conds": CONDS, "overrides": OVERRIDES, "events": evt, "arrays": tab,
         "bands": bands[["segment", "k", "tier", "basis", "null_median", "null_p05", "null_p95", "windows_sampled", "label_few_windows"]].to_dict("records"),
         "strips": {"meta": smeta, "arrays": sarr}}
    js = (C.REPO / ".venv/Lib/site-packages/plotly/package_data/plotly.min.js").read_text(encoding="utf-8")
    html = PAGE.replace("__DECODER__", SD.JS_DECODER).replace("__DATA__", json.dumps(clean(D), allow_nan=False))
    html = html.replace("<script>__PLOTLY__</script>", "<script>" + js + "</script>")
    out = C.REPO / C.SUITE / "chop_suite.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    size = out.stat().st_size
    assert size <= CFG["suite"]["size_budget_bytes"], f"suite {size:,} bytes exceeds the budget"
    C.write_json("t8_summary.json", {"config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t0, 1), "bytes": size, "rows": int(nrows),
                                     "events": len(evt["event_id"]), "strips": len(smeta), "data_hash": data_hash, "er_removed": er_removed,
                                     "cost_noise_scaling_rows_checked": scale_n, "arrays": {k: len(v["b"]) for k, v in tab.items()},
                                     "strip_bytes": SD.size_of(sarr), "assertions": ["development slice only", "no A12", "no hindsight condition", "no percentile or rank",
                                                                                      "row count = embedded sample", "decode length", "size budget"]})
    print(f"suite {size / 1e6:.1f} MB, {nrows:,} rows, {len(evt['event_id']):,} events, {len(smeta)} strips  {time.perf_counter() - t0:,.0f}s")
    return 0


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chop regime suite</title>
<style>
:root{--bg:#111418;--fg:#e6e6e6;--mut:#9aa4b2;--grid:#2a2f36;--card:#171b21;--kept:#4C9AFF;--filt:#FF8B3D;--warn:#ff6b6b;--ok:#7bd88f}
*{box-sizing:border-box} body{background:var(--bg);color:var(--fg);font:13px/1.4 system-ui,Segoe UI,sans-serif;margin:0}
header{position:sticky;top:0;z-index:20;background:#0d1013;border-bottom:1px solid var(--grid);padding:8px 16px}
header h1{font-size:16px;margin:0 0 2px} .hdr{color:#ffd479;font-weight:600} .sub{color:var(--mut);font-size:12px}
.warnline{color:var(--warn);font-size:12px} .wrap{display:flex;gap:12px;padding:0 16px}
#ctl{flex:0 0 380px;max-height:calc(100vh - 90px);overflow:auto;position:sticky;top:90px;padding:8px 4px 40px 0}
#main{flex:1;min-width:0;padding:8px 0 60px}
@media(max-width:900px){.wrap{flex-direction:column} #ctl{position:static;max-height:none;flex:auto}}
.card{background:var(--card);border:1px solid var(--grid);border-radius:6px;padding:8px;margin:0 0 10px}
h2{font-size:14px;margin:4px 0 6px} h3{font-size:12px;margin:6px 0 4px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:3px 0} .cond{border-top:1px solid var(--grid);padding:5px 0}
.cond.off .ctlz{opacity:.45} input[type=range]{width:150px} input[type=number]{width:92px;background:#1d2229;color:var(--fg);border:1px solid var(--grid);border-radius:3px;padding:2px 4px}
select,button{background:#1d2229;color:var(--fg);border:1px solid var(--grid);border-radius:4px;padding:3px 6px;font-size:12px} button{cursor:pointer} button.on{background:#2b4a7a}
.segtabs button{flex:1} .lab{min-width:110px} .unit{color:var(--mut);font-size:11px} .dis{color:var(--mut);font-style:italic}
table{border-collapse:collapse;font-size:12px} td,th{border-bottom:1px solid var(--grid);padding:2px 7px;text-align:right} th:first-child,td:first-child{text-align:left}
.lt20{color:var(--warn);font-weight:600} .big{font-size:22px;font-weight:700} .pill{display:inline-block;border-radius:9px;padding:0 7px;font-size:11px;font-weight:600}
.k{background:#1f3a66;color:#cfe0ff} .f{background:#663a1f;color:#ffe0cf} .r{background:#1f5a33;color:#cfffdc}
.gal{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:8px} .strip{background:#14181d;border:1px solid var(--grid);border-radius:6px;padding:4px;cursor:pointer}
.strip.pinned{border-color:#ffd479} .cap{font-size:11px;color:var(--mut);padding:2px 4px} .tabs button{margin:0 4px 4px 0}
</style></head><body>
<header><h1>Chop regime filter — C1 tuning suite</h1>
<div class="hdr" id="hdrtext"></div><div class="sub" id="hdrmeta"></div><div class="warnline" id="hdrwarn"></div></header>
<div class="wrap"><div id="ctl"></div><div id="main">
<div class="card" id="pA"></div>
<div class="card"><h2>B — each active measure against its threshold (full distribution per segment, weighted by moment-minutes)</h2><div id="pB"></div></div>
<div class="card"><h2>C — what the filter does to outcomes (hindsight; for judgement, never a condition)</h2><div class="row"><button id="bNoise">noise band (100 random filters)</button><button id="bBoot">ticker bootstrap</button><span class="sub" id="cNote"></span></div><div id="pC"></div><div id="pC2" class="sub"></div></div>
<div class="card"><h2>D — the hindsight chop label and S2's remaining-path type, kept vs filtered</h2><div id="pD"></div></div>
<div class="card"><h2>E — where the filter bites in time</h2><div id="pE"></div></div>
<div class="card"><h2>F — which conditions fire together (filtered moment-minutes)</h2><div id="pF"></div></div>
<div class="card"><h2>G — galleries: the evidence</h2><div class="sub" id="gNote"></div><div class="tabs" id="gTabs"></div><div class="row" id="gNav"></div><div id="gPinned" class="gal"></div><div id="gal" class="gal"></div></div>
</div></div>
<script>__PLOTLY__</script>
<script>
__DECODER__
const D = __DATA__;
const M = D.meta, SEGN = M.segs, H = M.horizons, NS = 3;
const $ = id => document.getElementById(id);
const L0 = {paper_bgcolor:'#171b21',plot_bgcolor:'#171b21',font:{color:'#e6e6e6',size:11},margin:{l:55,r:12,t:28,b:36},showlegend:true,legend:{orientation:'h',y:-0.18}};
const AX = {gridcolor:'#2a2f36',zeroline:false};
const COLK = '#4C9AFF', COLF = '#FF8B3D', SEGC = ['#c39bff','#4C9AFF','#7bd88f'];
const fmt = (x, d=3) => (x === null || x === undefined || Number.isNaN(x)) ? '—' : (!Number.isFinite(x) ? (x > 0 ? '∞' : '-∞') : (Math.abs(x) >= 1e5 || (Math.abs(x) < 1e-3 && x !== 0) ? x.toExponential(2) : x.toLocaleString(undefined,{maximumFractionDigits:d})));
let A, S, N, WT, TOD, EVT, TICK, NT;
const ST = {editSeg:1, cond:{}, comb:{mode:'any', m:2}, ovr:{}, view:{h:M.h_default, c:M.c_default, unit:'bp', net:false, fac:{year:'all', seg:'all', tier:'all', tcs:'all', dil:'all', quotes:'all'}}, last:null, gtab:'G1', gpage:0, pinned:new Set(), sorted:{}};
let STATE, FIRED, FAC;
function bit(f, b){ return (f >> b) & 1; }
function hval(i, key){ // cost_noise at the chosen horizon: the embedded rung x sqrt(h0 / h), exact within a ladder
  const h = ST.cond.cost_noise.h;
  if (M.wall[h] !== undefined) return A.c_cn_w5[i] * Math.sqrt(5 / M.wall[h]);
  return A.c_cn_v025[i] * Math.sqrt(0.25 / M.vol[h]);
}
function val(c, i){
  if (c.key === 'cost_noise') return hval(i);
  if (c.key === 'er'){ const r = ST.cond.er.rung; return r === 'every' ? A.er_all[i] : A['er_k' + r][i]; }
  return A[c.key][i];
}
function ovrVal(o, i){ return A[o.key][i]; }
function finiteRange(getter, seg){
  let lo = Infinity, hi = -Infinity, inf = false, nn = 0;
  for (let i = 0; i < N; i++){ if (A.seg[i] !== seg) continue; const v = getter(i); if (Number.isNaN(v)) continue; if (!Number.isFinite(v)){ inf = true; continue; } nn++; if (v < lo) lo = v; if (v > hi) hi = v; }
  return {lo, hi, inf, n:nn};
}
// ---------------------------------------------------------------- controls
function sliderToVal(c, p, r){ if (p >= 1000 && r.inf && c.dir === '>') return Infinity; if (c.log && r.lo > 0) return Math.exp(Math.log(r.lo) + p / 1000 * (Math.log(r.hi) - Math.log(r.lo))); return r.lo + p / 1000 * (r.hi - r.lo); }
function valToSlider(c, v, r){ if (!Number.isFinite(v)) return v > 0 ? 1000 : 0; if (c.log && r.lo > 0) return Math.max(0, Math.min(1000, 1000 * (Math.log(Math.max(v, r.lo)) - Math.log(r.lo)) / (Math.log(r.hi) - Math.log(r.lo) || 1))); return Math.max(0, Math.min(1000, 1000 * (v - r.lo) / ((r.hi - r.lo) || 1))); }
const RC = new Map();
function rangeOf(c, seg){ const key = [c.key, seg, c.key === 'cost_noise' ? ST.cond.cost_noise.h : '', c.key === 'er' ? ST.cond.er.rung : ''].join('|');
  if (!RC.has(key)) RC.set(key, finiteRange(i => c.kind === 'ovr' ? ovrVal(c, i) : val(c, i), seg)); return RC.get(key); }
function initState(){
  D.conds.forEach(c => { ST.cond[c.key] = {on:[false,false,false], th:[null,null,null], unav: c.group === 'presence' ? 'filtered' : 'passes'}; });
  ST.cond.cost_noise.h = M.h_default; ST.cond.er.rung = 'every';
  D.overrides.forEach(o => { o.kind = 'ovr'; ST.ovr[o.key] = {on:[false,false,false], th:[null,null,null]}; });
}
function noFilterValue(c, seg){ if (c.kind === 'ovr') return c.dir === '>=' ? Infinity : -Infinity;            // an override that rescues nothing
  const r = rangeOf(c, seg); return c.dir === '<' ? r.lo : (r.inf ? Infinity : r.hi); }
function unavCount(c, seg){ let w = 0; for (let i = 0; i < N; i++) if (A.seg[i] === seg && Number.isNaN(val(c, i))) w += WT[i]; return w; }
function buildControls(){
  const el = $('ctl'); let h = '';
  h += `<div class="card"><h2>Filter — values per segment</h2><div class="row segtabs">${SEGN.map((s,i)=>`<button data-seg="${i}" class="${i===ST.editSeg?'on':''}">${s}</button>`).join('')}</div>
  <div class="row"><button id="copySeg">copy this segment's settings to the other segments</button></div>
  <div class="row">combine: <select id="comb"><option value="any">filter if any active condition fires</option><option value="m">filter if at least m fire</option></select> m <input type="number" id="combm" min="1" value="2" style="width:50px"></div></div>`;
  for (const g of [['presence','Presence and cost'],['relative','Relative'],['scale_free','Scale-free']]){
    h += `<div class="card"><h3>${g[1]}</h3>`;
    D.conds.filter(c => c.group === g[0]).forEach(c => {
      const removed = c.key === 'er' && M.er_removed;
      if (removed){ h += `<div class="cond dis"><b>er</b> — removed from the conditions (Amendment 1 row 3b): ${M.removed.er}. Kept as a column; panel B shows it against its null band.</div>`; return; }
      h += `<div class="cond" id="cd_${c.key}"><div class="row"><label><input type="checkbox" id="on_${c.key}"> <b>${c.label}</b> ${c.dir} x</label>
        ${c.key==='cost_noise' ? `<select id="h_${c.key}">${H.map(x=>`<option ${x===ST.cond.cost_noise.h?'selected':''}>${x}</option>`).join('')}</select>` : ''}
        ${c.key==='er' ? `<select id="r_er">${['every',0,1,2,3,4,5,6].map(x=>`<option value="${x}" ${String(x)===String(ST.cond.er.rung)?'selected':''}>${x==='every'?'every valid rung':'rung '+x}</option>`).join('')}</select>` : ''}</div>
        <div class="row ctlz"><input type="range" min="0" max="1000" id="sl_${c.key}"><input type="number" step="any" id="nb_${c.key}"></div>
        <div class="row ctlz unit">${c.unit}${M.bucket_dependent[c.key==='cost_noise' ? 'cost_noise_' + ST.cond.cost_noise.h : (c.key==='er' ? 'er_mid' : c.key)] ? ' · <span class="lt20">bucket-dependent</span>' : ''}</div>
        <div class="row ctlz unit">unavailable: <select id="un_${c.key}"><option value="filtered">counts as filtered</option><option value="passes">passes</option></select> <span id="uc_${c.key}"></span></div></div>`;
    });
    h += `</div>`;
  }
  h += `<div class="card"><h3>Pause override (rescues only from relative and scale-free, never from presence and cost)</h3>`;
  D.overrides.forEach(o => { h += `<div class="cond" id="cd_${o.key}"><div class="row"><label><input type="checkbox" id="on_${o.key}"> <b>${o.label}</b> x</label></div>
     <div class="row ctlz"><input type="range" min="0" max="1000" id="sl_${o.key}"><input type="number" step="any" id="nb_${o.key}"></div><div class="row unit">${o.unit}</div></div>`; });
  h += `</div><div class="card"><h3>Viewing (does not change the filter)</h3>
   <div class="row">horizon <select id="vh">${H.map(x=>`<option ${x===ST.view.h?'selected':''}>${x}</option>`).join('')}</select>
   chop multiple c <input type="number" id="vc" step="0.1" value="${ST.view.c}" style="width:60px"></div>
   <div class="row">unit <select id="vu"><option value="bp">bp</option><option value="c">cents</option></select> <select id="vn"><option value="g">gross</option><option value="n">net of the round trip at t</option></select></div>
   <div class="row">year <select id="f_year"><option>all</option>${[...new Set(EVT.year)].sort().map(y=>`<option>${y}</option>`).join('')}</select>
   segment <select id="f_seg"><option>all</option>${SEGN.map((s,i)=>`<option value="${i}">${s}</option>`).join('')}</select></div>
   <div class="row">price tier at τ <select id="f_tier"><option>all</option>${M.tiers.map((s,i)=>`<option value="${i}">${s}</option>`).join('')}</select>
   tau_close_sensitive <select id="f_tcs"><option>all</option><option value="0">false</option><option value="1">true</option><option value="2">not settled</option></select></div>
   <div class="row">dilution <select id="f_dil"><option>all</option><option value="0">false</option><option value="1">true</option><option value="2">unknown</option></select>
   quotes ingested <select id="f_quotes"><option>all</option><option value="1">yes</option><option value="0">no</option></select></div></div>
   <div class="card"><button id="export">export the filter config (JSON)</button></div>`;
  el.innerHTML = h;
  el.querySelectorAll('.segtabs button').forEach(b => b.addEventListener('click', () => { ST.editSeg = +b.dataset.seg; el.querySelectorAll('.segtabs button').forEach(x => x.classList.toggle('on', +x.dataset.seg === ST.editSeg)); syncControls(); }));
  $('copySeg').addEventListener('click', () => { const s = ST.editSeg; for (const k in ST.cond) for (let t = 0; t < NS; t++){ ST.cond[k].on[t] = ST.cond[k].on[s]; ST.cond[k].th[t] = ST.cond[k].th[s]; } for (const k in ST.ovr) for (let t = 0; t < NS; t++){ ST.ovr[k].on[t] = ST.ovr[k].on[s]; ST.ovr[k].th[t] = ST.ovr[k].th[s]; } syncControls(); schedule(); });
  $('comb').addEventListener('change', e => { ST.comb.mode = e.target.value; schedule(); });
  $('combm').addEventListener('change', e => { ST.comb.m = Math.max(1, +e.target.value || 1); schedule(); });
  const wire = (c, isO) => {
    const st = isO ? ST.ovr[c.key] : ST.cond[c.key];
    const on = $('on_' + c.key), sl = $('sl_' + c.key), nb = $('nb_' + c.key);
    if (!on) return;
    on.addEventListener('change', () => { const s = ST.editSeg; st.on[s] = on.checked; if (st.on[s] && st.th[s] === null) st.th[s] = noFilterValue(c, s); syncControls(); if (!isO) ST.last = {key:c.key, seg:s}; schedule(); });
    sl.addEventListener('input', () => { const s = ST.editSeg; const r = rangeOf(c, s); st.th[s] = sliderToVal(c, +sl.value, r); nb.value = Number.isFinite(st.th[s]) ? +st.th[s].toPrecision(6) : ''; if (!isO) ST.last = {key:c.key, seg:s}; schedule(); });
    nb.addEventListener('change', () => { const s = ST.editSeg; st.th[s] = nb.value === '' ? (c.dir === '>' ? Infinity : -Infinity) : +nb.value; syncControls(); if (!isO) ST.last = {key:c.key, seg:s}; schedule(); });
    if (!isO){ const un = $('un_' + c.key); un.value = st.unav; un.addEventListener('change', () => { st.unav = un.value; schedule(); }); }
  };
  D.conds.forEach(c => wire(c, false)); D.overrides.forEach(o => wire(o, true));
  if ($('h_cost_noise')) $('h_cost_noise').addEventListener('change', e => { ST.cond.cost_noise.h = e.target.value; for (let s = 0; s < NS; s++) if (ST.cond.cost_noise.th[s] !== null && !ST.cond.cost_noise.on[s]) ST.cond.cost_noise.th[s] = null; syncControls(); schedule(); });
  if ($('r_er')) $('r_er').addEventListener('change', e => { ST.cond.er.rung = e.target.value === 'every' ? 'every' : +e.target.value; syncControls(); schedule(); });
  $('vh').addEventListener('change', e => { ST.view.h = e.target.value; drawOutcomes(); });
  $('vc').addEventListener('change', e => { ST.view.c = +e.target.value; drawD(); });
  $('vu').addEventListener('change', e => { ST.view.unit = e.target.value; drawOutcomes(); });
  $('vn').addEventListener('change', e => { ST.view.net = e.target.value === 'n'; drawOutcomes(); });
  for (const f of ['year','seg','tier','tcs','dil','quotes']) $('f_' + f).addEventListener('change', e => { ST.view.fac[f] = e.target.value; computeFacets(); drawAll(); });
  $('export').addEventListener('click', exportConfig);
  $('bNoise').addEventListener('click', noiseBand); $('bBoot').addEventListener('click', bootstrap);
  syncControls();
}
function syncControls(){
  const s = ST.editSeg;
  const sync = (c, isO) => {
    const st = isO ? ST.ovr[c.key] : ST.cond[c.key]; const on = $('on_' + c.key); if (!on) return;
    on.checked = st.on[s]; $('cd_' + c.key).classList.toggle('off', !st.on[s]);
    const r = rangeOf(c, s); const th = st.th[s] === null ? noFilterValue(c, s) : st.th[s];
    $('sl_' + c.key).value = valToSlider(c, th, r); $('nb_' + c.key).value = Number.isFinite(th) ? +th.toPrecision(6) : '';
    if (!isO){ $('un_' + c.key).value = st.unav; const w = unavCount(c, s); $('uc_' + c.key).textContent = `(${fmt(w,0)} moment-minutes unavailable in ${SEGN[s]})`; }
  };
  D.conds.forEach(c => sync(c, false)); D.overrides.forEach(o => sync(o, true));
}
// ---------------------------------------------------------------- the filter
function activeConds(){ return D.conds.filter(c => !(c.key === 'er' && M.er_removed)).map((c, ix) => ({c, ix})).filter(x => ST.cond[x.c.key].on.some(Boolean)); }
function recompute(){
  const act = activeConds(); const ovr = D.overrides.filter(o => ST.ovr[o.key].on.some(Boolean));
  const TH = {}; for (const {c} of act) TH[c.key] = [0, 1, 2].map(s => ST.cond[c.key].th[s] === null ? noFilterValue(c, s) : ST.cond[c.key].th[s]);
  for (let i = 0; i < N; i++){
    const s = A.seg[i]; let nP = 0, nR = 0, bits = 0;
    for (const {c, ix} of act){
      const st = ST.cond[c.key]; if (!st.on[s]) continue;
      const th = TH[c.key][s]; const v = val(c, i);
      const fired = Number.isNaN(v) ? st.unav === 'filtered' : (c.dir === '<' ? v < th : v > th);
      if (fired){ bits |= (1 << ix); if (c.group === 'presence') nP++; else nR++; }
    }
    const need = ST.comb.mode === 'any' ? 1 : ST.comb.m;
    let state = (nP + nR) >= need ? 1 : 0;
    if (state === 1 && nR > 0 && nP < need){
      let any = false, hold = true;
      for (const o of ovr){ const so = ST.ovr[o.key]; if (!so.on[s]) continue; any = true; const v = ovrVal(o, i); const th = so.th[s];
        if (Number.isNaN(v) || th === null || !(o.dir === '>=' ? v >= th : v <= th)) { hold = false; break; } }
      if (any && hold) state = 2;
    }
    STATE[i] = state; FIRED[i] = bits;
  }
}
function computeFacets(){
  const f = ST.view.fac;
  for (let i = 0; i < N; i++){
    const e = A.ev[i]; const fl = A.flags[i];
    FAC[i] = (f.year === 'all' || EVT.year[e] === +f.year) && (f.seg === 'all' || A.seg[i] === +f.seg) && (f.tier === 'all' || EVT.tier[e] === +f.tier)
      && (f.tcs === 'all' || ((fl >> 9) & 3) === +f.tcs) && (f.dil === 'all' || EVT.dilution[e] === +f.dil) && (f.quotes === 'all' || EVT.quotes_ingested[e] === +f.quotes) ? 1 : 0;
  }
}
let timer = null;
function schedule(){ clearTimeout(timer); timer = setTimeout(() => { recompute(); drawAll(); }, 120); }
function drawAll(){ drawA(); drawB(); drawOutcomes(); drawE(); drawF(); drawG(); }
// ---------------------------------------------------------------- A
function drawA(){
  const kept = [0,0,0], filt = [0,0,0], ky = {}, fy = {}, kt = [0,0,0,0], ft = [0,0,0,0]; const evk = new Set(), evs = new Set();
  const g = {G1:[[0,0],[0,0],[0,0]], G2:[[0,0],[0,0],[0,0]], G3:[[0,0],[0,0],[0,0]]};
  for (let i = 0; i < N; i++){ if (!FAC[i]) continue; const s = A.seg[i], w = WT[i], e = A.ev[i], y = EVT.year[e], t = EVT.tier[e], k = STATE[i] !== 1;
    evs.add(e); if (k){ kept[s] += w; ky[y] = (ky[y]||0) + w; kt[t] += w; evk.add(e); } else { filt[s] += w; fy[y] = (fy[y]||0) + w; ft[t] += w; }
    const fl = A.flags[i]; for (const [gname, b] of [['G1',5],['G2',6],['G3',7]]) if (bit(fl, b)){ g[gname][s][1]++; if (gname === 'G3' ? !k : k) g[gname][s][0]++; } }
  const c = x => `<span class="${x < M.readability ? 'lt20' : ''}">${fmt(x,0)}${x < M.readability ? ' (&lt;20)' : ''}</span>`;
  const tot = a => a.reduce((p, q) => p + q, 0);
  let h = `<div class="row" style="gap:24px"><div><div class="sub">Pauses filtered (G3, moments)</div><div class="big">${c(tot(g.G3.map(x=>x[0])))} of ${c(tot(g.G3.map(x=>x[1])))}</div><div class="sub">${SEGN.map((s,i)=>`${s}: ${c(g.G3[i][0])} of ${c(g.G3[i][1])}`).join(' · ')}</div></div>
    <div><div class="sub">Low-volume pops kept (G1)</div><div class="big">${c(tot(g.G1.map(x=>x[0])))} of ${c(tot(g.G1.map(x=>x[1])))}</div></div>
    <div><div class="sub">Higher-float noise kept (G2)</div><div class="big">${c(tot(g.G2.map(x=>x[0])))} of ${c(tot(g.G2.map(x=>x[1])))}</div></div>
    <div><div class="sub">Events with ≥ 1 kept moment</div><div class="big">${c(evk.size)} of ${c(evs.size)}</div></div></div>`;
  h += `<table><tr><th>moment-minutes</th>${SEGN.map(s=>`<th>${s}</th>`).join('')}<th>all</th></tr><tr><td>kept</td>${kept.map(c).map(x=>`<td>${x}</td>`).join('')}<td>${c(tot(kept))}</td></tr>
    <tr><td>filtered</td>${filt.map(c).map(x=>`<td>${x}</td>`).join('')}<td>${c(tot(filt))}</td></tr></table>`;
  const ys = Object.keys({...ky, ...fy}).sort();
  h += `<div class="row" style="gap:24px;align-items:flex-start"><table><tr><th>year</th><th>kept</th><th>filtered</th></tr>${ys.map(y=>`<tr><td>${y}</td><td>${c(ky[y]||0)}</td><td>${c(fy[y]||0)}</td></tr>`).join('')}</table>
    <table><tr><th>price tier at τ</th><th>kept</th><th>filtered</th></tr>${M.tiers.map((t,i)=>`<tr><td>${t}</td><td>${c(kt[i])}</td><td>${c(ft[i])}</td></tr>`).join('')}</table></div>`;
  $('pA').innerHTML = `<h2>A — pinned counts (facet applied; red = under ${M.readability})</h2>` + h;
}
// ---------------------------------------------------------------- B
function hist(get, seg, logx){
  let lo = Infinity, hi = -Infinity; const vs = [], ws = [];
  let nz = 0, ninf = 0;
  for (let i = 0; i < N; i++){ if (!FAC[i] || A.seg[i] !== seg) continue; const v = get(i); if (Number.isNaN(v)) continue; if (!Number.isFinite(v)){ ninf++; continue; } if (logx && v <= 0){ nz++; continue; } vs.push(v); ws.push(WT[i]); if (v < lo) lo = v; if (v > hi) hi = v; }
  if (!vs.length) return {x:[], y:[], n:0, nz, ninf};
  const nb = 60, a = logx ? Math.log10(lo) : lo, b = logx ? Math.log10(hi) : hi, step = (b - a) / nb || 1; const y = new Array(nb).fill(0);
  for (let k = 0; k < vs.length; k++){ const z = logx ? Math.log10(vs[k]) : vs[k]; y[Math.min(nb - 1, Math.floor((z - a) / step))] += ws[k]; }
  const x = y.map((_, k) => logx ? Math.pow(10, a + (k + 0.5) * step) : a + (k + 0.5) * step); return {x, y, n:vs.length, lo, hi, nz, ninf};
}
function drawB(){
  const el = $('pB'); el.innerHTML = '';
  const act = activeConds().map(x => x.c);
  const items = act.slice(); items.push({key:'__er', label:'er (reference: real vs simulated null band per rung)'});
  for (const c of items){
    const div = document.createElement('div'); div.style.height = '260px'; el.appendChild(div);
    if (c.key === '__er'){ drawER(div); continue; }
    const tr = [], shapes = [], ann = [];
    for (let s = 0; s < NS; s++){
      const h = hist(i => val(c, i), s, c.log); const xa = s === 0 ? 'x' : 'x' + (s + 1), ya = s === 0 ? 'y' : 'y' + (s + 1);
      tr.push({type:'bar', x:h.x, y:h.y, xaxis:xa, yaxis:ya, marker:{color:SEGC[s]}, name:`${SEGN[s]} (n=${fmt(h.n,0)}${h.nz ? ', ≤ 0 off the log axis: ' + fmt(h.nz,0) : ''}${h.ninf ? ', ∞: ' + fmt(h.ninf,0) : ''})`});
      const st = ST.cond[c.key]; const th = st.on[s] ? (st.th[s] === null ? noFilterValue(c, s) : st.th[s]) : null;
      if (th !== null && Number.isFinite(th) && h.n){ shapes.push({type:'line', xref:xa, yref:ya + ' domain', x0:th, x1:th, y0:0, y1:1, line:{color:'#ffd479', width:2}});
        shapes.push({type:'rect', xref:xa, yref:ya + ' domain', x0: c.dir === '<' ? h.lo : th, x1: c.dir === '<' ? th : h.hi, y0:0, y1:1, fillcolor:'rgba(255,107,107,0.13)', line:{width:0}}); }
      if (c.ref !== undefined) shapes.push({type:'line', xref:xa, yref:ya + ' domain', x0:c.ref, x1:c.ref, y0:0, y1:1, line:{color:'#9aa4b2', dash:'dash'}});
    }
    const lay = {...L0, height:260, title:{text:`${c.label}${c.key==='cost_noise' ? ' at ' + ST.cond.cost_noise.h : ''} — threshold (yellow), rejected side shaded${c.ref !== undefined ? ', dashed: ' + c.ref_label : ''}`, font:{size:12}}, shapes, grid:{rows:1, columns:3, pattern:'independent'}, bargap:0};
    for (let s = 0; s < NS; s++){ lay[s === 0 ? 'xaxis' : 'xaxis' + (s + 1)] = {...AX, type: c.log ? 'log' : 'linear', title:{text:SEGN[s] + ' · ' + c.label, font:{size:10}}}; lay[s === 0 ? 'yaxis' : 'yaxis' + (s + 1)] = {...AX, title:{text: s === 0 ? 'moment-minutes' : '', font:{size:10}}}; }
    Plotly.react(div, tr, lay, {displaylogo:false, responsive:true});
  }
}
function drawER(div){
  const tierSel = ST.view.fac.tier === 'all' ? null : +ST.view.fac.tier; const tr = []; const lay = {...L0, height:300, grid:{rows:1, columns:3, pattern:'independent'}, boxmode:'group',
    title:{text:`er per rung: real (boxes, embedded moments, n per box in hover) vs the A1.3 simulated null 5–95% band and median (midpoint cells${tierSel === null ? ', each tier' : ', tier ' + M.tiers[tierSel]})${M.er_removed ? ' — NOT a condition (row 3b)' : ''}`, font:{size:12}}};
  for (let s = 0; s < NS; s++){
    const xa = s === 0 ? 'x' : 'x' + (s + 1), ya = s === 0 ? 'y' : 'y' + (s + 1);
    const q1 = [], md = [], q3 = [], lf = [], uf = [], xs = [], nm = [];
    for (let k = 0; k <= 6; k++){ const arr = A['er_k' + k]; const ys = []; for (let i = 0; i < N; i++) if (FAC[i] && A.seg[i] === s && Number.isFinite(arr[i]) && (tierSel === null || EVT.tier[A.ev[i]] === tierSel)) ys.push(arr[i]);
      if (!ys.length) continue; const v = Float64Array.from(ys).sort(); const q = p => v[Math.min(v.length - 1, Math.floor(p * (v.length - 1)))];
      xs.push(k); q1.push(q(0.25)); md.push(q(0.5)); q3.push(q(0.75)); lf.push(v[0]); uf.push(v[v.length - 1]); nm.push(`rung ${k}: n ${v.length} moments (unweighted), whiskers = min / max`); }
    tr.push({type:'box', x:xs, q1, median:md, q3, lowerfence:lf, upperfence:uf, xaxis:xa, yaxis:ya, marker:{color:SEGC[s]}, name:SEGN[s] + ' real er', text:nm, hoverinfo:'text+y', showlegend:false});
    for (let t = 0; t < 4; t++){ if (tierSel !== null && t !== tierSel) continue;
      const b = D.bands.filter(r => r.segment === SEGN[s] && r.tier === M.tiers[t] && r.basis === 'mid' && r.k <= 6).sort((p, q) => p.k - q.k);
      tr.push({x:b.map(r=>r.k), y:b.map(r=>r.null_p95), xaxis:xa, yaxis:ya, mode:'lines', line:{width:0}, showlegend:false, hoverinfo:'skip'});
      tr.push({x:b.map(r=>r.k), y:b.map(r=>r.null_p05), xaxis:xa, yaxis:ya, mode:'lines', line:{width:0}, fill:'tonexty', fillcolor:'rgba(150,150,150,0.18)', showlegend:false, hoverinfo:'skip'});
      tr.push({x:b.map(r=>r.k), y:b.map(r=>r.null_median), xaxis:xa, yaxis:ya, mode:'lines+markers', line:{color:'#ffffff', dash:'dot', width:1}, marker:{size:4},
        text:b.map(r=>`${M.tiers[t]} null median ${fmt(r.null_median)} [${fmt(r.null_p05)}, ${fmt(r.null_p95)}], sampled windows ${r.windows_sampled}${r.label_few_windows ? ' (FEW < 20)' : ''}`), hoverinfo:'text', showlegend:false}); }
    lay[s === 0 ? 'xaxis' : 'xaxis' + (s + 1)] = {...AX, title:{text:SEGN[s] + ' · rung k', font:{size:10}}, dtick:1};
    lay[s === 0 ? 'yaxis' : 'yaxis' + (s + 1)] = {...AX, range:[0, 1], title:{text: s === 0 ? 'er' : '', font:{size:10}}};
  }
  div.style.height = '300px'; Plotly.react(div, tr, lay, {displaylogo:false, responsive:true});
}
// ---------------------------------------------------------------- outcomes (C, D)
function outVal(kind, h, i){ // kind 'ret' | 'mfe'; returns NaN if unavailable
  let v = A[`y_${kind}_${h}`][i]; if (!Number.isFinite(v)) return NaN;
  if (ST.view.unit === 'c') v = v * A.y_entry[i] / 100;
  if (ST.view.net){ const rt = ST.view.unit === 'c' ? A.c_spread_c[i] : A.c_spread_bp[i]; if (!Number.isFinite(rt)) return NaN; v -= rt; }
  return v;
}
function sortedIdx(kind, h){
  const key = [kind, h, ST.view.unit, ST.view.net].join('|'); if (ST.sorted[key]) return ST.sorted[key];
  const idx = [], vv = []; for (let i = 0; i < N; i++){ const v = outVal(kind, h, i); if (!Number.isNaN(v)){ idx.push(i); } }
  const vals = new Float64Array(N); for (const i of idx) vals[i] = outVal(kind, h, i);
  idx.sort((a, b) => vals[a] - vals[b]); const o = {idx:Uint32Array.from(idx), vals}; ST.sorted[key] = o; return o;
}
function wmedians(o, wk, wf){ // weighted medians of kept and filtered along the sorted order; wk/wf: functions i -> weight
  let tk = 0, tf = 0; for (const i of o.idx){ tk += wk(i); tf += wf(i); }
  let ck = 0, cf = 0, mk = NaN, mf = NaN;
  for (const i of o.idx){ const a = wk(i), b = wf(i); if (Number.isNaN(mk) && a > 0){ ck += a; if (ck >= tk / 2) mk = o.vals[i]; } if (Number.isNaN(mf) && b > 0){ cf += b; if (cf >= tf / 2) mf = o.vals[i]; } if (!Number.isNaN(mk) && !Number.isNaN(mf)) break; }
  return {mk, mf, tk, tf};
}
function drawOutcomes(){ drawC(); drawD(); }
function medianRT(){
  const key = 'rt|' + ST.view.unit; const arr = ST.view.unit === 'c' ? A.c_spread_c : A.c_spread_bp;
  if (!ST.sorted[key]){ const idx = []; for (let i = 0; i < N; i++) if (Number.isFinite(arr[i])) idx.push(i); idx.sort((a, b) => arr[a] - arr[b]); ST.sorted[key] = Uint32Array.from(idx); }
  let tot = 0; for (const i of ST.sorted[key]) if (FAC[i]) tot += WT[i]; let cum = 0; for (const i of ST.sorted[key]) if (FAC[i]){ cum += WT[i]; if (cum >= tot / 2) return arr[i]; } return NaN;
}
function drawC(){
  const h = ST.view.h, u = ST.view.unit === 'c' ? '¢' : 'bp'; const tr = []; const shapes = [];
  const lay = {...L0, height:340, grid:{rows:1, columns:2, pattern:'independent'}, title:{text:`ECDF of forward return and MFE at ${h} (${u}, ${ST.view.net ? 'net of the round trip at t' : 'gross'}), kept vs filtered, weighted by moment-minutes`, font:{size:12}}};
  let note = '';
  ['ret','mfe'].forEach((kind, ci) => {
    const o = sortedIdx(kind, h); const xa = ci === 0 ? 'x' : 'x2', ya = ci === 0 ? 'y' : 'y2';
    for (const [grp, col, test] of [['kept', COLK, i => STATE[i] !== 1], ['filtered', COLF, i => STATE[i] === 1]]){
      let tot = 0, n = 0; for (const i of o.idx) if (FAC[i] && test(i)){ tot += WT[i]; n++; }
      const xs = [], ys = []; let cum = 0, next = 0; const stepN = Math.max(1, Math.floor(n / 500));
      let q = 0; for (const i of o.idx){ if (!(FAC[i] && test(i))) continue; cum += WT[i]; q++; if (q % stepN === 0 || q === n){ xs.push(o.vals[i]); ys.push(cum / tot); } }
      tr.push({x:xs, y:ys, xaxis:xa, yaxis:ya, mode:'lines', line:{color:col, shape:'hv'}, name:`${kind} ${grp} (n=${fmt(n,0)})`});
    }
    const wm = wmedians(o, i => FAC[i] && STATE[i] !== 1 ? WT[i] : 0, i => FAC[i] && STATE[i] === 1 ? WT[i] : 0);
    note += `${kind}: median kept ${fmt(wm.mk,1)} ${u}, filtered ${fmt(wm.mf,1)} ${u}, kept − filtered ${fmt(wm.mk - wm.mf,1)} ${u}. `;
    const stack = ST.view.unit === 'c' ? M.stack.c : M.stack.bp; const mrt = medianRT();
    const lines = ST.view.net ? [[0, '#9aa4b2', 'solid']] : [[stack, '#ffd479', 'dash'], [mrt, '#c39bff', 'dot']];
    for (const [x, colr, dash] of lines) if (Number.isFinite(x)) shapes.push({type:'line', xref:xa, yref:ya + ' domain', x0:x, x1:x, y0:0, y1:1, line:{color:colr, dash}});
    lay[ci === 0 ? 'xaxis' : 'xaxis2'] = {...AX, title:{text:`${kind === 'ret' ? 'fwd_ret' : 'fwd_mfe'}_${h} (${u})`, font:{size:10}}};
    lay[ci === 0 ? 'yaxis' : 'yaxis2'] = {...AX, range:[0, 1], title:{text:'share of moment-minutes ≤ x', font:{size:10}}};
    if (!ST.view.net) note += `Lines: dashed = Phase 11 flat stack ${stack} ${u}; dotted = median round trip at t (${fmt(mrt,1)} ${u}). `;
  });
  lay.shapes = shapes; Plotly.react($('pC'), tr, lay, {displaylogo:false, responsive:true}); $('pC2').innerHTML = note;
}
function rng32(a){ return function(){ a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function minutesOf(j){ return j <= 60 ? j : 60 + 5 * (j - 60); }
function noiseBand(){
  $('cNote').textContent = 'computing noise band…';
  setTimeout(() => {
    const h = ST.view.h; const cells = new Map();
    for (let i = 0; i < N; i++){ if (!FAC[i]) continue; const mn = minutesOf(A.j[i]); const key = A.seg[i] * 100 + (mn === 0 ? -1 : Math.floor(Math.log2(mn)));
      if (!cells.has(key)) cells.set(key, {idx:[], kw:0, w:0}); const c = cells.get(key); c.idx.push(i); c.w += WT[i]; if (STATE[i] !== 1) c.kw += WT[i]; }
    const res = {ret:[], mfe:[]}; const keep = new Uint8Array(N);
    for (let r = 0; r < M.noise_band.filters; r++){
      const rnd = rng32(20260930 + r); keep.fill(0);
      for (const c of cells.values()){ const ix = c.idx.slice(); for (let a = ix.length - 1; a > 0; a--){ const b = Math.floor(rnd() * (a + 1)); [ix[a], ix[b]] = [ix[b], ix[a]]; }
        let cum = 0; for (const i of ix){ if (cum >= c.kw) break; keep[i] = 1; cum += WT[i]; } }
      for (const kind of ['ret','mfe']){ const wm = wmedians(sortedIdx(kind, h), i => FAC[i] && keep[i] ? WT[i] : 0, i => FAC[i] && !keep[i] ? WT[i] : 0); res[kind].push(wm.mk - wm.mf); }
    }
    let txt = `Noise band (${M.noise_band.filters} seeded random filters keeping the same moment-minute share in each segment × minutes-since-τ octave cell): `;
    for (const kind of ['ret','mfe']){ const v = res[kind].filter(Number.isFinite).sort((a, b) => a - b); const q = p => v[Math.min(v.length - 1, Math.floor(p * (v.length - 1)))];
      const real = wmedians(sortedIdx(kind, h), i => FAC[i] && STATE[i] !== 1 ? WT[i] : 0, i => FAC[i] && STATE[i] === 1 ? WT[i] : 0);
      txt += `${kind}: real kept − filtered ${fmt(real.mk - real.mf,1)}, random 5–95% [${fmt(q(0.05),1)}, ${fmt(q(0.95),1)}] (n filters ${v.length}). `; }
    $('cNote').textContent = txt;
  }, 20);
}
function bootstrap(){
  $('cNote').textContent = 'computing ticker bootstrap…';
  setTimeout(() => {
    const h = ST.view.h, B = M.bootstrap_B; const cnt = new Float64Array(NT); const out = {ret:[], mfe:[]};
    for (let b = 0; b < B; b++){ const rnd = rng32(777 + b); cnt.fill(0); for (let q = 0; q < NT; q++) cnt[Math.floor(rnd() * NT)] += 1;
      for (const kind of ['ret','mfe']){ const wm = wmedians(sortedIdx(kind, h), i => FAC[i] && STATE[i] !== 1 ? WT[i] * cnt[TICK[A.ev[i]]] : 0, i => FAC[i] && STATE[i] === 1 ? WT[i] * cnt[TICK[A.ev[i]]] : 0); out[kind].push(wm.mk - wm.mf); } }
    let txt = `Ticker bootstrap (${B} resamples of the ${NT} tickers): `;
    for (const kind of ['ret','mfe']){ const v = out[kind].filter(Number.isFinite).sort((a, b) => a - b); const q = p => v[Math.min(v.length - 1, Math.floor(p * (v.length - 1)))];
      txt += `${kind} kept − filtered median 95% [${fmt(q(0.025),1)}, ${fmt(q(0.975),1)}] (n ${v.length}). `; }
    $('cNote').textContent = txt;
  }, 20);
}
function drawD(){
  const c = ST.view.c; const xs = [], yk = [], yf = [], tk = [], tf = [];
  for (const h of H){ let k = 0, kn = 0, f = 0, fn = 0, kp = 0, fp = 0;
    const mfe = A['y_mfe_' + h];
    for (let i = 0; i < N; i++){ if (!FAC[i]) continue; const stc = (A.y_state[i] >> (2 * H.indexOf(h))) & 3; const kept = STATE[i] !== 1;
      if (stc === 2){ if (kept) kp += WT[i]; else fp += WT[i]; continue; } if (stc === 3) continue;
      const rt = ST.view.unit === 'c' ? A.c_spread_c[i] : A.c_spread_bp[i]; if (!Number.isFinite(rt)) continue;
      const m = ST.view.unit === 'c' ? mfe[i] * A.y_entry[i] / 100 : mfe[i]; const chop = m < c * rt;
      if (kept){ kn += WT[i]; if (chop) k += WT[i]; } else { fn += WT[i]; if (chop) f += WT[i]; } }
    xs.push(h); yk.push(kn ? k / kn : null); yf.push(fn ? f / fn : null); tk.push(`kept: chop ${fmt(k,0)} of ${fmt(kn,0)} mm; no print in h ${fmt(kp,0)} mm`); tf.push(`filtered: chop ${fmt(f,0)} of ${fmt(fn,0)} mm; no print in h ${fmt(fp,0)} mm`); }
  const tr = [{type:'bar', x:xs, y:yk, name:'kept', marker:{color:COLK}, text:tk, hoverinfo:'text+y'}, {type:'bar', x:xs, y:yf, name:'filtered', marker:{color:COLF}, text:tf, hoverinfo:'text+y'}];
  // rem_type mix at tau, +1, +2, +5, +10, +20
  const js = [0,1,2,5,10,20]; const tr2 = []; const cnt = {};
  for (let i = 0; i < N; i++){ if (!FAC[i]) continue; const jj = js.indexOf(A.j[i]); if (jj < 0) continue; const t = EVT.rem[A.ev[i]][jj]; if (t === 255) continue; const g = STATE[i] !== 1 ? 'kept' : 'filtered';
    const key = g + '|' + jj; cnt[key] = cnt[key] || new Array(6).fill(0); cnt[key][t] += WT[i]; }
  const cats = []; js.forEach((j, jj) => ['kept','filtered'].forEach(g => cats.push([g, jj, `${j === 0 ? 'τ' : '+' + j}m ${g}`])));
  const TC = ['#e15759','#f28e2b','#edc948','#59a14f','#76b7b2','#9aa4b2'];
  M.types.forEach((ty, t) => tr2.push({type:'bar', x:cats.map(c => c[2]), y:cats.map(c => { const a = cnt[c[0] + '|' + c[1]]; const s = a ? a.reduce((p, q) => p + q, 0) : 0; return s ? a[t] / s : null; }),
    name:ty, marker:{color:TC[t]}, text:cats.map(c => { const a = cnt[c[0] + '|' + c[1]]; return a ? `${ty}: ${fmt(a[t],0)} of ${fmt(a.reduce((p, q) => p + q, 0),0)} mm` : 'n 0'; }), hoverinfo:'text'}));
  const el = $('pD'); el.innerHTML = '<div id="pD1" style="height:280px"></div><div id="pD2" style="height:320px"></div>';
  Plotly.react($('pD1'), tr, {...L0, height:280, barmode:'group', title:{text:`share of chop_h (MFE < ${c} × round trip at t, ${ST.view.unit === 'c' ? 'cents' : 'bp'}) among moments with a print in h; both ladders; hover for n and the no-print class`, font:{size:12}}, xaxis:AX, yaxis:{...AX, range:[0, 1]}}, {displaylogo:false, responsive:true});
  Plotly.react($('pD2'), tr2, {...L0, height:320, barmode:'stack', title:{text:'S2 remaining-path type mix at τ, +1, +2, +5, +10, +20 min, kept vs filtered (shares; hover for n)', font:{size:12}}, xaxis:AX, yaxis:{...AX, range:[0, 1]}}, {displaylogo:false, responsive:true});
}
// ---------------------------------------------------------------- E, F
function drawE(){
  const tr = [], tr2 = [];
  for (let s = 0; s < NS; s++){ const byj = new Map(), byt = new Map();
    for (let i = 0; i < N; i++){ if (!FAC[i] || A.seg[i] !== s) continue; const mn = minutesOf(A.j[i]); const tod = Math.floor((EVT.tau_tod_min[A.ev[i]] + mn) / 15) * 15;
      for (const [mp, key] of [[byj, mn], [byt, tod]]){ const o = mp.get(key) || [0, 0, 0]; o[0] += WT[i]; if (STATE[i] !== 1) o[1] += WT[i]; o[2]++; mp.set(key, o); } }
    const pts = [...byj.entries()].sort((a, b) => a[0] - b[0]); tr.push({x:pts.map(p => Math.max(p[0], 0.5)), y:pts.map(p => p[1][1] / p[1][0]), mode:'lines+markers', marker:{size:3}, line:{color:SEGC[s]}, name:SEGN[s], text:pts.map(p => `n ${p[1][2]} moments`), hoverinfo:'x+y+text'});
    const pt2 = [...byt.entries()].sort((a, b) => a[0] - b[0]); tr2.push({x:pt2.map(p => 4 + p[0] / 60), y:pt2.map(p => p[1][1] / p[1][0]), mode:'lines+markers', marker:{size:3}, line:{color:SEGC[s]}, name:SEGN[s], text:pt2.map(p => `n ${p[1][2]} moments`), hoverinfo:'x+y+text'}); }
  const el = $('pE'); el.innerHTML = '<div id="pE1" style="height:260px"></div><div id="pE2" style="height:260px"></div>';
  Plotly.react($('pE1'), tr, {...L0, height:260, title:{text:'kept share of moment-minutes against minutes since τ (log; τ drawn at 0.5)', font:{size:12}}, xaxis:{...AX, type:'log'}, yaxis:{...AX, range:[0, 1.02]}}, {displaylogo:false, responsive:true});
  Plotly.react($('pE2'), tr2, {...L0, height:260, title:{text:'kept share against time of day (ET hours, 15-minute bins)', font:{size:12}}, xaxis:{...AX, range:[4, 20]}, yaxis:{...AX, range:[0, 1.02]}}, {displaylogo:false, responsive:true});
}
function drawF(){
  const act = activeConds(); const cnt = new Map(); const alone = {};
  for (let i = 0; i < N; i++){ if (!FAC[i] || STATE[i] !== 1) continue; const b = FIRED[i]; cnt.set(b, (cnt.get(b) || 0) + WT[i]); }
  const name = b => act.filter(x => (b >> x.ix) & 1).map(x => x.c.label).join(' + ') || '(unavailable only)';
  const rows = [...cnt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 25);
  Plotly.react($('pF'), [{type:'bar', orientation:'h', y:rows.map(r => name(r[0])), x:rows.map(r => r[1]), marker:{color:COLF}, text:rows.map(r => fmt(r[1],0)), textposition:'outside'}],
    {...L0, height:Math.max(160, 26 * rows.length + 60), showlegend:false, margin:{l:300, r:40, t:28, b:30}, title:{text:'filtered moment-minutes by the exact set of conditions that fired (largest 25 sets)', font:{size:12}}, xaxis:AX, yaxis:{...AX, autorange:'reversed'}}, {displaylogo:false, responsive:true});
}
// ---------------------------------------------------------------- G
const TABS = ['G1','G2','G3','near the line','random kept','random filtered'];
function poolRows(tab){
  const sm = D.strips.meta;
  if (tab === 'G1' || tab === 'G2' || tab === 'G3') return sm.filter(s => s.pools.includes(tab));
  if (tab === 'random kept') return sm.filter(s => s.pools.includes('random') && STATE[s.row] !== 1);
  if (tab === 'random filtered') return sm.filter(s => s.pools.includes('random') && STATE[s.row] === 1);
  if (!ST.last) return [];
  const c = D.conds.find(x => x.key === ST.last.key); const s = ST.last.seg; const st = ST.cond[c.key]; const th = st.th[s];
  if (th === null || !Number.isFinite(th)) return [];
  const cand = sm.filter(m => A.seg[m.row] === s && Number.isFinite(val(c, m.row))).map(m => ({m, v:val(c, m.row)}));
  const d = x => c.log && x > 0 && th > 0 ? Math.abs(Math.log(x / th)) : Math.abs(x - th);
  const below = cand.filter(x => x.v < th).sort((a, b) => d(a.v) - d(b.v)).slice(0, M.near_k), above = cand.filter(x => x.v >= th).sort((a, b) => d(a.v) - d(b.v)).slice(0, M.near_k);
  return [...below, ...above].map(x => x.m);
}
function badge(i){ const st = STATE[i]; const act = activeConds(); const f = act.filter(x => (FIRED[i] >> x.ix) & 1).map(x => x.c.label).join(', ');
  return st === 1 ? `<span class="pill f">FILTERED</span> ${f}` : (st === 2 ? `<span class="pill r">RESCUED by override</span> ${f}` : `<span class="pill k">KEPT</span>`); }
function caption(i){ const e = A.ev[i]; const mn = minutesOf(A.j[i]);
  return `${EVT.ticker[e]} ${EVT.date[e]} · ${SEGN[A.seg[i]]} · τ+${mn} min · spread ${fmt(A.c_spread_bp[i],1)} bp / ${fmt(A.c_spread_c[i],2)}¢ · trade_rate ${fmt(A.c_trade_rate[i],1)} · n_eff ${fmt(A.c_n_eff[i],1)} · top3 ${fmt(A.c_top3[i],2)} · cost_noise_${ST.cond.cost_noise.h} ${fmt(hval(i),2)} · er(every) ${fmt(A.er_all[i],2)} · leg_s ${fmt(A.o_leg_s[i],2)} · giveback ${fmt(A.o_giveback[i],2)} · act_ratio ${fmt(A.o_act_ratio[i],2)}`; }
function drawStrip(div, s){
  const i = s.row; const sl = (k) => S[k].subarray(s[k][0], s[k][1]); const pt = Array.from(sl('pt'), x => x / 60), pp = Array.from(sl('pp'));
  const qt = Array.from(sl('qt'), x => x / 60), qb = Array.from(sl('qb')), qa = Array.from(sl('qa')), vb = Array.from(sl('vb'));
  const nb = vb.length, w = (s.hi_s - s.lo_s) / nb / 60; const vx = vb.map((_, k) => s.lo_s / 60 + (k + 0.5) * w);
  const tr = [{x:qt, y:qb, mode:'lines', line:{color:'#7bd88f', width:1, shape:'hv'}, name:'bid'}, {x:qt, y:qa, mode:'lines', line:{color:'#ff6b6b', width:1, shape:'hv'}, name:'ask'},
    {x:pt, y:pp, mode:'markers', marker:{size:3, color:'#e6e6e6'}, name:`prints (${s.n_prints}${s.n_prints > pt.length ? ', ' + pt.length + ' shown' : ''})`},
    {x:vx, y:vb, type:'bar', xaxis:'x', yaxis:'y2', marker:{color:'#5b6573'}, name:'volume', width:w}];
  if (s.leg) tr.push({x:[s.leg.lo_t / 60, s.leg.hi_t / 60], y:[s.leg.lo_p, s.leg.hi_p], mode:'markers', marker:{size:9, symbol:['triangle-up','triangle-down'], color:['#ffd479','#ffd479']}, name:'leg low / high'});
  const lay = {...L0, height:300, showlegend:false, margin:{l:48, r:6, t:6, b:30},
    xaxis:{...AX, range:[s.lo_s / 60, s.hi_s / 60], title:{text:'minutes from t', font:{size:10}}, anchor:'y2'}, yaxis:{...AX, domain:[0.3, 1]}, yaxis2:{...AX, domain:[0, 0.24]},
    shapes:[{type:'rect', xref:'x', yref:'paper', x0:0, x1:s.hi_s / 60, y0:0, y1:1, fillcolor:'rgba(255,255,255,0.06)', line:{width:0}}, {type:'line', xref:'x', yref:'paper', x0:0, x1:0, y0:0, y1:1, line:{color:'#ffd479', width:1.5}}],
    annotations:[{x:s.hi_s / 120, y:1, xref:'x', yref:'paper', text:'hindsight', showarrow:false, font:{size:10, color:'#9aa4b2'}}]};
  Plotly.react(div, tr, lay, {displaylogo:false, staticPlot:false, responsive:true});
}
function drawG(){
  const t = $('gTabs'); t.innerHTML = TABS.map(x => `<button class="${x === ST.gtab ? 'on' : ''}">${x}</button>`).join('');
  t.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { ST.gtab = b.textContent; ST.gpage = 0; drawG(); }));
  const rows = poolRows(ST.gtab); const per = 12, pages = Math.max(1, Math.ceil(rows.length / per)); ST.gpage = Math.min(ST.gpage, pages - 1);
  $('gNote').innerHTML = `${M.gallery_label}. G1: ${M.g_rules.G1}. G2: ${M.g_rules.G2}. G3: ${M.g_rules.G3}. Pools fixed at build time (seeded); each strip's state is live. ` +
    (ST.gtab === 'near the line' ? (ST.last ? `Near the line: the ${M.near_k} pooled moments nearest each side of ${ST.last.key} in ${SEGN[ST.last.seg]}.` : 'Move a threshold first.') : '') + ` ${rows.length} strips in this tab.`;
  $('gNav').innerHTML = `<button id="gp">‹ prev</button> page ${ST.gpage + 1} of ${pages} <button id="gn">next ›</button>`;
  $('gp').addEventListener('click', () => { ST.gpage = Math.max(0, ST.gpage - 1); drawG(); }); $('gn').addEventListener('click', () => { ST.gpage = Math.min(pages - 1, ST.gpage + 1); drawG(); });
  const render = (host, list, pinned) => { host.innerHTML = ''; list.forEach(s => { const d = document.createElement('div'); d.className = 'strip' + (pinned ? ' pinned' : '');
    d.innerHTML = `<div class="cap">${badge(s.row)}</div><div class="plot" style="height:300px"></div><div class="cap">${caption(s.row)}</div>`; host.appendChild(d);
    drawStrip(d.querySelector('.plot'), s); d.addEventListener('click', () => { if (ST.pinned.has(s.row)) ST.pinned.delete(s.row); else ST.pinned.add(s.row); drawG(); }); }); };
  render($('gPinned'), D.strips.meta.filter(s => ST.pinned.has(s.row)), true);
  render($('gal'), rows.slice(ST.gpage * per, ST.gpage * per + per), false);
}
// ---------------------------------------------------------------- export
function exportConfig(){
  const segs = {};
  for (let s = 0; s < NS; s++){ segs[SEGN[s]] = {conditions:{}, override:{}};
    for (const c of D.conds){ if (c.key === 'er' && M.er_removed) continue; const st = ST.cond[c.key]; if (!st.on[s]) continue;
      segs[SEGN[s]].conditions[c.label] = {direction:c.dir, threshold: st.th[s] === null ? noFilterValue(c, s) : st.th[s], unit:c.unit, unavailable:st.unav, horizon: c.key === 'cost_noise' ? st.h : undefined, rung: c.key === 'er' ? st.rung : undefined}; }
    for (const o of D.overrides){ const so = ST.ovr[o.key]; if (so.on[s]) segs[SEGN[s]].override[o.label] = {threshold:so.th[s], unit:o.unit}; } }
  const cfg = {created:new Date().toISOString(), suite_config_hash:M.config_hash, data_hash:M.data_hash, sample_fraction:M.sample_fraction, events_embedded:M.events_embedded,
    combination: ST.comb.mode === 'any' ? 'any' : {at_least:ST.comb.m}, segments:segs, er_removed_row3b:M.er_removed,
    viewing:{horizon:ST.view.h, chop_multiple_c:ST.view.c, unit:ST.view.unit, net:ST.view.net, facets:ST.view.fac}};
  const blob = new Blob([JSON.stringify(cfg, null, 2)], {type:'application/json'}); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'chop_filter_config.json'; a.click();
}
// ---------------------------------------------------------------- init
async function init(){
  $('hdrtext').textContent = M.header;
  $('hdrmeta').textContent = `Embedded: ${M.events_embedded.toLocaleString()} of ${M.events_dev.toLocaleString()} development-slice events (sample fraction ${M.sample_fraction}, seeded, stratified by year × τ's segment, whole events) · ${M.moments_embedded.toLocaleString()} non-auction moments · auction-minute moments (not entry moments): ${M.auction_moment_minutes.toLocaleString()} moment-minutes · config ${M.config_hash} · data ${M.data_hash}`;
  const w = []; if (M.er_removed) w.push(`Row 3b: er removed from the conditions — ${M.removed.er}`);
  Object.entries(M.removed).filter(([k]) => k !== 'er').forEach(([k, v]) => w.push(`Row 3b: ${k} removed — ${v}`));
  if (M.row5) w.push(`Row 5 (LOG): embedded sample below 50% of development-slice events`);
  Object.entries(M.row6).forEach(([s, f]) => { if (f) w.push(`Row 6 (LOG): ${s} — ${(100 * M.row6_share[s]).toFixed(1)}% of moment-minutes have no valid scale-free rung`); });
  w.push(`Row 7 (LOG): ${M.row7_events} development-slice events have no quotes (facet "quotes ingested = no")`);
  $('hdrwarn').textContent = w.join(' · ');
  A = await decodeAll(D.arrays); S = await decodeAll(D.strips.arrays); N = A.ev.length;
  EVT = D.events; WT = new Float32Array(N); for (let i = 0; i < N; i++) WT[i] = A.j[i] <= 60 ? 1 : 5;
  const tk = [...new Set(EVT.ticker)]; NT = tk.length; const tix = new Map(tk.map((t, q) => [t, q])); TICK = EVT.ticker.map(t => tix.get(t));
  STATE = new Uint8Array(N); FIRED = new Uint32Array(N); FAC = new Uint8Array(N);
  initState(); buildControls(); computeFacets(); recompute(); drawAll();
}
init();
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
