"""The Herb Tower cabinet, and where the gantry lands on it.

Everything here is the reference ("m") build out of `design/params.py`:
1397 wide, 457 deep, 1829 tall, 40-series V-slot, five rail levels.
The gantry occupies the rear 254 mm corridor; trays occupy the front 203 mm.

Coordinates, millimetres:
    x  0 .. 1397   left to right, seen from the front
    y  0 .. 457    y = 0 is the FRONT face of the cabinet
    z  0 .. 1829   floor to the top of the top rail
"""
import math

import numpy as np

from kit3d import extrude, merge, mv, rot, circle_pts, cylinder, box
import parts as P

# ------------------------------------------------------------------ cabinet
W, H = 1397.0, 1829.0
SER = 40.0                      # 4040 V-slot
#
# DEPTH. Rev A had D = 457 and it does not work: see clearances(). The
# tightest fold the real 280 mesh can reach is 162.6 mm long, measured, so
# the corridor has to swallow 162.6 mm of arm plus the 88.35 mm carriage
# stack behind it before the tray line. 559 gives 25 mm of daylight.
D = 559.0
D_REV_A = 457.0
SPAN_X = W - 2 * SER            # 1317 clear between the uprights
SPAN_Y = D - 2 * SER            # 479
LEVELS = [0.0, 304.8, 965.2, 1397.0, 1789.0]     # bottom z of each rail
TRAY_D = 203.0                  # trays occupy y 0 .. 203
CORRIDOR = D - TRAY_D           # gantry corridor behind them
TIERS = LEVELS[1:4]             # the three tray levels

# -------------------------------------------------------------- gantry fit
RAIL_L = 1397.0                 # X rail, CUT from the 1500 mm stick
RAIL_Z = 1709.0                 # bottom of the X rail (80 tall, under the top rail)
RAIL_Y = D - 2 * SER            # front face of the rear uprights
CARR_T = 6.0                    # gantry plate
MAST_L = 1500.0
MAST_Z0 = 289.0                 # mast foot. 309 left the top collar 0.5 mm under the cabinet top
ARM_PLATE_T = 6.35
MOUNT_OFF = 30.0
SCREW_Y = None   # set below, once MAST_Y0 is known                # g_base origin to the arm's bottom mounting face

# Depth build-up, front face to the arm's J1 axis. Each carriage stack is
# plate 6 plus the 1.115 its back stands off the beam (spacer + half a
# wheel, less the 10 mm the groove sits behind the face): P.CARR_STACK.
MAST_Y1 = RAIL_Y - P.CARR_STACK            # mast back face, on the X plate
MAST_Y0 = MAST_Y1 - P.CB_D                 # mast mouth
ZCARR_Y = MAST_Y0 - P.CARR_STACK           # Z carriage plate front face
ARMPL_Y = ZCARR_Y - ARM_PLATE_T            # arm plate front face
J1_Y = ARMPL_Y - MOUNT_OFF                 # J1 axis origin
SCREW_Y = MAST_Y0 + 10.0                   # channel centreline
CARR_T = P.PLATE_T


def xform(mesh, R, at_origin=True):
    """Apply an explicit 3x3 basis map, then drop the result's min corner to 0."""
    V, F = mesh
    V = V @ np.asarray(R, float).T
    if at_origin:
        V = V - V.min(0)
    return (V, F)


# Basis maps, written as "where each LOCAL axis goes in the world".
# A mesh column convention: R[:, i] is the world image of local axis i.
def _basis(ex, ey, ez):
    return np.array([ex, ey, ez], float).T


def vslot(length, s=SER, axis="z"):
    """A 40-series V-slot stick, `length` long. Section s x s in the other two."""
    n = 2
    half, t = s / 2.0, 8.0
    outer = np.array([(0, 0), (s, 0), (s, s), (0, s)], float)
    prof = []
    corners = [(0, 0), (s, 0), (s, s), (0, s)]
    for i in range(4):
        prof.append(corners[i])
        prof += P._vnotch(corners[i], corners[(i + 1) % 4], 1)
    m = extrude(np.array(prof), length, z0=0.0,
                holes=[circle_pts(4.1, 14, half, half)])
    if axis == "x":        # length along +x, section in y/z
        m = xform(m, _basis((0, 1, 0), (0, 0, 1), (1, 0, 0)))
    elif axis == "y":      # length along +y, section in x/z
        m = xform(m, _basis((1, 0, 0), (0, 0, 1), (0, 1, 0)))
    return m


def _band(a, b, lo, hi):
    """Intersect the interval [a, b) with [lo, hi); None if it misses."""
    a2, b2 = max(a, lo), min(b, hi)
    return (a2, b2) if b2 - a2 > 1e-6 else None


def cabinet(z0=0.0, z1=H, x0=0.0, x1=W):
    """The bare 4040 cabinet: 4 uprights, 13 width rails, 11 depth rails.

    The bounds TRIM the members rather than clipping triangles, so a detail
    view gets real shortened extrusion instead of a hollow shell. Anything
    a bound cuts through is "shown shortened" in the drawing.
    """
    out = []
    # uprights
    up = _band(0.0, H, z0, z1)
    for x in (0.0, W - SER):
        c = _band(x, x + SER, x0, x1)
        if up and c:
            out.append(mv(vslot(up[1] - up[0]), x, 0.0, up[0]))
            out.append(mv(vslot(up[1] - up[0]), x, D - SER, up[0]))
    # width rails: front, back, and the three carrying the tray's rear edge.
    # Nothing of the frame sits behind y = TRAY_D, or the arm cannot pass it.
    wx = _band(SER, W - SER, x0, x1)
    for z in LEVELS:
        if not (wx and _band(z, z + SER, z0, z1)):
            continue
        ys = [0.0, D - SER] + ([TRAY_D - SER] if z in TIERS else [])
        for y in ys:
            out.append(mv(vslot(wx[1] - wx[0], axis="x"), wx[0], y, z))
    # depth rails at every level, both sides, plus one in the base mid-span
    for z in LEVELS:
        if not _band(z, z + SER, z0, z1):
            continue
        xs = [0.0, W - SER] + ([W / 2 - SER / 2] if z == 0.0 else [])
        for x in xs:
            if _band(x, x + SER, x0, x1):
                out.append(mv(vslot(SPAN_Y, axis="y"), x, SER, z))
    return merge(*out) if out else (np.zeros((0, 3)), np.zeros((0, 3), int))


def trays(z0=0.0, z1=H, x0=0.0, x1=W):
    """Tray pans, 203 deep, one per tier. Drawn as 2 mm folded sheet."""
    out = []
    tx = _band(SER, W - SER, x0, x1)
    for z in TIERS:
        if tx and _band(z + SER, z + SER + 2.0, z0, z1):
            out.append(mv(box(tx[1] - tx[0], TRAY_D - 4, 2.0),
                          tx[0], 2.0, z + SER))
    return merge(*out) if out else (np.zeros((0, 3)), np.zeros((0, 3), int))


# --------------------------------------------------------------- the gantry
def x_rail(length=RAIL_L):
    """C-Beam across the rear uprights, channel opening forward.

    cbeam() is built with its 40 mm depth on local x (channel mouth at
    x = 40), its 80 mm height on local y, and its length on local z.
    Here depth goes to -y so the mouth faces the front of the cabinet,
    height goes to +z, and the length runs along x.
    """
    m = xform(P.cbeam(length), _basis((0, -1, 0), (0, 0, 1), (1, 0, 0)))
    return mv(m, 0.0, RAIL_Y, RAIL_Z)


def z_mast(length=MAST_L):
    """C-Beam hanging from the X carriage, channel opening forward."""
    return xform(P.cbeam(length), _basis((0, -1, 0), (1, 0, 0), (0, 0, 1)))


def mast_at(x):
    return mv(z_mast(), x - P.CB_H / 2, MAST_Y0, MAST_Z0)


def carriage_plate(x, z, y):
    """Gantry plate, face normal along y."""
    return mv(rot(P.gantry_plate(), rx=math.pi / 2), x, y + CARR_T, z)


def arm_plate_at(x, z):
    return mv(rot(P.arm_plate(), rx=math.pi / 2), x, ARMPL_Y + ARM_PLATE_T, z)


def arm_base_frame(x, z):
    """Transform taking the arm's g_base frame into cabinet coordinates.

    The arm is SIDE mounted: its J1 axis is horizontal and points forward
    (-y), so the 437 mm the arm stands when extended is reach into the tier,
    not height, and the base radius no longer eats into the reach.
    """
    T = np.eye(4)
    # Columns are where each local axis lands: +Z (the J1 axis) -> -y.
    T[:3, :3] = _basis((1, 0, 0), (0, 0, 1), (0, -1, 0))
    T[:3, 3] = (x, J1_Y, z)
    return T


def _bench_to_xrail(mesh):
    """Bench frame (x along, mouth at y = 40, z up) to the X rail in the
    cabinet: mouth at RAIL_Y facing the front, bottom at RAIL_Z."""
    V, F = mesh
    W_ = np.c_[V[:, 0], RAIL_Y + (40.0 - V[:, 1]), RAIL_Z + V[:, 2]]
    return (W_, F)


def _bench_to_mast(mesh, x_mast, z0=None):
    """Bench frame to the hanging Z mast: bench x (along) -> up from z0,
    bench y (depth) -> toward the back from the mouth, bench z -> across."""
    V, F = mesh
    z0 = MAST_Z0 if z0 is None else z0
    W_ = np.c_[x_mast + (V[:, 2] - 40.0), MAST_Y0 + (40.0 - V[:, 1]),
               z0 + V[:, 0]]
    return (W_, F)


def _map(parts, fn):
    from kit3d import Part as _Part
    return [_Part(fn(p.mesh), p.color, p.edges, p.alpha, p.ghost, p.ang, p.lw)
            for p in parts]


X_MIN = P.MMP_L + P.PLATE / 2 + 5.0                     # clear of the X motor plate
X_MAX = min(RAIL_L - 50.0 - 9.0 - 43.0 - 5.0,          # clamps clear of the idler
            W - SER - P.CB_H / 2)                       # mast clear of the side rails
X_TRAVEL = X_MAX - X_MIN


def gantry_parts(x=698.5, z=700.0, q=None, grid=0.0, hi=None,
                 mast=None, rail=True, xdrive=True):
    """Everything the gantry adds to the cabinet, placed, as kit3d Parts.

    Built from assy.py, the same sub-assemblies the bench pages draw. `x` is
    the carriage centre along the rail, `z` the arm's J1 height. `mast` as
    (z0, length) draws a shortened mast for a detail view."""
    import assy as AS
    from kit3d import Part, ALU, ALU_D, STEEL, BLACKPART, ARM, HILITE
    import arm280 as A

    def col(key, default):
        return HILITE if hi == key else default

    out = []
    if rail:
        out.append(Part(x_rail(), col("rail", ALU)))
        out += _map(AS.carriage(x, clamp_holes=True), _bench_to_xrail)
        if xdrive:
            out += _map(AS.x_motor_plate() + AS.x_motor() + AS.x_pulley()
                        + AS.x_idler(RAIL_L) + AS.x_belt(RAIL_L, x)
                        + AS.x_clamps(x), _bench_to_xrail)
    mz0, mlen = mast if mast else (MAST_Z0, MAST_L)
    zc = z - mz0                                    # carriage along the mast
    bench = [Part(AS.rail(mlen), col("mast", ALU))]
    bench += AS.carriage(zc, hi="plate" if hi == "zcar" else None)
    bench += AS.z_screw(mlen, hi=hi == "screw") + AS.z_nut(zc)
    if mast is None:
        bench += AS.z_end_plate(0.0, True) + AS.z_motor(hi="motor" if hi == "zmotor" else False)
        bench += AS.z_end_plate(mlen, False) + AS.z_top_bearings(mlen)
    out += _map(bench, lambda m: _bench_to_mast(m, x, mz0))
    out.append(Part(arm_plate_at(x, z), col("armplate", ALU_D)))
    T = arm_base_frame(x, z)
    LC = {"g_base": ALU_D, "joint1": BLACKPART, "joint2": ARM, "joint3": ARM,
          "joint4": ARM, "joint5": ARM, "joint6": ARM, "joint6_flange": BLACKPART}
    for name, (V, F) in A.pose(q if q is not None else TIGHT_Q, grid=grid):
        Vw = (np.hstack([V, np.ones((len(V), 1))]) @ T.T)[:, :3]
        out.append(Part((Vw, F), col("arm", LC[name]), ang=33, lw=0.4))
    return out


# The two numbers below are measured off the official mesh, not quoted from
# a datasheet. TIGHT_Q is the shortest fold that is COLLISION FREE: found by
# ranking 83,607 poses by length and voxel-checking every link pair two or
# more apart in the chain (collide.py), then confirmed on the full 226,670
# face mesh. Rev C's first answer, (0, -135, -150, -150, 0, 0), was shorter
# only on paper: it drives J4 through the base. FOLD_L is set by the shoulder
# housing itself (joints 2 and 3 top out at 162.48 / 162.55), so no fold of
# any kind gets under it.
TIGHT_Q = (0, -110, -80, -140, -90, 0)
FOLD_L = 162.6
REACH_R = 292.6                 # flange, from the J1 axis. Gripper adds ~90.
GRIPPER = 90.0


def clearances(depth=None):
    """Every gap the gantry install depends on, in millimetres.

    Positive is daylight. Run this before cutting extrusion: `transit` going
    negative is the one that cannot be fixed with a shim.
    """
    d = D if depth is None else depth
    rail_y = d - 2 * SER
    j1 = (rail_y - P.CARR_STACK - P.CB_D - P.CARR_STACK - ARM_PLATE_T
          - MOUNT_OFF)
    return {
        "depth": d,
        "rail_y": rail_y,
        "j1_y": j1,
        "transit": (j1 - FOLD_L) - TRAY_D,
        "flange_front": j1 - REACH_R,
        "gripper_front": j1 - REACH_R - GRIPPER,
        "x_travel": X_TRAVEL,
        "x_min": X_MIN,
        "x_max": X_MAX,
    }


# ------------------------------------------------------------- the cut list
def members():
    """Every 4040 member in the cabinet, as (length, qty, what it is)."""
    return [
        (H,       4,  "uprights"),
        (SPAN_X, 10,  "width rails, front and back at all five levels"),
        (SPAN_X,  3,  "width rails carrying the tray's rear edge"),
        (SPAN_Y, 10,  "depth rails at all five levels, both sides"),
        (SPAN_Y,  1,  "depth rail, base mid-span"),
    ]


def cutlist(stock=2000.0, kerf=3.0):
    """Pack the members into sticks of `stock`, longest first."""
    want = []
    for L, n, _ in members():
        want += [L] * n
    want.sort(reverse=True)
    sticks = []
    for L in want:
        for s in sticks:
            if s["left"] >= L + kerf:
                s["cuts"].append(L)
                s["left"] -= L + kerf
                break
        else:
            sticks.append({"cuts": [L], "left": stock - L - kerf})
    return sticks


def cut_report(stock=2000.0):
    out = []
    tot = sum(L * n for L, n, _ in members())
    out.append(f"cabinet {W:.0f} x {D:.0f} x {H:.0f}, 4040 V-slot")
    for L, n, what in members():
        out.append(f"  {n:3d} x {L:7.1f}   {what}")
    out.append(f"  total 4040: {tot/1000:.2f} m")
    sticks = cutlist(stock)
    pat = {}
    for s in sticks:
        k = tuple(sorted(s["cuts"], reverse=True))
        pat[k] = pat.get(k, 0) + 1
    out.append(f"  from {stock:.0f} mm stock: {len(sticks)} sticks")
    for k, n in sorted(pat.items(), key=lambda kv: -kv[1]):
        drop = stock - sum(k) - 3.0 * len(k)
        out.append("    %2d x [ %s ]  drop %.0f" %
                   (n, " + ".join(f"{v:.0f}" for v in k), drop))
    return "\n".join(out)
