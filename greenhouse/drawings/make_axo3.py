#!/usr/bin/env python3
"""Rev 3 axonometric: trays on the external profiles, corner cut to clear the uprights."""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import render3d as R3

INK, LINE, DIM, WARN = "#1B2629", "#5E6E70", "#1F6F8B", "#B3261E"
ALU = ("#DDE4E2", "#B2BEBD", "#8B9A9C")
RAIL = ("#EBD9C4", "#D8B98C", "#B08B55")
TRAY = ("#DCE8F6", "#A9C6E6", "#6F93C4")
PAN = ("#E8EFF7", "#C3D5E8", "#90A6C2")
STL = ("#CFD4D8", "#A4ADB4", "#7C868E")
T = 1.6002

W, D, H = 1397.0, 457.0, 1829.0
LEVELS = [0.0, 304.8, 965.2, 1397.0, 1789.0]
TIERS = LEVELS[1:4]
C = 84.0
MID = (660.0, 700.0)
WT, WP = 203.0, 457.0
SHELF = 163.0


def frame(sc, levels, uprights=True):
    if uprights:
        for ux in (0.0, W - 40):
            for uy in (0.0, D - 40):
                R3.tslot(sc, "z", 0, H, ux, uy, ALU)
    for z in levels:
        R3.tslot(sc, "x", 40, W - 40, 0.0, z, ALU)          # front longitudinal
        R3.tslot(sc, "x", 40, W - 40, D - 40, z, ALU)       # back longitudinal
        R3.tslot(sc, "y", 40, D - 40, 0.0, z, ALU)          # left side member
        R3.tslot(sc, "y", 40, D - 40, W - 40, z, ALU)       # right side member
        if z in TIERS:
            R3.tslot(sc, "x", 40, W - 40, SHELF, z, ALU)    # shelf rail
            R3.tslot(sc, "y", 40, SHELF, MID[0], z, RAIL)   # the one mid rail
        if z == LEVELS[0]:
            R3.tslot(sc, "y", 40, D - 40, MID[0], z, RAIL)  # mid rail under the pan lap
    return sc


def sheet(sc, poly, flanged, z, pal, convex_split=None):
    """A formed sheet: floor polygon plus a 25 mm lip on each flanged edge."""
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
        ox, oy = uy * T, -ux * T          # inward offset (polygon is CCW)
        for a, b in (((P[0], P[1]), (Q[0], Q[1])),
                     ((P[0] - ox, P[1] - oy), (Q[0] - ox, Q[1] - oy))):
            sc.face([(a[0], a[1], z), (b[0], b[1], z),
                     (b[0], b[1], z + 25), (a[0], a[1], z + 25)], pal[1])
        sc.face([(P[0], P[1], z + 25), (Q[0], Q[1], z + 25),
                 (Q[0] - ox, Q[1] - oy, z + 25), (P[0] - ox, P[1] - oy, z + 25)], pal[2])
    return sc


def tray_polys(z, dz=0.0):
    zf = z + 40 + dz
    down = [(C, 0), (MID[1], 0), (MID[1], WT), (0, WT), (0, C)]
    down_fl = [True, False, True, True, True]
    up = [(MID[0], 3.5), (MID[1], 3.5), (MID[1], 0), (W - C, 0), (W, C),
          (W, WT), (MID[1], WT), (MID[1], WT - 3.5), (MID[0], WT - 3.5)]
    up_fl = [False, False, True, True, True, True, False, False, False]
    up_split = [[(MID[0], 3.5), (MID[1], 3.5), (MID[1], WT - 3.5), (MID[0], WT - 3.5)],
                [(MID[1], 0), (W - C, 0), (W, C), (W, WT), (MID[1], WT)]]
    return (down, down_fl, None, zf), (up, up_fl, up_split, zf + (T if dz == 0 else 0))


def pan_polys(z):
    zf = z + 40
    down = [(C, 0), (MID[1], 0), (MID[1], WP), (C, WP), (0, WP - C), (0, C)]
    down_fl = [True, False, True, True, True, True]
    up = [(MID[0], 3.5), (MID[1], 3.5), (MID[1], 0), (W - C, 0), (W, C),
          (W, WP - C), (W - C, WP), (MID[1], WP), (MID[1], WP - 3.5), (MID[0], WP - 3.5)]
    up_fl = [False, False, True, True, True, True, True, False, False, False]
    up_split = [[(MID[0], 3.5), (MID[1], 3.5), (MID[1], WP - 3.5), (MID[0], WP - 3.5)],
                [(MID[1], 0), (W - C, 0), (W, C), (W, WP - C), (W - C, WP), (MID[1], WP)]]
    return (down, down_fl, None, zf), (up, up_fl, up_split, zf + T)


def render(ax, scene, title, sub="", width=1500):
    img, to_px = R3.render(scene, width=width, pad=0.045)
    ax.imshow(img, interpolation="antialiased")
    ax.axis("off")
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK, loc="left", pad=4)
    if sub:
        ax.text(0, -0.025, sub, transform=ax.transAxes, fontsize=7.6, color=LINE,
                va="top", linespacing=1.5)
    return to_px


fig = plt.figure(figsize=(13.6, 13.8), facecolor="#FBFCFA")
fig.suptitle("Herb Tower  ·  trays on the 4040 frame  ·  Rev 3",
             fontsize=15, fontweight="bold", color=INK, x=.042, ha="left", y=.987)
fig.text(.042, .966,
         "No added profiles at the ends: the trays now run the full 1397 mm frame width and land on the external side members, with a 45 degree corner cut\n"
         "clearing each upright by 2.8 mm.  Amber = the one remaining new rail per level, carrying the lap.  The base pan is now 1397 x 457, mounted on the bottom\n"
         "longitudinals with the same corner cut at all four corners, and bolted down like everything else.",
         fontsize=8.4, color=LINE, va="top", linespacing=1.6)

axA = fig.add_axes([.022, .395, .46, .505])
sc = R3.Scene()
frame(sc, LEVELS)
for z in TIERS:
    for poly, fl, split, zf in tray_polys(z):
        sheet(sc, poly, fl, zf, TRAY, split)
for poly, fl, split, zf in pan_polys(LEVELS[0]):
    sheet(sc, poly, fl, zf, PAN, split)
render(axA, sc, "A   assembly",
       "Nine end rails deleted. Four rails remain in total: one under each tier lap and\n"
       "one under the pan lap. Everything else was already in the frame.")

axB = fig.add_axes([.505, .395, .48, .505])
sc = R3.Scene()
frame(sc, [TIERS[0]], uprights=False)
for poly, fl, split, zf in tray_polys(TIERS[0], dz=250.0):
    sheet(sc, poly, fl, zf, TRAY, split)
to_px = render(axB, sc, "B   one tier, exploded",
               "Four bearings per piece, all of them profiles that were already there:\n"
               "front longitudinal, shelf rail, side member and the mid rail.")
for x, yy in ((120.0, 6.0), (120.0, 197.0), (1280.0, 6.0), (1280.0, 197.0)):
    p0, p1 = to_px(x, yy, TIERS[0] + 42), to_px(x, yy, TIERS[0] + 288)
    axB.add_line(Line2D([p0[0], p1[0]], [p0[1], p1[1]], color=DIM, lw=.9,
                        ls=(0, (4, 3)), zorder=5))

# C  the corner cut, in plan ------------------------------------------------
axC = fig.add_axes([.045, .05, .40, .29])
axC.add_patch(plt.Rectangle((0, 0), 40, 40, fc=ALU[2], ec=INK, lw=1.1))
axC.text(20, 20, "upright", fontsize=6.6, color="#FBFCFA", ha="center", va="center",
         rotation=45, fontweight="bold")
axC.add_patch(plt.Rectangle((40, 0), 200, 40, fc=ALU[1], ec=INK, lw=1.0))
axC.add_patch(plt.Rectangle((0, 40), 40, 180, fc=ALU[1], ec=INK, lw=1.0))
axC.add_patch(plt.Rectangle((40, SHELF), 200, 40, fc=ALU[1], ec=INK, lw=1.0))
axC.add_patch(plt.Polygon([(C, 0), (240, 0), (240, WT), (0, WT), (0, C)],
                          fc=TRAY[0], ec=INK, lw=1.6, alpha=.72))
axC.plot([C, 0], [0, C], color=WARN, lw=1.8)
axC.plot([0, 80], [80, 0], color=WARN, lw=.8, ls=(0, (3, 2)))
axC.annotate("2.83 clear", (44, 44), (104, 92), fontsize=7.2, color=WARN,
             arrowprops=dict(arrowstyle="->", color=WARN, lw=.8))
axC.plot([20], [130], marker="o", ms=4, color=DIM)
axC.text(26, 130, "bolt into the side member", fontsize=7, color=DIM, va="center")
axC.plot([150], [20], marker="o", ms=4, color=DIM)
axC.plot([150], [183], marker="o", ms=4, color=DIM)
axC.text(160, 20, "front longitudinal", fontsize=7, color=DIM, va="center")
axC.text(160, 183, "shelf rail", fontsize=7, color=DIM, va="center")
axC.annotate("", (0, -14), (C, -14), arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axC.text(C / 2, -24, "84", fontsize=7.2, color=DIM, ha="center")
axC.set_xlim(-30, 330); axC.set_ylim(-34, 232)
axC.set_aspect("equal"); axC.axis("off")
axC.set_title("C   the corner cut, in plan", fontsize=11, fontweight="bold",
              color=INK, loc="left", pad=4)
axC.text(0, -.05, "A 45 degree chamfer, not a square notch. A square notch would put two perpendicular\n"
                  "lips into a re-entrant corner whose flanges overlap in the flat pattern and need a\n"
                  "mitred slit; one chamfer face replaces both and the piece still has four bends.",
         transform=axC.transAxes, fontsize=7.6, color=LINE, va="top", linespacing=1.5)

# D  fixing detail ----------------------------------------------------------
axD = fig.add_axes([.505, .05, .46, .29])


def rc(ax, x, y, w, h, fc, **kw):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=kw.pop("ec", INK),
                               lw=kw.pop("lw", 1.0), **kw))


rc(axD, 0, 18, 16, 22, ALU[1]); rc(axD, 24, 18, 16, 22, ALU[1])
rc(axD, 0, 10, 40, 8, ALU[1])
axD.plot([16, 16], [38, 40], color=INK, lw=1.0)
axD.plot([24, 24], [38, 40], color=INK, lw=1.0)
axD.add_patch(plt.Polygon([(16, 38), (12.2, 34), (12.2, 18), (27.8, 18), (27.8, 34), (24, 38)],
                          fc="#FBFCFA", ec=INK, lw=1.0))
rc(axD, 12.6, 19, 15.2, 6, STL[1])
rc(axD, -16, 40, 31.5, T, TRAY[1]); rc(axD, 24.5, 40, 31.5, T, TRAY[1])
rc(axD, 12, 41.6, 16, 1.6, STL[0])
axD.add_patch(plt.Polygon([(13, 43.2), (27, 43.2), (26, 47.4), (14, 47.4)], fc=STL[1], ec=INK, lw=1.0))
rc(axD, 16, 25, 8, 16, STL[2], lw=.8)
for x, y, t, c, ha in [(-20, 41, "tray floor\n1.6 mm", INK, "right"),
                       (62, 50, "M8 x 16 BHSCS", INK, "left"),
                       (62, 42, "M8 flat washer, which doubles as\nthe 1.6 mm shim under the UP piece", INK, "left"),
                       (62, 24, "M8 T-nut, slot 8\n(see the note on drop-in vs slide-in)", INK, "left"),
                       (-20, 28, "40-4040\nland, 16 mm", LINE, "right"),
                       (62, 13, "8 mm slot opening,\n12 mm deep", LINE, "left")]:
    axD.text(x, y, t, fontsize=7.2, color=c, va="center", linespacing=1.5, ha=ha)
for (lx, ly), (tx, ty) in [((22, 46), (61, 50)), ((27, 42.4), (61, 42)),
                           ((26, 22), (61, 24)), ((8, 29), (-19, 28)),
                           ((-8, 40.8), (-19, 41)), ((30, 15), (61, 13))]:
    axD.add_line(Line2D([lx, tx], [ly, ty], color="#AAB4B3", lw=.6, zorder=0))
axD.annotate("", (15.5, 53), (24.5, 53), arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axD.text(20, 54.5, "9 x 18 slot in the tray", fontsize=7.2, color=DIM, ha="center")
axD.set_xlim(-70, 190); axD.set_ylim(6, 58)
axD.set_aspect("equal"); axD.axis("off")
axD.set_title("D   how every sheet bolts down", fontsize=11, fontweight="bold",
              color=INK, loc="left", pad=4)
axD.text(0, -.05, "Eight slots per piece, on the top-face slot centreline of the four profiles it lands on.\n"
                  "Slotted 9 x 18 because 80/20 cut-to-length holds +/-0.5 mm and that accumulates over\n"
                  "1397 mm; the slot runs along the profile, which is also the way the T-nut slides.",
         transform=axD.transAxes, fontsize=7.6, color=LINE, va="top", linespacing=1.5)

fig.text(.955, .015, "Rev 3  ·  2026-10-10", fontsize=7.5, color=LINE, ha="right")
fig.savefig("tray_axonometric_rev3.png", dpi=150, facecolor="#FBFCFA")
print("ok")
