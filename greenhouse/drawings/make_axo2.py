#!/usr/bin/env python3
"""Rev 2 axonometric: real 40-4040 section, transverse support rails, T-slot fixings."""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import render3d as R3

INK, LINE, DIM, WARN = "#1B2629", "#5E6E70", "#1F6F8B", "#B3261E"
ALU  = ("#DDE4E2", "#B2BEBD", "#8B9A9C")
RAIL = ("#EBD9C4", "#D8B98C", "#B08B55")      # the new transverse rails
TRAY = ("#DCE8F6", "#A9C6E6", "#6F93C4")
PAN  = ("#E6EDF6", "#BBCFE4", "#8198B8")
STL  = ("#CFD4D8", "#A4ADB4", "#7C868E")
T = 1.6002

W, D, H = 1397.0, 457.0, 1829.0
LEVELS = [0.0, 304.8, 965.2, 1397.0, 1789.0]
TIERS = LEVELS[1:4]
XI0, XI1 = 40.0, 1357.0
LAP = 40.0
RAIL_MID, RAIL_L, RAIL_R = (660.0, 700.0), (40.0, 80.0), (1317.0, 1357.0)
L_DOWN, L_UP = 660.0, 697.0
Y_SHELF0, Y_SHELF1 = 163.0, 203.0
Y_TR0, Y_TR1 = 40.0, 163.0          # transverse rails run between the two long rails


def frame(sc, levels, uprights=True):
    if uprights:
        for ux in (0.0, W - 40):
            for uy in (0.0, D - 40):
                R3.tslot(sc, "z", 0, H, ux, uy, ALU)
    for z in levels:
        R3.tslot(sc, "x", XI0, XI1, 0.0, z, ALU)              # front longitudinal
        R3.tslot(sc, "x", XI0, XI1, D - 40, z, ALU)           # back longitudinal
        R3.tslot(sc, "y", 40, D - 40, 0.0, z, ALU)            # left depth member
        R3.tslot(sc, "y", 40, D - 40, W - 40, z, ALU)         # right depth member
        if z in TIERS:
            R3.tslot(sc, "x", XI0, XI1, Y_SHELF0, z, ALU)     # shelf rail
            for r0, _ in (RAIL_L, RAIL_MID, RAIL_R):          # NEW transverse rails
                R3.tslot(sc, "y", Y_TR0, Y_TR1, r0, z, RAIL)
    return sc


def tray(sc, x0, x1, y0, y1, zf, pal, lip_end, tongue=0.0):
    fx0 = x0 + (tongue if lip_end == "hi" else 0.0)
    sc.box(x0, x1, y0, y1, zf, zf + T, pal)
    sc.box(fx0, x1, y0, y0 + T, zf, zf + 25, pal)
    sc.box(fx0, x1, y1 - T, y1, zf, zf + 25, pal)
    if lip_end == "lo":
        sc.box(x0, x0 + T, y0, y1, zf, zf + 25, pal)
    else:
        sc.box(x1 - T, x1, y0, y1, zf, zf + 25, pal)
    return sc


def trays_at(sc, z, dz=0.0):
    zf = z + 40 + dz
    tray(sc, XI0, XI0 + L_DOWN, 0, 203, zf, TRAY, "lo")
    tray(sc, RAIL_MID[0], XI1, 0, 203, zf + (T if dz == 0 else 0), TRAY, "hi", tongue=LAP)
    return sc


def render(ax, scene, title, sub="", width=1500):
    img, to_px = R3.render(scene, width=width)
    ax.imshow(img, interpolation="antialiased")
    ax.axis("off")
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK, loc="left", pad=4)
    if sub:
        ax.text(0, -0.025, sub, transform=ax.transAxes, fontsize=7.6, color=LINE,
                va="top", linespacing=1.5)
    return to_px


fig = plt.figure(figsize=(13.6, 13.6), facecolor="#FBFCFA")
fig.suptitle("Herb Tower  ·  trays on the 4040 frame  ·  Rev 2",
             fontsize=15, fontweight="bold", color=INK, x=.042, ha="left", y=.987)
fig.text(.042, .966,
         "Real 40-series T-slot section: the top face is two 16 mm lands with an 8 mm groove, not a flat 40 mm bearing.  "
         "Amber = three new transverse 40-4040 rails per tier, so each tray\npiece lands on four profiles and the lap is "
         "carried rather than bridging.  Lap widened 30 to 40 mm to sit fully on the mid rail.  Mounting slots are cut "
         "into the DXFs.",
         fontsize=8.4, color=LINE, va="top", linespacing=1.6)

# A -------------------------------------------------------------------------
axA = fig.add_axes([.022, .40, .47, .54])
sc = R3.Scene()
frame(sc, LEVELS)
for z in TIERS:
    trays_at(sc, z)
sc.box(XI0, XI1, 40, 417, 0, T, PAN)
sc.box(XI0, XI1, 40, 40 + T, 0, 25, PAN)
sc.box(XI0, XI1, 417 - T, 417, 0, 25, PAN)
render(axA, sc, "A   assembly",
       "Base pan now sits on the floor inside the frame, where 1317 x 377 fits exactly\n"
       "between the bottom members, so it needs no support rails and no fixings.")

# B -------------------------------------------------------------------------
axB = fig.add_axes([.512, .40, .47, .54])
sc = R3.Scene()
frame(sc, [TIERS[0]], uprights=False)
trays_at(sc, TIERS[0], dz=250.0)
to_px = render(axB, sc, "B   one tier, exploded",
               "Four bearings per piece: front longitudinal, shelf rail, one end rail and the\n"
               "mid rail. The amber rails are 123 mm of 40-4040, nine of them across three tiers.")
for x in (XI0 + 160, XI1 - 160):
    for yy in (6.0, 197.0):
        p0 = to_px(x, yy, TIERS[0] + 42)
        p1 = to_px(x, yy, TIERS[0] + 288)
        axB.add_line(Line2D([p0[0], p1[0]], [p0[1], p1[1]], color=DIM, lw=.9,
                            ls=(0, (4, 3)), zorder=5))

# C  fixing detail ----------------------------------------------------------
axC = fig.add_axes([.045, .055, .41, .27])


def rc(ax, x, y, w, h, fc, ec=INK, lw=1.0, **kw):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, **kw))


# profile top 22 mm, section across the face: lands 0..16 and 24..40, groove between
rc(axC, 0, 18, 16, 22, ALU[1]); rc(axC, 24, 18, 16, 22, ALU[1])
rc(axC, 0, 10, 40, 8, ALU[1])
axC.plot([16, 16], [38, 40], color=INK, lw=1.0)
axC.plot([24, 24], [38, 40], color=INK, lw=1.0)
# T-channel widening below the 8 mm lip
axC.add_patch(plt.Polygon([(16, 38), (12.2, 34), (12.2, 18), (27.8, 18), (27.8, 34), (24, 38)],
                          fc="#FBFCFA", ec=INK, lw=1.0))
# T-nut
rc(axC, 12.6, 19, 15.2, 6, STL[1])
axC.plot([20, 20], [19, 25], color=INK, lw=.8, ls=(0, (2, 2)))
# tray floor with its 9 mm slot
rc(axC, -16, 40, 31.5, T, TRAY[1]); rc(axC, 24.5, 40, 31.5, T, TRAY[1])
# washer and button head
rc(axC, 12, 41.6, 16, 1.6, STL[0])
axC.add_patch(plt.Polygon([(13, 43.2), (27, 43.2), (26, 47.4), (14, 47.4)], fc=STL[1], ec=INK, lw=1.0))
rc(axC, 16, 25, 8, 16, STL[2], lw=.8)

for x, y, t, c, ha in [(-20, 41, "tray floor\n1.6 mm", INK, "right"),
                       (62, 50, "M8 x 16 BHSCS", INK, "left"),
                       (62, 42, "M8 flat washer, which doubles as\nthe 1.6 mm shim under the UP piece", INK, "left"),
                       (62, 24, "80/20 40-1981\nM8 economy T-nut", INK, "left"),
                       (-20, 28, "40-4040\nland, 16 mm", LINE, "right"),
                       (62, 13, "8 mm slot opening,\n12 mm deep", LINE, "left")]:
    axC.text(x, y, t, fontsize=7.2, color=c, va="center", linespacing=1.5, ha=ha)
for (lx, ly), (tx, ty) in [((22, 46), (61, 50)), ((27, 42.4), (61, 42)),
                           ((26, 22), (61, 24)), ((8, 29), (-19, 28)),
                           ((-8, 40.8), (-19, 41)), ((30, 15), (61, 13))]:
    axC.add_line(Line2D([lx, tx], [ly, ty], color="#AAB4B3", lw=.6, zorder=0))
axC.annotate("", (15.5, 53), (24.5, 53), arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axC.text(20, 54.5, "9 mm slot in the tray", fontsize=7.2, color=DIM, ha="center")
axC.set_xlim(-70, 170); axC.set_ylim(6, 58)
axC.set_aspect("equal"); axC.axis("off")
axC.set_title("C   how a tray bolts down, section across a profile face",
              fontsize=11, fontweight="bold", color=INK, loc="left", pad=4)
axC.text(0, -0.04, "Holes are 9 x 18 mm slots, not round. 80/20 cut-to-length holds +/-0.5 mm and that\n"
                   "accumulates over 1317 mm; a round M8 hole leaves 1 mm of play, which is not enough.\n"
                   "The slot runs along the profile, which is also the way the T-nut slides.",
         transform=axC.transAxes, fontsize=7.6, color=LINE, va="top", linespacing=1.5)

# D  lap over the mid rail --------------------------------------------------
axD = fig.add_axes([.515, .055, .44, .27])
rc(axD, 660, 0, 40, 40, RAIL[1])
axD.add_patch(plt.Polygon([(676, 38), (672.2, 34), (672.2, 22), (687.8, 22), (687.8, 34), (684, 38)],
                          fc="#FBFCFA", ec=INK, lw=1.0))
axD.plot([676, 676], [38, 40], color=INK, lw=1.0)
axD.plot([684, 684], [38, 40], color=INK, lw=1.0)
rc(axD, 600, 40, 100, 1.6, TRAY[1])                      # DOWN floor, ends at 700
rc(axD, 660, 41.6, 140, 1.6, TRAY[2])                    # UP floor, tongue on top
rc(axD, 700, 40, 100, 1.6, "#FBFCFA", ec=WARN, ls=(0, (3, 2)), lw=.9)
rc(axD, 672.4, 23, 15.2, 6, STL[1])
rc(axD, 676, 29, 8, 14.2, STL[2], lw=.8)
rc(axD, 672, 43.2, 16, 1.6, STL[0])
axD.add_patch(plt.Polygon([(673, 44.8), (687, 44.8), (686, 49), (674, 49)], fc=STL[1], ec=INK, lw=1.0))
axD.annotate("", (660, 58), (700, 58), arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axD.text(680, 59.5, "40 lap = 40 rail", fontsize=7.4, color=DIM, ha="center")
axD.annotate("flow", (625, 52), (770, 52), fontsize=8, color=DIM, ha="center", va="center",
             arrowprops=dict(arrowstyle="->", color=DIM, lw=1.2))
axD.text(612, 36, "DOWN", fontsize=7.4, color=INK)
axD.text(812, 46.5, "UP", fontsize=7.4, color=INK)
axD.text(806, 33, "1.6 mm washer shim under the\nUP piece at every fastener", fontsize=7.2,
         color=WARN, va="center", linespacing=1.5)
axD.add_line(Line2D([760, 804], [40.8, 35], color="#D7A9A3", lw=.6, zorder=0))
axD.text(680, 10, "40-4040\nmid rail", fontsize=7.2, color=INK, ha="center", va="center",
         linespacing=1.4)
axD.set_xlim(590, 1010); axD.set_ylim(-4, 66)
axD.set_aspect("equal"); axD.axis("off")
axD.set_title("D   the lap, carried by the mid rail", fontsize=11, fontweight="bold",
              color=INK, loc="left", pad=4)
axD.text(0, -0.04, "One M8 through both sheets into the mid rail clamps the seam. Because the UP piece\n"
                   "rides on the DOWN piece's floor, it sits 1.6 mm high; a flat washer under each of its\n"
                   "other fasteners takes that up, and the drainage shim stack absorbs the rest.",
         transform=axD.transAxes, fontsize=7.6, color=LINE, va="top", linespacing=1.5)

fig.text(.955, .015, "Rev 2  ·  2026-10-10", fontsize=7.5, color=LINE, ha="right")
fig.savefig("tray_axonometric_rev2.png", dpi=150, facecolor="#FBFCFA")
print("ok")
