"""First reach check into the harvest bin at B01: inverse kinematics for the cut point over
the bin with the tool pointing down, and what each answer hits. drop_path.py is its successor."""
import os, sys, math, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gantry"))
import ik, armcheck as AC, frame as Fr, collide as CL, arm280 as A
from scipy.optimize import least_squares
X0, J1Z = 163.5, 1005.0
tray_top = 965.2 + 40 + 2
LIM = np.radians(np.array(A.LIMITS))
def pos_ik(p_t, zmax=-0.5, seeds=40):
    r = np.random.default_rng(2); out = []
    for _ in range(seeds):
        x0 = r.uniform(LIM[:, 0] * 0.95, LIM[:, 1] * 0.95)
        def res(x):
            p, R = ik.tcp(np.degrees(x)); ac = ik.base_to_cab(R[:, 2], vec=True, x=X0, z=J1Z)
            return np.concatenate([p - p_t, [max(0.0, ac[2] - zmax) * 80.0]])
        s = least_squares(res, x0, bounds=(LIM[:, 0], LIM[:, 1]), max_nfev=300)
        q = np.degrees(s.x); p, R = ik.tcp(q); ac = ik.base_to_cab(R[:, 2], vec=True, x=X0, z=J1Z)
        if np.linalg.norm(p - p_t) < 1.0 and ac[2] < zmax + 0.02 and not any(np.abs(q - o).max() < 5 for o in out):
            out.append(q)
    return out
for bin_h, above in ((70.0, 25.0),):
    tgt = np.array([X0 - 70.0, 140.0, tray_top + bin_h + above])
    sols = pos_ik(ik.cab_to_base(tgt, x=X0, z=J1Z))
    print(f"bin {bin_h:.0f} tall: {len(sols)} IK", flush=True)
    for q in sols[:8]:
        qt = tuple(q); c = AC.clashes(qt); s = CL.clashes(qt)
        P = np.vstack([AC.to_cabinet(P, X0, J1Z) for nm, P in AC.arm_pts(qt, 1).items() if nm != "g_base"] + [AC.to_cabinet(AC.tool_in_base(qt), X0, J1Z)])
        p, R = ik.tcp(q); ac = ik.base_to_cab(R[:, 2], vec=True, x=X0, z=J1Z)
        print("   q", np.round(q).tolist(), "axis", np.round(ac, 2).tolist(), "tool-arm", c, "self", bool(s),
              "top z %.0f" % P[:, 2].max(), "low z %.0f" % P[:, 2].min(), flush=True)
