"""Gantry sub-assemblies, in one place, at real dimensions.

Both the assembly booklet and the cabinet model build from these, so the
bench drawings and the installed drawings cannot disagree again.

BENCH FRAME, for any C-Beam lying on the bench (the X rail, or the Z mast
before it is hung):
    x   along the beam, 0 .. L
    y   depth. Back face y = 0, channel floor y = 20, front lips and channel
        mouth y = 40. The carriage is on the +y side.
    z   height, 0 .. 80. MIDZ = 40 is the beam's centreline.

The carriage stack, front to back, as OpenBuilds designed it:
    screw head | plate 6 | spacer 6 | wheel 10.23 | nyloc
with the wheel's mid-plane on the top/bottom grooves 10 mm behind the front
face, so the plate's back sits 1.115 mm proud of the beam.
"""
import math

import numpy as np

import parts as P
from kit3d import (Part, merge, mv, rot, box, cylinder, ALU, ALU_D, STEEL,
                   BLACKPART, POM, BRASS, HILITE)

FRONT = 40.0
MIDZ = 40.0
GROOVE_Y = FRONT - P.GROOVE_BACK                 # 30
WHEEL_Y0 = GROOVE_Y - P.WHEEL_W / 2              # 24.885
SPACER_Y0 = GROOVE_Y + P.WHEEL_W / 2             # 35.115
PLATE_BACK = SPACER_Y0 + P.SPACER_T              # 41.115
PLATE_FRONT = PLATE_BACK + P.PLATE_T             # 47.115
CHANNEL_FLOOR = FRONT - (P.CB_D - P.CB_T)        # 20
SCREW_Y = (CHANNEL_FLOOR + FRONT) / 2            # 30, channel centreline

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
WHEELS = [(-1, -1, False), (1, 1, False), (1, -1, True), (-1, 1, True)]


def carriage(x=0.0, explode=0.0, hi=None, show=("plate", "fixed", "ecc"),
             clamp_holes=False, nuts=True):
    """XL plate with four wheel stacks, centred at x. `explode` pulls the
    screws out to +y and the spacers, wheels and nuts back to -y."""
    out = []
    e = explode
    if "plate" in show:
        out.append(Part(along_py(P.gantry_plate(clamp_holes),
                                 (x, PLATE_BACK, MIDZ)),
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
        out.append(Part(along_py(P.solid_v_wheel(), (wx, WHEEL_Y0 - e * 1.7, wz)),
                        HILITE if h else POM))
        out.append(Part(along_py(P.socket_cap(5, 27, low_profile=True),
                                 (wx, PLATE_FRONT + e * 1.2, wz)),
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
    a = (carriage_x - 32.0 + 6.0, zt)      # ends finish inside the clamps
    b = (carriage_x + 32.0 - 6.0, zt)
    path = np.vstack([[a], pts[t1:], pts[:t0 + 1], [b]])
    return [Part(P.ribbon(path, BELT_Y0, closed=False), c, lw=0.3)]


def x_clamps(cx, explode=0.0, hi=False, screws=True):
    """Two clamp blocks on the back of the X carriage, in the channel, each
    gripping one end of the top run; two M5 x 10 each through the plate."""
    out = []
    e = explode
    c = HILITE if hi else ALU_D
    for sx in (-1, 1):
        blk = place(P.belt_clamp(), X, NY, Z,
                    (cx + sx * 32.0 - 11.0, PLATE_BACK - e * 0.8, MIDZ + 4.0))
        out.append(Part(blk, c))
        if screws:
            for dx in (-5, 5):
                out.append(Part(along_py(P.socket_cap(5, 10),
                                         (cx + sx * 32.0 + dx, PLATE_FRONT + e, MIDZ + 9.0)),
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


def z_nut(cx, explode=0.0, hi=False, screws=True):
    """Anti-backlash nut on the Z carriage's back, around the screw, bore
    along x; two M5 x 12 through the plate into its top face."""
    c = HILITE if hi else BRASS
    nb = place(P.nut_block(), Z, Y, X, (cx - 5.5, SCREW_Y - explode * 0.6, MIDZ))
    out = [Part(nb, c)]
    if screws:
        for dz in (-13, 13):
            out.append(Part(along_py(P.socket_cap(5, 12),
                                     (cx, PLATE_FRONT + explode, MIDZ + dz)),
                            HILITE if hi else STEEL))
    return out


def z_end_plate(at_x, foot, hi=False, screws=True):
    """Plate across a mast end, bolted into the profile's end-face taps.
    Foot: the NEMA 23 motor plate (BOM D14), facing -x. Top: a C-Beam end
    mount, facing +x. The 96 mm side runs across the beam's 80 mm height."""
    c = HILITE if hi else ALU
    if foot:
        m = place(P.motor_mount_plate(), Y, Z, NX, (at_x, SCREW_Y, MIDZ))
        sx_out = at_x - 6.0
    else:
        # section-sized: a full motor plate here would hit the X carriage
        m = place(P.cbeam_end_plate(), Y, Z, X, (at_x, SCREW_Y, MIDZ))
        sx_out = at_x + 6.0
    out = [Part(m, c)]
    if screws:
        for oy, oz in ((-20.0, 10.0), (-20.0, 70.0), (0.0, 10.0), (0.0, 70.0)):
            scr = P.socket_cap(5, 12)
            if foot:
                g = place(scr, Y, Z, NX, (sx_out, SCREW_Y + oy, oz))
            else:
                g = place(scr, Y, Z, X, (sx_out, SCREW_Y + oy, oz))
            out.append(Part(g, HILITE if hi else STEEL))
    return out


def z_top_bearings(L_mast, hi=False):
    """Two thrust bearings clamping the top end plate, each held by an 8 mm
    lock collar, so the screw HANGS from the top and the coupler at the foot
    only ever carries torque."""
    c = HILITE if hi else STEEL
    xp = L_mast                     # plate x L .. L + 6
    out = [Part(along_nx(P.thrust_bearing(), (xp, SCREW_Y, MIDZ)), c),
           Part(along_px(P.thrust_bearing(), (xp + 6.0, SCREW_Y, MIDZ)), c),
           Part(along_nx(_collar(), (xp - 5.5, SCREW_Y, MIDZ)), c),
           Part(along_px(_collar(), (xp + 11.5, SCREW_Y, MIDZ)), c)]
    return out


def _collar():
    from kit3d import ring as _ring
    return _ring(8.0, 4.0, 8.0)


def z_motor(hi=False, coupler=True):
    """Braked NEMA 23 outside the foot plate, shaft along +x into the coupler."""
    out = [Part(place(P.nema23(76.0, brake=True), Y, Z, X,
                      (-6.0 - 76.0, SCREW_Y, MIDZ)),
                HILITE if hi == "motor" else STEEL)]
    if coupler:
        out.append(Part(along_px(P.coupler(), (2.0, SCREW_Y, MIDZ)),
                        HILITE if hi == "coupler" else ALU_D))
    return out
