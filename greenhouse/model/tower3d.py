#!/usr/bin/env python3
"""Maag as real 3D geometry, in millimetres.

Frame members come from drawings/brackets.py, so the cabinet is built from the
same table the bracket allocation uses. The arm is Elephant Robotics' own mesh
read through drawings/dae.py. Everything else is swept or boxed from the BOM's
real dimensions.

Returns triangle soup: a list of (name, verts Nx3, tris Mx3, tint) parts, which
make_views.py renders. No Blender needed.
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DRAW = os.path.join(os.path.dirname(HERE), "drawings")
sys.path.insert(0, DRAW)
sys.path.insert(0, HERE)

from brackets import W, D, H, SER, LEVELS, TIERS, SHELF, MID, members   # noqa: E402
from dae import load as dae_load                                        # noqa: E402

MESH_DIR = os.environ.get("MYCOBOT_MESH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "mycobot_mesh"))
TRAY_D, UPSTAND, SHEET = 203.0, 25.0, 1.6
POT = 114.3            # G085, 4.5 in square
POT_H = 127.0
PLATE_T = 6.35
ZCOL = (40.0, 80.0)    # C-Beam, modelled as its bounding section
# J1 is anchored to the design rule, not to a number typed into this file:
# ARM_SETBACK in design/params.py is the arm plate, both carriage plates, the
# mast, the X rail, the rear upright and the arm's own 30 mm mount offset.
ARM_SETBACK = 168.35
Y_J1 = D - ARM_SETBACK
Y_PLATE = Y_J1 - PLATE_T - 30.0

ALU, STEEL, SHEETC, DARK = (0.78, 0.80, 0.81), (0.55, 0.58, 0.60), \
                           (0.86, 0.88, 0.88), (0.30, 0.32, 0.33)
POTC, LEAF, SOIL = (0.34, 0.30, 0.28), (0.26, 0.52, 0.31), (0.22, 0.18, 0.15)


# ------------------------------------------------------------------ helpers
def _sweep(poly, length, axis, origin):
    """Sweep a 2D polygon (star-shaped about its centroid) along an axis."""
    poly = np.asarray(poly, dtype=float)
    n = len(poly)
    c = poly.mean(0)
    # lift the profile into 3D: 'x' sweeps along X, profile in (Y,Z), etc.
    def lift(p2, t):
        if axis == "x":
            return np.c_[np.full(len(p2), t), p2[:, 0], p2[:, 1]]
        if axis == "y":
            return np.c_[p2[:, 0], np.full(len(p2), t), p2[:, 1]]
        return np.c_[p2[:, 0], p2[:, 1], np.full(len(p2), t)]

    A, B = lift(poly, 0.0), lift(poly, length)
    ca, cb = lift(c[None, :], 0.0), lift(c[None, :], length)
    V = np.vstack([A, B, ca, cb])
    ia, ib, ic, id_ = 0, n, 2 * n, 2 * n + 1
    T = []
    for i in range(n):
        j = (i + 1) % n
        T += [[ia + i, ia + j, ib + j], [ia + i, ib + j, ib + i]]   # wall
        T += [[ic, ia + j, ia + i], [id_, ib + i, ib + j]]          # caps
    return V + np.asarray(origin, dtype=float), np.asarray(T, dtype=np.int64)


def _box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    x0, y0, z0 = lo; x1, y1, z1 = hi
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    T = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
                  [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
                  [1, 2, 6], [1, 6, 5], [3, 0, 4], [3, 4, 7]], np.int64)
    return V, T


def _merge(parts):
    V, T, base = [], [], 0
    for v, t in parts:
        V.append(v); T.append(t + base); base += len(v)
    return np.vstack(V), np.vstack(T)


def profile_tslot(size=40.0, slot=8.0, depth=6.0):
    """A t-slot cross-section: square with a groove in the middle of each face.

    Star-shaped about the centre, which is what _sweep's fan caps require.
    """
    h, s = size / 2.0, slot / 2.0
    pts = []
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        # corner, then run to the groove on the next face
        pts.append((sx * h, sy * h))
        if (sx, sy) == (1, 1):      # top face, travelling -x
            pts += [(s, h), (s, h - depth), (-s, h - depth), (-s, h)]
        elif (sx, sy) == (-1, 1):   # left face, travelling -y
            pts += [(-h, s), (-h + depth, s), (-h + depth, -s), (-h, -s)]
        elif (sx, sy) == (-1, -1):  # bottom face, travelling +x
            pts += [(-s, -h), (-s, -h + depth), (s, -h + depth), (s, -h)]
        else:                       # right face, travelling +y
            pts += [(h, -s), (h - depth, -s), (h - depth, s), (h, s)]
    return pts


SEC40 = profile_tslot(40.0)
SEC20 = profile_tslot(20.0, 6.0, 4.5)


# ------------------------------------------------------------------ cabinet
def frame():
    out = []
    for cx in (0.0, W - SER):
        for cy in (0.0, D - SER):
            V, T = _sweep(SEC40, H, "z", (cx + SER / 2, cy + SER / 2, 0.0))
            out.append((V, T))
    for mid_, z, axis, a0, a1, c, kind in members():
        if axis == "x":
            o = (a0, c + SER / 2, z + SER / 2)
        else:
            o = (c + SER / 2, a0, z + SER / 2)
        out.append(_sweep(SEC40, a1 - a0, axis, o))
    return _merge(out)


def _pan(y0, depth, z, x0, x1):
    """A folded sheet: floor plus a 25 mm upstand on all four edges."""
    p = [_box((x0, y0, z), (x1, y0 + depth, z + SHEET))]
    p.append(_box((x0, y0, z), (x1, y0 + SHEET, z + UPSTAND)))
    p.append(_box((x0, y0 + depth - SHEET, z), (x1, y0 + depth, z + UPSTAND)))
    p.append(_box((x0, y0, z), (x0 + SHEET, y0 + depth, z + UPSTAND)))
    p.append(_box((x1 - SHEET, y0, z), (x1, y0 + depth, z + UPSTAND)))
    return _merge(p)


def trays():
    out = []
    for z in TIERS:
        out.append(_pan(D - TRAY_D, TRAY_D, z + SER, SER, W - SER))
    out.append(_pan(0.0, D, LEVELS[0] + SER, SER, W - SER))
    return _merge(out)


def gantry(z_arm):
    out = []
    rail_z = LEVELS[-1] - 70.0
    out.append(_sweep(profile_tslot(40.0), W - 2 * SER, "x",
                      (SER, Y_PLATE - 120.0, rail_z)))
    x_col = 470.0
    out.append(_box((x_col - ZCOL[0] / 2, Y_PLATE - 86, 280.0),
                    (x_col + ZCOL[0] / 2, Y_PLATE - 86 + ZCOL[1], rail_z)))
    out.append(_box((x_col - 55, Y_PLATE - 40, z_arm - 66),
                    (x_col + 55, Y_PLATE, z_arm + 66)))
    out.append(_box((x_col - 80, Y_PLATE, z_arm - 80),
                    (x_col + 80, Y_PLATE + PLATE_T, z_arm + 80)))
    return _merge(out), x_col


def pots_and_plants():
    counts = {TIERS[0]: 7, TIERS[1]: 10, TIERS[2]: 10}
    head = {TIERS[i]: LEVELS[i + 2] - TIERS[i] for i in range(3)}
    pots, leaves = [], []
    for z in TIERS:
        n = counts[z]
        span = W - 2 * SER - 60
        step = span / n
        zb = z + SER + SHEET
        for k in range(n):
            cx = SER + 30 + step * (k + 0.5)
            cy = D - TRAY_D / 2
            pots.append(_box((cx - POT / 2, cy - POT / 2, zb),
                             (cx + POT / 2, cy + POT / 2, zb + POT_H)))
            ph = min(head[z] - POT_H - 120, 260)
            leaves.append(_box((cx - 7, cy - 7, zb + POT_H),
                               (cx + 7, cy + 7, zb + POT_H + ph)))
            for j in range(5):
                a = math.radians(72 * j + 18 * (k % 2))
                r0, r1 = 12.0, 12.0 + 58.0
                hz = zb + POT_H + ph * (0.35 + 0.13 * j)
                dx, dy = math.cos(a), math.sin(a)
                leaves.append(_box(
                    (cx + dx * r0 - 26, cy + dy * r0 - 26, hz - 2),
                    (cx + dx * r1 + 26, cy + dy * r1 + 26, hz + 2)))
    return _merge(pots), _merge(leaves)


# ------------------------------------------------------------------ the arm
_ARM_CACHE = {}


def arm(q, at):
    """Elephant Robotics' own mesh, posed and placed at `at` (mm)."""
    import xml.etree.ElementTree as ET

    def rpy(r, p, y):
        cr, sr, cp, sp, cy, sy = (math.cos(r), math.sin(r), math.cos(p),
                                  math.sin(p), math.cos(y), math.sin(y))
        return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                         [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                         [-sp, cp * sr, cp * cr]])

    def xf(xyz, R):
        M = np.eye(4); M[:3, :3] = R; M[:3, 3] = xyz
        return M

    def rotz(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

    root = ET.parse(os.path.join(MESH_DIR, "mycobot_280_pi.urdf")).getroot()
    links, joints = {}, []
    for l in root.findall("link"):
        v = l.find("visual")
        if v is None:
            continue
        o = v.find("origin")
        xyz = [float(x) for x in o.get("xyz", "0 0 0").split()] if o is not None else [0] * 3
        r = [float(x) for x in o.get("rpy", "0 0 0").split()] if o is not None else [0] * 3
        links[l.get("name")] = (os.path.basename(v.find("geometry/mesh").get("filename")),
                                xf(xyz, rpy(*r)))
    for j in root.findall("joint"):
        o = j.find("origin")
        xyz = [float(x) for x in o.get("xyz", "0 0 0").split()] if o is not None else [0] * 3
        r = [float(x) for x in o.get("rpy", "0 0 0").split()] if o is not None else [0] * 3
        joints.append((j.get("type"), j.find("parent").get("link"),
                       j.find("child").get("link"), xf(xyz, rpy(*r))))

    world, qi = {"g_base": np.eye(4)}, 0
    for typ, par, chi, M in joints:
        if typ == "revolute":
            M = M @ xf([0, 0, 0], rotz(q[qi])); qi += 1
        world[chi] = world.get(par, np.eye(4)) @ M

    # the plate face is vertical, so stand the arm's +Z out along -Y into the cabinet
    MOUNT = xf(np.asarray(at, float) / 1000.0,
               rpy(-math.pi / 2, 0, 0) @ rpy(0, 0, math.pi))
    parts = []
    for lname, (fn, vo) in links.items():
        if fn not in _ARM_CACHE:
            _ARM_CACHE[fn] = dae_load(os.path.join(MESH_DIR, fn))
        V, T = _ARM_CACHE[fn]
        Wm = MOUNT @ world.get(lname, np.eye(4)) @ vo
        parts.append(((np.c_[V, np.ones(len(V))] @ Wm.T[:, :3]) * 1000.0, T))
    return _merge(parts)


# ------------------------------------------------------------------ assembly
def build(q=None, z_arm=1180.0):
    q = q or [0, math.radians(-36), math.radians(-54), math.radians(-16), 0, 0]
    g, x_col = gantry(z_arm)
    pots, leaves = pots_and_plants()
    return [
        ("frame", *frame(), ALU),
        ("sheet", *trays(), SHEETC),
        ("gantry", *g, STEEL),
        ("arm", *arm(q, (x_col, Y_PLATE + PLATE_T, z_arm)), DARK),
        ("pots", *pots, POTC),
        ("plants", *leaves, LEAF),
    ]


if __name__ == "__main__":
    for name, V, T, tint in build():
        lo, hi = V.min(0), V.max(0)
        print(f"{name:8} tris={len(T):7d}  bbox "
              f"x[{lo[0]:7.1f},{hi[0]:7.1f}] y[{lo[1]:6.1f},{hi[1]:6.1f}] "
              f"z[{lo[2]:7.1f},{hi[2]:7.1f}]")
