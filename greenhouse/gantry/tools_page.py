"""Tools the gantry build needs, modelled at their real dimensions.

Each builder returns a list of (mesh, colour) in millimetres. The booklet
page scales each tool to its own cell, and prints its true size beside it.
"""
import math
import numpy as np
from kit3d import (extrude, cylinder, revolve, circle_pts, merge, mv, box,
                   STEEL, BLACKPART, ALU, ALU_D)
import earcut
from kit3d import rot as _rot


def rot(mesh, rx=0.0, ry=0.0, rz=0.0):
    """kit3d.rot in degrees."""
    return _rot(mesh, math.radians(rx), math.radians(ry), math.radians(rz))

RED = np.array([0.80, 0.22, 0.20])
BLUE = np.array([0.20, 0.36, 0.72])
YEL = np.array([0.93, 0.74, 0.20])
GRN = np.array([0.42, 0.70, 0.40])
DARK = np.array([0.22, 0.24, 0.26])
CHROME = np.array([0.78, 0.80, 0.83])
HSS = np.array([0.55, 0.57, 0.60])
SCREEN = np.array([0.55, 0.62, 0.55])


# ------------------------------------------------------------------ helpers
def loft(sections, cap=True):
    """Join closed rings of equal vertex count. sections: list of (n, 3)."""
    S = [np.asarray(s, float) for s in sections]
    n = len(S[0])
    V = np.vstack(S)
    F = []
    for k in range(len(S) - 1):
        a0, b0 = k * n, (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            F += [[a0 + i, a0 + j, b0 + j], [a0 + i, b0 + j, b0 + i]]
    if cap:
        for k, s in ((0, S[0]), (len(S) - 1, S[-1])):
            # cap in the ring's own plane: project on its best-fit plane
            c = s.mean(0)
            u, sv, vt = np.linalg.svd(s - c)
            pts2 = (s - c) @ vt[:2].T
            _, T = earcut.triangulate(pts2)
            F += (T + k * n).tolist()
    return (V, np.array(F, int))


def sweep(path, ring2d, cap=True):
    """Sweep a 2D ring (in the u, v plane) along a polyline lying in the XY
    plane, so the frame never flips: u = t x z, v = z."""
    P = np.asarray(path, float)
    secs = []
    for i, p in enumerate(P):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        t = t / np.linalg.norm(t)
        u = np.cross(t, [0, 0, 1.0]); u /= np.linalg.norm(u)
        v = np.array([0, 0, 1.0])
        secs.append(p + ring2d[:, :1] * u + ring2d[:, 1:2] * v)
    return loft(secs, cap)


def rrect(w, h, r, n=8, cx=0.0, cy=0.0):
    pts = []
    for (x, y, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + x + r * math.cos(a), cy + y + r * math.sin(a)))
    return np.array(pts)


def arc_pts(c, R, a0, a1, n):
    a = np.linspace(a0, a1, n)
    return np.c_[c[0] + R * np.cos(a), c[1] + R * np.sin(a)]


def to_x(mesh):
    """Turn a Z-axis part to lie along +X."""
    return rot(mesh, ry=90)


# ------------------------------------------------------------------- tools
def hex_key(af, L1, L2, ball=True):
    """ISO 2936 L key, long series, ball end on the long arm. Lies in XY:
    short arm along +Y from the bend, long arm along +X."""
    R = af / math.sqrt(3)                     # circumradius
    hexr = np.array([(R * math.cos(a), R * math.sin(a))
                     for a in np.linspace(0, 2 * math.pi, 7)[:-1] + math.pi / 6])
    rb = 1.5 * af
    path = [(0, L2, 0), (0, rb, 0)]
    for k in range(1, 8):
        a = math.pi + k * (math.pi / 2) / 8   # 180 -> 270 deg about (rb, rb)
        path.append((rb + rb * math.cos(a), rb + rb * math.sin(a), 0))
    path += [(rb, 0, 0), (L1 - (af * 1.2 if ball else 0), 0, 0)]
    path = path[::-1]
    out = [(sweep(path, hexr), CHROME)]
    if ball:
        x0 = L1 - af * 1.2
        neck = to_x(cylinder(af * 0.32, af * 0.5, n=16))
        prof = [(0, -af * 0.55)] + [(af * 0.55 * math.cos(t), af * 0.55 * math.sin(t))
                                    for t in np.linspace(-math.pi / 2, math.pi / 2, 9)[1:-1]] + [(0, af * 0.55)]
        ball_m = to_x(revolve(prof, n=18))
        out += [(mv(neck, x0, 0, 0), CHROME), (mv(ball_m, x0 + af * 0.65, 0, 0), CHROME)]
    return out


def hex_key_set():
    """2, 2.5, 3, 4 mm, long series, laid side by side."""
    out = []
    for i, (af, L1, L2) in enumerate(((2.0, 100, 18), (2.5, 112, 20), (3.0, 125, 23), (4.0, 140, 29))):
        for m, c in hex_key(af, L1, L2):
            out.append((mv(m, 0, 0, -i * 9.0), c))
    return out


def spanner(af1=8.0, af2=10.0, L=128.0, t=3.2, w=9.0, jaw=15.0):
    """Thin double open-end spanner, 8 x 10, heads at 15 deg. Flat in XY."""
    RA, RB = af1 * 1.18 + 1.0, af2 * 1.18 + 1.0
    pts = []

    def head(c, R, s, phi, a0, a1):
        beta = math.asin(s / 2 / R)
        e = np.array([math.cos(phi), math.sin(phi)]); nn = np.array([-e[1], e[0]])
        db = R - 1.08 * s
        # arc to the jaw's first edge, the jaw, then the rest of the arc
        # (all angles kept increasing through a0..a1)
        ph = phi
        while ph < a0:
            ph += 2 * math.pi
        out = list(arc_pts(c, R, a0, ph - beta, 18))
        out.append(c + db * e - s / 2 * nn)
        for u in np.linspace(0, math.pi, 9)[1:-1]:
            out.append(c + db * e + (s / 2) * (-math.cos(u) * nn - math.sin(u) * e))
        out.append(c + db * e + s / 2 * nn)
        out += list(arc_pts(c, R, ph + beta, a1, 18))
        return out

    aA = math.asin(w / 2 / RA); aB = math.asin(w / 2 / RB)
    pts += head(np.array([0.0, 0.0]), RA, af1, math.pi + math.radians(jaw), aA, 2 * math.pi - aA)
    pts += head(np.array([L, 0.0]), RB, af2, math.radians(jaw), math.pi + aB, 3 * math.pi - aB)
    poly = np.array(pts)
    return [(extrude(poly, t), CHROME)]


def nut_driver(af=5.5):
    """5.5 mm nut driver: handle, shaft, hex socket. Along +X."""
    handle = revolve([(0, 0), (11, 0), (13, 8), (13.5, 60), (12, 90), (8, 100), (6, 104), (0, 104)], n=28)
    shaft = cylinder(3.0, 80, n=18, c=(0, 0, 104))
    R = af / 2 / math.cos(math.pi / 6)
    sock = extrude(circle_pts(4.6, 24), 14, z0=182, holes=[circle_pts(R, 6, start=math.pi / 6)])
    return [(to_x(handle), YEL), (to_x(shaft), CHROME), (to_x(sock), CHROME)]


def drill_bit(d=5.2, L=86.0, flute=52.0):
    """HSS jobber bit: shank, two-flute twisted body, 118 deg point. Along +X."""
    r = d / 2
    shank = cylinder(r, L - flute, n=20)
    # cross-section: a circle with two flutes cut in it (two lobes)
    ang = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    rad = np.where(np.cos(2 * ang) > -0.2, r, r * 0.55 + 0.45 * r * (np.cos(2 * ang) + 1) / 0.8)
    sec = np.c_[rad * np.cos(ang), rad * np.sin(ang)]
    lead = 28.0
    z0 = L - flute
    secs = []
    for k in range(41):
        z = z0 + flute * k / 40
        th = 2 * math.pi * (z - z0) / lead
        c, s = math.cos(th), math.sin(th)
        secs.append(np.c_[sec[:, 0] * c - sec[:, 1] * s, sec[:, 0] * s + sec[:, 1] * c, np.full(len(sec), z)])
    body = loft(secs)
    tip = cylinder(r * 0.98, r / math.tan(math.radians(59)), n=20, c=(0, 0, L), r2=0.05)
    return [(to_x(shank), HSS), (to_x(body), HSS), (to_x(tip), HSS)]


def m5_tap():
    """M5 x 0.8 hand tap, three straight flutes, square drive; plus a
    T-handle tap wrench. Tap along +X."""
    L, Lt = 58.0, 16.0
    shank = cylinder(2.3, L - Lt - 6, n=18, c=(0, 0, 6))
    sq = box(4.0, 4.0, 6.0, c=(-2.0, -2.0, 0.0))
    ang = np.linspace(0, 2 * math.pi, 36, endpoint=False)
    secs = []
    for k in range(int(Lt / 0.2) + 1):
        z = L - Lt + 0.2 * k
        crest = 2.5 - 0.27 * abs(((z / 0.8) % 1.0) - 0.5) * 2      # thread rings
        cham = min(1.0, (L - z) / 3.0) if z > L - 3.0 else 1.0
        rr = np.where(np.cos(3 * ang) > -0.35, crest * (0.85 + 0.15 * cham), crest * 0.62)
        secs.append(np.c_[rr * np.cos(ang), rr * np.sin(ang), np.full(len(ang), z)])
    thr = loft(secs)
    tap = [(to_x(shank), HSS), (to_x(sq), HSS), (to_x(thr), HSS)]
    # wrench, clamped on the square, axis along X; bar along Y
    chuck = to_x(cylinder(7.0, 26.0, n=24, c=(0, 0, -20.0)))
    bar = rot(cylinder(4.5, 150.0, n=18, c=(0, 0, -75.0)), rx=90)
    grips = [mv(rot(cylinder(6.0, 52.0, n=18), rx=-90), -7, 23, 0),
             mv(rot(cylinder(6.0, 52.0, n=18), rx=90), -7, -23, 0)]
    wr = [(chuck, DARK), (mv(bar, -7, 0, 0), CHROME)] + [(g, DARK) for g in grips]
    return tap + [(mv(m, -60.0, 0, 0), c) for m, c in wr]


def hacksaw():
    """300 mm hacksaw: tubular frame, blade, pistol grip. Flat in XY."""
    fr = []
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
    ring = np.array([(9 * math.cos(a), 6 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]])
    fr.append((sweep(path, ring), BLUE))
    blade = box(350.0, 12.0, 0.65, c=(-2.0, -6.0, -0.3))
    grip = extrude(np.array([(-10, -10), (-10, 60), (-30, 85), (-62, 70), (-55, 10), (-40, -20), (-12, -20)]),
                   26, z0=-13)
    return fr + [(blade, STEEL), (mv(grip, 0, 0, 0), DARK)]


def spirit_level(L=600.0):
    """600 mm box level, 56 x 25, with the centre and plumb vials. Along X."""
    body = extrude(rrect(L, 56.0, 3.0), 25.0, z0=-12.5)
    out = [(rot(body, rx=90), ALU)]
    for x, (w, h) in ((0.0, (60.0, 18.0)), (L / 2 - 50, (18.0, 40.0))):
        win = extrude(rrect(w, h, 4.0), 1.2, z0=12.5)
        out.append((rot(mv(win, x, 0, 0), rx=90), DARK))
    vial = to_x(cylinder(5.0, 44.0, n=18, c=(0, 0, -22.0)))
    out.append((mv(vial, 0, -14.5, 0), GRN))
    caps = [extrude(rrect(14, 56.4, 2.0, cx=sx * (L / 2 - 6)), 25.6, z0=-12.8) for sx in (-1, 1)]
    out += [(rot(c, rx=90), RED) for c in caps]
    return out


def calipers():
    """150 mm digital calipers: beam with fixed jaws, slider with display."""
    beam = extrude(np.array([(-20, 0), (215, 0), (215, 16), (-20, 16)]), 3.5)
    fixed = extrude(np.array([(-20, 16), (0, 16), (0, -38), (-3, -42), (-12, -38), (-20, 0)]), 3.5)
    upper = extrude(np.array([(-20, 16), (-20, 34), (-14, 40), (-8, 34), (0, 16)]), 3.5)
    sx = 40.0
    slider = extrude(rrect(64, 34, 4.0, cx=sx + 30, cy=4), 9.0, z0=-3.0)
    sjaw = extrude(np.array([(sx, -13), (sx, -38), (sx + 3, -42), (sx + 12, -38), (sx + 20, -13)]), 3.5)
    disp = extrude(rrect(34, 14, 1.5, cx=sx + 36, cy=8), 0.8, z0=6.0)
    return [(beam, CHROME), (fixed, CHROME), (upper, CHROME), (slider, DARK), (sjaw, CHROME),
            (disp, SCREEN)]


def tape_measure():
    """5 m tape: case, blade out 120 mm, hook."""
    case = extrude(rrect(68, 68, 14), 32.0, z0=-16.0)
    blade = box(120.0, 0.4, 25.0, c=(34.0, -30.0, -12.5))
    hook = box(1.0, 9.0, 27.0, c=(154.0, -30.0, -13.5))
    lock = box(18.0, 6.0, 10.0, c=(-9.0, 34.0, -5.0))
    return [(case, YEL), (blade, YEL * 0.95 + 0.04), (hook, CHROME), (lock, DARK)]


def multimeter():
    """Handheld meter, 150 x 75 x 40, display, dial, two probes."""
    body = extrude(rrect(75, 150, 9), 38.0)
    boot = extrude(rrect(80, 156, 11), 30.0, z0=2.0)
    disp = extrude(rrect(56, 30, 2, cy=42), 1.0, z0=38.0)
    dial = cylinder(17.0, 6.0, n=32, c=(0, -12, 38.0))
    knob = box(30.0, 6.0, 4.0, c=(-15.0, -15.0, 44.0))
    out = [(boot, YEL), (body, DARK), (disp, SCREEN), (dial, BLACKPART), (knob, DARK)]
    for sx, col in ((-14, RED), (14, BLACKPART)):
        jack = cylinder(4.5, 3.0, n=16, c=(sx, -58, 38.0))
        path = [(sx, -58, 41), (sx, -66, 46), (sx * 2.2, -82, 47), (sx * 3.2, -96, 44)]
        P = np.asarray(path, float)
        lead = _tube(P, 2.0)
        probe = to_x(cylinder(4.0, 42.0, n=14, r2=2.5))
        probe = rot(probe, rz=-100 if sx < 0 else -80)
        out += [(jack, BLACKPART), (lead, col), (mv(probe, *P[-1]), col)]
    return out


def _tube(P, r, n=10):
    from kit3d import tube
    return tube(P, r, n)


def ferrule_crimper():
    """Self-adjusting square ferrule crimper, 0.25 to 10 mm², ~180 mm."""
    head = extrude(rrect(46, 40, 6), 14.0, z0=-7.0,
                   holes=[np.array([(-3, -3), (3, -3), (3, 3), (-3, 3)]) + np.array([4.0, 0])])
    jaws = extrude(np.array([(-23, -6), (-46, -6), (-46, 6), (-23, 6)]), 10.0, z0=-5.0)
    out = [(head, DARK), (jaws, CHROME)]
    for s in (1, -1):
        path = [(23, 10 * s, 0), (60, 16 * s, 0), (110, 26 * s, 0), (160, 30 * s, 0)]
        ring = np.array([(7 * math.cos(a), 6 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]])
        out.append((sweep(path, ring), RED))
    return out


def screwdriver(blade=3.5, L=100.0):
    """Terminal screwdriver, flat 3.5 (and a 2.5 behind it)."""
    out = []
    for i, (b, Ls) in enumerate(((3.5, 100.0), (2.5, 75.0))):
        handle = revolve([(0, 0), (7, 0), (9, 6), (9.5, 70), (8, 92), (0, 96)], n=24)
        shaft = cylinder(b / 2 * 0.85, Ls, n=14, c=(0, 0, 96))
        tip = extrude(np.array([(-b / 2, -0.25), (b / 2, -0.25), (b / 2, 0.25), (-b / 2, 0.25)]), 6.0,
                      z0=96 + Ls)
        wedge = loft([np.c_[circle_pts(b / 2 * 0.85, 4, start=math.pi / 4) * [1, 1], np.full(4, 96 + Ls - 8)],
                      np.c_[np.array([(b / 2, 0.25), (-b / 2, 0.25), (-b / 2, -0.25), (b / 2, -0.25)]),
                            np.full(4, 96 + Ls)]])
        parts = [(to_x(handle), RED if i == 0 else BLUE), (to_x(shaft), CHROME), (to_x(wedge), CHROME),
                 (to_x(tip), CHROME)]
        out += [(mv(m, 0, 0, -i * 26.0), c) for m, c in parts]
    return out


TOOLS = [
    # (builder, name, size, used in steps, view (az, el))
    (hex_key_set, "Hex keys, ball end", "2 · 2.5 · 3 · 4 mm, long series",
     "2: 14  ·  2.5: 7, 13, 15, 16, 19 (a long one)\n3: 2, 3, 10, 11, 13, 18, 24  ·  4: 6, 8, 9, 14, 23", (30, 34)),
    (spanner, "Thin open spanner", "8 × 10 mm, under 3.5 mm thick",
     "8 mm: M5 nylocs and nuts, 2, 3, 9, 11\n10 mm: the eccentric spacers, 3 and 4", (20, 40)),
    (nut_driver, "Nut driver", "5.5 mm", "M3 nuts: limit switches and\ncontroller standoffs, 15 and 16", (25, 25)),
    (drill_bit, "Drill and 5.2 mm bit", "HSS jobber, plus a centre punch", "the idler axle hole\nthrough the rail's web, 9", (25, 25)),
    (m5_tap, "M5 tap and tap wrench", "M5 × 0.8, with cutting oil",
     "C-Beam end holes, unless bought\ntapped: 8, 13, 14; plain plate holes, 6", (30, 30)),
    (hacksaw, "Saw", "hacksaw and mitre box, or a mitre saw",
     "the X rail, 1500 cut to 1397, 23.\nNon-ferrous blade; deburr the cut", (20, 40)),
    (spirit_level, "Spirit level", "600 mm, with a plumb vial", "the cabinet, 21; the X rail, 23;\nthe mast, 24", (25, 30)),
    (calipers, "Calipers", "150 mm, digital", "pulley hub 22 to 32 mm, 7; the 2 mm\ncoupler gap, 14; checking stock", (20, 45)),
    (tape_measure, "Tape measure", "5 m", "rail heights and the cut, 21 to 24", (30, 30)),
    (multimeter, "Multimeter", "continuity, ohms, DC volts",
     "motor coil pairs, limit loops, the\nbrake and both 24 V rails: wiring, 14, 17", (25, 40)),
    (ferrule_crimper, "Ferrule crimper and stripper", "0.25 to 2.5 mm², square crimp",
     "every screw terminal: wiring pages", (20, 42)),
    (screwdriver, "Terminal screwdrivers", "flat 2.5 and 3.5 mm",
     "relay, fuse block and controller\nterminals: wiring pages", (25, 30)),
]


def page_tools(MS, pdf):
    from kit3d import Part, iso_matrix
    fig, ax = MS.new_page(None, "Tools",
                          "Everything the 27 steps and the wiring need. Metric throughout; nothing is inch.")
    for i, (fn, name, size, steps, (az, el)) in enumerate(TOOLS):
        r, c = divmod(i, 4)
        x0, ytop = 40 + c * 270, 762 - r * 228
        ax.add_patch(MS.FancyBboxPatch((x0, ytop - 218), 258, 218, boxstyle="round,pad=0,rounding_size=8",
                                       facecolor="none", edgecolor="#dfe5e9", lw=1.0, zorder=5))
        parts = [Part(m, col, ang=30) for m, col in fn()]
        MS.scene(ax, parts, (x0 + 129, ytop - 62), (222, 92), MM=iso_matrix(az, el),
                 clip=(x0 + 2, ytop - 120, x0 + 256, ytop - 2))
        ax.text(x0 + 14, ytop - 132, name, fontsize=9.2, fontweight="semibold", family=MS.TITLE_FONT,
                color=MS.INK, va="top")
        ax.text(x0 + 14, ytop - 149, size, fontsize=7.8, color=MS.INK, va="top", linespacing=1.3)
        ny = ytop - 149 - 14.5 * (size.count("\n") + 1) - 4
        ax.text(x0 + 14, ny, "steps: " + steps, fontsize=7.4, color=MS.DIM, va="top", linespacing=1.35)
    ax._body_y = 60.0
    MS.save(fig, ax, pdf, "00c_tools")
