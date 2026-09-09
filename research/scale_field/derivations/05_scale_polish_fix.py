import numpy as np, time
from pathlib import Path
exec(open(Path(__file__).with_name('04_ridge_pipeline.py')).read().split('lam = lambda x: 6.0 + 60')[0])
rng = np.random.default_rng(5)

# ---- the missing piece: scale selection was snapped to the seeding ladder, never polished ----
# n_eff = sqrt(2)*sum(w)  ->  d n_eff/du = n_eff * M_2         (since dw/du = w*z^2)
# z    = -F*sqrt(n)/0.87  ->  dz/du     = -(sqrt(n)/0.87)*(F_u + F*M_2/2)
# cal  = z - sqrt(2*ln(T/s))  ->  dcal/du = dz/du + 1/sqrt(2*ln(T/s))
def dcal_du(P, t, s, span):
    M = moments(P, t, s)
    if M is None: return np.nan
    n = n_eff(P, t, s)
    if n <= 0: return np.nan
    F_  = M[2]-1.0
    Fu  = M[4]-2*M[2]-M[2]**2
    p   = np.sqrt(2*np.log(max(span/s, np.e)))
    return -(np.sqrt(n)/0.87)*(Fu + F_*M[2]/2.0) + 1.0/p

def polish_scale(P, t_seed, u_lo, u_hi, span, iters=80):
    """Bisect dcal/du = 0 along the ridge. Resolution-free scale selection."""
    def g(u):
        s = np.exp(u); tr = ridge_polish(P, t_seed, s)
        if tr is None: return np.nan, None
        return dcal_du(P, tr, s, span), tr
    a, b = u_lo, u_hi
    ga, _ = g(a); gb, _ = g(b)
    if not (np.isfinite(ga) and np.isfinite(gb)) or ga*gb > 0: return None
    for _ in range(iters):
        m = 0.5*(a+b); gm, tm = g(m)
        if not np.isfinite(gm): return None
        if ga*gm <= 0: b = m
        else: a, ga = m, gm
        if b-a < 1e-12: break
    u = 0.5*(a+b); s = np.exp(u); tr = ridge_polish(P, t_seed, s)
    return (tr, s) if tr is not None else None

def detect2(P, t0, t1, s_lo, s_hi, per_oct=6, kappa=1.0):
    D = detect(P, t0, t1, s_lo, s_hi, per_oct=per_oct, kappa=kappa)
    span = t1-t0; step = np.log(2)/per_oct
    for g_ in D:
        got = None
        for w in (1.0, 2.0, 3.0):                      # widen the bracket if the sign doesn't change
            got = polish_scale(P, g_['t'], np.log(g_['s'])-w*step, np.log(g_['s'])+w*step, span)
            if got: break
        if got:
            tr, s = got
            f, n = F(P,tr,s), n_eff(P,tr,s)
            z = -f*np.sqrt(n)/0.87
            g_.update(t=tr, s=s, F=f, n_eff=n, z=z,
                      cal=z-np.sqrt(2*np.log(max(span/s,np.e))), polished=True)
        else: g_['polished']=False
    return D

lam = lambda x: 6.0 + 60*np.exp(-(x-500.)**2/(2*8.0**2)) + 25*np.exp(-(x-900.)**2/(2*40.**2))
P = sample(lam, 1500.0, 70.0)

print("TEST 1 RERUN — seed independence, WITH scale polishing (bisect dcal/du = 0)\n")
base=None
for po in (3,4,6,9,12):
    D = detect2(P, 0.0, 1500.0, 2.0, 300.0, per_oct=po)
    S = sorted([(g['t'], g['s'], g['cal']) for g in D])
    if base is None:
        base=S; print(f"  per_octave={po:3d}  n={len(D)}   (reference)")
    else:
        dt_=max(abs(a[0]-b[0]) for a,b in zip(S,base))
        ds_=max(abs(np.log(a[1]/b[1])) for a,b in zip(S,base))
        dc_=max(abs(a[2]-b[2]) for a,b in zip(S,base))
        print(f"  per_octave={po:3d}  n={len(D)}   max |dt|={dt_:.2e}s   max |dln s|={ds_:.2e}   max |dcal|={dc_:.2e}")
    for g in sorted(D,key=lambda g:g['t']):
        print(f"      t={g['t']:11.6f}  s={g['s']:10.6f}  cal={g['cal']:9.5f}  polished={g['polished']}")
