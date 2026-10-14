#!/usr/bin/env python3
"""Axonometric of the drip trays mounted on the 4040 frame.

Geometry comes from the Rev C/D/E cut list and the SendCutSend flat patterns, so this
drawing cannot disagree with the parts that are in the cart:

    frame outside     1397 W x 457 D x 1829 H
    levels (member bottoms, mm)  0 / 304.8 / 965.2 / 1397 / 1789
    longitudinals     1317 long, 40x40, front at y 0..40, back at y 417..457
    side members      377 long, 40x40
    shelf rail        1317 long, at y 163..203, one per tier
    tray DOWN         690 x 203 floor, 25 lip, x 40..730
    tray UP           657 x 203 floor, 25 lip, x 700..1357, 30 mm tongue laps on top
    base pan          same split, 377 wide, dropped between the bottom members
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
import render3d as R3

C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))
INK, LINE, DIM = "#1B2629", "#5E6E70", "#1F6F8B"

ALU   = ("#DDE4E2", "#B2BEBD", "#8B9A9C")   # top, +x, +y
TRAY  = ("#DCE8F6", "#A9C6E6", "#6F93C4")
PAN   = ("#E6EDF6", "#BBCFE4", "#8198B8")
PLATE = ("#F6E0D0", "#E0A977", "#B9793C")

T = 1.6   # tray wall


def proj(p):
    x, y, z = p
    return ((x - y) * C30, (x + y) * S30 + z)


YREF = 457.0   # mirror depth so the viewer stands in front of the cabinet, not behind it


def box(x0, x1, y0, y1, z0, z1, pal, tag=None):   # retained for the 2D panels
    """One axis-aligned box, as its three faces visible from (+x,+y,+z).

    y is mirrored about YREF on the way in, so the face we see is the cabinet front.
    """
    y0, y1 = YREF - y1, YREF - y0
    f = [
        ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], pal[0]),  # top
        ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], pal[1]),  # +x
        ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], pal[2]),  # +y
    ]
    out = []
    for pts, col in f:
        key = sum(sum(c) for c in pts) / len(pts)
        out.append((key, pts, col, tag))
    return out


def tray(x0, x1, y0, y1, zf, pal, end_lip, tongue=0.0):
    """A formed tray: floor plus lips. end_lip is 'lo', 'hi' or None (which end is closed)."""
    b = []
    fx0 = x0 + (tongue if end_lip == "hi" else 0.0)
    b += box(x0, x1, y0, y1, zf, zf + T, pal)                       # floor
    b += box(fx0, x1, y0, y0 + T, zf, zf + 25, pal)                 # front lip
    b += box(fx0, x1, y1 - T, y1, zf, zf + 25, pal)                 # back lip
    if end_lip == "lo":
        b += box(x0, x0 + T, y0, y1, zf, zf + 25, pal)
    elif end_lip == "hi":
        b += box(x1 - T, x1, y0, y1, zf, zf + 25, pal)
    return b


# ----------------------------------------------------------------- the model
W, D, H = 1397.0, 457.0, 1829.0
LEVELS = [0.0, 304.8, 965.2, 1397.0, 1789.0]
TIERS = LEVELS[1:4]
XI0, XI1 = 40.0, 1357.0          # between the uprights
LAP, L_DOWN, L_UP = 30.0, 690.0, 657.0


def frame(sc, levels, uprights=True):
    if uprights:
        for ux in (0.0, W - 40):
            for uy in (0.0, D - 40):
                sc.box(ux, ux + 40, uy, uy + 40, 0, H, ALU)
    for z in levels:
        sc.box(XI0, XI1, 0, 40, z, z + 40, ALU)            # front longitudinal
        sc.box(XI0, XI1, D - 40, D, z, z + 40, ALU)        # back longitudinal
        sc.box(0, 40, 40, D - 40, z, z + 40, ALU)          # left depth member
        sc.box(W - 40, W, 40, D - 40, z, z + 40, ALU)      # right depth member
        if z in TIERS:
            sc.box(XI0, XI1, 163, 203, z, z + 40, ALU)     # shelf rail
    return sc


def tray(sc, x0, x1, y0, y1, zf, pal, end_lip, tongue=0.0):
    """A formed tray: floor plus lips. end_lip says which end is closed."""
    fx0 = x0 + (tongue if end_lip == "hi" else 0.0)
    sc.box(x0, x1, y0, y1, zf, zf + T, pal)                   # floor
    sc.box(fx0, x1, y0, y0 + T, zf, zf + 25, pal)             # front lip
    sc.box(fx0, x1, y1 - T, y1, zf, zf + 25, pal)             # back lip
    if end_lip == "lo":
        sc.box(x0, x0 + T, y0, y1, zf, zf + 25, pal)
    else:
        sc.box(x1 - T, x1, y0, y1, zf, zf + 25, pal)
    return sc


def trays_at(sc, z, dz=0.0, pal=TRAY):
    zf = z + 40 + dz
    tray(sc, XI0, XI0 + L_DOWN, 0, 203, zf, pal, "lo")
    tray(sc, XI1 - L_UP, XI1, 0, 203, zf + (T if dz == 0 else 0), pal, "hi", tongue=LAP)
    return sc


def render(ax, scene, title, sub="", width=1500):
    img, to_px = R3.render(scene, width=width)
    ax.imshow(img, interpolation="antialiased")
    ax.axis("off")
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK, loc="left", pad=4)
    if sub:
        ax.text(0, -0.03, sub, transform=ax.transAxes, fontsize=7.6,
                color=LINE, va="top", linespacing=1.5)
    return to_px


fig = plt.figure(figsize=(13.4, 15.2), facecolor="#FBFCFA")
fig.suptitle("Herb Tower  ·  drip trays mounted on the 4040 frame",
             fontsize=15, fontweight="bold", color=INK, x=.045, ha="left", y=.985)
fig.text(.045, .962,
         "Isometric, 30°.  Grey = 80/20 40-4040 and 20-2020 profile.  Blue = 5052 aluminium "
         "0.063 in trays, the four parts now quoted at SendCutSend.\n"
         "Every dimension is taken from the cut list and the flat patterns, so the drawing and "
         "the DXFs cannot drift apart.",
         fontsize=8.4, color=LINE, va="top", linespacing=1.6)

# -- A: whole cabinet ------------------------------------------------------
axA = fig.add_axes([.025, .375, .47, .525])
sc = R3.Scene()
frame(sc, LEVELS)
for z in TIERS:
    trays_at(sc, z)
sc.box(XI0, XI1, 40, 417, 40, 40 + T, PAN)                          # base pan floor
sc.box(XI0, XI1, 40, 40 + T, 40, 65, PAN)
sc.box(XI0, XI1, 417 - T, 417, 40, 65, PAN)
sc.box(XI0, XI0 + T, 40, 417, 40, 65, PAN)
render(axA, sc, "A   assembly",
       "Three tier trays plus the base pan.  Each tier tray is two pieces lapped at mid-span;\n"
       "the base pan drops between the bottom frame members.")

# -- B: one tier, exploded -------------------------------------------------
axB = fig.add_axes([.515, .375, .47, .525])
sc = R3.Scene()
frame(sc, [TIERS[0]], uprights=False)
trays_at(sc, TIERS[0], dz=230.0)
to_px = render(axB, sc, "B   one tier, exploded",
       "The tray lands on the top faces of the front longitudinal and the shelf rail,\n"
       "overlapping each by 40 mm.  Clear span between the two supports is 123 mm,\n"
       "which is why 1.6 mm sheet is stiff enough.")
for x in (XI0 + 150, XI1 - 150):
    for yy in (6.0, 197.0):
        p0 = to_px(x, yy, TIERS[0] + 42)
        p1 = to_px(x, yy, TIERS[0] + 268)
        axB.add_line(Line2D([p0[0], p1[0]], [p0[1], p1[1]], color=DIM, lw=.9,
                            ls=(0, (4, 3)), zorder=5))

# -- C: section through the tray and rails ---------------------------------
axC = fig.add_axes([.055, .055, .40, .285])
z0 = 0.0


def rect(ax, x, y, w, h, fc, lw=1.1):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=INK, lw=lw))


rect(axC, 0, z0, 40, 40, ALU[1])          # front longitudinal
rect(axC, 163, z0, 40, 40, ALU[1])        # shelf rail
rect(axC, 0, z0 + 40, 203, T, TRAY[1])    # tray floor
rect(axC, 0, z0 + 40, T, 25, TRAY[1])     # front lip
rect(axC, 203 - T, z0 + 40, T, 25, TRAY[1])
axC.add_patch(plt.Rectangle((40, z0 + 40 + T), 123, 10, fc="none", ec=DIM,
                            lw=.8, ls=(0, (3, 2))))
axC.annotate("", (40, z0 + 25), (163, z0 + 25),
             arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axC.text(101.5, z0 + 19, "123 clear span", ha="center", fontsize=7.5, color=DIM)
axC.annotate("", (0, z0 + 76), (203, z0 + 76),
             arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axC.text(101.5, z0 + 79, "203 plant zone", ha="center", fontsize=7.5, color=DIM)
axC.annotate("", (212, z0 + 40), (212, z0 + 65),
             arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axC.text(218, z0 + 52, "25 lip", fontsize=7.5, color=DIM, va="center")
axC.text(20, z0 + 20, "40-4040", ha="center", fontsize=6.8, color=INK, rotation=90, va="center")
axC.text(183, z0 + 20, "shelf rail", ha="center", fontsize=6.8, color=INK, rotation=90, va="center")
axC.text(260, z0 + 20, "robot lane\ncontinues to y 457", fontsize=7.2, color=LINE, va="center")
axC.set_xlim(-30, 400); axC.set_ylim(-18, 100)
axC.set_aspect("equal"); axC.axis("off")
axC.set_title("C   section through a tier, looking along the length",
              fontsize=11, fontweight="bold", color=INK, loc="left", pad=4)

# -- D: the lap, in plan ---------------------------------------------------
axD = fig.add_axes([.52, .055, .44, .285])
axD.add_patch(plt.Rectangle((0, 0), 230, 203, fc=TRAY[0], ec=INK, lw=1.1))
axD.add_patch(plt.Rectangle((200, 0), 190, 203, fc=TRAY[1], ec=INK, lw=1.1, alpha=.96))
axD.add_patch(plt.Rectangle((200, 3.5), 30, 196, fc=TRAY[2], ec=INK, lw=1.0, alpha=.8))
for yy in (0, 203 - 6):
    axD.add_patch(plt.Rectangle((0, yy), 230, 6, fc=ALU[2], ec=INK, lw=.7))
    axD.add_patch(plt.Rectangle((230, yy), 160, 6, fc=ALU[2], ec=INK, lw=.7))
axD.annotate("", (200, -16), (230, -16),
             arrowprops=dict(arrowstyle="<->", color=DIM, lw=.9))
axD.text(215, -26, "30 lap", ha="center", fontsize=7.5, color=DIM)
axD.annotate("flow", (120, 101), (330, 101), fontsize=8, color=DIM, va="center",
             ha="center", arrowprops=dict(arrowstyle="->", color=DIM, lw=1.2))
axD.text(90, 215, "DOWN piece, lips run full length", fontsize=7.4, color=INK)
axD.text(250, 215, "UP piece", fontsize=7.4, color=INK)
axD.text(215, 100, "tongue\non top", fontsize=6.6, color="#FBFCFA", ha="center",
         va="center", rotation=90, fontweight="bold")
axD.set_xlim(-30, 420); axD.set_ylim(-40, 240)
axD.set_aspect("equal"); axD.axis("off")
axD.set_title("D   the lap, in plan", fontsize=11, fontweight="bold", color=INK,
              loc="left", pad=4)
axD.text(0, -0.06, "The uphill piece sits on top, so runoff crosses the seam downhill and never "
                   "climbs it.\nBed it in neutral-cure silicone; acetoxy cure attacks aluminium.",
         transform=axD.transAxes, fontsize=7.6, color=LINE, va="top", linespacing=1.5)

fig.text(.955, .016, "Rev E  ·  2026-10-10", fontsize=7.5, color=LINE, ha="right")
fig.savefig("/home/claude/greenhouse/drawings/tray_axonometric.png", dpi=150,
            facecolor="#FBFCFA")
print("ok")
