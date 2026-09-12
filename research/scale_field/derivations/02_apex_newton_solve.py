import numpy as np
from pathlib import Path
exec(open(Path(__file__).with_name('01_verify_calculus.py')).read().split('# ---------- check every')[0])

def newton_apex(p, t0, s0, iters=60):
    """Solve {F=0, dF/dt=0} exactly. No grid: pure Newton on two analytic functions."""
    t, u = t0, np.log(s0)
    for _ in range(iters):
        s = np.exp(u)
        r = np.array([F(p,t,s), F_t(p,t,s)])
        J = np.array([[F_t(p,t,s), F_u(p,t,s)],
                      [F_tt(p,t,s), F_tu(p,t,s)]])
        try: d = np.linalg.solve(J, -r)
        except np.linalg.LinAlgError: return None
        d[0] = np.clip(d[0], -0.6*s, 0.6*s); d[1] = np.clip(d[1], -0.35, 0.35)
        t, u = t+d[0], u+d[1]
        if abs(d[0]) < 1e-10*s and abs(d[1]) < 1e-12: break
    s = np.exp(u)
    return dict(t=t, s=s, F=F(p,t,s), F_t=F_t(p,t,s), F_tt=F_tt(p,t,s), F_u=F_u(p,t,s))

print("TAPE: background 6/s, bump A at t=500 sigma=8, bump B at t=900 sigma=40\n")
print("Newton solve of {F=0, F_t=0} from deliberately crude seeds")
for seed_t, seed_s, why in [(470, 20, "near A, seeded 30 s early"), (515, 60, "near A, seeded late & coarse"),
                            (870, 60, "near B"), (930, 150, "near B, coarse seed")]:
    r = newton_apex(p, seed_t, seed_s)
    if r: print(f"   seed ({seed_t:4d}, {seed_s:5.1f})  ->  t*={r['t']:8.3f}  s*={r['s']:7.3f} "
                f" |F|={abs(r['F']):.1e} |F_t|={abs(r['F_t']):.1e}   [{why}]")

print("\nclassification at the solution: sign(F_u * F_tt) > 0 = arch apex (pair annihilates going up)")
for seed_t, seed_s in [(470,20),(870,60)]:
    r = newton_apex(p, seed_t, seed_s)
    print(f"   t*={r['t']:8.2f} s*={r['s']:7.2f}   F_u={r['F_u']:+.4f}  F_tt={r['F_tt']:+.3e}"
          f"   product {'>0  arch apex' if r['F_u']*r['F_tt']>0 else '<0  creation-going-up = FORBIDDEN'}")

# --- merge point: two bumps, known separation ---
print("\nMERGE TEST: two sigma=5 bumps on background, separation D; predicted merge s = sqrt(D^2/4 - sigma^2)")
for D in (80.0, 160.0, 300.0):
    lam2 = lambda x, D=D: 4.0 + 120*np.exp(-(x-750+D/2)**2/(2*5.0**2)) + 120*np.exp(-(x-750-D/2)**2/(2*5.0**2))
    q = sample(lam2, 1500.0, 130.0)
    r = newton_apex(q, 750.0, D/2)
    pred = np.sqrt(D**2/4 - 25.0)
    if r: print(f"   D={D:5.0f}   merge s* = {r['s']:7.2f}   predicted {pred:7.2f}   err {100*(r['s']/pred-1):+5.1f}%"
                f"   (t* = {r['t']:.1f}, true midpoint 750)")

# --- ridge tilt on an asymmetric burst ---
print("\nRIDGE TILT: sharp onset at t=700, exponential decay tau=25 -> deepest-t should drift later with s")
lam3 = lambda x: 5.0 + 90*np.where(x>700, np.exp(-(x-700)/25.0), 0.0)
q = sample(lam3, 1500.0, 100.0)
prev=None
for s in (4.0, 8.0, 16.0, 32.0, 64.0):
    t = 705.0
    for _ in range(80):                       # Newton on F_t = 0 (ridge in t at fixed s)
        ft, ftt = F_t(q,t,s), F_tt(q,t,s)
        if ftt == 0: break
        t -= np.clip(ft/ftt, -0.5*s, 0.5*s)
    lag = t-700
    print(f"   s={s:5.1f}   ridge t = {t:8.2f}   lag = {lag:6.2f} s = {lag/s:5.2f}·s   F = {F(q,t,s):+.3f}")
