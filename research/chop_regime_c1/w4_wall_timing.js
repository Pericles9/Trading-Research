// Chop regime C1, Amendment 3 W4 -- the wall's slider redraw timed in headless Chrome (real Plotly, real layout and paint)
// through the DevTools protocol (row W-e: LOG above 1 s for a full page of 12).
//
// Opens chart_wall.html?selftest=1 at 1600 x 1000. The page's selftest switches four conditions on in every segment, then
// moves one threshold five times; each redraw is timed from the recompute's start through the restyle of every visible
// chart and two animation frames (the 60 ms slider debounce comes on top). Reports the five times, the median and the
// maximum, and any page exception.
//
// Usage: node research/chop_regime_c1/w4_wall_timing.js <chart_wall.html> <chrome.exe> <profile dir>
const {spawn} = require('child_process'), path = require('path');
const [page, chrome, profile] = process.argv.slice(2);
const PORT = 9334;
const url = 'file:///' + path.resolve(page).replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/').replace(/^([A-Za-z])%3A/, '$1:') + '?selftest=1';
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const ch = spawn(chrome, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--window-size=1600,1000', '--no-first-run',
    '--no-default-browser-check', '--disable-extensions', url], {stdio:'ignore'});
  let target = null;
  for (let i = 0; i < 100 && !target; i++){ await wait(300); try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); target = l.find(t => t.type === 'page'); } catch (e) {} }
  if (!target) throw new Error('no page target');
  const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const pend = new Map(), errors = [];
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)){ pend.get(d.id)(d); pend.delete(d.id); }
    else if (d.method === 'Runtime.exceptionThrown') errors.push(d.params.exceptionDetails.exception ? d.params.exceptionDetails.exception.description : d.params.exceptionDetails.text); };
  const call = (method, params = {}) => new Promise(r => { const k = ++id; pend.set(k, r); ws.send(JSON.stringify({id:k, method, params})); });
  await call('Runtime.enable');
  const t0 = Date.now(); let res = null;
  while (Date.now() - t0 < 600000){ await wait(1000);
    const r = await call('Runtime.evaluate', {expression:'JSON.stringify({st: window.__selftest || null, charts: (typeof VIS !== "undefined") ? VIS.size : null, ua: navigator.userAgent})', returnByValue:true});
    const v = JSON.parse(r.result.result.value); if (v.st){ res = {...v.st, user_agent:v.ua}; break; } if (errors.length) break; }
  res = {selftest:res, seconds_to_result:(Date.now() - t0) / 1000, page_exceptions:errors, window:'1600x1000', debounce_ms:60};
  console.log(JSON.stringify(res));
  ws.close(); ch.kill();
  process.exit(res.selftest && !errors.length ? 0 : 1);
})().catch(e => { console.error('TIMING ERROR', e && e.stack || e); process.exit(2); });
