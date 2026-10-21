"""Herb Snip jaw linkage: servo crank -> coupler -> moving-jaw tail (4-bar).
2D in the jaw plane: x lateral (the jaw opens toward +x), z along the tool axis.
Jaw pivot P at the origin; jaw tip direction closed = +z, open by phi -> (sin phi, cos phi).
Units: metres, radians."""
import numpy as np
from scipy.optimize import differential_evolution

PHIS = np.linspace(0, np.radians(60), 241)

def tails(phis, c, beta):
    x0, z0 = c * np.sin(beta), -c * np.cos(beta)          # closed tail point, behind the pivot
    cp, sp = np.cos(phis), np.sin(phis)
    return np.stack([cp * x0 + sp * z0, -sp * x0 + cp * z0], 1)

def thetas(p, phis=PHIS):
    xs, zs, a, b, c, beta, branch = p
    T = tails(phis, c, beta)
    d = T - np.array([xs, zs]); L = np.hypot(d[:, 0], d[:, 1])
    ok = (np.abs(a - b) <= L) & (L <= a + b)
    ang = np.arctan2(d[:, 1], d[:, 0])
    cosg = np.clip((a * a + L * L - b * b) / (2 * a * L), -1, 1)
    th = ang + branch * np.arccos(cosg)
    th = np.where(ok, th, np.nan)
    return np.unwrap(th) if ok.all() else th

def evaluate(p, r_cut=0.020, tau=0.15, d_stem=0.0045):
    th = thetas(p)
    if np.isnan(th).any():
        return None
    MA = np.gradient(th, PHIS); MA = MA * np.sign(np.median(MA))
    span = np.degrees(abs(th[-1] - th[0]))
    sel = PHIS <= np.arcsin(d_stem / r_cut)
    F = tau * MA / r_cut
    return dict(span=span, MA=MA, F=F, Fmin_cut=F[sel].min(), MAmin=MA.min(), th=th)

def cost(x):
    p = tuple(x[:6]) + (1.0 if x[6] > 0 else -1.0,)
    e = evaluate(p)
    if e is None:
        return 1e6
    if e["MAmin"] <= 0.3:
        return 1e5 + (0.3 - e["MAmin"]) * 1e3
    c = max(0, e["span"] - 160) * 5 + max(0, 50 - e["Fmin_cut"]) * 3 - 0.05 * e["Fmin_cut"]
    # keep the crank pin from passing through the jaw pivot region: |S| >= 14 mm
    c += max(0, 0.014 - np.hypot(x[0], x[1])) * 5000
    return c

if __name__ == "__main__":
    bounds = [(-0.020, 0.030), (-0.045, -0.012), (0.005, 0.012), (0.008, 0.040), (0.008, 0.020),
              (np.radians(-90), np.radians(90)), (-1, 1)]
    best = None
    for seed in range(4):
        r = differential_evolution(cost, bounds, seed=seed, maxiter=600, popsize=40, tol=1e-9, polish=True)
        print(seed, round(r.fun, 3), flush=True)
        if best is None or r.fun < best.fun:
            best = r
    x = best.x; p = tuple(x[:6]) + (1.0 if x[6] > 0 else -1.0,)
    e = evaluate(p)
    print("S (mm)", np.round(np.array(p[:2]) * 1000, 2), "a b c (mm)", np.round(np.array(p[2:5]) * 1000, 2),
          "beta", round(np.degrees(p[5]), 1), "branch", p[6])
    print("servo span", round(e["span"], 1), "deg; F min over a 4.5 mm cut at r 20:", round(e["Fmin_cut"], 1), "N")
    for k in range(0, 241, 20):
        print(f"  phi {np.degrees(PHIS[k]):5.1f}  MA {e['MA'][k]:6.2f}  F@20mm {e['F'][k]:6.1f} N")
    np.save("linkage_best.npy", np.array(p, float))
