"""
Chop regime C1, Amendment 3 W3 -- chart_wall.html: 1-minute candles with volume for the wall events, the filter drawn on
every chart as red shading, one control panel that drives every chart, and the suite's config format loaded and exported.

The filter itself is the suite's code: val, hval, recompute, noFilterValue, rangeOf, syncControls and the rest are lifted
by name from t8_suite.PAGE (the source the committed suite was built from), so a setting means the same thing in both
instruments. The round trip is asserted by w4_wall_test.js under node on the real data of both pages (row W-c).

Embedded: the wall events' candles (open, high, low, close, volume per minute, NaN where no print), the 1-minute filter
table's condition, override and er columns (no hindsight value), per-event marks (tau, the crossing level, the XNYS
open and close, halts), the S1 type and the g1 / g2 / g3 bits as viewing labels, and the t6b null bands. The event
count is the longest prefix of W1's seeded stratified order (at most 600) whose page fits 60 MB (row W-d below 300).

Build assertions (rows W-b): every row in the development slice; no A12 column; no hindsight, type or percentile / rank
column among the conditions or the override; no outcome array embedded; the decoded arrays round-trip.

Writes results/chop_regime/c1/suite/chart_wall.html and artifacts/w3_summary.json.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/w3_wall_page.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402
import suite_table as ST  # noqa: E402
import suitedata as SD  # noqa: E402
import t8_suite as T8  # noqa: E402

CFG = C.load_cfg()
A3 = CFG["amendment_3"]
OUT = C.REPO / C.SUITE / "chart_wall.html"
SHARED_JS = ["fmt", "bit", "hval", "val", "ovrVal", "finiteRange", "sliderToVal", "valToSlider", "rangeOf", "initState", "noFilterValue", "unavCount",
             "activeConds", "recompute", "ceilingCells", "syncControls", "minutesOf"]


def extract(page: str, name: str) -> str:
    """One top-level definition from the suite's page source, by brace balance (const RC precedes rangeOf)."""
    if name == "fmt":
        i = page.index("\nconst fmt =")
        return page[i + 1: page.index("\n", i + 1)]
    i = page.index(f"\nfunction {name}(") + 1
    depth, j, started = 0, i, False
    while True:
        ch = page[j]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                break
        j += 1
    src = page[i: j + 1]
    if name == "rangeOf":
        src = "const RC = new Map();\n" + src
    return src


def shared_js() -> str:
    return "\n".join(extract(T8.PAGE, n) for n in SHARED_JS)


def clean(o):
    return T8.clean(o)


def table(m: pd.DataFrame, rungs: pd.DataFrame) -> dict:
    for c in list(ST.CONDITION_SOURCES.values()) + list(ST.OVERRIDE_SOURCES.values()):
        assert not c.startswith(ST.HINDSIGHT_PREFIXES) and not any(z in c.lower() for z in ST.FORBIDDEN) and c not in ("s1_type", "g1", "g2", "g3"), c
    n = len(m)
    tab = {}

    def put(name, arr, dt):
        assert not name.startswith("y_") and not any(z in name.lower() for z in ST.FORBIDDEN), f"{name} may not be embedded"
        tab[name] = SD.encode(np.asarray(arr), dt)

    put("ev", m["_e"].to_numpy(), "u2")
    put("j", m["j"].to_numpy(), "u2")
    put("seg", m["segment"].map({"premarket": 0, "regular": 1, "after_hours": 2}).fillna(3).astype(int).to_numpy(), "u1")
    b = lambda s: s.fillna(False).astype(bool).to_numpy().astype(np.uint16)  # noqa: E731
    fl = (b(m["quote_at_t"]) | b(m["no_print_since_last_moment"]) << 1 | b(m["halt_state"] == "label") << 2 | b(m["halt_state"] == "gap_proxy") << 3
          | b(m["price_basis"] == "vwap_fallback") << 4 | b(m["g1"]) << 5 | b(m["g2"]) << 6 | b(m["g3"]) << 7 | b(m["context_basis"] == "vwap_fallback") << 8
          | (m["tcs_state"].map(ST.TCS).fillna(2).astype(np.uint16).to_numpy() << 9) | b(m["measure_state"] != "ok") << 11)
    put("flags", fl, "u2")
    for k, c in {**ST.CONDITION_SOURCES, **ST.OVERRIDE_SOURCES}.items():
        put(k, m[c].astype(float).to_numpy(), "f4")
    e = rungs.pivot_table(index="moment_uid", columns="k", values="er", aggfunc="first")
    for k in range(7):
        put(f"er_k{k}", m["moment_uid"].map(e[k]) if k in e else np.full(n, np.nan), "f4")
    put("er_all", m["er_allmax"].astype(float).to_numpy(), "f4")
    return tab


def build(E: pd.DataFrame, m: pd.DataFrame, rungs: pd.DataFrame, candles: dict, pop: pd.DataFrame) -> tuple[str, dict]:
    ids = list(E["event_id"])
    eix = {e: i for i, e in enumerate(ids)}
    mm = m[m["event_id"].isin(eix)].assign(_e=lambda d: d["event_id"].map(eix)).sort_values(["_e", "j"]).reset_index(drop=True)
    assert mm["dev_slice"].all() and set(mm["event_id"]) <= set(pop.loc[pop["slice"] == "development", "event_id"]), "a non-development row (W-b)"
    ST.check_cost_noise_scaling(mm)
    tab = table(mm, rungs[rungs["event_id"].isin(eix)])
    cat = {k: [] for k in ("o", "h", "l", "c", "v")}
    co, mo, mn = [], [], []
    off, moff = 0, 0
    cnt = mm.groupby("_e").size()
    g = mm.groupby("_e")[["g1", "g2", "g3"]].any()
    for i, e in enumerate(ids):
        cd = candles[e]
        for k in cat:
            cat[k].append(cd[k])
        co.append(off)
        off += cd["n_min"]
        mo.append(moff)
        mn.append(int(cnt.get(i, 0)))
        moff += mn[-1]
    carr = {k: SD.encode(np.concatenate(v), "f4") for k, v in cat.items()}
    rng = np.random.default_rng(A3["W1_sample"]["seed"] + 1)
    types = ST.TYPES
    ev = {"event_id": ids, "ticker": E["ticker"].tolist(), "date": E["date"].tolist(), "year": E["year"].astype(int).tolist(),
          "tau_seg": [ST.TAU_SEGS.index(s) for s in E["tau_segment"]], "tier": [ST.TIERS.index(t) for t in E["price_tier"]],
          "type": [types.index(t) if isinstance(t, str) else 255 for t in E["s1_type"]], "tau_min": E["tau_min"].round(6).tolist(),
          "tau_price": E["tau_price"].tolist(), "cross": E["cross_level"].tolist(), "open_min": E["open_min"].tolist(), "close_min": E["close_min"].tolist(),
          "m0": E["m0"].astype(int).tolist(), "n_min": E["n_min"].astype(int).tolist(), "co": co, "mo": mo, "mn": mn,
          "halts": [json.loads(h) for h in E["halts"]], "g1": [bool(g.loc[i, "g1"]) if i in g.index else False for i in range(len(ids))],
          "g2": [bool(g.loc[i, "g2"]) if i in g.index else False for i in range(len(ids))], "g3": [bool(g.loc[i, "g3"]) if i in g.index else False for i in range(len(ids))],
          "rand": rng.permutation(len(ids)).tolist(), "in_suite": E["in_suite_sample"].astype(bool).tolist()}
    bands = pd.read_parquet(C.art("t6b_null_bands.parquet"))
    t8 = C.read_json("t8_summary.json")
    data_hash = hashlib.sha256(json.dumps({k: v["b"][:64] + str(v["n"]) for k, v in {**tab, **carr}.items()}, sort_keys=True).encode()).hexdigest()[:12]
    meta = {"header": "Development slice only (2020–22). Thresholds in absolute units, per segment. S1 type and the G flags choose what to show, never conditions. "
                      "Commit before any 2023–24 read. 2025 is sealed. The charts are the evidence; the counts summarise them.",
            "config_hash": C.cfg_hash(), "data_hash": data_hash, "suite_data_hash": t8["data_hash"], "events": len(ids), "events_dev": int((pop["slice"] == "development").sum()),
            "events_in_suite": int(E["in_suite_sample"].sum()), "minutes": int(len(mm)), "segs": list(C.SEGS), "horizons": C.HORIZONS, "wall": C.WALL, "vol": C.VOL,
            "types": types, "tiers": ST.TIERS, "tau_segs": ST.TAU_SEGS, "readability": CFG["suite"]["readability_line"],
            "ceiling": CFG["amendment_2"]["A2_1_ceiling_label"], "er_bucket_line": CFG["amendment_2"]["A2_2_bucket_line"], "er_removed": False,
            "er_note": t8.get("er_note"), "bucket_dependent": {k: v["bucket_dependent"] for k, v in C.read_json("t5_summary.json")["sweep"].items()},
            "opacity": A3["W3_page"]["shading_opacity"], "removed": {}, "h_default": CFG["suite"]["viewing"]["horizon_default"],
            "g_rules": {"G1": "n_eff ≤ 5 and top3_share ≥ 0.6 at the finest rate rung",
                        "G2": "turnover_t < 1%, dollar_flow ≥ $20,000/min at the finest rate rung, and er inside its cell's null 5–95% band at every valid rung 1–4",
                        "G3": "leg_s ≥ 2, 0.1 ≤ giveback ≤ 0.6, and in hindsight the price in (t, t + 60 min] beats the leg high by ≥ the spread at t and ≥ 1 own-noise unit"}}
    D = {"meta": meta, "conds": T8.CONDS, "overrides": T8.OVERRIDES, "events": ev, "arrays": tab, "candles": carr,
         "bands": bands[["segment", "k", "tier", "basis", "null_median", "null_p05", "null_p95", "windows_sampled", "label_few_windows"]].to_dict("records")}
    js = (C.REPO / ".venv/Lib/site-packages/plotly/package_data/plotly.min.js").read_text(encoding="utf-8")
    html = WALL.replace("__DECODER__", SD.JS_DECODER).replace("__SHARED__", shared_js()).replace("__DATA__", json.dumps(clean(D), allow_nan=False))
    html = html.replace("<script>__PLOTLY__</script>", "<script>" + js + "</script>")
    return html, {"data_hash": data_hash, "minutes": int(len(mm)), "table_bytes": SD.size_of(tab), "candle_bytes": SD.size_of(carr)}


def main() -> int:
    t0 = time.perf_counter()
    pop = C.load_population()
    E = pd.read_parquet(C.art("w1_events.parquet")).sort_values("order").reset_index(drop=True)
    m = pd.read_parquet(C.REPO / C.OUT / "cache" / "w2_moments.parquet")
    rungs = pd.read_parquet(C.REPO / C.OUT / "cache" / "w2_er_rungs.parquet")
    candles = {r["event_id"]: r for r in np.load(C.REPO / C.OUT / "cache" / "w1_candles.npy", allow_pickle=True)}
    budget = A3["W3_page"]["size_budget_bytes"]
    n = len(E)
    sizes = {}
    while True:
        html, info = build(E.head(n), m, rungs, candles, pop)
        # base64 has no '_', so the A12 flag's name cannot appear by chance; array names and condition sources are checked in table()
        assert "flag_cross_session_extreme" not in html, "A12 reached the wall (W-b)"
        sizes[n] = len(html.encode("utf-8"))
        if sizes[n] <= budget or n <= 1:
            break
        n = max(1, int(n * budget / sizes[n] * 0.98))          # fewer events; never fewer minutes
    OUT.write_text(html, encoding="utf-8")
    size = OUT.stat().st_size
    assert size <= budget
    summ = {"config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t0, 1), "events": n, "events_built": len(E), "bytes": size,
            "bytes_per_event": round(size / n), "sizes_tried": sizes, "rowWd_fires": n < A3["W1_sample"]["min_events"], **info,
            "shared_js": SHARED_JS, "events_in_suite_sample": int(E.head(n)["in_suite_sample"].sum()),
            "assertions": ["development slice only", "no A12", "no hindsight, type or percentile / rank column in the conditions", "no outcome array embedded",
                           "cost_noise ladder scaling exact"]}
    C.write_json("w3_summary.json", summ)
    print(json.dumps({k: v for k, v in summ.items() if k != "shared_js"}, indent=1))
    return 0


WALL = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chop regime chart wall</title>
<style>
:root{--bg:#111418;--fg:#e6e6e6;--mut:#9aa4b2;--grid:#2a2f36;--card:#171b21;--warn:#ff6b6b}
*{box-sizing:border-box} body{background:var(--bg);color:var(--fg);font:13px/1.4 system-ui,Segoe UI,sans-serif;margin:0}
header{padding:8px 16px;border-bottom:1px solid var(--grid)} header h1{font-size:16px;margin:0 0 2px} .hdr{color:#ffd479;font-weight:600} .sub{color:var(--mut);font-size:12px}
#ctl{position:sticky;top:0;z-index:30;background:#0d1013;border-bottom:1px solid var(--grid);padding:6px 16px;max-height:52vh;overflow:auto}
.row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:3px 0} .conds{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:4px 10px}
.cond{border:1px solid var(--grid);border-radius:5px;padding:3px 6px} .cond.off .ctlz{opacity:.45} .unit{color:var(--mut);font-size:11px} .ceil{color:#ffd479}
input[type=range]{width:140px} input[type=number]{width:88px;background:#1d2229;color:var(--fg);border:1px solid var(--grid);border-radius:3px;padding:2px 4px}
select,button{background:#1d2229;color:var(--fg);border:1px solid var(--grid);border-radius:4px;padding:3px 6px;font-size:12px} button{cursor:pointer} button.on{background:#2b4a7a}
h3{font-size:11px;margin:6px 0 2px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
#counts{padding:6px 16px} table{border-collapse:collapse;font-size:12px} td,th{border-bottom:1px solid var(--grid);padding:2px 8px;text-align:right} th:first-child,td:first-child{text-align:left}
.big{font-size:20px;font-weight:700} .small{font-size:11px;color:var(--mut)} .lt20{color:var(--warn);font-weight:600}
#nav{padding:4px 16px} #grid{display:grid;gap:8px;padding:4px 16px 60px} .chart{background:var(--card);border:1px solid var(--grid);border-radius:6px;padding:4px;cursor:zoom-in}
.cap{font-size:11px;color:var(--mut);padding:2px 4px} .cap b{color:var(--fg)}
#modal{display:none;position:fixed;inset:0;z-index:50;background:rgba(10,12,15,.97);padding:10px 16px;overflow:auto} #modal.open{display:block}
#tip{display:none;position:fixed;z-index:60;pointer-events:none;background:#232a33;border:1px solid #3a434f;border-radius:4px;padding:4px 7px;font-size:11px;max-width:330px}
</style></head><body>
<header><h1>Chop regime filter — C1 chart wall</h1><div class="hdr" id="hdrtext"></div><div class="sub" id="hdrmeta"></div></header>
<div id="ctl"></div><div id="counts"></div><div id="nav"></div><div id="grid"></div>
<div id="modal"><div class="row"><button id="mclose">close (Esc)</button><span class="sub" id="mcap"></span></div><div id="mplot" style="height:78vh"></div><div class="cap" id="mcap2"></div></div><div id="tip"></div>
<script>__PLOTLY__</script>
<script>
__DECODER__
const D = __DATA__;
const M = D.meta, SEGN = M.segs, H = M.horizons, NS = 3;
const $ = id => document.getElementById(id);
const AXC = {gridcolor:'#2a2f36', zeroline:false};
let A, CA, N, WT, EVT, STATE, FIRED;
const ST = {editSeg:1, cond:{}, comb:{mode:'any', m:2}, ovr:{}, last:null, sorted:{}};
const VW = {set:'all', year:'all', tauseg:'all', tier:'all', order:'random', page:0, per:12, cols:2, xr:'tau30', vlog:false, pane:'off', modal:null};
// ---------------------------------------------------------------- the suite's filter code, lifted verbatim (w3_wall_page.SHARED_JS)
__SHARED__
// ---------------------------------------------------------------- config load / export: the suite's JSON
function loadConfig(cfg){
  for (const k in ST.cond){ ST.cond[k].on = [false,false,false]; ST.cond[k].th = [null,null,null]; }
  for (const k in ST.ovr){ ST.ovr[k].on = [false,false,false]; ST.ovr[k].th = [null,null,null]; }
  const byL = {}; D.conds.forEach(c => byL[c.label] = c); const oByL = {}; D.overrides.forEach(o => oByL[o.label] = o);
  ST.comb = cfg.combination === 'any' ? {mode:'any', m:ST.comb.m} : {mode:'m', m:cfg.combination.at_least};
  SEGN.forEach((sn, s) => { const sg = (cfg.segments || {})[sn]; if (!sg) return;
    for (const [lab, v] of Object.entries(sg.conditions || {})){ const c = byL[lab]; if (!c) throw new Error('unknown condition ' + lab); const st = ST.cond[c.key];
      st.on[s] = true; st.th[s] = v.threshold === null ? (c.dir === '>' ? Infinity : -Infinity) : v.threshold; if (v.unavailable) st.unav = v.unavailable;
      if (c.key === 'cost_noise' && v.horizon) st.h = v.horizon; if (c.key === 'er' && v.rung !== undefined) st.rung = v.rung; }
    for (const [lab, v] of Object.entries(sg.override || {})){ const o = oByL[lab]; if (!o) throw new Error('unknown override ' + lab); const so = ST.ovr[o.key];
      so.on[s] = true; so.th[s] = v.threshold === null ? (o.dir === '>=' ? Infinity : -Infinity) : v.threshold; } });
  RC.clear();
}
function configObject(){
  const segs = {};
  for (let s = 0; s < NS; s++){ segs[SEGN[s]] = {conditions:{}, override:{}};
    for (const c of D.conds){ if (c.key === 'er' && M.er_removed) continue; const st = ST.cond[c.key]; if (!st.on[s]) continue;
      segs[SEGN[s]].conditions[c.label] = {direction:c.dir, threshold: st.th[s] === null ? noFilterValue(c, s) : st.th[s], unit:c.unit, unavailable:st.unav, horizon: c.key === 'cost_noise' ? st.h : undefined, rung: c.key === 'er' ? st.rung : undefined}; }
    for (const o of D.overrides){ const so = ST.ovr[o.key]; if (so.on[s]) segs[SEGN[s]].override[o.label] = {threshold:so.th[s], unit:o.unit}; } }
  return {created:new Date().toISOString(), instrument:'chart_wall', suite_config_hash:M.config_hash, data_hash:M.data_hash, events_embedded:M.events,
    combination: ST.comb.mode === 'any' ? 'any' : {at_least:ST.comb.m}, segments:segs, er_removed_row3b:M.er_removed, er_note:M.er_note,
    viewing:{set:VW.set, year:VW.year, tau_segment:VW.tauseg, tier:VW.tier, order:VW.order, x_range:VW.xr, volume_log:VW.vlog, pane:VW.pane}};
}
function exportConfig(){ const blob = new Blob([JSON.stringify(configObject(), null, 2)], {type:'application/json'}); const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'chop_filter_config.json'; a.click(); }
// ---------------------------------------------------------------- controls
function buildControls(){
  let h = `<div class="row"><b>Filter</b> — values for segment:${SEGN.map((s,i)=>`<button data-seg="${i}" class="segb ${i===ST.editSeg?'on':''}">${s}</button>`).join('')}
    <button id="copySeg">copy to the other segments</button> combine <select id="comb"><option value="any">any active condition</option><option value="m">at least m</option></select>
    m <input type="number" id="combm" min="1" value="2" style="width:50px"> <button id="export">export config</button> <label><button id="loadb">load config</button><input type="file" id="loadf" accept=".json" style="display:none"></label>
    <button id="hideCtl">hide / show the filter controls</button> <span class="sub" id="timing"></span></div><div id="ctlbody">`;
  for (const g of [['presence','Presence and cost'],['relative','Relative'],['scale_free','Scale-free']]){
    h += `<h3>${g[1]}</h3><div class="conds">`;
    D.conds.filter(c => c.group === g[0]).forEach(c => {
      h += `<div class="cond" id="cd_${c.key}"><div class="row"><label><input type="checkbox" id="on_${c.key}"> <b>${c.label}</b> ${c.dir} x</label>
        ${c.key==='cost_noise' ? `<select id="h_cost_noise">${H.map(x=>`<option ${x===ST.cond.cost_noise.h?'selected':''}>${x}</option>`).join('')}</select>` : ''}
        ${c.key==='er' ? `<select id="r_er">${['every',0,1,2,3,4,5,6].map(x=>`<option value="${x}" ${String(x)===String(ST.cond.er.rung)?'selected':''}>${x==='every'?'every valid rung':'rung '+x}</option>`).join('')}</select>` : ''}
        <input type="range" min="0" max="1000" id="sl_${c.key}" class="ctlz"><input type="number" step="any" id="nb_${c.key}" class="ctlz"></div>
        <div class="row ctlz unit">${c.unit}${M.bucket_dependent[c.key==='cost_noise' ? 'cost_noise_' + ST.cond.cost_noise.h : (c.key==='er' ? 'er_mid' : c.key)] ? ' · <span class="lt20">bucket-dependent</span>' + (c.key === 'er' ? ' — ' + M.er_bucket_line : '') : ''}</div>
        ${c.key === 'er' ? '<div class="row ctlz unit ceil" id="ceil_er"></div>' : ''}
        <div class="row ctlz unit">unavailable: <select id="un_${c.key}"><option value="filtered">counts as filtered</option><option value="passes">passes</option></select> <span id="uc_${c.key}"></span></div></div>`; });
    h += `</div>`;
  }
  h += `<h3>Pause override (rescues only from relative and scale-free, never from presence and cost)</h3><div class="conds">`;
  D.overrides.forEach(o => { h += `<div class="cond" id="cd_${o.key}"><div class="row"><label><input type="checkbox" id="on_${o.key}"> <b>${o.label}</b> x</label>
    <input type="range" min="0" max="1000" id="sl_${o.key}" class="ctlz"><input type="number" step="any" id="nb_${o.key}" class="ctlz"></div><div class="row unit">${o.unit}</div></div>`; });
  h += `</div></div><div class="row" style="margin-top:6px"><b>Show</b> set <select id="vset"><option value="all">all events</option>${M.types.map((t,i)=>`<option value="t${i}">S1 type: ${t}</option>`).join('')}
    <option value="G1">events with a G1 minute</option><option value="G2">events with a G2 minute</option><option value="G3">events with a G3 minute</option></select>
    year <select id="vyear"><option>all</option>${[...new Set(EVT.year)].sort().map(y=>`<option>${y}</option>`).join('')}</select>
    τ's segment <select id="vtauseg"><option>all</option>${M.tau_segs.map((s,i)=>`<option value="${i}">${s}</option>`).join('')}</select>
    price tier <select id="vtier"><option>all</option>${M.tiers.map((s,i)=>`<option value="${i}">${s}</option>`).join('')}</select>
    order <select id="vorder"><option value="random">seeded random</option><option value="date">date</option><option value="tau">time of τ</option></select>
    page <select id="vper"><option>6</option><option selected>12</option><option>24</option></select> columns <select id="vcols"><option>1</option><option selected>2</option><option>3</option></select>
    x <select id="vxr"><option value="tau30">τ − 30 min → 20:00</option><option value="full">full day</option><option value="tau2h">τ ± 2 h</option></select>
    volume <select id="vlog"><option value="lin">linear</option><option value="log">log</option></select>
    measure pane <select id="vpane"><option value="off">off</option></select></div>`;
  $('ctl').innerHTML = h;
  document.querySelectorAll('.segb').forEach(b => b.addEventListener('click', () => { ST.editSeg = +b.dataset.seg; document.querySelectorAll('.segb').forEach(x => x.classList.toggle('on', +x.dataset.seg === ST.editSeg)); syncControls(); }));
  $('copySeg').addEventListener('click', () => { const s = ST.editSeg; for (const k in ST.cond) for (let t = 0; t < NS; t++){ ST.cond[k].on[t] = ST.cond[k].on[s]; ST.cond[k].th[t] = ST.cond[k].th[s]; } for (const k in ST.ovr) for (let t = 0; t < NS; t++){ ST.ovr[k].on[t] = ST.ovr[k].on[s]; ST.ovr[k].th[t] = ST.ovr[k].th[s]; } syncControls(); schedule(); });
  $('comb').addEventListener('change', e => { ST.comb.mode = e.target.value; schedule(); });
  $('combm').addEventListener('change', e => { ST.comb.m = Math.max(1, +e.target.value || 1); schedule(); });
  $('export').addEventListener('click', exportConfig);
  $('loadb').addEventListener('click', () => $('loadf').click());
  $('loadf').addEventListener('change', e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { loadConfig(JSON.parse(r.result)); syncAll(); schedule(); }; r.readAsText(f); });
  $('hideCtl').addEventListener('click', () => { const b = $('ctlbody'); b.style.display = b.style.display === 'none' ? '' : 'none'; });
  const wire = (c, isO) => {
    const st = isO ? ST.ovr[c.key] : ST.cond[c.key];
    const on = $('on_' + c.key), sl = $('sl_' + c.key), nb = $('nb_' + c.key);
    on.addEventListener('change', () => { const s = ST.editSeg; st.on[s] = on.checked; if (st.on[s] && st.th[s] === null) st.th[s] = noFilterValue(c, s); syncControls(); refreshPane(); schedule(); });
    sl.addEventListener('input', () => { const s = ST.editSeg; const r = rangeOf(c, s); st.th[s] = sliderToVal(c, +sl.value, r); nb.value = Number.isFinite(st.th[s]) ? +st.th[s].toPrecision(6) : ''; schedule(); });
    nb.addEventListener('change', () => { const s = ST.editSeg; st.th[s] = nb.value === '' ? (c.dir === '>' ? Infinity : -Infinity) : +nb.value; syncControls(); schedule(); });
    if (!isO){ const un = $('un_' + c.key); un.value = st.unav; un.addEventListener('change', () => { st.unav = un.value; schedule(); }); }
  };
  D.conds.forEach(c => wire(c, false)); D.overrides.forEach(o => wire(o, true));
  $('h_cost_noise').addEventListener('change', e => { ST.cond.cost_noise.h = e.target.value; for (let s = 0; s < NS; s++) if (ST.cond.cost_noise.th[s] !== null && !ST.cond.cost_noise.on[s]) ST.cond.cost_noise.th[s] = null; syncControls(); schedule(); });
  $('r_er').addEventListener('change', e => { ST.cond.er.rung = e.target.value === 'every' ? 'every' : +e.target.value; syncControls(); schedule(); });
  const vw = (id, f) => $(id).addEventListener('change', e => { f(e.target.value); renderPage(); });
  vw('vset', v => { VW.set = v; VW.page = 0; }); vw('vyear', v => { VW.year = v; VW.page = 0; }); vw('vtauseg', v => { VW.tauseg = v; VW.page = 0; }); vw('vtier', v => { VW.tier = v; VW.page = 0; });
  vw('vorder', v => { VW.order = v; VW.page = 0; }); vw('vper', v => { VW.per = +v; VW.page = 0; }); vw('vcols', v => { VW.cols = +v; }); vw('vxr', v => { VW.xr = v; });
  vw('vlog', v => { VW.vlog = v === 'log'; }); vw('vpane', v => { VW.pane = v; });
  $('mclose').addEventListener('click', closeModal); document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
  syncControls();
}
function syncAll(){
  $('comb').value = ST.comb.mode; $('combm').value = ST.comb.m; $('h_cost_noise').value = ST.cond.cost_noise.h; $('r_er').value = String(ST.cond.er.rung);
  syncControls(); refreshPane();
}
function refreshPane(){
  const act = activeConds().map(x => x.c); const sel = $('vpane'); const cur = VW.pane;
  sel.innerHTML = '<option value="off">off</option>' + act.map(c => `<option value="${c.key}">${c.label}</option>`).join('');
  if (act.some(c => c.key === cur)) sel.value = cur; else { VW.pane = 'off'; sel.value = 'off'; }
}
// ---------------------------------------------------------------- the wall
let timer = null;
function schedule(){ clearTimeout(timer); timer = setTimeout(() => { updateAll(); }, 60); }
function applyFilter(){ recompute(); for (let i = 0; i < N; i++) if (A.seg[i] === 3){ STATE[i] = 3; FIRED[i] = 0; } }
function evList(){
  const out = [];
  for (let e = 0; e < EVT.event_id.length; e++){
    if (VW.set !== 'all'){ if (VW.set[0] === 't'){ if (EVT.type[e] !== +VW.set.slice(1)) continue; } else if (!EVT[VW.set.toLowerCase()][e]) continue; }
    if (VW.year !== 'all' && EVT.year[e] !== +VW.year) continue; if (VW.tauseg !== 'all' && EVT.tau_seg[e] !== +VW.tauseg) continue; if (VW.tier !== 'all' && EVT.tier[e] !== +VW.tier) continue;
    out.push(e); }
  const key = VW.order === 'random' ? (e => EVT.rand[e]) : (VW.order === 'date' ? (e => EVT.date[e] + String(EVT.tau_min[e]).padStart(10, '0')) : (e => EVT.tau_min[e]));
  out.sort((a, b) => { const x = key(a), y = key(b); return x < y ? -1 : (x > y ? 1 : a - b); });
  return out;
}
const hr = m => 4 + m / 60;
const hhmm = m => { const t = Math.floor(240 + m); return String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0'); };
function xrange(e){ const t = hr(EVT.tau_min[e]); if (VW.xr === 'full') return [Math.min(hr(EVT.m0[e]), 9.5), 20]; return VW.xr === 'tau2h' ? [t - 2, Math.min(20, t + 2)] : [t - 0.5, 20]; }
const hhmmss = m => { const s = Math.round((240 + m) * 60); return String(Math.floor(s / 3600)).padStart(2, '0') + ':' + String(Math.floor(s / 60) % 60).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };
function segRanges(e){ return [[4, hr(EVT.open_min[e])], [hr(EVT.open_min[e] + 1), hr(EVT.close_min[e])], [hr(EVT.close_min[e] + 1), 20]]; }
function chartData(e, big){
  const m0 = EVT.m0[e], co = EVT.co[e], nm = EVT.n_min[e];
  const cx = [], o = [], h = [], l = [], c = [], vx = [], vy = [], vc = [];
  for (let k = 0; k < nm; k++){ const x = hr(m0 + k + 0.5); const op = CA.o[co + k]; vx.push(x); vy.push(CA.v[co + k]);
    if (Number.isFinite(op)){ cx.push(x); o.push(op); h.push(CA.h[co + k]); l.push(CA.l[co + k]); c.push(CA.c[co + k]); vc.push(CA.c[co + k] >= op ? '#3fb27f' : '#e5534b'); } else vc.push('#555'); }
  const pane = VW.pane !== 'off';
  const tr = [
    {type:'candlestick', x:cx, open:o, high:h, low:l, close:c, xaxis:'x', yaxis:'y', increasing:{line:{color:'#3fb27f', width:1}}, decreasing:{line:{color:'#e5534b', width:1}}, hoverinfo:'skip', name:'1-min candles'},
    {type:'bar', x:vx, y:vy, xaxis:'x', yaxis:'y2', marker:{color:vc}, hoverinfo:'skip', width:1 / 60, name:'volume'},
    {type:'bar', x:[], y:[], base:[], xaxis:'x', yaxis:'y3', width:1 / 60, marker:{color:`rgba(255,60,60,${M.opacity})`, line:{width:0}}, hoverinfo:'skip', name:'filtered'},
    {type:'bar', x:[], y:[], base:[], xaxis:'x', yaxis:'y3', width:1 / 60, marker:{color:'rgba(255,190,60,0.95)', line:{width:0}}, hoverinfo:'skip', name:'rescued by the override'},
    {type:'bar', x:EVT.halts[e].map(z => hr((z[0] + z[1]) / 2)), y:EVT.halts[e].map(() => 1), base:EVT.halts[e].map(() => 0), width:EVT.halts[e].map(z => Math.max((z[1] - z[0]) / 60, 1 / 120)),
      xaxis:'x', yaxis:'y3', marker:{color:'rgba(200,200,200,0.10)', pattern:{shape:'/', fgcolor:'rgba(220,220,220,0.5)', size:6}, line:{width:0}}, hoverinfo:'skip', name:'halt'},
    {type:'scatter', x:minuteXs(e), y:minuteXs(e).map(() => 0.5), xaxis:'x', yaxis:'y3', mode:'markers', marker:{size:6, opacity:0}, hoverinfo:'none', name:'minute'}];
  const shapes = [], ann = [], t = hr(EVT.tau_min[e]), op = hr(EVT.open_min[e]), cl = hr(EVT.close_min[e]);
  const xr = xrange(e);
  shapes.push({type:'rect', xref:'x', yref:'paper', x0:Math.min(xr[0], hr(m0)), x1:t, y0:0, y1:1, fillcolor:'rgba(160,160,160,0.10)', line:{width:0}});
  ann.push({x:Math.max(xr[0], t - 0.02), y:1, xref:'x', yref:'paper', xanchor:'right', yanchor:'top', text:'before τ — no filter', showarrow:false, font:{size:9, color:'#9aa4b2'}});
  for (const a of [op, cl]) shapes.push({type:'rect', xref:'x', yref:'paper', x0:a, x1:a + 1 / 60, y0:0, y1:1, fillcolor:'rgba(160,160,160,0.35)', line:{width:0}});
  shapes.push({type:'line', xref:'x', yref:'paper', x0:t, x1:t, y0:0, y1:1, line:{color:'#ffd479', width:1.5}});
  for (const a of [op, cl]) shapes.push({type:'line', xref:'x', yref:'paper', x0:a, x1:a, y0:0, y1:1, line:{color:'#9aa4b2', width:1, dash:'dot'}});
  shapes.push({type:'line', xref:'paper', yref:'y', x0:0, x1:1, y0:EVT.cross[e], y1:EVT.cross[e], line:{color:'#c39bff', width:1, dash:'dash'}});
  const lay = {paper_bgcolor:'#171b21', plot_bgcolor:'rgba(0,0,0,0)', font:{color:'#e6e6e6', size:10}, margin:{l:46, r:8, t:6, b:24}, showlegend:false, hovermode:'x', bargap:0,
    height: big ? Math.round(window.innerHeight * 0.76) : (pane ? 380 : 300), dragmode: big ? 'zoom' : false, shapes, annotations:ann,
    xaxis:{...AXC, range:xr, fixedrange:!big, rangeslider:{visible:false}, tickformat:'.2f', title:{text:'hours (ET)', font:{size:9}}},
    yaxis:{...AXC, domain: pane ? [0.46, 1] : [0.3, 1], fixedrange:!big, title:{text:'price', font:{size:9}}},
    yaxis2:{...AXC, domain: pane ? [0, 0.18] : [0, 0.25], fixedrange:!big, type: VW.vlog ? 'log' : 'linear', title:{text:'shares', font:{size:9}}},
    yaxis3:{domain:[0, 1], range:[0, 1], fixedrange:true, visible:false, anchor:'x'}};
  if (pane){ const c = D.conds.find(x => x.key === VW.pane);
    lay.yaxis4 = {...AXC, domain:[0.22, 0.42], fixedrange:!big, type: c && c.log ? 'log' : 'linear', title:{text:c ? c.label : '', font:{size:9}}};
    tr.push({type:'scatter', x:[], y:[], xaxis:'x', yaxis:'y4', mode:'lines', line:{color:'#e6e6e6', width:1}, hoverinfo:'skip', name:'measure'});
    tr.push({type:'scatter', x:[], y:[], xaxis:'x', yaxis:'y4', mode:'lines', line:{color:'#ffd479', width:1.5}, hoverinfo:'skip', name:'threshold'});
    tr.push({type:'scatter', x:[], y:[], xaxis:'x', yaxis:'y4', mode:'lines', line:{width:0}, hoverinfo:'skip', name:'null 95th'});
    tr.push({type:'scatter', x:[], y:[], xaxis:'x', yaxis:'y4', mode:'lines', line:{width:0}, fill:'tonexty', fillcolor:'rgba(150,150,150,0.25)', hoverinfo:'skip', name:'null 5th'}); }
  return {tr, lay};
}
function minuteXs(e){ const mo = EVT.mo[e], base = Math.floor(EVT.tau_min[e]), x = new Array(EVT.mn[e]); for (let q = 0; q < x.length; q++) x[q] = hr(base + A.j[mo + q] + 0.5); return x; }
function eventState(e){            // the shading and the caption's counts; the hover text is built on hover, for one minute
  const mo = EVT.mo[e], mn = EVT.mn[e], base = Math.floor(EVT.tau_min[e]);
  const fx = [], rx = []; let nf = 0, nt = 0; const g = {G1:[0,0], G2:[0,0], G3:[0,0]};
  for (let q = 0; q < mn; q++){ const i = mo + q, s = STATE[i];
    if (s === 1) fx.push(hr(base + A.j[i] + 0.5)); else if (s === 2) rx.push(hr(base + A.j[i] + 0.5));
    if (s !== 3){ nt++; if (s === 1) nf++; const fl = A.flags[i]; if (fl & 32){ g.G1[1]++; if (s === 1) g.G1[0]++; } if (fl & 64){ g.G2[1]++; if (s === 1) g.G2[0]++; } if (fl & 128){ g.G3[1]++; if (s === 1) g.G3[0]++; } }
  }
  return {fx, rx, nf, nt, g};
}
function hoverText(e, q){
  const i = EVT.mo[e] + q, k = A.j[i], base = Math.floor(EVT.tau_min[e]), s = STATE[i], act = activeConds();
  const fired = act.filter(z => (FIRED[i] >> z.ix) & 1).map(z => z.c.label);
  const ci = EVT.co[e] + (base + k - EVT.m0[e]); const inC = ci >= EVT.co[e] && ci < EVT.co[e] + EVT.n_min[e];
  return `${hhmmss(EVT.tau_min[e] + k)} (τ + ${k} min) · ${s === 3 ? 'auction minute' : SEGN[A.seg[i]]} · <b>${s === 1 ? 'FILTERED' : s === 2 ? 'RESCUED' : s === 3 ? 'unavailable' : 'kept'}</b>` +
    (fired.length ? `<br>fired: ${fired.join(', ')}` : '') + act.map(z => `<br>${z.c.label}${z.c.key === 'cost_noise' ? '_' + ST.cond.cost_noise.h : ''} ${fmt(val(z.c, i), 3)}`).join('') +
    `<br>close ${fmt(inC ? CA.c[ci] : NaN, 4)} · volume ${fmt(inC ? CA.v[ci] : NaN, 0)}`;
}
function wireHover(div, e){
  if (typeof div.on !== 'function') return;
  div.on('plotly_hover', d => { const p = (d.points || []).find(z => z.curveNumber === 5); if (!p) return; const tip = $('tip'); tip.innerHTML = hoverText(e, p.pointIndex);
    const ev = d.event || {}; tip.style.left = Math.min((ev.clientX || 0) + 14, window.innerWidth - 340) + 'px'; tip.style.top = ((ev.clientY || 0) + 14) + 'px'; tip.style.display = 'block'; });
  div.on('plotly_unhover', () => { $('tip').style.display = 'none'; });
}
function caption(e, es){
  const tsn = M.tau_segs[EVT.tau_seg[e]], ty = EVT.type[e] === 255 ? 'untyped' : M.types[EVT.type[e]];
  const c = x => x < M.readability ? `<span class="lt20">${x}</span>` : x;
  return `${EVT.ticker[e]} ${EVT.date[e]} · τ ${hhmm(EVT.tau_min[e])} (${tsn}) · ${M.tiers[EVT.tier[e]]} · S1 type ${ty} · filtered ${es.nt ? (100 * es.nf / es.nt).toFixed(1) : '—'}% of ${es.nt} post-τ minutes · G1 filtered ${c(es.g.G1[0])} of ${c(es.g.G1[1])} · G2 filtered ${c(es.g.G2[0])} of ${c(es.g.G2[1])} · <b>pauses filtered ${c(es.g.G3[0])} of ${c(es.g.G3[1])}</b>`;
}
function paneData(e){
  const c = D.conds.find(x => x.key === VW.pane); if (!c) return null;
  const mo = EVT.mo[e], mn = EVT.mn[e], base = Math.floor(EVT.tau_min[e]); const x = [], y = [];
  for (let q = 0; q < mn; q++){ const i = mo + q; if (A.seg[i] === 3) { x.push(null); y.push(null); continue; } x.push(hr(base + A.j[i] + 0.5)); const v = val(c, i); y.push(Number.isFinite(v) ? v : null); }
  const sr = segRanges(e), tx = [], ty = [], bx = [], b95 = [], b05 = []; const st = ST.cond[c.key];
  for (let s = 0; s < NS; s++){ if (!st.on[s]) continue; const th = st.th[s] === null ? noFilterValue(c, s) : st.th[s]; if (!Number.isFinite(th)) continue; tx.push(sr[s][0], sr[s][1], null); ty.push(th, th, null); }
  if (c.key === 'er' && ST.cond.er.rung !== 'every'){ const rung = +ST.cond.er.rung;     // a band belongs to one rung; none is drawn for 'every valid rung'
    for (let s = 0; s < NS; s++){ const b = D.bands.find(r => r.segment === SEGN[s] && r.k === rung && r.tier === M.tiers[EVT.tier[e]] && r.basis === 'mid'); if (!b) continue;
      bx.push(sr[s][0], sr[s][1], null); b95.push(b.null_p95, b.null_p95, null); b05.push(b.null_p05, b.null_p05, null); } }
  return {x, y, tx, ty, bx, b95, b05};
}
const VIS = new Map();   // div -> event index (the page's charts and the open modal)
function shade(div, e){
  const es = eventState(e);
  const upd = {x:[es.fx, es.rx], y:[es.fx.map(() => 1), es.rx.map(() => 0.035)], base:[es.fx.map(() => 0), es.rx.map(() => 0.965)]};
  const p = [Plotly.restyle(div, upd, [2, 3])];
  if (VW.pane !== 'off'){ const pd = paneData(e); if (pd) p.push(Plotly.restyle(div, {x:[pd.x, pd.tx, pd.bx, pd.bx], y:[pd.y, pd.ty, pd.b95, pd.b05]}, [6, 7, 8, 9])); }
  const cap = div.parentNode && div.parentNode.querySelector ? div.parentNode.querySelector('.cap') : null; if (cap) cap.innerHTML = caption(e, es);
  if (VW.modal === e && div === $('mplot')) $('mcap2').innerHTML = caption(e, es);
  return Promise.all(p);
}
function renderPage(){
  const list = evList(); const pages = Math.max(1, Math.ceil(list.length / VW.per)); VW.page = Math.min(VW.page, pages - 1);
  const show = list.slice(VW.page * VW.per, VW.page * VW.per + VW.per);
  $('nav').innerHTML = `<div class="row"><button id="pp">‹ previous</button> page ${VW.page + 1} of ${pages} · ${list.length} events in this set (of ${M.events}) <button id="pn">next ›</button></div>`;
  $('pp').addEventListener('click', () => { VW.page = Math.max(0, VW.page - 1); renderPage(); }); $('pn').addEventListener('click', () => { VW.page = Math.min(pages - 1, VW.page + 1); renderPage(); });
  const grid = $('grid'); grid.style.gridTemplateColumns = `repeat(${VW.cols}, minmax(0, 1fr))`; grid.innerHTML = '';
  for (const k of [...VIS.keys()]) if (k !== $('mplot')) VIS.delete(k);
  const proms = [];
  for (const e of show){ const box = document.createElement('div'); box.className = 'chart'; box.innerHTML = '<div class="plot"></div><div class="cap"></div>'; grid.appendChild(box);
    const div = box.querySelector('.plot'); const cd = chartData(e, false); proms.push(Plotly.newPlot(div, cd.tr, cd.lay, {displaylogo:false, responsive:true, displayModeBar:false}).then(() => { wireHover(div, e); return shade(div, e); }));
    VIS.set(div, e); box.addEventListener('click', () => openModal(e)); }
  if (VW.modal !== null) openModal(VW.modal);
  return Promise.all(proms);
}
function openModal(e){ VW.modal = e; $('modal').classList.add('open'); const div = $('mplot'); const cd = chartData(e, true); VIS.set(div, e);
  $('mcap').textContent = 'drag to zoom, double-click to reset; every control still applies';
  return Plotly.newPlot(div, cd.tr, cd.lay, {displaylogo:false, responsive:true, scrollZoom:true}).then(() => { wireHover(div, e); return shade(div, e); }); }
function closeModal(){ VW.modal = null; $('modal').classList.remove('open'); VIS.delete($('mplot')); }
function drawCounts(){
  const kept = [0,0,0], filt = [0,0,0], g = {G1:[[0,0],[0,0],[0,0]], G2:[[0,0],[0,0],[0,0]], G3:[[0,0],[0,0],[0,0]]};
  for (let i = 0; i < N; i++){ const s = A.seg[i]; if (s === 3) continue; const f = STATE[i] === 1; if (f) filt[s]++; else kept[s]++;
    const fl = A.flags[i]; for (const [gn, b] of [['G1',5],['G2',6],['G3',7]]) if (bit(fl, b)){ g[gn][s][1]++; if (f) g[gn][s][0]++; } }
  const c = x => `<span class="${x < M.readability ? 'lt20' : ''}">${x.toLocaleString()}${x < M.readability ? ' (&lt;20)' : ''}</span>`;
  const tot = a => a.reduce((p, q) => p + q, 0); const row = (lab, per, all, big) => `<tr><td>${lab}</td>${per.map(x => `<td class="${big ? 'big' : ''}">${x}</td>`).join('')}<td class="small">${all}</td></tr>`;
  let h = `<table><tr><th>all ${M.events} wall events (not just this page)</th>${SEGN.map(s => `<th>${s}</th>`).join('')}<th class="small">all segments (pooled)</th></tr>`;
  h += row('G3 pauses filtered (minutes)', g.G3.map(x => `${c(x[0])} of ${c(x[1])}`), `${c(tot(g.G3.map(x => x[0])))} of ${c(tot(g.G3.map(x => x[1])))}`, true);
  h += row('G1 low-volume pops filtered', g.G1.map(x => `${c(x[0])} of ${c(x[1])}`), `${c(tot(g.G1.map(x => x[0])))} of ${c(tot(g.G1.map(x => x[1])))}`, false);
  h += row('G2 higher-float noise filtered', g.G2.map(x => `${c(x[0])} of ${c(x[1])}`), `${c(tot(g.G2.map(x => x[0])))} of ${c(tot(g.G2.map(x => x[1])))}`, false);
  h += row('minutes filtered', filt.map(c), c(tot(filt)), false); h += row('minutes kept', kept.map(c), c(tot(kept)), false);
  $('counts').innerHTML = h + `</table><div class="small">Counts on the wall's own sample; the suite's counts, on its sample, stay authoritative for anything committed. Red = under ${M.readability}.</div>`;
}
function updateAll(){
  const t0 = performance.now(); applyFilter(); drawCounts();
  const proms = []; for (const [div, e] of VIS) proms.push(shade(div, e));
  return Promise.all(proms).then(() => { const ms = performance.now() - t0; window.__lastRedrawMs = ms; $('timing').textContent = `redraw ${ms.toFixed(0)} ms for ${VIS.size} charts`; return ms; });
}
async function selftest(){
  // headless timing for row W-e: switch on four conditions at mid-slider in every segment, redraw five times
  const keys = ['c_spread_bp', 'c_trade_rate', 'cost_noise', 'er']; const out = [];
  for (const k of keys){ const c = D.conds.find(x => x.key === k); for (let s = 0; s < NS; s++){ ST.cond[k].on[s] = true; ST.cond[k].th[s] = sliderToVal(c, 500, rangeOf(c, s)); } }
  const paint = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  await updateAll(); await paint();
  for (let r = 0; r < 5; r++){ const c = D.conds.find(x => x.key === 'c_spread_bp'); for (let s = 0; s < NS; s++) ST.cond.c_spread_bp.th[s] = sliderToVal(c, 300 + 100 * r, rangeOf(c, s));
    const t0 = performance.now(); await updateAll(); await paint(); out.push(performance.now() - t0); }     // recompute + counts + restyle of every chart + two frames
  out.sort((a, b) => a - b);
  const part = {}; let t = performance.now(); applyFilter(); part.recompute = performance.now() - t; t = performance.now(); drawCounts(); part.counts = performance.now() - t;
  t = performance.now(); for (const [div, e] of VIS) eventState(e); part.event_state = performance.now() - t;
  t = performance.now(); for (const [div, e] of VIS) for (let q = 0; q < EVT.mn[e]; q++) hoverText(e, q); part.hover_text_every_minute_not_on_redraw = performance.now() - t;
  t = performance.now(); await Promise.all([...VIS].map(([div, e]) => shade(div, e))); await paint(); part.shade_and_paint = performance.now() - t;
  window.__selftest = {charts:VIS.size, ms:out, median:out[2], max:out[4], parts_ms:part};
}
async function init(){
  $('hdrtext').textContent = M.header;
  $('hdrmeta').textContent = `${M.events} of ${M.events_dev.toLocaleString()} development-slice events (seeded, stratified by year × τ's segment; ${M.events_in_suite} also in the suite's sample) · ${M.minutes.toLocaleString()} filter minutes from τ to 20:00 · config ${M.config_hash} · data ${M.data_hash} · ` +
    (M.er_note ? M.er_note + ' · ' : '') + `S1 type and the G flags are viewing labels only. The filter state at t = τ + j min (measures to t, none after) shades the candle that contains t.`;
  A = await decodeAll(D.arrays); CA = await decodeAll(D.candles); N = A.ev.length; EVT = D.events; WT = new Float32Array(N).fill(1);
  STATE = new Uint8Array(N); FIRED = new Uint32Array(N);
  initState(); buildControls(); applyFilter(); drawCounts(); await renderPage();
  if (typeof location !== 'undefined' && /selftest/.test(location.search)) await selftest();
}
init();
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
