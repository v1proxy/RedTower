#!/usr/bin/env python3
"""Rev 4: L cut, hugging the upright.

Vittorio, 2026-10-10: "don't do 45 degrees, do a L cut ... so it perfectly hug around
the corner."

So the corner cut is a square notch 41 x 41, which is the 40 mm upright plus 1 mm all
round. The tray wraps the post on two faces instead of cutting the corner off, which
keeps 1592 mm2 of floor per corner that the 45 degree version threw away and puts the
upstand right against the post.

The cost is the one thing the chamfer was avoiding: a 90 degree inside corner is
re-entrant, so the two notch lips overlap in the flat pattern. They are mitred apart at
45 degrees with a 2.5 mm gap, which is wider than the 1.6 mm material so the laser has
room, and the joint gets the same silicone bead as every other corner. Five bends per
piece instead of four.
"""
import os
import math, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unfold import unfold, MAXFLAT, MAXBEND, MITRE_GAP

N = 41.0                 # 40 mm upright + 1 mm clearance
WT, WP = 203.0, 559.0
XF1 = 1397.0
MID = (660.0, 700.0)
LAP, TON, INS = 40.0, 40.0, 3.5
LD, LU = MID[1], XF1 - MID[0]        # 700, 737

tray_down = ([(N, 0), (LD, 0), (LD, WT), (0, WT), (0, N), (N, N)],
             [True, False, True, True, True, True])
tray_up = ([(0, INS), (TON, INS), (TON, 0), (LU - N, 0), (LU - N, N), (LU, N),
            (LU, WT), (TON, WT), (TON, WT - INS), (0, WT - INS)],
           [False, False, True, True, True, True, True, False, False, False])
pan_down = ([(N, 0), (LD, 0), (LD, WP), (N, WP), (N, WP - N), (0, WP - N), (0, N), (N, N)],
            [True, False, True, True, True, True, True, True])
pan_up = ([(0, INS), (TON, INS), (TON, 0), (LU - N, 0), (LU - N, N), (LU, N),
           (LU, WP - N), (LU - N, WP - N), (LU - N, WP), (TON, WP),
           (TON, WP - INS), (0, WP - INS)],
          [False, False, True, True, True, True, True, True, True, False, False, False])

TF, TB, TS, MY = 20.0, WT - 20.0, 130.0, 100.0
PF, PB, PS = 20.0, WP - 20.0, WP / 2.0
tray_down_h = [(x, TF, "x") for x in (150, 400, 650)] + \
              [(x, TB, "x") for x in (150, 400, 650)] + \
              [(20.0, TS, "y"), (sum(MID) / 2, MY, "y")]
tray_up_h = [(x - MID[0], TF, "x") for x in (800, 1050, 1260)] + \
            [(x - MID[0], TB, "x") for x in (800, 1050, 1260)] + \
            [(1377.0 - MID[0], TS, "y"), (sum(MID) / 2 - MID[0], MY, "y")]
pan_down_h = [(x, PF, "x") for x in (150, 400, 650)] + \
             [(x, PB, "x") for x in (150, 400, 650)] + \
             [(20.0, PS, "y"), (sum(MID) / 2, PS, "y")]
pan_up_h = [(x - MID[0], PF, "x") for x in (800, 1050, 1260)] + \
           [(x - MID[0], PB, "x") for x in (800, 1050, 1260)] + \
           [(1377.0 - MID[0], PS, "y"), (sum(MID) / 2 - MID[0], PS, "y")]

SPEC = [("tray_DOWN", tray_down, tray_down_h, (66.0, 95.0), 3),    # drain: frame/cabinet.py DRAIN
        ("tray_UP", tray_up, tray_up_h, None, 3),
        ("basepan_DOWN", pan_down, pan_down_h, None, 1),    # no drain: see frame/cabinet.py BUCKET
        ("basepan_UP", pan_up, pan_up_h, None, 1)]

print(f"{'part':14} {'flat W x L (mm)':>20} {'flat (in)':>16} {'fits':>5} "
      f"{'max bend':>11} {'bends':>6} holes")
print("-" * 92)
ok = True
for name, (poly, fl), holes, drain, qty in SPEC:
    g, (x0, x1, y0, y1), bends = unfold(poly, fl, holes, drain)
    w, l = y1 - y0, x1 - x0
    short, long_ = min(w, l), max(w, l)
    fits = short <= MAXFLAT[0] + 1e-6 and long_ <= MAXFLAT[1] + 1e-6
    bok = max(bends) <= MAXBEND
    ok &= fits and bok
    open(f"{name}.dxf", "w").write(g.dumps())
    print(f"{name:14} {w:8.2f} x {l:8.2f} {short/25.4:6.2f} x {long_/25.4:6.2f} "
          f"{'yes' if fits else 'NO':>5} {max(bends)/25.4:8.2f} in {len(bends):>6} {len(holes)}")

print(f"\nspan {LD} + {LU} - {LAP} = {LD + LU - LAP} mm  (frame width {XF1})")
print(f"notch {N} x {N} hugs the 40 mm upright with {N - 40:.1f} mm all round")
print(f"mitre gap {MITRE_GAP} mm vs 1.60 mm material")
print(f"floor kept per corner vs the 45 deg chamfer: {84*84/2 - N*N:.0f} mm2")
assert abs(LD + LU - LAP - XF1) < 1e-9 and ok and MITRE_GAP > 1.6002
print("all checks pass")
