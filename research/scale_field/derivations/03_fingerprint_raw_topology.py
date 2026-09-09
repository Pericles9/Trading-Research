import numpy as np
rng = np.random.default_rng(5)

# ---- truncated moments: only prints within +-CUT*s matter (exp(-18) ~ 1.5e-8) ----
CUT = 6.0
def moments(P, t, s, K=6):
    a, b = np.searchsorted(P, [t-CUT*s, t+CUT*s])
    if b-a < 3: return None
    z = (t - P[a:b])/s                       # CONVENTION z = (t - t_i)/s
    w = np.exp(-0.5*z*z); W = w.sum()
    if W <= 0: return None
    out = np.empty(K+1); zz = np.ones_like(z)
    for k in range(K+1):
        out[k] = (w*zz).sum()/W; zz = zz*z
    return out
def F(P,t,s):
    M=moments(P,t,s);  return np.nan if M is None else M[2]-1.0
def F_t(P,t,s):
    M=moments(P,t,s);  return np.nan if M is None else (-M[3]+2*M[1]+M[2]*M[1])/s
def F_u(P,t,s):
    M=moments(P,t,s);  return np.nan if M is None else M[4]-2*M[2]-M[2]**2
def F_tt(P,t,s):
    M=moments(P,t,s)
    if M is None: return np.nan
    dM1=(-M[2]+1.0+M[1]**2); dM3=(-M[4]+3*M[2]+M[3]*M[1]); dM2=(-M[3]+2*M[1]+M[2]*M[1])
    return (-dM3+2*dM1+M[2]*dM1+M[1]*dM2)/s**2
def F_tu(P,t,s):
    M=moments(P,t,s)
    if M is None: return np.nan
    A=-M[3]+2*M[1]+M[2]*M[1]
    d1=M[3]-M[1]-M[1]*M[2]; d3=M[5]-3*M[3]-M[3]*M[2]; d2=M[4]-2*M[2]-M[2]**2
    return ((-d3+2*d1+M[2]*d1+M[1]*d2)-A)/s

def sample(lam_fn, T, rate_max):
    n=rng.poisson(rate_max*T); c=np.sort(rng.random(n)*T)
    return c[rng.random(n) < lam_fn(c)/rate_max]

# ---------- STAGE 1: seed. coarse ladder, roots of F(.,s)=0 in t by bisection ----------
def zeros_at_scale(P, s, t0, t1, n_probe=None):
    n = n_probe or int(np.clip((t1-t0)/(0.35*s), 60, 6000))
    ts = np.linspace(t0, t1, n); vs = np.array([F(P,t,s) for t in ts])
    ok = np.isfinite(vs); roots=[]
    for i in np.where(ok[:-1] & ok[1:] & (np.sign(vs[:-1])*np.sign(vs[1:]) < 0))[0]:
        lo,hi = ts[i], ts[i+1]
        for _ in range(50):
            m=(lo+hi)/2; fm=F(P,m,s)
            if np.sign(fm)==np.sign(F(P,lo,s)): lo=m
            else: hi=m
        roots.append((lo+hi)/2)
    return np.array(roots)

# ---------- STAGE 2: polish. Newton on {F=0, F_t=0}. machine precision, no grid ----------
def polish(P, t0, s0, iters=80):
    t,u = t0, np.log(s0)
    for _ in range(iters):
        s=np.exp(u); r=np.array([F(P,t,s),F_t(P,t,s)])
        if not np.all(np.isfinite(r)): return None
        J=np.array([[F_t(P,t,s),F_u(P,t,s)],[F_tt(P,t,s),F_tu(P,t,s)]])
        if not np.all(np.isfinite(J)) or abs(np.linalg.det(J))<1e-300: return None
        d=np.linalg.solve(J,-r)
        d[0]=np.clip(d[0],-0.3*s,0.3*s); d[1]=np.clip(d[1],-0.2,0.2)
        t,u=t+d[0],u+d[1]
        if abs(d[0])<1e-11*s and abs(d[1])<1e-13: break
    s=np.exp(u)
    if abs(F(P,t,s))>1e-7 or abs(F_t(P,t,s)*s)>1e-7: return None
    return t, s

def fingerprint(P, t0, t1, s_lo, s_hi, per_octave=8):
    """Witkin fingerprint: track zeros of F up the scale ladder; an arch closes where a pair annihilates."""
    ladder = np.exp(np.linspace(np.log(s_lo), np.log(s_hi),
                                int(per_octave*np.log2(s_hi/s_lo))+1))
    prev, apexes = zeros_at_scale(P, ladder[0], t0, t1), []
    for s_a, s_b in zip(ladder[:-1], ladder[1:]):
        cur = zeros_at_scale(P, s_b, t0, t1)
        for r in prev:                                    # which previous roots vanished?
            if cur.size == 0 or np.min(np.abs(cur - r)) > 1.2*s_b:
                got = polish(P, r, np.sqrt(s_a*s_b))
                if got: apexes.append(got)
        prev = cur
    # dedupe
    out=[]
    for t,s in sorted(apexes, key=lambda x:-x[1]):
        if all(abs(t-t2)>0.4*max(s,s2) or abs(np.log(s/s2))>0.35 for t2,s2 in out): out.append((t,s))
    return sorted(out)

lam = lambda x: 6.0 + 60*np.exp(-(x-500.)**2/(2*8.0**2)) + 25*np.exp(-(x-900.)**2/(2*40.**2))
P = sample(lam, 1500.0, 70.0)
print(f"TAPE: bg 6/s + bump A (t=500, sigma=8) + bump B (t=900, sigma=40).  {P.size} prints\n")
import time; t_=time.time()
ap = fingerprint(P, 60.0, 1440.0, 2.0, 300.0)
print(f"fingerprint apexes found in {time.time()-t_:.1f}s  (seed = coarse ladder, polish = Newton to 1e-11)")
for t,s in ap:
    near = "A (500, sig 8)" if abs(t-500)<90 else ("B (900, sig 40)" if abs(t-900)<160 else "-")
    print(f"   t* = {t:8.2f}   s* = {s:8.3f}   |F|={abs(F(P,t,s)):.1e}   nearest injected: {near}")

# ============ STAGE 3: filter. significance + persistence, both derived not tuned ============
SQ2 = np.sqrt(2.0)
def n_eff(P, t, s):
    a,b = np.searchsorted(P,[t-CUT*s, t+CUT*s])
    if b-a < 1: return 0.0
    z=(t-P[a:b])/s
    return SQ2*np.exp(-0.5*z*z).sum()      # == 2*sqrt(pi)*s*lambda, with NO rate estimate

def ridge_t(P, t0, s, iters=60):
    t=t0
    for _ in range(iters):
        ft,ftt = F_t(P,t,s), F_tt(P,t,s)
        if not np.isfinite(ft) or ftt==0: return None
        d=-np.clip(ft/ftt,-0.4*s,0.4*s); t+=d
        if abs(d)<1e-9*s: break
    return t if F_tt(P,t,s)>0 else None      # a MINIMUM in t = the spine of a negative arch

def describe(P, t_ap, s_ap, T_span, oct_down=3.0, n_step=13):
    """Walk down the arch's spine from the apex. Returns depth, persistence, calibrated significance."""
    best=None; rows=[]; t=t_ap
    for s in np.exp(np.linspace(np.log(s_ap), np.log(s_ap)-oct_down*np.log(2), n_step)):
        tr = ridge_t(P, t, s)
        if tr is None or abs(tr-t_ap) > 2.5*s_ap: break
        f, ne = F(P,tr,s), n_eff(P,tr,s)
        if not np.isfinite(f) or ne < 4: break
        t = tr
        z  = -f*np.sqrt(ne)/0.87                                  # negative field -> positive z
        cal= z - np.sqrt(2*np.log(max(T_span/s, np.e)))           # Dumbgen-Spokoiny per-scale penalty
        rows.append((s, tr, f, ne, z, cal))
        if best is None or cal > best[5]: best = rows[-1]
    if not best or len(rows) < 2: return None
    persist = np.log2(rows[0][0]/rows[-1][0])                     # octaves the spine survives
    return dict(t_apex=t_ap, s_apex=s_ap, s_best=best[0], t_best=best[1], depth=best[2],
                n_eff=best[3], z=best[4], calibrated=best[5], persistence_oct=persist)

T_span = 1440.0-60.0
feats = [describe(P, t, s, T_span) for t,s in ap]
feats = [f for f in feats if f]
KAPPA = 1.0                                                        # one global threshold, all scales
keep  = [f for f in feats if f["calibrated"] > KAPPA and f["persistence_oct"] >= 1.0]

print(f"\n\n=== STAGE 3 ===\n{len(ap)} raw apexes -> {len(feats)} describable -> "
      f"{len(keep)} survive (calibrated > {KAPPA}, persistence >= 1 octave)\n")
print(f"{'t_apex':>9} {'s_apex':>8} {'s_best':>8} {'depth F':>9} {'n_eff':>8} {'z':>7} {'calib':>7} {'oct':>5}   match")
for f in sorted(keep, key=lambda x:-x["calibrated"]):
    m = "A (t=500, sigma=8)" if abs(f["t_best"]-500)<40 else ("B (t=900, sigma=40)" if abs(f["t_best"]-900)<110 else "** false positive **")
    print(f"{f['t_apex']:9.2f} {f['s_apex']:8.2f} {f['s_best']:8.2f} {f['depth']:9.3f} "
          f"{f['n_eff']:8.1f} {f['z']:7.2f} {f['calibrated']:7.2f} {f['persistence_oct']:5.2f}   {m}")
print(f"\nfor reference: A sigma=8, B sigma=40.  The -0.5 crossing scale is the duration readout.")
