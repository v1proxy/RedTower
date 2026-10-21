"""The Maag cabinet: frame, brackets, trays, base pan and feet, as one model.

Every page of the frame booklet is drawn from this module, and the gantry's
cabinet (greenhouse/gantry/frame.py) shares its numbers, so a frame page and a
gantry page cannot disagree about where a rail is.

Coordinates, millimetres, the same as frame.py:
    x  0 .. 1397   left to right, seen from the front
    y  0 .. 559    y = 0 is the FRONT face
    z  0 .. 1829   bottom of the uprights to the top of the top rail.
                   The floor is at z = -20: the TPU feet lift everything.

Frame Rev 6 (this module) over the Rev 5 bracket schedule
---------------------------------------------------------
Rev 5 put an M8 end tap on all 54 member ends and a bracket on 30 of them.
An end-tap joint puts a screw head in the mating member's slot, and a head can
only enter a slot from its open end. In this cabinet that cannot be sequenced:
a shelf rail's heads must be in both side rails before those rails meet the
uprights, so every tier would have to go in as a six-headed unit lowered 1.8 m
down four free-standing uprights. The end tap also needs a centre bore cored
for M8, and the profile's bore has not been measured.

Rev 6 drops the end taps. Every one of the 54 joints gets a bracket:
    44 PETOX 3540 gussets (20 owned, two more sets of 20 to buy), every bolt
       into a DROP-IN M8 T-nut, so any bracket goes on in any order;
    10 TOCLUX hidden connectors, where a gusset has no room: the eight floor
       corners (nothing below a rail that sits 20 mm off the floor, the base
       pan on top) and the two rear ends of the top side rails (the gantry's
       X rail sits under them).
The placement rule is unchanged: no bracket on a top face.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "gantry"))
sys.path.insert(0, _HERE)

from kit3d import extrude, merge, mv, rot, circle_pts, cylinder, box, revolve   # noqa: E402
import frame as GF                                                               # noqa: E402
import tpu_foot as TF                                                            # noqa: E402

# ------------------------------------------------------------------ the frame
W, D, H = GF.W, GF.D, GF.H          # 1397 x 559 x 1829
SER = GF.SER                        # 40
LEVELS = list(GF.LEVELS)            # bottom z of each rail: 0, 304.8, 965.2, 1397, 1789
TIERS = list(GF.TIERS)              # 304.8, 965.2, 1397: tiers A, B, C
TIER_NAME = {LEVELS[1]: "A", LEVELS[2]: "B", LEVELS[3]: "C"}
TRAY_D = GF.TRAY_D                  # 203: trays occupy y 0 .. 203
SHELF_Y = TRAY_D - SER              # 163: the shelf rail carries the tray's back edge
MID = (660.0, 700.0)                # mid rails, under the sheet laps (make_dxf_rev4.MID)
SPAN_X = W - 2 * SER                # 1317
SPAN_Y = D - 2 * SER                # 479
MID_T = SHELF_Y - SER               # 123, tier mid rail
FOOT_H = 20.0                       # TPU feet, the floor is at z = -FOOT_H
DRAIN_FALL = 5.0                    # every tray and the pan fall 5 mm to the drain (BOM G090)

# EU slot-8 4040: one slot per face. (across, depth from the face), mm.
SLOT8 = [(-4.1, 0.0), (-4.1, 4.3), (-8.25, 4.3), (-8.25, 7.0), (-3.0, 12.25),
         (3.0, 12.25), (8.25, 7.0), (8.25, 4.3), (4.1, 4.3), (4.1, 0.0)]
SLOT_OPEN, SLOT_LIP, SLOT_DEPTH = 8.2, 4.3, 12.25
CORNER_R = 2.4                      # drawn to match the foot; step 1 checks it
BORE_DRAW = 8.4                     # the bore drawn; step 1 measures the real one


def profile_outline(s=SER, r=CORNER_R, seg=6):
    """40 x 40 outline, CCW, slots as notches, corners rounded."""
    pts = []
    corners = [((r, r), 180), ((s - r, r), 270), ((s - r, s - r), 0), ((r, s - r), 90)]
    edges = [((s / 2, 0.0), (1, 0), (0, 1)), ((s, s / 2), (0, 1), (-1, 0)),
             ((s / 2, s), (-1, 0), (0, -1)), ((0.0, s / 2), (0, -1), (1, 0))]
    for (c, a0), (m, t, n) in zip(corners, edges):
        for j in range(seg + 1):
            a = math.radians(a0 + 90.0 * j / seg)
            pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
        for u, v in SLOT8:
            pts.append((m[0] + u * t[0] + v * n[0], m[1] + u * t[1] + v * n[1]))
    return np.array(pts)


_OUTLINE = profile_outline()


def _basis(ex, ey, ez):
    return np.array([ex, ey, ez], float).T


def stick(length, axis="z", bore=BORE_DRAW):
    """A 4040 stick, min corner at the origin, `length` along `axis`."""
    m = extrude(_OUTLINE, length, holes=[circle_pts(bore / 2, 40, SER / 2, SER / 2)])
    V, F = m
    if axis == "x":
        V = V @ _basis((0, 1, 0), (0, 0, 1), (1, 0, 0)).T
    elif axis == "y":
        V = V @ _basis((1, 0, 0), (0, 0, 1), (0, 1, 0)).T
    return (V - V.min(0), F)


class Member:
    """One cut piece of 4040."""
    __slots__ = ("label", "kind", "axis", "x", "y", "z", "length", "level")

    def __init__(self, label, kind, axis, x, y, z, length, level=None):
        self.label, self.kind, self.axis = label, kind, axis
        self.x, self.y, self.z, self.length, self.level = x, y, z, length, level

    def mesh(self, lo=None, hi=None):
        """The stick placed, optionally trimmed to the [lo, hi] box along its axis."""
        a0 = {"x": self.x, "y": self.y, "z": self.z}[self.axis]
        a1 = a0 + self.length
        if lo is not None or hi is not None:
            k = "xyz".index(self.axis)
            a0 = max(a0, lo[k]) if lo is not None else a0
            a1 = min(a1, hi[k]) if hi is not None else a1
            if a1 - a0 < 1e-6:
                return None
        V, F = stick(a1 - a0, self.axis)
        o = [self.x, self.y, self.z]
        o["xyz".index(self.axis)] = a0
        return (V + np.array(o), F)

    def bbox(self):
        lo = np.array([self.x, self.y, self.z], float)
        hi = lo + SER
        hi["xyz".index(self.axis)] = lo["xyz".index(self.axis)] + self.length
        return lo, hi


def members():
    """All 31 pieces, labelled the way the booklet labels them.

    FL FR BL BR   uprights, by corner
    F0..F4        front rails at levels 0 to 4
    B0..B4        back rails
    L0..L4 R0..R4 left and right side rails
    S1..S3        shelf rails, the tray's back edge, tiers A to C
    M0            base mid rail, under the pan's lap
    M1..M3        tier mid rails, under the trays' laps
    """
    M = []
    for lab, x, y in (("FL", 0.0, 0.0), ("FR", W - SER, 0.0), ("BL", 0.0, D - SER), ("BR", W - SER, D - SER)):
        M.append(Member(lab, "upright", "z", x, y, 0.0, H))
    for k, z in enumerate(LEVELS):
        M.append(Member(f"F{k}", "front rail", "x", SER, 0.0, z, SPAN_X, k))
        M.append(Member(f"B{k}", "back rail", "x", SER, D - SER, z, SPAN_X, k))
        M.append(Member(f"L{k}", "side rail", "y", 0.0, SER, z, SPAN_Y, k))
        M.append(Member(f"R{k}", "side rail", "y", W - SER, SER, z, SPAN_Y, k))
    for k, z in enumerate(LEVELS):
        if z in TIERS:
            M.append(Member(f"S{k}", "shelf rail", "x", SER, SHELF_Y, z, SPAN_X, k))
            M.append(Member(f"M{k}", "tier mid rail", "y", MID[0], SER, z, MID_T, k))
    M.append(Member("M0", "base mid rail", "y", MID[0], SER, 0.0, SPAN_Y, 0))
    return M


def by_label():
    return {m.label: m for m in members()}


def frame_mesh(only=None, lo=None, hi=None):
    out = []
    for m in members():
        if only is not None and m.label not in only:
            continue
        mm = m.mesh(lo, hi)
        if mm is not None:
            out.append(mm)
    return merge(*out) if out else (np.zeros((0, 3)), np.zeros((0, 3), int))


def cut_list():
    """(length, labels) groups, longest first."""
    g = {}
    for m in members():
        g.setdefault(m.length, []).append(m.label)
    return sorted(g.items(), key=lambda kv: -kv[0])


def cut_plan(stock=2000.0, kerf=3.0):
    """First-fit decreasing into 2000 mm sticks: list of [labels], drop."""
    want = sorted(members(), key=lambda m: -m.length)
    sticks = []
    for m in want:
        for s in sticks:
            if s["left"] >= m.length + kerf:
                s["cuts"].append(m); s["left"] -= m.length + kerf
                break
        else:
            sticks.append({"cuts": [m], "left": stock - m.length - kerf})
    return sticks


# ------------------------------------------------------------- the brackets
G_LEG, G_W, G_T, G_HOLE = 35.0, 40.0, 6.0, 20.0     # PETOX 3540
H_LEG, H_W, H_D0, H_D1 = 38.0, 7.8, 1.0, 11.5       # TOCLUX hidden: reach, width, depth band


def _place(mesh, P, a, b):
    """Local (u, v, w) to the world: u along a, v along b, w along a x b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = np.cross(a, b)
    V, F = mesh
    W_ = np.asarray(P, float) + V[:, :1] * a + V[:, 1:2] * b + V[:, 2:3] * n
    return (W_, F)


def _plate_uw(L, Wd, t, hole_u, slot=(8.5, 11.0)):
    """A plate L long (u) x Wd wide (w) x t thick (v), with a slotted hole at u."""
    from kit3d import _mesh
    hl, hw = slot[1], slot[0]
    r = hw / 2
    hole = [(hole_u + (hl / 2 - r) + r * math.cos(a), r * math.sin(a))
            for a in np.linspace(-math.pi / 2, math.pi / 2, 14)]
    hole += [(hole_u - (hl / 2 - r) + r * math.cos(a), r * math.sin(a))
             for a in np.linspace(math.pi / 2, 3 * math.pi / 2, 14)]
    poly = np.array([(0, -Wd / 2), (L, -Wd / 2), (L, Wd / 2), (0, Wd / 2)])
    V, F = extrude(poly, t, holes=[np.array(hole)])
    # extrude gives (u, w, v); swap to (u, v, w)
    return _mesh(V[:, [0, 2, 1]], F)


def gusset_local():
    """PETOX 3540, inside corner at the origin, legs along +u and +v, plates
    in the +u/+v quadrant (outside both members), 40 wide across w."""
    from kit3d import _mesh
    legA = _plate_uw(G_LEG, G_W, G_T, G_HOLE)                 # on face A (v = 0)
    V, F = _plate_uw(G_LEG, G_W, G_T, G_HOLE)
    legB = _mesh(V[:, [1, 0, 2]], F)                          # on face B (u = 0)
    tri = np.array([(G_T, G_T), (G_LEG, G_T), (G_T, G_LEG)])
    webs = []
    for w0 in (-G_W / 2, G_W / 2 - 3.0):
        Vw, Fw = extrude(tri, 3.0, z0=w0)
        webs.append((Vw, Fw))
    return merge(legA, legB, *webs)


def hidden_local():
    """TOCLUX hidden connector: an L inside both slots, at negative u and v
    (the members are on those sides), reaching H_LEG along each, two M6 grubs."""
    legA = box(H_LEG + H_D1, H_D1 - H_D0, H_W, c=(-H_D1, -H_D1, -H_W / 2))
    legB = box(H_D1 - H_D0, H_LEG + H_D1, H_W, c=(-H_D1, -H_D1, -H_W / 2))
    grubA = mv(cylinder(3.0, 6.0), 0, 0, 0)
    gA = _swap_zv(grubA)
    gs = [mv(gA, H_LEG * 0.62, -H_D1 - 0.5, 0), ]
    gB = _swap_zu(cylinder(3.0, 6.0))
    gs.append(mv(gB, -H_D1 - 0.5, H_LEG * 0.62, 0))
    return merge(legA, legB, *gs)


def _swap_zv(m):
    V, F = m
    return (V[:, [0, 2, 1]], F)


def _swap_zu(m):
    V, F = m
    return (V[:, [2, 1, 0]], F)


class Joint:
    __slots__ = ("label", "a", "b", "kind", "P", "ua", "vb", "note", "level")

    def __init__(self, label, a, b, kind, P, ua, vb, note="", level=None):
        self.label, self.a, self.b, self.kind = label, a, b, kind
        self.P, self.ua, self.vb, self.note, self.level = P, ua, vb, note, level

    def bracket(self, explode=0.0):
        """The bracket placed. `explode` as a number moves it out along the
        corner diagonal; as (du, dv) it moves it along the two legs."""
        m = gusset_local() if self.kind == "gusset" else hidden_local()
        V, F = m
        if isinstance(explode, (tuple, list)):
            V = V + np.array([explode[0], explode[1], 0.0])
        elif explode:
            V = V + np.array([1.0, 1.0, 0.0]) / math.sqrt(2) * explode
        return _place((V, F), self.P, self.ua, self.vb)

    def local_point(self, u, v, w=0.0):
        a, b = np.asarray(self.ua, float), np.asarray(self.vb, float)
        return np.asarray(self.P, float) + u * a + v * b + w * np.cross(a, b)

    def bolt_points(self):
        """World points of the two bolt holes (gussets), on the member faces."""
        if self.kind != "gusset":
            return []
        P, a, b = np.asarray(self.P, float), np.asarray(self.ua, float), np.asarray(self.vb, float)
        return [(P + a * G_HOLE, -b), (P + b * G_HOLE, -a)]      # point on the face, into the member


X, Y, Z = np.eye(3)


def joints():
    """All 54 joints with the bracket each one gets (Rev 6)."""
    J = []
    top = LEVELS[-1]
    for k, z in enumerate(LEVELS):
        corners = [("F", "FL", (SER, SER / 2), X), ("F", "FR", (W - SER, SER / 2), -X),
                   ("B", "BL", (SER, D - SER / 2), X), ("B", "BR", (W - SER, D - SER / 2), -X),
                   ("L", "FL", (SER / 2, SER), Y), ("L", "BL", (SER / 2, D - SER), -Y),
                   ("R", "FR", (W - SER / 2, SER), Y), ("R", "BR", (W - SER / 2, D - SER), -Y)]
        for rail, post, (px, py), a in corners:
            lab = f"{rail}{k}-{post}"
            if z == 0.0:
                # floor: hidden connector, rail's TOP slot + the post's face slot
                J.append(Joint(lab, f"{rail}{k}", post, "hidden", (px, py, SER), a, Z,
                               "hidden: floor corner, no room below", k))
            elif z == top and rail in ("L", "R") and post in ("BL", "BR"):
                # under the top side rail's rear end sits the gantry's X rail
                J.append(Joint(lab, f"{rail}{k}", post, "hidden", (px, py, z), a, -Z,
                               "hidden: the X rail sits below", k))
            else:
                J.append(Joint(lab, f"{rail}{k}", post, "gusset", (px, py, z), a, -Z,
                               "gusset under the rail, leg down the post", k))
    for k, z in enumerate(LEVELS):
        zc = z + SER / 2
        if z in TIERS:
            J.append(Joint(f"S{k}-L{k}", f"S{k}", f"L{k}", "gusset", (SER, SHELF_Y, zc), X, -Y,
                           "gusset, front side of the shelf rail", k))
            J.append(Joint(f"S{k}-R{k}", f"S{k}", f"R{k}", "gusset", (W - SER, SHELF_Y, zc), -X, -Y,
                           "gusset, front side of the shelf rail", k))
            J.append(Joint(f"M{k}-F{k}", f"M{k}", f"F{k}", "gusset", (MID[0], SER, zc), Y, -X,
                           "gusset, left side of the mid rail", k))
            J.append(Joint(f"M{k}-S{k}", f"M{k}", f"S{k}", "gusset", (MID[0], SHELF_Y, zc), -Y, -X,
                           "gusset, left side of the mid rail", k))
        if z == 0.0:
            J.append(Joint("M0-F0", "M0", "F0", "gusset", (MID[0], SER, zc), Y, -X,
                           "gusset, left side of the mid rail", 0))
            J.append(Joint("M0-B0", "M0", "B0", "gusset", (MID[0], D - SER, zc), -Y, -X,
                           "gusset, left side of the mid rail", 0))
    return J


def bracket_meshes(kind=None, level=None, labels=None, explode=0.0):
    out = []
    for j in joints():
        if kind and j.kind != kind:
            continue
        if level is not None and j.level != level:
            continue
        if labels is not None and j.label not in labels:
            continue
        out.append(j.bracket(explode))
    return merge(*out) if out else (np.zeros((0, 3)), np.zeros((0, 3), int))


# ------------------------------------------------------------- fasteners
def button_head(M=8.0, L=16.0):
    """ISO 7380 button head, head on z = 0 up, shank down to -L."""
    hd, hh = {6: (10.5, 3.3), 8: (14.0, 4.4)}.get(int(M), (M * 1.75, M * 0.55))
    head = revolve([(0, 0), (hd / 2, 0), (hd / 2, hh * 0.25), (hd * 0.38, hh * 0.78),
                    (hd * 0.2, hh), (0, hh)])
    shank = cylinder(M / 2, L, c=(0, 0, -L))
    return merge(head, shank)


def cap_screw(M=8.0, L=16.0):
    """ISO 4762, head on z = 0 up."""
    hd, hh = 13.0, 8.0
    head = revolve([(0, 0), (hd / 2 - 0.4, 0), (hd / 2, 0.4), (hd / 2, hh - 0.6), (hd / 2 - 0.6, hh), (0, hh)])
    return merge(head, cylinder(M / 2, L, c=(0, 0, -L)))


def washer8(t=1.6):
    from kit3d import ring
    return ring(8.0, 4.2, t)


def tnut8():
    """Drop-in (roll-in) M8 T-nut for slot 8, in its own frame: top at z = 0
    sitting against the underside of the slot lips, body down to -6."""
    body = extrude(np.array([(-8.0, -5.5), (8.0, -5.5), (8.0, 5.5), (-8.0, 5.5)]), 4.0, z0=-4.0,
                   holes=[circle_pts(3.4, 36)])
    keel = extrude(np.array([(-5.5, -3.0), (5.5, -3.0), (5.5, 3.0), (-5.5, 3.0)]), 2.0, z0=-6.0,
                   holes=[circle_pts(3.4, 36)])
    return merge(body, keel)


def grub6(L=8.0):
    return cylinder(3.0, L)


def place_axis(mesh, p, d):
    """Put a z-axis part (head at z = 0, shank along -z) at point p with its
    shank along unit direction d (pointing into the material)."""
    d = np.asarray(d, float) / np.linalg.norm(d)
    z = -d
    t = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(t, z); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    V, F = mesh
    return (np.asarray(p, float) + V[:, :1] * x + V[:, 1:2] * y + V[:, 2:3] * z, F)


def gusset_fasteners(j, explode=0.0, nut_explode=None, bracket_explode=0.0):
    """Cap screw + washer + drop-in T-nut at both of a gusset's holes.
    `explode` lifts the screws off the plate, `nut_explode` drops the nuts
    out of the slot (along the screw axis, into the member's side)."""
    out = []
    ne = explode if nut_explode is None else nut_explode
    for p, d in j.bolt_points():
        d = np.asarray(d, float)
        outward = -d
        p = p + outward * bracket_explode
        head = p + outward * (G_T + 1.6 + explode)
        out.append(("bolt", place_axis(cap_screw(8, 16), head, d)))
        out.append(("washer", place_axis(washer8(), p + outward * (G_T + 1.6 + explode * 0.55), d)))
        nut_at = p - outward * bracket_explode + d * SLOT_LIP - outward * ne
        out.append(("tnut", place_axis(tnut8(), nut_at, d)))
    return out


# ------------------------------------------------------------- sheet metal
# Floor polygons and holes, exactly as greenhouse/sendcutsend/make_dxf_rev4.py
# cuts them (that file is the one the DXFs come from; check_sheets() below
# parses the shipped DXFs back and compares).
T_SHEET, LIP = 1.6002, 25.0
N_NOTCH = 41.0
WT, WP = TRAY_D, D
LAP, TON, INS = 40.0, 40.0, 3.5
LD, LU = MID[1], W - MID[0]        # 700, 737

TRAY_DOWN = ([(N_NOTCH, 0), (LD, 0), (LD, WT), (0, WT), (0, N_NOTCH), (N_NOTCH, N_NOTCH)],
             [True, False, True, True, True, True])
TRAY_UP = ([(0, INS), (TON, INS), (TON, 0), (LU - N_NOTCH, 0), (LU - N_NOTCH, N_NOTCH), (LU, N_NOTCH),
            (LU, WT), (TON, WT), (TON, WT - INS), (0, WT - INS)],
           [False, False, True, True, True, True, True, False, False, False])
PAN_DOWN = ([(N_NOTCH, 0), (LD, 0), (LD, WP), (N_NOTCH, WP), (N_NOTCH, WP - N_NOTCH), (0, WP - N_NOTCH),
             (0, N_NOTCH), (N_NOTCH, N_NOTCH)],
            [True, False, True, True, True, True, True, True])
PAN_UP = ([(0, INS), (TON, INS), (TON, 0), (LU - N_NOTCH, 0), (LU - N_NOTCH, N_NOTCH), (LU, N_NOTCH),
           (LU, WP - N_NOTCH), (LU - N_NOTCH, WP - N_NOTCH), (LU - N_NOTCH, WP), (TON, WP),
           (TON, WP - INS), (0, WP - INS)],
          [False, False, True, True, True, True, True, True, True, False, False, False])

TF_, TB_, TS_, MY_ = 20.0, WT - 20.0, 130.0, 100.0
PF_, PB_, PS_ = 20.0, WP - 20.0, WP / 2.0
LAP_X = sum(MID) / 2                  # 680, the shared lap bolt
HOLES = {
    "tray_DOWN": [(x, TF_, "x") for x in (150, 400, 650)] + [(x, TB_, "x") for x in (150, 400, 650)]
                 + [(20.0, TS_, "y"), (LAP_X, MY_, "y")],
    "tray_UP": [(x - MID[0], TF_, "x") for x in (800, 1050, 1260)] + [(x - MID[0], TB_, "x") for x in (800, 1050, 1260)]
               + [(1377.0 - MID[0], TS_, "y"), (LAP_X - MID[0], MY_, "y")],
    "basepan_DOWN": [(x, PF_, "x") for x in (150, 400, 650)] + [(x, PB_, "x") for x in (150, 400, 650)]
                    + [(20.0, PS_, "y"), (LAP_X, PS_, "y")],
    "basepan_UP": [(x - MID[0], PF_, "x") for x in (800, 1050, 1260)] + [(x - MID[0], PB_, "x") for x in (800, 1050, 1260)]
                  + [(1377.0 - MID[0], PS_, "y"), (LAP_X - MID[0], PS_, "y")],
}
DRAIN = {"tray_DOWN": (66.0, 95.0)}
# Drains: one 1/2 in bulkhead near the left end of each tray's DOWN piece, at
# (66, 95): clear of the FL gussets (x 0 to 75, y 0 to 75), the left rail and
# the shelf rail by 5 or more round a 42 nut. Each tray's runoff runs down a
# short branch, under its left rail and out of the side, into one riser
# zip-tied to the outside of the FL post. Tier C joins it at an elbow, B and A
# at tees. The riser ends in the lid of a 2 gal bucket standing left of the
# cabinet (rim 250 off the floor; the riser leaves the post at 285).
# The base pan has no drain: its outlet would hang 38 off the floor, below the
# rim of any bucket. It is the dry catch tray, with the leak sensor at its low,
# left end.
BUCKET = dict(x=-140.0, y=125.0, r_top=122.0, r_bot=103.0, h=241.0, lid=9.0)
RISER = (-9.0, 20.0)                # tube centre, on the FL post's left face (x 0)
TUBE_R = 8.0                        # 1/2 in ID vinyl, 16 OD
BULKHEAD = dict(flange_r=24.0, flange_t=3.0, body_r=10.7, body_l=26.0, nut_r=21.0, nut_t=8.0)


def bucket_mesh():
    """2 gal bucket with its lid, standing on the floor."""
    b = BUCKET
    prof = [(0, 0), (b["r_bot"], 0), (b["r_top"], b["h"]), (b["r_top"] + 3, b["h"]),
            (b["r_top"] + 3, b["h"] + b["lid"]), (0, b["h"] + b["lid"])]
    return mv(revolve(prof, n=48), b["x"], b["y"], -FOOT_H)


def _junction_z(zl):
    return zl - 40.0


def drain_routes():
    """Tube centre lines. {"branches": [C, B, A], "riser": riser into the bucket}.
    Each branch: down from its bulkhead, a 90 deg elbow, under its left rail
    (top of tube 4 below the rail), out of the side and forward to the riser."""
    dx, dy = DRAIN["tray_DOWN"]
    rx, ry = RISER
    branches = []
    for zl in TIERS[::-1]:
        zf = zl + SER
        jz = _junction_z(zl)
        branches.append(np.array([
            (dx, dy, zf - 22.4), (dx, dy, zl - 4), (dx - 12, dy, zl - TUBE_R - 4),
            (20.0, dy - 2, zl - 15), (0.0, dy - 4, zl - 18), (rx, dy - 12, zl - 22),
            (rx, 55.0, zl - 30), (rx, 32.0, jz + 4), (rx + 0.01, ry, jz)]))
    lid = -FOOT_H + BUCKET["h"] + BUCKET["lid"]
    ja = _junction_z(TIERS[0])
    riser = np.array([(rx, ry, _junction_z(TIERS[2])), (rx, ry, ja), (rx - 3, ry + 4, ja - 9),
                      (-35.0, 45.0, ja - 19), (-62.0, 66.0, lid + 8), (-75.0, 75.0, lid - 2),
                      (-75.0, 75.0, lid - 25)])
    return {"branches": branches, "riser": riser}


def drain_ties():
    """Zip tie heights round the FL post and the riser: just inside each
    junction and mid-span."""
    jc, jb, ja = [_junction_z(z) for z in TIERS[::-1]]
    return [jc - 30, (jc + jb) / 2, jb + 30, (jb + ja) / 2, ja + 30]


def drain_fittings():
    """(kind, mesh): the elbow under each bulkhead, the elbow at C's junction,
    a tee at B's and A's, and the zip ties."""
    dx, dy = DRAIN["tray_DOWN"]
    rx, ry = RISER
    out = []
    for zl in TIERS:
        el = merge(cylinder(9.0, 16.0, c=(0, 0, -8.0)), rot(cylinder(9.0, 20.0), ry=-math.pi / 2))
        out.append(("elbow", mv(el, dx, dy, zl - 4)))
    for k, zl in enumerate(TIERS[::-1]):
        jz = _junction_z(zl)
        run = cylinder(9.0, 40.0 if k else 22.0, c=(0, 0, -20.0 if k else -22.0))
        stub = rot(cylinder(9.0, 20.0), rx=-math.pi / 2)
        out.append(("elbow" if k == 0 else "tee", mv(merge(run, stub), rx, ry, jz)))
    ring = [(-19.5, -1.5), (41.5, -1.5), (41.5, 41.5), (-19.5, 41.5)]
    inner = [(-18.3, -0.3), (-18.3, 40.3), (40.3, 40.3), (40.3, -0.3)]
    for z in drain_ties():
        out.append(("tie", extrude(np.array(ring), 4.8, z0=z - 2.4, holes=[np.array(inner)])))
    return out


def bulkhead_mesh(x, y, z_floor):
    """1/2 in bulkhead through a floor at z_floor: flange on top, body and nut below."""
    b = BULKHEAD
    fl = revolve([(0, 0), (b["flange_r"], 0), (b["flange_r"], b["flange_t"]), (0, b["flange_t"])])
    body = revolve([(0, 0), (b["body_r"], 0), (b["body_r"], b["body_l"]), (0, b["body_l"])])
    nut = cylinder(b["nut_r"], b["nut_t"], n=6)
    return merge(mv(fl, x, y, z_floor + T_SHEET), mv(body, x, y, z_floor - 22.4),
                 mv(nut, x, y, z_floor - 2.0 - b["nut_t"]))


SHEETS = {"tray_DOWN": TRAY_DOWN, "tray_UP": TRAY_UP, "basepan_DOWN": PAN_DOWN, "basepan_UP": PAN_UP}
SHEET_QTY = {"tray_DOWN": 3, "tray_UP": 3, "basepan_DOWN": 1, "basepan_UP": 1}


def _slot_loop(cx, cy, along, L=18.0, Wd=9.0, n=14):
    r = Wd / 2
    h = L / 2 - r
    pts = [(h + r * math.cos(a), r * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, n)]
    pts += [(-h + r * math.cos(a), r * math.sin(a)) for a in np.linspace(math.pi / 2, 3 * math.pi / 2, n)]
    pts = np.array(pts)
    if along == "y":
        pts = pts[:, ::-1]
    return pts + np.array([cx, cy])


def sheet_local(name, drain_d=None):
    """Folded sheet in its own frame: floor bottom at z = 0, lips up to LIP."""
    poly, flags = SHEETS[name]
    P = np.array(poly, float)
    holes = [_slot_loop(cx, cy, al) for cx, cy, al in HOLES[name]]
    if name in DRAIN:
        dd = drain_d or 6.0
        holes.append(np.array(circle_pts(dd / 2, 40, *DRAIN[name])))
    floor = extrude(P, T_SHEET, holes=holes)
    walls = []
    n = len(P)
    area = sum(P[i, 0] * P[(i + 1) % n, 1] - P[(i + 1) % n, 0] * P[i, 1] for i in range(n))
    for i in range(n):
        if not flags[i]:
            continue
        p0, p1 = P[i], P[(i + 1) % n]
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        nin = np.array([-d[1], d[0]]) if area > 0 else np.array([d[1], -d[0]])
        q = np.array([p0, p1, p1 + nin * T_SHEET, p0 + nin * T_SHEET])
        walls.append(extrude(q, LIP - T_SHEET, z0=T_SHEET))
    return merge(floor, *walls)


def sheet_world(name, z_level, up_raise=True):
    """Place a sheet on its level: floor on the rails' top face (z_level + 40).
    UP pieces sit one sheet thickness proud: they lie on the DOWN piece at the lap."""
    V, F = sheet_local(name)
    x0 = MID[0] if name.endswith("_UP") else 0.0
    dz = T_SHEET if (name.endswith("_UP") and up_raise) else 0.0
    return (V + np.array([x0, 0.0, z_level + SER + dz]), F)


def sheet_holes_world(name, z_level):
    x0 = MID[0] if name.endswith("_UP") else 0.0
    dz = T_SHEET if name.endswith("_UP") else 0.0
    return [(x0 + cx, cy, z_level + SER + dz, al) for cx, cy, al in HOLES[name]]


def sheets_for_level(z):
    return ("basepan_DOWN", "basepan_UP") if z == 0.0 else ("tray_DOWN", "tray_UP")


def sheet_fasteners(z_level, which=("DOWN", "UP"), explode=0.0, nuts=True, bolts=True):
    """Every sheet fastener on one level: (kind, mesh) list.

    The lap bolt at x = 680 goes through both sheets into one T-nut; the UP
    piece's other seven bolts each get a 1.6 mm washer under the sheet as a
    shim. Lengths: M8 x 12 through one sheet, M8 x 16 through two layers."""
    names = sheets_for_level(z_level)
    out = []
    top = z_level + SER
    seen_lap = False
    for nm in names:
        piece = "UP" if nm.endswith("_UP") else "DOWN"
        if piece not in which:
            continue
        for x, y, zz, al in sheet_holes_world(nm, z_level):
            lap = abs(x - LAP_X) < 1e-6
            if lap and piece == "DOWN" and "UP" in which:
                continue                  # the lap bolt is drawn with the UP piece
            stack = T_SHEET + 1.6 + (1.6 if piece == "UP" else 0.0)    # sheet, washer, (shim or DOWN)
            L = 16.0 if piece == "UP" else 12.0
            head_z = top + stack + explode
            if bolts:
                out.append(("bolt", mv(button_head(8, L), x, y, head_z)))
                out.append(("washer", mv(washer8(), x, y, head_z - 1.6 - explode * 0.3)))
            if piece == "UP" and not lap:
                out.append(("shim", mv(washer8(), x, y, top + explode * 0.1)))
            if nuts:
                out.append(("tnut", mv(tnut8(), x, y, top - SLOT_LIP - explode * 0.15)))
            seen_lap |= lap
    return out


def screw_depths():
    """How far each sheet screw reaches below the rail's top face, against
    the slot's depth. A screw that bottoms clamps nothing."""
    out = {}
    for piece, L, stack in (("DOWN", 12.0, T_SHEET + 1.6), ("UP", 16.0, T_SHEET + 3.2),
                            ("lap", 16.0, 2 * T_SHEET + 1.6), ("gusset", 16.0, G_T + 1.6)):
        out[piece] = dict(length=L, stack=stack, reach=L - stack, slot=SLOT_DEPTH,
                          spare=SLOT_DEPTH - (L - stack), thread=L - stack - SLOT_LIP)
    return out


# ---------------------------------------------------------------- the feet
def foot_mesh(bore=BORE_DRAW):
    TF.use("4040", bore=bore)
    v, f = TF.build_foot(TF.HEIGHT, "TPU")
    tris = []
    for face in f:
        for k in range(1, len(face) - 1):
            tris.append((face[0], face[k], face[k + 1]))
    return (np.array(v, float), np.array(tris, int))


def feet_world(explode=0.0, which=("FL", "FR", "BL", "BR")):
    fm = foot_mesh()
    out = []
    for m in members():
        if m.kind == "upright" and m.label in which:
            V, F = fm
            out.append((V + np.array([m.x + SER / 2, m.y + SER / 2, -FOOT_H - explode]), F))
    return merge(*out)


# -------------------------------------------------------------- the checks
def corridor_clear():
    """Nothing of the frame may sit in the gantry corridor: x 40..1357,
    y 203..519, from above the base pan's lip to the top. Returns the
    offending parts (should be none)."""
    lo, hi = np.array([SER, TRAY_D, SER + LIP]), np.array([W - SER, D - SER, H])
    bad = []
    for m in members():
        a, b = m.bbox()
        if np.all(b > lo + 1e-6) and np.all(a < hi - 1e-6):
            bad.append(m.label)
    for j in joints():
        V, _ = j.bracket()
        a, b = V.min(0), V.max(0)
        if np.all(b > lo + 1e-6) and np.all(a < hi - 1e-6):
            bad.append(j.label)
    return bad


def fastener_clearances():
    """Gap along the slot between every sheet hole's slot (9 x 18) and the
    nearest bracket that occupies the same slot. Positive is clear."""
    out = []
    for z in LEVELS[:4]:
        for nm in sheets_for_level(z):
            for x, y, zz, al in sheet_holes_world(nm, z):
                best = 1e9
                for j in joints():
                    if j.level != LEVELS.index(z):
                        continue
                    V, _ = j.bracket()
                    a, b = V.min(0), V.max(0)
                    # bracket must reach the rail's top slot region to matter
                    if b[2] < z + SER - SLOT_DEPTH - 0.5:
                        continue
                    if al == "x":
                        if not (a[1] - 1 < y < b[1] + 1):
                            continue
                        gap = max(a[0] - (x + 9.0), (x - 9.0) - b[0])
                    else:
                        if not (a[0] - 1 < x < b[0] + 1):
                            continue
                        gap = max(a[1] - (y + 9.0), (y - 9.0) - b[1])
                    best = min(best, gap)
                out.append((nm, z, x, y, best))
    return out


def check_sheets(dxf_dir=None):
    """Parse the shipped DXFs and confirm every 9 x 18 slot this model draws
    is in them (slot centres from the arc pairs)."""
    dxf_dir = dxf_dir or os.path.join(_HERE, "..", "sendcutsend")
    report = {}
    for nm in SHEETS:
        txt = open(os.path.join(dxf_dir, nm + ".dxf")).read().split("\n")
        arcs = []
        i = 0
        while i < len(txt):
            if txt[i].strip() == "ARC":
                d = {}
                j = i + 1
                while j < len(txt) and txt[j].strip() != "0":
                    d[txt[j].strip()] = txt[j + 1].strip(); j += 2
                if abs(float(d["40"]) - 4.5) < 1e-3:
                    arcs.append((float(d["10"]), float(d["20"])))
                i = j
            else:
                i += 1
        # each slot has two arcs, 9 apart; pair them into centres
        cents = []
        used = set()
        for a in range(len(arcs)):
            if a in used:
                continue
            for b in range(a + 1, len(arcs)):
                if b in used:
                    continue
                if abs(math.dist(arcs[a], arcs[b]) - 9.0) < 1e-3:
                    cents.append(((arcs[a][0] + arcs[b][0]) / 2, (arcs[a][1] + arcs[b][1]) / 2))
                    used |= {a, b}
                    break
        report[nm] = cents
    return report


def drain_clear(step=4.0):
    """Closest any drain tube comes to a member or a bracket (bounding boxes),
    tube radius included. Positive is clear."""
    boxes = [(m.label,) + m.bbox() for m in members()]
    for j in joints():
        V, _ = j.bracket()
        boxes.append((j.label, V.min(0), V.max(0)))
    for zl in TIERS:
        V, _ = bulkhead_mesh(*DRAIN["tray_DOWN"], zl + SER)
        boxes.append(("bulkhead", V.min(0), V.max(0)))
    r = drain_routes()
    worst = (1e9, None)
    for P in r["branches"] + [r["riser"]]:
        pts = []
        for a_, b_ in zip(P[:-1], P[1:]):
            n = max(2, int(np.linalg.norm(b_ - a_) / step))
            pts += [a_ + (b_ - a_) * t for t in np.linspace(0, 1, n)]
        pts = np.array(pts)[3:]                # skip the start, inside its own bulkhead
        for lab, lo, hi in boxes:
            if lab == "bulkhead":
                continue
            d = np.maximum(np.maximum(lo - pts, pts - hi), 0.0)
            dist = np.sqrt((d ** 2).sum(1)) - TUBE_R
            i = int(dist.argmin())
            if dist[i] < worst[0]:
                worst = (float(dist[i]), lab)
    return worst


def bulkhead_clear():
    """Gap from each bulkhead's nut and body to the nearest member or bracket."""
    worst = (1e9, None)
    for zl in TIERS:
        V, _ = bulkhead_mesh(*DRAIN["tray_DOWN"], zl + SER)
        below = V[V[:, 2] < zl + SER]
        lo_b, hi_b = below.min(0), below.max(0)
        cands = [(m.label,) + m.bbox() for m in members()]
        for j in joints():
            W_, _ = j.bracket()
            cands.append((j.label, W_.min(0), W_.max(0)))
        for lab, lo, hi in cands:
            gap = np.maximum(lo - hi_b, lo_b - hi).max()
            if gap < worst[0]:
                worst = (float(gap), lab)
    return worst


if __name__ == "__main__":
    M = members()
    print(len(M), "pieces;", sum(m.length for m in M) / 1000, "m of 4040")
    for L, labs in cut_list():
        print(f"  {len(labs):2d} x {L:7.1f}  {' '.join(labs)}")
    sticks = cut_plan()
    print(len(sticks), "sticks of 2000")
    J = joints()
    from collections import Counter
    print(len(J), "joints", Counter(j.kind for j in J))
    print("corridor clear:", corridor_clear() or "yes")
    fc = fastener_clearances()
    print("tightest bracket to sheet slot: %.1f mm" % min(g for *_, g in fc))
    print("drain tubes, closest to frame or bracket: %.1f mm (%s)" % drain_clear())
    print("bulkheads, closest to frame or bracket: %.1f mm (%s)" % bulkhead_clear())
    for k, v in screw_depths().items():
        print(k, v)
