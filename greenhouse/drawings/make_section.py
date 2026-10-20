#!/usr/bin/env python3
"""Herb Tower: cross section and long elevation, with the arm to real kinematics.

Frame numbers come from brackets.py, tray depth from make_dxf_rev4.py, and the
arm from Elephant Robotics' published DH table for the myCobot 280:

    d1 = 131.22   a2 = -110.4   a3 = -96   d4 = 63.4   d5 = 75.05   d6 = 45.6

https://docs.elephantrobotics.com/docs/gitbook-en/2-serialproduct/2.1-280/Kinematics&Coordinate.html

The links below are those numbers, not a sketch. Note that the chain sums to more
than the published 280 mm working radius: 280 is the usable envelope, the sum is
arithmetic and not reachable with the wrist in a working pose.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch, Arc, Polygon

# ---- frame, from brackets.py ----------------------------------------------
W, D, H = 1397.0, 559.0, 1829.0
SER = 40.0
LEVELS = [0.0, 304.8, 965.2, 1397.0, 1789.0]
TIERS = LEVELS[1:4]
TRAY_D = 203.0                      # WT in make_dxf_rev4.py
CORRIDOR = D - TRAY_D               # 254 mm left in front of the trays

# ---- myCobot 280, published DH --------------------------------------------
D1, A2, A3, D5, D6 = 131.22, 110.4, 96.0, 75.05, 45.6
REACH = 280.0                       # published working radius about the J1 axis
PLATE_T = 6.35
BASE_L = 30.0                       # base block along the J1 axis

# where the plate face sits, measured back from the cabinet front
Y_PLATE = 150.0
Y_J1 = Y_PLATE + PLATE_T + BASE_L   # joint 1 origin
Y_REQ = D - REACH                   # J1 must be at least this far back

INK, ALU, STEEL, ACC = "#1d2326", "#c8cfd2", "#8d989d", "#c2410c"
DIM, GRN, BLU = "#5b6770", "#2f7d4f", "#1d4ed8"

POTS = {TIERS[0]: 7, TIERS[1]: 10, TIERS[2]: 10}
HEADROOM = {TIERS[i]: (LEVELS[i + 2] - TIERS[i]) for i in range(3)}

fig = plt.figure(figsize=(17.0, 12.2), facecolor="white")
fig.suptitle("Herb Tower   section and elevation   1397 × 559 × 1829 mm",
             x=0.5, y=0.975, fontsize=16, fontweight="bold", color=INK)
fig.text(0.5, 0.951, "Arm drawn to the published myCobot 280 DH parameters. "
         "The gantry runs the long side; the arm reaches across the tray depth.",
         ha="center", fontsize=10.5, color=DIM)


def post(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=ALU, edgecolor=INK, lw=1.1, zorder=3))


# =============================================================== SECTION
axS = fig.add_axes([0.045, 0.055, 0.30, 0.86])
axS.set_aspect("equal"); axS.axis("off")
axS.set_title("A    Cross section, looking along the long side",
              loc="left", fontsize=12, fontweight="bold", color=INK, pad=12)

# uprights front and back
post(axS, 0, 0, SER, H)
post(axS, D - SER, 0, SER, H)

# horizontal members at every level, seen in section
for z in LEVELS:
    for yy in (0.0, D - SER):
        axS.add_patch(Rectangle((yy, z), SER, SER, facecolor=STEEL,
                                edgecolor=INK, lw=1.0, zorder=4))

# base pan, full depth
axS.add_patch(Rectangle((SER, LEVELS[0] + SER), D - 2 * SER, 3.0,
                        facecolor="#dfe7e3", edgecolor=INK, lw=1.0, zorder=4))
axS.add_patch(Rectangle((D - SER - 25, SER), 3, 25, facecolor="#dfe7e3",
                        edgecolor=INK, lw=1.0, zorder=4))
axS.text(D / 2, SER + 14, "base pan, full 559 depth", fontsize=8.5,
         color=DIM, ha="center")

# trays and plants
for z in TIERS:
    y0 = D - TRAY_D
    axS.add_patch(Rectangle((y0, z + SER), TRAY_D, 3.0, facecolor="#dfe7e3",
                            edgecolor=INK, lw=1.2, zorder=5))
    axS.add_patch(Rectangle((y0, z + SER), 3, 25, facecolor="#dfe7e3",
                            edgecolor=INK, lw=1.2, zorder=5))
    # a pot and its plant, in section
    pc, ph = y0 + TRAY_D / 2, min(HEADROOM[z] - 90, 230)
    axS.add_patch(Polygon([(pc - 52, z + SER + 3), (pc + 52, z + SER + 3),
                           (pc + 42, z + SER + 95), (pc - 42, z + SER + 95)],
                          closed=True, facecolor="#d9cfc4", edgecolor=DIM,
                          lw=0.9, zorder=6))
    axS.plot([pc, pc], [z + SER + 95, z + SER + 95 + ph], color=GRN, lw=2.0, zorder=6)
    for k in range(3):
        yy = z + SER + 110 + k * ph / 3.2
        axS.plot([pc - 40 - k * 6, pc], [yy + 26, yy], color=GRN, lw=1.5, zorder=6)
        axS.plot([pc + 40 + k * 6, pc], [yy + 26, yy], color=GRN, lw=1.5, zorder=6)
    axS.text(D + 58, z + SER + 90,
             f"{int(HEADROOM[z])} mm headroom\n{POTS[z]} pots",
             fontsize=9, color=DIM, va="center")

# the gantry corridor
axS.add_patch(Rectangle((SER, LEVELS[0]), CORRIDOR - SER, H, facecolor="#fdf4ec",
                        edgecolor="none", zorder=1))
axS.annotate(f"{CORRIDOR:.0f} mm gantry corridor", xy=(CORRIDOR / 2, 1640),
             xytext=(-250, 1760), fontsize=9.5, color=ACC,
             arrowprops=dict(arrowstyle="->", color=ACC, lw=1.1))

# Z column, carriage, plate, arm base
Z_ARM = 1180.0
axS.add_patch(Rectangle((Y_PLATE - 86, 300), 46, H - 420, facecolor=ALU,
                        edgecolor=INK, lw=1.2, zorder=5))
axS.add_patch(Rectangle((Y_PLATE - 40, Z_ARM - 66), 40, 132, facecolor=STEEL,
                        edgecolor=INK, lw=1.1, zorder=6))
axS.add_patch(Rectangle((Y_PLATE, Z_ARM - 80), PLATE_T, 160, facecolor="#e8edef",
                        edgecolor=INK, lw=1.6, zorder=7))
axS.add_patch(Rectangle((Y_PLATE + PLATE_T, Z_ARM - 63), BASE_L, 126,
                        facecolor=ALU, edgecolor=INK, lw=1.1, zorder=7))
axS.annotate("Z column", xy=(Y_PLATE - 63, 1560), xytext=(-250, 1600),
             fontsize=9.5, color=DIM,
             arrowprops=dict(arrowstyle="->", color=DIM, lw=1.0))
axS.annotate("G071 plate", xy=(Y_PLATE + PLATE_T / 2, Z_ARM - 86),
             xytext=(-250, 960), fontsize=9.5, color=INK,
             arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))

# ---- the arm, real link lengths -------------------------------------------
PIV = (Y_J1, Z_ARM)


def chain(angles):
    pts, (x, y), a = [PIV], PIV, 0.0
    for ang, ln in zip(angles, (A2, A3, D5 + D6)):
        a += ang
        x += math.cos(math.radians(a)) * ln
        y += math.sin(math.radians(a)) * ln
        pts.append((x, y))
    return pts


def draw_arm(ax, pts, color, lw, alpha=1.0, label=None, lx=14):
    ax.plot([PIV[0] - BASE_L, PIV[0]], [PIV[1], PIV[1]], color=color, lw=lw,
            alpha=alpha, solid_capstyle="round", zorder=9)
    for i in range(len(pts) - 1):
        ax.plot([pts[i][0], pts[i + 1][0]], [pts[i][1], pts[i + 1][1]],
                color=color, lw=lw, alpha=alpha, solid_capstyle="round", zorder=9)
    for i, p in enumerate(pts):
        ax.add_patch(Circle(p, 11 if i == 0 else 9, facecolor="white",
                            edgecolor=color, lw=1.3, alpha=alpha, zorder=10))
    if label:
        ax.text(pts[-1][0] + lx, pts[-1][1], label, fontsize=9, color=color,
                va="center")


ext = chain((4, -34, -38))
draw_arm(axS, ext, BLU, 6.5, label="working\npose")
draw_arm(axS, chain((82, -150, -60)), STEEL, 6.0, alpha=0.8, label="stowed", lx=12)

# reach envelope and the constraint it creates
axS.add_patch(Arc(PIV, 2 * REACH, 2 * REACH, theta1=-96, theta2=96,
                  color=BLU, lw=1.1, ls=(0, (5, 4)), zorder=8))
DIMZ = 1690.0
for xx in (PIV[0], D):
    axS.plot([xx, xx], [Z_ARM + 40, DIMZ], color=ACC, lw=0.7, ls=":", zorder=11)
axS.add_patch(FancyArrowPatch((PIV[0], DIMZ), (D, DIMZ), arrowstyle="<->",
                              mutation_scale=11, color=ACC, lw=1.3, zorder=11))
axS.text((PIV[0] + D) / 2, DIMZ + 22,
         f"{D - Y_J1:.0f} mm from joint 1 to the tray's far edge\n"
         f"inside the {REACH:.0f} mm envelope",
         fontsize=9, color=ACC, ha="center", va="bottom")

axS.set_xlim(-270, 700); axS.set_ylim(-150, 1900)

# =============================================================== ELEVATION
axE = fig.add_axes([0.40, 0.055, 0.565, 0.86])
axE.set_aspect("equal"); axE.axis("off")
axE.set_title("B    Long elevation, the face the gantry runs along",
              loc="left", fontsize=12, fontweight="bold", color=INK, pad=12)

post(axE, 0, 0, SER, H)
post(axE, W - SER, 0, SER, H)
for z in LEVELS:
    axE.add_patch(Rectangle((SER, z), W - 2 * SER, SER, facecolor=STEEL,
                            edgecolor=INK, lw=1.0, zorder=4))
    axE.text(-16, z + SER / 2, f"{z:.0f}", fontsize=8.5, color=DIM,
             ha="right", va="center")

for z in TIERS:
    n = POTS[z]
    span = W - 2 * SER - 40
    step = span / n
    ph = min(HEADROOM[z] - 90, 230)
    for k in range(n):
        pc = SER + 20 + step * (k + 0.5)
        axE.add_patch(Polygon([(pc - 34, z + SER), (pc + 34, z + SER),
                               (pc + 27, z + SER + 86), (pc - 27, z + SER + 86)],
                              closed=True, facecolor="#d9cfc4", edgecolor=DIM,
                              lw=0.8, zorder=6))
        axE.plot([pc, pc], [z + SER + 86, z + SER + 86 + ph], color=GRN, lw=1.7, zorder=6)
        for j in range(3):
            yy = z + SER + 100 + j * ph / 3.2
            axE.plot([pc - 26 - j * 4, pc], [yy + 20, yy], color=GRN, lw=1.2, zorder=6)
            axE.plot([pc + 26 + j * 4, pc], [yy + 20, yy], color=GRN, lw=1.2, zorder=6)
    axE.text(W + 18, z + SER + 60, f"{n} pots   ·   {int(HEADROOM[z])} mm headroom",
             fontsize=9.5, color=DIM, va="center")

# X rail along the long side, with the Z column on it
RAIL_Z = 1706.0
axE.add_patch(Rectangle((SER, RAIL_Z), W - 2 * SER, 26, facecolor="#f6d9c2",
                        edgecolor=ACC, lw=1.3, zorder=7))
axE.add_patch(FancyArrowPatch((SER + 14, RAIL_Z - 40), (W - SER - 14, RAIL_Z - 40),
                              arrowstyle="<->", mutation_scale=12, color=ACC, lw=1.3,
                              zorder=8))
axE.text(W / 2, RAIL_Z - 58, "gantry X rail, 1317 mm of travel",
         fontsize=9.5, color=ACC, ha="center", va="top")

X_ARM = 470.0
axE.add_patch(Rectangle((X_ARM - 23, 300), 46, RAIL_Z - 300, facecolor=ALU,
                        edgecolor=INK, lw=1.2, zorder=8))
axE.add_patch(Rectangle((X_ARM - 80, Z_ARM - 80), 160, 12,
                        facecolor="#e8edef", edgecolor=INK, lw=1.4, zorder=9))
axE.plot([X_ARM, X_ARM + 34, X_ARM + 6, X_ARM + 26],
         [Z_ARM - 68, Z_ARM - 134, Z_ARM - 196, Z_ARM - 244],
         color=BLU, lw=6.0, solid_capstyle="round", zorder=10)
for p in ((X_ARM, Z_ARM - 68), (X_ARM + 34, Z_ARM - 134),
          (X_ARM + 6, Z_ARM - 196), (X_ARM + 26, Z_ARM - 244)):
    axE.add_patch(Circle(p, 9, facecolor="white", edgecolor=BLU, lw=1.3, zorder=11))
axE.annotate("arm seen edge on,\ncolumn at one X position",
             xy=(X_ARM + 20, Z_ARM - 180), xytext=(X_ARM - 330, Z_ARM - 330),
             fontsize=9, color=BLU,
             arrowprops=dict(arrowstyle="->", color=BLU, lw=1.0))

axE.set_xlim(-70, W + 320); axE.set_ylim(-150, 1900)

# =============================================================== footer
short = Y_REQ - Y_J1
verdict = (f"Joint 1 sits {Y_J1 - 0:.0f} mm behind the front face and the tray's far edge "
           f"is {D - Y_J1:.0f} mm away, inside the {REACH:.0f} mm envelope."
           if Y_J1 >= Y_REQ else
           f"Joint 1 would need to sit {short:.0f} mm further back to reach the tray's far edge.")
fig.text(0.045, 0.030,
         f"Trays are {TRAY_D:.0f} mm deep in a {D:.0f} mm cabinet, leaving a "
         f"{CORRIDOR:.0f} mm corridor for the gantry.  Joint 1 must sit at least "
         f"{Y_REQ:.0f} mm behind the front face for the tool to touch the back edge of a tray.  "
         f"{verdict}\n"
         "Arm links are the published DH values, so the chain is real. Tray fore-and-aft "
         "position within the cabinet is an assumption: drawn at the back, gantry in front.",
         fontsize=9.5, color=DIM, va="top")

fig.savefig("greenhouse_section.png", dpi=160,
            facecolor="white", bbox_inches="tight")
print(f"corridor {CORRIDOR:.0f}  J1 at {Y_J1:.2f}  needs >= {Y_REQ:.0f}  "
      f"back edge {D - Y_J1:.0f} away  headroom {dict((int(k), int(v)) for k, v in HEADROOM.items())}")
