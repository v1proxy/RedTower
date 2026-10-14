#!/usr/bin/env python3
"""Rev 2 flat patterns: lap widened onto a support rail, plus T-slot mounting holes.

Changes from Rev 1, all from Vittorio's review on 2026-10-10:

  * lap 30 -> 40 mm, so the whole seam lands on a 40 mm support rail rather than
    bridging between the two long rails
  * three transverse 40-4040 rails per tier (both ends and mid-span) so each tray
    piece bears on FOUR profiles, not two, and the seam cannot sag under wet pots
  * mounting holes, cut into the DXF, on the top-face slot centreline of every
    profile the tray lands on

Holes are SLOTS, 9 mm wide x 18 mm long, not round. 80/20 cut-to-length holds
+/-0.5 mm and that error accumulates over 1317 mm; a 9 mm round hole on an M8
screw leaves 1 mm of play, which is not enough. The slot runs parallel to the
profile it bolts into, which is also the direction the T-nut slides.

Slot centrelines, from the frame geometry:
    front longitudinal   y 0..40     -> y = 20
    shelf rail           y 163..203  -> y = 183
    transverse rails     y 40..163   -> x = rail centre
"""
import math

T   = 1.6002
BD  = 2.438
LIP = 25.0
R   = 2.0
f   = LIP - BD

HOLE_W, HOLE_L = 9.0, 18.0       # M8 clearance, slotted for build tolerance
MAXFLAT = (30.0 * 25.4, 44.0 * 25.4)
MAXBEND = 44.0 * 25.4

# assembly stations (mm from the cabinet's left outer face)
XI0, XI1 = 40.0, 1357.0
LAP = 40.0
RAIL_MID = (660.0, 700.0)
RAIL_L   = (40.0, 80.0)
RAIL_R   = (1317.0, 1357.0)
L_DOWN = RAIL_MID[1] - XI0        # 660 floor, x 40..700
L_UP   = XI1 - RAIL_MID[0]        # 697 floor, x 660..1357
Y_FRONT, Y_SHELF, Y_TRANS = 20.0, 183.0, 100.0


class Dxf:
    def __init__(self):
        self.e = []

    def line(self, p, q, dashed=False):
        self.e.append(("LINE", p, q, dashed))

    def arc(self, c, r, a0, a1):
        self.e.append(("ARC", c, r, a0, a1))

    def circle(self, c, r):
        self.e.append(("CIRCLE", c, r))

    def slot(self, a, b, w):
        th = math.atan2(b[1] - a[1], b[0] - a[0])
        r = w / 2.0
        px, py = -math.sin(th) * r, math.cos(th) * r
        self.line((a[0] + px, a[1] + py), (b[0] + px, b[1] + py))
        self.line((b[0] - px, b[1] - py), (a[0] - px, a[1] - py))
        d = math.degrees(th)
        self.arc(b, r, d - 90.0, d + 90.0)
        self.arc(a, r, d + 90.0, d + 270.0)

    def hole(self, cx, cy, along):
        """Slotted hole centred at (cx, cy), running along 'x' or 'y'."""
        h = (HOLE_L - HOLE_W) / 2.0
        if along == "x":
            self.slot((cx - h, cy), (cx + h, cy), HOLE_W)
        else:
            self.slot((cx, cy - h), (cx, cy + h), HOLE_W)

    def dumps(self):
        o = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4",
             "9", "$MEASUREMENT", "70", "1", "0", "ENDSEC",
             "0", "SECTION", "2", "TABLES",
             "0", "TABLE", "2", "LTYPE", "70", "2",
             "0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line",
             "72", "65", "73", "0", "40", "0.0",
             "0", "LTYPE", "2", "DASHED", "70", "0", "3", "Dashed",
             "72", "65", "73", "2", "40", "9.0", "49", "6.0", "49", "-3.0",
             "0", "ENDTAB",
             "0", "TABLE", "2", "LAYER", "70", "1",
             "0", "LAYER", "2", "0", "70", "0", "62", "7", "6", "CONTINUOUS",
             "0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        for ent in self.e:
            if ent[0] == "LINE":
                _, p, q, dashed = ent
                o += ["0", "LINE", "8", "0", "6", "DASHED" if dashed else "CONTINUOUS",
                      "10", f"{p[0]:.4f}", "20", f"{p[1]:.4f}", "30", "0.0",
                      "11", f"{q[0]:.4f}", "21", f"{q[1]:.4f}", "31", "0.0"]
            elif ent[0] == "ARC":
                _, c, r, a0, a1 = ent
                o += ["0", "ARC", "8", "0", "6", "CONTINUOUS",
                      "10", f"{c[0]:.4f}", "20", f"{c[1]:.4f}", "30", "0.0",
                      "40", f"{r:.4f}", "50", f"{a0:.4f}", "51", f"{a1:.4f}"]
            else:
                _, c, r = ent
                o += ["0", "CIRCLE", "8", "0", "6", "CONTINUOUS",
                      "10", f"{c[0]:.4f}", "20", f"{c[1]:.4f}", "30", "0.0",
                      "40", f"{r:.4f}"]
        o += ["0", "ENDSEC", "0", "EOF"]
        return "\n".join(o) + "\n"


def piece_down(Lfloor, Wfloor, holes=(), drain=None):
    d = Dxf()
    d.line((0.0, -f), (Lfloor, -f))
    d.line((Lfloor, -f), (Lfloor, Wfloor + f))
    d.line((Lfloor, Wfloor + f), (0.0, Wfloor + f))
    d.line((0.0, Wfloor + f), (0.0, Wfloor - R))
    d.arc((R, Wfloor - R), R, 90.0, 180.0)
    d.line((R, Wfloor), (-f, Wfloor))
    d.line((-f, Wfloor), (-f, 0.0))
    d.line((-f, 0.0), (R, 0.0))
    d.arc((R, R), R, 180.0, 270.0)
    d.line((0.0, R), (0.0, -f))
    d.line((R, 0.0), (Lfloor, 0.0), dashed=True)
    d.line((R, Wfloor), (Lfloor, Wfloor), dashed=True)
    d.line((0.0, R), (0.0, Wfloor - R), dashed=True)
    if drain:
        d.circle(drain, 3.0)
    for cx, cy, along in holes:
        d.hole(cx, cy, along)
    return d, (-f, Lfloor, -f, Wfloor + f), [Lfloor - R, Lfloor - R, Wfloor - 2 * R]


def piece_up(Lfloor, Wfloor, Ltongue, inset, holes=(), drain=None):
    d = Dxf()
    yl, yu = inset, Wfloor - inset
    d.line((0.0, yl), (Ltongue + R, yl))
    d.arc((Ltongue + R, yl + R), R, 180.0, 270.0)
    d.line((Ltongue, yl + R), (Ltongue, -f))
    d.line((Ltongue, -f), (Lfloor, -f))
    d.line((Lfloor, -f), (Lfloor, R))
    d.arc((Lfloor - R, R), R, 270.0, 360.0)
    d.line((Lfloor - R, 0.0), (Lfloor + f, 0.0))
    d.line((Lfloor + f, 0.0), (Lfloor + f, Wfloor))
    d.line((Lfloor + f, Wfloor), (Lfloor - R, Wfloor))
    d.arc((Lfloor - R, Wfloor - R), R, 0.0, 90.0)
    d.line((Lfloor, Wfloor - R), (Lfloor, Wfloor + f))
    d.line((Lfloor, Wfloor + f), (Ltongue, Wfloor + f))
    d.line((Ltongue, Wfloor + f), (Ltongue, yu - R))
    d.arc((Ltongue + R, yu - R), R, 90.0, 180.0)
    d.line((Ltongue + R, yu), (0.0, yu))
    d.line((0.0, yu), (0.0, yl))
    d.line((Ltongue, 0.0), (Lfloor - R, 0.0), dashed=True)
    d.line((Ltongue, Wfloor), (Lfloor - R, Wfloor), dashed=True)
    d.line((Lfloor, R), (Lfloor, Wfloor - R), dashed=True)
    if drain:
        d.circle(drain, 3.0)
    for cx, cy, along in holes:
        d.hole(cx, cy, along)
    return d, (0.0, Lfloor + f, -f, Wfloor + f), [Lfloor - R - Ltongue,
                                                  Lfloor - R - Ltongue, Wfloor - 2 * R]


# ---- hole schedules, in each piece's own flat-pattern coordinates ----------
# DOWN floor spans assembly x 40..700, so local x = assembly x - 40
DOWN_X = [100.0, 370.0, 640.0]
down_holes = [(x - XI0, Y_FRONT, "x") for x in DOWN_X] + \
             [(x - XI0, Y_SHELF, "x") for x in DOWN_X] + \
             [(sum(RAIL_L) / 2 - XI0, Y_TRANS, "y"),
              (sum(RAIL_MID) / 2 - XI0, Y_TRANS, "y")]
# UP floor spans assembly x 660..1357, so local x = assembly x - 660
UP_X = [760.0, 1020.0, 1290.0]
up_holes = [(x - RAIL_MID[0], Y_FRONT, "x") for x in UP_X] + \
           [(x - RAIL_MID[0], Y_SHELF, "x") for x in UP_X] + \
           [(sum(RAIL_MID) / 2 - RAIL_MID[0], Y_TRANS, "y"),
            (sum(RAIL_R) / 2 - RAIL_MID[0], Y_TRANS, "y")]

PARTS = []
d, bb, bends = piece_down(L_DOWN, 203.0, down_holes, drain=(45.0, 101.5))
PARTS.append(("tray_DOWN", d, bb, bends, 3))
d, bb, bends = piece_up(L_UP, 203.0, LAP, 3.5, up_holes)
PARTS.append(("tray_UP", d, bb, bends, 3))
d, bb, bends = piece_down(L_DOWN, 377.0, (), drain=(45.0, 188.5))
PARTS.append(("basepan_DOWN", d, bb, bends, 1))
d, bb, bends = piece_up(L_UP, 377.0, LAP, 3.5)
PARTS.append(("basepan_UP", d, bb, bends, 1))

print(f"{'part':16} {'flat W x L (mm)':>20} {'flat (in)':>16} {'fits':>6} {'bend':>9} holes")
print("-" * 86)
ok = True
for name, d, (x0, x1, y0, y1), bends, qty in PARTS:
    w, l = (y1 - y0), (x1 - x0)
    short, long_ = min(w, l), max(w, l)
    fits = short <= MAXFLAT[0] + 1e-6 and long_ <= MAXFLAT[1] + 1e-6
    bend_ok = max(bends) <= MAXBEND
    nh = sum(1 for e in d.e if e[0] == "ARC") - 2        # 2 corner reliefs, rest are slot caps
    ok &= fits and bend_ok
    open(f"{name}.dxf", "w").write(d.dumps())
    print(f"{name:16} {w:8.2f} x {l:8.2f} {short/25.4:6.2f} x {long_/25.4:6.2f} "
          f"{'yes' if fits else 'NO':>6} {max(bends)/25.4:6.2f}in {'ok' if bend_ok else 'OVER'}"
          f"  {nh // 2}")

span = L_DOWN + L_UP - LAP
print(f"\nlength check: {L_DOWN} + {L_UP} - {LAP} = {span} mm   (clear span {XI1 - XI0})")
print(f"hole clearances: front row to y=0 bend {Y_FRONT - HOLE_W/2:.1f} mm, "
      f"shelf row to y=203 bend {203 - Y_SHELF - HOLE_W/2:.1f} mm "
      f"(SendCutSend wants >= half the die width, about 6.4 mm)")
assert abs(span - (XI1 - XI0)) < 1e-9 and ok
assert HOLE_W > T and Y_FRONT - HOLE_W / 2 >= 6.4 and 203 - Y_SHELF - HOLE_W / 2 >= 6.4
print("all checks pass")
