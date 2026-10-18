#!/usr/bin/env python3
"""myCobot 280 Pi general arrangement, rendered from the official meshes.

Geometry is Elephant Robotics' own COLLADA from mycobot_description
(elephantrobotics/mycobot_ros, branch noetic), assembled with the joint
transforms in mycobot_280_pi.urdf. Nothing here is drawn by hand.
"""
import sys, os, math
import numpy as np
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dae import load

MESH = "/mnt/user-data/uploads/greenhouse-esphome/mycobot_mesh"
URDF = os.path.join(MESH, "mycobot_280_pi.urdf")

INK, DIM, ACC, BLU = "#1d2326", "#5b6770", "#c2410c", "#1d4ed8"


# ----------------------------------------------------------------- urdf
def rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = (math.cos(r), math.sin(r), math.cos(p),
                              math.sin(p), math.cos(y), math.sin(y))
    return np.array([[cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
                     [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
                     [-sp,   cp*sr,            cp*cr]])


def xform(xyz, r):
    M = np.eye(4); M[:3, :3] = r; M[:3, 3] = xyz
    return M


def rotz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


root = ET.parse(URDF).getroot()
links, joints = {}, []
for l in root.findall("link"):
    v = l.find("visual")
    if v is None:
        continue
    m = v.find("geometry/mesh")
    o = v.find("origin")
    oxyz = np.array([float(x) for x in (o.get("xyz", "0 0 0").split())]) if o is not None else np.zeros(3)
    orpy = [float(x) for x in (o.get("rpy", "0 0 0").split())] if o is not None else [0, 0, 0]
    links[l.get("name")] = (os.path.basename(m.get("filename")), xform(oxyz, rpy(*orpy)))
for j in root.findall("joint"):
    o = j.find("origin")
    oxyz = np.array([float(x) for x in (o.get("xyz", "0 0 0").split())]) if o is not None else np.zeros(3)
    orpy = [float(x) for x in (o.get("rpy", "0 0 0").split())] if o is not None else [0, 0, 0]
    joints.append((j.get("name"), j.get("type"), j.find("parent").get("link"),
                   j.find("child").get("link"), xform(oxyz, rpy(*orpy))))

CACHE = {}


def mesh(fn):
    if fn not in CACHE:
        V, T = load(os.path.join(MESH, fn))
        CACHE[fn] = (V, T)
    return CACHE[fn]


def assemble(q):
    """Return [(verts Nx3 metres, tris)] for every link at joint vector q."""
    world = {}
    out, qi = [], 0
    for name, typ, par, chi, M in joints:
        base = world.get(par, np.eye(4))
        if typ == "revolute":
            M = M @ xform(np.zeros(3), rotz(q[qi])); qi += 1
        world[chi] = base @ M
    world.setdefault("g_base", np.eye(4))
    for lname, (fn, vo) in links.items():
        W = world.get(lname, np.eye(4)) @ vo
        V, T = mesh(fn)
        out.append((np.c_[V, np.ones(len(V))] @ W.T[:, :3], T))
    return out


# ----------------------------------------------------------------- render
def render(ax, parts, view, light=(0.35, -0.75, 0.56)):
    """Painter's-algorithm flat-shaded orthographic projection, in mm."""
    ax.set_aspect("equal"); ax.axis("off")
    L = np.array(light, dtype=float); L /= np.linalg.norm(L)
    polys, shades, depth = [], [], []
    for V, T in parts:
        P = (V * 1000.0)[T]                            # (m,3,3) in mm
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ok = ln > 1e-9
        P, n, ln = P[ok], n[ok], ln[ok]
        n = n / ln[:, None]
        if view == "side":        # look along -Y: plot (X, Z)
            xy, d, nn = P[:, :, [0, 2]], P[:, :, 1].mean(1), n
        elif view == "front":     # look along +X: plot (Y, Z)
            xy, d, nn = P[:, :, [1, 2]], -P[:, :, 0].mean(1), n
        else:                     # iso
            a, b = math.radians(30), math.radians(22)
            R = rotz(a) @ np.array([[1, 0, 0],
                                    [0, math.cos(b), -math.sin(b)],
                                    [0, math.sin(b), math.cos(b)]])
            Q = P @ R.T
            xy, d, nn = Q[:, :, [0, 2]], Q[:, :, 1].mean(1), n @ R.T
        # the Elephant meshes are not consistently wound, so use |n·L|
        c = np.abs(nn @ L) * 0.52 + 0.44
        polys.append(xy); shades.append(c); depth.append(d)
    XY = np.concatenate(polys); SH = np.concatenate(shades); DP = np.concatenate(depth)
    o = np.argsort(DP)
    g = SH[o][:, None] * np.array([[0.95, 0.96, 0.97]])
    ax.add_collection(PolyCollection(XY[o], facecolors=np.clip(g, 0, 1),
                                     edgecolors="none", linewidths=0, zorder=2))
    lo = XY.reshape(-1, 2).min(0); hi = XY.reshape(-1, 2).max(0)
    pad = 0.10 * max(hi - lo)
    ax.set_xlim(lo[0] - pad, hi[0] + pad); ax.set_ylim(lo[1] - pad, hi[1] + pad)
    return lo, hi


HOME = [0, 0, 0, 0, 0, 0]
WORK = [0, math.radians(-38), math.radians(-52), math.radians(-18), 0, 0]

fig = plt.figure(figsize=(16.5, 8.4), facecolor="white")
fig.suptitle("myCobot 280 Pi   general arrangement from the manufacturer's own mesh",
             x=0.5, y=0.972, fontsize=15, fontweight="bold", color=INK)
fig.text(0.5, 0.930,
         "COLLADA from elephantrobotics/mycobot_ros · mycobot_description, "
         "assembled with the joint transforms in mycobot_280_pi.urdf",
         ha="center", fontsize=10, color=DIM)

specs = [("A   Side, home pose", HOME, "side"),
         ("B   Front, home pose", HOME, "front"),
         ("C   Side, working pose", WORK, "side")]
for i, (title, q, view) in enumerate(specs):
    ax = fig.add_axes([0.035 + i * 0.322, 0.07, 0.30, 0.80])
    lo, hi = render(ax, assemble(q), view)
    fig.text(0.035 + i * 0.322, 0.886, title, fontsize=11.5,
             fontweight="bold", color=INK, va="bottom")
    if i == 0:
        ax.plot([lo[0] - 16, lo[0] - 16], [0, hi[1]], color=ACC, lw=1.2)
        for yy in (0, hi[1]):
            ax.plot([lo[0] - 24, lo[0] - 8], [yy, yy], color=ACC, lw=1.2)
        ax.text(lo[0] - 30, hi[1] / 2, f"{hi[1]:.0f} mm\nstowed height", color=ACC,
                fontsize=9.5, rotation=90, ha="right", va="center")
    if i == 1:
        ax.plot([lo[0], hi[0]], [lo[1] - 14, lo[1] - 14], color=ACC, lw=1.2)
        ax.text((lo[0] + hi[0]) / 2, lo[1] - 22, f"{hi[0]-lo[0]:.0f} mm across the base",
                color=ACC, fontsize=9.5, ha="center", va="top")

fig.text(0.035, 0.035,
         "Joint origins, from the URDF:  J1→J2 139.56 mm  ·  J2→J3 −1.0 mm  ·  "
         "J3→J4 110.4 mm  ·  J4→J5 96.0 / 64.62 mm  ·  J5→J6 73.18 mm  ·  "
         "J6→flange 45.6 mm.\nThe published 280 mm figure is the usable working "
         "radius, not the sum of the links.",
         fontsize=9.5, color=DIM, va="top")

out = "/home/claude/outputs/mycobot280_ga.png"
fig.savefig(out, dpi=165, facecolor="white", bbox_inches="tight")
print("saved", out)
