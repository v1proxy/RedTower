"""Gantry parts modelled at real dimensions.

Rev E: the OpenBuilds parts now follow bd_warehouse's open_builds.py, which
models them from OpenBuilds' own drawings (github.com/gumyr/bd_warehouse):
  C-Beam 40 x 80 profile with its 14 T-grooves, M5 end taps and cores
  XL C-Beam gantry plate 125 x 125 x 6: wheel mounts 100.6 c/c, EXCENTRICS
    ON ONE SIDE (7.2, counterbored 12.25) and FIXED ON THE OTHER (5.1,
    counterbored 9.135), 35 x 35 centre recess, tapped M5 at (+/-50.3, +/-30)
  Xtreme Solid V wheel 23.9 x 10.2, two 625 bearings, 11 over the bearings
  Eccentric spacer: 10 mm hex, 6 cam, 7.11 boss 2.5 long, 0.79 offset
  Aluminium spacer 10 OD x 6, precision shim 10 x 5 x 1
  Anti-backlash nut block 34 x 33 x 12, two M5 on 20, hex nut pockets
  C-Beam End Mount 80 x 50 x 12 with a 16.1 x 4.5 bearing recess
  Lock collar 8 mm: 14 OD x 7
  M5 low profile screw (OpenBuilds): head 9.0 x 1.5, 3 mm hex
Other numbers:
  NEMA 23: 56.4 flange, 47.14 hole square, 38.1 boss    StepperOnline drawing
  GT2 20T: pitch dia 12.73, 2 mm pitch                  GT2 standard
  Lead screw Tr8x8(p2), 8 mm OD, 8 mm lead              BOM D10

How a C-Beam carriage goes together: the wheels STRADDLE the 80 mm beam and
ride the V-grooves on its two 40 mm faces, 10 mm behind the mouth. Stack,
outside in: low profile screw, plate 6, spacer 6 (or eccentric), shim 1,
wheel 11, nyloc. The plate's back sits 2.5 mm proud of the beam.
"""
import math
import numpy as np
from kit3d import (box, extrude, cylinder, revolve, tube, merge, mv, rot, scale,
                   circle_pts, ring, hexring, disc, Part, SEG,
                   ALU, ALU_D, STEEL, BLACKPART, POM, BRASS, PCB, ARM, HILITE)

# ------------------------------------------------------------------ C-Beam
CB_D, CB_H, CB_T = 40.0, 80.0, 20.0     # depth, height, wall
SLOT_W, SLOT_D = 6.25, 1.455            # V lip opening and the V's depth
GROOVE_BACK = 10.0                      # side-face grooves, behind the mouth

# OpenBuilds T-groove, in groove coords: gx = 10 at the surface, gy across.
_GROOVE = [(10, -4.58), (8.545, -3.125), (8.2, -3.125), (8.2, -5.5),
           (6.5607, -5.5), (3.9, -2.8393), (3.9, -0.21), (3.69, 0.0),
           (3.9, 0.21), (3.9, 2.8393), (6.5607, 5.5), (8.2, 5.5),
           (8.2, 3.125), (8.545, 3.125), (10, 4.58)]
_FLANGE_CORE = [(-2.7, 38.2), (-2.7, 36.2393), (-6.1, 32.8393), (-6.1, 27.1607),
                (-0.73934, 21.8), (2.7, 21.8), (2.7, 23.7607), (6.1, 27.1607),
                (6.1, 32.8393), (2.7, 36.2393), (2.7, 38.2)]
_WEB_CORE = [(-8.2, 2.7), (-8.2, -2.7), (-6.2393, -2.7), (-2.8393, -6.1),
             (2.8393, -6.1), (6.2393, -2.7), (8.2, -2.7), (8.2, 2.7),
             (6.2393, 2.7), (2.8393, 6.1), (-2.8393, 6.1), (-6.2393, 2.7)]


def cbeam_profile():
    """(outer, holes) of the C-Beam section in OpenBuilds' frame: X -20..20
    with the channel mouth at X = +20, Y -40..40."""
    corners = [(-20, -40), (20, -40), (20, -20), (0, -20), (0, 20), (20, 20),
               (20, 40), (-20, 40)]
    grooves = {0: [-10, 10], 1: [-30], 2: [10], 3: [-10, 10], 4: [10], 5: [30],
               6: [10, -10], 7: [30, 10, -10, -30]}
    fillet = {0, 1, 2, 5, 6, 7}           # every corner except the two at X = 0
    r = 1.5
    pts = []
    n = len(corners)
    for k in range(n):
        c0 = np.array(corners[k], float)
        c1 = np.array(corners[(k + 1) % n], float)
        t = (c1 - c0) / np.linalg.norm(c1 - c0)
        nin = np.array([-t[1], t[0]])
        # leaving corner k
        if k in fillet:
            tp = np.array(corners[k], float) - np.array(corners[k - 1], float)
            tp /= np.linalg.norm(tp)
            cen = c0 - tp * r + t * r
            a0 = math.atan2(*(c0 - tp * r - cen)[::-1])
            a1 = math.atan2(*(c0 + t * r - cen)[::-1])
            if a1 < a0:
                a1 += 2 * math.pi
            for a in np.linspace(a0, a1, 7):
                pts.append(tuple(cen + r * np.array([math.cos(a), math.sin(a)])))
        else:
            pts.append(tuple(c0))
        for gpos in grooves[k]:
            # groove centre on this edge, at coordinate gpos along it
            s0 = c0 + t * (np.dot(t, np.array([gpos, gpos]) * np.abs(t)) - np.dot(t, c0 * np.abs(t)))
            s0 = c0 + t * abs(np.dot(np.abs(t), np.array([gpos, gpos]) - c0))
            for gx, gy in _GROOVE:
                pts.append(tuple(s0 + nin * (10.0 - gx) + t * gy))
    holes = [circle_pts(2.3, SEG, x, y) for x, y in
             ((10, 30), (-10, 30), (-10, 10), (-10, -10), (-10, -30), (10, -30))]
    A = np.array(_FLANGE_CORE)
    B = A * np.array([1, -1])
    C = np.c_[20 - A[:, 1], 20 - A[:, 0]]
    D = np.c_[20 + B[:, 1], B[:, 0] - 20]
    W = np.array(_WEB_CORE) + np.array([-10.0, 0.0])
    holes += [A, B[::-1], C[::-1], D, W]
    return np.array(pts), holes


def cbeam(length):
    """C-Beam swept along +Z. Section in XY: x 0..40 deep (mouth at x = 40),
    y 0..80 tall: OpenBuilds' profile shifted by (+20, +40)."""
    outer, holes = cbeam_profile()
    sh = np.array([20.0, 40.0])
    return extrude(outer + sh, length, z0=0.0, holes=[h + sh for h in holes])


# ------------------------------------------------------------- gantry plate
PLATE, PLATE_T = 125.0, 6.0
WH_X = WH_Y = 100.6               # wheel centres, both ways, across the beam
HOLE_FIXED, HOLE_ECC = 5.1, 7.2
SPACER_T = 6.0
SHIM_T = 1.0
WHEEL_W = 11.0                    # over the two bearings' faces
TIRE_W = 10.2
WHEEL_R = 11.95                   # radius at the V ridge
# plate back to the beam's mouth: the wheel's mid-plane sits on the groove
# 10 mm behind the mouth; spacer + shim + half a wheel is 12.5 from the plate
PLATE_GAP = SPACER_T + SHIM_T + WHEEL_W / 2 - GROOVE_BACK  # 2.5
CARR_STACK = PLATE_GAP + PLATE_T                          # 8.5
TAPPED_90 = [(sx * 50.3, sy * 30.0) for sx in (-1, 1) for sy in (-1, 1)]
NUT_HOLES = [(sx * 10.0, sy * 10.0) for sx in (-1, 1) for sy in (-1, 1)]
PLAIN_HOLES = ([(x, y) for x in (-30, 0, 30) for y in (-30, 0, 30)]
               + [(sx * 10.0, sy * 40.3) for sx in (-1, 1) for sy in (-1, 1)]
               + [(sx * 32.5, sy * 40.3) for sx in (-1, 1) for sy in (-1, 1)]
               + [(sx * 30.0, sy * 10.0) for sx in (-1, 1) for sy in (-1, 1)]
               + [(sx * 30.0, sy * 50.3) for sx in (-1, 1) for sy in (-1, 1)])
ECC_MOUNTS = [(x, -50.3) for x in (-50.3, 0.0, 50.3)]     # 7.2, one side
FIXED_MOUNTS = [(x, 50.3) for x in (-50.3, 0.0, 50.3)]    # 5.1, the other


def _rrect(w, h, r, n=8, cx=0.0, cy=0.0):
    pts = []
    for (qx, qy, a0) in ((w/2 - r, -h/2 + r, -90), (w/2 - r, h/2 - r, 0),
                         (-w/2 + r, h/2 - r, 90), (-w/2 + r, -h/2 + r, 180)):
        for a in np.radians(np.linspace(a0, a0 + 90, n)):
            pts.append((cx + qx + r * math.cos(a), cy + qy + r * math.sin(a)))
    return np.array(pts)


def _slot(L, W, cx, cy, n=16):
    """Stadium slot, overall length L along x, width W."""
    r = W / 2
    pts = [(cx + (L/2 - r) + r * math.cos(a), cy + r * math.sin(a))
           for a in np.linspace(-math.pi/2, math.pi/2, n)]
    pts += [(cx - (L/2 - r) + r * math.cos(a), cy + r * math.sin(a))
            for a in np.linspace(math.pi/2, 3*math.pi/2, n)]
    return np.array(pts)


def gantry_plate(clamp_holes=False):
    """OpenBuilds XL C-Beam gantry plate, 125 x 125 x 6, local z 0..6 with
    the OUTER face (screw heads, counterbores, recess) at z = 6. Local x runs
    along the beam, y across it: eccentric mounts at y = -50.3, fixed at
    +50.3. `clamp_holes` is ignored: the real plate has none, the belt clamps
    use the (+/-10, +/-30 ... ) pattern below."""
    out = _rrect(PLATE, PLATE, 10.0)
    cb = 1.6
    base_holes, top_holes = [], []
    for (x, y) in PLAIN_HOLES + NUT_HOLES:
        base_holes.append(circle_pts(2.6, SEG, x, y))
    for (x, y) in TAPPED_90:
        base_holes.append(circle_pts(2.1, SEG, x, y))
    for (x, y) in ECC_MOUNTS:
        base_holes.append(circle_pts(3.6, SEG, x, y))
        top_holes.append(circle_pts(6.125, SEG, x, y))
    for (x, y) in FIXED_MOUNTS:
        base_holes.append(circle_pts(2.55, SEG, x, y))
        top_holes.append(circle_pts(4.5675, SEG, x, y))
    for sx in (-1, 1):
        for sy in (-1, 1):
            base_holes.append(_slot(7.1, 5.1, sx * 51.3, sy * 10.0))
            top_holes.append(_slot(11.135, 9.136, sx * 51.3, sy * 10.0))
    # the top 1.6: the 35 x 35 recess swallows the nut holes and the centre
    # hole; everything else keeps its own hole at that level
    recess = _rrect(35.0, 35.0, 2.8)
    keep = []
    for (x, y) in PLAIN_HOLES:
        if abs(x) <= 17.5 and abs(y) <= 17.5:
            continue
        keep.append(circle_pts(2.6, SEG, x, y))
    for (x, y) in TAPPED_90:
        keep.append(circle_pts(2.7, SEG, x, y))        # the countersink lip
    base = extrude(out, PLATE_T - cb, z0=0.0, holes=base_holes)
    top = extrude(out, cb, z0=PLATE_T - cb, holes=top_holes + keep + [recess])
    return merge(base, top)


# ------------------------------------------------------------------- wheels
def solid_v_wheel():
    """Xtreme Solid V wheel on its two 625 bearings: tire 23.9 x 10.2 with a
    2.15 chamfer each side making the V, bearings 16 OD standing 0.4 proud
    each side (11 overall), 5 bore. Local z 0..11."""
    R, T = WHEEL_R, TIRE_W
    z0 = (WHEEL_W - T) / 2
    tire = revolve([(8.0, z0), (R - 2.15, z0), (R, z0 + 2.15), (R, z0 + T - 2.15),
                    (R - 2.15, z0 + T), (8.0, z0 + T), (8.0, z0)])
    brg = revolve([(2.5, 0.0), (8.0, 0.0), (8.0, WHEEL_W), (2.5, WHEEL_W), (2.5, 0.0)])
    return merge(tire, brg)


def wheel_assembly(flip=False):
    return solid_v_wheel()


def eccentric_spacer():
    """OpenBuilds eccentric spacer, 6 mm: 10 mm hex (a 10 mm spanner turns
    it), 7.11 boss 2.5 long that drops into the plate's 7.2 hole, 5 bore
    0.79 off centre. Local z: hex 0..6, boss -2.5..0."""
    off = (0.0, 0.79)
    hx = hexring(10.0, 2.55, SPACER_T, c=(0, 0, 0), bore_off=off)
    boss = disc(3.555, 2.55, 2.5, c=(0, 0, -2.5), bore_off=off)
    return merge(hx, boss)


def plain_spacer(h=SPACER_T):
    """OpenBuilds aluminium spacer, 10 OD, M5 bore."""
    return ring(5.0, 2.6, h)


def shim(od=10.0, t=SHIM_T):
    """Precision shim 10 x 5 x 1."""
    return ring(od / 2, 2.55, t)


# ------------------------------------------------------------------ motors
NEMA_B = 56.4
NEMA_HOLE_SQ = 47.14
NEMA_FLANGE_T = 5.0


def _octagon(half, cut):
    """Square of half-size `half` with 45 degree corners where |x|+|y| > cut."""
    t = cut - half
    return np.array([(half, -t), (half, t), (t, half), (-t, half),
                     (-half, t), (-half, -t), (-t, -half), (t, -half)])


def nema23(length=76.0, brake=False):
    """NEMA 23 stepper, front face at z = length, shaft along +z.

    Chamfered stator, a full 56.4 square front flange 5 thick with four
    5.1 through holes on the 47.14 square, the 38.1 pilot boss and a 6.35
    shaft with a flat. The chamfers are what leave room for the screw heads
    behind the flange."""
    b = NEMA_B / 2
    L = length
    stator = extrude(_octagon(b, 41.0), L - NEMA_FLANGE_T, z0=0.0)
    holes = [circle_pts(2.55, SEG, sx*NEMA_HOLE_SQ/2, sy*NEMA_HOLE_SQ/2)
             for sx in (-1, 1) for sy in (-1, 1)]
    flange = extrude(np.array([(-b, -b), (b, -b), (b, b), (-b, b)]),
                     NEMA_FLANGE_T, z0=L - NEMA_FLANGE_T, holes=holes)
    boss = cylinder(19.05, 1.6, c=(0, 0, L))
    r = 6.35 / 2
    shaft = cylinder(r, 6.0, c=(0, 0, L + 1.6))
    tc = math.asin((r - 0.5) / r)                        # flat 0.5 deep on +y
    a = np.linspace(math.pi - tc, 2 * math.pi + tc, SEG)
    dprof = np.c_[r * np.cos(a), r * np.sin(a)]
    dshaft = extrude(dprof, 15.0, z0=L + 7.6)              # the flat
    rear = extrude(_octagon(b - 0.6, 40.2), 3.0, z0=-3.0)
    parts = [stator, flange, boss, shaft, dshaft, rear,
             cylinder(5.0, 6.0, c=(b - 9.0, 0, -9.0))]      # cable exit
    if brake:
        parts.append(cylinder(25.0, 36.0, c=(0, 0, -39.0)))
        parts.append(cylinder(9.0, 4.0, c=(0, 0, -43.0)))
    return merge(*parts)


# -------------------------------------------------------------- Z drive bits
def lead_screw(length, r=4.0, lead=8.0, turns_seg=24):
    """8 mm Acme rod with a helical thread sweep."""
    core = cylinder(r * 0.78, length)
    n = int(length / lead * turns_seg)
    t = np.linspace(0, length / lead * 2 * math.pi, max(n, 8))
    path = np.c_[r*0.86*np.cos(t), r*0.86*np.sin(t), t/(2*math.pi)*lead]
    thread = tube(path, 1.25, n=7)
    return merge(core, thread)


NB_W, NB_L, NB_T = 34.0, 33.0, 12.0   # across the screw, along it, thick
NB_HOLE_OFF = 6.5                       # mounting holes sit this far along the screw


def nut_block():
    """OpenBuilds anti-backlash nut block for 8 mm Acme: Delrin, 34 across
    the screw x 33 along it x 12 thick, local z -6..6. Screw bore along local
    y through the centre. Two M5 mounting holes on 20 across, 6.5 along from
    the centre; counterbored 9 x 2 on +z, M5 nut pockets 5 deep on -z. The
    tension slot runs in from the +x side; an M5 across it, parallel to the
    screw, closes it to take the backlash out."""
    r = 3.0
    q = _rrect(NB_W, NB_L, r)
    # notch the outline from x = +17 back to the slot's round end at x = -9
    sx0, sx1, y0, y1 = -9.0, NB_W / 2, 3.5, 8.5
    keep = [p for p in q if not (p[0] > sx0 and y0 < p[1] < y1)]
    k = min(range(len(keep)), key=lambda i: (abs(keep[i][0] - NB_W/2) + abs(keep[i][1] - y0)))
    end = [(sx0 + 2.5 * math.cos(a), 6.0 + 2.5 * math.sin(a)) for a in np.linspace(-math.pi/2, -3*math.pi/2, 12)]
    notch = [(sx1, y0)] + end + [(sx1, y1)]
    out = np.array(keep[:k + 1] + notch + keep[k + 1:])
    mh = [circle_pts(2.55, SEG, sx * 10.0, -NB_HOLE_OFF) for sx in (-1, 1)]
    hexes = [np.array([(sx * 10.0 + 4.6188 * math.cos(math.radians(30 + 60 * j)),
                        -NB_HOLE_OFF + 4.6188 * math.sin(math.radians(30 + 60 * j)))
                       for j in range(6)]) for sx in (-1, 1)]
    cbs = [circle_pts(4.5, SEG, sx * 10.0, -NB_HOLE_OFF) for sx in (-1, 1)]
    low = extrude(out, 5.0, z0=-6.0, holes=hexes)
    mid = extrude(out, 5.0, z0=-1.0, holes=mh)
    top = extrude(out, 2.0, z0=4.0, holes=cbs)
    # screw bore along y, shown as a ring on each end face
    ends = [mv(rot(ring(5.2, 4.0, 0.2), rx=-math.pi/2), 0, yy, 0) for yy in (-NB_L/2 - 0.2, NB_L/2)]
    tens = mv(rot(ring(4.0, 2.5, 0.2), rx=-math.pi/2), 10.0, NB_L/2, 0)
    return merge(low, mid, top, *ends, tens)


def thrust_bearing():
    """8 mm thrust bearing: two washers and the ball cage, 8 bore, 16 OD."""
    a = ring(8.0, 4.1, 1.5)
    cage = ring(7.3, 4.8, 2.0, c=(0, 0, 1.5))
    b = ring(8.0, 4.1, 1.5, c=(0, 0, 3.5))
    return merge(a, cage, b)


def coupler(bore=6.35):
    """Flexible beam coupler, 19 OD x 25, with its cut slots showing."""
    segs = []
    z = 0.0
    for k, h in enumerate((6.0, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 7.4)):
        if k % 2 == 0:
            segs.append(ring(9.5, bore / 2 if z < 12 else 4.0, h, c=(0, 0, z)))
        else:
            segs.append(ring(8.2, bore / 2 if z < 12 else 4.0, h, c=(0, 0, z)))
        z += h
    return merge(*segs)


# -------------------------------------------------------------- X drive bits
GT2_PITCH = 2.0
BELT_W, BELT_T = 9.0, 1.38


def gt2_pulley(teeth=20, bore=6.35):
    """GT2 20T, 9 mm belt: toothed hub between two flanges, set-screw boss.
    Local z: flange 0..1, hub 1..11, flange 11..12, boss 12..19."""
    pd = teeth * GT2_PITCH / math.pi
    ro = pd / 2 - 0.254
    rr = ro - 0.75
    pts = []
    for k in range(teeth):
        a0 = 2 * math.pi * k / teeth
        for frac, rad in ((0.0, rr), (0.18, rr), (0.32, ro), (0.68, ro), (0.82, rr)):
            a = a0 + frac * 2 * math.pi / teeth
            pts.append((rad * math.cos(a), rad * math.sin(a)))
    hub = extrude(np.array(pts), 10.0, z0=1.0, holes=[circle_pts(bore/2, SEG)])
    f1 = ring(8.0, bore / 2, 1.0)
    f2 = ring(8.0, bore / 2, 1.0, c=(0, 0, 11.0))
    boss = ring(8.0, bore / 2, 7.0, c=(0, 0, 12.0))
    return merge(f1, hub, f2, boss)


def idler(belt_w=BELT_W):
    """Smooth flanged idler for a 9 mm belt, 5 mm bore. Local z 0..12."""
    f1 = ring(9.0, 2.55, 1.0)
    core = ring(6.0, 2.55, 10.0, c=(0, 0, 1.0))
    f2 = ring(9.0, 2.55, 1.0, c=(0, 0, 11.0))
    return merge(f1, core, f2)


def ribbon(path_xz, y0, w=BELT_W, t=BELT_T, closed=False):
    """A belt: band of thickness t along a 2D centreline in the x-z plane,
    width w along y (the pulley axis). Teeth face the inside of the loop."""
    P = np.asarray(path_xz, float)
    n = len(P)
    if closed:
        d = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    else:
        d = np.gradient(P, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-12)[:, None]
    nrm = np.c_[d[:, 1], -d[:, 0]]                 # outward for a CCW loop
    inner = P - nrm * t / 2
    outer = P + nrm * t / 2
    V = []
    for loop in (inner, outer):
        for yy in (y0, y0 + w):
            V.append(np.c_[loop[:, 0], np.full(n, yy), loop[:, 1]])
    V = np.vstack(V)                                # blocks: in0 in1 out0 out1
    I0, I1, O0, O1 = 0, n, 2 * n, 3 * n
    F = []
    m = n if closed else n - 1
    for i in range(m):
        j = (i + 1) % n
        for a, b in ((I0, I1), (O0, O1), (I0, O0), (I1, O1)):
            F += [[a + i, a + j, b + j], [a + i, b + j, b + i]]
    if not closed:
        for k in (0, n - 1):
            F += [[I0 + k, I1 + k, O1 + k], [I0 + k, O1 + k, O0 + k]]
    return (V, np.array(F, int))


def belt_loop(c1, r1, c2, r2, n_arc=48):
    """Closed belt centreline around two pulleys (x, z centres, pitch radii),
    counter-clockwise. Returns the polyline and the index range of the TOP
    run, so a carriage can cut it and clamp the two ends."""
    (x1, z1), (x2, z2) = c1, c2
    # external tangents for near-equal radii on a near-horizontal line
    ang = math.atan2(z2 - z1, x2 - x1)
    D = math.hypot(x2 - x1, z2 - z1)
    phi = math.asin((r1 - r2) / D)
    up = ang + math.pi / 2 + phi
    pts = []
    # arc around pulley 2 (right), from the bottom tangent to the top one
    a0, a1 = ang - math.pi / 2 - phi, up
    for a in np.linspace(a0, a1, n_arc):
        pts.append((x2 + r2 * math.cos(a), z2 + r2 * math.sin(a)))
    top0 = len(pts) - 1
    # arc around pulley 1 (left), top to bottom, going over the left side
    for a in np.linspace(up, ang - math.pi / 2 - phi + 2 * math.pi, n_arc):
        pts.append((x1 + r1 * math.cos(a), z1 + r1 * math.sin(a)))
    top1 = n_arc
    return np.array(pts), (top0, top1)


CLAMP_L, CLAMP_DEPTH = 28.0, 20.0


def belt_clamp():
    """Clamp block on the back of the X carriage, reaching into the rail's
    channel to grip one end of the belt. Local: x 0..28 along the rail, y
    0..20 deep (into the channel), z 0..10 high, belt slot at z 2..4.5. Two
    M5 holes 20 apart at z = 6, matching the plate's (10, 30) hole pair."""
    L, Dp = CLAMP_L, CLAMP_DEPTH
    hole = lambda: [circle_pts(2.6, SEG, L / 2 + dx, 6.0) for dx in (-10, 10)]
    lower = box(L, Dp, 2.0)
    upper = rot(extrude(np.array([(0, 4.5), (L, 4.5), (L, 10.0), (0, 10.0)]), Dp,
                        holes=hole()), rx=-math.pi/2)
    upper = mv(upper, 0, Dp, 0)
    side = box(L, 4.0, 2.5, c=(0, Dp - 4.0, 2.0))
    return merge(lower, upper, side)


# --------------------------------------------------------------- electronics
def limit_switch():
    body = box(20.0, 6.5, 10.5, c=(-10, -3.25, 0))
    lever = box(16.0, 0.8, 1.2, c=(-8, -4.4, 8.0))
    btn = cylinder(1.6, 1.4, n=24, c=(4.5, 0, 10.5))
    return merge(body, lever, btn)


def controller_board():
    """Footprint block, per the project's model-fidelity rule for boards."""
    pcb = box(100.0, 70.0, 1.8, c=(0, 0, 0))
    blocks = [box(12, 12, 9, c=(8+18*k, 8, 1.8)) for k in range(4)]     # TMC2209
    esp = box(26, 18, 4.5, c=(8, 44, 1.8))
    conn = [box(16, 8, 9, c=(8+20*k, 58, 1.8)) for k in range(4)]
    term = box(38, 10, 11, c=(56, 44, 1.8))
    return merge(pcb, esp, term, *blocks, *conn)


def psu_block():
    return merge(box(215, 115, 30, c=(0, 0, 0)),
                 box(215, 10, 30, c=(0, 115, 0)))


# ---------------------------------------------------------------- robot arm
ARM_BASE_HOLES = [(sx * 22.0, sy * 22.0) for sx in (-1, 1) for sy in (-1, 1)]     # M4, 44 square
ARM_GBASE_HOLES = [(sx * 46.0, sy * 65.0) for sx in (-1, 1) for sy in (-1, 1)]    # M3, G base
ARM_PLATE_CSK = [(sx * 30.0, sy * 50.3) for sx in (-1, 1) for sy in (-1, 1)]


def arm_plate():
    """Arm plate Rev B (SendCutSend, 6061-T6 0.250 in): 160 square, R12
    corners, 22 bore. Four M3 TAPPED at (+/-46, +/-65): the arm's G base
    bolts down through its four outer corner holes. Four M4 TAPPED at
    (+/-22, +/-22), the arm's own 44 mm square, for mounting without the G
    base. Four 5.5 holes COUNTERSUNK 90 deg to 10.4 on the arm side at
    (+/-30, +/-50.3): flat head M5 x 10 into the XL gantry plate's four
    tapped holes, flush under the base. All read off Elephant's G_base mesh
    and the OpenBuilds plate. Local x = world x, y = world z (up), z 0..6.35
    with the countersunk face at z = 6.35."""
    out = _rrect(160.0, 160.0, 12.0)
    T = 6.35
    try:
        return _arm_plate_solid(out, T)
    except ImportError:
        pass
    # no manifold3d: the countersinks as four stacked layers (drawn with seams)
    bore = circle_pts(11.0, SEG)
    taps = ([circle_pts(1.65, SEG, x, y) for x, y in ARM_BASE_HOLES]
            + [circle_pts(1.25, SEG, x, y) for x, y in ARM_GBASE_HOLES])
    layers = [(0.0, T - 2.6, 2.75), (T - 2.6, 0.9, 3.6), (T - 1.7, 0.85, 4.4), (T - 0.85, 0.85, 5.2)]
    parts = []
    for z0, h, r in layers:
        csk = [circle_pts(r, SEG, x, y) for x, y in ARM_PLATE_CSK]
        parts.append(extrude(out, h, z0=z0, holes=[bore] + taps + csk))
    return merge(*parts)


def _arm_plate_solid(outline, T):
    """The arm plate as one closed solid (manifold3d): true 90 degree cones for
    the countersinks and no faces inside the plate, so nothing shows through
    in the line drawings."""
    import manifold3d as M3
    cs = M3.CrossSection([np.asarray(outline, float).tolist()])
    plate = M3.Manifold.extrude(cs, T)
    cuts = [M3.Manifold.cylinder(T + 2.0, 11.0, 11.0, SEG).translate([0, 0, -1.0])]
    for (x, y), r in [(h, 1.65) for h in ARM_BASE_HOLES] + [(h, 1.25) for h in ARM_GBASE_HOLES]:
        cuts.append(M3.Manifold.cylinder(T + 2.0, r, r, SEG).translate([x, y, -1.0]))
    r0, r1 = 2.75, 5.2                                    # 5.5 through, 10.4 at the arm face, 90 deg
    zc = T - (r1 - r0)
    for x, y in ARM_PLATE_CSK:
        cuts.append(M3.Manifold.cylinder(T + 2.0, r0, r0, SEG).translate([x, y, -1.0]))
        cuts.append(M3.Manifold.cylinder(r1 - r0 + 1.0, r0, r1 + 1.0, SEG).translate([x, y, zc]))
    for c in cuts:
        plate = plate - c
    m = plate.to_mesh()
    return np.asarray(m.vert_properties, float)[:, :3], np.asarray(m.tri_verts, int)


def arm_envelope():
    """Retained for old callers only; drawings use the real mesh (arm280)."""
    base = cylinder(80.0, 62.0)
    return base


# ================================================================ fasteners
def socket_cap(M=5.0, L=12.0, n=SEG, low_profile=False):
    """Socket head cap screw, head at z = 0 up, shank down to z = -L.
    DIN 912, or DIN 7984 low profile (the wheel screws)."""
    if low_profile:              # OpenBuilds low profile: 9.0 x 1.5 (M5)
        hd, hh = {3: (5.68, 1.5), 4: (7.22, 1.5), 5: (9.0, 1.5)}.get(int(M), (M * 1.8, 1.5))
    else:                        # ISO 4762
        hd, hh = {2.5: (4.68, 2.5), 3: (5.68, 3.0), 4: (7.22, 4.0), 5: (8.72, 5.0)}.get(M, (M * 1.7, M))
    head = revolve([(0, 0), (hd/2 - 0.3, 0), (hd/2, 0.3), (hd/2, hh - 0.4),
                    (hd/2 - 0.4, hh), (0, hh)])
    af = {3: 2.5, 4: 3.0, 5: 4.0, 6: 5.0}.get(int(M), M * 0.8)
    if low_profile:
        af = {3: 2.0, 4: 2.5, 5: 3.0}.get(int(M), af)
    R = af / 2 / math.cos(math.pi / 6)
    sock = mv(extrude(circle_pts(R, 6, start=math.pi/6), 0.02), 0, 0, hh)
    shank = cylinder(M / 2, L, c=(0, 0, -L))
    # thread: shallow rings so it reads as threaded at a glance
    rings = [cylinder(M/2 + 0.12, 0.45, c=(0, 0, -L + 0.8 + k * 1.6))
             for k in range(int(max(1, (L - 2.0) / 1.6)))]
    return merge(head, sock, shank, *rings)


def grub_screw(M=5.0, L=6.0):
    body = cylinder(M / 2, L)
    R = 2.5 / 2 / math.cos(math.pi / 6)
    sock = mv(extrude(circle_pts(R, 6, start=math.pi/6), 0.02), 0, 0, L)
    return merge(body, sock)


def washer(M=5.0, od=None, t=1.0):
    od = od or M * 2.0
    return ring(od / 2, M / 2 * 1.08, t)


def nyloc(M=5.0, h=5.0):
    """Hex body with the nylon collar on top, bored through."""
    af = M * 1.6
    body = hexring(af, M / 2, h * 0.72)
    collar = ring(af / 2 * 0.95, M / 2, h * 0.28, c=(0, 0, h * 0.72))
    return merge(body, collar)


def hex_nut(M=5.0):
    """ISO 4032 hex nut: M5 is 8 across flats, 4.7 thick. Local z 0..m."""
    af, m = {3: (5.5, 2.4), 4: (7.0, 3.2), 5: (8.0, 4.7)}.get(int(M), (M * 1.6, M * 0.9))
    return hexring(af, M / 2, m)


def tnut(M=5.0):
    """Drop-in T-nut for an 8 mm 20-series slot: head, neck, threaded bore."""
    hole = [circle_pts(M / 2 * 0.85, SEG)]
    head = extrude(np.array([(-9.5, -4.9), (9.5, -4.9), (9.5, 4.9), (-9.5, 4.9)]),
                   2.4, holes=hole)
    neck = extrude(np.array([(-5.5, -3.0), (5.5, -3.0), (5.5, 3.0), (-5.5, 3.0)]),
                   2.0, z0=2.4, holes=hole)
    ball = cylinder(1.6, 1.2, c=(7.0, 0, -1.2))     # the spring detent
    return merge(head, neck, ball)


def corner_bracket(a=40.0, t=5.0, w=20.0):
    """90 degree corner bracket for 20-series slots, with its two holes."""
    leg1 = extrude(np.array([(0, 0), (a, 0), (a, w), (0, w)]), t,
                   holes=[circle_pts(2.75, SEG, a * 0.6, w / 2)])
    leg2 = rot(extrude(np.array([(0, 0), (a, 0), (a, w), (0, w)]), t,
                       holes=[circle_pts(2.75, SEG, a * 0.6, w / 2)]), ry=-math.pi/2)
    gus = box(t * 0.8, w * 0.5, t * 0.8, c=(t, w * 0.25, t))
    return merge(leg1, mv(leg2, t, 0, 0), gus)


MMP_W, MMP_L = 70.0, 96.0        # motor mount plate: across the beam, along it


def motor_mount_plate():
    """NEMA 23 mount: 70 across the beam x 96 along it, 6 thick. 38.1 pilot
    bore, four M5 TAPPED holes on the 47.14 square for the motor, and four
    5.5 holes into the beam's front-lip grooves (60 apart), outside the
    motor flange so the heads clear it. Local x = across the beam."""
    out = np.array([(-MMP_W/2, -MMP_L/2), (MMP_W/2, -MMP_L/2),
                    (MMP_W/2, MMP_L/2), (-MMP_W/2, MMP_L/2)])
    holes = [circle_pts(19.05, SEG)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            holes.append(circle_pts(2.1, SEG, sx*NEMA_HOLE_SQ/2, sy*NEMA_HOLE_SQ/2))
            holes.append(circle_pts(2.75, SEG, sx*30, sy*40))
    return extrude(out, 6.0, holes=holes)


EM_W, EM_D, EM_T = 80.0, 50.0, 12.0
BEARING_RECESS = (16.1, 4.5)


def cbeam_end_mount():
    """OpenBuilds C-Beam End Mount, 80 x 50 x 12. Local: x along the beam's
    80, y across its depth with y = 0 on the beam's BACK face and y = 50 ten
    mm beyond the mouth, z 0..12 with z = 0 against the beam's end. Bearing
    recess 16.1 x 4.5 on the outer face, 11.2 through, on the screw axis;
    four M5 counterbored 9.2 x 1.55 into the beam's end taps (web pair 20
    apart, flange pair 60 apart); two M5 tapped on 47.14 for a motor."""
    out = _rrect(EM_W, EM_D, 1.0, cx=0.0, cy=EM_D / 2)
    sy = 30.5                   # screw axis, from the back face (assy.SCREW_Y)
    taps = [(-10.0, 10.0), (10.0, 10.0), (-30.0, 30.0), (30.0, 30.0)]
    thr = [circle_pts(2.6, SEG, x, y) for x, y in taps]
    cbr = [circle_pts(4.6, SEG, x, y) for x, y in taps]
    mot = [circle_pts(2.1, SEG, sx * 23.57, sy - 23.57) for sx in (-1, 1)]
    rd, rh = BEARING_RECESS
    l1 = extrude(out, EM_T - rh, z0=0.0, holes=[circle_pts(5.59, SEG, 0.0, sy)] + thr + mot)
    l2 = extrude(out, rh - 1.55, z0=EM_T - rh, holes=[circle_pts(rd / 2, SEG, 0.0, sy)] + thr + mot)
    l3 = extrude(out, 1.55, z0=EM_T - 1.55, holes=[circle_pts(rd / 2, SEG, 0.0, sy)] + cbr + mot)
    return merge(l1, l2, l3)


def lock_collar(bore=8.0):
    """OpenBuilds lock collar, 8 mm: 14 OD x 7, M5 set screw. Local z 0..7."""
    body = ring(7.0, bore / 2, 7.0)
    ss = mv(rot(cylinder(2.5, 0.6), rx=-math.pi/2), 0, 7.0, 3.5)
    return merge(body, ss)


def cbeam_end_plate():
    """Retained name: the top of the mast is the real C-Beam End Mount."""
    return cbeam_end_mount()


def standoff(h=8.0, M=3.0):
    return merge(hexring(5.5, M / 2, h), cylinder(M * 0.5, 4.0, c=(0, 0, -4.0)))


# ================================================================ Rev E additions
def flat_head(M=5.0, L=10.0):
    """ISO 10642 countersunk socket screw: M5 head 10.0 dia, 90 deg, 2.8 deep.
    Head top at z = 0, shank down to z = -L (L includes the head)."""
    dk, k = {4: (8.0, 2.3), 5: (10.0, 2.8), 3: (6.0, 1.7)}.get(int(M), (2 * M, 0.56 * M))
    head = revolve([(0, -k), (M / 2, -k), (dk / 2, 0.0), (0, 0.0)])
    shank = cylinder(M / 2, L - k, c=(0, 0, -L))
    af = {3: 2.0, 4: 2.5, 5: 3.0}.get(int(M), M * 0.6)
    R = af / 2 / math.cos(math.pi / 6)
    sock = mv(extrude(circle_pts(R, 6, start=math.pi / 6), 0.02), 0, 0, 0.0)
    return merge(head, shank, sock)


def cast_corner_bracket():
    """20-series cast corner bracket (OpenBuilds / 2020 type): 20 wide, legs
    20, 4 thick, M5 slot in each leg centred 10 from the corner, so each leg's
    screw lands on a 20-series slot whose centreline is 10 from the joint.
    Local: corner along x (0..20), leg A on z = 0 running +y, leg B on y = 0
    running +z, the joint line at the origin edge."""
    t, L, W = 4.0, 20.0, 20.0
    slot = lambda: [np.array([(W / 2 + 2.75 * math.cos(a), 10.0 + 1.5 * (1 if math.sin(a) > 0 else -1)
                               + 2.75 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)])]
    legA = extrude(np.array([(0, 0), (W, 0), (W, L), (0, L)]), t, holes=slot())
    legB = extrude(np.array([(0, 0), (W, 0), (W, L), (0, L)]), t, holes=slot())
    legB = rot(legB, rx=math.pi / 2)            # into the x-z plane, y = 0..-t
    legB = mv(legB, 0, t, 0)
    V, F = extrude(np.array([(t, t), (L - 3, t), (t, L - 3)]), 3.0)   # web, in y-z
    rib = (np.c_[V[:, 2] + W / 2 - 1.5, V[:, 0], V[:, 1]], F)
    return merge(legA, legB, rib)


def standoff_mf(h=10.0, M=3.0, male=6.0):
    """Male-female hex standoff: 5.5 hex, `h` body, `male` thread below."""
    return merge(hexring(5.5, M / 2 * 0.85, h), cylinder(M / 2, male, c=(0, 0, -male)))


def mounting_panel(w=150.0, d=110.0, t=3.0, holes=()):
    """Aluminium mounting panel inside the electronics enclosure."""
    out = np.array([(0, 0), (w, 0), (w, d), (0, d)])
    return extrude(out, t, z0=-t, holes=[circle_pts(1.6, SEG, x, y) for x, y in holes])


# --------------------------------------------------------- X rail brackets
# SendCutSend, 5052-H32 aluminium 0.125 in, one 90 deg bend. Outside
# dimensions. Leg A lies on the C-Beam (top or bottom face), its two M5 on
# the face's FRONT groove, 30 behind the leg-B face; leg B lies on the 4040.
RB_T = 3.175
RB_RI = RB_T                     # inner bend radius
RB_W = 40.0
RB_KIND = {
    # leg A length, leg B length, leg A holes (x), leg B holes (x, from-corner)
    "top":    (40.0, 35.0, (10.0, 30.0), [(10.0, 20.0), (30.0, 20.0)]),
    "bottom": (40.0, 50.0, (10.0, 30.0), [(20.0, 20.0), (20.0, 40.0)]),
}
RB_HOLE_A = 30.0                 # leg A holes, from leg B's outer face


def rail_bracket(kind="top", n_arc=12):
    """Bent bracket, local: width along x 0..40; corner (virtual sharp,
    outside) at y = 0, z = 0; leg A on z 0..t running toward -y; leg B on
    y -t..0 running up +z."""
    La, Lb, ha, hb = RB_KIND[kind]
    t, Ri = RB_T, RB_RI
    Ro = Ri + t
    holeA = [circle_pts(2.75, SEG, x, -RB_HOLE_A) for x in ha]
    legA = extrude(np.array([(0, -La), (RB_W, -La), (RB_W, -Ro), (0, -Ro)]), t, holes=holeA)
    # leg B: in x-z, thickness y -t..0
    holeB = [circle_pts(2.75, SEG, x, z) for x, z in hb]
    V, F = extrude(np.array([(0, Ro), (RB_W, Ro), (RB_W, Lb), (0, Lb)]), t, holes=holeB)
    legB = (np.c_[V[:, 0], -V[:, 2], V[:, 1]], F)
    # the bend: quarter annulus about (y, z) = (-Ro, Ro), swept along x
    a = np.linspace(-math.pi / 2, 0.0, n_arc)
    ring_pts = []
    for r in (Ro, Ri):
        ring_pts.append(np.c_[-Ro + r * np.cos(a), Ro + r * np.sin(a)])
    prof = np.vstack([ring_pts[0], ring_pts[1][::-1]])
    V, F = extrude(prof, RB_W)                   # profile in (y, z), extruded along x
    bend = (np.c_[V[:, 2], V[:, 0], V[:, 1]], F)
    return merge(legA, legB, bend)


def rail_bracket_flat(kind="top", K=0.42):
    """Flat pattern for SendCutSend: (outline pts, holes [(x, y, d)], bend_y,
    flat length). x across the 40 width, y along the flat from leg A's end."""
    La, Lb, ha, hb = RB_KIND[kind]
    t, Ri = RB_T, RB_RI
    Ro = Ri + t
    BA = math.pi / 2 * (Ri + K * t)
    fa, fb = La - Ro, Lb - Ro
    L = fa + BA + fb
    holes = [(x, La - RB_HOLE_A, 5.5) for x in ha]
    holes += [(x, fa + BA + (z - Ro), 5.5) for x, z in hb]
    return L, holes, fa + BA / 2, BA


# ------------------------------------------------------- 40-series slot 8
# EU 40 x 40 slot 8 T-slot, groove coords as _GROOVE (gx = 12.2 at the face).
_TSLOT8 = [(12.2, -4.1), (9.9, -4.1), (9.9, -8.0), (7.4, -8.0), (4.6, -3.2),
           (4.6, 3.2), (7.4, 8.0), (9.9, 8.0), (9.9, 4.1), (12.2, 4.1)]


def _vnotch(p0, p1, n_slots):
    """One 40-series slot-8 T-groove in the middle of the segment p0 -> p1
    (the 4040 frame members; the C-Beam has its own profile above)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    if L < 1e-9 or n_slots < 1:
        return []
    u = d / L
    nrm = np.array([-u[1], u[0]])
    pts = []
    seg = L / n_slots
    for k in range(n_slots):
        c = p0 + u * (seg * (k + 0.5))
        for gx, gy in _TSLOT8:
            pts.append(tuple(c + nrm * (12.2 - gx) + u * gy))
    return pts
