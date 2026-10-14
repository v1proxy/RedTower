#!/usr/bin/env python3
"""Rev 3 tray flat patterns: trays reach over the existing side members.

Vittorio, 2026-10-10: "There is no reason to double the profiles: just use the external
ones and extend the corner cut in the trays."

He is right. The two end rails per tier sat directly beside the side depth members and
bought nothing. Gone. Instead the tray now runs the full 1397 mm frame width and lands
on the side members, with the front corner cut away to clear the upright.

The corner cut is a 45 degree chamfer, not a square notch, and that is the whole reason
this is buildable. A square notch puts two perpendicular flanges into a 270 degree
re-entrant corner; their flange strips overlap in the flat pattern and have to be
mitred, which means a knife-edge slit and five bends. One chamfer face replaces both,
every corner stays convex so no flange overlaps another, and the piece still has four
bends.

    chamfer line   x + y = 84 at the left end
    upright corner (40, 40)
    clearance      |40 + 40 - 84| / sqrt(2) = 2.83 mm

Pot zone is untouched: plants sit on the 1317 pitch, so the nearest pot corner is at
(56.2, 44.5), which is 11.8 mm clear of the chamfer.

Only the two tray parts change. The base pan sits on the floor between the bottom
members at x 40..1357 and never meets an upright, so Rev 2 stands and it stays in the
cart as quoted.
"""
import math

T, BD, LIP, R = 1.6002, 2.438, 25.0, 2.0
f = LIP - BD
HOLE_W, HOLE_L = 9.0, 18.0
MAXFLAT, MAXBEND = (30.0 * 25.4, 44.0 * 25.4), 44.0 * 25.4

W = 203.0                      # tray depth
CHAM = 84.0                    # chamfer intercept
XF0, XF1 = 0.0, 1397.0         # tray now spans the whole frame width
RAIL_MID = (660.0, 700.0)      # the one remaining new rail, under the lap
LAP = 40.0
L_DOWN = RAIL_MID[1] - XF0     # 700
L_UP = XF1 - RAIL_MID[0]       # 737
SQ = math.sqrt(2.0)


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
             "0", "ENDTAB", "0", "TABLE", "2", "LAYER", "70", "1",
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


def unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


def corner(P, a, b, r=R):
    """Bend relief where two flange edges leave P along unit directions a and b.

    Both cut edges overrun the bend intersection into the floor and are joined by an
    arc of radius r, so the root of the notch is radiused instead of knife sharp. This
    is the same relief already accepted on the Rev 1 and Rev 2 corners, generalised to
    corners that are not 90 degrees.
    """
    v = unit((a[0] + b[0], a[1] + b[1]))          # bisector of the void wedge
    half = math.acos(max(-1.0, min(1.0, a[0] * v[0] + a[1] * v[1])))
    t = r / math.sin(half)
    C = (P[0] - t * v[0], P[1] - t * v[1])
    da = (C[0] - P[0]) * a[0] + (C[1] - P[1]) * a[1]
    db = (C[0] - P[0]) * b[0] + (C[1] - P[1]) * b[1]
    ta = (P[0] + da * a[0], P[1] + da * a[1])
    tb = (P[0] + db * b[0], P[1] + db * b[1])
    aa = math.degrees(math.atan2(ta[1] - C[1], ta[0] - C[0])) % 360
    ab = math.degrees(math.atan2(tb[1] - C[1], tb[0] - C[0])) % 360
    lo, hi = (aa, ab) if (ab - aa) % 360 <= 180 else (ab, aa)
    return ta, tb, (C, r, lo, hi)


def tray_down(L, holes, drain):
    """Left-hand piece: chamfer at x+y = CHAM, open lap end at x = L."""
    d = Dxf()
    A, B = (CHAM, 0.0), (0.0, CHAM)
    n = (-1 / SQ, -1 / SQ)                                   # chamfer outward normal
    Ap = (A[0] + f * n[0], A[1] + f * n[1])
    Bp = (B[0] + f * n[0], B[1] + f * n[1])
    aA, aB = corner(A, (0.0, -1.0), n), corner(B, (-1.0, 0.0), n)
    tA_front, tA_cham, arcA = aA
    tB_end, tB_cham, arcB = aB

    d.line((L, -f), (L, W + f))                              # open lap end
    d.line((L, W + f), (0.0, W + f))                         # back flange, outer edge
    d.line((0.0, W + f), (0.0, W - R))                       # back flange, left edge
    d.arc((R, W - R), R, 90.0, 180.0)                        # relief at (0, W)
    d.line((R, W), (-f, W))                                  # end flange, top edge
    d.line((-f, W), (-f, CHAM))                              # end flange, outer edge
    d.line((-f, CHAM), tB_end)                               # end flange, bottom edge
    d.arc(*arcB[0:2], arcB[2], arcB[3])                      # relief at B
    d.line(tB_cham, Bp)                                      # chamfer flange, B end
    d.line(Bp, Ap)                                           # chamfer flange, outer edge
    d.line(Ap, tA_cham)                                      # chamfer flange, A end
    d.arc(*arcA[0:2], arcA[2], arcA[3])                      # relief at A
    d.line(tA_front, (CHAM, -f))                             # front flange, left edge
    d.line((CHAM, -f), (L, -f))                              # front flange, outer edge

    d.line((CHAM + 5, 0.0), (L, 0.0), dashed=True)           # front bend
    d.line((CHAM - 3.5, 3.5), (3.5, CHAM - 3.5), dashed=True)  # chamfer bend
    d.line((0.0, CHAM + 5), (0.0, W - R), dashed=True)       # end bend
    d.line((R, W), (L, W), dashed=True)                      # back bend
    d.circle(drain, 3.0)
    for cx, cy, al in holes:
        d.hole(cx, cy, al)
    bends = [L - CHAM - 5, CHAM * SQ, W - CHAM - 5, L - R]
    return d, (-f, L, -f, W + f), bends


def tray_up(L, tongue, inset, holes):
    """Right-hand piece: flat tongue at x = 0, chamfer at the far end."""
    d = Dxf()
    A, B = (L - CHAM, 0.0), (L, CHAM)
    n = (1 / SQ, -1 / SQ)
    Ap = (A[0] + f * n[0], A[1] + f * n[1])
    Bp = (B[0] + f * n[0], B[1] + f * n[1])
    tA_front, tA_cham, arcA = corner(A, (0.0, -1.0), n)
    tB_end, tB_cham, arcB = corner(B, (1.0, 0.0), n)
    yl, yu = inset, W - inset

    d.line((0.0, yl), (tongue + R, yl))                      # tongue, lower edge
    d.arc((tongue + R, yl + R), R, 180.0, 270.0)             # relief at the step
    d.line((tongue, yl + R), (tongue, -f))                   # step down to the lip
    d.line((tongue, -f), (CHAM and A[0] or 0, -f))           # front flange, outer edge
    d.line((A[0], -f), tA_front)                             # front flange, right edge
    d.arc(*arcA[0:2], arcA[2], arcA[3])                      # relief at A
    d.line(tA_cham, Ap)                                      # chamfer flange, A end
    d.line(Ap, Bp)                                           # chamfer flange, outer edge
    d.line(Bp, tB_cham)                                      # chamfer flange, B end
    d.arc(*arcB[0:2], arcB[2], arcB[3])                      # relief at B
    d.line(tB_end, (L + f, CHAM))                            # end flange, bottom edge
    d.line((L + f, CHAM), (L + f, W))                        # end flange, outer edge
    d.line((L + f, W), (L - R, W))                           # end flange, top edge
    d.arc((L - R, W - R), R, 0.0, 90.0)                      # relief at (L, W)
    d.line((L, W - R), (L, W + f))                           # back flange, right edge
    d.line((L, W + f), (tongue, W + f))                      # back flange, outer edge
    d.line((tongue, W + f), (tongue, yu - R))                # step up to the tongue
    d.arc((tongue + R, yu - R), R, 90.0, 180.0)              # relief at the step
    d.line((tongue + R, yu), (0.0, yu))                      # tongue, upper edge
    d.line((0.0, yu), (0.0, yl))                             # tongue end

    d.line((tongue, 0.0), (A[0] - 5, 0.0), dashed=True)
    d.line((A[0] + 3.5, 3.5), (L - 3.5, CHAM - 3.5), dashed=True)
    d.line((L, CHAM + 5), (L, W - R), dashed=True)
    d.line((tongue, W), (L - R, W), dashed=True)
    for cx, cy, al in holes:
        d.hole(cx, cy, al)
    bends = [A[0] - 5 - tongue, CHAM * SQ, W - CHAM - 5, L - R - tongue]
    return d, (0.0, L + f, -f, W + f), bends


# ---- hole schedules -------------------------------------------------------
Y_FRONT, Y_SHELF, Y_SIDE, Y_MID = 20.0, 183.0, 130.0, 100.0
down_holes = [(x, Y_FRONT, "x") for x in (150.0, 400.0, 650.0)] + \
             [(x, Y_SHELF, "x") for x in (150.0, 400.0, 650.0)] + \
             [(20.0, Y_SIDE, "y"),                                  # left side member
              (sum(RAIL_MID) / 2 - XF0, Y_MID, "y")]                # mid rail
up_holes = [(x - RAIL_MID[0], Y_FRONT, "x") for x in (800.0, 1050.0, 1260.0)] + \
           [(x - RAIL_MID[0], Y_SHELF, "x") for x in (800.0, 1050.0, 1260.0)] + \
           [(1377.0 - RAIL_MID[0], Y_SIDE, "y"),                    # right side member
            (sum(RAIL_MID) / 2 - RAIL_MID[0], Y_MID, "y")]

PARTS = [("tray_DOWN",) + tray_down(L_DOWN, down_holes, (45.0, 150.0)) + (3,),
         ("tray_UP",) + tray_up(L_UP, LAP, 3.5, up_holes) + (3,)]

print(f"{'part':12} {'flat W x L (mm)':>20} {'flat (in)':>16} {'fits':>5} {'max bend':>12} bends")
print("-" * 82)
ok = True
for name, d, (x0, x1, y0, y1), bends, qty in PARTS:
    w, l = y1 - y0, x1 - x0
    short, long_ = min(w, l), max(w, l)
    fits = short <= MAXFLAT[0] + 1e-6 and long_ <= MAXFLAT[1] + 1e-6
    bok = max(bends) <= MAXBEND
    ok &= fits and bok
    open(f"{name}.dxf", "w").write(d.dumps())
    print(f"{name:12} {w:8.2f} x {l:8.2f} {short/25.4:6.2f} x {long_/25.4:6.2f} "
          f"{'yes' if fits else 'NO':>5} {max(bends)/25.4:8.2f} in  {len(bends)}")

span = L_DOWN + L_UP - LAP
clear = abs(40 + 40 - CHAM) / SQ
pot = (56.2 + 44.5 - CHAM) / SQ
print(f"\nspan {L_DOWN} + {L_UP} - {LAP} = {span} mm   (frame width {XF1 - XF0})")
print(f"chamfer clears the upright corner by {clear:.2f} mm, nearest pot corner by {pot:.2f} mm")
assert abs(span - (XF1 - XF0)) < 1e-9 and ok and clear > 2.0 and pot > 8.0
print("all checks pass")
