"""Gantry parts modelled at real dimensions.

Sources for the numbers:
  C-Beam 40 x 80, 20-series V-slot                       Maker Store LR-C-S
  XL gantry plate 125 x 125 x 6; wheel holes 100.6 c/c,  OpenBuilds forum, V10
    plain 5.1, eccentric 7.2                              drawing measurements
  Solid V wheel OD 23.90 at the ridge, 10.23 wide, 5 bore OpenBuilds spec
  Eccentric spacer: 8 mm hex, 6 long, 0.79 bore offset   OpenBuilds spec
  M5 low profile head 9.5 x 2.8                          DIN 7984 class
  NEMA 23: 56.4 flange, 47.14 hole square, 5.1 through   StepperOnline drawing
    holes, 38.1 boss, 6.35 shaft
  GT2 20T: pitch dia 12.73, 2 mm pitch, 6 mm belt height GT2 standard
  Lead screw Tr8x8(p2), 8 mm OD, 8 mm lead               BOM D10

How a C-Beam carriage actually goes together, because Rev C drew it wrong:
the wheels STRADDLE the 80 mm beam and ride the V-grooves on its top and
bottom faces, 10 mm behind the front face. Screw, plate, 6 mm spacer, wheel,
nyloc. That leaves the plate's back 1.1 mm off the beam's front face.
"""
import math
import numpy as np
from kit3d import (box, extrude, cylinder, revolve, tube, merge, mv, rot, scale,
                   circle_pts, ring, hexring, disc, Part, SEG,
                   ALU, ALU_D, STEEL, BLACKPART, POM, BRASS, PCB, ARM, HILITE)

# ------------------------------------------------------------------ C-Beam
CB_D, CB_H, CB_T = 40.0, 80.0, 20.0     # depth, height, wall
SLOT_W, SLOT_D = 6.2, 1.8               # V-groove mouth and depth
GROOVE_BACK = 10.0                      # top/bottom grooves, behind the front face


def _vnotch(p0, p1, n_slots):
    """Insert n V notches along the straight segment p0 -> p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    if L < 1e-9 or n_slots < 1:
        return []
    u = d / L
    nrm = np.array([-u[1], u[0]])          # into the material (CCW loop)
    pts = []
    seg = L / n_slots
    for k in range(n_slots):
        c = p0 + u * (seg * (k + 0.5))
        pts += [tuple(c - u * (SLOT_W / 2)), tuple(c + nrm * SLOT_D),
                tuple(c + u * (SLOT_W / 2))]
    return pts


def cbeam(length):
    """C-Beam swept along +Z. Section in XY: x 0..40 deep (mouth at x = 40),
    y 0..80 tall. Grooves: 2 on the top face, 2 on the bottom, 1 on each
    front lip, 4 on the back."""
    c = [(0, 0), (CB_D, 0), (CB_D, CB_T), (CB_T, CB_T),
         (CB_T, CB_H - CB_T), (CB_D, CB_H - CB_T), (CB_D, CB_H), (0, CB_H)]
    prof = [c[0]]
    prof += _vnotch(c[0], c[1], 2)          # bottom face
    prof.append(c[1])
    prof += _vnotch(c[1], c[2], 1)          # lower front lip
    prof += [c[2], c[3], c[4], c[5]]
    prof += _vnotch(c[5], c[6], 1)          # upper front lip
    prof.append(c[6])
    prof += _vnotch(c[6], c[7], 2)          # top face
    prof.append(c[7])
    prof += _vnotch(c[7], c[0], 4)          # back face
    return extrude(np.array(prof), length, z0=0.0)


# ------------------------------------------------------------- gantry plate
PLATE, PLATE_T = 125.0, 6.0
WH_X = WH_Y = 100.6               # wheel centres, both ways, across the beam
HOLE_FIXED, HOLE_ECC = 5.1, 7.2
SPACER_T = 6.0
WHEEL_W = 10.23
WHEEL_R = 11.95                   # radius at the V ridge
# plate back to the beam's front face: the wheel's mid-plane sits on the
# groove 10 mm behind that face, and spacer + half a wheel is 11.115
PLATE_GAP = SPACER_T + WHEEL_W / 2 - GROOVE_BACK          # 1.115
CARR_STACK = PLATE_GAP + PLATE_T                          # 7.115


def gantry_plate(clamp_holes=False):
    """XL C-Beam gantry plate, 125 x 125 x 6. Fixed wheels on the +/+ and -/-
    diagonal (5.1), eccentrics on the other (7.2), nut-block window, and the
    four M5 holes the mast or arm plate bolts through."""
    out = np.array([(-PLATE/2, -PLATE/2), (PLATE/2, -PLATE/2),
                    (PLATE/2, PLATE/2), (-PLATE/2, PLATE/2)])
    holes = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            d = HOLE_FIXED if sx * sy > 0 else HOLE_ECC
            holes.append(circle_pts(d / 2, SEG, sx*WH_X/2, sy*WH_Y/2))
    holes.append(np.array([(-14, -11), (14, -11), (14, 11), (-14, 11)]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            holes.append(circle_pts(2.6, SEG, sx*25, sy*38))
    if clamp_holes:                       # belt clamps, X carriage only
        for sx in (-1, 1):
            for dx in (-5, 5):
                holes.append(circle_pts(2.6, SEG, sx*32 + dx, 9.0))
    return extrude(out, PLATE_T, z0=0.0, holes=holes)


# ------------------------------------------------------------------- wheels
def solid_v_wheel():
    """Solid V wheel with its two bearings: OD 23.90 at the ridge, 10.23 wide."""
    R, W = WHEEL_R, WHEEL_W
    # one revolved solid: bore, bearing face recessed 0.4, V tread
    return revolve([(2.5, 0.4), (6.2, 0.4), (6.2, 0), (9.2, 0), (R, W/2),
                    (9.2, W), (6.2, W), (6.2, W - 0.4), (2.5, W - 0.4),
                    (2.5, 0.4)])


def wheel_assembly(flip=False):
    return solid_v_wheel()


def eccentric_spacer():
    """8 mm hex, 6 long, with a 7.1 boss that sits in the plate's 7.2 hole.
    The bore is 0.79 off centre: turning the hex moves the wheel toward or
    away from the beam. The hex is BETWEEN plate and wheel; an 8 mm spanner
    reaches it from the side. Local z: hex 0..6, boss -6..0."""
    off = (0.0, 0.79)
    hx = hexring(8.0, 2.55, SPACER_T, c=(0, 0, 0), bore_off=off)
    boss = disc(3.55, 2.55, PLATE_T, c=(0, 0, -PLATE_T), bore_off=off)
    return merge(hx, boss)


def plain_spacer(h=SPACER_T):
    return ring(5.0, 2.55, h)


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


def nut_block():
    """Anti-backlash nut block: flange block, threaded boss, spring and the
    floating half, all bored 8.2 for the screw."""
    blk = extrude(np.array([(-19, -10), (19, -10), (19, 10), (-19, 10)]), 11.0,
                  holes=[circle_pts(4.1, SEG), circle_pts(2.6, SEG, -13, 0),
                         circle_pts(2.6, SEG, 13, 0)])
    boss = ring(9.0, 4.1, 9.0, c=(0, 0, 11.0))
    spring = ring(7.0, 5.0, 5.0, c=(0, 0, 20.0))
    half = ring(9.0, 4.1, 6.0, c=(0, 0, 25.0))
    # the two tapped M5 holes on the face that meets the carriage plate
    taps = [mv(rot(cylinder(2.1, 0.05), rx=-math.pi/2), sx * 13, 10.0, 5.5)
            for sx in (-1, 1)]
    return merge(blk, boss, spring, half, *taps)


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


def belt_clamp():
    """Clamp block on the back of the X carriage, reaching into the rail's
    channel to grip one end of the belt. Local: x 22 along the rail, y 0..18
    deep (into the channel), z 0..10 high, belt slot at z 2..4.5."""
    lower = box(22.0, 18.0, 2.0)
    upper = box(22.0, 18.0, 5.5, c=(0, 0, 4.5))
    side = box(22.0, 4.0, 2.5, c=(0, 14.0, 2.0))
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
def arm_plate():
    """The SendCutSend plate: 160 square, 6.35 thick, 22 bore, 8 radial slots."""
    out = np.array([(-80, -80), (80, -80), (80, 80), (-80, 80)])
    holes = [circle_pts(11.0, SEG)]
    for k in range(8):
        a = 2*math.pi*k/8
        ca, sa = math.cos(a), math.sin(a)
        # stadium slot from r = 20 to r = 54, 7 wide, with round ends
        pts = []
        for th in np.linspace(math.pi/2, 3*math.pi/2, 24):
            pts.append((20*ca + 3.5*(math.cos(th)*ca - math.sin(th)*sa),
                        20*sa + 3.5*(math.cos(th)*sa + math.sin(th)*ca)))
        for th in np.linspace(-math.pi/2, math.pi/2, 24):
            pts.append((54*ca + 3.5*(math.cos(th)*ca - math.sin(th)*sa),
                        54*sa + 3.5*(math.cos(th)*sa + math.sin(th)*ca)))
        holes.append(np.array(pts))
    for sx in (-1, 1):
        for sy in (-1, 1):
            holes.append(circle_pts(2.6, SEG, sx*25, sy*38))
    return extrude(out, 6.35, z0=0.0, holes=holes)


def arm_envelope():
    """Retained for old callers only; drawings use the real mesh (arm280)."""
    base = cylinder(80.0, 62.0)
    return base


# ================================================================ fasteners
def socket_cap(M=5.0, L=12.0, n=SEG, low_profile=False):
    """Socket head cap screw, head at z = 0 up, shank down to z = -L.
    DIN 912, or DIN 7984 low profile (the wheel screws)."""
    if low_profile:
        hd, hh = 9.5 if M == 5 else M * 1.8, 2.8 if M == 5 else M * 0.55
    else:
        hd, hh = M * 1.7, M * 1.0
    head = revolve([(0, 0), (hd/2 - 0.3, 0), (hd/2, 0.3), (hd/2, hh - 0.4),
                    (hd/2 - 0.4, hh), (0, hh)])
    af = {3: 2.5, 4: 3.0, 5: 4.0, 6: 5.0}.get(int(M), M * 0.8)
    if low_profile:
        af = 3.0 if M == 5 else af
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


def cbeam_end_plate():
    """End plate the size of the C-Beam section, 40 x 80 x 6, with a 22 mm
    bearing bore on the channel centreline and four M5 holes into the end
    taps. Local x across the 40 depth (bore at x = 0 = channel centre, which
    sits 10 mm behind the mouth), local y along the 80 height."""
    out = np.array([(-30, -40), (10, -40), (10, 40), (-30, 40)])
    holes = [circle_pts(11.0, SEG)]
    for hx in (-20.0, 0.0):
        for hy in (-30.0, 30.0):
            holes.append(circle_pts(2.75, SEG, hx, hy))
    return extrude(out, 6.0, holes=holes)


def standoff(h=8.0, M=3.0):
    return merge(hexring(5.5, M / 2, h), cylinder(M * 0.5, 4.0, c=(0, 0, -4.0)))
