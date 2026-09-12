import numpy as np
from scipy.ndimage import gaussian_filter1d
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "results" / "scale_field" / "charts" / "mockups"
OUT.mkdir(parents=True, exist_ok=True)


rng = np.random.default_rng(23)
dt, T = 0.05, 3600.0
t = np.arange(0, T, dt); n = t.size

# ---- intensity: U-shape + one genuine rate hump (A) + one rate VOID (V) ----
lam = 6.0 + 5.0*np.exp(-(t)**2/(2*450**2)) + 5.0*np.exp(-(t-T)**2/(2*450**2))
lam = lam + 70.0*np.exp(-(t-600)**2/(2*6.0**2))              # A: real rate hump
lam = lam * (1 - 0.75*np.exp(-(t-1400)**2/(2*25.0**2)))      # V: a genuine void

# ---- sample prints from it ----
cdf = np.cumsum(lam*dt); N = int(cdf[-1])
prints = np.sort(np.interp(rng.random(N)*cdf[-1], cdf, t))

# ---- feature E: CLUMPING AT CONSTANT MEAN RATE, 2250-2550 s ----
e0, e1 = 2250.0, 2550.0
lam_e = float(np.mean(lam[(t>=e0)&(t<=e1)]))
prints = prints[(prints < e0) | (prints > e1)]
K = 7                                        # offspring per parent
parents = e0 + np.sort(rng.random(rng.poisson(lam_e/K*(e1-e0))))*(e1-e0)
kids = (parents[:,None] + rng.exponential(0.015, size=(parents.size, K))).ravel()
prints = np.sort(np.concatenate([prints, kids[(kids>e0)&(kids<e1)]]))

# ---- field computed from the actual prints ----
counts = np.histogram(prints, bins=np.append(t, T))[0]/dt
scales = np.logspace(np.log10(0.5), np.log10(400.0), 52)
step = 24; tc = t[::step]
_pad = int(4*400/dt)
def _mk(x):
    xp = np.concatenate([np.zeros(_pad), x, np.zeros(_pad)]); m = xp.size
    X = np.fft.rfft(xp); k = 2*np.pi*np.fft.rfftfreq(m, d=dt)
    def sm(s, o=0):
        H = np.exp(-0.5*(k*s)**2)
        if o == 2: H = H*(-(k**2))
        return np.fft.irfft(X*H, m)[_pad:_pad+x.size]
    return sm
_sm = None
def gsm(x, s, o=0):
    global _sm
    if _sm is None: _sm = _mk(x)
    return _sm(s, o)
F = np.array([ (s*s*gsm(counts,s,2)/np.maximum(gsm(counts,s),1e-9))[::step] for s in scales ])
lam_hat = gsm(counts, 3.0)[::step]
s_min = 2.26/np.maximum(lam_hat, 1e-6)
F[scales[:,None] < s_min[None,:]] = np.nan
n_eff = 2*np.sqrt(np.pi)*scales[:,None]*lam_hat[None,:]
floor = 2*0.87/np.sqrt(np.maximum(n_eff, 1e-9))
F_raw = F.copy()
F[np.abs(F) < floor] = np.nan
squash = lambda x: x/(1.0+np.abs(x))

# ---- ITT and its rolling log-quantiles, on the SAME log-time axis ----
itt = np.diff(prints); itt = np.maximum(itt, 1e-7)
mid = prints[1:]; lg = np.log10(itt)
W = 25.0
lo = np.searchsorted(mid, tc-W); hi = np.searchsorted(mid, tc+W)
q10=np.full(tc.size,np.nan); q50=q10.copy(); q90=q10.copy()
for i,(a,b) in enumerate(zip(lo,hi)):
    if b-a >= 30:
        q10[i],q50[i],q90[i] = np.percentile(lg[a:b], [10,50,90])
POISSON_BAND = np.log10(np.log(1/0.10)/np.log(1/0.90))   # 1.3396 decades, any rate
POISSON_OFF  = np.log10(2.26) - np.log10(np.log(2))      # s_min sits this far above median ITT

CURV=[[0,"#1F5C8B"],[0.30,"#7FA8C4"],[0.5,"#E9E7E2"],[0.70,"#D08A5F"],[1,"#A8431C"]]
INK,INK2,GRID,SURF="#1A1A1A","#5A5A5A","#E2E0DC","#FFFFFF"

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
  row_heights=[0.42,0.30,0.28], subplot_titles=(
   "1 · Scale field with the ITT cloud on the SAME log-time axis — ribbon = rolling 10/50/90th pct of log₁₀ Δt.  Field shown only where it clears ±2·0.87/√n_eff; grey = inside the noise floor",
   "2 · Width of that ribbon vs the Poisson constant 1.340 decades — above the line is over-dispersed (clumped), and it is a universal constant, not a fit",
   "3 · Every print at its own log₁₀ Δt. Coloured only where the field clears its noise floor at s = 8 s — if the mark tracks clustering, the colour sits at the BOTTOM of the cloud"))

# panel 1
fig.add_trace(go.Heatmap(x=tc, y=np.log10(scales), z=squash(F), colorscale=CURV, zmid=0,
    zmin=-1, zmax=1, colorbar=dict(title=dict(text="s²λ̂″/λ̂",font=dict(size=10)), len=0.30, y=0.83,
    thickness=11, tickmode="array", tickvals=[squash(v) for v in (-1,-.5,0,2,8)],
    ticktext=["-1","-0.5","0","2","8"], tickfont=dict(size=9)),
    hovertemplate="t=%{x:.0f}s<extra></extra>"), row=1,col=1)
fig.add_trace(go.Scatter(x=np.concatenate([tc,tc[::-1]]), y=np.concatenate([q90,q10[::-1]]),
    fill="toself", fillcolor="rgba(26,26,26,0.13)", line=dict(width=0),
    name="ITT 10–90th pct", hoverinfo="skip"), row=1,col=1)
fig.add_trace(go.Scatter(x=tc, y=q50, mode="lines", name="median log₁₀ Δt",
    line=dict(color=INK, width=1.8)), row=1,col=1)
fig.add_trace(go.Scatter(x=tc, y=np.log10(s_min), mode="lines", name="s_min = 2.26/λ̂",
    line=dict(color=INK2, width=1.3, dash="dot")), row=1,col=1)
fig.add_trace(go.Scatter(x=tc, y=q50+POISSON_OFF, mode="lines",
    name="where s_min would sit if the tape were Poisson",
    line=dict(color="#2C6B45", width=1.3, dash="dash")), row=1,col=1)

# panel 2
fig.add_trace(go.Scatter(x=tc, y=q90-q10, mode="lines", showlegend=False,
    line=dict(color=INK, width=1.8), hovertemplate="t=%{x:.0f}s<br>%{y:.2f} dec<extra></extra>"), row=2,col=1)
fig.add_hline(y=POISSON_BAND, line=dict(color="#2C6B45", width=1.4, dash="dash"), row=2, col=1,
    annotation_text="Poisson: 1.340 decades", annotation_position="top left",
    annotation_font=dict(size=10, color="#2C6B45"))

# panel 3
S_READ = 8.0
row  = np.argmin(np.abs(scales-S_READ))
Fp   = np.interp(mid, tc, np.nan_to_num(F_raw[row], nan=0.0))
flr  = np.interp(mid, tc, floor[row])
sig  = np.abs(Fp) > flr
sub  = np.zeros(mid.size, bool); sub[::max(1, mid.size//14000)] = True
a = sub & ~sig; b = sub & sig
fig.add_trace(go.Scattergl(x=mid[a], y=lg[a], mode="markers", showlegend=False,
    marker=dict(size=2.6, color="#C9C7C2", opacity=0.55), hoverinfo="skip"), row=3,col=1)
fig.add_trace(go.Scattergl(x=mid[b], y=lg[b], mode="markers", showlegend=False,
    marker=dict(size=4.2, color=squash(Fp[b]), colorscale=CURV, cmid=0, cmin=-1, cmax=1,
                showscale=False, opacity=0.85, line=dict(width=0)),
    hovertemplate="t=%{x:.0f}s<br>log₁₀Δt=%{y:.2f}<extra></extra>"), row=3,col=1)

for x0,x1,lab,col in [(575,625,"A · real rate hump","#A8431C"),
                      (1375,1425,"V · genuine void","#1F5C8B"),
                      (e0,e1,"E · clumping at CONSTANT mean rate","#2C6B45")]:
    for r in (1,2,3):
        fig.add_vrect(x0=x0,x1=x1,row=r,col=1,fillcolor=col,opacity=0.07,line_width=0)
    fig.add_annotation(x=(x0+x1)/2, y=0.94, yref="y domain", row=1, col=1,
        text=f"<b>{lab.split(' · ')[0]}</b>", showarrow=False, yanchor="top",
        font=dict(size=12, color=col))

fig.update_layout(height=1080, paper_bgcolor=SURF, plot_bgcolor=SURF,
  font=dict(family="ui-sans-serif, system-ui, Segoe UI, Helvetica, Arial", size=12, color=INK),
  margin=dict(l=82,r=96,t=214,b=112), hovermode="x unified",
  title=dict(x=0.012, xanchor="left", text=
    "<b>Overlaying the ITT chart on the scale field — layout mockup</b><br>"
    "<span style='font-size:12px;color:#5A5A5A'>SYNTHETIC DATA. Both axes are log₁₀ of a duration in "
    "seconds, so the interval cloud and the kernel scale belong on one axis.<br>"
    "<b>A</b> real rate hump (5 s) · <b>V</b> a genuine void · "
    "<b>E</b> clumping at CONSTANT mean rate — the case that matters.<br>"
    "Across E the mean rate is unchanged, so the field has no coherent trumpet — only speckle. "
    "The ITT ribbon doubles, and the gap between the two dashed lines opens from 0.51 to 1.90 decades.</span>"),
  legend=dict(orientation="h", y=-0.085, x=0.012, font=dict(size=11)))
for r in (1,2,3):
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, row=r, col=1)
    fig.update_yaxes(showgrid=False, zeroline=False, row=r, col=1)
fig.update_yaxes(title_text="log₁₀ duration (s)", row=1, col=1)
fig.update_yaxes(title_text="ribbon width<br>(decades)", row=2, col=1)
fig.update_yaxes(title_text=f"log₁₀ Δt per print", row=3, col=1)
fig.update_xaxes(title_text="session time (s)", row=3, col=1)
for a in fig.layout.annotations[:3]:
    a.font.size=12; a.xanchor="left"; a.x=0.012; a.align="left"
fig.add_annotation(x=2400, y=-1.55, row=1, col=1, ax=118, ay=-34, arrowhead=0, arrowcolor="#5A5A5A",
    text="this gap <b>is</b> the clustering:<br>1.90 decades here, 0.51 under Poisson",
    font=dict(size=10, color="#2A2A2A"), align="left")
fig.add_annotation(x=600, y=2.15, row=1, col=1, ax=96, ay=-4, arrowhead=0, arrowcolor="#5A5A5A",
    text="a real rate hump makes a trumpet;<br>E makes speckle", font=dict(size=10, color="#2A2A2A"),
    align="left")

fig.write_html(str(OUT / "scale_field_itt_overlay.html"), include_plotlyjs=True, full_html=True)

print("prints:", prints.size, "| E mean rate in:", round(len(prints[(prints>e0)&(prints<e1)])/(e1-e0),2),
      "vs ambient", round(lam_e,2))
m=(tc>e0)&(tc<e1); q=(tc>2900)
print("ribbon width  E:", round(float(np.nanmedian((q90-q10)[m])),3),
      " quiet:", round(float(np.nanmedian((q90-q10)[q])),3), " Poisson:", round(POISSON_BAND,3))
print("significant cells kept:", round(float(np.isfinite(F).sum()/np.isfinite(F_raw).sum()),3))
print("s_min minus median ITT   quiet:", round(float(np.nanmedian((np.log10(s_min)-q50)[q])),3),
      " E:", round(float(np.nanmedian((np.log10(s_min)-q50)[m])),3), " Poisson:", round(POISSON_OFF,3))
print("field |F| median  E:", round(float(np.nanmedian(np.abs(F[row][m]))),3),
      " quiet:", round(float(np.nanmedian(np.abs(F[row][q]))),3))
