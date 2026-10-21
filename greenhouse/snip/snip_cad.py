"""Herb Snip Rev A: the Maag cut-and-hold end effector for the myCobot 280.

Every printed part is built here as a signed-distance solid (sdf.py) and meshed
for printing. The purchased parts it fits are modelled from their makers'
data: Elephant Robotics' end flange mesh (LEGO holes measured off joint7.dae),
Intel's D405 mesh and its two M3 back holes, the TowerPro MG90S datasheet, the
9 mm snap-off blade.

TOOL FRAME (mm): origin on the flange's outer face, +z out along the tool,
y along the jaw pivot axis, x the direction the moving jaw opens. The flange's
LEGO grid lies on the x and y axes.
"""
from __future__ import annotations
import math
import numpy as np
import sdf as S

# ------------------------------------------------------------- linkage (linkage.py)
P = np.array([4.0, 62.0])              # jaw pivot (x, z)
SV = P + np.array([2.25, -17.86])      # servo output shaft (x, z)
A_CRANK, B_LINK, C_TAIL = 11.27, 14.73, 14.51
BETA = math.radians(7.2)
BRANCH = -1.0
T0 = P + C_TAIL * np.array([math.sin(BETA), -math.cos(BETA)])   # tail pin, jaws closed

# ------------------------------------------------------------- layers along y
JAW = (-3.0, 3.0)          # jaw plates; the blade sits at y -0.38 .. 0
CHEEK = (-8.0, -3.0)       # the body's single pivot cheek
LUG = (3.0, 6.0)           # moving-jaw tail lug
LINK = (6.3, 9.3)
CRANK = (9.6, 13.6)
HORN = (11.7, 13.6)        # MG90S single-arm horn arm, in the crank's pocket; hub to 17.1
SERVO_TOP = 17.6           # servo case top (the face the shaft comes out of)
SERVO_H = 22.7             # case height below the top
TAB = (23.0, 25.5)         # mounting tabs
PAD = (3.0, 9.0)           # pad ribs on both jaws, z >= 72
LEDGE = (20.0, TAB[0])     # servo ledge under the tabs
C_TABS = 18.0              # ledge half-length along z

# ------------------------------------------------------------- jaw geometry, closed
ANVIL_X = 0.0              # anvil face: the cut line, on the tool axis
FJ_X = (-10.0, 0.0)
MJ_EDGE = 1.2              # moving-jaw inner edge
MJ_BACK = 14.5             # its back: room for the clamp screw's insert behind the blade
# OLFA AB 9 mm snap-off blade, 0.38 thick, a piece with about 34 of cutting edge. Its
# ends are the score lines, so the piece is a parallelogram; OLFA does not publish
# the score angle, so the pocket takes any angle from 52 to 68 degrees (nominal 59).
BLADE = dict(x0=-0.3, h=9.0, z0=70.5, z1=104.5, t=0.38, ang=59.0, ang_lo=52.0, ang_hi=68.0, slack=1.0,
             proud=0.08)
TIP_Z = 107.5
ROOT_R = 7.0               # moving-jaw root disc around the pivot
ROOT_CLEAR = 7.6
FJ_RIB_EDGE = -1.2         # the pad ribs' faces, closed: 3.6 apart
MJ_RIB_EDGE = 2.4
PAD_Z = (72.0, 105.0)

# ------------------------------------------------------------- form
R_EDGE = 0.6               # every outside edge of the tool's printed parts
R_SMALL = 0.4              # the link, the crank and the pads
K_FILLET = 2.5             # fillets in the profiles, where a wall meets a boss or a rib

# ------------------------------------------------------------- fasteners, all flush
# Pivot: a shoulder screw (ISO 7379 pattern, Ganter GN 7379 / ELESA: 4 shoulder, M3, head 7 x 3,
# 2 hex, thread listed as 7). The shoulder's end clamps on a heat-set insert in the cheek; the jaw
# turns on the shoulder between the cheek and the head, which sits flush in a counterbore in jaw
# B's lug. The cheek's camera side is a closed hub over the thread's end.
SHOULDER = dict(d=4.0, L=6.0, head_d=7.0, head_k=3.0, s=2.0, thread=7.0)
INSERT_M3 = dict(od=4.6, L=5.7, hole=4.0)       # heat-set, pressed in from the jaw side
INSERT_M2 = dict(od=3.6, L=3.0, hole=3.2)       # heat-set, pressed into jaw B from outside
CB_FLOOR = SHOULDER["L"] + JAW[0] - 0.2         # counterbore floor y: 0.2 of axial play
HUB = (-11.0, 4.4)                              # the cheek's hub: its face (y) and radius
CLAMP = (11.5, 88.0)                            # the one blade-clamp screw, (x, z) on the jaw
CSK_M2 = (2.25, 1.15)                           # 90 deg countersink: mouth radius, hole radius
CSK_M3 = (3.45, 1.65)
CAM_PLATE = 3.0                                 # the camera bracket's plate: countersunk M3 x 5

# ------------------------------------------------------------- the pads: TPU 95A, printed
# One part, printed twice: a dovetail base that slides into each rib from the servo side (+y),
# and a comb of fins slanted toward the jaw root. The fins bend around a stem and seat it between
# them; a cut piece pulled toward the tips straightens them into it. 2.2 proud of the rib, as the
# foam rod was, so the pads still close on the stem before the blade does. The dovetail is steeper
# at the tip end than at the root end, so a pad only goes in with its fins slanted toward the root.
PADT = dict(y=(3.1, 8.9), slot=5.0, base=1.4, z=(74.0, 103.0), dove=(0.5, 1.0), t=0.8, pitch=2.35, n=11,
            root0=77.7, ang=35.0, proud=2.2, clear=0.05, E=26.0)

# ------------------------------------------------------------- base and flange
BASE_R = 19.2
BASE_T = 8.0               # LEGO pin bosses
BASE_DISC = 5.0
LEGO = [(11.25, 0.0), (-11.25, 0.0), (0.0, 11.25), (0.0, -11.25)]
LEGO_D = 4.85
LEGO_CB = (6.4, 0.6)

# ------------------------------------------------------------- servo (MG90S datasheet)
SERVO_L, SERVO_W = 22.8, 12.2
SHAFT_FROM_END = 6.0
TAB_SPAN = 32.2
TAB_HOLE = 27.8
SERVO_X = (SV[0] - SERVO_W / 2, SV[0] + SERVO_W / 2)
SERVO_Z = (SV[1] + SHAFT_FROM_END - SERVO_L, SV[1] + SHAFT_FROM_END)

# ------------------------------------------------------------- D405 placement
CAM_TILT = 20.0            # optical axis tilted toward +y
CAM_G = np.array([0.0, -40.0, 26.0])   # glass centre


def cam_R():
    """Columns: where the camera mesh's x, y, z axes land in the tool frame.
    Mesh +z is the view direction, +x the USB-C face (-> tool -x), +y the top."""
    t = math.radians(CAM_TILT)
    ez = np.array([0.0, math.sin(t), math.cos(t)])
    ex = np.array([-1.0, 0.0, 0.0])
    ey = np.cross(ez, ex)
    return np.stack([ex, ey, ez], 1)


# =====================================================================
def _in_layer(poly, layer):
    return S.prism(poly, "y", *layer)


def _cyl_y(xz, r, layer):
    return S.cyl((xz[0], 0.0, xz[1]), r, "y", *layer)


def _yx(g, layer, r=R_EDGE, sharp=(False, False), cove=0.0):
    return S.extrude(g, "y", layer[0], layer[1], r, sharp, cove)


def _rect(x0, z0, x1, z1, r=0.0):
    """A rectangle profile, its corners rounded by r."""
    return S.p_poly(S.rpoly([(x0, z0, r), (x1, z0, r), (x1, z1, r), (x0, z1, r)]))


# --------------------------------------------------------------- the pads
def _pad_x(x, flip):
    """x on the fixed jaw's rib, or its mirror on the moving jaw's (the pads are one part turned
    half a turn about z between the two ribs)."""
    return (FJ_RIB_EDGE + MJ_RIB_EDGE) - x if flip else x


def pad_fins():
    """Each fin's centre line, root to tip, on the fixed jaw: [(A, B)]."""
    T = PADT
    xb1 = FJ_RIB_EDGE - T["slot"] + T["base"]
    xt = FJ_RIB_EDGE + T["proud"] - T["t"] / 2                 # the tip's centre: the round ends at the proud line
    a = math.radians(T["ang"]); u = np.array([math.cos(a), -math.sin(a)])
    out = []
    for i in range(T["n"]):
        A = np.array([xb1, T["root0"] + i * T["pitch"]])
        L = (xt - xb1) / u[0]
        out.append((A - 0.6 * u, A + L * u))
    return out


def pad_profile():
    """The pad in (x, z), as it sits in the fixed jaw's rib: a dovetail base along the bottom of
    the slot and the fins from it, filleted at their roots."""
    T = PADT
    xb0 = FJ_RIB_EDGE - T["slot"]; xb1 = xb0 + T["base"]
    z0, z1 = T["z"]; d0, d1 = T["dove"]
    base = S.p_poly(S.rpoly([(xb0, z0, 0.3), (xb0, z1, 0.3), (xb1, z1 - d1, 0.3), (xb1, z0 + d0, 0.3)]))
    fins = [S.p_capsule(A, B, T["t"] / 2) for A, B in pad_fins()]
    return S.p_blend(0.5, base, *fins)


def tpu_pad():
    """One pad, TPU 95A, as it sits on the fixed jaw. The moving jaw's is the same part, turned
    half a turn about z (PAD_FLIP)."""
    return S.extrude(pad_profile(), "y", *PADT["y"], r=0.3)


PAD_FLIP = (np.diag([-1.0, -1.0, 1.0]), np.array([FJ_RIB_EDGE + MJ_RIB_EDGE, PAD[0] + PAD[1], 0.0]))


def pad_slot(flip=False):
    """The slot in a rib that the pad's base slides into from +y: the dovetail at the bottom, then
    straight out through the rib's face. Closed at y 3 by the jaw plate."""
    T = PADT; c = T["clear"]
    xb0 = FJ_RIB_EDGE - T["slot"]; xb1 = xb0 + T["base"]
    z0, z1 = T["z"]; d0, d1 = T["dove"]; xo = FJ_RIB_EDGE + 0.6
    pts = [(xb0 - c, z0 - c), (xb0 - c, z1 + c), (xb1, z1 - d1 + c), (xo, z1 - d1 + c), (xo, z0 + d0 - c),
           (xb1, z0 + d0 - c)]
    pts = [(_pad_x(x, flip), z) for x, z in pts]
    return S.prism(np.array(pts), "y", PAD[0], PAD[1] + 1.0)


# --------------------------------------------------------------- body
def fj_profile():
    """The fixed jaw and the spine under it, in (x, z), in the jaw layer: a straight inner edge
    on the anvil, a rounded tip and a long round back."""
    return S.p_poly(S.rpoly([(-10.0, BASE_DISC), (1.0, BASE_DISC), (1.0, 53.5), (0.0, 55.5), (0.0, TIP_Z, 1.2),
                             (-10.0, TIP_Z, 6.0)]))


def cheek_profile():
    """The cheek layer: the spine and the disc round the pivot, filleted where they meet."""
    return S.p_blend(K_FILLET, _rect(-10.0, BASE_DISC, 1.0, 62.0, 0.0), S.p_circle(P, 8.0))


def fj_rib_profile():
    return S.p_poly(S.rpoly([(-10.0, 68.0), (FJ_RIB_EDGE, 71.5, 1.0), (FJ_RIB_EDGE, 105.4, 1.0), (-3.0, 107.3),
                             (-10.0, 107.3, 5.8)]))


# ------------------------------------------------------------- the housing
# One block from the flange up: a round collar on the flange with a band cut into it, a waist
# that eases into a rounded housing round the servo and the linkage, and a deck the jaws stand on.
# The crank, link and lug move in a cavity cut to their own swept shapes; two ports show the link
# (and let a finger guide it onto the crank's dowel) and let the horn's arm pass the wall.
HOUSING = dict(x=(-13.0, 21.0), y=(-9.0, 42.0), rc=9.0, rc0=3.0, top=58.0, rtop=5.0, waist=(6.0, 21.0))
SPLIT = 2.4                               # the camera ring below, the body above: both print without supports
BAND = (SPLIT - 0.5, SPLIT + 0.5, 0.5)    # the collar's band, on the line between them: z from, z to, depth
RING_X = 21.0                             # the chin and the camera's plate, each side: the D405's own width.
                                          # +x is flush with the housing's flat side: the ring prints on that face
PHIS = np.radians(np.arange(0.0, 58.01, 1.0))      # 55 opens it fully; 3 of margin
SWEEP_GROW = 0.8                          # clearance round every moving part's swept shape
WINDOW_X = (SERVO_X[0] - 0.25, SERVO_X[1] + 0.55)   # the servo goes in crank first: the crank's tip passes here
REG_BAY = dict(x=(15.85, 23.0), y=(26.2, 39.8), z=(28.65, 47.35))   # 0.45 round the board, corners 0.3
LANE = dict(x=17.7, y=(30.0, 35.6), z=(13.5, 31.0), bar=(19.0, 20.7, 18.5, 21.5))   # the cable lane under the bay
THROAT = [(0.0, -3.0), (30.0, -3.0), (30.0, 3.3), (17.0, 3.3), (17.0, 17.6), (-7.0, 17.6), (-7.0, 2.7),
          (0.0, 2.7)]                     # the jaw's plane runs out through the +x face: it swings out there                     # the deck's one opening, in plan: the jaw's nest, the lug and link, the crank


def housing_plan():
    (x0, x1), (y0, y1) = HOUSING["x"], HOUSING["y"]; r, r0 = HOUSING["rc"], HOUSING["rc0"]
    return S.p_poly(S.rpoly([(x0, y0, r0), (x1, y0, r), (x1, y1, r), (x0, y1, r)]))


def base_footprint():
    """The collar in plan (x, y): round on the flange, long toward the servo, filleted between, and
    flat on +x where the blend would bulge past the housing's side: one plane from the flange face
    to the deck there, the face the camera ring prints on."""
    x1 = HOUSING["x"][1]
    return S.p_inter(S.p_blend(6.0, S.p_circle((0, 0), BASE_R), housing_plan()),
                     S.p_poly([(-80.0, -80.0), (x1, -80.0), (x1, 80.0), (-80.0, 80.0)]))


def housing():
    return S.loft(base_footprint(), housing_plan(), 0.0, HOUSING["top"], *HOUSING["waist"], r=HOUSING["rtop"])


def _jaw_mats(phis=PHIS):
    return [jaw_R(p) for p in phis]


def _crank_mats():
    th = [crank_angle(p) for p in PHIS]
    th = np.r_[th[0] - math.radians(4), th, th[-1] + math.radians(4)]
    return [np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]]) for t in th]


def crank_horn_profile():
    """The crank and the horn's arm and hub, along +x from the shaft (the parts' own frame)."""
    crank_ = S.p_blend(1.5, S.p_circle((0, 0), 5.2), S.p_capsule((0, 0), (A_CRANK, 0), 3.4))
    horn = S.p_union(S.p_poly([(0, -3.0), (16.0, -2.1), (16.0, 2.1), (0, 3.0)]), S.p_circle((0, 0), 3.7))
    return S.p_union(crank_, horn)


def link_sweep():
    caps = []
    for p in PHIS:
        T = P + jaw_R(p) @ (T0 - P)
        th = crank_angle(p)
        Cp = SV + A_CRANK * np.array([math.cos(th), math.sin(th)])
        caps.append(S.p_capsule(T, Cp, 3.0 + SWEEP_GROW))
    return S.p_cache(S.p_union(*caps), step=0.05)


def mj_pad_profile():
    """The moving jaw's pad in its own (x, z), closed: the fixed jaw's pad mirrored across the gap."""
    g = pad_profile()
    m = FJ_RIB_EDGE + MJ_RIB_EDGE
    h = lambda Q: g(np.c_[m - Q[:, 0], Q[:, 1]])
    lo, hi = np.asarray(g.bounds[0]), np.asarray(g.bounds[1])
    h.bounds = (np.array([m - hi[0], lo[1]]), np.array([m - lo[0], hi[1]]))
    return h


import functools


@functools.lru_cache(maxsize=1)
def cavity():
    """Everything the moving parts sweep, each in its own layer, grown by SWEEP_GROW, and the ways
    the jaw (from above) and the servo (from the back) come in."""
    g = SWEEP_GROW
    jaw_sw = S.p_sweep(mj_profile(), _jaw_mats(), P, P, grow=0.6, step=0.06)
    lug_sw = S.p_sweep(mj_lug_profile(), _jaw_mats(), P, P, grow=g, step=0.06)
    rib_sw = S.p_sweep(S.p_union(mj_rib_profile(), mj_pad_profile()), _jaw_mats(), P, P, grow=g, step=0.06)
    link_sw = link_sweep()
    crank_sw = S.p_sweep(crank_horn_profile(), _crank_mats(), SV, (0.0, 0.0), grow=g, step=0.06)
    nest = S.p_union(jaw_sw, S.p_poly([(0.0, 54.0), (16.0, 54.0), (16.0, 120.0), (0.0, 120.0)]))
    out = [
        # the moving jaw's nest, from the cheek's face (the jaw bears on it there) to past jaw B
        S.extrude(nest, "y", JAW[0], JAW[1] + 0.3),
        # each swept, and each raised from where it sits closed: the jaw comes down from above
        S.extrude(S.p_union(lug_sw, S.p_rise(S.p_offset(mj_lug_profile(), g), 40.0)), "y", LUG[0] - 0.3, LUG[1] + 0.3),
        S.extrude(rib_sw, "y", PAD[0] - 0.3, PAD[1] + 0.6),
        S.extrude(S.p_union(link_sw, S.p_rise(S.p_capsule(T0, SV + A_CRANK * np.array([math.cos(crank_angle(0.0)),
                                                                                         math.sin(crank_angle(0.0))]),
                                                          3.0 + g), 40.0)), "y", LINK[0] - 0.3, LINK[1] + 0.3),
        S.extrude(crank_sw, "y", CRANK[0] - 0.3, SERVO_TOP - 0.2),
        S.cyl((SV[0], 0, SV[1]), 6.4, "y", SERVO_TOP - 4.4, SERVO_TOP + 0.5),       # the servo's boss
        # the servo's case, from the cavity out through the back, and its tabs' way in
        S.box((WINDOW_X[0], CRANK[0] - 0.3, SERVO_Z[0] - 0.25), (WINDOW_X[1], 60.0, SERVO_Z[1] + 0.25)),
        S.box((SERVO_X[0] - 0.3, TAB[0], (SERVO_Z[0] + SERVO_Z[1]) / 2 - TAB_SPAN / 2 - 0.3),
              (SERVO_X[1] + 0.3, 60.0, (SERVO_Z[0] + SERVO_Z[1]) / 2 + TAB_SPAN / 2 + 0.3)),
    ]
    # a 0.4 relief in the cheek's face wherever the jaw swings, outside the disc it bears on
    away = lambda Q: np.maximum(jaw_sw(Q), -(np.hypot(Q[:, 0] - P[0], Q[:, 1] - P[1]) - (ROOT_R + 1.2)))
    away.bounds = jaw_sw.bounds
    out.append(S.extrude(away, "y", JAW[0] - 0.4, JAW[0] + 0.1))
    return out, jaw_sw


def ports():
    """The openings in the housing, each with its rim rounded: the deck's one opening where the
    jaw, its lug and link and the crank move; a porthole on -x over the link, to see and guide it
    onto the crank's dowel; a window on +x where the horn's arm swings past the wall; the servo's
    way in at the back; the regulator's bay and the cable lane under it on +x."""
    zc = (SERVO_Z[0] + SERVO_Z[1]) / 2
    throat = S.extrude(S.p_poly(S.rpoly([(x, y, 2.5) for x, y in THROAT])), "z", 50.5, 90.0, cache=False)
    port_mx = S.extrude(S.p_capsule((8.0, 39.0), (8.0, 47.0), 4.2), "x", -30.0, -6.0, cache=False)
    port_px = S.extrude(S.p_capsule((13.4, 40.0), (13.4, 48.3), 4.4), "x", 14.0, 40.0, cache=False)
    back = S.box((SERVO_X[0] - 0.3, 30.0, zc - TAB_SPAN / 2 - 0.3), (SERVO_X[1] + 0.3, 60.0, zc + TAB_SPAN / 2 + 0.3))
    b = REG_BAY
    bay = S.box((b["x"][0], b["y"][0], b["z"][0]), (b["x"][1], b["y"][1], b["z"][1]), r=0.3)
    L = LANE
    yl = (L["y"][0] + L["y"][1]) / 2; rl = (L["y"][1] - L["y"][0]) / 2
    lane = S.extrude(S.p_capsule((yl, L["z"][0] + rl), (yl, L["z"][1]), rl), "x", L["x"], 40.0, cache=False)
    return [(throat, 1.5), (port_mx, 1.5), (port_px, 1.5), (back, 1.2), (bay, 0.8), (lane, 0.8)]


def band():
    """The band round the collar, half in the ring and half in the body: the line between them."""
    fp = S.p_cache(base_footprint())
    band_g = lambda Q: np.maximum(-(fp(Q) + BAND[2]), fp(Q) - 6.0)
    band_g.bounds = (np.asarray(fp.bounds[0]) - 6.0, np.asarray(fp.bounds[1]) + 6.0)
    return S.extrude(band_g, "z", BAND[0], BAND[1], cache=False)


def camera_ring():
    """The camera's ring: the bottom of the collar, from the flange face to SPLIT, and one curved
    chin out to the D405's plate. It lies between the flange and the body on the same four LEGO
    pins. The collar's flat side, the chin and the plate meet one plane at x = +RING_X: it prints
    lying on that face, its edges there square."""
    Rc = cam_R()
    back = CAM_G - 23.0 * Rc[:, 2]
    disc = S.extrude(base_footprint(), "z", 0.0, SPLIT, 0.0)
    bed = S.box((-80.0, -80.0, -80.0), (RING_X, 80.0, 80.0))
    plate = S.inter(S.transform(S.box((-RING_X - 1.5, -13.0, -CAM_PLATE), (RING_X, 15.0, 0.0), r=1.5), Rc, back),
                    bed)
    chin_p = S.p_poly(S.rpoly([(-14.0, SPLIT), (-14.0, -1.0), (-20.0, -7.0, 4.0), (-46.0, -8.5, 4.0),
                               (-52.0, -1.5, 3.0), (-50.0, 1.9, 1.0), (-36.7, -2.9, 2.0), (-28.6, -3.2, 3.0),
                               (-22.6, 0.6, 2.0), (-20.2, SPLIT)]))
    chin = S.extrude(chin_p, "x", -RING_X, RING_X, 2.5, sharp=(False, True))
    solid = S.union(disc, plate, chin)
    cuts = []
    for x, y in LEGO:
        cuts.append(S.cyl((x, y, 0), LEGO_D / 2, "z", -1.0, SPLIT + 1.0))
        cuts.append(S.cyl((x, y, 0), LEGO_CB[0] / 2, "z", -1.0, LEGO_CB[1]))
    cuts.append(S.transform(S.box((-21.4, -21.4, -23.4), (21.4, 21.4, 0.4), r=2.4), Rc, CAM_G))
    for sx in (-10.0, 10.0):
        cuts.append(S.transform(S.cyl((sx, 0.0, 0.0), CSK_M3[1], "z", -6.0, 1.0), Rc, back))
        cuts.append(S.transform(S.cone((sx, 0.0, 0.0), CSK_M3[0], CSK_M3[1], "z", -CAM_PLATE - 0.01,
                                       -CAM_PLATE + CSK_M3[0] - CSK_M3[1]), Rc, back))
        cuts.append(S.transform(S.cyl((sx, 0.0, 0.0), 2.9, "z", -12.0, -CAM_PLATE - 0.005), Rc, back))
    cuts.append(S.cyl((0, 0, 0), 19.6, "z", -20.0, 0.0))             # nothing below the flange face inside it
    cuts.append(S.extrude(base_footprint(), "z", SPLIT, 200.0))       # nothing over the collar above the split:
                                                                      # that is the body. The plate stands clear of it
    out = S.diff(solid, *cuts)
    return S.smooth_diff(out, band(), 0.25)


def body():
    rE = R_EDGE
    zc = (SERVO_Z[0] + SERVO_Z[1]) / 2
    top = HOUSING["top"]
    # ---- the housing, its band, the column and the cheek that rise from its deck
    block = housing()
    cheek = _yx(cheek_profile(), CHEEK, rE, sharp=(False, True))
    jaw = _yx(fj_profile(), JAW, rE)
    seam = S.extrude(S.p_inter(cheek_profile(), fj_profile()), "y", JAW[0] - rE, JAW[0] + rE)
    hub = S.union(S.rcyl((P[0], 0, P[1]), HUB[1], "y", HUB[0], CHEEK[0] + 1.0, 0.8, sharp=(False, True)),
                  S.inter(S.extrude(S.p_circle(P, HUB[1]), "y", HUB[0], CHEEK[0], 0.8, cove=1.2, cove_at=1),
                          _yx(cheek_profile(), (CHEEK[0] - 2.0, CHEEK[0] + 1.0), 0.0)))
    rib = _yx(fj_rib_profile(), (JAW[1] - rE, PAD[1]), rE, sharp=(True, False))
    # a fillet where the column and the cheek's disc stand on the deck (trimmed off the deck's rim)
    stand = S.p_union(S.p_poly(S.rpoly([(-10.0, -8.0), (1.0, -8.0), (1.0, JAW[1]), (-10.0, JAW[1])])),
                      S.p_poly([(-3.4, -8.0), (11.4, -8.0), (11.4, CHEEK[1]), (-3.4, CHEEK[1])]))
    deck = S.extrude(S.p_offset(housing_plan(), -HOUSING["rtop"]), "z", top - 1.0, top + 4.0)
    foot = S.inter(S.extrude(stand, "z", top, top + 3.0, 0.0, cove=2.5), deck)
    solid = S.union(block, cheek, jaw, seam, hub, rib, foot)

    cav, jaw_sw = cavity()
    cuts = list(cav)
    cuts.append(_cyl_y(P, ROOT_CLEAR, (JAW[0] - 0.01, JAW[1] + 0.01)))
    # anvil pocket
    cuts.append(S.box((-2.6, -2.1, 69.8), (0.01, 2.1, 105.6)))
    # the pad's slot in the rib
    cuts.append(pad_slot())
    # the pivot: the M3 insert from the jaw side, then room for the shoulder screw's thread, blind
    cuts.append(_cyl_y(P, INSERT_M3["hole"] / 2, (JAW[0] - INSERT_M3["L"] - 0.2, JAW[0] + 0.01)))
    cuts.append(_cyl_y(P, 1.6, (JAW[0] - SHOULDER["thread"] - 0.4, JAW[0])))
    # tab screw pilots through the ledge the tabs sit on (slotted +/-1 along z), screwed from the back
    for dz in (-TAB_HOLE / 2, TAB_HOLE / 2):
        cuts.append(S.prism(S.stadium((SV[0], zc + dz - 1.0), (SV[0], zc + dz + 1.0), 0.8),
                            "y", TAB[1] - 9.0, TAB[0] + 1.0))                 # deep enough for the 8 long screws
    # the servo lead's way out, under the case's end, to the back face
    cuts.append(S.box((3.0, 33.0, SERVO_Z[0] - 4.0), (9.5, 60.0, SERVO_Z[0] + 0.5), r=0.8))
    # LEGO pin holes
    for x, y in LEGO:
        cuts.append(S.cyl((x, y, 0), LEGO_D / 2, "z", -1.0, BASE_T + 1.0))
        cuts.append(S.cyl((x, y, 0), LEGO_CB[0] / 2, "z", -1.0, LEGO_CB[1]))
    # the camera itself, dilated 0.4
    Rc = cam_R()
    cuts.append(S.transform(S.box((-21.4, -21.4, -23.4), (21.4, 21.4, 0.4), r=2.4), Rc, CAM_G))
    out = S.diff(S.inter(solid, S.box((-80, -80, SPLIT), (80, 80, 200))), *cuts)
    # the band, the ports, with their rims rounded
    out = S.smooth_diff(out, band(), 0.25)
    for p_, k in ports():
        out = S.smooth_diff(out, p_, k)
    # the tie bar across the cable lane, just under the face
    t0, t1, z0_, z1_ = LANE["bar"]
    out = S.union(out, S.box((t0, LANE["y"][0] - 0.3, z0_), (t1, LANE["y"][1] + 0.3, z1_), r=0.5))
    return out


# --------------------------------------------------------------- moving jaw
def mj_profile():
    """Both halves' outline in (x, z), closed: a straight inner edge, the same rounded tip as the
    fixed jaw, a long round back, and the root disc round the pivot, filleted into it."""
    plate = S.p_poly(S.rpoly([(MJ_EDGE, 64.0), (MJ_EDGE, TIP_Z, 1.2), (MJ_BACK, TIP_Z, 7.5), (MJ_BACK, 64.0, 3.0)]))
    disc = S.p_circle(P, ROOT_R)
    # the fillet only behind the inner edge: in front of it the fixed jaw closes past the root
    keep = S.p_union(S.p_poly([(MJ_EDGE, 40.0), (40.0, 40.0), (40.0, 130.0), (MJ_EDGE, 130.0)]), disc)
    return S.p_inter(S.p_blend(K_FILLET, plate, disc), keep)


def mj_outline():
    """The outline as a polygon (drawings only)."""
    return np.array([(MJ_EDGE, 66.0), (MJ_EDGE, 104.0), (3.0, TIP_Z), (7.0, TIP_Z - 0.6),
                     (MJ_BACK, 99.0), (MJ_BACK, 66.0)])


def blade_offset(ang):
    """How far the back of the piece sits below its cutting edge, for a score angle."""
    return BLADE["h"] / math.tan(math.radians(ang))


def blade_outline(ang=None):
    """The snapped piece in (x, z): cutting edge on x0, back on x0 + h, ends along the score lines."""
    b = BLADE; o = blade_offset(b["ang"] if ang is None else ang)
    xe, xb = b["x0"], b["x0"] + b["h"]
    return np.array([(xe, b["z0"]), (xe, b["z1"]), (xb, b["z1"] - o), (xb, b["z0"] - o)])


def blade_pocket():
    """A pocket any piece from ang_lo to ang_hi drops into, with slack at each end; it is
    0.08 shallower than the blade, so the clamp screw pinches it."""
    b = BLADE; s_ = b["slack"]
    xe, xb = b["x0"] - 1.0, b["x0"] + b["h"] + 0.3
    return np.array([(xe, b["z0"] - s_), (xe, b["z1"] + s_),
                     (xb, b["z1"] - blade_offset(b["ang_hi"]) + s_), (xb, b["z0"] - blade_offset(b["ang_lo"]) - s_)])


def _shoulder_bore(y0, y1):
    return _cyl_y(P, SHOULDER["d"] / 2 + 0.08, (y0, y1))


def mj_half_a():
    """Camera-side half: the blade's pocket, and the clamp screw's countersink, flush."""
    plate = _yx(mj_profile(), (JAW[0], 0.0), R_EDGE, sharp=(False, True))
    cx, cz = CLAMP
    cuts = [_shoulder_bore(JAW[0] - 1, 1),
            S.prism(blade_pocket(), "y", -(BLADE["t"] - BLADE["proud"]), 0.5),
            S.cyl((cx, 0, cz), CSK_M2[1], "y", JAW[0] - 1, 1),
            S.cone((cx, 0, cz), CSK_M2[0], CSK_M2[1], "y", JAW[0] - 0.01, JAW[0] + CSK_M2[0] - CSK_M2[1])]
    return S.diff(plate, *cuts)


def mj_lug_profile():
    """The lug in (x, z): the tail to the link and the round boss that takes the pivot's head."""
    return S.p_blend(K_FILLET, S.p_capsule(P, T0, 3.6), S.p_circle(P, SHOULDER["head_d"] / 2 + 1.5))


def mj_rib_profile():
    x0 = MJ_RIB_EDGE
    return S.p_poly(S.rpoly([(x0, 71.5, 1.0), (9.4, 71.5, 1.5), (9.4, 107.3, 4.0), (x0, 107.3, 1.0)]))


def mj_half_b():
    """Servo-side half: the tail lug with the pivot's counterbore, the pad rib with its slot, the
    clamp screw's insert."""
    plate = _yx(mj_profile(), (0.0, JAW[1]), R_EDGE, sharp=(True, False))
    # the lug from the plate's face, and across the plate's rounded rim only where the plate is
    lug = S.union(_yx(mj_lug_profile(), (JAW[1], LUG[1]), R_EDGE, sharp=(True, False)),
                  S.extrude(S.p_inter(mj_lug_profile(), mj_profile()), "y", JAW[1] - R_EDGE, JAW[1] + R_EDGE))
    rib = _yx(mj_rib_profile(), (JAW[1] - R_EDGE, PAD[1]), R_EDGE, sharp=(True, False))
    solid = S.inter(S.union(plate, lug, rib), S.box((-30, 0.0, 0), (40, 20, 130)))
    cx, cz = CLAMP
    cuts = [_shoulder_bore(-1, LUG[1] + 1),
            _cyl_y(P, SHOULDER["head_d"] / 2 + 0.2, (CB_FLOOR, LUG[1] + 1)),              # the head, flush
            S.cyl((T0[0], 0, T0[1]), 1.075, "y", LUG[0] - 0.5, LUG[1] + 0.5),           # tail dowel, slip
            pad_slot(flip=True),
            S.cyl((cx, 0, cz), INSERT_M2["hole"] / 2, "y", -0.5, JAW[1] + 0.5)]          # M2 insert, through
    return S.diff(solid, *cuts)


# --------------------------------------------------------------- link and crank
def link():
    """Coupler, modelled along +x from the tail pin. The 2 x 6 tail dowel is
    pressed into it (sticks out -y into the lug); the crank's dowel slips in."""
    out = _yx(S.p_capsule((0, 0), (B_LINK, 0), 3.0), LINK, R_SMALL)
    return S.diff(out, S.cyl((0, 0, 0), 0.975, "y", LINK[0] - 1, LINK[1] + 1),
                  S.cyl((B_LINK, 0, 0), 1.075, "y", LINK[0] - 1, LINK[1] + 1))


def crank():
    """Crank arm on the MG90S horn, modelled along +x from the shaft. The horn
    arm drops into a pocket on the servo side; a countersunk M2 x 6 through the
    centre replaces the horn screw, flush with the face the link runs under."""
    arm = _yx(S.p_blend(1.5, S.p_circle((0, 0), 5.2), S.p_capsule((0, 0), (A_CRANK, 0), 3.4)), CRANK, R_SMALL)
    horn_pocket = S.union(S.cyl((0, 0, 0), 3.9, "y", CRANK[1] - 1.9, CRANK[1] + 1),
                          S.prism(np.array([(0, -3.2), (16.5, -2.3), (16.5, 2.3), (0, 3.2)]),
                                  "y", CRANK[1] - 1.9, CRANK[1] + 1))
    return S.diff(arm, horn_pocket,
                  S.cyl((0, 0, 0), 1.15, "y", CRANK[0] - 1, CRANK[1] + 1),
                  # 90 deg countersink for an ISO 10642 M2 x 6: the head sits flush, because the
                  # link passes 0.4 from the shaft axis just under this face
                  S.cone((0, 0, 0), 2.3, 1.15, "y", CRANK[0] - 0.6, CRANK[0] + 1.15),
                  S.cyl((A_CRANK, 0, 0), 0.975, "y", CRANK[0] - 1.0, CRANK[1] - 2.0))   # 2 x 5 dowel, pressed


def anvil():
    return S.box((-2.4, -1.9, 70.0), (0.0, 1.9, 105.2), r=0.2)


# --------------------------------------------------------------- kinematics
def crank_angle(phi):
    """Servo crank angle (rad, in the x-z plane from +x toward +z) for jaw opening phi."""
    T = P + jaw_R(phi) @ (T0 - P)
    d = T - SV; L = math.hypot(*d)
    g = math.acos(max(-1, min(1, (A_CRANK ** 2 + L ** 2 - B_LINK ** 2) / (2 * A_CRANK * L))))
    return math.atan2(d[1], d[0]) + BRANCH * g


def jaw_R(phi):
    c, s = math.cos(phi), math.sin(phi)
    return np.array([[c, s], [-s, c]])


def jaw3(phi):
    """3x3 rotation of the moving jaw about the pivot axis (y), as (R, t) on tool points."""
    c, s = math.cos(phi), math.sin(phi)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    p = np.array([P[0], 0, P[1]])
    return R, p - R @ p


PARTS = {"body": body, "ring": camera_ring, "mj_a": mj_half_a, "mj_b": mj_half_b, "link": link, "crank": crank,
         "anvil": anvil, "pad": tpu_pad}


# ------------------------------------------------------------ where the cuts go
# Harvest Rev B replaces the printed harvest drawer. Dead leaves go into its
# dead-leaf tray in the base bay: the gantry takes the folded arm over it at the lowest Z and
# the jaws open, as they did over the drawer. Leaves and veggies go out through the right panel
# into its feeder at tier B. The tray's numbers below are the ones the arm checks need, as
# harvest.py's TRAY and drops.yaml give them: outside x 171.5 to 628.5 and y 32 to 512, rims
# at z 120, five drops along it at y 330.
TRAY = dict(x=(171.5, 628.5), y=(32.0, 512.0), rim_z=120.0, wall=1.6,
            drops_x=(231.5, 315.75, 400.0, 484.25, 568.5), drop_y=330.0)

