"""The Herb Snip on the arm: self-collision, transit clearance and reach, from
Elephant's link meshes (arm280, collide) and the tool's own meshes."""
from __future__ import annotations
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gantry"))
import arm280 as A
import collide as CL
import frame as Fr
import assembly as AS

FLANGE_FACE = 1.7          # tool frame origin above the flange frame origin


def _surf(V, F, step):
    return CL._surface_points(V, F, step)


_TOOL = {}


def tool_points(phi=0.0, step=1.6):
    key = (round(phi, 1), step)
    if key not in _TOOL:
        pts = []
        for name, (V, F), _ in AS.parts(phi, cots=True):
            if len(F) > 60000:                               # thin the dense printed meshes
                F = F[np.random.default_rng(0).choice(len(F), 60000, replace=False)]
            pts.append(_surf(V, F, step))
        P = np.vstack(pts)
        P[:, 2] += FLANGE_FACE                               # tool frame -> flange frame
        _TOOL[key] = P
    return _TOOL[key]


def flange_T(q):
    T = A.frames(q)["joint6_flange"].copy()
    T[:3, 3] *= A.MM
    return T


def arm_pts(q, which=1):
    return CL.posed_pts(q, which)


def tool_in_base(q, phi=0.0):
    T = flange_T(q)
    P = tool_points(phi)
    return P @ T[:3, :3].T + T[:3, 3]


def clashes(q, phi=0.0, vox=2.0, skip=("joint6_flange",)):
    """Voxels the tool shares with each arm link (the flange itself excluded)."""
    tp = set(map(tuple, np.floor(tool_in_base(q, phi) / vox).astype(np.int64)))
    out = {}
    for name, P in arm_pts(q, 0).items():
        if name in skip:
            continue
        n = len(tp & set(map(tuple, np.floor(P / vox).astype(np.int64))))
        if n:
            out[name] = n
    return out


def to_cabinet(P, x=698.5, z=1000.0):
    T = Fr.arm_base_frame(x, z)
    return P @ T[:3, :3].T + T[:3, 3]


def transit_report(q, phi=0.0):
    tool = to_cabinet(tool_in_base(q, phi))
    arm = np.vstack([to_cabinet(P) for P in arm_pts(q, 0).values()])
    return dict(tool_ymin=float(tool[:, 1].min()), arm_ymin=float(arm[:, 1].min()),
                tool_zmin_rel=float(tool[:, 2].min() - 1000.0), tool_zmax_rel=float(tool[:, 2].max() - 1000.0),
                tool_x=(float(tool[:, 0].min() - 698.5), float(tool[:, 0].max() - 698.5)),
                tool_ymax=float(tool[:, 1].max()))


if __name__ == "__main__":
    q0 = Fr.TIGHT_Q
    for j6 in range(-180, 181, 30):
        q = tuple(q0[:5]) + (j6,)
        c = clashes(q)
        r = transit_report(q)
        print(f"J6 {j6:4d}: clash {c}  tool y {r['tool_ymin']:.1f}..{r['tool_ymax']:.1f} "
              f"(tray line+20 = 223)  arm ymin {r['arm_ymin']:.1f}  tool z {r['tool_zmin_rel']:.0f}..{r['tool_zmax_rel']:.0f} "
              f"x {r['tool_x'][0]:.0f}..{r['tool_x'][1]:.0f}", flush=True)
