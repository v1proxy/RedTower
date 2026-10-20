#!/usr/bin/env python3
"""Flat patterns for the Maag drip trays, sized to SendCutSend's real limits.

5052 aluminium 0.063 in, BENT, caps out at a 30 x 44 in flat blank and a 44 in bend
length. The one-piece 1317 mm tray in BOM Rev E is 51.85 in long, so it is simply not
makeable there. Each tray is therefore split into two pieces that lap shingle-fashion,
uphill piece on top, so runoff never has to climb the seam.

Bend maths, derived from SendCutSend's own published minimum flange figures for this
material (0.255 in flat / 0.303 in formed, effective bend radius 0.035 in at 90 deg):

    outside setback  = R + T            = 0.098 in
    bend allowance   = 0.303 - 0.255 ... -> BA = 0.100 in = 2.540 mm
    bend deduction   = 2(R + T) - BA    = 0.096 in = 2.438 mm
    implied K-factor = 0.455

So a flange of outside height H contributes (H - BD/2) to the flat length, and a
blank with two opposed flanges unfolds to (W + 2H - 2*BD).
"""
import os
import math

T   = 1.6002          # 0.063 in
BD  = 2.438           # bend deduction, 90 deg
LIP = 25.0            # outside lip height
R   = 2.0             # bend-relief root radius
f   = LIP - BD        # flat flange allowance = 22.562

MAXFLAT = (30.0 * 25.4, 44.0 * 25.4)   # 762 x 1117.6 mm
MAXBEND = 44.0 * 25.4                  # 1117.6 mm


# ------------------------------------------------------------------ DXF writer
class Dxf:
    def __init__(self):
        self.e = []

    def line(self, p, q, dashed=False):
        self.e.append(("LINE", p, q, dashed))

    def arc(self, c, r, a0, a1):
        self.e.append(("ARC", c, r, a0, a1))

    def circle(self, c, r):
        self.e.append(("CIRCLE", c, r))

    def dumps(self):
        o = ["0", "SECTION", "2", "HEADER",
             "9", "$INSUNITS", "70", "4",
             "9", "$MEASUREMENT", "70", "1",
             "0", "ENDSEC",
             "0", "SECTION", "2", "TABLES",
             "0", "TABLE", "2", "LTYPE", "70", "2",
             "0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line",
             "72", "65", "73", "0", "40", "0.0",
             "0", "LTYPE", "2", "DASHED", "70", "0", "3", "Dashed",
             "72", "65", "73", "2", "40", "9.0", "49", "6.0", "49", "-3.0",
             "0", "ENDTAB",
             "0", "TABLE", "2", "LAYER", "70", "1",
             "0", "LAYER", "2", "0", "70", "0", "62", "7", "6", "CONTINUOUS",
             "0", "ENDTAB", "0", "ENDSEC",
             "0", "SECTION", "2", "ENTITIES"]
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


# ------------------------------------------------------------------ geometry
def piece_down(Lfloor, Wfloor, drain_x=45.0, drain_d=6.0):
    """Downhill piece: end lip at x=0, side lips full length, open lap end at x=Lfloor.

    Outline runs counter-clockwise. Both cut edges at each corner of the end lip
    overrun their bend line by R and are joined by a fillet: that is the bend relief.
    """
    d = Dxf()
    # lower side lip, bottom edge
    d.line((0.0, -f), (Lfloor, -f))
    # open lap end
    d.line((Lfloor, -f), (Lfloor, Wfloor + f))
    # upper side lip, top edge
    d.line((Lfloor, Wfloor + f), (0.0, Wfloor + f))
    # left edge of upper side lip, running R past the y=Wfloor bend line
    d.line((0.0, Wfloor + f), (0.0, Wfloor - R))
    d.arc((R, Wfloor - R), R, 90.0, 180.0)
    # end lip
    d.line((R, Wfloor), (-f, Wfloor))
    d.line((-f, Wfloor), (-f, 0.0))
    d.line((-f, 0.0), (R, 0.0))
    d.arc((R, R), R, 180.0, 270.0)
    # left edge of lower side lip
    d.line((0.0, R), (0.0, -f))
    # bends
    d.line((R, 0.0), (Lfloor, 0.0), dashed=True)
    d.line((R, Wfloor), (Lfloor, Wfloor), dashed=True)
    d.line((0.0, R), (0.0, Wfloor - R), dashed=True)
    # drain pilot
    d.circle((drain_x, Wfloor / 2.0), drain_d / 2.0)
    return d, (-f, Lfloor, -f, Wfloor + f), [Lfloor - R, Lfloor - R, Wfloor - 2 * R]


def piece_up(Lfloor, Wfloor, Ltongue, inset):
    """Uphill piece: end lip at x=Lfloor, side lips stop at x=Ltongue, flat tongue
    from x=0 to Ltongue that drops inside the downhill piece's channel.

    The tongue is inset from the floor edge on both sides, which both clears the
    other piece's lips and gives the side-lip bends their relief for free.
    """
    d = Dxf()
    yl, yu = inset, Wfloor - inset
    # tongue, lower edge, overrunning the step corner by R
    d.line((0.0, yl), (Ltongue + R, yl))
    d.arc((Ltongue + R, yl + R), R, 180.0, 270.0)
    # step down to the lower side lip
    d.line((Ltongue, yl + R), (Ltongue, -f))
    d.line((Ltongue, -f), (Lfloor, -f))
    # right edge of lower side lip, R past the y=0 bend line
    d.line((Lfloor, -f), (Lfloor, R))
    d.arc((Lfloor - R, R), R, 270.0, 360.0)
    # end lip
    d.line((Lfloor - R, 0.0), (Lfloor + f, 0.0))
    d.line((Lfloor + f, 0.0), (Lfloor + f, Wfloor))
    d.line((Lfloor + f, Wfloor), (Lfloor - R, Wfloor))
    d.arc((Lfloor - R, Wfloor - R), R, 0.0, 90.0)
    # right edge of upper side lip
    d.line((Lfloor, Wfloor - R), (Lfloor, Wfloor + f))
    d.line((Lfloor, Wfloor + f), (Ltongue, Wfloor + f))
    # step up to the tongue
    d.line((Ltongue, Wfloor + f), (Ltongue, yu - R))
    d.arc((Ltongue + R, yu - R), R, 90.0, 180.0)
    d.line((Ltongue + R, yu), (0.0, yu))
    # tongue end
    d.line((0.0, yu), (0.0, yl))
    # bends
    d.line((Ltongue, 0.0), (Lfloor - R, 0.0), dashed=True)
    d.line((Ltongue, Wfloor), (Lfloor - R, Wfloor), dashed=True)
    d.line((Lfloor, R), (Lfloor, Wfloor - R), dashed=True)
    return d, (0.0, Lfloor + f, -f, Wfloor + f), [Lfloor - R - Ltongue,
                                                  Lfloor - R - Ltongue, Wfloor - 2 * R]


# ------------------------------------------------------------------ build
TOTAL  = 1317.0      # tray length between uprights
LAP    = 30.0        # shingle overlap
L_DOWN = 690.0
L_UP   = TOTAL - L_DOWN + LAP          # 657.0

PARTS = []
for name, W, inset, qty in [("tray", 203.0, 3.5, 3), ("basepan", 377.0, 3.5, 1)]:
    d, bb, bends = piece_down(L_DOWN, W)
    PARTS.append((f"{name}_DOWN_x{qty}", d, bb, bends, qty))
    d, bb, bends = piece_up(L_UP, W, LAP, inset)
    PARTS.append((f"{name}_UP_x{qty}", d, bb, bends, qty))

print(f"{'part':22} {'flat W x L (mm)':>22} {'flat (in)':>16} {'fits 30x44':>11}  longest bend")
print("-" * 92)
ok = True
for name, d, (x0, x1, y0, y1), bends, qty in PARTS:
    w, l = (y1 - y0), (x1 - x0)
    short, long_ = min(w, l), max(w, l)
    fits = short <= MAXFLAT[0] + 1e-6 and long_ <= MAXFLAT[1] + 1e-6
    bend_ok = max(bends) <= MAXBEND
    ok &= fits and bend_ok
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name.split('_x')[0]}.dxf"), "w").write(d.dumps())
    print(f"{name:22} {w:9.2f} x {l:9.2f} {short/25.4:6.2f} x {long_/25.4:6.2f} "
          f"{'yes' if fits else 'NO':>11}  {max(bends):7.1f} mm = {max(bends)/25.4:5.2f} in "
          f"{'ok' if bend_ok else 'OVER'}")

print(f"\nall parts within SendCutSend 5052 0.063 in bent limits: {ok}")
print(f"length check: {L_DOWN} + {L_UP} - {LAP} = {L_DOWN + L_UP - LAP} mm (target {TOTAL})")
assert abs(L_DOWN + L_UP - LAP - TOTAL) < 1e-9
assert ok
