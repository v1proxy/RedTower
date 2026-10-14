#!/usr/bin/env python3
"""Rev 3: trays AND base pan land on the existing external profiles.

Two corrections from Vittorio, 2026-10-10:

  1. "No reason to double the profiles: just use the external ones and extend the
     corner cut in the trays."  The six end rails sat beside the side depth members
     and bought nothing. Gone. Trays now run the full 1397 mm frame width and bear on
     the side members, with the front corner cut away to clear the upright.

  2. "Why basepan has no holes."  Because in Rev 2 I floated it on the floor instead
     of mounting it, which was my call and the wrong one: 1317 x 377 only touches the
     side members at its two ends, so it would have spanned 1317 mm unsupported. The
     pan is now 1397 x 457, sits on the bottom front and back longitudinals like every
     other pan, has a chamfer at all four corners, and is bolted down the same way.

The corner cut is a 45 degree chamfer rather than a square notch. A square notch puts
two perpendicular lips into a 270 degree re-entrant corner; their flange strips overlap
in the flat pattern and need a mitred slit. One chamfer face replaces both, every
corner stays convex, and nothing overlaps.

    chamfer line     x + y = 84 at a front-left corner
    upright corner   (40, 40)
    clearance        |40 + 40 - 84| / sqrt(2) = 2.83 mm
"""
import math, sys
sys.path.insert(0, "/home/claude/greenhouse/sendcutsend")
from unfold import unfold, MAXFLAT, MAXBEND, F, R

C = 84.0                 # chamfer intercept
SQ = math.sqrt(2.0)
WT, WP = 203.0, 457.0    # tray depth, pan depth (full frame depth)
XF1 = 1397.0
MID = (660.0, 700.0)
LAP, TON, INS = 40.0, 40.0, 3.5
LD, LU = MID[1], XF1 - MID[0]        # 700, 737

# --- floor polygons, counter-clockwise, in each piece's own coordinates ----
tray_down_poly = [(C, 0), (LD, 0), (LD, WT), (0, WT), (0, C)]
tray_down_fl   = [True, False, True, True, True]

tray_up_poly = [(0, INS), (TON, INS), (TON, 0), (LU - C, 0), (LU, C),
                (LU, WT), (TON, WT), (TON, WT - INS), (0, WT - INS)]
tray_up_fl   = [False, False, True, True, True, True, False, False, False]

pan_down_poly = [(C, 0), (LD, 0), (LD, WP), (C, WP), (0, WP - C), (0, C)]
pan_down_fl   = [True, False, True, True, True, True]

pan_up_poly = [(0, INS), (TON, INS), (TON, 0), (LU - C, 0), (LU, C),
               (LU, WP - C), (LU - C, WP), (TON, WP), (TON, WP - INS), (0, WP - INS)]
pan_up_fl   = [False, False, True, True, True, True, True, False, False, False]

# --- mounting holes, on the top-face slot centreline of each profile ------
TRAY_F, TRAY_B, TRAY_S, MIDY = 20.0, WT - 20.0, 130.0, 100.0
PAN_F, PAN_B, PAN_S = 20.0, WP - 20.0, WP / 2.0

tray_down_h = [(x, TRAY_F, "x") for x in (150, 400, 650)] + \
              [(x, TRAY_B, "x") for x in (150, 400, 650)] + \
              [(20.0, TRAY_S, "y"), (sum(MID) / 2, MIDY, "y")]
tray_up_h = [(x - MID[0], TRAY_F, "x") for x in (800, 1050, 1260)] + \
            [(x - MID[0], TRAY_B, "x") for x in (800, 1050, 1260)] + \
            [(1377.0 - MID[0], TRAY_S, "y"), (sum(MID) / 2 - MID[0], MIDY, "y")]
pan_down_h = [(x, PAN_F, "x") for x in (150, 400, 650)] + \
             [(x, PAN_B, "x") for x in (150, 400, 650)] + \
             [(20.0, PAN_S, "y"), (sum(MID) / 2, PAN_S, "y")]
pan_up_h = [(x - MID[0], PAN_F, "x") for x in (800, 1050, 1260)] + \
           [(x - MID[0], PAN_B, "x") for x in (800, 1050, 1260)] + \
           [(1377.0 - MID[0], PAN_S, "y"), (sum(MID) / 2 - MID[0], PAN_S, "y")]

SPEC = [
    ("tray_DOWN", tray_down_poly, tray_down_fl, tray_down_h, (45.0, 150.0), 3),
    ("tray_UP", tray_up_poly, tray_up_fl, tray_up_h, None, 3),
    ("basepan_DOWN", pan_down_poly, pan_down_fl, pan_down_h, (60.0, PAN_S), 1),
    ("basepan_UP", pan_up_poly, pan_up_fl, pan_up_h, None, 1),
]

print(f"{'part':14} {'flat W x L (mm)':>20} {'flat (in)':>16} {'fits':>5} "
      f"{'max bend':>11} {'bends':>6} holes")
print("-" * 92)
ok = True
for name, poly, fl, holes, drain, qty in SPEC:
    g, (x0, x1, y0, y1), bends = unfold(poly, fl, holes, drain)
    w, l = y1 - y0, x1 - x0
    short, long_ = min(w, l), max(w, l)
    fits = short <= MAXFLAT[0] + 1e-6 and long_ <= MAXFLAT[1] + 1e-6
    bok = max(bends) <= MAXBEND
    ok &= fits and bok
    open(f"{name}.dxf", "w").write(g.dumps())
    print(f"{name:14} {w:8.2f} x {l:8.2f} {short/25.4:6.2f} x {long_/25.4:6.2f} "
          f"{'yes' if fits else 'NO':>5} {max(bends)/25.4:8.2f} in {len(bends):>6} "
          f"{len(holes)}")

span = LD + LU - LAP
clear = abs(40 + 40 - C) / SQ
pot = (56.2 + 44.5 - C) / SQ
print(f"\nspan {LD} + {LU} - {LAP} = {span} mm   (frame width {XF1})")
print(f"chamfer clears the upright corner by {clear:.2f} mm, nearest pot corner by {pot:.2f} mm")
print("rails: 3 x 123 mm under the tier laps, 1 x 377 mm under the pan lap  (was 9)")
assert abs(span - XF1) < 1e-9 and ok and clear > 2.0 and pot > 8.0
print("all checks pass")
