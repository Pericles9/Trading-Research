// Chop regime C1, T8 -- the suite page's JavaScript run under node with a stub DOM and a recording Plotly stub.
// Decodes the real embedded data (DecompressionStream, fetch of a data: URL), switches conditions on, moves thresholds,
// turns the override and the combination rule on, changes every viewing control and facet, presses the noise-band and
// bootstrap buttons, walks every gallery tab and exports. Fails on any exception or on a trace carrying a non-finite
// number where Plotly needs a finite one.
//
// Usage: node research/chop_regime_c1/t8_page_test.js results/chop_regime/c1/suite/chop_suite.html
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const app = scripts[scripts.length - 1];
const els = new Map();
function el(id){
  const e = {id, innerHTML:'', textContent:'', value:'', checked:false, style:{}, dataset:{}, children:[], listeners:{},
    classList:{toggle(){}, add(){}, remove(){}}, addEventListener(t, f){ (this.listeners[t] = this.listeners[t] || []).push(f); },
    fire(t){ (this.listeners[t] || []).forEach(f => f({target:this})); }, appendChild(c){ this.children.push(c); return c; },
    querySelectorAll(){ return []; }, querySelector(){ return el('_q' + Math.random()); }, click(){}};
  return e;
}
const document = {getElementById(id){ if (!els.has(id)) els.set(id, el(id)); return els.get(id); }, createElement(){ return el('_c' + Math.random()); }};
const calls = []; let bad = [];
const Plotly = {react(div, tr, lay){ calls.push(tr.length); for (const t of tr) for (const k of ['x','y']) if (Array.isArray(t[k])) t[k].forEach(v => { if (v !== null && typeof v === 'number' && !Number.isFinite(v)) bad.push([lay && lay.title && lay.title.text, k, v]); }); },
  newPlot(){}, purge(){}};
const ctx = {document, Plotly, console, fetch, Response, Blob, DecompressionStream, setTimeout, clearTimeout, URL:{createObjectURL(){ return 'blob:x'; }},
  Float32Array, Float64Array, Uint8Array, Uint16Array, Uint32Array, Int32Array, Math, JSON, Map, Set, Promise, Number, Array, Object, String, Date, Infinity, NaN};
vm.createContext(ctx);
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  vm.runInContext(app.replace(/\ninit\(\);\s*$/, '\n'), ctx);
  const t0 = Date.now();
  await vm.runInContext('init()', ctx);
  console.log('init', Date.now() - t0, 'ms; rows', vm.runInContext('N', ctx), 'plots', calls.length);
  const $ = id => document.getElementById(id);
  const conds = vm.runInContext('D.conds.map(c => c.key)', ctx);
  for (const k of conds){ const on = $('on_' + k); if (!on.listeners.change) continue; on.checked = true; on.fire('change'); const sl = $('sl_' + k); sl.value = 500; sl.fire('input'); }
  for (const k of ['o_leg_s','o_giveback','o_act_ratio']){ const on = $('on_' + k); on.checked = true; on.fire('change'); const sl = $('sl_' + k); sl.value = 400; sl.fire('input'); }
  await wait(300);
  const st = vm.runInContext('[...STATE].reduce((a, v) => (a[v] = (a[v] || 0) + 1, a), {})', ctx);
  console.log('states after all conditions on at mid-slider', JSON.stringify(st));
  $('comb').value = 'm'; $('comb').fire('change'); $('combm').value = 2; $('combm').fire('change'); await wait(300);
  for (const [id, v] of [['vh','v05'],['vu','c'],['vn','n'],['vc','1.5'],['f_year','2021'],['f_seg','0'],['f_tier','1'],['f_tcs','1'],['f_dil','1'],['f_quotes','0'],['f_quotes','all'],['f_dil','all'],['f_tcs','all'],['f_tier','all'],['f_seg','all'],['f_year','all']]){ $(id).value = v; $(id).fire('change'); }
  if ($('h_cost_noise').listeners.change){ $('h_cost_noise').value = 'v1'; $('h_cost_noise').fire('change'); }
  await wait(300);
  // the buttons' numbers are an outcome reading at an arbitrary setting: record only that each computation completed
  const done = async (btn, word) => { $(btn).fire('click'); await wait(50); for (let q = 0; q < 1200 && /computing/.test($('cNote').textContent); q++) await wait(100);
    const t = $('cNote').textContent; return t.startsWith(word) && !/NaN|undefined/.test(t) && /n filters 100|n 200/.test(t); };
  console.log('noise band computed:', await done('bNoise', 'Noise band'), '| ticker bootstrap computed:', await done('bBoot', 'Ticker bootstrap'));
  for (const tab of ['G1','G2','G3','near the line','random kept','random filtered']){ vm.runInContext(`ST.gtab = ${JSON.stringify(tab)}; ST.gpage = 0; drawG();`, ctx); console.log('tab', tab, 'strips', vm.runInContext(`poolRows(${JSON.stringify(tab)}).length`, ctx)); }
  $('export').fire('click');
  vm.runInContext("for (const k in ST.cond) ST.cond[k].on = [false,false,false]; for (const k in ST.ovr) ST.ovr[k].on = [false,false,false]; recompute();", ctx);
  const none = vm.runInContext('[...STATE].filter(v => v === 1).length', ctx);
  console.log('filtered with every condition off:', none);
  console.log('plot calls', calls.length, 'non-finite plotted values', bad.length, bad.slice(0, 5));
  if (none !== 0 || bad.length) process.exit(1);
})().catch(e => { console.error('PAGE ERROR', e); process.exit(2); });
