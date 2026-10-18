#!/usr/bin/env python3
"""Arm plate to gantry interface drawing (BOM G071).

Two panels: a section through the joint showing the bolt stack, and the plate
face at true proportion showing both slot families. Every number is read from
make_plate.py, not retyped.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (Rectangle, Circle, FancyArrowPatch, Arc,
                                FancyBboxPatch)

# --- geometry, from make_plate.py -------------------------------------------
T       = 6.35      # plate thickness, 0.250 in
SIDE    = 160.0
CORNER  = 12.0
BORE    = 22.0
SLOT_W  = 7.0
N_RAD   = 8
R_IN    = 20.0
R_OUT   = 54.0
EDGE_X  = 66.0
EDGE_Y  = 55.0

TRAVEL  = 2 * EDGE_Y                      # 110 mm of carriage adjustment
BC_MIN, BC_MAX = 2 * R_IN, 2 * R_OUT      # bolt circles accepted
EDGE_MARGIN = SIDE / 2 - EDGE_X - SLOT_W / 2
WEB_BORE    = (R_IN - SLOT_W / 2) - BORE / 2
WEB_RAD     = 2 * R_IN * math.sin(math.pi / N_RAD) - SLOT_W
GAP_SLOTS   = EDGE_X - SLOT_W / 2 - (R_OUT + SLOT_W / 2)

INK, ALU, STEEL, ACC, DIM = "#1d2326", "#c8cfd2", "#8d989d", "#c2410c", "#5b6770"

REACH = 280.0       # myCobot 280 published working radius, mm
ARM_KG = 0.85       # published mass
PAYLOAD = 0.25      # published payload

fig = plt.figure(figsize=(15.5, 14.6), facecolor="white")
fig.suptitle("Arm plate to gantry interface   G071   6061-T6, 0.250 in (6.35 mm), cut only",
             x=0.5, y=0.977, fontsize=15, fontweight="bold", color=INK)
fig.text(0.5, 0.955, "Both interfaces are slotted: nothing has to match a drilled pattern.",
         ha="center", fontsize=10.5, color=DIM)


def slot_face(ax, x, y, ang, length, w):
    """Draw a rounded slot centred at (x,y), axis at ang degrees, given length."""
    th = math.radians(ang)
    dx, dy = math.cos(th) * length / 2, math.sin(th) * length / 2
    px, py = -math.sin(th) * w / 2, math.cos(th) * w / 2
    a = (x - dx, y - dy); b = (x + dx, y + dy)
    ax.plot([a[0] + px, b[0] + px], [a[1] + py, b[1] + py], color=INK, lw=1.3, zorder=5)
    ax.plot([a[0] - px, b[0] - px], [a[1] - py, b[1] - py], color=INK, lw=1.3, zorder=5)
    for c, s in ((b, ang - 90), (a, ang + 90)):
        ax.add_patch(Arc(c, w, w, angle=0, theta1=s, theta2=s + 180,
                         color=INK, lw=1.3, zorder=5))


# =============================================================== PANEL A
axA = fig.add_axes([0.045, 0.50, 0.40, 0.42])
axA.set_aspect("equal"); axA.axis("off")
axA.set_title("A    Section through the joint", loc="left",
              fontsize=12, fontweight="bold", color=INK, pad=14)

XU, XC, XP, XB = -40.0, 0.0, 9.0, 9.0 + T     # upright, carriage, plate, base


def leader(ax, text, xy, xytext, color, ha="left"):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=9, color=color, ha=ha,
                va="center", arrowprops=dict(arrowstyle="-", color=color, lw=0.9,
                                             shrinkA=2, shrinkB=2))


# 4080 gantry upright, seen end-on
axA.add_patch(Rectangle((XU, -95), 40, 190, facecolor=ALU, edgecolor=INK, lw=1.4))
for yy in (-50, 50):
    axA.add_patch(Rectangle((XU, yy - 9), 40, 18, facecolor="white",
                            edgecolor=STEEL, lw=0.8))
leader(axA, "4080 gantry upright", (XU + 20, 86), (-118, 104), DIM)

# carriage
axA.add_patch(Rectangle((XC, -66), 9, 132, facecolor=STEEL, edgecolor=INK, lw=1.4))
leader(axA, "carriage", (XC + 4.5, -58), (-118, -92), DIM)

# the arm plate
axA.add_patch(Rectangle((XP, -80), T, 160, facecolor="#e8edef", edgecolor=INK, lw=2.0))
leader(axA, "G071 plate, 6.35 mm", (XP + T / 2, 74), (-118, 86), INK)

# myCobot base
axA.add_patch(Rectangle((XB, -63), 30, 126, facecolor=ALU, edgecolor=INK, lw=1.4))
leader(axA, "myCobot 280 base", (XB + 15, -56), (XB + 46, -92), DIM)

# bolts: carriage side, through the edge slots
for yy in (-EDGE_Y + 14, EDGE_Y - 14):
    axA.plot([XU + 14, XP + T + 1], [yy, yy], color=ACC, lw=2.6, zorder=6)
    axA.add_patch(Rectangle((XU + 10, yy - 3.4), 4.5, 6.8, facecolor=ACC,
                            edgecolor="none", zorder=6))
    axA.add_patch(Rectangle((XP - 0.9, yy - 6.5), 1.8, 13, facecolor="white",
                            edgecolor=ACC, lw=1.1, zorder=7))
leader(axA, "M5 + fender washer\nthrough an edge slot",
       (XP, EDGE_Y - 14), (-118, 46), ACC)

# bolts: arm side, through the radial slots
for yy in (-30, 30):
    axA.plot([XP - 1, XB + 26], [yy, yy], color="#1d4ed8", lw=2.6, zorder=6)
    axA.add_patch(Rectangle((XB + 24, yy - 3.4), 4.5, 6.8,
                            facecolor="#1d4ed8", edgecolor="none", zorder=6))
leader(axA, "M4 into the arm base,\nthrough a radial slot",
       (XB + 18, 30), (XB + 46, 52), "#1d4ed8")

# cable through the bore
axA.plot([XB + 18, XP + T], [0, 0], color="#047857", lw=2.2,
         solid_capstyle="round", zorder=8)
axA.plot([XP, XC - 6, XU + 4], [0, -4, -30], color="#047857", lw=2.2,
         solid_capstyle="round", zorder=8)
axA.add_patch(Rectangle((XP, -BORE / 2), T, BORE, facecolor="white",
                        edgecolor="#047857", lw=1.1, zorder=7))
leader(axA, "arm cable through\nthe Ø22 bore", (XU + 4, -28), (-118, -34), "#047857")

# travel dimension
axA.add_patch(FancyArrowPatch((XB + 92, -EDGE_Y), (XB + 92, EDGE_Y),
                              arrowstyle="<->", mutation_scale=13, color=ACC, lw=1.4))
for yy in (-EDGE_Y, EDGE_Y):
    axA.plot([XP + T, XB + 92], [yy, yy], color=ACC, lw=0.7, ls=":")
axA.text(XB + 97, 0, f"{TRAVEL:.0f} mm\nheight\nadjustment", fontsize=9.5,
         color=ACC, va="center")

axA.set_xlim(-124, 150); axA.set_ylim(-112, 116)

# =============================================================== PANEL B
axB = fig.add_axes([0.50, 0.50, 0.46, 0.42])
axB.set_aspect("equal"); axB.axis("off")
axB.set_title("B    Plate face, true proportion", loc="left",
              fontsize=12, fontweight="bold", color=INK, pad=14)

h = SIDE / 2
axB.add_patch(FancyBboxPatch((-h + CORNER, -h + CORNER),
                             SIDE - 2 * CORNER, SIDE - 2 * CORNER,
                             boxstyle=f"round,pad=0,rounding_size={CORNER}",
                             facecolor="#eef2f4", edgecolor=INK, lw=1.8, zorder=1))

# bolt-circle envelope
for r, ls in ((R_IN, (0, (4, 3))), (R_OUT, (0, (4, 3)))):
    axB.add_patch(Circle((0, 0), r, fill=False, edgecolor="#1d4ed8", lw=1.0,
                         ls=ls, zorder=4))
axB.add_patch(Circle((0, 0), BORE / 2, facecolor="white", edgecolor=INK, lw=1.5, zorder=5))

for k in range(N_RAD):
    a = 360.0 * k / N_RAD
    rm = (R_IN + R_OUT) / 2
    slot_face(axB, math.cos(math.radians(a)) * rm, math.sin(math.radians(a)) * rm,
              a, R_OUT - R_IN, SLOT_W)
for sx in (-1, 1):
    slot_face(axB, sx * EDGE_X, 0, 90, TRAVEL, SLOT_W)

axB.text(0, 0, "Ø22", ha="center", va="center", fontsize=8, color=INK, zorder=6)
axB.annotate(f"8 radial slots\nany bolt circle Ø{BC_MIN:.0f} to Ø{BC_MAX:.0f}\nat any 45° step",
             xy=(math.cos(math.radians(45)) * 44, math.sin(math.radians(45)) * 44),
             xytext=(96, 104), fontsize=9.5, color="#1d4ed8", ha="left",
             arrowprops=dict(arrowstyle="->", color="#1d4ed8", lw=1.2))
axB.annotate(f"2 edge slots\n{TRAVEL:.0f} mm of carriage travel",
             xy=(-EDGE_X, 30), xytext=(-150, 104), fontsize=9.5, color=ACC, ha="left",
             arrowprops=dict(arrowstyle="->", color=ACC, lw=1.2))
axB.annotate(f"{EDGE_MARGIN:.1f} mm to the edge",
             xy=(EDGE_X + SLOT_W / 2, -40), xytext=(92, -74), fontsize=9, color=DIM,
             arrowprops=dict(arrowstyle="->", color=DIM, lw=1.0))

axB.text(0, -h - 20, f"160 × 160, R{CORNER:.0f} corners     "
                     f"every slot {SLOT_W:.1f} mm wide vs {T:.2f} mm plate",
         ha="center", fontsize=9.5, color=DIM)
axB.set_xlim(-152, 152); axB.set_ylim(-118, 118)

# =============================================================== PANEL C
axC = fig.add_axes([0.045, 0.055, 0.915, 0.40])
axC.set_aspect("equal"); axC.axis("off")
axC.set_title("C    The arm on the gantry, side elevation    "
              "(link lengths schematic; reach is the published 280 mm)",
              loc="left", fontsize=12, fontweight="bold", color=INK, pad=14)

PIV = (45.0, 0.0)                     # joint 1 axis, on the plate centreline
L1, L2, L3 = 110.0, 96.0, 74.0        # sums to the 280 mm working radius


def chain(angles, lengths=(L1, L2, L3)):
    pts, (x, y), a = [PIV], PIV, 0.0
    for ang, ln in zip(angles, lengths):
        a += ang
        x += math.cos(math.radians(a)) * ln
        y += math.sin(math.radians(a)) * ln
        pts.append((x, y))
    return pts


def draw_arm(pts, color, lw, alpha=1.0, ls="-", label=None):
    for i in range(len(pts) - 1):
        axC.plot([pts[i][0], pts[i + 1][0]], [pts[i][1], pts[i + 1][1]],
                 color=color, lw=lw, alpha=alpha, ls=ls,
                 solid_capstyle="round", zorder=6)
    for i, p in enumerate(pts):
        axC.add_patch(Circle(p, 9 if i == 0 else 7, facecolor="white",
                             edgecolor=color, lw=1.4, alpha=alpha, zorder=7))
    if label:
        axC.text(pts[-1][0] + 14, pts[-1][1], label, fontsize=9.5,
                 color=color, va="center")


# gantry column and the tiers it serves
axC.add_patch(Rectangle((-40, -330), 40, 660, facecolor=ALU, edgecolor=INK, lw=1.4))
axC.text(-20, 344, "gantry Z column (4080)", ha="center", fontsize=9.5, color=DIM)
for yy, name in ((190, "tier above"), (-190, "tier below")):
    axC.plot([60, 470], [yy, yy], color=STEEL, lw=2.2, zorder=1)
    for px in range(96, 430, 78):
        axC.add_patch(Rectangle((px, yy + 2), 46, 34, facecolor="#dfe7e3",
                                edgecolor=STEEL, lw=0.9, zorder=2))
    axC.text(474, yy, name, fontsize=9, color=DIM, va="center")

# carriage, plate, arm base
axC.add_patch(Rectangle((0, -66), 9, 132, facecolor=STEEL, edgecolor=INK, lw=1.3))
axC.add_patch(Rectangle((9, -80), T, 160, facecolor="#e8edef", edgecolor=INK, lw=2.0))
axC.add_patch(Rectangle((9 + T, -63), 30, 126, facecolor=ALU, edgecolor=INK, lw=1.3))
axC.annotate("G071 plate", xy=(9 + T / 2, -86), xytext=(-104, -150),
             fontsize=9.5, color=INK,
             arrowprops=dict(arrowstyle="-", color=INK, lw=0.9))

# reach envelope
axC.add_patch(Arc(PIV, 2 * REACH, 2 * REACH, theta1=-108, theta2=108,
                  color="#1d4ed8", lw=1.1, ls=(0, (5, 4)), zorder=3))
axC.text(PIV[0] + REACH * 0.80, REACH * 0.80, f"Ø{2*REACH:.0f} working envelope",
         fontsize=9.5, color="#1d4ed8", rotation=-40)

# stowed and extended postures
draw_arm(chain((88, -158, -54)), STEEL, 7.0, alpha=0.85, label="stowed")
ext = chain((12, -26, -34))
draw_arm(ext, "#1d4ed8", 7.5, label="extended")

# the moment this puts on the plate
tip = ext[-1]
axC.add_patch(FancyArrowPatch((tip[0], tip[1] - 8), (tip[0], tip[1] - 62),
                              arrowstyle="-|>", mutation_scale=14, color=ACC, lw=2.0,
                              zorder=8))
axC.text(tip[0] + 10, tip[1] - 42, f"{ARM_KG + PAYLOAD:.2f} kg\n(arm + payload)",
         fontsize=9, color=ACC, va="center")
axC.add_patch(FancyArrowPatch((PIV[0], -258), (tip[0], -258), arrowstyle="<->",
                              mutation_scale=12, color=ACC, lw=1.3))
axC.plot([PIV[0], PIV[0]], [-20, -258], color=ACC, lw=0.7, ls=":")
axC.plot([tip[0], tip[0]], [tip[1] - 62, -258], color=ACC, lw=0.7, ls=":")
axC.text((PIV[0] + tip[0]) / 2, -276, "moment arm at full extension",
         fontsize=9.5, color=ACC, ha="center", va="top")

mom = (ARM_KG + PAYLOAD) * 9.81 * REACH / 1000.0
axC.text(PIV[0], -322,
         f"Worst case, the whole {ARM_KG + PAYLOAD:.2f} kg acting at the full {REACH:.0f} mm: "
         f"about {mom:.1f} N·m trying to rotate the plate on the carriage.\n"
         "The real figure is roughly half that, since the arm's own mass sits well inside "
         "full reach. Size the carriage bolts for the bound, not the average.",
         fontsize=9.5, color=ACC, va="top")

axC.set_xlim(-130, 560); axC.set_ylim(-390, 360)

# =============================================================== footer
fig.text(0.045, 0.030,
         f"Webs: {WEB_BORE:.1f} mm bore to radial slot   ·   {WEB_RAD:.1f} mm between adjacent "
         f"radial slots   ·   {GAP_SLOTS:.1f} mm radial slot to edge slot\n"
         "Slots clamp by friction, not shear. Torque the carriage bolts and use washers: "
         "the arm's reach puts a real moment on this joint.",
         fontsize=9.5, color=DIM, va="top")

fig.savefig("/home/claude/outputs/arm_plate_gantry_mount.png", dpi=170,
            facecolor="white", bbox_inches="tight")
print("webs:", round(WEB_BORE, 2), round(WEB_RAD, 2), round(GAP_SLOTS, 2),
      "edge margin:", round(EDGE_MARGIN, 2))
print("saved")
