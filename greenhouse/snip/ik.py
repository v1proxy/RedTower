"""Numerical IK for the 280 with the Herb Snip: put the cut point at a position
with the tool axis along a direction (roll left free or set), inside joint limits."""
from __future__ import annotations
import os, sys, math
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gantry"))
import arm280 as A
import frame as Fr

TCP_TOOL = np.array([0.0, -0.19, 88.0])       # cut point in the tool frame
FLANGE_FACE = 1.7
LIM = np.array(A.LIMITS)


def flange_T(q):
    T = A.frames(q)["joint6_flange"].copy()
    T[:3, 3] *= A.MM
    return T


def tcp(q, tool_pt=TCP_TOOL):
    T = flange_T(q)
    p = tool_pt + np.array([0, 0, FLANGE_FACE])
    return T[:3, :3] @ p + T[:3, 3], T[:3, :3]


def cab_to_base(p, x=698.5, z=1000.0, vec=False):
    T = Fr.arm_base_frame(x, z)
    R, t = T[:3, :3], T[:3, 3]
    return R.T @ (np.asarray(p) - (0 if vec else t))


def base_to_cab(p, x=698.5, z=1000.0, vec=False):
    T = Fr.arm_base_frame(x, z)
    return T[:3, :3] @ np.asarray(p) + (0 if vec else T[:3, 3])


def solve(p_target, axis_target, roll_target=None, seeds=24, tool_pt=TCP_TOOL, rng=0):
    """p_target, axis_target in the g_base frame (mm, unit). roll_target: desired
    tool +y axis direction (unit, roughly perpendicular to the axis) or None."""
    r = np.random.default_rng(rng)
    sols = []
    lo, hi = np.radians(LIM[:, 0]), np.radians(LIM[:, 1])
    for k in range(seeds):
        x0 = r.uniform(lo * 0.9, hi * 0.9)

        def res(x):
            q = np.degrees(x)
            p, R = tcp(q, tool_pt)
            e = [(p - p_target) / 1.0, (R[:, 2] - axis_target) * 60.0]
            if roll_target is not None:
                e.append((R[:, 1] - roll_target) * 20.0)
            return np.concatenate(e)
        s = least_squares(res, x0, bounds=(lo, hi), xtol=1e-10, ftol=1e-10, max_nfev=400)
        q = np.degrees(s.x)
        p, R = tcp(q, tool_pt)
        err = np.linalg.norm(p - p_target); aerr = math.degrees(math.acos(np.clip(R[:, 2] @ axis_target, -1, 1)))
        if err < 0.5 and aerr < 1.0:
            sols.append((q, err, aerr))
    # unique
    out = []
    for q, e, a in sols:
        if not any(np.abs(q - o[0]).max() < 3 for o in out):
            out.append((q, e, a))
    return out
