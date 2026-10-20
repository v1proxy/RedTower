"""Gantry sub-assemblies, in one place, at real dimensions.

Both the assembly booklet and the cabinet model build from these, so the
bench drawings and the installed drawings cannot disagree again.

BENCH FRAME, for any C-Beam lying on the bench (the X rail, or the Z mast
before it is hung):
    x   along the beam, 0 .. L
    y   depth. Back face y = 0, channel floor y = 20, front lips and channel
        mouth y = 40. The carriage is on the +y side.
    z   height, 0 .. 80. MIDZ = 40 is the beam's centreline.

The carriage stack, outside in, as OpenBuilds designed it:
    low profile screw | plate 6 | spacer 6 (or eccentric) | shim 1 | wheel 11 | nyloc
with the wheel's mid-plane on the side-face grooves 10 mm behind the mouth,
so the plate's back sits 2.5 mm proud of the beam. Fixed wheels on one
side of the plate, eccentrics on the other: that is how the XL plate is
drilled.
"""
import math

import numpy as np

import parts as P
from kit3d import (Part, merge, mv, rot, box, cylinder, ALU, ALU_D, STEEL,
                   BLACKPART, POM, BRASS, HILITE)

FRONT = 40.0
MIDZ = 40.0
GROOVE_Y = FRONT - P.GROOVE_BACK                 # 30
WHEEL_Y0 = GROOVE_Y - P.WHEEL_W / 2              # 24.5
SHIM_Y0 = GROOVE_Y + P.WHEEL_W / 2               # 35.5
SPACER_Y0 = SHIM_Y0 + P.SHIM_T                   # 36.5
PLATE_BACK = SPACER_Y0 + P.SPACER_T              # 42.5
PLATE_FRONT = PLATE_BACK + P.PLATE_T             # 48.5
CB_DEPTH = 1.6                                   # plate counterbores / recess
CHANNEL_FLOOR = FRONT - (P.CB_D - P.CB_T)        # 20
NB_Y = PLATE_BACK - P.SPACER_T - P.NB_T / 2      # 30.5, nut block centre
SCREW_Y = NB_Y                                   # lead screw axis

BELT_TOOTH_R = 20 * P.GT2_PITCH / math.pi / 2 - 0.254   # pulley tooth tips
BELT_Y0 = 22.5                                   # belt band, y 22.5 .. 31.5
BLACK = BLACKPART
BELT = np.array([0.20, 0.21, 0.22])


# -------------------------------------------------------------- placement
def place(mesh, ex, ey, ez, t):
    """Map local axes to the bench: local x -> ex, y -> ey, z -> ez, then
    translate. Columns, so any basis (mirrored or not) reads plainly."""
    V, F = mesh
    R = np.array([ex, ey, ez], float).T
    return (V @ R.T + np.asarray(t, float), F)


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
NX, NY, NZ = (-1, 0, 0), (0, -1, 0), (0, 0, -1)


def along_py(mesh, t):
    """A part built along local +z, pointing along bench +y."""
    return place(mesh, X, Z, Y, t)


def along_ny(mesh, t):
    return place(mesh, X, Z, NY, t)


def along_px(mesh, t):
    """Along bench +x (lead screw, nut block bore)."""
    return place(mesh, Y, Z, X, t)


def along_nx(mesh, t):
    return place(mesh, NY, Z, NX, t)


def rail(L):
    """C-Beam on the bench: cbeam() local x (depth) -> y, local y -> z,
    local z (length) -> x."""
    return place(P.cbeam(L), Y, Z, X, (0, 0, 0))


# ---------------------------------------------------------------- carriage
# (along, across, eccentric): the XL plate's 5.1 fixed mounts are all on
# +across, its 7.2 eccentric mounts all on -across. On the X rail +across is
# up, so the fixed wheels carry the load and the eccentrics preload from below.
WHEELS = [(-1, 1, False), (1, 1, False), (-1, -1, True), (1, -1, True)]


def carriage(x=0.0, explode=0.0, hi=None, show=("plate", "fixed", "ecc"),
             clamp_holes=False, nuts=True):
    """XL plate with four wheel stacks, centred at x. `explode` pulls the
    screws out to +y and the spacers, shims, wheels and nuts back to -y."""
    out = []
    e = explode
    if "plate" in show:
        out.append(Part(along_py(P.gantry_plate(), (x, PLATE_BACK, MIDZ)),
                        HILITE if hi == "plate" else STEEL))
    for sx, sy, ecc in WHEELS:
        grp = "ecc" if ecc else "fixed"
        if grp not in show:
            continue
        wx, wz = x + sx * P.WH_X / 2, MIDZ + sy * P.WH_Y / 2
        h = hi == grp
        if ecc:
            sp = along_ny(P.eccentric_spacer(), (wx, PLATE_BACK - e * 0.8, wz))
        else:
            sp = along_py(P.plain_spacer(), (wx, SPACER_Y0 - e * 0.8, wz))
        out.append(Part(sp, HILITE if h else ALU_D))
        out.append(Part(along_py(P.shim(), (wx, SHIM_Y0 - e * 1.25, wz)),
                        HILITE if h else STEEL))
        out.append(Part(along_py(P.solid_v_wheel(), (wx, WHEEL_Y0 - e * 1.7, wz)),
                        HILITE if h else POM))
        out.append(Part(along_py(P.socket_cap(5, 30, low_profile=True),
                                 (wx, PLATE_FRONT - CB_DEPTH + e * 1.2, wz)),
                        HILITE if h else STEEL))
        if nuts:
            out.append(Part(along_ny(P.nyloc(), (wx, WHEEL_Y0 - e * 2.6, wz)),
                            HILITE if h else STEEL))
    return out


# ----------------------------------------------------------------- X drive
X_MOTOR_X = P.MMP_L / 2            # motor plate flush with the rail's left end
X_IDLER_INSET = 50.0               # idler axle from the right end


def x_motor_plate(explode=0.0, hi=False, screws=True, tnuts=True):
    """Motor mount plate on the front lips at the rail's left end, with its
    four M5 x 10 into T-nuts in the lip grooves (z = 10 and 70)."""
    c = HILITE if hi else ALU
    plate = place(P.motor_mount_plate(), Z, X, Y,
                  (X_MOTOR_X, FRONT + explode * 0.0, MIDZ))
    out = [Part(plate, c)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, pz = X_MOTOR_X + sy * 40, MIDZ + sx * 30
            if screws:
                out.append(Part(along_py(P.socket_cap(5, 10),
                                         (px, FRONT + 6 + explode * 1.0, pz)),
                                HILITE if hi else STEEL))
            if tnuts:
                out.append(Part(along_py(rot(P.tnut(), rz=0.0),
                                         (px, FRONT - 4.4 - explode * 0.6, pz)),
                                HILITE if hi else STEEL))
    return out


def x_motor(explode=0.0, hi=False, screws=True, length=76.0):
    """NEMA 23 in front of its plate, shaft pointing -y into the channel.
    Four M5 x 10 go in FROM THE MOTOR SIDE: NEMA 23 flanges are through
    drilled, so the heads seat on the back of the flange and the threads
    take in the plate."""
    y_face = FRONT + 6.0 + explode
    out = [Part(along_ny(P.nema23(length), (X_MOTOR_X, y_face + length, MIDZ)),
                HILITE if hi == "motor" else STEEL)]
    if screws:
        for sx in (-1, 1):
            for sy in (-1, 1):
                out.append(Part(along_py(P.socket_cap(5, 10),
                                         (X_MOTOR_X + sx * P.NEMA_HOLE_SQ / 2,
                                          y_face + P.NEMA_FLANGE_T + explode * 0.9,
                                          MIDZ + sy * P.NEMA_HOLE_SQ / 2)),
                                HILITE if hi == "screws" else STEEL))
    return out


def x_pulley(explode=0.0, hi=False, grubs=True):
    """GT2 20T on the X motor shaft, inside the rail's channel: boss toward
    the motor, toothed hub on the belt plane y 22.5 .. 31.5."""
    y0 = 21.0 - explode
    c = HILITE if hi else STEEL
    out = [Part(along_py(P.gt2_pulley(), (X_MOTOR_X, y0, MIDZ)), c)]
    if grubs:
        for k, (dx, dz) in enumerate(((0.0, 8.0), (8.0, 0.0))):
            g = P.grub_screw(5, 6)
            if dz:
                g = place(g, X, Y, NZ, (X_MOTOR_X, y0 + 15.5, MIDZ + 8.0 + explode * 0.6))
            else:
                g = place(g, Z, Y, NX, (X_MOTOR_X + 8.0 + explode * 0.6, y0 + 15.5, MIDZ))
            out.append(Part(g, c))
    return out


def x_idler(L, explode=0.0, hi=False):
    """Idler at the right end on an M5 x 40 through the web (drill 5.2):
    head on the back face, washer, idler, washer, nyloc, all in the channel."""
    xi = L - X_IDLER_INSET
    e = explode
    c = HILITE if hi else STEEL
    return [Part(along_ny(P.socket_cap(5, 40), (xi, 0.0 - e * 1.4, MIDZ)), c),
            Part(along_py(P.washer(), (xi, CHANNEL_FLOOR + e * 0.2, MIDZ)), c),
            Part(along_py(P.idler(), (xi, CHANNEL_FLOOR + 1.0 + e * 0.5, MIDZ)), c),
            Part(along_py(P.washer(), (xi, CHANNEL_FLOOR + 13.0 + e * 0.8, MIDZ)), c),
            Part(along_py(P.nyloc(), (xi, CHANNEL_FLOOR + 14.0 + e * 1.1, MIDZ)), c)]


def x_belt(L, carriage_x=None, hi=False):
    """GT2 belt in the rail's channel, width along y (the pulley axis), teeth
    inward. With a carriage, the top run is cut and both ends clamp to it."""
    r1 = BELT_TOOTH_R + P.BELT_T / 2
    r2 = 6.0 + P.BELT_T / 2
    pts, (t0, t1) = P.belt_loop((X_MOTOR_X, MIDZ), r1, (L - X_IDLER_INSET, MIDZ), r2)
    c = HILITE if hi else BELT
    if carriage_x is None:
        return [Part(P.ribbon(pts, BELT_Y0, closed=True), c, lw=0.3)]
    zt = MIDZ + r1                         # top run height (near-equal radii)
    inner = CLAMP_X - P.CLAMP_L / 2 + 3.0  # ends finish inside the clamps
    a = (carriage_x - inner, zt)
    b = (carriage_x + inner, zt)
    path = np.vstack([[a], pts[t1:], pts[:t0 + 1], [b]])
    return [Part(P.ribbon(path, BELT_Y0, closed=False), c, lw=0.3)]


CLAMP_X = 20.0      # clamp centres, from the carriage centre


def x_clamps(cx, explode=0.0, hi=False, screws=True):
    """Two clamp blocks on the back of the X carriage, in the channel, each
    gripping one end of the top run. Each takes two M5 x 25 low profile
    through the plate's existing holes at (+/-10, +10) and (+/-30, +10)."""
    out = []
    e = explode
    c = HILITE if hi else ALU_D
    for sx in (-1, 1):
        blk = place(P.belt_clamp(), X, NY, Z,
                    (cx + sx * CLAMP_X - P.CLAMP_L / 2, PLATE_BACK - e * 0.8, MIDZ + 4.0))
        out.append(Part(blk, c))
        if screws:
            for dx in (-10, 10):
                out.append(Part(along_py(P.socket_cap(5, 25, low_profile=True),
                                         (cx + sx * CLAMP_X + dx, PLATE_FRONT + e, MIDZ + 10.0)),
                                HILITE if hi else STEEL))
    return out


# ----------------------------------------------------------------- Z drive
def z_screw(L_mast, hi=False):
    """Tr8x8 on the channel centreline, from the coupler at the foot to the
    top end plate, where it hangs between two thrust bearings."""
    # starts 2 mm clear of the motor shaft inside the coupler, ends past the
    # top collar
    return [Part(along_px(P.lead_screw(L_mast + 1.4), (18.6, SCREW_Y, MIDZ)),
                 HILITE if hi else STEEL)]


def z_nut(cx, explode=0.0, hi=False, screws=True, nuts=True, spacers=True):
    """OpenBuilds anti-backlash nut block on the Z carriage's back, in the
    mast's channel, screw bore along x. Two M5 x 25 low profile from the
    plate's face through its nut holes at (-10, +/-10), through two 6 mm
    spacers and the block, into M5 nuts in the block's pockets."""
    c = HILITE if hi else BLACK
    e = explode
    bx = cx - 10.0 + P.NB_HOLE_OFF            # block centre along the mast
    nb = place(P.nut_block(), Z, X, Y, (bx, NB_Y - e * 1.0, MIDZ))
    out = [Part(nb, c)]
    for dz in (-10.0, 10.0):
        if spacers:
            out.append(Part(along_py(P.plain_spacer(), (cx - 10.0, SPACER_Y0 - e * 0.5, MIDZ + dz)),
                            HILITE if hi else ALU_D))
        if screws:
            out.append(Part(along_py(P.socket_cap(5, 25, low_profile=True),
                                     (cx - 10.0, PLATE_FRONT - CB_DEPTH + e * 0.9, MIDZ + dz)),
                            HILITE if hi else STEEL))
        if nuts:
            out.append(Part(along_ny(P.hex_nut(), (cx - 10.0, NB_Y - P.NB_T / 2 - e * 1.6 + 4.7, MIDZ + dz)),
                            HILITE if hi else STEEL))
    return out


TAPS = [(10.0, 30.0), (10.0, 50.0), (10.0, 10.0), (10.0, 70.0), (30.0, 10.0), (30.0, 70.0)]
# (bench y, bench z) of the C-Beam's six M5 end taps


def z_end_plate(at_x, foot, hi=False, screws=True):
    """Foot: the NEMA 23 motor plate (BOM D14) across the mast end, facing
    -x, four M5 x 12 into the end taps. Top: the OpenBuilds C-Beam End Mount,
    four M5 x 25 low profile into the end taps (web pair and flange pair)."""
    c = HILITE if hi else ALU
    if foot:
        m = place(P.motor_mount_plate(), Y, Z, NX, (at_x, SCREW_Y, MIDZ))
        out = [Part(m, c)]
        if screws:
            for ty, tz in ((10.0, 10.0), (10.0, 70.0), (30.0, 10.0), (30.0, 70.0)):
                out.append(Part(place(P.socket_cap(5, 12), Y, Z, NX, (at_x - 6.0, ty, tz)),
                                HILITE if hi else STEEL))
        return out
    m = place(P.cbeam_end_mount(), NZ, Y, X, (at_x, 0.0, MIDZ))
    out = [Part(m, c)]
    if screws:
        for ty, tz in ((10.0, 30.0), (10.0, 50.0), (30.0, 10.0), (30.0, 70.0)):
            out.append(Part(place(P.socket_cap(5, 25, low_profile=True), Y, Z, X,
                                  (at_x + P.EM_T - 1.55, ty, tz)), HILITE if hi else STEEL))
    return out


def z_top_bearings(L_mast, hi=False):
    """Two 8 mm thrust bearings and two lock collars at the top: one bearing
    seated in the End Mount's recess with its collar above, one under the
    mount with its collar below, so the screw HANGS from the top and the
    coupler at the foot only ever carries torque."""
    c = HILITE if hi else STEEL
    rec = L_mast + P.EM_T - P.BEARING_RECESS[1]          # recess floor
    out = [Part(along_px(P.thrust_bearing(), (rec, SCREW_Y, MIDZ)), c),
           Part(along_px(P.lock_collar(), (rec + 5.0, SCREW_Y, MIDZ)), c),
           Part(along_nx(P.thrust_bearing(), (L_mast, SCREW_Y, MIDZ)), c),
           Part(along_nx(P.lock_collar(), (L_mast - 5.0, SCREW_Y, MIDZ)), c)]
    return out


def _collar():
    return P.lock_collar()


def z_motor(hi=False, coupler=True):
    """Braked NEMA 23 outside the foot plate, shaft along +x into the coupler."""
    out = [Part(place(P.nema23(76.0, brake=True), Y, Z, X,
                      (-6.0 - 76.0, SCREW_Y, MIDZ)),
                HILITE if hi == "motor" else STEEL)]
    if coupler:
        out.append(Part(along_px(P.coupler(), (2.0, SCREW_Y, MIDZ)),
                        HILITE if hi == "coupler" else ALU_D))
    return out
