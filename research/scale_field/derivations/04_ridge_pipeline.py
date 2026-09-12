import numpy as np, time
from pathlib import Path
exec(open(Path(__file__).with_name('03_fingerprint_raw_topology.py')).read().split('# ---------- STAGE 1')[0])
SQ2=np.sqrt(2.0)
def n_eff(P,t,s):
    a,b=np.searchsorted(P,[t-CUT*s,t+CUT*s])
    if b-a<1: return 0.0
    z=(t-P[a:b])/s; return SQ2*np.exp(-0.5*z*z).sum()

def ridge_polish(P,t0,s,iters=60):
    t=t0
    for _ in range(iters):
        ft,ftt=F_t(P,t,s),F_tt(P,t,s)
        if not np.isfinite(ft) or ftt<=0: return None
        d=-np.clip(ft/ftt,-0.4*s,0.4*s); t+=d
        if abs(d)<1e-10*s: break
    return t if (np.isfinite(F_tt(P,t,s)) and F_tt(P,t,s)>0) else None

def detect(P, t0, t1, s_lo, s_hi, per_oct=6, kappa=1.0):
    """Ridge-first: find minima of F in t at each scale, calibrate, THEN group. Grid only seeds."""
    ladder=np.exp(np.linspace(np.log(s_lo),np.log(s_hi),int(per_oct*np.log2(s_hi/s_lo))+1))
    span=t1-t0; pts=[]
    for s in ladder:
        lo,hi = t0+CUT*s, t1-CUT*s                       # cone of influence: stay CUT*s inside
        if hi<=lo: continue
        ts=np.linspace(lo,hi,max(40,int((hi-lo)/(0.3*s))))
        vs=np.array([F(P,t,s) for t in ts])
        ok=np.isfinite(vs)
        for i in np.where(ok[:-2]&ok[1:-1]&ok[2:])[0]+1:
            if vs[i]<vs[i-1] and vs[i]<vs[i+1]:          # seed: a local min in t
                tr=ridge_polish(P,ts[i],s)
                if tr is None or tr<lo or tr>hi: continue
                f,ne=F(P,tr,s),n_eff(P,tr,s)
                if not np.isfinite(f) or ne<8 or f>=0: continue
                z=-f*np.sqrt(ne)/0.87
                cal=z-np.sqrt(2*np.log(max(span/s,np.e)))
                if cal>kappa: pts.append((tr,s,f,ne,z,cal))
    # group ridge points into features: same feature if close in t relative to s
    pts.sort(key=lambda r:-r[5]); feats=[]
    for r in pts:
        if all(abs(r[0]-g['t'])>1.0*max(r[1],g['s']) for g in feats):
            feats.append(dict(t=r[0],s=r[1],F=r[2],n_eff=r[3],z=r[4],cal=r[5],members=[r]))
        else:
            g=min((g for g in feats if abs(r[0]-g['t'])<=1.0*max(r[1],g['s'])),key=lambda g:abs(r[0]-g['t']))
            g['members'].append(r)
    for g in feats:
        ss=[m[1] for m in g['members']]
        g['persist_oct']=np.log2(max(ss)/min(ss)) if len(ss)>1 else 0.0
        # duration readout: scale where the spine first reaches F = -0.5
        below=[m for m in sorted(g['members'],key=lambda m:m[1]) if m[2]<-0.5]
        g['sigma_hat']=below[0][1] if below else None
    return [g for g in feats if g['persist_oct']>=1.0]

lam = lambda x: 6.0 + 60*np.exp(-(x-500.)**2/(2*8.0**2)) + 25*np.exp(-(x-900.)**2/(2*40.**2))
P = sample(lam, 1500.0, 70.0)
t_=time.time(); D=detect(P,0.0,1500.0,2.0,300.0); el=time.time()-t_
print(f"TAPE: bg 6/s + A(t=500, sigma=8) + B(t=900, sigma=40).  {P.size} prints.  {el:.1f}s\n")
print(f"{'t':>9} {'s_sel':>8} {'F':>8} {'n_eff':>9} {'z':>7} {'calib':>7} {'oct':>5} {'sigma_hat':>10}   match")
for g in sorted(D,key=lambda g:-g['cal']):
    m=("A  true sigma=8" if abs(g['t']-500)<40 else "B  true sigma=40" if abs(g['t']-900)<120 else "** FALSE POSITIVE **")
    sh=f"{g['sigma_hat']:.2f}" if g['sigma_hat'] else "  n/a"
    print(f"{g['t']:9.2f} {g['s']:8.2f} {g['F']:8.3f} {g['n_eff']:9.1f} {g['z']:7.2f} {g['cal']:7.2f} {g['persist_oct']:5.2f} {sh:>10}   {m}")

# --- false-alarm control: identical machinery on a pure inhomogeneous-Poisson tape, no bumps ---
flat = lambda x: 6.0+0*x
Q = sample(flat, 1500.0, 8.0)
Dn = detect(Q,0.0,1500.0,2.0,300.0)
print(f"\nNULL CONTROL — flat 6/s Poisson tape, {Q.size} prints, same settings: {len(Dn)} detections"
      + ("" if not Dn else "  -> " + ", ".join(f"t={g['t']:.0f} cal={g['cal']:.2f}" for g in Dn)))

# ===== the duration readout, done properly: fit the closed form along the spine =====
# For a Gaussian bump (width sigma, integral N) on background b, along the spine:
#     F(s) = -( s^2/(sigma^2+s^2) ) * 1/( 1 + c*sqrt(sigma^2+s^2) ),   c = b*sqrt(2pi)/N
# Two parameters. The -0.5 crossing is the c=0 special case, which is why it reads high.
from scipy.optimize import least_squares
def fit_sigma(members):
    m=sorted(members,key=lambda r:r[1]); s=np.array([r[1] for r in m]); f=np.array([r[2] for r in m])
    if s.size<4: return None
    def resid(p):
        sig,lc=np.exp(p[0]),p[1]; c=np.exp(lc); u=sig**2+s**2
        return (-(s**2/u)/(1+c*np.sqrt(u))) - f
    best=None
    for s0 in (s.min(), np.sqrt(s.min()*s.max()), s.max()):
        for c0 in (-9.0,-5.0,-2.0):
            try: r=least_squares(resid,[np.log(s0),c0],method='lm',max_nfev=4000)
            except Exception: continue
            if best is None or r.cost<best.cost: best=r
    return None if best is None else np.exp(best.x[0])

print("\n\n=== duration readout: -0.5 crossing vs 2-parameter fit of the closed form ===")
print(f"{'feature':>10} {'true sigma':>11} {'-0.5 crossing':>14} {'err':>8} {'model fit':>11} {'err':>8}")
for g in sorted(D,key=lambda g:g['t']):
    truth = 8.0 if abs(g['t']-500)<40 else 40.0
    sh, sf = g['sigma_hat'], fit_sigma(g['members'])
    print(f"{('A' if truth==8 else 'B'):>10} {truth:11.1f} {sh:14.2f} {100*(sh/truth-1):+7.0f}% "
          f"{sf:11.2f} {100*(sf/truth-1):+7.0f}%")

# ===== a second tape, four widths, to see whether the fit holds up =====
print("\n=== four bumps of different width on one tape, same pipeline end to end ===")
truths=[(300.0,4.0),(700.0,12.0),(1200.0,35.0),(1900.0,90.0)]
lam4=lambda x: 6.0+sum(55*np.exp(-(x-c)**2/(2*w**2)) for c,w in truths)
R=sample(lam4,2400.0,70.0)
D4=detect(R,0.0,2400.0,2.0,400.0)
print(f"{'true t':>8} {'true sigma':>11} {'found t':>9} {'-0.5':>8} {'err':>7} {'fit':>8} {'err':>7} {'oct':>5}")
for c,w in truths:
    g=min(D4,key=lambda g:abs(g['t']-c)) if D4 else None
    if g is None or abs(g['t']-c)>4*w: print(f"{c:8.0f} {w:11.1f}     -- not detected --"); continue
    sf=fit_sigma(g['members']); sh=g['sigma_hat']
    shs=f"{sh:8.2f}" if sh else "     n/a"; she=f"{100*(sh/w-1):+6.0f}%" if sh else "      -"
    sfs=f"{sf:8.2f}" if sf else "     n/a"; sfe=f"{100*(sf/w-1):+6.0f}%" if sf else "      -"
    print(f"{c:8.0f} {w:11.1f} {g['t']:9.1f} {shs} {she} {sfs} {sfe} {g['persist_oct']:5.2f}")
print(f"\ntotal detections on that tape: {len(D4)} (4 injected)")
