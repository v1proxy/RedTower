"""The arm's drops into the feeder and the dead-leaf tray: solved and checked.

Needs two meshes that are not in the repo:

    MAAG_ARM_NPZ   the myCobot 280 Pi link meshes, decimated (or MYCOBOT_MESH,
                   Elephant Robotics' .dae folder, as the gantry booklet uses)
    SNIP_STL       the Herb Snip body, snip_body.stl as printed (mount face at
                   z 8.5, flange centre at (0, 12.7)): the tool's real envelope

    python reach.py            # solve, check, write drops.yaml

Every pose is one the arm can hold with the tool clear of the frame, the panel's
opening, tier B's plants (y < 210), the gantry and itself, and with the snip's
wide servo end still inside the cabinet. The numbers are the margins found.
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "gantry"))
sys.path.insert(0, _HERE)

import arm280 as A                     # noqa: E402
import frame as GF                     # noqa: E402

FACE = 1.7                             # flange face off the joint6_flange origin (cover/ik.py)
RELEASE = np.array([-5.0, 3.0, 125.0])  # between the snip's jaws, flange frame
JAW = ((-14.0, 4.0), (-10.0, 16.0), (70.0, 140.0))
LO = np.array([l[0] for l in A.LIMITS])
HI = np.array([l[1] for l in A.LIMITS])
J1_Z = (368.0, 1718.0)                 # the arm's J1 height over the Z travel


def full_meshes():
    """True when the arm's own CAD (Elephant's .dae link meshes) is on disk:
    MYCOBOT_MESH, or mycobot_mesh/ next to the repo."""
    d = os.environ.get("MYCOBOT_MESH")
    if d and os.path.isdir(d):
        A.MESH_DIR = d
    return os.path.exists(os.path.join(A.MESH_DIR, "G_base.dae"))


def load_meshes():
    """The arm's link meshes: the full CAD when it is on disk (drawings use it
    undecimated), else the decimated copy in MAAG_ARM_NPZ. Returns False when
    neither can be found."""
    if full_meshes():
        return True
    npz = os.environ.get("MAAG_ARM_NPZ")
    if npz and os.path.exists(npz):
        d = np.load(npz)
        for _, fn, _, _ in A.LINKS:
            m = (d["V_" + fn].astype(float), d["F_" + fn].astype(int))
            for g in (0.0, 0.0012, 0.0015, 0.002, 0.003):
                A._CACHE[(fn, g)] = m
        return True
    return os.path.exists(os.path.join(A.MESH_DIR, "G_base.dae"))


def snip_tris():
    p = os.environ.get("SNIP_STL")
    if not p or not os.path.exists(p):
        return None
    raw = open(p, "rb").read()
    n = struct.unpack("<I", raw[80:84])[0]
    a = np.frombuffer(raw[84:84 + n * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    T = a["v"].astype(float)
    T[:, :, 1] -= 12.7
    T[:, :, 2] -= 8.5
    return T


def _surface(T, step, seed=0):
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)
    n = np.maximum(1, np.ceil(area / (step * step))).astype(int)
    idx = np.repeat(np.arange(len(T)), n)
    r = np.random.default_rng(seed)
    r1, r2 = r.random(len(idx)), r.random(len(idx))
    f = r1 + r2 > 1
    r1[f], r2[f] = 1 - r1[f], 1 - r2[f]
    return T[idx, 0] + e1[idx] * r1[:, None] + e2[idx] * r2[:, None]


def tool_points(step=4.0):
    T = snip_tris()
    (x0, x1), (y0, y1), (z0, z1) = JAW
    g = [(x, y, z) for x in np.linspace(x0, x1, 7) for y in np.linspace(y0, y1, 9) for z in np.linspace(z0, z1, 15)
         if x in (x0, x1) or y in (y0, y1) or z in (z0, z1)]
    jaw = np.array(g)
    if T is None:
        # no snip mesh: a 40 x 100 x 60 servo block behind the jaw finger, the snip's bounding sizes
        blk = np.array([(x, y, z) for x in (-19.2, 19.2) for y in np.linspace(-62.5, 37.1, 12)
                        for z in np.linspace(-8.5, 60.0, 10)])
        return np.vstack([blk, jaw])
    return np.vstack([_surface(T, step), jaw])


def tool_T(q):
    T = A.frames(q)["joint6_flange"].copy()
    T[:3, 3] *= 1000
    Tz = np.eye(4)
    Tz[2, 3] = FACE
    return T @ Tz


def box_dist(P, lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    d_out = np.linalg.norm(np.maximum(np.maximum(lo - P, P - hi), 0), axis=1)
    inside = np.all((P > lo) & (P < hi), axis=1)
    d_in = np.min(np.minimum(P - lo, hi - P), axis=1)
    return np.where(inside, -d_in, d_out)


class Scene:
    """Everything the arm must miss at one carriage x, as boxes and a gantry point cloud."""

    def __init__(self, xc, boxes, z_ref, crop_x=250.0, crop_z=450.0):
        import collide as CL
        from scipy.spatial import cKDTree
        self.CL = CL
        self.xc, self.boxes, self.z_ref = xc, boxes, z_ref
        parts = GF.gantry_parts(xc, z_ref, q=(0, 0, 0, 0, 0, 0), grid=0.003)
        P = []
        for p in parts[:-8]:
            V, F = p.mesh
            if len(F) == 0:
                continue
            c = V[F].mean(1)
            keep = (np.abs(c[:, 0] - xc) < crop_x) & (np.abs(c[:, 2] - z_ref) < crop_z)
            if keep.any():
                P.append(_surface(V[F[keep]], 3.0))
        self.tree = cKDTree(np.vstack(P))
        self.tool = tool_points()
        self.servo = self.tool[:, 2] < 60.0

    def world(self, v, which=1):
        q, zj = v[:6], v[6]
        Tb = GF.arm_base_frame(self.xc, zj)
        pts = self.CL.posed_pts(q, which=which)
        arm = np.vstack([(np.c_[p, np.ones(len(p))] @ Tb.T)[:, :3] for k, p in pts.items() if k != "g_base"])
        T = Tb @ tool_T(q)
        tool = (np.c_[self.tool, np.ones(len(self.tool))] @ T.T)[:, :3]
        return arm, tool

    def clearance(self, v, inside_x=None, which=1):
        arm, tool = self.world(v, which)
        rep = {}
        for nm, (lo, hi) in self.boxes.items():
            key = nm.split("#")[0]
            d = min(box_dist(arm, lo, hi).min(), box_dist(tool, lo, hi).min())
            rep[key] = min(rep.get(key, 1e9), round(float(d), 1))
        # the gantry moves with J1 in z (carriage, arm plate); the mast is uniform along z
        d, _ = self.tree.query(np.vstack([arm, tool]) + np.array([0, 0, self.z_ref - v[6]]))
        rep["gantry"] = round(float(d.min()), 1)
        if inside_x is not None:
            rep["servo inside"] = round(float(inside_x(tool[self.servo])), 1)
        rep["self"] = bool(self.CL.clean(v[:6]))
        return rep


def ik(scene, target, zdir, seeds=24, rng=0, zj=J1_Z, seed_v=None):
    from scipy.optimize import least_squares
    zd = np.asarray(zdir, float)
    zd = zd / np.linalg.norm(zd)
    tw = np.asarray(target, float)

    def res(v):
        T = GF.arm_base_frame(scene.xc, v[6]) @ tool_T(v[:6])
        p = T[:3, :3] @ RELEASE + T[:3, 3]
        return list(p - tw) + list(200 * (T[:3, 2] - zd))
    lo, hi = np.r_[LO, zj[0]], np.r_[HI, zj[1]]
    r = np.random.default_rng(rng)
    out = []
    starts = [seed_v] if seed_v is not None else []
    starts += [np.r_[r.uniform(LO * 0.9, HI * 0.9), r.uniform(max(zj[0], tw[2] - 300), min(zj[1], tw[2] + 300))]
               for _ in range(seeds)]
    for v0 in starts:
        v0 = np.clip(np.asarray(v0, float), lo + 1e-3, hi - 1e-3)
        sol = least_squares(res, v0, bounds=(lo, hi), xtol=1e-9, ftol=1e-9, max_nfev=800)
        e = np.array(res(sol.x))
        if np.linalg.norm(e[:3]) < 0.5 and np.abs(e[3:]).max() < 1.0:
            out.append(sol.x)
    return out


def best(scene, sols, inside_x=None, ignore=()):
    top = None
    for v in sols:
        c = scene.clearance(v, inside_x, which=1)
        m = min(val for k, val in c.items() if k != "self" and k not in ignore)
        if c["self"] and (top is None or m > top[0]):
            top = (m, v, c)
    return top


def feeder_boxes(f):
    """Obstacles for a feeder drop, cabinet coordinates (right side)."""
    W = GF.W
    P0, P1 = W + 3.5, W + 3.5 + 3.175
    zl = f.rail_v - 20.0
    out = {"side rail below": [(W - 40, 40, zl), (W, 519, zl + 40)],
           "side rail above": [(W - 40, 40, zl + 431.8), (W, 519, zl + 471.8)],
           "back post": [(W - 40, 519, 0), (W, 559, 1829)],
           "plants (y < 210)": [(600, 0, zl + 40), (W - 40, 210, zl + 431.8)],
           "plants below (y < 210)": [(600, 0, GF.LEVELS[1] + 40), (W - 40, 210, zl)],
           "tier rails": [(40, 163, zl), (W - 40, 203, zl + 40)],
           "tier rails#back": [(40, 519, zl), (W - 40, 559, zl + 40)]}
    ys = sorted({0.0, 559.0} | {o[0] for o in f.openings} | {o[1] for o in f.openings})
    zs = sorted({zl - 60, zl + 520} | {o[2] for o in f.openings} | {o[3] for o in f.openings})
    k = 0
    for i in range(len(ys) - 1):
        for j in range(len(zs) - 1):
            yc, zc = (ys[i] + ys[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            if any(o[0] < yc < o[1] and o[2] < zc < o[3] for o in f.openings):
                continue
            out[f"panel#{k}"] = [(P0, ys[i], zs[j]), (P1 + f.BACK, ys[i + 1], zs[j + 1])]   # and the back plate
            k += 1
    # the feeder's own walls and lid, from outside
    wb, wo = W + f.wb, W + f.w_out
    for kk, (a, b) in enumerate(f.mods):
        out[f"feeder floor#{kk}"] = [(wb, a, f.vf), (wo, b, f.vf + f.FLOOR + f.TRAY_H)]   # tray rims and below
        out[f"feeder walls#{kk}a"] = [(wb, a, f.vf), (wo, a + f.WALL, f.vt)]
        out[f"feeder walls#{kk}b"] = [(wb, b - f.WALL, f.vf), (wo, b, f.vt)]
    sw, mg = f.reed_switch()
    for nm, m in (("reed switch", sw), ("reed magnet", mg)):
        V = m[0]
        out[nm] = [(W + V[:, 0].min(), V[:, 1].min(), V[:, 2].min()), (W + V[:, 0].max(), V[:, 1].max(), V[:, 2].max())]
    for kind, (w, u, v), M, L in f.screws():
        if kind == "m4":                                   # the button heads inside, over the openings
            out[f"M4 head#{u:.0f}"] = [(W + w, u - 3.8, v - 3.8), (W + w + 2.2, u + 3.8, v + 3.8)]
    for s in np.linspace(0, 1, 6)[:-1]:
        w0 = f.wb + s * f.DEPTH
        w1 = f.wb + (s + 0.2) * f.DEPTH
        out[f"lid#{s:.1f}"] = [(W + w0, f.mods[0][0], f.lid_under(w1)), (W + w1, f.mods[1][1], f.vt + 60)]
    return out


def tray_boxes():
    import harvest as Hv
    t = Hv.TRAY
    return {"tray and rims": [(t["x0"] - t["rim"], t["y0"] - 30, 0.0), (t["x1"] + t["rim"], t["y1"] + 40, Hv.RIM_Z + 1.6)],
            "handle": [(Hv.HANDLE["x0"], 0.0, 0.0), (Hv.HANDLE["x1"], t["y0"], Hv.HANDLE["z1"])],
            "tier A tray": [(0, 0, GF.LEVELS[1]), (GF.W, 203, GF.LEVELS[1] + 70)],
            "plants A (y < 210)": [(0, 0, GF.LEVELS[1] + 40), (GF.W, 210, GF.LEVELS[2])],
            "back rail": [(0, 519, 0), (GF.W, 559, 40)],
            "tier A rails": [(40, 163, GF.LEVELS[1]), (GF.W - 40, 203, GF.LEVELS[1] + 40)],
            "tier A rails#back": [(40, 519, GF.LEVELS[1]), (GF.W - 40, 559, GF.LEVELS[1] + 40)]}


LIFT = float(os.environ.get("REACH_LIFT", 30.0))      # the through leg, over the release: under the 45° lid
SEEDS = int(os.environ.get("REACH_SEEDS", 30))
RNGS = [int(r) for r in os.environ.get("REACH_RNGS", "0,1,2").split(",")]
ONLY = [x for x in os.environ.get("REACH_ONLY", "").split(",") if x]   # solve these compartments only


def solve_feeder(f, report=print):
    """Pre-pose inside, out through the opening high, down to the release: for
    each compartment. Every leg is solved from many starts; the three poses kept
    are the set with the best worst margin whose joints move least between legs."""
    W = GF.W
    sc = Scene(GF.X_MAX, feeder_boxes(f), z_ref=f.rail_v + 230)
    out = {}
    for k, nm in enumerate(f.NAMES):
        if ONLY and nm not in ONLY:
            continue
        a, b, v0, v1 = f.openings[k]
        y = (a + b) / 2
        x_rel = W + f.wb + 41.0                  # 41 past the panel's outer face: over the tray's back third
        z_rel = f.vf + f.FLOOR + f.TRAY_H + 28.0      # 28 over the tray's rim: the jaws clear it by 10
        z_hi = z_rel + LIFT
        legs = [("inside", (W - 22.0, y, z_hi)), ("through", (x_rel, y, z_hi)), ("release", (x_rel, y, z_rel))]
        cands = []
        for leg, tgt in legs:
            sols = []
            for r in RNGS:                       # several independent sets of starts, pooled
                sols += ik(sc, tgt, (1, 0, 0), seeds=SEEDS, rng=k + 100 * r)
            inside = (lambda tl: W - tl[:, 0].max()) if leg != "inside" else None
            ok = []
            for v in sols:
                c = sc.clearance(v, inside, which=1)
                if c["self"]:
                    ok.append((min(val for kk, val in c.items() if kk != "self"), v, c))
            cands.append(ok)
        top = None
        for m0, v0_, c0 in cands[0]:
            for m1, v1_, c1 in cands[1]:
                if np.abs(v1_[:6] - v0_[:6]).max() > 60 or abs(v1_[6] - v0_[6]) > 80:
                    continue
                for m2, v2_, c2 in cands[2]:
                    if np.abs(v2_[:6] - v1_[:6]).max() > 40 or abs(v2_[6] - v1_[6]) > 120:
                        continue
                    score = min(m0, m1, m2)
                    move = np.abs(v1_ - v0_)[:6].max() + np.abs(v2_ - v1_)[:6].max()
                    key = (round(score, 0), -move)
                    if top is None or key > top[0]:
                        top = (key, [(v0_, c0), (v1_, c1), (v2_, c2)])
        if top is None:
            report(f"  {nm}: no continuous set of clean poses")
            out[nm] = []
            continue
        seq = []
        for (leg, tgt), (v, c) in zip(legs, top[1]):
            seq.append(dict(leg=leg, release_xyz=[round(float(cc), 1) for cc in tgt], carriage_x=round(GF.X_MAX, 2),
                            j1_z=round(float(v[6]), 1), joints_deg=[round(float(j), 1) for j in v[:6]], margins=c))
            worst = sorted((val, kk) for kk, val in c.items() if kk != "self")[:2]
            report(f"  {nm:8s} {leg:8s} J1 z {v[6]:7.1f}  q {np.round(v[:6], 0)}  tightest {worst}")
        out[nm] = seq
    return out


def solve_tray(report=print):
    import harvest as Hv
    t = Hv.TRAY
    xs = np.linspace(t["x0"] + 60, t["x1"] - 60, 5)
    out = {}
    z_rel = Hv.RIM_Z + 55.0
    for i, x in enumerate(xs):
        sc = Scene(float(x), tray_boxes(), z_ref=500.0)
        sols = []
        for y in (280.0, 330.0):
            sols += [(y, v) for v in ik(sc, (x, y, z_rel), (0, 0, -1), seeds=10, zj=(J1_Z[0], 700.0))]
        top = None
        for y, v in sols:
            c = sc.clearance(v)
            m = min(val for k, val in c.items() if k != "self")
            if c["self"] and (top is None or m > top[0]):
                top = (m, v, c, y)
        if top is None:
            report(f"  tray drop {i}: no clean pose")
            continue
        out[f"drop{i + 1}"] = dict(release_xyz=[round(float(x), 1), top[3], z_rel], carriage_x=round(float(x), 1),
                                   j1_z=round(float(top[1][6]), 1), joints_deg=[round(float(j), 1) for j in top[1][:6]],
                                   margins=top[2])
        worst = sorted((val, kk) for kk, val in top[2].items() if kk != "self")[:2]
        report(f"  tray drop {i + 1}: x {x:6.1f} y {top[3]:5.0f}  J1 z {top[1][6]:6.1f}  tightest {worst}")
    return out


def write_yaml(feed, tray, path):
    import harvest as Hv
    f = Hv.FEEDER
    L = ["# Where the Herb Snip puts what it cuts. Written by greenhouse/harvest/reach.py; do not edit by hand.",
         "# Cabinet coordinates, mm (x right, y back from the front face, z up from the frame's foot).",
         "# release_xyz is the point between the jaws; joints_deg are J1..J6 for the myCobot 280 Pi;",
         "# carriage_x and j1_z place the gantry. Margins are the clearances found, mm, with the snip's real body.",
         "# Commissioning converts carriage_x and j1_z to machine coordinates (robot.yaml) by jogging to them.",
         "feeder:",
         f"  side: {f.side}", f"  tier: {f.tier}",
         "  lid_switch: in series with the door reeds (safety chain): the arm has no power while the lid is open"]
    for nm, seq in feed.items():
        L.append(f"  {nm}:")
        for p in seq:
            L.append(f"    - leg: {p['leg']}")
            for k in ("release_xyz", "carriage_x", "j1_z", "joints_deg"):
                L.append(f"      {k}: {json.dumps(p[k])}")
            L.append("      margins: {" + ", ".join(f"{k}: {v}" for k, v in p["margins"].items() if k != "self") + "}")
    L.append("dead_leaf_tray:")
    L.append("  # five drops along the tray, left to right: rotate through them so it fills evenly")
    for nm, p in tray.items():
        L.append(f"  {nm}:")
        for k in ("release_xyz", "carriage_x", "j1_z", "joints_deg"):
            L.append(f"    {k}: {json.dumps(p[k])}")
        L.append("    margins: {" + ", ".join(f"{k}: {v}" for k, v in p["margins"].items() if k != "self") + "}")
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    if not load_meshes():
        sys.exit("reach.py needs the arm meshes: set MAAG_ARM_NPZ or MYCOBOT_MESH")
    if snip_tris() is None:
        print("SNIP_STL not set: using the snip's bounding block instead of its body")
    import harvest as Hv
    print("feeder drops")
    feed = solve_feeder(Hv.FEEDER)
    print("dead-leaf tray drops")
    tray = solve_tray()
    path = os.path.join(_HERE, "drops.yaml")
    write_yaml(feed, tray, path)
    json.dump(dict(feeder=feed, tray=tray), open(os.path.join(_HERE, "drops.json"), "w"), indent=1)
    print("wrote", path)
