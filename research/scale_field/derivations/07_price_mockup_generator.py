import numpy as np
from scipy.ndimage import gaussian_filter1d
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "results" / "scale_field" / "charts" / "mockups"
OUT.mkdir(parents=True, exist_ok=True)


rng = np.random.default_rng(11)

# ---------------- synthetic session ----------------
dt = 0.05
T  = 3600.0
t  = np.arange(0, T, dt)
n  = t.size

def bump(c, w, amp):
    return amp*np.exp(-(t-c)**2/(2*w**2))

# U-shaped background rate + three injected features
lam = 6.0 + 6.0*np.exp(-(t-0)**2/(2*500**2)) + 6.0*np.exp(-(t-T)**2/(2*500**2))
lam = lam + bump(600, 5.0, 90.0)     # A: 5 s sweep
lam = lam + bump(1500, 40.0, 45.0)   # B: 40 s churn
lam = lam + bump(2600, 300.0, 14.0)  # C: 300 s slow accumulation

# order-flow imbalance profile in [-1,1]
q = 0.015*np.sin(t/220.0)
q = q + 0.72*np.exp(-(t-600)**2/(2*5.0**2))     # A strongly bought
q = q + 0.00*np.exp(-(t-1500)**2/(2*40.0**2))   # B two-sided churn
q = q - 0.22*np.exp(-(t-2600)**2/(2*300**2))    # C steadily sold
q = q + 0.50*np.exp(-(t-2000)**2/(2*40.0**2))   # D: pressure with NO rate signature
q = np.clip(q, -1, 1)

lam_b = lam*(1+q)/2.0
lam_s = lam*(1-q)/2.0

# price driven by signed flow + noise scaled by activity
impact = 2.2e-5
dlogp  = impact*(lam_b-lam_s)*dt + 2.6e-5*np.sqrt(lam*dt)*rng.standard_normal(n)
logp   = np.cumsum(dlogp)
logp  -= logp[0]
price  = 4.10*np.exp(logp)

# ---------------- fields ----------------
scales = np.logspace(np.log10(0.4), np.log10(420.0), 56)
step   = 24                              # render-column decimation
tc     = t[::step]

def gsm(x, s, order=0):
    # gaussian_filter1d differentiates w.r.t. sample index; convert to per-second
    return gaussian_filter1d(x, s/dt, order=order, mode="nearest")/(dt**order)

F_rate, F_imb, F_px = [], [], []
for s in scales:
    lh  = gsm(lam, s)
    d2  = gsm(lam, s, order=2)
    F_rate.append((s*s*d2/np.maximum(lh, 1e-9))[::step])
    sb, ss = gsm(lam_b, s), gsm(lam_s, s)
    F_imb.append(((sb-ss)/np.maximum(sb+ss, 1e-9))[::step])
    c = s*s*gsm(logp, s, order=2)
    F_px.append((c/ (1.4826*np.median(np.abs(c-np.median(c)))+1e-12))[::step])
F_rate = np.array(F_rate); F_imb = np.array(F_imb); F_px = np.array(F_px)

# admissibility floor s_min = 2.26 / local rate
lam_loc  = gsm(lam, 2.0)[::step]
s_min    = 2.26/lam_loc
mask     = scales[:, None] < s_min[None, :]
F_rate[mask] = np.nan
F_imb[mask]  = np.nan
F_px[mask]   = np.nan

squash = lambda F: F/(1.0+np.abs(F))          # -1 floor -> -0.5, unbounded top -> 1

# ---------------- palette (diverging: two hues + neutral grey midpoint) ----
CURV = [[0.0,"#1F5C8B"],[0.30,"#7FA8C4"],[0.5,"#E9E7E2"],[0.70,"#D08A5F"],[1.0,"#A8431C"]]
FLOW = [[0.0,"#6B3B92"],[0.30,"#A98CC0"],[0.5,"#E9E7E2"],[0.70,"#71A97F"],[1.0,"#2C6B45"]]
INK, INK2, GRID, SURF = "#1A1A1A", "#5A5A5A", "#E2E0DC", "#FFFFFF"

def ticks(vals):
    return dict(tickmode="array", tickvals=[squash(v) for v in vals],
                ticktext=[f"{v:g}" for v in vals])

def ticksI(vals):
    return dict(tickmode="array", tickvals=[squash(v/0.35) for v in vals],
                ticktext=[f"{v:g}" for v in vals])

def ticks3(vals):
    return dict(tickmode="array", tickvals=[squash(v/3.0) for v in vals],
                ticktext=[f"{v:g}" for v in vals])

fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.035,
    row_heights=[0.28, 0.24, 0.24, 0.24],
    subplot_titles=(
      "Price — with the smooth at the scale you are hovering, and the measured duration of each feature",
      "1 · Trade-rate curvature   s²·λ̂″/λ̂    orange = rate turning over · blue = rate hollowing out",
      "2 · Order-flow imbalance   (λ̂buy−λ̂sell)/(λ̂buy+λ̂sell)    green = bought · purple = sold",
      "3 · Log-price curvature   s²·(ln p)″, in units of each row's own noise    orange = price rounding over · blue = basing  —  the fine-scale carpet IS a random walk: that is what 'no structure' looks like"))

# --- panel 1: price
fig.add_trace(go.Scatter(x=t[::10], y=price[::10], mode="lines", name="price",
    line=dict(color=INK, width=1.2), hovertemplate="t=%{x:.0f}s<br>%{y:.4f}<extra>price</extra>"),
    row=1, col=1)

slider_scales = scales[::4]
for i, s in enumerate(slider_scales):
    fig.add_trace(go.Scatter(x=t[::10], y=(4.10*np.exp(gsm(logp, s)))[::10], mode="lines",
        name=f"smooth s={s:.1f}s", visible=(i == 7),
        line=dict(color="#A8431C", width=2.4), hoverinfo="skip"), row=1, col=1)

# --- panels 2-4: fields
for r, (Z, cs, tk, cbt) in enumerate([
        (F_rate, CURV, ticks([-1,-0.5,0,2,8]), "s²λ̂″/λ̂"),
        (F_imb/0.35, FLOW, ticksI([-0.6,-0.3,0,0.3,0.6]), "imbalance"),
        (F_px/3.0, CURV, ticks3([-9,-3,0,3,9]), "σ units")], start=2):
    fig.add_trace(go.Heatmap(x=tc, y=np.log10(scales), z=squash(Z), colorscale=cs,
        zmid=0, zmin=-1, zmax=1, showscale=True,
        colorbar=dict(title=dict(text=cbt, font=dict(size=10)), len=0.19,
                      y={2:0.615, 3:0.375, 4:0.135}[r], thickness=11,
                      tickfont=dict(size=9), **tk),
        hovertemplate="t=%{x:.0f}s<br>s=%{y:.2f} (log₁₀ s)<extra></extra>"), row=r, col=1)
    fig.add_trace(go.Scatter(x=tc, y=np.clip(np.log10(s_min), np.log10(scales[0]), np.log10(scales[-1])), mode="lines", showlegend=(r==2),
        name="s_min = 2.26/λ̂  (below this the estimate does not exist)", line=dict(color=INK2, width=1.2, dash="dot"),
        hoverinfo="skip"), row=r, col=1)

# --- the slider-driven read line on each field
for i, s in enumerate(slider_scales):
    for r in (2,3,4):
        fig.add_trace(go.Scatter(x=[tc[0], tc[-1]], y=[np.log10(s)]*2, mode="lines",
            visible=(i == 7), showlegend=False,
            line=dict(color=INK, width=1.6), hoverinfo="skip"), row=r, col=1)

n_static = 1 + len(slider_scales) + 6
steps = []
for i, s in enumerate(slider_scales):
    vis = [True]*len(fig.data)
    for j in range(len(slider_scales)):
        vis[1+j] = (i == j)
        for k in range(3):
            vis[n_static + j*3 + k] = (i == j)
    steps.append(dict(method="update", args=[{"visible": vis}], label=f"{s:.1f}"))

# --- measured durations from the -0.5 crossing, drawn on the price panel
notes, unread = [], []
for centre, label, truth in [(600,"A",5.0), (1500,"B",40.0), (2600,"C",300.0), (2000,"D",None)]:
    col = np.argmin(np.abs(tc-centre))
    prof = F_rate[:, col]
    ok = np.isfinite(prof) & (prof < -0.5)
    if ok.any():
        sig = float(scales[np.argmax(ok)])
        notes.append((centre, sig, label, truth))
        fig.add_vrect(x0=centre-sig, x1=centre+sig, row=1, col=1,
                      fillcolor="#A8431C", opacity=0.10, line_width=0)
    else:
        unread.append((centre, label))

fig.update_layout(
    height=1180, paper_bgcolor=SURF, plot_bgcolor=SURF,
    font=dict(family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Helvetica, Arial",
              size=12, color=INK),
    margin=dict(l=76, r=96, t=176, b=100),
    title=dict(text="<b>Scale field against price — layout mockup</b><br>"
        "<span style='font-size:12px;color:#5A5A5A'>SYNTHETIC DATA, not any event. "
        "Four injected features: <b>A</b> 5 s sweep (bought) · <b>B</b> 40 s churn (two-sided) · "
        "<b>C</b> 300 s accumulation (sold) · <b>D</b> at t≈2000 s: pressure with no rate signature.<br>"
        "The point of the layout: B is loud on panel 1 and silent on panels 2–3. "
        "D is invisible on panel 1 and visible on panels 2–3.</span>", x=0.012, xanchor="left"),
    legend=dict(orientation="h", y=1.055, x=0.012, font=dict(size=11)),
    hovermode="x unified",
    sliders=[dict(active=7, steps=steps, x=0.012, len=0.80, y=-0.045,
        currentvalue=dict(prefix="read scale s = ", suffix=" s", font=dict(size=12)),
        pad=dict(t=32), font=dict(size=10))])

for r in range(1,5):
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, row=r, col=1)
    fig.update_yaxes(showgrid=False, zeroline=False, row=r, col=1)
fig.update_xaxes(title_text="session time (s)", row=4, col=1)
fig.update_yaxes(title_text="price", row=1, col=1)
for r in (2,3,4):
    fig.update_yaxes(title_text="log₁₀ scale s (s)",
                     range=[np.log10(scales[0]), np.log10(scales[-1])], row=r, col=1)
for a in fig.layout.annotations[:4]:
    a.font.size = 12; a.xanchor = "left"; a.x = 0.012; a.align = "left"

for centre, sig, label, truth in notes:
    fig.add_annotation(x=centre, y=0.86, yref="y domain", row=1, col=1,
        text=f"<b>{label}</b>  σ read {sig:.0f}s / true {truth:.0f}s",
        showarrow=False, font=dict(size=10, color="#A8431C"), yanchor="bottom")
for centre, label in unread:
    fig.add_annotation(x=centre, y=0.04, yref="y domain", row=1, col=1,
        text=f"<b>{label}</b>  no duration readable on panel 1",
        showarrow=False, font=dict(size=10, color="#5A5A5A"), yanchor="bottom")

fig.add_annotation(x=3150, y=np.log10(300), row=2, col=1, text="session envelope —<br>this band is the clock,<br>not the tape",
    showarrow=True, arrowhead=0, arrowcolor="#5A5A5A", ax=-52, ay=26,
    font=dict(size=10, color="#3A3A3A"), align="left")

fig.write_html(str(OUT / "scale_field_price_mockup.html"),
               include_plotlyjs=True, full_html=True)
print("read:", [(l, round(s,1)) for _,s,l,_ in notes], "unread:", [l for _,l in unread])
print("ok")
