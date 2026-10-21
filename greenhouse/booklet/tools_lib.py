"""Tools for the Maag booklets' tools pages, modelled from the real thing.

The gantry booklet's tools_page.py drew its tools at true size; this library
goes further, part by part: a snap-off knife with its blade segments and
grip, flush cutters with their pivot, spring and sleeves, a caulking gun with
its cradle, rod, trigger and cartridge, a combination square with its
graduations, F-clamps with a toothed bar and a threaded screw. Each builder
returns [(mesh, colour)], millimetres, lying the way it would on a bench.
"""
import math

import numpy as np

from kit3d import extrude, merge, mv, circle_pts, cylinder, revolve, box, tube
from tools_page import loft, rrect, to_x, rot, CHROME, DARK, RED, BLUE, YEL, GRN, HSS, SCREEN

ORANGE = np.array([0.93, 0.55, 0.15])
WOOD = np.array([0.80, 0.63, 0.40])
WOOD_D = np.array([0.62, 0.45, 0.27])
WHITE = np.array([0.95, 0.95, 0.93])
PLASTIC = np.array([0.88, 0.91, 0.93])
WATER = np.array([0.55, 0.74, 0.90])
TEAL = np.array([0.28, 0.60, 0.66])
STEELD = np.array([0.45, 0.48, 0.52])
LABEL = np.array([0.24, 0.45, 0.74])


# ------------------------------------------------------------------ helpers
def fillet(points, r, n=6):
    """Round every corner of a closed polygon by radius r (or a per-corner list)."""
    P = np.asarray(points, float)
    m = len(P)
    rs = r if isinstance(r, (list, tuple)) else [r] * m
    out = []
    for i in range(m):
        a, b, c = P[i - 1], P[i], P[(i + 1) % m]
        u, v = a - b, c - b
        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        if rs[i] <= 0 or lu < 1e-9 or lv < 1e-9:
            out.append(tuple(b)); continue
        u, v = u / lu, v / lv
        cosang = np.clip(np.dot(u, v), -1, 1)
        ang = math.acos(cosang)
        if ang > math.pi - 1e-3:
            out.append(tuple(b)); continue
        d = min(rs[i] / math.tan(ang / 2), 0.45 * lu, 0.45 * lv)
        rr = d * math.tan(ang / 2)
        p1, p2 = b + u * d, b + v * d
        bis = (u + v) / np.linalg.norm(u + v)
        ctr = b + bis * rr / math.sin(ang / 2)
        a1, a2 = math.atan2(p1[1] - ctr[1], p1[0] - ctr[0]), math.atan2(p2[1] - ctr[1], p2[0] - ctr[0])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            t = a1 + da * k / n
            out.append((ctr[0] + rr * math.cos(t), ctr[1] + rr * math.sin(t)))
    return np.array(out)


def xz(mesh, y0=0.0):
    """A mesh built in (x, y-as-z, thickness-as-y): profile drawn in XY and
    extruded along z, turned to stand in the XZ plane with its thickness in y."""
    V, F = mesh
    return (np.c_[V[:, 0], -V[:, 2] + y0, V[:, 1]], F)


def yz_to_x(mesh):
    """Profile drawn in (u, v) = (y, z), extruded along w: turned so w runs along x."""
    V, F = mesh
    return (np.c_[V[:, 2], V[:, 0], V[:, 1]], F)


def tube_var(path, radii, n=18, caps=True):
    """Elliptical sections (ru across in the path's plane, rv out of it) lofted
    along a polyline; the frame never flips for paths that stay off vertical."""
    P = np.asarray(path, float)
    secs = []
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    for i, p in enumerate(P):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        t = t / np.linalg.norm(t)
        ref = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(t, ref); u /= np.linalg.norm(u)
        v = np.cross(u, t)
        ru, rv = radii[i]
        secs.append(p + np.outer(ru * np.cos(ang), u) + np.outer(rv * np.sin(ang), v))
    return loft(secs, cap=caps)


def ridged(r_out, r_in, n_ridges, h, z0=0.0, seg=6):
    """A knurled or ribbed cylinder: n ridges round it."""
    k = n_ridges * seg
    a = np.linspace(0, 2 * math.pi, k, endpoint=False)
    rr = r_in + (r_out - r_in) * (0.5 + 0.5 * np.cos(a * n_ridges))
    return extrude(np.c_[rr * np.cos(a), rr * np.sin(a)], h, z0=z0)


def helix_rod(r, L, pitch, depth, n=28, steps=8):
    """A threaded rod along z, 0 .. L."""
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rings = []
    for z in np.arange(0.0, L + 1e-9, pitch / steps):
        ph = (z / pitch - th / (2 * math.pi)) % 1.0
        rr = r - depth * np.abs(2 * ph - 1.0)
        rings.append(np.c_[rr * np.cos(th), rr * np.sin(th), np.full(n, z)])
    return loft(rings, cap=True)


# ------------------------------------------------------------------ cutting
def utility_knife():
    """18 mm snap-off knife, 160 long: body, rubber grip panels, ridged
    slider, steel nose, a segmented blade out 30, the end cap."""
    out = []
    body = fillet([(0, 3), (6, 0), (128, 0), (150, 7), (156, 13), (150, 20), (130, 26), (8, 26), (0, 20)],
                  [3, 4, 6, 4, 3, 4, 6, 4, 3])
    out.append((extrude(body, 18.0, z0=-9.0), YEL))
    grip = rrect(84.0, 16.0, 6.0, cx=66.0, cy=12.0)
    for z0 in (9.0, -9.8):
        out.append((extrude(grip, 0.8, z0=z0), DARK))
        for k in range(7):
            x = 30.0 + k * 12.0
            out.append((box(2.4, 10.0, 0.5, c=(x, 7.0, z0 + (0.8 if z0 > 0 else -0.5))), DARK))
    nose = fillet([(124, 0), (128, 0), (150, 7), (156, 13), (150, 20), (130, 26), (124, 26)], [0, 3, 4, 3, 4, 3, 0])
    for z0 in (9.0, -9.6):
        out.append((extrude(nose, 0.6, z0=z0), CHROME))
    out.append((box(26.0, 2.2, 12.0, c=(58.0, 26.0, -6.0)), DARK))
    for k in range(5):
        out.append((box(2.0, 3.0, 10.0, c=(60.0 + k * 4.8, 28.0, -5.0)), DARK))
    cap = fillet([(0, 3), (6, 0), (11, 0), (11, 26), (8, 26), (0, 20)], [3, 3, 0, 0, 3, 3])
    out.append((extrude(cap, 18.8, z0=-9.4), DARK))
    out.append((box(1.2, 14.0, 19.0, c=(5.0, 6.0, -9.5)), np.array([0.15, 0.16, 0.17])))
    # blade: segments parallel to its slanted front edge, 9 apart, 0.35 snap lines
    s = 10.4 / 18.0
    xf = lambda y, k: 186.0 - s * (y - 4.0) - 9.0 * k            # noqa: E731
    for k in range(5):
        a0, a1 = xf(4.0, k + 1) + 0.35, xf(4.0, k)
        b0, b1 = xf(22.0, k + 1) + 0.35, xf(22.0, k)
        poly = np.array([(a0, 4.0), (a1, 4.0), (b1, 22.0), (b0, 22.0)])
        out.append((extrude(poly, 0.5, z0=-0.25), CHROME))
    out.append((extrude(np.array([(150.0, 4.0), (186.0, 4.0), (184.8, 5.6), (150.0, 5.6)]), 0.52, z0=-0.26), HSS))
    return out


def flush_cutters():
    """125 mm flush cutters: two halves lapped at the pivot, rivet, return
    spring, red dipped sleeves."""
    out = []
    t = 4.4
    half = [(-30.0, 0.3), (-24.0, 3.6), (-14.0, 7.4), (-5.0, 9.2)]
    for a in np.linspace(math.radians(110), math.radians(-20), 12):
        half.append((9.2 * math.cos(a), 9.2 * math.sin(a)))
    half += [(30.0, -7.0), (30.0, -13.0), (8.0, -10.5), (-2.0, -8.5), (-6.0, -4.0), (-7.0, 0.3)]
    H = np.array(half)
    jaw = np.array([(-30.0, 0.3), (-24.0, 3.6), (-14.0, 7.4), (-6.5, 8.6), (-6.5, 0.3)])
    Hb, jawb = H * np.array([1.0, -1.0]), jaw * np.array([1.0, -1.0])
    out.append((extrude(H, t, z0=0.0), STEELD))           # half A: lower lap, its jaw full thickness
    out.append((extrude(jaw, t, z0=t), STEELD))
    out.append((extrude(Hb[::-1], t, z0=t), STEELD))      # half B: upper lap
    out.append((extrude(jawb[::-1], t, z0=0.0), STEELD))
    for sg in (1, -1):                                     # polished cutting faces along the jaws
        bev = np.array([(-30.0, 0.3 * sg), (-7.0, 0.3 * sg), (-7.5, 2.6 * sg), (-26.0, 1.6 * sg)])
        if sg < 0:
            bev = bev[::-1]
        out.append((extrude(bev, 0.2, z0=2 * t), HSS))
    out.append((cylinder(4.2, 2 * t + 1.2, c=(0, 0, -0.6), n=32), CHROME))
    out.append((mv(revolve([(0, 0), (5.2, 0), (4.6, 1.0), (2.5, 1.7), (0, 1.9)], n=32), 0, 0, 2 * t + 0.6), CHROME))
    spring = tube(np.array([(12.0, 4.5, t), (21.0, 2.0, t), (24.0, 0.0, t), (21.0, -2.0, t), (12.0, -4.5, t)]), 0.7, 10)
    out.append((spring, CHROME))
    for sg in (1, -1):
        P = [(27.0, -10.0 * sg, t), (40.0, -12.5 * sg, t), (60.0, -16.5 * sg, t), (85.0, -20.0 * sg, t),
             (108.0, -22.5 * sg, t), (122.0, -23.2 * sg, t), (126.0, -23.4 * sg, t), (128.0, -23.5 * sg, t)]
        R = [(5.0, 5.0), (5.6, 5.4), (6.6, 6.0), (7.4, 6.4), (7.2, 6.2), (6.4, 5.8), (5.0, 4.6), (2.5, 2.4)]
        out.append((tube_var(P, R, n=20), RED))
        out.append((tube_var(P[:2] + [(42.0, -12.8 * sg, t)], [(5.3, 5.3), (5.8, 5.6), (5.9, 5.7)], n=20), DARK))
    return out


# ------------------------------------------------------------------ sealing
def caulking_gun():
    """Skeleton caulking gun with a 300 ml cartridge: half-pipe cradle, front
    plate with the nozzle notch, rear block, pistol grip, trigger, plunger rod
    with its hook and disc. The cartridge's axis is x."""
    out = []
    a = np.radians(np.linspace(200, 340, 24))
    U = np.r_[np.c_[26.6 * np.cos(a), 26.6 * np.sin(a)], np.c_[25.2 * np.cos(a[::-1]), 25.2 * np.sin(a[::-1])]]
    out.append((yz_to_x(mv(extrude(U, 207.0), 0, 0, 10.0)), RED))
    for a0 in (200.0, 340.0):                       # rolled edges of the cradle
        ra = math.radians(a0)
        out.append((mv(to_x(cylinder(1.3, 207.0, n=12)), 10.0, 25.9 * math.cos(ra), 25.9 * math.sin(ra)), RED))
    fp = fillet([(-31, -31), (31, -31), (31, 29), (8.5, 29), (8.5, 0), (6.0, -6.0), (0.0, -8.5), (-6.0, -6.0),
                 (-8.5, 0), (-8.5, 29), (-31, 29)], [6, 6, 6, 2, 0, 0, 0, 0, 0, 2, 6])
    out.append((yz_to_x(mv(extrude(fp, 3.0), 0, 0, 217.0)), RED))
    rb = rrect(58.0, 54.0, 9.0, cy=-4.0)
    out.append((yz_to_x(mv(extrude(rb, 20.0), 0, 0, -10.0)), RED))
    grip = fillet([(-16, -26), (12, -26), (16, -42), (18, -112), (11, -125), (-6, -125), (-13, -112), (-18, -42)], 6)
    out.append((xz(extrude(grip, 26.0, z0=-13.0)), DARK))
    for k in range(4):
        rib = fillet([(14.5, -60 - 14 * k), (19, -60 - 14 * k), (19, -66 - 14 * k), (14.5, -66 - 14 * k)], 1.5)
        out.append((xz(extrude(rib, 22.0, z0=-11.0)), DARK))
    trig = fillet([(14, -24), (24, -27), (42, -38), (50, -56), (49, -102), (42, -115), (33, -113), (31, -62),
                   (20, -42)], 5)
    out.append((xz(extrude(trig, 16.0, z0=-8.0)), RED))
    out.append((to_x(cylinder(3.6, 180.0, n=20, c=(0, 0, -168.0))), CHROME))
    hook = tube(np.array([(-168.0, 0, 0), (-176.0, 0, 0), (-183.0, 0, -6.0), (-183.0, 0, -14.0),
                          (-176.0, 0, -20.0), (-160.0, 0, -20.0)]), 3.6, 14)
    out.append((hook, CHROME))
    out.append((box(4.0, 20.0, 30.0, c=(-14.0, -10.0, 14.0)), CHROME))       # release plate
    out.append((to_x(cylinder(23.0, 3.0, n=40, c=(0, 0, 10.0))), DARK))
    out.append((to_x(cylinder(24.3, 192.0, n=48, c=(0, 0, 13.0))), WHITE))
    out.append((to_x(cylinder(24.45, 120.0, n=48, c=(0, 0, 45.0))), LABEL))
    out.append((to_x(cylinder(24.5, 30.0, n=48, c=(0, 0, 95.0))), WHITE))
    out.append((to_x(cylinder(24.3, 12.0, n=48, c=(0, 0, 205.0), r2=8.0)), WHITE))
    noz = to_x(revolve([(0, 0), (7.5, 0), (7.0, 6), (2.2, 72), (0, 74)], n=36))
    out.append((mv(noz, 217.0, 0, 0), PLASTIC))
    return out


def neutral_silicone():
    """The cartridge alone, for parts lists."""
    return [(m, c) for m, c in caulking_gun()[-5:]]


def ipa_and_cloth():
    """500 ml isopropyl alcohol: bottle, label, ribbed cap; a folded
    microfibre cloth beside it."""
    out = []
    prof = [(0, 0), (30, 0), (33, 2), (34, 7), (34, 120), (33, 130), (28, 142), (18, 154), (13, 160), (13, 168), (0, 168)]
    out.append((revolve(prof, n=56), PLASTIC))
    out.append((cylinder(34.25, 70.0, c=(0, 0, 30.0), n=56), LABEL))
    out.append((cylinder(34.3, 18.0, c=(0, 0, 64.0), n=56), WHITE))
    out.append((ridged(15.8, 15.1, 36, 20.0, z0=164.0), DARK))
    out.append((mv(revolve([(0, 0), (15.4, 0), (14.8, 2.0), (10.0, 3.2), (0, 3.4)], n=48), 0, 0, 184.0), DARK))
    lay = [(55.0, -55.0), (185.0, -55.0), (185.0, 55.0), (55.0, 55.0)]
    out.append((extrude(fillet(lay, 4), 2.6), TEAL))
    up = [(58.0, -52.0), (183.0, -52.0), (183.0, 4.0), (58.0, 4.0)]
    out.append((extrude(fillet(up, 4), 2.6, z0=2.6), TEAL))
    out.append((mv(to_x(cylinder(2.6, 125.0, n=16)), 58.0, -52.0, 2.6), TEAL))
    return out


def kettle_and_mug():
    """An electric kettle on its base and a mug of hot water."""
    out = []
    out.append((cylinder(86.0, 14.0, n=64), DARK))
    out.append((revolve([(0, 14), (80, 14), (84, 19), (82, 60), (76, 150), (68, 188), (0, 188)], n=64), CHROME))
    out.append((revolve([(0, 188), (67, 188), (62, 196), (36, 203), (0, 204)], n=64), DARK))
    out.append((box(24.0, 10.0, 8.0, c=(-12.0, -5.0, 203.0)), DARK))
    hP = [(-62.0, 0, 182.0), (-92.0, 0, 178.0), (-110.0, 0, 150.0), (-112.0, 0, 100.0), (-104.0, 0, 55.0),
          (-88.0, 0, 34.0), (-78.0, 0, 30.0)]
    out.append((tube_var(hP, [(11, 9)] * len(hP), n=20), DARK))
    sP = [(66.0, 0, 140.0), (84.0, 0, 160.0), (98.0, 0, 178.0), (106.0, 0, 188.0)]
    out.append((tube_var(sP, [(20, 14), (14, 10), (10, 7), (8.5, 6)], n=24, caps=True), CHROME))
    out.append((mv(box(4.0, 16.0, 90.0), 76.0, -8.0, 40.0), WATER))
    out.append((box(14.0, 10.0, 10.0, c=(-96.0, -5.0, 32.0)), RED))
    mx = 200.0
    mug = [(0, 0), (42, 0), (43.5, 2.5), (43.5, 93), (42.5, 95), (40.5, 95), (39.5, 93), (39.5, 7), (0, 7)]
    out.append((mv(revolve(mug, n=56), mx, 0, 0), RED * 0.9 + 0.08))
    out.append((cylinder(39.5, 1.0, c=(mx, 0, 76.0), n=48), WATER))
    mh = [(mx + 41.0, 0, 80.0), (mx + 62.0, 0, 76.0), (mx + 70.0, 0, 52.0), (mx + 62.0, 0, 26.0), (mx + 41.0, 0, 22.0)]
    out.append((tube_var(mh, [(6.0, 4.5)] * len(mh), n=16), RED * 0.9 + 0.08))
    return out


# ------------------------------------------------------------------ measuring
def tape_measure():
    """5 m tape: case with its rubber band, side medallions, lock, belt clip,
    a cupped blade out 120 with graduations, the hook and its rivets."""
    out = []
    side = fillet([(-34, -34), (34, -34), (34, 34), (-34, 34)], 13)
    out.append((xz(extrude(side, 30.0, z0=-15.0)), YEL))
    band = fillet([(-36, -36), (36, -36), (36, 36), (-36, 36)], 14)
    out.append((xz(extrude(band, 16.0, z0=-8.0)), DARK))
    for y0 in (15.0, -15.8):
        out.append((mv(xz(extrude(circle_pts(21.0, 48), 0.8)), 0, y0 + 0.8, 0), DARK))
        out.append((mv(xz(extrude(circle_pts(4.0, 24), 1.2)), 0, y0 + 1.2 if y0 > 0 else y0 + 0.4, 0), CHROME))
    out.append((box(18.0, 10.0, 6.0, c=(8.0, -5.0, 35.5)), DARK))
    clip = fillet([(-20, -26), (20, -26), (20, 26), (-20, 26)], 6)
    out.append((mv(xz(extrude(clip, 1.4)), 0, -16.6, 0), CHROME))
    y = np.linspace(-12.5, 12.5, 15)
    sag = 2.6 * (1 - (y / 12.5) ** 2)
    sec = np.r_[np.c_[y, sag], np.c_[y[::-1], sag[::-1] + 0.35]]
    blade = yz_to_x(extrude(sec, 118.0))
    out.append((mv(blade, 36.0, 0, -29.0), YEL * 0.96 + 0.03))
    for k in range(12):
        x = 40.0 + k * 10.0
        L = 9.0 if k % 5 == 0 else 5.0
        out.append((box(0.8, L, 0.2, c=(x, -12.0, -29.0 + 0.35 + 2.6 * (1 - (11.5 / 12.5) ** 2) - 0.05)), DARK))
    hook = box(1.2, 27.0, 11.0, c=(154.0, -13.5, -38.5))
    out.append((hook, CHROME))
    out.append((box(10.0, 18.0, 0.8, c=(145.0, -9.0, -27.8)), CHROME))
    for yy in (-4.0, 4.0):
        out.append((cylinder(1.3, 0.8, c=(149.0, yy, -27.0), n=16), CHROME))
    return out


def calipers():
    """150 mm digital calipers: beam, outside and inside jaws, slider with
    display, buttons, thumb roller, lock screw and the depth rod."""
    out = []
    out.append((extrude(np.array([(-20, 0), (215, 0), (215, 16), (-20, 16)]), 3.5), CHROME))
    out.append((extrude(fillet([(-20, 16), (0, 16), (0, -38), (-3, -43), (-12, -38), (-20, 0)], 1.5), 3.5), CHROME))
    out.append((extrude(fillet([(-20, 16), (-20, 34), (-15, 41), (-10, 34), (-4, 16)], 1.0), 3.5), CHROME))
    sx = 40.0
    out.append((extrude(rrect(66, 36, 5.0, cx=sx + 30, cy=4), 9.0, z0=-3.0), DARK))
    out.append((extrude(fillet([(sx, -14), (sx, -38), (sx + 3, -43), (sx + 12, -38), (sx + 20, -14)], 1.5), 3.5),
                CHROME))
    out.append((extrude(fillet([(sx + 4, 16), (sx + 9, 34), (sx + 14, 41), (sx + 16, 34), (sx + 14, 16)], 1.0),
                        3.5), CHROME))
    out.append((extrude(rrect(32, 13, 1.5, cx=sx + 36, cy=9), 0.8, z0=6.0), SCREEN))
    for k, bx in enumerate((sx + 14, sx + 50, sx + 58)):
        out.append((cylinder(2.6, 1.6, c=(bx, -4.0 if k else 9.0, 6.0), n=20), np.array([0.62, 0.65, 0.68])))
    out.append((mv(ridged(5.0, 4.5, 18, 4.0), sx + 8, -10.5, -0.2), CHROME))
    out.append((cylinder(2.8, 5.0, c=(sx + 30, 20.5, 2.0), n=16), CHROME))
    out.append((box(160.0, 3.0, 1.2, c=(sx + 60, 6.0, -1.3)), CHROME))
    for k in range(16):
        out.append((box(0.4, 4.0 if k % 5 else 6.0, 0.1, c=(-15.0 + k * 10.0, 11.0, 3.5)), DARK))
    return out


def combination_square():
    """300 mm combination square: ruled blade with its groove, cast head with
    the 90 and 45 degree faces, bubble vial, knurled lock, scriber."""
    out = []
    out.append((box(300.0, 25.0, 1.6, c=(0, 0, 9.0)), CHROME))
    out.append((box(300.0, 1.0, 0.25, c=(0, 12.0, 10.6)), STEELD))
    for k in range(59):
        x = 5.0 + k * 5.0
        L = 7.0 if k % 2 == 1 else 4.0
        out.append((box(0.4, L, 0.06, c=(x, 25.0 - L - 0.6, 10.6)), DARK))
    head = fillet([(70, -78), (96, -78), (96, 4), (96, 28), (70, 28), (70, 4), (46, 4), (70, -20)],
                  [3, 3, 0, 2, 2, 0, 0, 0])
    head = fillet([(70, -78), (96, -78), (96, 28), (70, 28), (70, 4), (48, 4), (48, 0), (70, -22)],
                  [3, 3, 2, 2, 0, 1, 1, 0])
    out.append((extrude(head, 22.0), DARK))
    out.append((extrude(rrect(10, 34, 4.5, cx=83, cy=-46), 0.6, z0=22.0), np.array([0.12, 0.13, 0.14])))
    out.append((mv(rot(cylinder(3.6, 30.0, n=20, c=(0, 0, -15.0)), rx=90), 83.0, -46.0, 21.4), GRN))
    out.append((mv(to_x(ridged(9.0, 8.2, 24, 10.0)), 96.0, 14.0, 11.0), CHROME))
    out.append((mv(to_x(cylinder(2.0, 6.0, n=16)), 106.0, 14.0, 11.0), CHROME))
    out.append((mv(rot(cylinder(1.6, 14.0, n=16, r2=0.3), rx=90), 83.0, -78.0, 11.0), CHROME))
    return out


# ------------------------------------------------------------------ holding and lifting
def f_clamp(open_=150.0):
    """F-clamp 300: toothed steel bar, fixed and sliding cast jaws with pads,
    a threaded screw with its swivel pad and a turned wooden handle. In XZ,
    thickness along y."""
    out = []
    teeth = [(0.0, -10.0), (300.0, -10.0), (300.0, 10.0)]
    for k in range(48, 0, -1):
        x = 8.0 + k * 6.0
        teeth += [(x, 10.0), (x - 3.0, 11.2)]
    teeth += [(8.0, 10.0), (0.0, 10.0)]
    out.append((xz(extrude(np.array(teeth), 6.0, z0=-3.0)), STEELD))
    fj = fillet([(-10, 14), (14, 14), (14, -22), (10, -96), (-4, -104), (-12, -94), (-8, -22), (-10, -14)],
                [3, 3, 6, 4, 4, 4, 6, 3])
    out.append((xz(extrude(fj, 12.0, z0=-6.0)), RED))
    out.append((mv(to_x(cylinder(10.0, 3.0, n=32)), 12.0, 0, -92.0), DARK))
    sx = open_
    sj = fillet([(sx - 12, 15), (sx + 14, 15), (sx + 14, -24), (sx + 12, -84), (sx + 18, -100), (sx - 4, -104),
                 (sx - 10, -88), (sx - 10, -24), (sx - 12, -15)], [3, 3, 6, 4, 4, 4, 4, 6, 3])
    out.append((xz(extrude(sj, 12.0, z0=-6.0)), RED))
    rod = to_x(helix_rod(5.0, 120.0, 3.0, 0.9))
    out.append((mv(rod, sx - 90.0, 0, -92.0), CHROME))
    out.append((mv(to_x(cylinder(10.0, 3.0, n=32)), sx - 94.0, 0, -92.0), DARK))
    out.append((mv(to_x(cylinder(4.5, 4.0, n=24)), sx - 91.0, 0, -92.0), CHROME))
    hd = revolve([(0, 0), (9, 0), (12, 8), (13, 30), (14, 52), (12, 74), (10, 80), (0, 80)], n=40)
    out.append((mv(to_x(hd), sx + 30.0, 0, -92.0), WOOD))
    for k in range(3):
        out.append((mv(to_x(cylinder(13.6, 1.4, n=40)), sx + 52.0 + k * 9.0, 0, -92.0), WOOD_D))
    out.append((mv(to_x(cylinder(7.0, 6.0, n=24)), sx + 24.0, 0, -92.0), CHROME))
    return out


def f_clamps():
    a = f_clamp(150.0)
    b = [(mv(m, 0, 70.0, 0), c) for m, c in f_clamp(205.0)]
    return a + b


def pry_bar_and_block():
    """380 mm flat pry bar with a nail slot at each end and its bent end, and
    a 2 x 4 offcut."""
    out = []
    W = 32.0
    plan = [(0.0, -W / 2), (380.0, -W / 2), (380.0, -4.0), (366.0, -1.0), (366.0, 1.0), (380.0, 4.0), (380.0, W / 2),
            (0.0, W / 2), (0.0, 4.0), (14.0, 1.0), (14.0, -1.0), (0.0, -4.0)]
    V, F = extrude(fillet(plan, [3, 3, 1, 0.5, 0.5, 1, 3, 3, 1, 0.5, 0.5, 1]), 6.0)
    V = V.copy()
    x0, R = 320.0, 70.0
    m = V[:, 0] > x0
    th = (V[m, 0] - x0) / R
    rr = R - V[m, 2]
    V[m, 0] = x0 + rr * np.sin(th)
    V[m, 2] = R - rr * np.cos(th)
    out.append(((V, F), BLUE))
    blk = extrude(fillet([(0, 0), (140, 0), (140, 89), (0, 89)], 2.5), 38.0)
    out.append((mv(blk, 60.0, 50.0, 0.0), WOOD))
    for k, yy in enumerate((62.0, 80.0, 101.0, 118.0)):
        out.append((box(138.0, 1.2, 0.3, c=(61.0, yy + (k % 2) * 3.0, 38.0)), WOOD_D))
    return out


def step_drill():
    """Step drill to 22: ten steps on a cone, one straight flute, a three-flat shank."""
    prof = [(0, 0), (5, 0), (5, 40)]
    r, z = 11.0, 40.0
    for k in range(10):
        prof += [(r, z), (r, z + 4.0)]
        z += 4.0
        r -= 1.0
    prof += [(1.5, z + 6), (0, z + 8)]
    body = to_x(revolve(prof[2:] + [(0, z + 8), (0, 40)], n=48))
    a = np.linspace(0, 2 * math.pi, 48, endpoint=False)
    rr = np.minimum(5.0, 4.3 / np.maximum(np.abs(np.cos((a % (2 * math.pi / 3)) - math.pi / 3)), 1e-3))
    shank = to_x(extrude(np.c_[rr * np.cos(a), rr * np.sin(a)], 40.0))
    out = [(shank, HSS), (body, HSS)]
    fl = [(40.0, 0.0)]
    r, z = 11.0, 40.0
    for k in range(10):
        fl += [(z, r + 0.05), (z + 4.0, r + 0.05)]
        z += 4.0
        r -= 1.0
    fl += [(z + 6, 1.6), (z + 6, 0.0)]
    flute = extrude(np.array(fl), 1.6, z0=-0.8)
    out.append(((np.c_[flute[0][:, 0], flute[0][:, 2], flute[0][:, 1]], flute[1]), np.array([0.25, 0.27, 0.29])))
    return out


def hacksaw():
    """300 mm hacksaw: tubular frame, a toothed blade under tension, the
    closed pistol grip with its hand hole, the tensioning wing nut. Flat in XY."""
    out = []
    H = 90.0
    path = [(0, 0, 0), (0, H - 15, 0)]
    for k in range(1, 6):
        a = math.pi - k * math.pi / 2 / 6
        path.append((15 + 15 * math.cos(a), H - 15 + 15 * math.sin(a), 0))
    path += [(15, H, 0), (330, H, 0)]
    for k in range(1, 6):
        a = math.pi / 2 - k * math.pi / 2 / 6
        path.append((330 + 15 * math.cos(a), H - 15 + 15 * math.sin(a), 0))
    path += [(345, H - 15, 0), (345, 0, 0)]
    from tools_page import sweep
    ring = np.array([(8 * math.cos(a), 6 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 17)[:-1]])
    out.append((sweep(path, ring), BLUE))
    teeth = [(-4.0, 6.0), (-4.0, -4.6)]
    p = 1.41
    x = -4.0
    while x < 350.0:
        teeth += [(x + p * 0.7, -6.0), (x + p, -4.6)]
        x += p
    teeth += [(352.0, -4.6), (352.0, 6.0)]
    out.append((extrude(np.array(teeth), 0.65, z0=-0.33), CHROME))
    for xx in (-2.0, 347.0):
        out.append((cylinder(2.6, 8.0, c=(xx, 0.0, -4.0), n=16), CHROME))
    grip = fillet([(-6, -14), (-6, 66), (-24, 92), (-70, 84), (-74, 20), (-52, -26), (-20, -30)], [4, 6, 14, 14, 10, 14, 8])
    hole = fillet([(-22, -6), (-22, 50), (-34, 66), (-56, 60), (-58, 18), (-44, -8)], [3, 6, 8, 8, 8, 6])
    out.append((extrude(grip, 26.0, z0=-13.0, holes=[hole]), DARK))
    out.append((extrude(fillet([(-6, 8), (-6, 56), (-12, 58), (-12, 8)], 1.5), 27.0, z0=-13.5), RED))
    wing = fillet([(-8, -4), (8, -4), (14, 8), (8, 4), (-8, 4), (-14, 8)], 1.5)
    out.append((mv(to_x(extrude(wing, 6.0, z0=-3.0)), 360.0, 0.0, 0.0), CHROME))
    out.append((mv(to_x(cylinder(3.0, 14.0, n=16)), 347.0, 0, 0), CHROME))
    return out
