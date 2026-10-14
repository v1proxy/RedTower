#!/usr/bin/env python3
"""Arm mounting plate (BOM G071), 6061-T6 0.250 in, cut only, no bends.

Elephant Robotics publishes the myCobot 280 base hole pattern only as an image, nowhere
as numbers, so this plate is designed NOT TO NEED the pattern: the arm bolts into eight
radial slots, which absorb any bolt-circle diameter from 40 to 108 mm, at any multiple of
45 degrees. The carriage side uses two long edge slots so it can bolt to the C-Beam
gantry anywhere over 110 mm of travel.

Slot width is 7.0 mm against a 6.35 mm plate, which clears SendCutSend's
minimum-feature-equals-thickness rule for aluminium. An M4 fender washer (12 mm OD) or
an M5 one (15 mm OD) covers it with room to spare.
"""
import math, sys
sys.path.insert(0, "/home/claude/greenhouse/sendcutsend")
from make_dxf import Dxf

T       = 6.35      # 0.250 in
SIDE    = 160.0     # plate is SIDE x SIDE
CORNER  = 12.0      # corner radius
BORE    = 22.0      # central cable pass-through diameter
SLOT_W  = 7.0       # every slot, > T as required
N_RAD   = 8         # radial slots
R_IN    = 20.0      # radial slot centreline, inner end
R_OUT   = 54.0      # radial slot centreline, outer end
EDGE_X  = 66.0      # edge slot centreline x
EDGE_Y  = 55.0      # edge slot runs +/- this in y

assert SLOT_W > T, "slot narrower than the plate is thick: SendCutSend will reject it"


def slot(d, a, b, w):
    """Rounded slot: two parallel flanks plus a semicircular cap at each end."""
    th = math.atan2(b[1] - a[1], b[0] - a[0])
    r = w / 2.0
    px, py = -math.sin(th) * r, math.cos(th) * r
    d.line((a[0] + px, a[1] + py), (b[0] + px, b[1] + py))
    d.line((b[0] - px, b[1] - py), (a[0] - px, a[1] - py))
    deg = math.degrees(th)
    d.arc(b, r, deg - 90.0, deg + 90.0)
    d.arc(a, r, deg + 90.0, deg + 270.0)


def build():
    d = Dxf()
    h, c = SIDE / 2.0, CORNER
    # rounded-square outline, counter-clockwise
    d.line((-h + c, -h), (h - c, -h))
    d.arc((h - c, -h + c), c, 270.0, 360.0)
    d.line((h, -h + c), (h, h - c))
    d.arc((h - c, h - c), c, 0.0, 90.0)
    d.line((h - c, h), (-h + c, h))
    d.arc((-h + c, h - c), c, 90.0, 180.0)
    d.line((-h, h - c), (-h, -h + c))
    d.arc((-h + c, -h + c), c, 180.0, 270.0)
    # cable pass-through
    d.circle((0.0, 0.0), BORE / 2.0)
    # arm side: radial slots
    for k in range(N_RAD):
        th = math.radians(360.0 * k / N_RAD)
        u = (math.cos(th), math.sin(th))
        slot(d, (R_IN * u[0], R_IN * u[1]), (R_OUT * u[0], R_OUT * u[1]), SLOT_W)
    # carriage side: two long edge slots
    for sx in (-1.0, 1.0):
        slot(d, (sx * EDGE_X, -EDGE_Y), (sx * EDGE_X, EDGE_Y), SLOT_W)
    return d


d = build()
open("arm_plate.dxf", "w").write(d.dumps())

env_out = R_OUT + SLOT_W / 2.0
env_in = R_IN - SLOT_W / 2.0
checks = [
    ("bolt circles the radial slots accept",
     f"{2*R_IN:.0f} to {2*R_OUT:.0f} mm diameter", True),
    ("slot width vs plate thickness",
     f"{SLOT_W:.2f} mm slot vs {T:.2f} mm thick", SLOT_W > T),
    ("web between bore and slot inner end",
     f"{env_in - BORE/2:.2f} mm", env_in - BORE / 2 >= T * 0.8),
    ("material between adjacent radial slots at inner end",
     f"{2*R_IN*math.sin(math.pi/N_RAD) - SLOT_W:.2f} mm",
     2 * R_IN * math.sin(math.pi / N_RAD) - SLOT_W >= T),
    ("gap, radial slot outer end to edge slot",
     f"{EDGE_X - SLOT_W/2 - env_out:.2f} mm", EDGE_X - SLOT_W / 2 - env_out >= T * 0.7),
    ("edge slot to plate edge",
     f"{SIDE/2 - EDGE_X - SLOT_W/2:.2f} mm", SIDE / 2 - EDGE_X - SLOT_W / 2 >= T),
    ("flat size vs SendCutSend 6061 .250 max 36 x 46 in",
     f"{SIDE/25.4:.2f} x {SIDE/25.4:.2f} in", SIDE / 25.4 <= 36.0),
]
print(f"{'check':52} {'value':26} ok")
print("-" * 86)
ok = True
for name, val, good in checks:
    ok &= good
    print(f"{name:52} {val:26} {'yes' if good else 'NO'}")
print(f"\nall checks pass: {ok}")
print(f"plate area {SIDE*SIDE/645.16:.1f} sq in")
assert ok
