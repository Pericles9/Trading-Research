import numpy as np
rng = np.random.default_rng(5)

# ---------- the whole machinery: weighted moments M_0..M_6 at any (t, s) ----------
def moments(prints, t, s, K=6):
    z = (t - prints)/s          # CONVENTION: z = (t - t_i)/s.  F is invariant to this; every ODD t-derivative is not.
    w = np.exp(-0.5*z*z)
    W = w.sum()
    if W <= 0: return None
    return np.array([ (w*z**k).sum()/W for k in range(K+1) ])

def dM_dt(M, k, s):   return (-M[k+1] + k*M[k-1] + M[k]*M[1])/s if k >= 1 else (-M[1] + M[0]*M[1])/s
def dM_du(M, k):      return  M[k+2] - k*M[k] - M[k]*M[2]

def F   (p,t,s): M=moments(p,t,s); return M[2]-1.0
def F_t (p,t,s):
    M=moments(p,t,s); return (-M[3] + 2*M[1] + M[2]*M[1])/s
def F_u (p,t,s):
    M=moments(p,t,s); return M[4] - 2*M[2] - M[2]**2
def F_tt(p,t,s):
    M=moments(p,t,s)
    dM1 = (-M[2] + 1.0 + M[1]**2)          # (1/s) factored out
    dM3 = (-M[4] + 3*M[2] + M[3]*M[1])
    dM2 = (-M[3] + 2*M[1] + M[2]*M[1])
    return (-dM3 + 2*dM1 + M[2]*dM1 + M[1]*dM2)/s**2
def F_tu(p,t,s):
    M=moments(p,t,s)
    A   = -M[3] + 2*M[1] + M[2]*M[1]
    dM1u = M[3] - 1*M[1] - M[1]*M[2]
    dM3u = M[5] - 3*M[3] - M[3]*M[2]
    dM2u = M[4] - 2*M[2] - M[2]*M[2]
    dAu  = -dM3u + 2*dM1u + M[2]*dM1u + M[1]*dM2u
    return (dAu - A)/s
def F_uu(p,t,s):
    M=moments(p,t,s)
    dM4u = M[6] - 4*M[4] - M[4]*M[2]
    dM2u = M[4] - 2*M[2] - M[2]*M[2]
    return dM4u - 2*dM2u - 2*M[2]*dM2u

# ---------- a synthetic print set with real structure ----------
def sample(lam_fn, T, rate_max):
    n = rng.poisson(rate_max*T); c = np.sort(rng.random(n)*T)
    return c[rng.random(n) < lam_fn(c)/rate_max]

lam = lambda x: 6.0 + 60.0*np.exp(-(x-500.0)**2/(2*8.0**2)) + 25*np.exp(-(x-900.)**2/(2*40.**2))
p = sample(lam, 1500.0, 70.0)
print(f"prints: {p.size}\n")

# ---------- check every analytic derivative against central differences ----------
print("analytic vs central difference (max rel err over 40 random probe points)")
pts = [(rng.uniform(200,1200), np.exp(rng.uniform(np.log(2),np.log(120)))) for _ in range(40)]
def cd(f, t, s, wrt, h=1e-5):
    if wrt=='t': return (f(p,t+h*s,s)-f(p,t-h*s,s))/(2*h*s)
    return (f(p,t,s*np.exp(h))-f(p,t,s*np.exp(-h)))/(2*h)
rows = [("F_t ", F_t , F , 't'), ("F_u ", F_u , F , 'u'),
        ("F_tt", F_tt, F_t, 't'), ("F_tu", F_tu, F_t, 'u'), ("F_uu", F_uu, F_u, 'u')]
for name, ana, base, wrt in rows:
    e = [abs(ana(p,t,s)-cd(base,t,s,wrt))/max(abs(cd(base,t,s,wrt)),1e-9) for t,s in pts]
    print(f"   {name}  max rel err = {max(e):.2e}")

# ---------- sanity: uniform tape -> F=0, F_t=0, F_u=0 ----------
u = np.sort(rng.random(400000)*1500.0)
print(f"\nuniform tape at (t=750, s=30):  F={F(u,750,30):+.4f}  F_t={F_t(u,750,30)*30:+.4f}  F_u={F_u(u,750,30):+.4f}")
