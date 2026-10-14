#!/usr/bin/env python3
"""Rev 5 axonometric: the two bought brackets placed on the frame.

Rev 4 showed the trays. This adds the hardware that holds the frame square, and
shows the one rule that governs where it can go: nothing mounts on a top face,
because every top face here is either a tray bearing surface or the slot the
tray's T-nut needs.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import render3d as R3
import brackets as BK

INK, LINE, DIM, WARN = "#1B2629", "#5E6E70", "#1F6F8B", "#B3261E"
ALU = ("#DDE4E2", "#B2BEBD", "#8B9A9C")
RAIL = ("#EBD9C4", "#D8B98C", "#B08B55")
TRAY = ("#DCE8F6", "#A9C6E6", "#6F93C4")
PAN = ("#E8EFF7", "#C3D5E8", "#90A6C2")
GUS = ("#F2C9C3", "#DC9A90", "#B3675B")
HID = ("#CFE3D4", "#9FC4A9", "#6D9478")
STL = ("#CFD4D8", "#A4ADB4", "#7C868E")
T = 1.6002

W, D, H = BK.W, BK.D, BK.H
LEVELS, TIERS = BK.LEVELS, BK.TIERS
N = 41.0
MID, SHELF = BK.MID, BK.SHELF
WT, WP = 203.0, 457.0
PLATE, LEG = BK.GUSSET["plate"], BK.GUSSET["leg"]


def frame(sc, levels, uprights=True):
    if uprights:
        for ux in (0.0, W - 40):
            for uy in (0.0, D - 40):
                R3.tslot(sc, "z", 0, H, ux, uy, ALU)
    for z in levels:
        R3.tslot(sc, "x", 40, W - 40, 0.0, z, ALU)
        R3.tslot(sc, "x", 40, W - 40, D - 40, z, ALU)
        R3.tslot(sc, "y", 40, D - 40, 0.0, z, ALU)
        R3.tslot(sc, "y", 40, D - 40, W - 40, z, ALU)
        if z in TIERS:
            R3.tslot(sc, "x", 40, W - 40, SHELF, z, ALU)
            R3.tslot(sc, "y", 40, SHELF, MID[0], z, RAIL)
        if z == LEVELS[0]:
            R3.tslot(sc, "y", 40, D - 40, MID[0], z, RAIL)
    return sc


def gusset(sc, axis, at, inward, cross, z, pal=GUS):
    """An L hanging UNDER a horizontal member, leg down the face it butts into.

    axis   'x' or 'y', the member's run direction
    at     the coordinate of the joint face along that axis
    inward +1 if the member runs away from the joint in +axis, else -1
    cross  the member's 40 mm band on the other horizontal axis, as (lo, hi)
    z      the member's top; the member occupies z-40 .. z
    """
    zt = z                      # underside of the member
    s = inward
    a0, a1 = sorted((at, at + s * LEG))         # plate under the member
    b0, b1 = sorted((at, at + s * PLATE))       # plate on the mating face
    c0, c1 = cross
    if axis == "x":
        sc.box(a0, a1, c0, c1, zt - PLATE, zt, pal)
        sc.box(b0, b1, c0, c1, zt - LEG, zt, pal)
    else:
        sc.box(c0, c1, a0, a1, zt - PLATE, zt, pal)
        sc.box(c0, c1, b0, b1, zt - LEG, zt, pal)
    return sc


def place_gussets(sc, levels):
    """The 20 gussets, exactly where brackets.allocate() puts them."""
    n = 0
    for z in levels:
        if z > 0.0:
            for cy in ((0.0, 40.0), (D - 40, D)):          # front, back
                gusset(sc, "x", 40.0, +1, cy, z); n += 1
                gusset(sc, "x", W - 40, -1, cy, z); n += 1
        if z in TIERS[1:]:                                  # upper-tier mid rails
            gusset(sc, "y", 40.0, +1, MID, z); n += 1
            gusset(sc, "y", SHELF, -1, MID, z); n += 1
    return n


def hidden(sc, axis, at, inward, cross, z, pal=HID):
    """The concealed connector, drawn as the block it is inside the 8 mm slot."""
    s, t = inward, BK.HIDDEN["width"]
    a0, a1 = sorted((at, at + s * BK.HIDDEN["leg"]))
    c0, c1 = (cross[0] + cross[1]) / 2 - t / 2, (cross[0] + cross[1]) / 2 + t / 2
    if axis == "x":
        sc.box(a0, a1, c0, c1, z - 12, z, pal)
    else:
        sc.box(c0, c1, a0, a1, z - 12, z, pal)
    return sc


def sheet(sc, poly, flanged, z, pal, convex_split=None):
    for part in (convex_split or [poly]):
        sc.face([(x, y, z + T) for x, y in part], pal[0])
    n = len(poly)
    for i in range(n):
        if not flanged[i]:
            continue
        P, Q = poly[i], poly[(i + 1) % n]
        dx, dy = Q[0] - P[0], Q[1] - P[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        ox, oy = uy * T, -ux * T
        for a, b in (((P[0], P[1]), (Q[0], Q[1])),
                     ((P[0] - ox, P[1] - oy), (Q[0] - ox, Q[1] - oy))):
            sc.face([(a[0], a[1], z), (b[0], b[1], z),
                     (b[0], b[1], z + 25), (a[0], a[1], z + 25)], pal[1])
        sc.face([(P[0], P[1], z + 25), (Q[0], Q[1], z + 25),
                 (Q[0] - ox, Q[1] - oy, z + 25), (P[0] - ox, P[1] - oy, z + 25)], pal[2])
    return sc


def tray_polys(z, dz=0.0):
    zf = z + 40 + dz
    down = [(N, 0), (MID[1], 0), (MID[1], WT), (0, WT), (0, N), (N, N)]
    down_fl = [True, False, True, True, True, True]
    down_split = [[(N, 0), (MID[1], 0), (MID[1], WT), (N, WT)],
                  [(0, N), (N, N), (N, WT), (0, WT)]]
    XN = W - N
    up = [(MID[0], 3.5), (MID[1], 3.5), (MID[1], 0), (XN, 0), (XN, N), (W, N),
          (W, WT), (MID[1], WT), (MID[1], WT - 3.5), (MID[0], WT - 3.5)]
    up_fl = [False, False, True, True, True, True, True, False, False, False]
    up_split = [[(MID[0], 3.5), (MID[1], 3.5), (MID[1], WT - 3.5), (MID[0], WT - 3.5)],
                [(MID[1], 0), (XN, 0), (XN, WT), (MID[1], WT)],
                [(XN, N), (W, N), (W, WT), (XN, WT)]]
    return ((down, down_fl, down_split, zf), (up, up_fl, up_split, zf + T))


def pan_polys(z):
    zf = z + 40
    down = [(N, 0), (MID[1], 0), (MID[1], WP), (N, WP), (N, WP - N), (0, WP - N),
            (0, N), (N, N)]
    down_fl = [True, False, True, True, True, True, True, True]
    down_split = [[(N, 0), (MID[1], 0), (MID[1], WP), (N, WP)],
                  [(0, N), (N, N), (N, WP - N), (0, WP - N)]]
    XN = W - N
    up = [(MID[0], 3.5), (MID[1], 3.5), (MID[1], 0), (XN, 0), (XN, N), (W, N),
          (W, WP - N), (XN, WP - N), (XN, WP), (MID[1], WP),
          (MID[1], WP - 3.5), (MID[0], WP - 3.5)]
    up_fl = [False, False, True, True, True, True, True, True, True, False, False, False]
    up_split = [[(MID[0], 3.5), (MID[1], 3.5), (MID[1], WP - 3.5), (MID[0], WP - 3.5)],
                [(MID[1], 0), (XN, 0), (XN, WP), (MID[1], WP)],
                [(XN, N), (W, N), (W, WP - N), (XN, WP - N)]]
    return (down, down_fl, down_split, zf), (up, up_fl, up_split, zf + T)


def render(ax, scene, title, sub="", width=1500):
    img, to_px = R3.render(scene, width=width, pad=0.045)
    ax.imshow(img, interpolation="antialiased")
    ax.axis("off")
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK, loc="left", pad=4)
    if sub:
        ax.text(0, -0.025, sub, transform=ax.transAxes, fontsize=7.6, color=LINE,
                va="top", linespacing=1.5)
    return to_px


fig = plt.figure(figsize=(13.6, 13.6), facecolor="#FBFCFA")
fig.suptitle("Herb Tower  ·  the two bought T-slot brackets, placed  ·  Rev 5",
             fontsize=15, fontweight="bold", color=INK, x=.042, ha="left", y=.987)
fig.text(.042, .966,
         "Terracotta = PETOX 3540 external gusset, 20 off, \$29.99.  Green = TOCLUX hidden inside connector, 10 off, \$16.99.  Both are 40 series, slot 8.\n"
         "One rule decides every position: no bracket mounts on a top face. Every top face in this cabinet is either a tray bearing surface or the slot its\n"
         "T-nut slides in, so each gusset hangs UNDER its rail and each hidden connector lives inside the slot. Closest approach to a sheet fastener: 16 mm.",
         fontsize=8.4, color=LINE, va="top", linespacing=1.6)

# A  assembly ---------------------------------------------------------------
axA = fig.add_axes([.022, .40, .46, .50])
sc = R3.Scene()
frame(sc, LEVELS)
ng = place_gussets(sc, LEVELS)
for z in TIERS:
    for poly, fl, split, zf in tray_polys(z):
        sheet(sc, poly, fl, zf, TRAY, split)
for poly, fl, split, zf in pan_polys(LEVELS[0]):
    sheet(sc, poly, fl, zf, PAN, split)
render(axA, sc, "A   assembly, brackets in place",
       f"{ng} gussets, all of them hanging under a rail. Level 0 gets none: there is no room\n"
       "below a rail that sits on the floor, and the bolted-down base pan braces it instead.")

# B  one joint, exploded ----------------------------------------------------
axB = fig.add_axes([.505, .40, .48, .50])
sc = R3.Scene()
z = TIERS[1]
R3.tslot(sc, "z", z - 260, z + 300, 0.0, 0.0, ALU)
R3.tslot(sc, "x", 40, 520, 0.0, z, ALU)
R3.tslot(sc, "y", 40, 300, 0.0, z, ALU)
R3.tslot(sc, "x", 40, 520, SHELF, z, ALU)
gusset(sc, "x", 40.0, +1, (0.0, 40.0), z)
hidden(sc, "x", 40.0, +1, (SHELF, SHELF + 40), z)
poly, fl, split, zf = tray_polys(z, dz=170.0)[0]
sheet(sc, [p for p in poly if p[0] <= 520], [True, False, True, True, True, True],
      zf, TRAY, [[(N, 0), (520, 0), (520, WT), (N, WT)],
                 [(0, N), (N, N), (N, WT), (0, WT)]])
to_px = render(axB, sc, "B   the front-left joint, exploded",
               "The gusset hangs below the longitudinal, so the whole 35 mm of its reach is under\n"
               "the tray floor. The hidden connector at the shelf-rail end takes no outside room at all.")
for x, yy in ((120.0, 6.0), (120.0, 197.0), (400.0, 6.0), (400.0, 197.0)):
    p0, p1 = to_px(x, yy, z + 42), to_px(x, yy, z + 208)
    axB.add_line(Line2D([p0[0], p1[0]], [p0[1], p1[1]], color=DIM, lw=.9,
                        ls=(0, (4, 3)), zorder=5))

# C  the gusset in elevation ------------------------------------------------
axC = fig.add_axes([.045, .055, .40, .28])


def rc(ax, x, y, w, h, fc, ec=INK, lw=1.0, **kw):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, **kw))


rc(axC, 0, -40, 40, 220, ALU[1])                    # upright
rc(axC, 40, 100, 230, 40, ALU[1])                    # longitudinal, z 100..140
rc(axC, 41, 141.6, 229, 1.6, TRAY[1])                # tray floor
rc(axC, 41, 143.2, 2.4, 25, TRAY[2], lw=.8)                 # upstand against the post
rc(axC, 40, 94, 35, 6, GUS[1])                       # gusset, plate under the rail
rc(axC, 40, 65, 6, 35, GUS[1])                       # gusset, plate on the post
axC.plot([60, 60], [94, 104], color=STL[2], lw=3, solid_capstyle="butt", zorder=5)
axC.plot([43, 53], [80, 80], color=STL[2], lw=3, solid_capstyle="butt", zorder=5)
axC.annotate("", (40, 58), (75, 58), arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axC.text(80, 58, "35 mm leg, 6 mm plate", fontsize=7.2, color=DIM, ha="left", va="center")
axC.annotate("", (40, 186), (150, 186), arrowprops=dict(arrowstyle="<->", color=WARN, lw=.9))
axC.text(95, 190, "110 mm to the first tray bolt", fontsize=7.2, color=WARN, ha="center")
axC.plot([150], [141.6], marker="o", ms=4.5, color=WARN, zorder=6)
for x, y, t, c, ha in [(285, 140, "tray floor 1.6 mm, bolted at x = 150", INK, "left"),
                       (285, 112, "front longitudinal 40-4040", LINE, "left"),
                       (285, 82, "3540 gusset, M8 into the slot\ncentreline of both profiles", GUS[2], "left"),
                       (-14, 10, "upright", LINE, "right")]:
    axC.text(x, y, t, fontsize=7.4, color=c, va="center", ha=ha, linespacing=1.5)
for (lx, ly), (tx, ty) in [((200, 142), (283, 140)), ((200, 120), (283, 112)),
                           ((70, 90), (283, 82)), ((20, 10), (-13, 10))]:
    axC.add_line(Line2D([lx, tx], [ly, ty], color="#AAB4B3", lw=.6, zorder=0))
axC.set_xlim(-90, 540); axC.set_ylim(-50, 205)
axC.set_aspect("equal"); axC.axis("off")
axC.set_title("C   gusset under the rail, in elevation", fontsize=11,
              fontweight="bold", color=INK, loc="left", pad=4)
axC.text(0, -.05,
         "Mounted the usual way, above the rail, this bracket would sit in the 41 x 41 notch the tray\n"
         "already cuts for the post, lift the sheet 6 mm and take the slot its T-nut needs. Hung below,\n"
         "it clears everything and the bolt still lands on the slot centreline, 20 mm from the corner.",
         transform=axC.transAxes, fontsize=7.6, color=LINE, va="top", linespacing=1.5)

# D  the hidden connector in section ----------------------------------------
axD = fig.add_axes([.505, .055, .46, .28])
rc(axD, 0, 0, 40, 40, ALU[0])                        # shelf rail, section
rc(axD, 16, 28, 8, 12, "#FBFCFA")                    # top slot
rc(axD, 12, 10, 16, 18, "#FBFCFA")
rc(axD, 16, 0, 8, 12, "#FBFCFA", lw=.8)
rc(axD, 12.6, 11, 14.8, 7.8, HID[1])                 # the connector, inside the slot
axD.plot([20, 20], [19, 27], color=STL[2], lw=3, solid_capstyle="butt", zorder=5)
rc(axD, 80, 0, 40, 40, ALU[0])
rc(axD, 96, 28, 8, 12, "#FBFCFA")
rc(axD, 92, 38.4, 16, 1.6, STL[0], lw=.8)
rc(axD, 70, 40, 60, 1.6, TRAY[1])
rc(axD, 94, 41.6, 12, 1.6, STL[0])
axD.add_patch(plt.Polygon([(95, 43.2), (105, 43.2), (104, 47), (96, 47)],
                          fc=STL[1], ec=INK, lw=1.0))
rc(axD, 96, 20, 8, 18, STL[2], lw=.8)
for x, y, t, c, ha in [(-6, 20, "hidden connector sits\n11 to 19 mm deep, inside\nthe slot, nothing outside", HID[2], "right"),
                       (146, 46, "M8 x 16 BHSCS + washer", INK, "left"),
                       (146, 32, "M8 T-nut, drop-in", INK, "left"),
                       (146, 12, "slot 8: 8 mm opening,\n12 mm deep", LINE, "left"),
                       (60, 52, "same slot, 110 mm apart", DIM, "center")]:
    axD.text(x, y, t, fontsize=7.4, color=c, va="center", ha=ha, linespacing=1.5)
for (lx, ly), (tx, ty) in [((12, 15), (-5, 20)), ((106, 45), (145, 46)),
                           ((105, 29), (145, 32)), ((110, 34), (145, 12))]:
    axD.add_line(Line2D([lx, tx], [ly, ty], color="#AAB4B3", lw=.6, zorder=0))
axD.annotate("", (24, 50), (92, 50), arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axD.set_xlim(-80, 260); axD.set_ylim(-12, 58)
axD.set_aspect("equal"); axD.axis("off")
axD.set_title("D   hidden connector and tray bolt, same slot", fontsize=11,
              fontweight="bold", color=INK, loc="left", pad=4)
axD.text(0, -.05,
         "The hidden connector reaches 38 mm along the shelf rail from the joint. The nearest tray bolt\n"
         "is at x = 150, so 110 mm of clear slot sits between them. The tightest case anywhere in the\n"
         "cabinet is the tier mid rail, where a gusset and the lap bolt are 16 mm apart.",
         transform=axD.transAxes, fontsize=7.6, color=LINE, va="top", linespacing=1.5)

fig.text(.955, .015, "Rev 5  ·  2026-10-10", fontsize=7.5, color=LINE, ha="right")
fig.savefig("tray_axonometric_rev5.png", dpi=150, facecolor="#FBFCFA")
print("ok")
