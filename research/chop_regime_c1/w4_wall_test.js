// Chop regime C1, Amendment 3 W4 -- the chart wall's JavaScript run under node on the real data, and the config round trip
// with the suite (row W-c).
//
// Page test (stub DOM, recording Plotly stub that applies restyles to the stored traces): decodes the embedded data; checks
// that nothing is filtered or shaded on load with every condition off; switches every condition and override on, moves
// thresholds, the combination rule, the cost_noise horizon, the er rung and the unavailable choices; walks every viewing
// control (set, year, tau's segment, tier, order, page size, columns, x range, volume scale, measure pane, next / previous,
// the full-width view); exports and loads; switches everything off and checks again that nothing is shaded. Fails on any
// exception or on a non-finite number in a trace where Plotly needs a finite one. Prints no filter count and no outcome.
//
// Round trip: the suite page (unchanged) and the wall run in two contexts. On every (event, t) both pages carry -- suite
// moment (event, minutesOf(j)), wall minute (event, j), auction moments excluded by both -- the embedded condition values are
// compared first, then 25 seeded settings are made in the suite's code, exported by the suite's own exportConfig, loaded
// into the wall, and 25 made in the wall, exported by the wall, loaded into the suite's code (the wall's loader injected,
// the suite has no Load button). After each, the filter state and the fired-condition bits must agree on every shared
// minute, and the config re-exported after the load must be the text that was loaded.
//
// Usage: node research/chop_regime_c1/w4_wall_test.js <chart_wall.html> <chop_suite.html> <seed>
const fs = require('fs'), vm = require('vm');
const [wallPath, suitePath, seedArg] = process.argv.slice(2);
const SEED = +seedArg;
const wait = ms => new Promise(r => setTimeout(r, ms));
const T0 = Date.now(); const step = n => console.error(`[${((Date.now() - T0) / 1000).toFixed(1)} s] ${n}`);
const lastScript = html => { const s = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]); return s[s.length - 1]; };

function makeDom(){
  const els = new Map();
  function el(id){
    const q = new Map();
    const e = {id, innerHTML:'', textContent:'', value:'', checked:false, style:{}, dataset:{}, children:[], listeners:{}, parentNode:null,
      classList:{toggle(){}, add(){}, remove(){}}, addEventListener(t, f){ (this.listeners[t] = this.listeners[t] || []).push(f); },
      fire(t){ (this.listeners[t] || []).forEach(f => f({target:this, key:'x'})); }, appendChild(c){ this.children.push(c); c.parentNode = this; return c; },
      querySelectorAll(){ return []; }, querySelector(sel){ if (!q.has(sel)){ const c = el(id + ' ' + sel); c.parentNode = e; q.set(sel, c); } return q.get(sel); }, click(){}};
    return e;
  }
  const document = {getElementById(id){ if (!els.has(id)) els.set(id, el(id)); return els.get(id); }, createElement(){ return el('_c' + Math.random()); },
    querySelectorAll(){ return []; }, addEventListener(){}};
  return document;
}
const bad = [];
function checkFinite(tag, tr){ for (const k of ['x', 'y', 'open', 'high', 'low', 'close', 'base']) if (Array.isArray(tr[k])) for (const v of tr[k]) if (v !== null && typeof v === 'number' && !Number.isFinite(v)){ bad.push([tag, k, v]); return; } }
const CAP = {text:null};
class CaptureBlob { constructor(parts){ CAP.text = parts.join(''); } }
function context(doc, plotly){
  const ctx = {document:doc, Plotly:plotly, console, fetch, Response, Blob, DecompressionStream, setTimeout, clearTimeout, URL:{createObjectURL(){ return 'blob:x'; }},
    performance, window:{innerHeight:900}, Float32Array, Float64Array, Uint8Array, Uint16Array, Uint32Array, Int32Array, Math, JSON, Map, Set, Promise, Number, Array,
    Object, String, Date, Infinity, NaN};
  vm.createContext(ctx);
  return ctx;
}
// the wall's Plotly stub keeps each chart's traces and applies restyles, so the shading on every chart can be read back
const wallPlots = [];
const WallPlotly = {
  newPlot(div, tr, lay){ div.__tr = tr.map(t => ({...t})); div.__lay = lay; wallPlots.push(div); tr.forEach(t => checkFinite('newPlot', t)); return Promise.resolve(div); },
  restyle(div, upd, idx){ idx.forEach((ti, q) => { for (const k in upd){ const v = upd[k][q]; if (v === null) delete div.__tr[ti][k]; else div.__tr[ti][k] = v; } checkFinite('restyle', div.__tr[ti]); });
    return Promise.resolve(div); }, react(){ return Promise.resolve(); }, purge(){}};
const SuitePlotly = {react(div, tr){ tr.forEach(t => checkFinite('suite', t)); }, newPlot(){}, purge(){}};
const RNG_SRC = `
function __mul(a){ return function(){ a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function __gen(seed){                                   // one seeded setting, made with this page's own ranges and slider mapping
  const R = __mul(seed);
  for (const k in ST.cond){ ST.cond[k].on = [false,false,false]; ST.cond[k].th = [null,null,null]; }
  for (const k in ST.ovr){ ST.ovr[k].on = [false,false,false]; ST.ovr[k].th = [null,null,null]; }
  ST.cond.cost_noise.h = M.horizons[Math.floor(R() * M.horizons.length)];
  ST.cond.er.rung = ['every', 0, 1, 2, 3, 4, 5, 6][Math.floor(R() * 8)];
  ST.comb = R() < 0.6 ? {mode:'any', m:2} : {mode:'m', m:1 + Math.floor(R() * 3)};
  RC.clear();
  for (const c of D.conds){ if (c.key === 'er' && M.er_removed) continue; ST.cond[c.key].unav = R() < 0.5 ? 'filtered' : 'passes';
    for (let s = 0; s < NS; s++){ if (R() >= 0.3) continue; ST.cond[c.key].on[s] = true; const u = R();
      ST.cond[c.key].th[s] = u < 0.1 ? null : (u < 0.15 ? (c.dir === '>' ? Infinity : -Infinity) : sliderToVal(c, Math.floor(R() * 1001), rangeOf(c, s))); } }
  for (const o of D.overrides) for (let s = 0; s < NS; s++){ if (R() >= 0.35) continue; ST.ovr[o.key].on[s] = true;
    ST.ovr[o.key].th[s] = R() < 0.15 ? noFilterValue(o, s) : sliderToVal(o, Math.floor(R() * 1001), rangeOf(o, s)); }
}`;
function extractFn(src, name){
  const i = src.indexOf('\nfunction ' + name + '(') + 1; if (i <= 0) throw new Error('no ' + name);
  let d = 0, j = i, started = false;
  for (;; j++){ const ch = src[j]; if (ch === '{'){ d++; started = true; } else if (ch === '}'){ d--; if (started && d === 0) break; } }
  return src.slice(i, j + 1);
}
const out = {page:{}, round_trip:{}};
(async () => {
  const wallApp = lastScript(fs.readFileSync(wallPath, 'utf8')), suiteApp = lastScript(fs.readFileSync(suitePath, 'utf8'));
  const wdoc = makeDom(), W = context(wdoc, WallPlotly);
  vm.runInContext(wallApp.replace(/\ninit\(\);\s*$/, '\n'), W);
  let t0 = Date.now(); await vm.runInContext('init()', W);
  const $ = id => wdoc.getElementById(id);
  const ev = (code) => vm.runInContext(code, W);
  step('wall init done');
  out.page.init_ms = Date.now() - t0;
  out.page.rows = ev('N'); out.page.events = ev('EVT.event_id.length'); out.page.charts_on_load = ev('VIS.size');
  const shadedCharts = () => [...ev('[...VIS.keys()]')].filter(d => (d.__tr[2].x || []).length || (d.__tr[3].x || []).length).length;
  out.page.filtered_on_load = ev('[...STATE].filter(v => v === 1 || v === 2).length');
  out.page.shaded_charts_on_load = shadedCharts();
  out.page.hover_points_on_load = ev('[...VIS.keys()]').reduce((a, d) => a + (d.__tr[5].x || []).length, 0) > 0;
  step('on-load checks done');
  // every condition and override on, thresholds moved, in every segment
  const conds = ev('D.conds.map(c => c.key)'), ovrs = ev('D.overrides.map(o => o.key)');
  for (const k of conds){ $('on_' + k).checked = true; $('on_' + k).fire('change'); $('sl_' + k).value = 500; $('sl_' + k).fire('input'); $('un_' + k).value = 'filtered'; $('un_' + k).fire('change'); }
  for (const k of ovrs){ $('on_' + k).checked = true; $('on_' + k).fire('change'); $('sl_' + k).value = 400; $('sl_' + k).fire('input'); }
  $('copySeg').fire('click');
  $('nb_c_spread_bp').value = '120'; $('nb_c_spread_bp').fire('change');
  $('comb').value = 'm'; $('comb').fire('change'); $('combm').value = 2; $('combm').fire('change');
  for (const h of ['w15', 'v1', 'w5']){ $('h_cost_noise').value = h; $('h_cost_noise').fire('change'); }
  for (const r of ['3', 'every', '1']){ $('r_er').value = r; $('r_er').fire('change'); }
  await wait(200); await ev('updateAll()');
  step('conditions on');
  out.page.filter_computed_all_on = ev('[...STATE].every(v => v <= 3)');
  out.page.shading_traces_written = ev('[...VIS.keys()]').every(d => Array.isArray(d.__tr[2].x) && Array.isArray(d.__tr[3].x));
  const opts = {vset:['t0','t1','t2','t3','t4','t5','G1','G2','G3','all'], vyear:['2020','2021','2022','all'], vtauseg:['0','2','4','all'], vtier:['0','3','all'],
    vorder:['date','tau','random'], vper:['6','24','12'], vcols:['1','3','2'], vxr:['full','tau2h','tau30'], vlog:['log','lin']};
  for (const [id, vs] of Object.entries(opts)) for (const v of vs){ $(id).value = v; $(id).fire('change'); await wait(0); }
  step('viewing controls walked');
  for (const p of [...conds, 'off']){ $('vpane').value = p; $('vpane').fire('change'); await wait(0); }
  $('vpane').value = 'er'; $('vpane').fire('change'); await wait(0);
  $('pn').fire('click'); $('pn').fire('click'); $('pp').fire('click'); await wait(0);
  await ev('openModal(evList()[0])'); $('sl_c_trade_rate').value = 700; $('sl_c_trade_rate').fire('input'); await wait(200); await ev('closeModal()');
  out.page.viewing_controls_walked = Object.keys(opts).length + 3;
  step('modal done');
  W.Blob = CaptureBlob; $('export').fire('click'); const exported = CAP.text;
  ev(`loadConfig(${exported}); syncAll();`); await ev('updateAll()');
  out.page.export_load_reexport_identical = JSON.stringify(JSON.parse(exported).segments) === JSON.stringify(ev('configObject()').segments);
  step('export / load done');
  // everything off: nothing filtered, nothing shaded
  for (const k of [...conds, ...ovrs]) for (let s = 0; s < 3; s++){ ev(`ST.editSeg = ${s}; syncControls();`); $('on_' + k).checked = false; $('on_' + k).fire('change'); }
  await wait(200); await ev('updateAll()');
  out.page.filtered_all_off = ev('[...STATE].filter(v => v === 1 || v === 2).length');
  out.page.shaded_charts_all_off = shadedCharts();
  out.page.plot_calls = wallPlots.length;

  step('page test done');
  // ---------------- round trip with the suite
  const sdoc = makeDom(), S = context(sdoc, SuitePlotly);
  vm.runInContext(suiteApp.replace(/\ninit\(\);\s*$/, '\n'), S);
  t0 = Date.now(); await vm.runInContext('init()', S); out.round_trip.suite_init_ms = Date.now() - t0;
  step('suite init done');
  const es = c => vm.runInContext(c, S);
  vm.runInContext(RNG_SRC, S); vm.runInContext(RNG_SRC, W);
  vm.runInContext(extractFn(wallApp, 'loadConfig'), S);           // the wall's loader, injected into the suite's context
  S.Blob = CaptureBlob;
  const sKey = es('(() => { const k = new Map(); for (let i = 0; i < N; i++) k.set(EVT.event_id[A.ev[i]] + "|" + minutesOf(A.j[i]), i); return k; })()');
  const pairs = [];
  ev('(() => { const r = []; for (let i = 0; i < N; i++) if (A.seg[i] !== 3) r.push([EVT.event_id[A.ev[i]] + "|" + A.j[i], i]); return r; })()').forEach(([k, i]) => { if (sKey.has(k)) pairs.push([sKey.get(k), i]); });
  out.round_trip.shared_minutes = pairs.length;
  { const sev = es('EVT.event_id'), sA = es('A'); out.round_trip.shared_events = new Set(pairs.map(([si]) => sev[sA.ev[si]])).size; }
  // the embedded condition values and segments on the shared minutes
  const arrays = ev('Object.keys(A)').filter(k => /^(c_|o_|er_)/.test(k));
  step('shared minutes mapped');
  const SA = es('A'), WA = ev('A');
  const diff = {};
  for (const k of [...arrays, 'seg']){ let n = 0; const a = SA[k], b = WA[k];
    for (const [si, wi] of pairs){ const x = a[si], y = b[wi]; if (!(x === y || (Number.isNaN(x) && Number.isNaN(y)))) n++; } diff[k] = n; }
  out.round_trip.value_mismatches = diff;
  step('values compared');
  const compare = () => { const ss = es('STATE'), sf = es('FIRED'), ws = ev('STATE'), wf = ev('FIRED'); let n = 0, f = 0;
    for (const [si, wi] of pairs){ if (ss[si] !== ws[wi] || sf[si] !== wf[wi]) n++; if (ws[wi] === 1) f++; } return {mismatch:n, any_filtered:f > 0}; };
  const res = {suite_to_wall:[], wall_to_suite:[]};
  for (let r = 0; r < 25; r++){
    es(`__gen(${SEED + r}); syncControls(); recompute();`); CAP.text = null; es('exportConfig()'); const txt = CAP.text;
    ev(`loadConfig(${txt}); applyFilter();`);
    const c = compare(); c.reexport_identical = JSON.stringify(JSON.parse(txt).segments) === JSON.stringify(ev('configObject()').segments)
      && JSON.stringify(JSON.parse(txt).combination) === JSON.stringify(ev('configObject()').combination);
    res.suite_to_wall.push(c);
  }
  step('suite -> wall done');
  for (let r = 0; r < 25; r++){
    ev(`__gen(${SEED + 1000 + r}); applyFilter();`); CAP.text = null; W.Blob = CaptureBlob; ev('exportConfig()'); const txt = CAP.text;
    es(`loadConfig(${txt}); recompute();`);
    const c = compare(); CAP.text = null; es('exportConfig()'); const back = JSON.parse(CAP.text), sent = JSON.parse(txt);   // the suite's own export
    c.reexport_identical = JSON.stringify(sent.segments) === JSON.stringify(back.segments) && JSON.stringify(sent.combination) === JSON.stringify(back.combination);
    res.wall_to_suite.push(c);
  }
  step('wall -> suite done');
  for (const k of ['suite_to_wall', 'wall_to_suite']){ const a = res[k];
    out.round_trip[k] = {configs:a.length, configs_with_mismatch:a.filter(x => x.mismatch).length, minutes_mismatched:a.reduce((s, x) => s + x.mismatch, 0),
      configs_filtering_some_shared_minute:a.filter(x => x.any_filtered).length, reexport_identical:a.every(x => x.reexport_identical)}; }
  out.non_finite_plotted = bad.length; out.non_finite_examples = bad.slice(0, 3);
  const ok = out.page.filtered_on_load === 0 && out.page.shaded_charts_on_load === 0 && out.page.filtered_all_off === 0 && out.page.shaded_charts_all_off === 0
    && out.page.export_load_reexport_identical && bad.length === 0;
  const rt = Object.values(diff).every(v => v === 0) && out.round_trip.suite_to_wall.minutes_mismatched === 0 && out.round_trip.wall_to_suite.minutes_mismatched === 0
    && out.round_trip.suite_to_wall.reexport_identical && out.round_trip.wall_to_suite.reexport_identical && pairs.length > 0;
  out.page_test_pass = ok; out.round_trip_pass = rt;
  console.log(JSON.stringify(out));
  process.exit(ok && rt ? 0 : 1);
})().catch(e => { console.error('PAGE ERROR', e && e.stack || e); process.exit(2); });
