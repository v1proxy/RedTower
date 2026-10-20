"""Cover scene for the gantry booklet: the Maag cabinet, the gantry,
the myCobot 280 with Elephant's adaptive gripper tending a basil plant on
Tier B. Everything the gantry and arm contribute comes from the same models
the booklet draws (frame.py / assy.py / arm280.py); pots, plants and lights
are modelled here.

Output: cover_scene.npz, one (V float32 metres, F int32) pair per material,
plus camera/scene metadata. render_cover.py builds the Blender scene from it.
"""
import sys, math, json
import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, ".."), HERE]          # greenhouse/gantry, then here
import numpy as np
import frame as Fr, parts as P, arm280 as A, dae
from kit3d import (ALU, ALU_D, STEEL, BLACKPART, POM, ARM, HILITE, BRASS, PCB,
                   box, cylinder, revolve, extrude, circle_pts, mv, rot)

rng = np.random.default_rng(7)
G = {}                                   # material -> list of (V mm, F)


def add(mat, mesh):
    V, F = mesh
    if len(F):
        G.setdefault(mat, []).append((np.asarray(V, float), np.asarray(F, int)))


def xf(xyz, rpy):
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    R = np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                  [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                  [-sp, cp * sr, cp * cr]])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = xyz
    return T


def apply(T, V):
    return (np.hstack([V, np.ones((len(V), 1))]) @ T.T)[:, :3]


# ------------------------------------------------------------ the gripper
# Elephant Robotics' adaptive gripper meshes (mycobot_ros, mycobot_description/urdf/
# adaptive_gripper), kept beside the arm meshes, outside the repo, like arm280.py's.
GD = os.environ.get("MYCOBOT_GRIPPER", os.path.join(HERE, "..", "..", "..", "..", "..",
                                                     "mycobot_mesh", "adaptive_gripper")) + os.sep
# finger mesh offsets inside gripper_base, from the URDF chain at q = 0;
# the base sits flush on the flange (its mounting face at the flange face)
FING = {"gripper_left1": (0.0, 0.0077), "gripper_left2": (0.0, 0.0075), "gripper_left3": (0.0, 0.0075),
        "gripper_right1": (0.0, 0.0077), "gripper_right2": (0.0, 0.0075), "gripper_right3": (0.0, 0.0075)}
G_MOUNT = xf((0, 0, 0.034), (1.579, 0, 0))


def gripper_local():
    """Gripper meshes in the joint6_flange frame, metres."""
    out = []
    V, F = dae.load(GD + "gripper_base.dae")
    out.append(("grip_body", apply(G_MOUNT, V + [0, 0, -0.012]), F))
    for n, (dx, dy) in FING.items():
        V, F = dae.load(GD + n + ".dae")
        out.append(("grip_link", apply(G_MOUNT, V + [dx, dy - 0.0077, -0.012]), F))
    return out


GRIP = gripper_local()
tips = np.vstack([V for n, V, F in GRIP if n == "grip_link"])
TIP_Z = tips[:, 2].max()
TCP = np.array([0.0, 0.0, TIP_Z * 1000 - 8.0])      # between the finger pads, mm, flange frame


# ------------------------------------------------------------ plants
def leaf(L, W, cup=0.25, droop=0.25, nu=11, nv=7, tip=1.0):
    """Blade along +x from the petiole end, width along y, up +z."""
    V = []
    for i in range(nu):
        u = i / (nu - 1)
        w = W / 2 * (math.sin(math.pi * min(1.0, u ** 0.75)) ** 0.9) * (1 - 0.15 * u) + 0.15
        for j in range(nv):
            v = -1 + 2 * j / (nv - 1)
            x = L * u
            y = w * v
            z = -cup * W * 0.5 * v * v - droop * L * u * u + 0.08 * W * (1 - abs(v)) * math.sin(math.pi * u)
            V.append((x, y, z))
    F = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j; b = a + 1; c = a + nv; d = c + 1
            F += [[a, c, b], [b, c, d]]
    return np.array(V), np.array(F)


def orient(V, yaw, pitch, roll=0.0, at=(0, 0, 0)):
    T = xf(at, (roll, -pitch, yaw))
    return apply(T, V)


def stem(p0, p1, r0, r1, n=7):
    d = np.asarray(p1, float) - p0
    L = np.linalg.norm(d)
    m = cylinder(r0, L, n=n, r2=r1)
    z = d / L
    x = np.cross(z, [0, 0, 1.0]) if abs(z[2]) < 0.99 else np.array([1.0, 0, 0])
    x /= np.linalg.norm(x); y = np.cross(z, x)
    R = np.c_[x, y, z]
    return (m[0] @ R.T + p0, m[1])


def leaf_ovate(L, W, cup=0.3, droop=0.25, nu=12, nv=7, pucker=0.0, r=None,
               teeth=0, tooth=0.0, ruffle=0.0, shape=0.72, blunt=False):
    """Ovate blade: widest at ~40 % of its length, pointed tip, convex
    (edges curl down), a shallow V along the midrib. `teeth` serrations of
    depth `tooth` (fraction of the half width) for mint and parsley;
    `ruffle` waves the margin for lettuce; `shape` moves the widest point."""
    V = []
    for i in range(nu):
        u = i / (nu - 1)
        w = W / 2 * (math.sin(math.pi * u ** shape) ** 0.85) * (1.0 - 0.2 * u) + 0.2
        if blunt:                                  # lettuce: rounded, not pointed
            w = W / 2 * math.sqrt(max(0.0, 1.0 - ((u - 0.58) / 0.62) ** 2)) + 0.2
        if teeth:
            w *= 1.0 - tooth * abs(math.sin(math.pi * u * teeth))
        for j in range(nv):
            v = -1 + 2 * j / (nv - 1)
            z = (-cup * W * 0.5 * v * v - droop * L * u * u + 0.10 * W * abs(v) * (1 - u) * 0.6
                 + 0.06 * W * math.sin(math.pi * u) * (1 - v * v))
            if ruffle:
                z += ruffle * W * abs(v) ** 3 * math.sin(u * 9.0 * math.pi + 1.3 * v)
            if pucker and r is not None and 0 < i < nu - 1 and 0 < j < nv - 1:
                z += r.normal(0, pucker)
            V.append((L * u, w * v, z))
    F = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j; b = a + 1; c = a + nv; d = c + 1
            F += [[a, c, b], [b, c, d]]
    return np.array(V), np.array(F)


def _shoot(p0, d0, n_nodes, L0, r, leaves, stems, scale=1.0, depth=0, yaw0=0.0, wr=(0.58, 0.68)):
    """One basil shoot from p0 along d0: decussate leaf pairs, side shoots."""
    p = np.asarray(p0, float)
    d = np.asarray(d0, float); d /= np.linalg.norm(d)
    for k in range(n_nodes):
        f = k / max(1, n_nodes - 1)
        inter = (30.0 - 12.0 * f) * scale * r.uniform(0.85, 1.15)
        d = d + np.array([r.normal(0, 0.05), r.normal(0, 0.05), 0.12]); d /= np.linalg.norm(d)
        q = p + d * inter
        stems.append(stem(p, q, (3.4 - 1.6 * f) * scale ** 0.5, (3.0 - 1.6 * f) * scale ** 0.5))
        p = q
        L = L0 * (0.75 + 0.55 * math.sin(math.pi * (0.2 + 0.55 * f)) - 0.55 * f) * r.uniform(0.85, 1.1)
        W = L * r.uniform(*wr)
        pitch = math.radians(r.uniform(5, 25) + 30 * f)
        for s in (0, 1):
            yaw = yaw0 + k * math.pi / 2 + s * math.pi + r.normal(0, 0.15)
            pet = (8 + 10 * (1 - f)) * scale
            e = np.array([math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), math.sin(pitch)])
            a = p + pet * e
            stems.append(stem(p, a, 1.2 * scale ** 0.5, 1.0 * scale ** 0.5, n=5))
            Vl, Fl = leaf_ovate(L, W, cup=r.uniform(0.28, 0.42), droop=r.uniform(0.18, 0.32) * (1.1 - 0.6 * f),
                                pucker=0.35, r=r)
            Vl = orient(Vl, yaw, pitch * 0.55, roll=r.normal(0, 0.12), at=a)
            leaves[r.choice(list(leaves))].append((Vl, Fl))
        if depth == 0 and 0 < k < n_nodes - 1 and r.random() < 0.85:
            for s in (0, 1):
                yaw = yaw0 + k * math.pi / 2 + math.pi / 2 + s * math.pi
                dd = np.array([math.cos(yaw) * 0.8, math.sin(yaw) * 0.8, 1.0])
                _shoot(p, dd, 2 + (k < n_nodes - 2), L0 * 0.62, r, leaves, stems, scale * 0.8, 1, yaw + 0.4, wr)
    for t in range(4):                                   # tip cluster
        yaw = yaw0 + t * math.pi / 2 + 0.4
        Vl, Fl = leaf_ovate(L0 * 0.32, L0 * 0.32 * (wr[0] + wr[1]) / 2, cup=0.45, droop=0.0)
        Vl = orient(Vl, yaw, math.radians(58), at=p)
        leaves[list(leaves)[-1]].append((Vl, Fl))
    return p


BASIL = {   # leaf materials, stem material, leaf width / length, flower spikes
    "genovese": (("leaf_a", "leaf_b", "leaf_c"), "stem", (0.58, 0.68), None),
    "purple":   (("leaf_purple", "leaf_purple2"), "stem_purple", (0.55, 0.64), None),
    "thai":     (("leaf_a", "leaf_thai"), "stem_purple", (0.40, 0.48), "flower_purple"),
}


def flower_spike(p, r, mat, h=45.0):
    """Basil inflorescence: a stalk with whorls of small bracts."""
    q = p + np.array([r.normal(0, 4), r.normal(0, 4), h])
    add("stem_purple", stem(p, q, 1.4, 0.8, n=5))
    for t in np.linspace(0.2, 1.0, 7):
        c = p + (q - p) * t
        for k in range(4):
            yaw = k * math.pi / 2 + t * 2.0
            Vl, Fl = leaf_ovate(7.0, 5.0, cup=0.5, droop=0.0, nu=5, nv=3)
            add(mat, (orient(Vl, yaw, math.radians(48), at=c), Fl))


def basil(base, H=170.0, nodes=6, Lmax=58.0, seed=0, young=False, variety="genovese", leaders=None):
    """A topped basil in a 4.5 in pot: two or three leaders from a short
    trunk, opposite decussate leaves, side shoots. Genovese, purple (Dark
    Opal type) or Thai (narrow leaves, purple stems, flower spikes)."""
    r = np.random.default_rng(seed)
    mats, stem_mat, wr, flower = BASIL[variety]
    leaves = {m: [] for m in mats}
    stems = []
    base = np.asarray(base, float)
    trunk = base + np.array([0, 0, 22.0])
    stems.append(stem(base, trunk, 4.0, 3.6))
    nlead = 1 if young else (leaders or r.integers(2, 4))
    scale = H / 175.0
    tops = []
    yaw0 = r.uniform(0, math.pi)
    for i in range(nlead):
        ang = yaw0 + i * 2 * math.pi / nlead
        lean = 0.0 if nlead == 1 else 0.35
        d = np.array([math.cos(ang) * lean, math.sin(ang) * lean, 1.0])
        tops.append(_shoot(trunk, d, nodes if not young else nodes, Lmax, r, leaves, stems,
                           scale=scale, depth=0 if not young else 1, yaw0=ang + 0.8, wr=wr))
    for k_, v in leaves.items():
        for m in v:
            add(k_, m)
    for m in stems:
        add(stem_mat, m)
    if flower and not young:
        for t in tops:
            flower_spike(t, r, flower)
    return max(tops, key=lambda t: t[2])


def mint(base, H=150.0, seed=0):
    """Spearmint: many square stems leaning out of the pot, wrinkled
    serrated leaves in opposite pairs, a dense mound."""
    r = np.random.default_rng(seed)
    base = np.asarray(base, float)
    for i in range(int(r.integers(7, 11))):
        ang = r.uniform(0, 2 * math.pi)
        lean = r.uniform(0.25, 0.9)
        d = np.array([math.cos(ang) * lean, math.sin(ang) * lean, 1.0]); d /= np.linalg.norm(d)
        p = base + np.array([r.normal(0, 12), r.normal(0, 12), 0])
        L = H * r.uniform(0.6, 1.0)
        n = 6
        for k in range(n):
            f = k / (n - 1)
            q = p + d * L / n
            d = d + np.array([0, 0, 0.10]); d /= np.linalg.norm(d)
            add("stem", stem(p, q, 2.2 - f, 1.9 - f, n=5))
            p = q
            Ll = (38 - 16 * f) * r.uniform(0.85, 1.15)
            for s2 in (0, 1):
                yaw = ang + k * math.pi / 2 + s2 * math.pi + r.normal(0, 0.2)
                Vl, Fl = leaf_ovate(Ll, Ll * 0.62, cup=0.35, droop=0.15, pucker=0.9, r=r, teeth=7, tooth=0.10)
                add(r.choice(["leaf_mint", "leaf_mint2"]), (orient(Vl, yaw, math.radians(15 + 30 * f), at=p), Fl))


def parsley(base, H=170.0, seed=0, curly=False):
    """Flat-leaf parsley: a rosette of long petioles from the crown, each
    ending in three toothed, lobed leaflets."""
    r = np.random.default_rng(seed)
    base = np.asarray(base, float)
    for i in range(int(r.integers(14, 20))):
        ang = r.uniform(0, 2 * math.pi)
        tilt = r.uniform(0.15, 0.75)
        L = H * r.uniform(0.65, 1.0)
        tip = base + L * np.array([math.cos(ang) * tilt, math.sin(ang) * tilt, 1.0]) / math.sqrt(1 + tilt ** 2)
        mid = (base + tip) / 2 + np.array([0, 0, 8.0])
        add("stem_light", stem(base, mid, 1.6, 1.3, n=5)); add("stem_light", stem(mid, tip, 1.3, 1.0, n=5))
        # pinnae: a terminal group at the tip and a pair of groups below it
        groups = [(tip, (-0.9, 0.0, 0.9), 1.0)]
        side = base + (tip - base) * 0.68
        groups += [(side, (-1.3,), 0.8), (side, (1.3,), 0.8)]
        for at, dys, sc in groups:
            for dy in dys:
                yaw = ang + dy
                for lobe in (-0.45, 0.0, 0.45):
                    Vl, Fl = leaf_ovate(24 * sc, 15 * sc, cup=0.25 if not curly else 0.6, droop=0.12, nu=8, nv=5,
                                        teeth=5, tooth=0.35, pucker=0.6 if curly else 0.2, r=r)
                    add(r.choice(["leaf_parsley", "leaf_parsley2"]),
                        (orient(Vl, yaw + lobe, math.radians(r.uniform(10, 35)), at=at), Fl))


def chives(base, H=210.0, seed=0):
    """Chives: a clump of hollow, tapering, gently arching leaves and a few
    purple pompom flowers on stiff stalks."""
    r = np.random.default_rng(seed)
    base = np.asarray(base, float)
    for i in range(int(r.integers(34, 46))):
        ang = r.uniform(0, 2 * math.pi)
        lean = r.uniform(0.02, 0.35)
        p = base + np.array([r.normal(0, 9), r.normal(0, 9), 0])
        L = H * r.uniform(0.6, 1.0)
        d = np.array([math.cos(ang) * lean, math.sin(ang) * lean, 1.0]); d /= np.linalg.norm(d)
        for k in range(6):
            f = k / 6
            q = p + d * L / 6
            d = d + np.array([math.cos(ang), math.sin(ang), 0]) * 0.07 * (1 + k); d /= np.linalg.norm(d)
            add("chive", stem(p, q, 2.0 * (1 - 0.8 * f), 2.0 * (1 - 0.8 * (f + 1 / 6)) + 0.2, n=6))
            p = q
    for i in range(3):
        ang = r.uniform(0, 2 * math.pi)
        top = base + np.array([math.cos(ang) * 25, math.sin(ang) * 25, H * 1.05])
        add("chive", stem(base, top, 1.5, 1.2, n=6))
        head = revolve([(0, -11)] + [(11 * math.sin(t), -11 * math.cos(t)) for t in np.linspace(0.2, math.pi - 0.2, 8)]
                       + [(0, 11)], n=14)
        add("flower_purple", mv(head, *(top + [0, 0, 10])))


def thyme(base, H=120.0, seed=0, mat="leaf_thyme"):
    """Thyme or oregano: thin woody stems in a low mound, tiny leaves in
    pairs every few millimetres."""
    r = np.random.default_rng(seed)
    base = np.asarray(base, float)
    for i in range(int(r.integers(32, 42))):
        ang = r.uniform(0, 2 * math.pi)
        lean = r.uniform(0.4, 1.4)
        d = np.array([math.cos(ang) * lean, math.sin(ang) * lean, 1.0]); d /= np.linalg.norm(d)
        p = base + np.array([r.normal(0, 8), r.normal(0, 8), 0])
        L = H * r.uniform(0.6, 1.1)
        n = 10
        for k in range(n):
            q = p + d * L / n
            d = d + np.array([0, 0, 0.12]); d /= np.linalg.norm(d)
            add("stem_woody", stem(p, q, 0.9, 0.8, n=4))
            p = q
            for s2 in (0, 1):
                yaw = ang + k * math.pi / 2 + s2 * math.pi
                Vl, Fl = leaf_ovate(7.5 if mat == "leaf_thyme" else 13.0, 4.0 if mat == "leaf_thyme" else 9.0,
                                    cup=0.3, droop=0.05, nu=4, nv=3)
                add(mat, (orient(Vl, yaw, math.radians(35), at=p), Fl))


def lettuce(base, H=110.0, seed=0, red=False):
    """Loose-leaf lettuce rosette: broad, ruffled leaves from a short core."""
    r = np.random.default_rng(seed)
    base = np.asarray(base, float)
    n = int(r.integers(12, 17))
    for i in range(n):
        f = i / n
        yaw = i * 2.4 + r.normal(0, 0.1)
        L = H * (1.15 - 0.55 * f) * r.uniform(0.85, 1.1)
        pitch = math.radians(20 + 55 * f)
        Vl, Fl = leaf_ovate(L, L * 0.75, cup=-0.15, droop=0.25 * (1 - f), nu=12, nv=9, ruffle=0.12,
                            pucker=0.8, r=r, blunt=True)
        mats = ["leaf_lettuce_red", "leaf_lettuce"] if red else ["leaf_lettuce", "leaf_lettuce2"]
        add(mats[0] if (red and r.random() < 0.7) else r.choice(mats), (orient(Vl, yaw, pitch, at=base + [0, 0, 6]), Fl))


PEPPER = {   # pod materials, pod length, pod radius, pods stand up
    "jalapeno": (("pepper_red", "pepper_green"), (50, 70), 10.5, False),
    "bell":     (("pepper_yellow", "pepper_green"), (40, 55), 21.0, False),
    "orange":   (("pepper_orange", "pepper_green"), (45, 60), 17.0, False),
    "thai":     (("pepper_red", "pepper_red", "pepper_orange"), (30, 42), 4.5, True),
}


def pepper_plant(base, H=380.0, seed=0, kind="jalapeno"):
    """A pepper in a 1 gal pot: forked branching, ovate-lanceolate leaves,
    pods hanging (or standing, for Thai chilies)."""
    pod_mats, pod_len, pod_r, upright = PEPPER[kind]
    r = np.random.default_rng(seed)
    base = np.asarray(base, float)
    fork = base + np.array([0, 0, H * 0.35])
    add("stem", stem(base, fork, 5.5, 4.5, n=8))

    def branch(p, d, L, lvl):
        d = d / np.linalg.norm(d)
        q = p + d * L
        add("stem", stem(p, q, 4.5 - lvl, 3.6 - lvl, n=7))
        for t in np.linspace(0.25, 1.0, 4):
            a = p + (q - p) * t
            for s in (-1, 1):
                yaw = math.atan2(d[1], d[0]) + s * r.uniform(0.9, 1.6)
                Ll = r.uniform(70, 105)
                Vl, Fl = leaf_ovate(Ll, Ll * r.uniform(0.40, 0.48), cup=0.15, droop=0.35, pucker=0.4, r=r)
                Vl = orient(Vl, yaw, math.radians(r.uniform(-10, 20)), roll=r.normal(0, 0.2), at=a)
                add(r.choice(["leaf_b", "leaf_c", "leaf_a"]), (Vl, Fl))
        if lvl < 2:
            for s in (-1, 1):
                yaw = math.atan2(d[1], d[0]) + s * 0.7 + r.normal(0, 0.2)
                nd = np.array([math.cos(yaw) * 0.6, math.sin(yaw) * 0.6, 1.0])
                branch(q, nd, L * 0.8, lvl + 1)
        if lvl >= 1:
            for _ in range(1 + (kind == "thai") * 2):
                if r.random() > 0.85:
                    continue
                a = p + (q - p) * r.uniform(0.6, 0.95)
                Lp = r.uniform(*pod_len)
                taper = 0.35 if kind in ("jalapeno", "thai") else 0.15
                pod = revolve([(0, 0)] + [(pod_r * math.sin(math.pi * min(1, t) ** 0.55) * (1 - taper * t), -Lp * t)
                                          for t in np.linspace(0.05, 1, 14)] + [(0, -Lp)], n=18)
                if upright:
                    pod = rot(pod, rx=math.pi + r.normal(0, 0.3), ry=r.normal(0, 0.3))
                    add(r.choice(pod_mats), mv(pod, *(a + [0, 0, 6])))
                else:
                    add(r.choice(pod_mats), mv(pod, *(a + [0, 0, -6])))
                add("stem", stem(a + [0, 0, -6], a + [0, 0, 6], 2.2, 2.0, n=6))

    for i in range(3):
        ang = r.uniform(0, 2 * math.pi) + i * 2.1
        branch(fork, np.array([math.cos(ang) * 0.7, math.sin(ang) * 0.7, 1.0]), H * 0.28, 0)


def square_pot(cx, cy, z0, top=89.0, bot=72.0, h=89.0):
    def ring(w, z, r=6.0):
        P2 = []
        n = 4
        for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
            for k in range(n + 1):
                a = math.radians(a0 + 90 * k / n)
                P2.append((cx + sx * (w / 2 - r) + r * math.cos(a), cy + sy * (w / 2 - r) + r * math.sin(a), z))
        return np.array(P2)
    rings = [ring(bot, z0), ring(top, z0 + h - 4), ring(top + 5, z0 + h - 3), ring(top + 5, z0 + h),
             ring(top - 2.4, z0 + h), ring(top - 4, z0 + h - 14)]
    V = np.vstack(rings); n = len(rings[0]); F = []
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            a, b, c, d = k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i
            F += [[a, b, c], [a, c, d]]
    c0 = len(V); V = np.vstack([V, [[cx, cy, z0]]])
    for i in range(n):
        F.append([c0, (i + 1) % n, i])
    add("pot", (V, np.array(F)))
    soil(cx, cy, z0 + h - 12, top - 6)


def round_pot(cx, cy, z0, top=165.0, bot=135.0, h=165.0):
    m = revolve([(0, 0), (bot / 2, 0), (top / 2, h - 6), (top / 2 + 4, h - 5), (top / 2 + 4, h),
                 (top / 2 - 1.5, h), (top / 2 - 4, h - 18)], n=40)
    add("pot", mv(m, cx, cy, z0))
    soil(cx, cy, z0 + h - 16, top - 10, round_=True)


def soil(cx, cy, z, w, round_=False):
    n = 10
    V = []
    for i in range(n + 1):
        for j in range(n + 1):
            u, v = -1 + 2 * i / n, -1 + 2 * j / n
            if round_:
                rr = max(abs(u), abs(v)) + 1e-9
                ang = math.atan2(v, u)
                x, y = cx + w / 2 * rr * math.cos(ang), cy + w / 2 * rr * math.sin(ang)
            else:
                x, y = cx + w / 2 * u, cy + w / 2 * v
            V.append((x, y, z + rng.normal(0, 1.4) + 3 * (1 - max(abs(u), abs(v)))))
    F = []
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j; b = a + 1; c = a + n + 1; d = c + 1
            F += [[a, c, b], [b, c, d]]
    add("soil", (np.array(V), np.array(F)))


def tray(z):
    """Folded tray G013: 1317 x 203 pan with a 25 mm upstand."""
    x0, x1, y0, y1, t, h = Fr.SER, Fr.W - Fr.SER, 2.0, Fr.TRAY_D - 1.0, 1.6, 25.0
    add("tray", mv(box(x1 - x0, y1 - y0, t), x0, y0, z))
    for (bx, by, sx, sy) in ((x0, y0, x1 - x0, t), (x0, y1 - t, x1 - x0, t),
                             (x0, y0, t, y1 - y0), (x1 - t, y0, t, y1 - y0)):
        add("tray", mv(box(sx, sy, h), bx, by, z))


def led_bars(z_under):
    for y in (62.0, 146.0):
        for x0 in (Fr.SER + 60.0, Fr.SER + 60.0 + 600.0):
            add("led_body", mv(box(560.0, 22.0, 9.0), x0, y - 11, z_under - 9.0))
            add("led_emit", mv(box(548.0, 12.0, 0.6), x0 + 6, y - 6, z_under - 9.6))
            for xx in (x0 + 30, x0 + 530):
                add("steel", mv(box(4.0, 4.0, 14.0), xx, y - 2, z_under - 0.5))


# ------------------------------------------------------------ build
COLMAP = [(ALU, "alu"), (ALU_D, "alu_dark"), (STEEL, "steel"), (BLACKPART, "black"), (POM, "pom"),
          (ARM, "arm_white"), (HILITE, "alu"), (BRASS, "brass"), (PCB, "pcb"),
          (np.array([0.20, 0.21, 0.22]), "rubber")]


def mat_of(c):
    d = [np.abs(np.asarray(c) - k).sum() for k, _ in COLMAP]
    return COLMAP[int(np.argmin(d))][1]


def solve_pose(target_w, x_car, z_j1, approach_w):
    import ik
    T = Fr.arm_base_frame(x_car, z_j1)
    Ti = np.linalg.inv(T)
    tl = apply(Ti, np.array([target_w]))[0]
    dl = Ti[:3, :3] @ np.asarray(approach_w, float)
    dl /= np.linalg.norm(dl)
    sols = ik.solve(tl, TCP, zdir=dl, seeds=60, rng=3)
    return sols


def room():
    """A living room behind the cabinet, seen only through the frosted
    panels: a window onto the garden at the left, sofa under it, a book
    shelf and a floor lamp behind the cabinet, a house plant. Simple shapes
    on purpose; the panels blur them."""
    r = np.random.default_rng(42)
    def bx(m, x0, y0, z0, x1, y1, z1):
        add(m, mv(box(x1 - x0, y1 - y0, z1 - z0), x0, y0, z0))
    bx("room_floor", -4000, -3000, -20, 6000, 3400, 0)
    # back wall with a 1.8 x 1.6 m window at the left
    W0, W1, Z0, Z1 = -2300, -500, 850, 2450
    bx("room_wall", -4000, 3300, 0, W0, 3420, 2900)
    bx("room_wall", W1, 3300, 0, 6000, 3420, 2900)
    bx("room_wall", W0, 3300, 0, W1, 3420, Z0)
    bx("room_wall", W0, 3300, Z1, W1, 3420, 2900)
    for x in (W0, (W0 + W1) / 2, W1):
        bx("room_frame", x - 25, 3290, Z0, x + 25, 3330, Z1)
    for z in (Z0, Z1):
        bx("room_frame", W0 - 25, 3290, z - 25, W1 + 25, 3330, z + 25)
    bx("room_window", W0 - 100, 3600, Z0 - 150, W1 + 100, 3610, Z1 + 150)
    bx("room_wall", -2600, -3000, 0, -2480, 3420, 2900)       # left wall
    bx("room_wall", 4200, -3000, 0, 4320, 3420, 2900)         # right wall
    bx("room_ceiling", -4000, -3000, 2900, 6000, 3420, 2960)
    # sofa under the window
    sx0, sx1 = -2350, -300
    bx("room_sofa", sx0, 2450, 120, sx1, 3150, 430)
    bx("room_sofa", sx0, 2950, 430, sx1, 3150, 860)
    bx("room_sofa", sx0 - 150, 2450, 120, sx0, 3150, 640)
    bx("room_sofa", sx1, 2450, 120, sx1 + 150, 3150, 640)
    for x0 in (sx0 + 20, sx0 + 700, sx0 + 1380):
        bx("room_cushion", x0, 2470, 430, x0 + 660, 2960, 540)
    for x0 in (sx0 + 120, sx0 + 1600):
        bx(r.choice(["room_book1", "room_book3"]), x0, 2880, 520, x0 + 380, 2960, 860)   # throw pillows
    bx("room_rug", -2500, 1100, 0, 300, 2600, 8)
    bx("room_wood", -1800, 1550, 400, -700, 2150, 440)        # coffee table
    for (x, y) in ((-1770, 1580), (-730, 1580), (-1770, 2120), (-730, 2120)):
        bx("room_dark", x - 15, y - 15, 0, x + 15, y + 15, 400)
    # book shelf behind the cabinet
    X0, X1 = 150, 1550
    for z in (0, 420, 840, 1260, 1680, 2050):
        bx("room_wood", X0, 2950, z, X1, 3290, z + 25)
    bx("room_wood", X0, 2950, 0, X0 + 25, 3290, 2075); bx("room_wood", X1 - 25, 2950, 0, X1, 3290, 2075)
    for z in (25, 445, 865, 1285, 1705):
        x = X0 + 35
        while x < X1 - 60:
            if r.random() < 0.12:                            # a gap, an object
                bx(r.choice(["room_terracotta", "room_dark"]), x, 3050, z, x + 120, 3200, z + r.uniform(120, 220))
                x += 140
                continue
            w = r.uniform(22, 45); h = r.uniform(230, 360)
            bx(r.choice(["room_book1", "room_book2", "room_book3", "room_book4"]), x, 3000, z, x + w, 3260, z + h)
            x += w + r.uniform(0, 6)
    # floor lamp beside the shelf
    add("room_dark", mv(cylinder(150, 25, n=24), 1850, 2900, 0))
    add("room_dark", mv(cylinder(12, 1500, n=10), 1850, 2900, 0))
    add("room_lamp", mv(cylinder(190, 280, n=28, r2=150), 1850, 2900, 1480))
    # house plant, a fiddle-leaf fig in a terracotta pot, at the window's edge
    px_, py_ = -150, 2800
    add("room_terracotta", mv(revolve([(0, 0), (170, 0), (210, 380), (0, 380)], n=28), px_, py_, 0))
    for i in range(26):
        z = 600 + i * 55
        p = np.array([px_ + r.normal(0, 30), py_ + r.normal(0, 30), z])
        Vl, Fl = leaf_ovate(r.uniform(220, 300), r.uniform(150, 190), cup=0.3, droop=0.3, shape=1.0, nu=8, nv=6)
        add("leaf_b", (orient(Vl, i * 2.39, math.radians(r.uniform(-10, 30)), at=p), Fl))
    add("stem_woody", stem(np.array([px_, py_, 380.0]), np.array([px_, py_, 2000.0]), 18, 10, n=8))
    # pendant over the table
    add("room_dark", mv(cylinder(3, 600, n=6), -1250, 1850, 2300))
    add("room_lamp", mv(revolve([(0, 0)] + [(140 * math.sin(t), -140 * math.cos(t)) for t in np.linspace(0.3, 2.6, 10)]
                                + [(0, 120)], n=24), -1250, 1850, 2180))


def enclosure():
    """Frosted polycarbonate on the back, both sides and the top, 4 mm."""
    W, D, H, t = Fr.W, Fr.D, Fr.H, 4.0
    add("frosted", mv(box(W, t, H), 0, D, 0))
    add("frosted", mv(box(t, D, H), -t, 0, 0))
    add("frosted", mv(box(t, D, H), W, 0, 0))
    add("frosted", mv(box(W + 2 * t, D + t, t), -t, 0, H))


POT_Y = 140.0
TARGET_K = 6


def build(x_car, z_j1, q, plant_xy=None, tierB_soil=None):
    cab = Fr.cabinet()
    add("frame", cab)
    for z in Fr.TIERS:
        tray(z + Fr.SER)
    led_bars(Fr.LEVELS[2])                 # under the rails above tier A
    led_bars(Fr.LEVELS[3])                 # above tier B
    led_bars(Fr.LEVELS[4])                 # above tier C
    for p in Fr.gantry_parts(x=x_car, z=z_j1, q=q, grid=0.0):
        nm = mat_of(p.color)
        add(nm, p.mesh)
    # gripper on the flange
    T = Fr.arm_base_frame(x_car, z_j1)
    Tf = A.frames(q)["joint6_flange"].copy()
    for n, V, F in GRIP:
        Vm = apply(Tf, V) * 1000.0
        add(n, (apply(T, Vm), F))
    # plants, as design/solve.py lays them out for the reference build:
    # tier A 8 x 1 gal, tiers B and C 10 x 4.5 in, one row at the tray's back
    zA, zB, zC = (z + Fr.SER + 1.6 for z in Fr.TIERS)
    peppers = ["jalapeno", "bell", "thai", "orange", "jalapeno", "bell", "thai", "orange"]
    for k in range(8):                                     # tier A: peppers, four kinds
        cx = Fr.SER + 82.3 + k * 164.6
        round_pot(cx, 112.0, zA)
        pepper_plant((cx, 112.0, zA + 149), H=rng.uniform(320, 430), seed=100 + k, kind=peppers[k])
    tier_b = ["oregano", "genovese", "thyme", "parsley", "thai", "chives", "genovese", "purple", "parsley", "mint"]
    tier_c = ["lettuce", "young", "lettuce_red", "young_purple", "lettuce", "thyme", "lettuce_red", "young",
              "parsley", "lettuce"]
    for k in range(10):
        cx = Fr.SER + 65.85 + k * 131.7
        for z, kind, sd, tall in ((zB, tier_b[k], k * 10 + 1, 1.0), (zC, tier_c[k], 500 + k * 10, 0.62)):
            square_pot(cx, POT_Y, z, top=114.0, bot=92.0, h=102.0)
            b = (cx, POT_Y, z + 88)
            if kind in ("genovese", "purple", "thai"):
                H = 175.0 if (z == zB and k == TARGET_K) else rng.uniform(140, 195)
                basil(b, H=H, nodes=6, Lmax=60 if kind != "thai" else 48, seed=sd, variety=kind,
                      leaders=3 if (z == zB and k == TARGET_K) else None)
            elif kind in ("young", "young_purple"):
                basil(b, H=rng.uniform(80, 120), nodes=4, Lmax=44, seed=sd, young=True,
                      variety="purple" if kind == "young_purple" else "genovese")
            elif kind == "mint":
                mint(b, H=rng.uniform(140, 175) * tall, seed=sd)
            elif kind == "parsley":
                parsley(b, H=rng.uniform(150, 190) * tall, seed=sd)
            elif kind == "chives":
                chives(b, H=rng.uniform(190, 230), seed=sd)
            elif kind == "thyme":
                thyme(b, H=rng.uniform(100, 130) * tall, seed=sd)
            elif kind == "oregano":
                thyme(b, H=rng.uniform(120, 150), seed=sd, mat="leaf_oregano")
            elif kind in ("lettuce", "lettuce_red"):
                lettuce(b, H=rng.uniform(95, 125), seed=sd, red=(kind == "lettuce_red"))
    enclosure()
    room()

def export(path, cam, wall_y=0.95, look=None):
    out = {}
    for mat, lst in G.items():
        Vs, Fs, off = [], [], 0
        for V, F in lst:
            Vs.append(V); Fs.append(F + off); off += len(V)
        out["V_" + mat] = (np.vstack(Vs) / 1000.0).astype(np.float32)
        out["F_" + mat] = np.vstack(Fs).astype(np.int32)
    out["meta"] = np.array(json.dumps(dict({"camera": cam, "wall_y": wall_y}, **(look or {}))))
    np.savez_compressed(path, **out)
    return {m: len(out["F_" + m]) for m in G}



# The cover pose: carriage 230 right of the basil, J1 at 1320, gripper coming
# in from behind-right. Found by ik.solve with the tier's headroom, the canopy
# and a link-pair clash check (collide.clashes == 0).
COVER_POSE = dict(dx=230.0, zj=1320.0, q=(-31.1, -24.3, 137.8, 10.1, -48.5, -19.3))
CAMERA = {"loc": [1.30, -0.62, 1.47], "target": [0.95, 0.24, 1.25], "lens": 33.0, "fstop": 4.0,
          "exposure": -0.6}
LOOK = {"mist": 9.0, "mist_base": 0.25, "frost": 0.10, "window": 5.0, "lamp": 16.0}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "cover_scene.npz")
    px = Fr.SER + 65.85 + TARGET_K * 131.7
    x_car, zj, q = px + COVER_POSE["dx"], COVER_POSE["zj"], COVER_POSE["q"]
    build(x_car, zj, q)
    T = Fr.arm_base_frame(x_car, zj)
    Tf = A.frames(q)["joint6_flange"].copy()
    tip = apply(T, apply(Tf, np.array([[0, 0, TCP[2] / 1000.0]])) * 1000.0)[0] / 1000.0
    cam = dict(CAMERA, focus=tip.tolist())
    n = export(out, cam, wall_y=0.95, look=LOOK)
    print("wrote", out, sum(n.values()), "faces; fingertips at", np.round(tip, 3))
    print("render: blender -b --factory-startup --python render_cover.py -- --npz", out,
          "--out cover.png --res 2400 1500 --samples 320")
