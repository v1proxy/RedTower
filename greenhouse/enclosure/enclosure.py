"""The Maag enclosure: frosted panels, doors and their hardware, as one model.

Every page of the enclosure booklet and every cut file is drawn from this
module, on top of cabinet.py, so a panel hole and the slot behind it cannot
disagree.

Coordinates are cabinet.py's: x 0..1397 left to right seen from the front,
y 0..559 with y = 0 the FRONT face, z 0..1829, floor at z = -20.

What it is
----------
Back, sides and top: 1/8 in (3.175) frosted polycarbonate, TUFFAK GP Matte,
cut and drilled by A&C Plastics (Houston) from three 48 x 96 in sheets.
Every panel is surface mounted on the frame's outer faces:

    EPDM foam tape 3/16 x 1/2 in on the land beside each slot, compressed
    from 4.76 to 3.5; an M5 x 16 button head and a DIN 9021 washer through an
    8 mm hole into a drop-in M5 T-nut, no more than 300 apart along any slot.

The 8 mm hole round a 5 mm screw is the expansion allowance: polycarbonate
moves 0.07 mm per metre per degree, 1.9 mm over the back's width for 20 C.
Screw holes sit at least two diameters (16) from any edge.

The back is three panels (no sheet is 1397 x 1829). They meet over the back
rails B1 and B2 with a 6 mm gap on the slot line, and an aluminium batten
over each seam clamps both edges: M5 x 20 through the batten and the gap.

Front: four doors, two stacked pairs, 4.5 clear polycarbonate cut by
SendCutSend. Each hangs on two 1 ft stainless piano hinges (McMaster 1658A15):
the frame leaf on a 3.0 polycarbonate spacer, screwed into drop-in M3 T-nuts
in the post's front slot; the door leaf bonded to the door with VHB 4905.
The doors close on cup magnets on the front rails (bottom pair F0 and F1, top
pair F3 and F4: F2 carries the split) and seal on EPDM weatherstrip on the
rail and post lands. The right door of each pair carries an astragal behind
the left one's edge: open the left door first.

The drain riser leaves the FL post: it runs outside the left panel on five
P-clips, and each tier's branch comes through the panel in a grommet.

    python enclosure.py        # the checks, as a report
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "gantry"))
sys.path.insert(0, os.path.join(_HERE, "..", "frame"))
sys.path.insert(0, _HERE)

from kit3d import extrude, merge, mv, rot, circle_pts, cylinder, box, revolve, ring, tube   # noqa: E402
import cabinet as C                                                                           # noqa: E402

W, D, H, SER = C.W, C.D, C.H, C.SER
LV = C.LEVELS
TOP = LV[-1]

# ------------------------------------------------------------------ panels
T_PANEL = 3.175                 # TUFFAK GP Matte 0.125 in, frosted
TAPE_T0 = 4.7625                # Presbond 2A1 EPDM foam strip, 3/16 x 1/2 in
TAPE = 3.5                      # compressed 26 %
TAPE_W = 12.7
OUT = TAPE + T_PANEL            # 6.675: panel outer face, off the frame face
HOLE = 8.0                      # M5 through an 8: the expansion allowance
EDGE_MIN = 2 * HOLE             # hole centre to any edge
PITCH = 300.0                   # most screws apart along a slot
LINE_IN = 4.5                   # tape edge off the slot centreline (slot mouth 8.2)
SEAM_GAP = 6.0
WASH = dict(od=15.0, id=5.3, t=1.2)          # DIN 9021 M5
CTE = 6.75e-5                   # polycarbonate, per C
SHEET = (1219.2, 2438.4)        # 48 x 96 in
KERF = 3.2

# Frame faces. A face point (u, v, w): u and v on the face, w out of it (w = 0
# is the frame's outer face, the tape sits on it, the panel at w = TAPE).
FACES = {
    "left":  dict(O=(0.0, 0.0, 0.0), eu=(0, 1, 0), ev=(0, 0, 1), ew=(-1, 0, 0), size=(D, H)),
    "right": dict(O=(W, 0.0, 0.0), eu=(0, 1, 0), ev=(0, 0, 1), ew=(1, 0, 0), size=(D, H)),
    "back":  dict(O=(0.0, D, 0.0), eu=(1, 0, 0), ev=(0, 0, 1), ew=(0, 1, 0), size=(W, H)),
    "top":   dict(O=(0.0, 0.0, H), eu=(1, 0, 0), ev=(0, 1, 0), ew=(0, 0, 1), size=(W, D)),
    "front": dict(O=(0.0, 0.0, 0.0), eu=(1, 0, 0), ev=(0, 0, 1), ew=(0, -1, 0), size=(W, H)),
}


def world(face, u, v, w=0.0):
    f = FACES[face]
    return (np.asarray(f["O"], float) + u * np.asarray(f["eu"], float)
            + v * np.asarray(f["ev"], float) + w * np.asarray(f["ew"], float))


def to_face(face, mesh):
    """A mesh built in (u, v, w) placed on `face`."""
    f = FACES[face]
    V, F = mesh
    M = np.array([f["eu"], f["ev"], f["ew"]], float)
    return (np.asarray(f["O"], float) + V @ M, F)


def slot_lines(face):
    """(vertical u-lines, horizontal v-lines) of the slots on a face."""
    if face in ("left", "right"):
        return [SER / 2, D - SER / 2], [z + SER / 2 for z in LV]
    if face == "back":
        return [SER / 2, W - SER / 2], [z + SER / 2 for z in LV]
    if face == "top":
        return [SER / 2, W - SER / 2], [SER / 2, D - SER / 2]
    raise KeyError(face)


SEAMS_V = [LV[1] + SER / 2, LV[2] + SER / 2]      # 324.8, 985.2: the back's seams


def _split(a, b, pitch=PITCH):
    n = max(1, math.ceil((b - a) / pitch - 1e-9))
    return [a + (b - a) * k / n for k in range(n + 1)]


def panels():
    """{name: (face, u0, v0, u1, v1)}, the six frosted panels."""
    s1, s2 = SEAMS_V
    g = SEAM_GAP / 2
    return {
        "left":        ("left", 0.0, 0.0, D, H),
        "right":       ("right", 0.0, 0.0, D, H),
        "back_bottom": ("back", 0.0, 0.0, W, s1 - g),
        "back_middle": ("back", 0.0, s1 + g, W, s2 - g),
        "back_upper":  ("back", 0.0, s2 + g, W, H),
        "top":         ("top", 0.0, 2.0, W, D - 2.0),
    }


# ------------------------------------------------------------------ the screw schedule
CLIP_V = None          # set below: the five P-clip heights on the FL line
ANTITIP_U = None


def _screws(face):
    """Every fastener through a panel into a slot on `face`:
    list of dicts (u, v, kind, line) where kind is 'panel', 'batten', 'clip'
    or 'antitip'. Every point is on a slot centreline, so a drop-in T-nut sits
    under it."""
    us, vs = slot_lines(face)
    out = []
    if face == "top":
        a, b = SER + 20.0, W - SER - 20.0          # clear of the post ends: no slot there
        for v in vs:
            for u in _split(a, b):
                out.append(dict(u=u, v=v, kind="panel", line="x"))
        a, b = SER + 20.0, D - SER - 20.0
        for u in us:
            for v in _split(a, b):
                out.append(dict(u=u, v=v, kind="panel", line="y"))
        for p in out:
            if p["line"] == "x" and abs(p["v"] - (D - SER / 2)) < 1e-6 and \
                    any(abs(p["u"] - a_) < 1e-6 for a_ in ANTITIP_U):
                p["kind"] = "antitip"
        return out
    seams = SEAMS_V if face == "back" else []
    # down each post line, every rail line plus a split of each bay
    for u in us:
        for v0, v1 in zip(vs[:-1], vs[1:]):
            for v in _split(v0, v1)[:-1]:
                out.append(dict(u=u, v=v, kind="batten" if any(abs(v - s) < 1e-6 for s in seams) else "panel",
                                line="post"))
        out.append(dict(u=u, v=vs[-1], kind="panel", line="post"))
    # along each rail line, between the posts
    for v in vs:
        if any(abs(v - s) < 1e-6 for s in seams):
            for u in BATTEN_U[1:-1]:
                out.append(dict(u=u, v=v, kind="batten", line="rail"))
            continue
        for u in _split(us[0], us[1])[1:-1]:
            out.append(dict(u=u, v=v, kind="panel", line="rail"))
    if face == "left":
        for p in out:
            if p["line"] == "post" and abs(p["u"] - SER / 2) < 1e-6 and \
                    any(abs(p["v"] - c) < 1e-6 for c in CLIP_V):
                p["kind"] = "clip"
    return out


def screws(face):
    """Every fastener through a panel into a slot on `face`:
    list of dicts (u, v, kind, line) where kind is 'panel', 'batten', 'clip'
    or 'antitip'. Where the harvest feeder covers a rail line its own M5 x 20
    screws take the place of the panel's (they are in cutouts(), as 'feeder M5')."""
    out = _screws(face)
    f = feeder()
    if f is not None and f.face == face:
        lo, hi = f.mods[0][0] - 10.0, f.mods[1][1] + 10.0
        out = [p for p in out if not (p["line"] == "rail" and abs(p["v"] - f.rail_v) < 1e-6 and lo < p["u"] < hi)]
    return out


BATTEN_U = [SER / 2, 245.0, 470.0, 678.5, 718.5, 927.0, 1152.0, W - SER / 2]
BATTEN = dict(w=25.4, t=3.175, gap=1.0, hole=5.5)     # 1 x 1/8 in, 5052, SendCutSend: two pieces a seam


def batten_pieces():
    """(u0, u1, [hole u]) for the two pieces over each seam."""
    mid = W / 2
    g = BATTEN["gap"] / 2
    return [(0.0, mid - g, [u for u in BATTEN_U if u < mid]),
            (mid + g, W, [u for u in BATTEN_U if u > mid])]


# The left face: the riser's P-clips are the panel screws on the FL line that
# fall inside the riser's run, so they hold the panel too.
def _fl_line():
    us, vs = slot_lines("left")
    out = []
    for v0, v1 in zip(vs[:-1], vs[1:]):
        out += _split(v0, v1)[:-1]
    return out + [vs[-1]]


def _junction_z(zl):
    return zl - 40.0


CLIP_V = [v for v in _fl_line() if _junction_z(LV[1]) + 30 < v < _junction_z(LV[3]) - 60]
ANTITIP_U = [_split(SER + 20.0, W - SER - 20.0)[1], _split(SER + 20.0, W - SER - 20.0)[-2]]


# ------------------------------------------------------------------ cutouts
FAN_HOLE, FAN_PITCH, FAN_SQ, FAN_T = 115.0, 105.0, 120.0, 25.0     # Noctua NF-F12 PWM
FAN_SCREW = 4.5
FANS = [(420.0, 310.0), (977.0, 310.0)]          # top face (x, y): hung under the panel, over the folded arm
FAN_GRILLS = 2                                   # per fan: one on the panel's outer face, one under the fan
INTAKE = (300.0, 170.0)                          # right face (y, z): base bay, filtered, passive
DUCT = (300.0, 420.0)                            # right face: humidifier duct, tier A bay
DUCT_HOLE, DUCT_PCD, DUCT_SCREW = 48.0, 66.0, 4.5
GLANDS = [(440.0, 200.0), (440.0, 780.0), (440.0, 1600.0)]   # right face: PG21, base, A (under the feeder), C bays
GLAND_HOLE = 28.5
GROMMET_HOLE = 22.2                              # 7/8 in, for 5/8 OD tube in a 1/8 panel
DRAIN_DY = 91.0

# The harvest feeder (greenhouse/harvest/harvest.py) hangs on one side panel:
# it adds two openings for the arm, its screw and wire holes, and takes over
# the panel's middle screw on that tier's rail line.
FEEDER_ON = True


def feeder():
    if not FEEDER_ON:
        return None
    hv = os.path.join(_HERE, "..", "harvest")
    if hv not in sys.path:
        sys.path.insert(0, hv)
    import harvest
    return harvest.FEEDER


def rect_cutouts(face):
    """[(u0, v0, u1, v1, r, what)] rectangular cut-outs through a face's panels."""
    f = feeder()
    return f.panel_cutouts() if f is not None and f.face == face else []


def grommets():
    """(y, z) on the left face: each branch leaves under its tier's left rail."""
    return [(DRAIN_DY, zl - 18.0) for zl in C.TIERS]


def cutouts(face):
    """[(u, v, dia, what)] through the panels on a face."""
    out = []
    if face == "top":
        for x, y in FANS:
            out.append((x, y, FAN_HOLE, "fan"))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    out.append((x + sx * FAN_PITCH / 2, y + sy * FAN_PITCH / 2, FAN_SCREW, "fan screw"))
    if face == "right":
        out.append((INTAKE[0], INTAKE[1], FAN_HOLE, "intake"))
        for sx in (-1, 1):
            for sy in (-1, 1):
                out.append((INTAKE[0] + sx * FAN_PITCH / 2, INTAKE[1] + sy * FAN_PITCH / 2, FAN_SCREW, "grill screw"))
        out.append((DUCT[0], DUCT[1], DUCT_HOLE, "duct"))
        for k in range(3):
            a = math.radians(90 + 120 * k)
            out.append((DUCT[0] + DUCT_PCD / 2 * math.cos(a), DUCT[1] + DUCT_PCD / 2 * math.sin(a),
                        DUCT_SCREW, "collar screw"))
        for u, v in GLANDS:
            out.append((u, v, GLAND_HOLE, "gland"))
    if face == "left":
        for u, v in grommets():
            out.append((u, v, GROMMET_HOLE, "grommet"))
    f = feeder()
    if f is not None and f.face == face:
        out += f.panel_holes()
    return out


def panel_rects(name):
    """[(u0, v0, u1, v1, r, what)] rectangular cut-outs inside one panel."""
    face, u0, v0, u1, v1 = panels()[name]
    return [c for c in rect_cutouts(face) if u0 <= c[0] and c[2] <= u1 and v0 <= c[1] and c[3] <= v1]


def panel_holes(name):
    """[(u, v, dia, what)] in face coordinates for one panel."""
    face, u0, v0, u1, v1 = panels()[name]
    out = []
    for p in screws(face):
        if p["kind"] == "batten":
            continue
        if u0 - 1e-6 <= p["u"] <= u1 + 1e-6 and v0 - 1e-6 <= p["v"] <= v1 + 1e-6:
            out.append((p["u"], p["v"], HOLE, p["kind"]))
    for c in cutouts(face):
        if u0 <= c[0] <= u1 and v0 <= c[1] <= v1:
            out.append(c)
    return out


def _rrect_loop(u0, v0, u1, v1, r, n=6):
    pts = []
    for (cx, cy), a0 in (((u1 - r, v0 + r), -90), ((u1 - r, v1 - r), 0), ((u0 + r, v1 - r), 90), ((u0 + r, v0 + r), 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def panel_mesh(name, w0=TAPE):
    face, u0, v0, u1, v1 = panels()[name]
    r = 3.0
    outline = []
    for (cx, cy), a0 in (((u1 - r, v0 + r), -90), ((u1 - r, v1 - r), 0), ((u0 + r, v1 - r), 90), ((u0 + r, v0 + r), 180)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            outline.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    holes = [circle_pts(d / 2, 40 if d < 30 else 96, u, v) for u, v, d, _ in panel_holes(name)]
    holes += [_rrect_loop(*c[:5]) for c in panel_rects(name)]
    m = extrude(np.array(outline), T_PANEL, z0=w0, holes=holes)
    return to_face(face, m)


def tapes(face):
    """Tape strips on a face, [(u0, v0, u1, v1)], on the land beside each slot
    on the bay's side: perimeter strips on the inside, intermediate rails on
    the upper land, both lands under a seam."""
    us, vs = slot_lines(face)
    a, b = LINE_IN, LINE_IN + TAPE_W
    out = []
    if face == "top":
        out.append((us[0] + a, vs[0] + a, us[0] + b, vs[1] - a))          # L4
        out.append((us[1] - b, vs[0] + a, us[1] - a, vs[1] - a))          # R4
        out.append((us[0] + a, vs[0] + a, us[1] - a, vs[0] + b))          # F4
        out.append((us[0] + a, vs[1] - b, us[1] - a, vs[1] - a))          # B4
        return out
    lo, hi = vs[0] + a, vs[-1] - a
    out.append((us[0] + a, lo, us[0] + b, hi))
    out.append((us[1] - b, lo, us[1] - a, hi))
    seams = SEAMS_V if face == "back" else []
    for k, v in enumerate(vs):
        sides = (1,) if k == 0 else (-1,) if k == len(vs) - 1 else (-1, 1) if v in seams else (1,)
        for s in sides:
            v0, v1 = (v + a, v + b) if s > 0 else (v - b, v - a)
            ua, ub = (us[0] + a, us[1] - a) if k in (0, len(vs) - 1) else (us[0] + b, us[1] - b)
            out.append((ua, v0, ub, v1))
    return out


def tape_mesh(face, squeeze=True):
    t = TAPE if squeeze else TAPE_T0
    ms = [box(u1 - u0, v1 - v0, t, c=(u0, v0, 0.0)) for u0, v0, u1, v1 in tapes(face)]
    return to_face(face, merge(*ms))


# ------------------------------------------------------------------ fasteners
def button5(L=16.0, detail=False):
    return C.button_head(5, L, detail)


def washer9021():
    return C.HW.washer(WASH["id"], WASH["od"], WASH["t"])


def tnut(M=5):
    """Drop-in hammer-head T-nut for slot 8, the wings' top at z = 0 against
    the lips (booklet/hardware.py)."""
    return C.HW.hammer_tnut(M)


def flat3(L=12.0, detail=False):
    """ISO 10642 M3 flat head with its socket, the top of the head on z = 0."""
    return C.HW.flat_head(3, L, detail)


def nyloc4():
    return C.HW.nyloc(4)


CLIP = dict(r_in=8.0, band=0.8, cushion=1.5, width=12.7, reach=18.0)   # 5/8 in cushioned P-clip
RISER = (-(OUT + CLIP["band"] + CLIP["cushion"] + C.TUBE_R), SER / 2 + CLIP["reach"])   # (-17, 38)


def fasteners(face, explode=0.0, nuts=True, heads=True, only=None):
    """(kind, mesh) for every panel fastener on a face. Kinds: screw, washer,
    tnut, batten_screw, clip_screw, antitip_screw."""
    out = []
    d = -np.asarray(FACES[face]["ew"], float)
    pts = list(screws(face))
    f = feeder()
    if f is not None and f.face == face and (not only or "panel" in only):
        # the harvest feeder's rail-line holes carry ordinary panel screws until the feeder goes on
        pts += [dict(u=u, v=v, kind="panel", line="feeder") for u, v, dd, w in cutouts(face) if w == "feeder M5"]
    for p in pts:
        if only and p["kind"] not in only:
            continue
        base = world(face, p["u"], p["v"], 0.0)
        if p["kind"] == "batten":
            top = OUT + BATTEN["t"]
            L = 20.0
        elif p["kind"] == "clip":
            top = OUT + 2 * CLIP["band"]
            L = 16.0
        elif p["kind"] == "antitip":
            top = OUT + ANTITIP["t"]
            L = 16.0
        else:
            top = OUT + WASH["t"]
            L = 16.0
        if heads:
            k = {"panel": "screw"}.get(p["kind"], p["kind"] + "_screw")
            out.append((k, C.place_axis(button5(L), base - d * (top + explode), d)))
            if p["kind"] == "panel":
                out.append(("washer", C.place_axis(washer9021(), base - d * (top + explode * 0.6), d)))
        if nuts:
            out.append(("tnut", C.place_axis(tnut(5), base + d * C.SLOT_LIP - d * (-explode * 0.0), d)))
    return out


def screw_stack():
    """Reach of each M5 below the frame face against the slot's depth."""
    rows = {}
    for kind, L, stack in (("panel", 16.0, WASH["t"] + OUT), ("batten", 20.0, BATTEN["t"] + OUT),
                           ("clip", 16.0, 2 * CLIP["band"] + OUT), ("antitip", 16.0, 2.0 + OUT)):
        reach = L - stack
        rows[kind] = dict(L=L, stack=round(stack, 3), reach=round(reach, 3),
                          spare=round(C.SLOT_DEPTH - reach, 3), past_lip=round(reach - C.SLOT_LIP, 3))
    return rows


# ------------------------------------------------------------------ battens
def batten_mesh(seam_v, explode=0.0):
    out = []
    for u0, u1, hs in batten_pieces():
        holes = [circle_pts(BATTEN["hole"] / 2, 36, u, seam_v) for u in hs]
        poly = np.array([(u0, seam_v - BATTEN["w"] / 2), (u1, seam_v - BATTEN["w"] / 2),
                         (u1, seam_v + BATTEN["w"] / 2), (u0, seam_v + BATTEN["w"] / 2)])
        out.append(extrude(poly, BATTEN["t"], z0=OUT + explode, holes=holes))
    return to_face("back", merge(*out))


# ------------------------------------------------------------------ fans, grills, filter, duct, glands
def fan_mesh():
    """Noctua NF-F12 PWM, drawn: 120 x 120 x 25 frame, Ø 114 throat, 105 holes,
    seven blades and a hub. Origin at the frame's centre, inlet face on z = 0."""
    r = 6.0
    sq = []
    for (cx, cy), a0 in (((60 - r, -60 + r), -90), ((60 - r, 60 - r), 0), ((-60 + r, 60 - r), 90), ((-60 + r, -60 + r), 180)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            sq.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    holes = [circle_pts(57.0, 96)]
    frame = extrude(np.array(sq), FAN_T, holes=holes)
    # the corner flanges' holes show as short bosses
    bosses = [cylinder(2.3, FAN_T + 0.2, c=(sx * 52.5, sy * 52.5, -0.1), n=16) for sx in (-1, 1) for sy in (-1, 1)]
    hub = cylinder(20.0, 21.0, c=(0, 0, 2.0))
    struts = [rot(box(38.0, 3.0, 3.0, c=(19.0, -1.5, FAN_T - 3.0)), rz=math.radians(45 + 90 * k)) for k in range(4)]
    blades = []
    for k in range(7):
        bl = extrude(np.array([(20.0, -9.0), (55.0, -14.0), (55.0, 14.0), (20.0, 9.0)]), 1.2, z0=-0.6)
        bl = rot(bl, rx=math.radians(32))
        bl = mv(bl, 0, 0, 11.0)
        blades.append(rot(bl, rz=2 * math.pi * k / 7))
    return merge(frame, hub, *struts, *blades), merge(*bosses)


def grill_mesh():
    """Noctua NA-FG1-12: steel wire rings and four tabs, on z = 0 up 2."""
    parts = [ring(r + 0.8, r - 0.8, 1.6) for r in (14.0, 28.0, 42.0, 56.0)]
    for k in range(4):
        parts.append(rot(box(60.0, 1.6, 1.6, c=(0.0, -0.8, 0.0)), rz=math.radians(45 + 90 * k)))
        tab = extrude(np.array([(-7.0, -7.0), (7.0, -7.0), (7.0, 7.0), (-7.0, 7.0)]), 1.6,
                      holes=[circle_pts(2.3, 24)])
        parts.append(mv(tab, (1 if k in (0, 3) else -1) * FAN_PITCH / 2, (1 if k < 2 else -1) * FAN_PITCH / 2, 0))
        parts.append(rot(box(14.0, 1.6, 1.6, c=(66.0, -0.8, 0.0)), rz=math.radians(45 + 90 * k)))
    return merge(*parts)


def filter_mesh():
    """DEMCiflex 120 mm magnetic dust filter: a thin square with its mesh."""
    rim = extrude(np.array([(-60, -60), (60, -60), (60, 60), (-60, 60)], float), 2.0,
                  holes=[np.array([(-54, -54), (-54, 54), (54, 54), (54, -54)], float)])
    mesh_ = box(108.0, 108.0, 0.6, c=(-54.0, -54.0, 0.7))
    return rim, mesh_


COLLAR = dict(flange_od=84.0, flange_t=3.0, bore=DUCT_HOLE - 1.0, spigot_od=50.3, spigot_l=32.0, wall=2.4)


def collar_mesh():
    """The printed duct collar (PETG): a flange on the panel's outer face, a
    spigot the 2 in duct slides over. Flange face on z = 0, spigot up +z."""
    c = COLLAR
    ri = c["spigot_od"] / 2 - c["wall"]
    prof = [(ri, 0.0), (c["flange_od"] / 2, 0.0), (c["flange_od"] / 2, c["flange_t"]),
            (c["spigot_od"] / 2, c["flange_t"]), (c["spigot_od"] / 2, c["flange_t"] + c["spigot_l"] - 1.5),
            (c["spigot_od"] / 2 - 1.5, c["flange_t"] + c["spigot_l"]), (ri, c["flange_t"] + c["spigot_l"]), (ri, 0.0)]
    body = revolve(prof, n=96)
    return body


def collar_solid():
    """The same collar as a closed, printable solid with its three screw holes."""
    c = COLLAR
    ri = c["spigot_od"] / 2 - c["wall"]
    holes = [circle_pts(ri, 96)]
    for k in range(3):
        a = math.radians(90 + 120 * k)
        holes.append(circle_pts(DUCT_SCREW / 2, 32, DUCT_PCD / 2 * math.cos(a), DUCT_PCD / 2 * math.sin(a)))
    fl = extrude(circle_pts(c["flange_od"] / 2, 96), c["flange_t"], holes=holes)
    sp = extrude(circle_pts(c["spigot_od"] / 2, 96), c["spigot_l"] + c["flange_t"] - 1.0, z0=1.0, holes=[circle_pts(ri, 96)])
    return fl, sp


def gland_mesh():
    """PG21 nylon gland, panel face on z = 0, outside +z: hex body, dome nut; the
    locknut on the inside, below z = -T_PANEL."""
    out_ = merge(cylinder(19.0, 8.0, n=6), mv(revolve([(0, 0), (15.5, 0), (15.5, 7), (12, 13), (7.5, 14.5), (0, 14.5)]), 0, 0, 8.0))
    lock = mv(cylinder(19.0, 6.0, n=6), 0, 0, -T_PANEL - 6.0)
    thread = mv(cylinder(14.1, T_PANEL + 6.0), 0, 0, -T_PANEL - 6.0)
    return merge(out_, lock, thread)


def grommet_mesh():
    """Rubber grommet, 7/8 in hole, 5/8 in bore: panel between z = 0 and -T_PANEL."""
    prof = [(8.1, -T_PANEL - 3.0), (14.3, -T_PANEL - 3.0), (14.3, -T_PANEL), (11.1, -T_PANEL), (11.1, 0.0),
            (14.3, 0.0), (14.3, 3.0), (8.1, 3.0)]
    return revolve(prof + [prof[0]], n=48)


def clip_mesh():
    """5/8 in cushioned P-clip in its own frame: screw axis on the origin along
    +z (head side), the panel face on z = 0, the loop at +y = reach."""
    c = CLIP
    rc = c["r_in"] + c["cushion"] + c["band"] / 2
    ctr_z = c["band"] * 2 + 0.0 + c["r_in"] + c["cushion"]
    loop_steel = rot(ring(c["r_in"] + c["cushion"] + c["band"], c["r_in"] + c["cushion"], c["width"],
                          c=(0, 0, -c["width"] / 2)), ry=0)
    loop_rub = ring(c["r_in"] + c["cushion"], c["r_in"], c["width"] - 1.0, c=(0, 0, -(c["width"] - 1.0) / 2))
    # the loop's axis is the riser's (along the face's v); build it on z then turn
    loop = merge(loop_steel)
    loop = rot(loop, rx=-math.pi / 2)            # axis now along y
    loop = rot(loop, rz=math.pi / 2)             # axis along x (the face's v)
    loop_r = rot(rot(loop_rub, rx=-math.pi / 2), rz=math.pi / 2)
    ctr = (0.0, c["reach"], c["r_in"] + c["cushion"] + c["band"])
    tab = extrude(np.array([(-c["width"] / 2, -6.0), (c["width"] / 2, -6.0), (c["width"] / 2, c["reach"] - 6.0),
                            (-c["width"] / 2, c["reach"] - 6.0)]), 2 * c["band"],
                  holes=[circle_pts(2.7, 24)])
    return merge(mv(loop, *ctr), tab), mv(loop_r, *ctr)


# ------------------------------------------------------------------ drain, re-routed
def _branch_inner(zl):
    """The inside part of a branch, as cabinet.py draws it, up to the frame face."""
    dx, dy = C.DRAIN["tray_DOWN"]
    zf = zl + SER
    return [(dx, dy, zf - 22.4), (dx, dy, zl - 4), (dx - 12, dy, zl - C.TUBE_R - 4),
            (20.0, dy - 2, zl - 15), (0.0, DRAIN_DY, zl - 18)]


def drain_routes():
    """The re-routed drain: each branch through its grommet, the riser on the
    P-clips outside the left panel, into the bucket."""
    rx, ry = RISER
    branches = []
    for zl in C.TIERS[::-1]:
        jz = _junction_z(zl)
        P = _branch_inner(zl) + [(-OUT - 6.0, DRAIN_DY, zl - 18.5), (rx + 3.0, DRAIN_DY - 8.0, zl - 23),
                                 (rx, 62.0, zl - 30), (rx, ry + 10.0, jz + 3.0), (rx + 0.01, ry, jz)]
        branches.append(np.array(P, float))
    lid = -C.FOOT_H + C.BUCKET["h"] + C.BUCKET["lid"]
    ja = _junction_z(C.TIERS[0])
    bx, by = -75.0, 75.0
    riser = np.array([(rx, ry, _junction_z(C.TIERS[2])), (rx, ry, ja), (rx - 2, ry + 3, ja - 9),
                      (-36.0, 50.0, ja - 20), (-62.0, 66.0, lid + 8), (bx, by, lid - 2), (bx, by, lid - 25)])
    return {"branches": branches, "riser": riser}


def _plen(P):
    P = np.asarray(P, float)
    return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())


def branch_trim():
    """Tube length change per tier, outside the frame face: old route (to the
    riser on the post) against the new one (through the grommet to the riser
    on the clips). Negative: cut that much off."""
    old = C.drain_routes()["branches"]
    new = drain_routes()["branches"]
    out = {}
    for lab, o, n in zip(("C", "B", "A"), old, new):
        o_out = o[[i for i, p in enumerate(o) if p[0] <= 0.0 + 1e-6]]
        n_out = n[[i for i, p in enumerate(n) if p[0] <= 0.0 + 1e-6]]
        out[lab] = round(_plen(n_out) - _plen(o_out), 1)
    return out


def drain_fittings():
    """Tees, elbow and P-clips of the re-routed riser: (kind, mesh)."""
    rx, ry = RISER
    out = []
    dx, dy = C.DRAIN["tray_DOWN"]
    for zl in C.TIERS:
        el = merge(cylinder(9.0, 16.0, c=(0, 0, -8.0)), rot(cylinder(9.0, 20.0), ry=-math.pi / 2))
        out.append(("elbow", mv(el, dx, dy, zl - 4)))
    for k, zl in enumerate(C.TIERS[::-1]):
        jz = _junction_z(zl)
        run = cylinder(9.0, 40.0 if k else 22.0, c=(0, 0, -20.0 if k else -22.0))
        stub = rot(cylinder(9.0, 20.0), rx=-math.pi / 2)
        out.append(("elbow" if k == 0 else "tee", mv(merge(run, stub), rx, ry, jz)))
    return out


def clips_world(explode=0.0):
    """(steel, rubber) meshes of the five P-clips, screwed on the FL line."""
    st, rb = [], []
    for v in CLIP_V:
        s, r = clip_mesh()
        # clip frame: x along face v, y along face u, z out of the face
        def place(m):
            V, F = m
            u = SER / 2 + V[:, 1]
            vv = v + V[:, 0]
            w = OUT + V[:, 2] + explode
            P = np.array([world("left", a, b, c) for a, b, c in zip(u, vv, w)])
            return (P, F)
        st.append(place(s)); rb.append(place(r))
    return merge(*st), merge(*rb)


def grommets_world(explode=0.0):
    ms = []
    for u, v in grommets():
        g = grommet_mesh()
        ms.append(to_face("left", mv(g, u, v, OUT + explode)))
    return merge(*ms)


# ------------------------------------------------------------------ anti-tip
ANTITIP = dict(t=2.0, base=(32.0, 25.0), up=25.0)


def antitip_mesh(u, explode=0.0):
    """Anti-tip kit, cabinet bracket: an L on the top panel over B4, its leg up,
    the cable leaving toward the wall."""
    a = ANTITIP
    y0 = D - SER / 2
    base = extrude(np.array([(-a["base"][0] / 2, -10.0), (a["base"][0] / 2, -10.0), (a["base"][0] / 2, 15.0),
                             (-a["base"][0] / 2, 15.0)]), a["t"], holes=[circle_pts(2.75, 24)])
    leg = box(a["base"][0], a["t"], a["up"], c=(-a["base"][0] / 2, 15.0 - a["t"], 0.0))
    m = merge(base, leg)
    cable = tube(np.array([(0, 15.0, 15.0), (0, 40.0, 18.0), (0, 70.0, 26.0)]), 1.6, 10)
    m = mv(m, u, y0, H + OUT + explode)
    cable = mv(cable, u, y0, H + OUT + explode)
    return m, cable


# ------------------------------------------------------------------ doors
DOOR_T = 4.5                    # SendCutSend polycarbonate 0.177 in, clear
SPACER_T = 3.0                  # SendCutSend polycarbonate 0.118 in
LEAF_T = 0.042 * 25.4           # McMaster 1658A15, 304 stainless, 1 1/2 in open
KNUCKLE_R = 0.178 * 25.4 / 2
LEAF_W = 0.75 * 25.4            # pin axis to leaf edge
HINGE_L = 12.0 * 25.4
VHB_T = 0.5                     # 3M VHB 4905
GAP_F = SPACER_T + 2 * LEAF_T + VHB_T          # 5.634: frame face to the door's inner face
PIN_W = SPACER_T + LEAF_T                      # pin axis off the frame face
HOLE_LINE = 9.5                                # pin to the leaf's hole line, as drawn: step 1 measures it
PIN_U = SER / 2 - HOLE_LINE                    # 10.5: the leaf's holes sit on the slot line
SPACER_SLOT = 6.0                              # takes a hole line anywhere from 8 to 11
CTR_GAP = 3.0
SPLIT = LV[2] + SER / 2         # 985.2: the pairs meet on F2's slot line
SPLIT_GAP = 3.0
MAG = dict(d=16.0, t=4.5)       # cup magnet, M3 countersunk
DISC = dict(d=16.0, t=1.0)      # steel disc, adhesive backed
STRIP = dict(w=7.9, t=6.35)     # Frost King V25BK, EPDM, 5/16 x 1/4 in
PULL = dict(cc=96.0, L=128.0, d=10.0, proj=30.0, screw=4.5)
REED = dict(sw=(64.0, 16.0, 13.0), mag=(51.0, 13.0, 10.0))   # Honeywell 7939WG-WH, drawn as blocks


def door_x(side):
    edge = PIN_U + KNUCKLE_R + 0.5
    if side == "L":
        return edge, W / 2 - CTR_GAP / 2
    return W / 2 + CTR_GAP / 2, W - edge


def door_z(pair):
    return (0.0, SPLIT - SPLIT_GAP / 2) if pair == "bottom" else (SPLIT + SPLIT_GAP / 2, H)


DOORS = [(p, s) for p in ("bottom", "top") for s in ("L", "R")]


def door_name(pair, side):
    return f"door_{pair}_{side}"


def hinge_z(pair):
    z0, z1 = door_z(pair)
    if pair == "bottom":
        return [(60.0, 60.0 + HINGE_L), (z1 - 60.0 - HINGE_L, z1 - 60.0)]
    return [(z0 + 30.0, z0 + 30.0 + HINGE_L), (z1 - 30.0 - HINGE_L, z1 - 30.0)]


MAG_X = {"L": 640.0, "R": W - 640.0}
MAG_Z = {"bottom": [LV[0] + SER / 2, LV[1] + SER / 2], "top": [LV[3] + SER / 2, LV[4] + SER / 2]}
PULL_X = {"L": W / 2 - CTR_GAP / 2 - 40.0, "R": W / 2 + CTR_GAP / 2 + 42.0}
PULL_Z = {"bottom": 650.0, "top": 1200.0}
REED_X = {"L": 592.0, "R": W - 592.0}
REED_RAIL = {"bottom": LV[2], "top": LV[4]}     # switch on the underside of F2 and F4


def pull_holes(pair, side):
    x, z = PULL_X[side], PULL_Z[pair]
    return [(x, z - PULL["cc"] / 2), (x, z + PULL["cc"] / 2)]


def door_outline(pair, side, r=3.0):
    x0, x1 = door_x(side)
    z0, z1 = door_z(pair)
    pts = []
    for (cx, cy), a0 in (((x1 - r, z0 + r), -90), ((x1 - r, z1 - r), 0), ((x0 + r, z1 - r), 90), ((x0 + r, z0 + r), 180)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def door_mesh(pair, side, angle=0.0):
    holes = [circle_pts(PULL["screw"] / 2, 32, x, z) for x, z in pull_holes(pair, side)]
    m = extrude(door_outline(pair, side), DOOR_T, z0=GAP_F, holes=holes)
    return swing(to_face("front", m), side, angle)


def pin_xy(side):
    u = PIN_U if side == "L" else W - PIN_U
    return np.array([u, -PIN_W])


def swing(mesh, side, angle):
    """Turn a door-side mesh about its hinge pin by `angle` degrees open."""
    if not angle:
        return mesh
    V, F = mesh
    p = pin_xy(side)
    a = math.radians(angle) * (-1 if side == "L" else 1)       # left door opens clockwise from above
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c, -s], [s, c]])
    xy = (V[:, :2] - p) @ R.T + p
    return (np.c_[xy, V[:, 2]], F)


def hinge_meshes(pair, side, angle=0.0):
    """(frame leaf + knuckle, door leaf, spacer) for both hinges of a door."""
    fr, dr, sp = [], [], []
    pu = pin_xy(side)[0]
    sgn = 1 if side == "L" else -1
    for z0, z1 in hinge_z(pair):
        L = z1 - z0
        lf = box(LEAF_W - KNUCKLE_R, LEAF_T, L, c=(0.0, 0.0, 0.0))
        lf = (lf[0] * np.array([sgn, 1, 1]) + np.array([pu + sgn * KNUCKLE_R, -SPACER_T - LEAF_T, z0]), lf[1])
        kn = mv(cylinder(KNUCKLE_R, L, n=24), pu, -PIN_W, z0)
        fr.append(merge(lf, kn))
        dl = box(LEAF_W - KNUCKLE_R, LEAF_T, L)
        dl = (dl[0] * np.array([sgn, 1, 1]) + np.array([pu + sgn * KNUCKLE_R, -SPACER_T - 2 * LEAF_T, z0]), dl[1])
        dr.append(swing(dl, side, angle))
        s0 = pu + sgn * (KNUCKLE_R + 0.3)
        s1 = pu + sgn * LEAF_W
        a_, b_ = min(s0, s1), max(s0, s1)
        sc = SER / 2 if side == "L" else W - SER / 2
        h = SPACER_SLOT / 2
        slot = np.array([(sc - h, z0 + 8.0), (sc + h, z0 + 8.0), (sc + h, z1 - 8.0), (sc - h, z1 - 8.0)])
        spc = extrude(np.array([(a_, z0), (b_, z0), (b_, z1), (a_, z1)]), SPACER_T, holes=[slot[::-1]])
        sp.append(to_face("front", spc))
    return merge(*fr), merge(*dr), merge(*sp)


def spacer_outline(side="L"):
    """The spacer in its own flat frame for the DXF: (outline, slot)."""
    a_ = KNUCKLE_R + 0.3
    b_ = LEAF_W
    L = HINGE_L
    off = SER / 2 - PIN_U
    h = SPACER_SLOT / 2
    return (np.array([(a_, 0), (b_, 0), (b_, L), (a_, L)]),
            np.array([(off - h, 8.0), (off + h, 8.0), (off + h, L - 8.0), (off - h, L - 8.0)]))


def hinge_screws(pair, side):
    """Where the frame leaf's screws are drawn: four per hinge on the slot
    line. The real hinge's own holes decide; every hole gets one."""
    u = SER / 2 if side == "L" else W - SER / 2
    out = []
    for z0, z1 in hinge_z(pair):
        for k in range(4):
            out.append((u, z0 + (k + 0.5) * (z1 - z0) / 4))
    return out


def magnet_meshes(pair, side):
    """(cup magnets on the rails, steel discs on the door) for one door."""
    mags, discs = [], []
    x = MAG_X[side]
    for z in MAG_Z[pair]:
        cup = revolve([(0, 0), (MAG["d"] / 2, 0), (MAG["d"] / 2, MAG["t"]), (3.0, MAG["t"]), (1.7, MAG["t"] - 1.7),
                       (1.7, 0)], n=48)
        mags.append(to_face("front", mv(cup, x, z, 0.0)))
        dsc = cylinder(DISC["d"] / 2, DISC["t"], c=(x, z, GAP_F - DISC["t"]), n=48)
        discs.append(to_face("front", dsc))
    return merge(*mags), merge(*discs)


def strips(pair):
    """Weatherstrip on the frame face for one pair: [(x0, z0, x1, z1)]."""
    xl0 = PIN_U + LEAF_W + 0.15
    xl1 = xl0 + STRIP["w"]
    xr1 = W - xl0
    xr0 = xr1 - STRIP["w"]
    if pair == "bottom":
        zb0 = LV[0] + SER / 2 + MAG["d"] / 2 + 0.5                   # above F0's magnets
        zt1 = LV[2] + SER / 2 - 4.1 - 0.4                            # F2's lower land, by the slot
        hz = [(zb0, zb0 + STRIP["w"]), (zt1 - STRIP["w"], zt1)]
    else:
        zb0 = LV[2] + SER / 2 + 4.1 + 0.4 + 2.4                      # F2's upper land
        zt1 = LV[4] + SER / 2 - MAG["d"] / 2 - 0.5                   # under F4's magnets
        hz = [(zb0, zb0 + STRIP["w"]), (zt1 - STRIP["w"], zt1)]
    out = [(xl0, h0, xr1, h1) for h0, h1 in hz]
    out.append((xl0, hz[0][0], xl1, hz[1][1]))
    out.append((xr0, hz[0][0], xr1, hz[1][1]))
    return out


def strip_mesh(pair, squeeze=True):
    t = GAP_F if squeeze else STRIP["t"]
    return to_face("front", merge(*[box(x1 - x0, z1 - z0, t, c=(x0, z0, 0.0)) for x0, z0, x1, z1 in strips(pair)]))


ASTRAGAL = dict(w=40.0, t=SPACER_T, bond=18.5)


def astragal_span(pair):
    s = strips(pair)
    z0 = s[0][3] + 1.5
    z1 = s[1][1] - 1.5
    return z0, z1


def astragal_mesh(pair, angle=0.0):
    z0, z1 = astragal_span(pair)
    xc = W / 2
    m = box(ASTRAGAL["w"], z1 - z0, ASTRAGAL["t"], c=(xc - ASTRAGAL["w"] / 2, z0, GAP_F - VHB_T - ASTRAGAL["t"]))
    return swing(to_face("front", m), "R", angle)


def pull_mesh(pair, side, angle=0.0):
    (x, za), (_, zb) = pull_holes(pair, side)
    w0 = GAP_F + DOOR_T
    p = PULL
    posts = [cylinder(4.0, p["proj"] - p["d"] / 2, c=(x, z, w0), n=24) for z in (za, zb)]
    bar = rot(cylinder(p["d"] / 2, p["L"], n=24), rx=-math.pi / 2)        # along +v
    bar = (bar[0][:, [0, 2, 1]] * np.array([1, 1, -1]) * np.array([1, -1, 1]), bar[1])
    bar = mv(cylinder(p["d"] / 2, p["L"], n=24), 0, 0, 0)
    bar = (bar[0][:, [0, 2, 1]], bar[1])                                      # axis along v
    bar = mv(bar, x, (za + zb) / 2 - p["L"] / 2, w0 + p["proj"] - p["d"] / 2)
    heads = [cylinder(3.6, 2.8, c=(x, z, GAP_F - 2.8 - 1.0), n=24) for z in (za, zb)]
    washers = [ring(4.5, 2.2, 1.0, c=(x, z, GAP_F - 1.0)) for z in (za, zb)]
    m = to_face("front", merge(*posts, bar, *heads, *washers))
    return swing(m, side, angle)


def reed_meshes(pair, side, angle=0.0):
    """(switch on the underside of the rail, magnet on the door) as blocks."""
    x = REED_X[side]
    zr = REED_RAIL[pair]
    sw, mg = REED["sw"], REED["mag"]
    s = box(sw[0], sw[1], sw[2], c=(x - sw[0] / 2, 3.0, zr - sw[2]))
    m_w0 = GAP_F
    mag = box(mg[0], mg[2], mg[1], c=(x - mg[0] / 2, -m_w0, zr - sw[2] - 1.0 - mg[1]))
    return s, swing(mag, side, angle)


def door_parts(pair, side, angle=0.0):
    """Every door-side mesh, swung: {name: mesh}."""
    out = {"door": door_mesh(pair, side, angle)}
    fr, dl, sp = hinge_meshes(pair, side, angle)
    out["hinge_frame"], out["hinge_door"], out["spacer"] = fr, dl, sp
    mags, discs = magnet_meshes(pair, side)
    out["discs"] = swing(discs, side, angle)
    out["pull"] = pull_mesh(pair, side, angle)
    out["reed_magnet"] = reed_meshes(pair, side, angle)[1]
    if side == "R":
        out["astragal"] = astragal_mesh(pair, angle)
    return out


def frame_side(pair):
    """What stays on the frame for a pair: magnets, strips, reed switches,
    hinge frame leaves, spacers."""
    out = {}
    ms = [magnet_meshes(pair, s)[0] for s in ("L", "R")]
    out["magnets"] = merge(*ms)
    out["strips"] = strip_mesh(pair)
    out["reeds"] = merge(*[reed_meshes(pair, s)[0] for s in ("L", "R")])
    return out


# ------------------------------------------------------------------ checks
def nest():
    """Three 48 x 96 sheets: [(sheet, [(panel, w along 48, l along 96)], spare across)]."""
    P = panels()
    dims = {k: (abs(v[3] - v[1]), abs(v[4] - v[2])) for k, v in P.items()}
    plan = [("A", ["back_bottom", "back_upper"]), ("B", ["back_middle", "top"]), ("C", ["left", "right"])]
    out = []
    for sh, names in plan:
        rows = []
        for n in names:
            a, b = dims[n]
            lng, sht = max(a, b), min(a, b)
            rows.append((n, sht, lng))
        across = sum(r[1] for r in rows) + KERF * (len(rows) - 1)
        out.append((sh, rows, SHEET[0] - across, SHEET[1] - max(r[2] for r in rows)))
    return out


def edge_report():
    """Smallest hole-centre-to-edge distance per panel, against 2 x diameter
    (small holes) or 25 clear (cutouts)."""
    rep = {}
    for name, (face, u0, v0, u1, v1) in panels().items():
        worst = (1e9, None)
        for u, v, d, what in panel_holes(name):
            e = min(u - u0, u1 - u, v - v0, v1 - v)
            need = 2 * d if d <= 10 else d / 2 + 25.0
            if e - need < worst[0]:
                worst = (e - need, (what, round(u, 1), round(v, 1), round(e, 1), round(need, 1)))
        rep[name] = worst
    return rep


def footprints(face):
    """What occupies the panel's outer face: [(kind, ('c', u, v, r) or ('r', u0, v0, u1, v1))]."""
    out = []
    for p in screws(face):
        r = {"panel": WASH["od"] / 2, "batten": 5.0, "clip": 8.0, "antitip": 16.5}[p["kind"]]
        out.append((p["kind"], ("c", p["u"], p["v"], r)))
    if face == "top":
        for x, y in FANS:
            out.append(("fan", ("r", x - 60, y - 60, x + 60, y + 60)))
    if face == "right":
        x, y = INTAKE
        out.append(("intake", ("r", x - 61, y - 61, x + 61, y + 61)))
        out.append(("collar", ("c", DUCT[0], DUCT[1], COLLAR["flange_od"] / 2)))
        for u, v in GLANDS:
            out.append(("gland", ("c", u, v, 19.0)))
    if face == "left":
        for u, v in grommets():
            out.append(("grommet", ("c", u, v, 14.3)))
    f = feeder()
    if f is not None and f.face == face:
        out.append(("feeder", ("r", f.mods[0][0], f.v_low, f.mods[1][1], f.vt)))
    if face == "back":
        for s in SEAMS_V:
            out.append(("batten", ("r", 0.0, s - BATTEN["w"] / 2, W, s + BATTEN["w"] / 2)))
    return out


def _gap(a, b):
    """Clear distance between two footprints (negative: overlap)."""
    if a[0] == "c" and b[0] == "c":
        return math.hypot(a[1] - b[1], a[2] - b[2]) - a[3] - b[3]
    if a[0] == "r" and b[0] == "r":
        dx = max(a[1] - b[3], b[1] - a[3]); dy = max(a[2] - b[4], b[2] - a[4])
        return max(dx, dy) if (dx < 0 or dy < 0) and not (dx > 0 or dy > 0) else math.hypot(max(dx, 0), max(dy, 0)) if dx > 0 and dy > 0 else max(dx, dy)
    if a[0] == "r":
        a, b = b, a
    _, cu, cv, r = a
    _, u0, v0, u1, v1 = b
    du = max(u0 - cu, 0, cu - u1); dv = max(v0 - cv, 0, cv - v1)
    if du == 0 and dv == 0:
        return -r - min(cu - u0, u1 - cu, cv - v0, v1 - cv)
    return math.hypot(du, dv) - r


def footprint_report():
    """Tightest pair of unrelated things on each face's outside."""
    rep = {}
    for face in ("left", "right", "back", "top"):
        F = footprints(face)
        worst = (1e9, None)
        for i in range(len(F)):
            for j in range(i + 1, len(F)):
                ki, ai = F[i]; kj, aj = F[j]
                if {ki, kj} == {"batten"}:
                    continue
                if "batten" in (ki, kj) and ai[0] != aj[0]:
                    # batten screws live under the batten strip by design
                    if (ki == "batten" and ai[0] == "c") or (kj == "batten" and aj[0] == "c"):
                        continue
                g = _gap(ai, aj)
                if g < worst[0]:
                    worst = (round(g, 2), (ki, kj))
        rep[face] = worst
    return rep


def members_on(face):
    """Frame member faces behind a face, as (u0, v0, u1, v1)."""
    us, vs = slot_lines(face)
    if face == "top":
        return [(0, 0, W, SER), (0, D - SER, W, D), (0, 0, SER, D), (W - SER, 0, W, D)]
    out = [(us[0] - SER / 2, 0, us[0] + SER / 2, H), (us[1] - SER / 2, 0, us[1] + SER / 2, H)]
    out += [(0, v - SER / 2, FACES[face]["size"][0], v + SER / 2) for v in vs]
    return out


def cutout_report():
    """Every cutout must open into a bay: its inside footprint (gland locknut,
    grommet flange, fan screw nut, collar hole) clear of every member and every
    tape strip."""
    rep = {}
    for face in ("left", "right", "top"):
        worst = (1e9, None)
        obst = [("member", ("r",) + tuple(m)) for m in members_on(face)]
        obst += [("tape", ("r",) + tuple(t)) for t in tapes(face)]
        for u, v, d, what in cutouts(face):
            if what == "feeder M5":
                continue                      # screws into the rail, like a panel screw
            r = {"gland": 19.0, "grommet": 14.3, "fan": FAN_HOLE / 2, "intake": FAN_HOLE / 2,
                 "duct": DUCT_HOLE / 2, "feeder well nut": 8.0, "reed wire": 6.0}.get(what, 5.0)
            for k, ob in obst:
                g = _gap(("c", u, v, r), ob)
                if g < worst[0]:
                    worst = (round(g, 2), (what, k, round(u, 1), round(v, 1)))
        for u0, v0, u1, v1, r, what in rect_cutouts(face):
            for k, ob in obst:
                g = _gap(("r", u0, v0, u1, v1), ob)
                if g < worst[0]:
                    worst = (round(g, 2), (what, k, round(u0, 1), round(v0, 1)))
        rep[face] = worst
    return rep


def gantry_report():
    """The gantry's parts against the panels' inner faces (no arm: its meshes
    are not in the repo, and it stays inside the corridor)."""
    try:
        import frame as GF
        import arm280 as A
        keep = A.pose
        A.pose = lambda *a, **k: []
        V = []
        for x in (GF.X_MIN, GF.X_MAX):
            for z in (GF.MAST_Z0 + 60, 1700.0):
                for p in GF.gantry_parts(x=x, z=z):
                    V.append(p.mesh[0])
        A.pose = keep
        V = np.vstack(V)
    except Exception as e:                      # pragma: no cover
        return {"error": str(e)}
    return {"left": round(float(V[:, 0].min() + TAPE), 2),
            "right": round(float(W + TAPE - V[:, 0].max()), 2),
            "back": round(float(D + TAPE - V[:, 1].max()), 2),
            "top": round(float(H + TAPE - V[:, 2].max()), 2)}


def door_swing(pair, side, step=0.5):
    """Widest the door opens before any part of it (door, door leaf, pull,
    reed magnet, astragal) meets the post, the side panel or the frame leaf."""
    import matplotlib.path as mpath
    obst = []
    if side == "L":
        obst.append(np.array([(-OUT - 0.5, 0.0), (SER, 0.0), (SER, 60.0), (-OUT - 0.5, 60.0)]))
        obst.append(np.array([(PIN_U + KNUCKLE_R + 0.3, -SPACER_T - LEAF_T), (PIN_U + LEAF_W, -SPACER_T - LEAF_T),
                              (PIN_U + LEAF_W, 0.0), (PIN_U + KNUCKLE_R + 0.3, 0.0)]))
    else:
        obst.append(np.array([(W - SER, 0.0), (W + OUT + 0.5, 0.0), (W + OUT + 0.5, 60.0), (W - SER, 60.0)]))
        obst.append(np.array([(W - PIN_U - LEAF_W, -SPACER_T - LEAF_T), (W - PIN_U - KNUCKLE_R - 0.3, -SPACER_T - LEAF_T),
                              (W - PIN_U - KNUCKLE_R - 0.3, 0.0), (W - PIN_U - LEAF_W, 0.0)]))
    paths = [mpath.Path(o) for o in obst]
    a = 0.0
    while a < 270:
        a2 = a + step
        parts = door_parts(pair, side, a2)
        pts = np.vstack([parts[k][0][:, :2] for k in ("door", "pull", "hinge_door")])
        hit = any(p.contains_points(pts, radius=-0.05).any() for p in paths)
        if hit:
            return a
        a = a2
    return a


def gap_budget():
    return dict(hinge=round(GAP_F, 3), magnet_disc=MAG["t"] + DISC["t"],
                air_at_magnet=round(GAP_F - MAG["t"] - DISC["t"], 3),
                strip_squeeze=round((STRIP["t"] - GAP_F) / STRIP["t"] * 100, 1),
                astragal_to_frame=round(GAP_F - VHB_T - ASTRAGAL["t"], 3),
                astragal_to_left_door=round(VHB_T, 3),
                tape_squeeze=round((TAPE_T0 - TAPE) / TAPE_T0 * 100, 1))


def counts():
    from collections import Counter
    c = Counter()
    for face in ("left", "right", "back", "top"):
        for p in screws(face):
            c["M5 drop-in T-nut"] += 1
            if p["kind"] == "panel":
                c["M5 x 16 button head"] += 1; c["DIN 9021 M5 washer"] += 1
            elif p["kind"] == "batten":
                c["M5 x 20 button head"] += 1
            else:
                c["M5 x 16 button head"] += 1
    f = feeder()
    if f is not None:
        n = len([c for c in cutouts(f.face) if c[3] == "feeder M5"])
        c["M5 drop-in T-nut"] += n
        c["M5 x 16 button head"] += n
        c["DIN 9021 M5 washer"] += n
    n_h = sum(len(hinge_screws(p, s)) for p, s in DOORS)
    c["M3 x 12 flat head, hinges (drawn)"] = n_h
    c["M3 x 12 flat head, magnets"] = sum(len(MAG_Z[p]) for p, s in DOORS)
    c["M3 drop-in T-nut"] = n_h + c["M3 x 12 flat head, magnets"]
    c["M4 x 40 button head, fans"] = 8
    c["M4 x 16 button head, intake grill"] = 4
    c["M4 x 16 button head, duct collar"] = 3
    c["M4 nyloc"] = 15
    c["M4 washer"] = 30
    c["M4 x 10 button head, pulls"] = 8
    return dict(c)


def m4_stacks():
    """Each through-bolted M4 against what it clamps: its tip must clear the
    nyloc's insert (5.0) by a thread or more."""
    nyloc, wash = 5.0, 0.8
    rows = {"fan, M4 x 40": (40.0, 1.6 + T_PANEL + FAN_T + 1.6 + 2 * wash + nyloc),
            "intake grill, M4 x 16": (16.0, 1.6 + T_PANEL + 2 * wash + nyloc),
            "duct collar, M4 x 16": (16.0, COLLAR["flange_t"] + T_PANEL + 2 * wash + nyloc)}
    return {k: round(L - st, 2) for k, (L, st) in rows.items()}


def fan_clearance():
    """The fans hang inside, under the top panel, through-bolted from inside:
    M4 x 40 heads under the inner grill, nylocs on the outer grill. Their lowest
    point (the heads) against the highest point of the gantry and of the arm
    folded for travel (frame.TIGHT_Q) with J1 at the top of its stroke, over the
    whole X travel, inside each fan's footprint plus 10."""
    gp = os.path.join(_HERE, "..", "gantry")
    if gp not in sys.path:
        sys.path.insert(0, gp)
    import frame as GF
    import arm280 as A
    npz = os.environ.get("MAAG_ARM_NPZ")                 # decimated link meshes, if the CAD isn't here
    if npz and os.path.exists(npz) and not os.path.exists(os.path.join(A.MESH_DIR, "G_base.dae")):
        d = np.load(npz)
        for _, fn, _, _ in A.LINKS:
            A._CACHE[(fn, 0.003)] = (d["V_" + fn].astype(float), d["F_" + fn].astype(int))
    z_in = H + TAPE                                      # the top panel's inner face
    wash, head = 0.8, 2.2                                # M4 washer; ISO 7380 M4 head height
    fan_low = z_in - FAN_T - 1.6                         # under the inner grill
    head_low = fan_low - wash - head
    hi = {"gantry": -1e9, "arm": -1e9}
    z1 = GF.J1_Z_MAX if hasattr(GF, "J1_Z_MAX") else 1718.0
    # everything on the carriage passes under both fans somewhere along X: take its
    # points within a fan's y band (plus 10) at any x; the same for the fixed parts,
    # which over-counts them
    xc = (GF.X_MIN + GF.X_MAX) / 2
    parts = GF.gantry_parts(xc, z1, q=GF.TIGHT_Q, grid=0.003)
    for i, p in enumerate(parts):
        V = p.mesh[0]
        if len(V) == 0:
            continue
        for fx, fy in FANS:
            m = np.abs(V[:, 1] - fy) < FAN_SQ / 2 + 10
            if m.any():
                k = "arm" if i >= len(parts) - 8 else "gantry"          # the arm's 8 links come last
                hi[k] = max(hi[k], float(V[m, 2].max()))
    return {"fan's underside (inner grill)": round(fan_low, 1), "M4 heads": round(head_low, 1),
            "gantry, highest under a fan": "nothing" if hi["gantry"] < -1e8 else round(hi["gantry"], 1),
            "folded arm, J1 at the top": round(hi["arm"], 1),
            "clear, heads to the highest": round(head_low - max(hi.values()), 1)}


def tape_lengths():
    t = 0.0
    for face in ("left", "right", "back", "top"):
        for u0, v0, u1, v1 in tapes(face):
            t += max(u1 - u0, v1 - v0)
    s = 0.0
    for pair in ("bottom", "top"):
        for x0, z0, x1, z1 in strips(pair):
            s += max(x1 - x0, z1 - z0)
    return dict(panel_tape_m=round(t / 1000, 2), door_strip_m=round(s / 1000, 2))


def expansion():
    return {"back, 1397 over 20 C": round(1397 * CTE * 20, 2), "allowance each way": (HOLE - 5.0) / 2}


if __name__ == "__main__":
    print("panels:")
    for k, v in panels().items():
        print(f"  {k:12s} {v[0]:6s} {abs(v[3] - v[1]):7.1f} x {abs(v[4] - v[2]):7.1f}   holes {len(panel_holes(k))}")
    print("nest (48 x 96 in):")
    for sh, rows, spare_a, spare_l in nest():
        print(f"  {sh}: " + " + ".join(f"{n} {a:.1f}x{b:.1f}" for n, a, b in rows),
              f"  spare across {spare_a:.1f}, along {spare_l:.1f}")
    print("edge distance, tightest per panel (margin, (what, u, v, edge, need)):")
    for k, v in edge_report().items():
        print(" ", k, v)
    print("outside footprints, tightest pair per face:", footprint_report())
    print("cutouts into bays, tightest per face:", cutout_report())
    print("gantry to panel inner faces:", gantry_report())
    print("screw stacks:", screw_stack())
    print("door gap budget:", gap_budget())
    for p, s in DOORS:
        print(f"  door {p} {s}: {door_x(s)} x {door_z(p)}  swings to {door_swing(p, s):.1f} deg")
    print("P-clips at", [round(v, 1) for v in CLIP_V], " riser at", RISER)
    print("branch tube change outside the frame (mm):", branch_trim())
    print("anti-tip at x", [round(u, 1) for u in ANTITIP_U])
    print("M4 tips past their nylocs:", m4_stacks())
    print("fans inside, over the gantry and the folded arm:", fan_clearance())
    print("counts:", counts())
    print("tape:", tape_lengths(), " expansion:", expansion())
