import numpy as np, time
from pathlib import Path
src = open(Path(__file__).with_name('04_ridge_pipeline.py')).read()
exec(src.split('lam = lambda x: 6.0 + 60')[0])          # machinery + detect(), no demo tape

rng = np.random.default_rng(5)
lam = lambda x: 6.0 + 60*np.exp(-(x-500.)**2/(2*8.0**2)) + 25*np.exp(-(x-900.)**2/(2*40.**2))
P = sample(lam, 1500.0, 70.0)

def summarize(D):
    return sorted([(round(g['t'],4), round(g['s'],4), round(g['cal'],4), round(g['persist_oct'],3)) for g in D])

print("TEST 1 — SEED INDEPENDENCE.  The 'resolution free' claim says the seeding ladder must not")
print("         affect any reported number. Vary it 4x and compare.\n")
base = None
for po in (3, 4, 6, 9, 12):
    t0=time.time(); D = detect(P, 0.0, 1500.0, 2.0, 300.0, per_oct=po); el=time.time()-t0
    S = summarize(D)
    if base is None: base = S; note = "(reference)"
    else:
        if len(S) != len(base): note = f"** COUNT CHANGED: {len(S)} vs {len(base)} **"
        else:
            dt_ = max(abs(a[0]-b[0]) for a,b in zip(S,base))
            ds_ = max(abs(np.log(a[1]/b[1])) for a,b in zip(S,base))
            dc_ = max(abs(a[2]-b[2]) for a,b in zip(S,base))
            note = f"max |dt|={dt_:.2e}s   max |dln s|={ds_:.2e}   max |dcal|={dc_:.2e}"
    print(f"  per_octave={po:3d}  n={len(D)}  {el:5.2f}s   {note}")
    for g in sorted(D, key=lambda g: g['t']):
        print(f"      t={g['t']:9.4f}  s={g['s']:8.4f}  cal={g['cal']:7.3f}  oct={g['persist_oct']:.2f}")

print("\n\nTEST 2 — TIME-RESCALING INVARIANCE.  Multiply every timestamp by c.")
print("         t* and s* must scale by exactly c; F, n_eff, z, calibrated must be UNCHANGED.\n")
D1 = detect(P, 0.0, 1500.0, 2.0, 300.0)
for c in (1e-3, 1e3):
    Pc = P*c
    Dc = detect(Pc, 0.0, 1500.0*c, 2.0*c, 300.0*c)
    A = sorted(D1, key=lambda g:g['t']); B = sorted(Dc, key=lambda g:g['t'])
    if len(A)!=len(B): print(f"  c={c:9.0e}   ** COUNT CHANGED {len(B)} vs {len(A)} **"); continue
    et = max(abs(b['t']/c - a['t'])/max(a['t'],1e-9) for a,b in zip(A,B))
    es = max(abs(b['s']/c - a['s'])/a['s'] for a,b in zip(A,B))
    eF = max(abs(b['F']-a['F']) for a,b in zip(A,B))
    en = max(abs(b['n_eff']/a['n_eff']-1) for a,b in zip(A,B))
    ec = max(abs(b['cal']-a['cal']) for a,b in zip(A,B))
    print(f"  c={c:9.0e}   rel err  t*:{et:.2e}  s*:{es:.2e} |  abs err  F:{eF:.2e}  n_eff:{en:.2e}  cal:{ec:.2e}")

print("\n\nTEST 3 — INPUT-ORDER PERMUTATION.  Output must be bitwise identical.\n")
Pp = np.sort(rng.permutation(P))
D2 = detect(Pp, 0.0, 1500.0, 2.0, 300.0)
print("  identical:", summarize(D1) == summarize(D2))

print("\n\nTEST 4 — THINNING.  Keep each print with prob 0.5.  F is invariant to first order, n_eff halves,")
print("         so z should fall by ~sqrt(2) and NO NEW feature may appear.\n")
for trial in range(3):
    keep = rng.random(P.size) < 0.5
    Dh = detect(P[keep], 0.0, 1500.0, 2.0, 300.0)
    matched = [(g, min(D1, key=lambda a: abs(a['t']-g['t']))) for g in Dh]
    new = [g for g,a in matched if abs(g['t']-a['t']) > 1.0*max(g['s'], a['s'])]
    zr  = [g['z']/a['z'] for g,a in matched if abs(g['t']-a['t']) <= 1.0*max(g['s'],a['s'])]
    print(f"  trial {trial+1}: {len(Dh)} features (full tape: {len(D1)})   "
          f"z ratio {np.mean(zr):.3f} (predicted {1/np.sqrt(2):.3f})   NEW features: {len(new)}")
