#!/usr/bin/env python3
"""Render the Herb Tower from the real 3D model: cut-away section, elevation, iso.

This replaces the hand-drawn section. Every line here comes from geometry in
tower3d.py, which is built from brackets.py's member table, the BOM dimensions
and Elephant Robotics' own arm mesh.
"""
import os, sys, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "drawings"))

from tower3d import build, W, D, H, LEVELS, TIERS, TRAY_D, Y_J1   # noqa: E402

INK, DIM, ACC, BLU = "#1d2326", "#5b6770", "#c2410c", "#1d4ed8"
LIGHT = np.array([0.38, -0.72, 0.58]); LIGHT /= np.linalg.norm(LIGHT)


def project(P, view):
    """P is (m,3,3) in mm. Return 2D polys, depth, and rotated normals."""
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ln = np.linalg.norm(n, axis=1)
    keep = ln > 1e-9
    P, n = P[keep], n[keep] / np.maximum(ln[keep], 1e-12)[:, None]
    if view == "section":          # look along +X, cut away the near half
        return P[:, :, [1, 2]], -P[:, :, 0].mean(1), n
    if view == "elevation":        # look along +Y
        return P[:, :, [0, 2]], P[:, :, 1].mean(1), n
    a, b = math.radians(-34), math.radians(20)
    Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    R = Rx @ Rz
    Q = P @ R.T
    return Q[:, :, [0, 2]], Q[:, :, 1].mean(1), n @ R.T


def render(ax, parts, view, cut=None):
    ax.set_aspect("equal"); ax.axis("off")
    XY, DP, CO = [], [], []
    for name, V, T, tint in parts:
        P = V[T]
        if cut is not None:
            P = P[P[:, :, 0].mean(1) <= cut]       # cut-away for the section
            if not len(P):
                continue
        xy, d, n = project(P, view)
        sh = np.abs(n @ LIGHT) * 0.55 + 0.42
        XY.append(xy); DP.append(d)
        CO.append(np.clip(sh[:, None] * np.asarray(tint)[None, :], 0, 1))
    XY, DP, CO = np.concatenate(XY), np.concatenate(DP), np.concatenate(CO)
    o = np.argsort(DP)
    ax.add_collection(PolyCollection(XY[o], facecolors=CO[o], edgecolors="none",
                                     linewidths=0, zorder=2))
    lo, hi = XY.reshape(-1, 2).min(0), XY.reshape(-1, 2).max(0)
    pad = 0.06 * max(hi - lo)
    ax.set_xlim(lo[0] - pad, hi[0] + pad); ax.set_ylim(lo[1] - pad, hi[1] + pad)
    return lo, hi


parts = build()
ntri = sum(len(t) for _, _, t, _ in parts)

fig = plt.figure(figsize=(17.4, 11.0), facecolor="white")
fig.suptitle("Herb Tower   rendered from the 3D model   1397 × 559 × 1829 mm",
             x=0.5, y=0.972, fontsize=16, fontweight="bold", color=INK)
fig.text(0.5, 0.947,
         f"{ntri:,} triangles. Frame from the member table in brackets.py; "
         "arm is Elephant Robotics' own mesh posed through the URDF.",
         ha="center", fontsize=10.5, color=DIM)

axA = fig.add_axes([0.035, 0.07, 0.235, 0.84])
render(axA, parts, "section", cut=640.0)
fig.text(0.035, 0.912, "A   Cut-away section at x = 640", fontsize=11.5,
         fontweight="bold", color=INK)

axB = fig.add_axes([0.305, 0.07, 0.40, 0.84])
render(axB, parts, "elevation")
fig.text(0.305, 0.912, "B   Long elevation", fontsize=11.5,
         fontweight="bold", color=INK)

axC = fig.add_axes([0.725, 0.07, 0.255, 0.84])
render(axC, parts, "iso")
fig.text(0.725, 0.912, "C   Isometric", fontsize=11.5,
         fontweight="bold", color=INK)

head = {TIERS[i]: LEVELS[i + 2] - TIERS[i] for i in range(3)}
fig.text(0.035, 0.038,
         f"Tiers at {TIERS[0]:.1f}, {TIERS[1]:.1f}, {TIERS[2]:.0f} mm with "
         f"{head[TIERS[0]]:.0f}, {head[TIERS[1]]:.0f} and {head[TIERS[2]]:.0f} mm of headroom.  "
         f"Trays {TRAY_D:.0f} mm deep in a {D:.0f} mm cabinet, leaving a "
         f"{D - TRAY_D:.0f} mm gantry corridor.\n"
         f"Arm joint 1 at {Y_J1:.0f} mm behind the front face, side mounted so J1 is "
         "horizontal.  437 mm is the arm EXTENDED, not stowed: folded as tightly as\n"
         "its joint limits allow it is 162.6 mm long, which is what has to clear the "
         "tray line on every tier change.  It does, by 25 mm.",
         fontsize=9.5, color=DIM, va="top")

out = "tower_views.png"
fig.savefig(out, dpi=155, facecolor="white", bbox_inches="tight")
print("saved", out, f"({ntri:,} triangles)")
