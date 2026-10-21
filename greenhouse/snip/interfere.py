"""Interference check: moving parts against the body's SDF over the jaw travel,
and the purchased parts against the printed ones."""
import os, sys, math, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gantry"))
import snip_cad as C, assembly as AS, sdf as S
body = C.body()
def pen(mesh, f, tol=0.05):
    V, F = mesh
    d = f(V)
    return float(-d.min()) if d.min() < -tol else 0.0, int((d < -tol).sum())
static = dict((n, m) for n, m, c in AS.parts(0.0, cots=True))
for nm in ("servo", "d405", "insert_pivot", "regulator", "anvil", "pad_fj", "pivot", "cam_screws"):
    print(f"{nm:10s} into body: depth {pen(static[nm], body)[0]:.2f} mm, verts {pen(static[nm], body)[1]}")
for phi in range(0, 61, 5):
    ps = dict((n, m) for n, m, c in AS.parts(phi, cots=True))
    row = [f"phi {phi:2d}:"]
    for nm in ("mj_a", "mj_b", "link", "crank", "horn", "blade", "pad_mj", "dowel_tail", "dowel_crank", "clamp",
               "insert_clamp"):
        d, n = pen(ps[nm], body)
        if d > 0: row.append(f"{nm} {d:.2f}({n})")
    print(" ".join(row), flush=True)
