#!/usr/bin/env python3
"""Gantry assembly instructions, Rev E.

Rev E over Rev D
  * OpenBuilds parts drawn from bd_warehouse's models of OpenBuilds' drawings:
    the XL plate (fixed wheels on one side, eccentrics on the other, no window),
    the C-Beam profile, the nut block with its spacers and nuts, the End Mount
  * carriage stack: spacer 6 + shim 1 + wheel 11; plate 2.5 off the beam
  * cover render, tools page, gantry wiring, clearer steps 11, 16, 23 and 27
  * arm plate Rev B: tapped M3 for the G base (M4 on the 44 square without
    it), countersunk M5 into the XL plate
  * X rail held by bent 5052 brackets, two per end, instead of cast corners

Rev D notes:

Every drawing is generated from assy.py, the same sub-assemblies the cabinet
model uses, so a bench page and an installed page cannot disagree.

Rev D over Rev C
  * carriages corrected: the wheels straddle the beam and ride its top and
    bottom grooves; screw, plate, spacer, wheel, nyloc
  * X drive corrected: motor at the rail's end, belt in the channel with its
    width on the pulley axis, both ends clamped to the carriage
  * Z drive: screw hangs from the top end plate between two thrust bearings
  * beams are drawn full length and run off the page; the scale is set by
    the part that matters in that step
  * every round part is round and every bored part has its bore
"""
import os, math, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit3d import *
import parts as P
import assy as AS
import frame as Fr
import arm280 as A

# ------------------------------------------------------------------ type
# Maag house style: IBM Plex Mono for titles, Inter for everything else.
# The fonts are not in the repo; they are looked for in $MAAG_FONTS, then in
# greenhouse-esphome/_fonts beside the repo, then among the system's fonts.
import glob as _glob
from matplotlib import font_manager as _fm
_HERE = os.path.dirname(os.path.abspath(__file__))
for _d in (os.environ.get("MAAG_FONTS", ""), os.path.join(_HERE, "..", "..", "..", "..", "_fonts")):
    for _f in _glob.glob(os.path.join(_d, "*.ttf")) if _d else []:
        _fm.fontManager.addfont(_f)
TITLE_FONT = ("IBM Plex Mono" if any(f.name == "IBM Plex Mono" for f in _fm.fontManager.ttflist)
              else "DejaVu Sans Mono")
plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]

OUT = os.environ.get("GANTRY_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build"))
os.makedirs(OUT, exist_ok=True)
REV = "Rev E"
M = iso_matrix(34, 24)
XL = Fr.RAIL_L                 # the X rail, cut
ZL = Fr.MAST_L                 # the Z mast
PAGES = []
WIN_TOP = 772.0


# ================================================================ page kit
def new_page(step, title, sub=""):
    fig = plt.figure(figsize=(11.5, 9.0), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(0, 1150); ax.set_ylim(0, 900)
    ax.add_patch(Rectangle((18, 18), 1114, 864, facecolor="none",
                           edgecolor="#dfe5e9", lw=1.2, zorder=300))
    if step is not None:
        ax.add_patch(Circle((78, 812), 34, facecolor=INK, edgecolor="none", zorder=301))
        ax.text(78, 812, str(step), ha="center", va="center", color="white",
                fontsize=24, fontweight="bold", family=TITLE_FONT, zorder=302)
    title = title.replace("  ·  ", " · ")          # monospace: single spaces round the dot
    ax.text(132 if step is not None else 48, 822, title, fontsize=17.5,
            fontweight="semibold", family=TITLE_FONT, color=INK, va="center", zorder=302)
    if sub:
        ax.text(132 if step is not None else 48, 790, sub, fontsize=11,
                color=DIM, va="center", zorder=302)
    ax.text(1114, 30, f"Maag  ·  Gantry {REV}", fontsize=8, color=DIM,
            ha="right", zorder=302)
    ax._geom = []
    return fig, ax


class View:
    """The mapping a scene used, so arrows and axis lines can be placed in 3D."""

    def __init__(self, MM, s, c, xy):
        self.MM, self.s, self.c, self.xy = MM, s, np.asarray(c), np.asarray(xy)

    def __call__(self, p):
        q = np.asarray(p, float) @ self.MM.T
        return (q[..., :2] - self.c) * self.s + self.xy


def scene(ax, parts, box_xy, box_wh, MM=None, focus=None, clip=None, px=3.0):
    """Render `parts`, scaled so `focus` (Parts, or world points) fills the
    box. Whatever lies outside runs on and is clipped at the drawing window,
    which is how a 1.4 m rail stays full length on an A4-ish page."""
    MM = M if MM is None else MM
    if focus is None:
        pts = np.vstack([p.mesh[0] for p in parts if len(p.mesh[1])])
    elif isinstance(focus, np.ndarray):
        pts = focus
    else:
        pts = np.vstack([p.mesh[0] for p in focus if len(p.mesh[1])])
    Q = pts @ MM.T
    lo, hi = Q[:, :2].min(0), Q[:, :2].max(0)
    ext = np.maximum(hi - lo, 1e-9)
    s = min(box_wh[0] / ext[0], box_wh[1] / ext[1])      # fit each axis
    c = (lo + hi) / 2
    sp = [Part(((p.mesh[0] @ MM.T - np.array([c[0], c[1], 0])) * s
                + np.array([box_xy[0], box_xy[1], 0]), p.mesh[1]),
               p.color, p.edges, p.alpha, p.ghost, p.ang, p.lw) for p in parts]
    before = set(map(id, ax.images + ax.collections))
    render(ax, sp, M=np.eye(3), px=px)
    new = [a for a in ax.images + ax.collections if id(a) not in before]
    ax._geom.append((new, clip))
    return View(MM, s, c, box_xy)


def inset(ax, x, y, w, h, parts, MM, focus=None, label=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=10",
                                facecolor="white", edgecolor="#9aa7b0", lw=1.0,
                                zorder=150))
    v = scene(ax, parts, (x + w / 2, y + h / 2 - (8 if label else 0)),
              (w * 0.86, h * 0.80), MM=MM, focus=focus, clip=(x, y, x + w, y + h))
    for a in ax._geom[-1][0]:
        a.set_zorder(a.get_zorder() + 150)
    if label:
        ax.text(x + 12, y + h - 16, label, fontsize=8.6, color=DIM, zorder=330,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    return v


def save(fig, ax, pdf, name):
    top = WIN_TOP
    bot = getattr(ax, "_body_y", 44.0) + 4.0
    for arts, clip in ax._geom:
        x0, y0, x1, y1 = clip if clip else (20.0, bot, 1130.0, top)
        r = Rectangle((x0, y0), x1 - x0, y1 - y0, transform=ax.transData,
                      facecolor="none", edgecolor="none")
        for a in arts:
            a.set_clip_path(r)
    pdf.savefig(fig); fig.savefig(f"{OUT}/d_{name}.png", dpi=130); plt.close(fig)


def arrow2(ax, p0, p1, color="#c2410c", lw=2.3, rad=0.0, ms=16):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                 lw=lw, color=color, zorder=200,
                                 connectionstyle=f"arc3,rad={rad}"))


def axis3(ax, v, p0, p1, color="#6b7780"):
    """IKEA-style dashed assembly axis between two 3D points."""
    a, b = v(p0), v(p1)
    ax.plot([a[0], b[0]], [a[1], b[1]], ls=(0, (5, 4)), lw=0.9, color=color,
            zorder=120)


def tag(ax, x, y, text, qty=None, fs=10.2, hi=False):
    t = f"{qty}×   {text}" if qty else text
    ax.text(x, y, t, fontsize=fs, color=INK, va="center", zorder=201,
            bbox=dict(boxstyle="round,pad=0.4",
                      fc="#fff4e8" if hi else "white",
                      ec="#e08a3c" if hi else "#c3ccd2", lw=0.9))


def body(ax, txt, color=INK, fs=10.5):
    base = getattr(ax, "_body_y", 44.0)
    ax.text(60, base, txt, fontsize=fs, color=color, va="bottom",
            linespacing=1.62, zorder=302)
    ax._body_y = base + (txt.count("\n") + 1) * fs * 2.25 + 14.0


def tool(ax, x, y, label):
    w = max(140.0, 8.6 * len(label) + 24.0)
    ax.add_patch(Rectangle((x, y - 16), w, 32, facecolor="#eef2f5",
                           edgecolor="#c3ccd2", lw=0.9, zorder=200))
    ax.text(x + w / 2, y, label, ha="center", va="center", fontsize=9.5,
            color="#334", zorder=201, fontweight="bold")


def note(ax, x, y, txt, w=None):
    ax.text(x, y, txt, fontsize=8.8, color=DIM, va="top", linespacing=1.45,
            zorder=302)


def page(fn):
    PAGES.append(fn); return fn


def railp(L=XL, hi=False):
    return Part(AS.rail(L), HILITE if hi else ALU)


MZ = AS.MIDZ


# ============================================================ inventory
@page
def p_inv1(pdf):
    fig, ax = new_page(None, "Gantry  ·  parts",
                       "Count everything first. Quantities cover the complete gantry.")
    items = [("C-Beam 1500, silver", "2", lambda: AS.rail(300), ALU),
             ("XL gantry plate 125 × 125 × 6", "2", P.gantry_plate, STEEL),
             ("Xtreme Solid V wheel", "8", P.solid_v_wheel, POM),
             ("Eccentric spacer, 10 mm hex", "4", P.eccentric_spacer, ALU_D),
             ("Aluminium spacer 6 mm", "6", P.plain_spacer, ALU_D),
             ("Precision shim 10 × 5 × 1", "8", P.shim, STEEL),
             ("NEMA 23  ·  X axis", "1", lambda: P.nema23(76), STEEL),
             ("NEMA 23 + 24 V brake  ·  Z", "1", lambda: P.nema23(76, True), STEEL),
             ("NEMA 23 motor plate", "2", P.motor_mount_plate, ALU),
             ("C-Beam End Mount", "1", P.cbeam_end_mount, ALU),
             ("GT2 pulley 20T, 6.35 bore", "1", P.gt2_pulley, STEEL),
             ("Idler, 9 mm belt", "1", P.idler, STEEL),
             ("Belt clamp block", "2", P.belt_clamp, ALU_D),
             ("Lead screw Tr8x8, 1500", "1", lambda: P.lead_screw(200), STEEL),
             ("Anti-backlash nut block", "1", P.nut_block, BLACKPART),
             ("Thrust bearing 8 × 16 × 5", "2", P.thrust_bearing, STEEL),
             ("Lock collar 8 mm, 14 × 7", "2", P.lock_collar, BLACKPART),
             ("Coupler 6.35 → 8", "1", P.coupler, ALU_D),
             ("Limit switch, NC", "4", P.limit_switch, BLACKPART),
             ("Rail bracket, top  ·  5052", "2", lambda: P.rail_bracket("top"), ALU),
             ("Rail bracket, bottom", "2", lambda: P.rail_bracket("bottom"), ALU),
             ("Arm plate Rev B, 160 × 6.35", "1", P.arm_plate, ALU)]
    for i, (nm, q, fn_, col) in enumerate(items):
        r, c = divmod(i, 4)
        cx, cy = 92 + c * 262, 716 - r * 100
        scene(ax, [Part(fn_(), col)], (cx, cy), (70, 70), MM=iso_matrix(30, 30),
              clip=(cx - 46, cy - 46, cx + 46, cy + 46))
        ax.text(cx + 52, cy + 11, nm, fontsize=8.5, color=INK, va="center")
        ax.text(cx + 52, cy - 11, f"{q}×", fontsize=9.6, color="#c2410c",
                fontweight="bold", va="center")
    body(ax, "Also: GT2 belt 9 mm (2.8 m for the loop), the wiring on the wiring pages, fuse block, E-stop "
             "and the safety relay.\nIn the BOM, not drawn. Rev E changes: shims, the End Mount, the spacer "
             "count and the bent rail brackets.", fs=9.0, color=DIM)
    save(fig, ax, pdf, "00_parts")


@page
def p_inv2(pdf):
    fig, ax = new_page(None, "Gantry  ·  fasteners",
                       "Every screw in the build. Lay them out in labelled pots first.")
    items = [("M5 × 30 low profile  ·  wheels", "8", lambda: P.socket_cap(5, 30, low_profile=True)),
             ("M5 nyloc  ·  wheels, idler", "9", P.nyloc),
             ("M5 × 25 low profile  ·  block, clamps, mount", "10",
              lambda: P.socket_cap(5, 25, low_profile=True)),
             ("M5 hex nut  ·  nut block", "2", P.hex_nut),
             ("M5 × 10 low profile  ·  mast to X carriage", "6", lambda: P.socket_cap(5, 10, low_profile=True)),
             ("M5 × 10 socket cap  ·  motors, X motor plate", "12", lambda: P.socket_cap(5, 10)),
             ("M5 × 12 socket cap  ·  Z foot plate", "4", lambda: P.socket_cap(5, 12)),
             ("M5 × 40 socket cap  ·  idler axle", "1", lambda: P.socket_cap(5, 40)),
             ("M5 × 10 flat head  ·  arm plate", "4", lambda: P.flat_head(5, 10)),
             ("M5 × 10 socket cap  ·  rail brackets", "16", lambda: P.socket_cap(5, 10)),
             ("M5 T-nut, 20 series  ·  C-Beam slots", "14", P.tnut),
             ("M5 T-nut, slot 8  ·  4040 frame", "8", P.tnut),
             ("M5 washer  ·  idler", "2", P.washer),
             ("M5 × 6 grub  ·  pulley", "2", lambda: P.grub_screw(5, 6)),
             ("M4 × 6 grub  ·  coupler", "4", lambda: P.grub_screw(4, 6)),
             ("M3 × 35 socket cap  ·  arm G base", "4", lambda: P.socket_cap(3, 35)),
             ("M3 × 10 + T-nut  ·  limit switches", "8", lambda: P.socket_cap(3, 10)),
             ("M3 standoff, nut, M3 × 6  ·  controller", "4", P.standoff_mf)]
    for i, (nm, q, fn_) in enumerate(items):
        r, c = divmod(i, 3)
        cx, cy = 96 + c * 352, 712 - r * 98
        scene(ax, [Part(fn_(), STEEL)], (cx, cy), (62, 62), MM=iso_matrix(30, 30),
              clip=(cx - 44, cy - 44, cx + 44, cy + 44))
        ax.text(cx + 50, cy + 11, nm, fontsize=8.3, color=INK, va="center")
        ax.text(cx + 50, cy - 11, f"{q}×", fontsize=10.0, color="#c2410c",
                fontweight="bold", va="center")
    body(ax, "OpenBuilds low profile heads are only 1.5 mm tall: that is what lets them sit between a plate "
             "and the beam\n(2.5 mm gap) and inside the plate's 1.6 mm counterbores. Do not substitute "
             "DIN 7984 heads (2.8 to 3.5).", fs=9.2, color="#b91c1c")
    save(fig, ax, pdf, "00b_fasteners")


@page
def s1(pdf):
    fig, ax = new_page(1, "Know your plate",
                       "Fixed wheels on one edge, eccentrics on the other. Use the outer two of each row.")
    pl = Part(AS.along_py(P.gantry_plate(), (0, 0, 0)), STEEL)
    v = scene(ax, [pl], (440, 470), (520, 520), MM=iso_matrix(18, 14))
    labels = [((P.WH_X / 2, 50.3), "Ø 5.1, counterbored  ·  FIXED wheels, this edge"),
              ((P.WH_X / 2, -50.3), "Ø 7.2, counterbored  ·  ECCENTRICS, this edge"),
              ((50.3, 30.0), "tapped M5 × 4  ·  the arm plate screws in here"),
              ((10.0, 10.0), "20 × 20 nut holes in a 1.6 recess  ·  nut block (Z)"),
              ((0.0, -50.3), "middle mounts: for six-wheel builds, leave empty")]
    ys = [700, 330, 600, 500, 250]
    for ((x, y), lab), ty in zip(labels, ys):
        p = v((x, P.PLATE_T, y))
        ax.plot([p[0], 780], [p[1], ty], color=DIM, lw=0.8, zorder=200)
        tag(ax, 786, ty, lab, hi=ty in (700, 330), fs=9.2)
    body(ax, "The wheels straddle the beam's 80 mm, 100.6 mm apart. Both FIXED wheels go on one edge and "
             "both eccentrics on the\nother: the plate is drilled that way, and it is what lets two "
             "eccentrics squeeze the beam between the rows.\nOn the X carriage the fixed edge goes UP, so "
             "the fixed wheels carry the hanging mast.")
    save(fig, ax, pdf, "01")


@page
def s2(pdf):
    fig, ax = new_page(2, "Fixed wheels  ·  the stack",
                       "Screw, plate, spacer, shim, wheel, nyloc. The two outer 5.1 holes.")
    MMv = iso_matrix(236, 20)                    # from the wheel side
    parts = AS.carriage(0.0, show=("plate",))
    ex = AS.carriage(0.0, explode=22.0, show=("fixed",), hi="fixed")
    v = scene(ax, parts + ex, (500, 470), (580, 520), MM=MMv)
    for sx, sy, ecc in AS.WHEELS:
        if not ecc:
            wx, wz = sx * P.WH_X / 2, MZ + sy * P.WH_Y / 2
            axis3(ax, v, (wx, AS.PLATE_FRONT + 40, wz), (wx, AS.WHEEL_Y0 - 70, wz))
    tag(ax, 820, 690, "M5 × 30 low profile", 2, hi=True)
    tag(ax, 820, 642, "Aluminium spacer 6 mm", 2, hi=True)
    tag(ax, 820, 594, "Precision shim 10 × 5 × 1", 2, hi=True)
    tag(ax, 820, 546, "Xtreme Solid V wheel", 2, hi=True)
    tag(ax, 820, 498, "M5 nyloc", 2, hi=True)
    tool(ax, 820, 432, "3 mm hex  ·  8 mm")
    body(ax, "Heads go in the counterbores, on the plate's outer face. The shim keeps the bearing's outer race "
             "off the spacer.\nSnug the nylocs, do not torque them: you re-check every one after preload.")
    save(fig, ax, pdf, "02")


@page
def s3(pdf):
    fig, ax = new_page(3, "Eccentric wheels",
                       "The opposite edge. The hex sits between the plate and the shim.")
    MMv = iso_matrix(236, 20)
    parts = AS.carriage(0.0, show=("plate", "fixed"))
    ex = AS.carriage(0.0, explode=22.0, show=("ecc",), hi="ecc")
    v = scene(ax, parts + ex, (500, 470), (580, 520), MM=MMv)
    for sx, sy, ecc in AS.WHEELS:
        if ecc:
            wx, wz = sx * P.WH_X / 2, MZ + sy * P.WH_Y / 2
            axis3(ax, v, (wx, AS.PLATE_FRONT + 40, wz), (wx, AS.WHEEL_Y0 - 70, wz))
    tag(ax, 820, 690, "Eccentric spacer, 10 mm hex", 2, hi=True)
    tag(ax, 820, 642, "Precision shim 10 × 5 × 1", 2, hi=True)
    tag(ax, 820, 594, "Xtreme Solid V wheel", 2, hi=True)
    tag(ax, 820, 546, "M5 × 30 low profile", 2, hi=True)
    tag(ax, 820, 498, "M5 nyloc", 2, hi=True)
    body(ax, "The spacer's 2.5 mm boss drops into the 7.2 mm hole; its hex is the spacer. Set both at their "
             "LOOSEST (bore\nfurthest from the beam) before fitting, or the carriage will not go on. "
             "A thin 10 mm spanner turns them later.")
    save(fig, ax, pdf, "03")


@page
def s4(pdf):
    fig, ax = new_page(4, "Onto the rail, then set the preload",
                       "Slide on from the end. Then the one adjustment that decides the machine.")
    car = AS.carriage(170.0)
    v = scene(ax, [railp()] + car, (470, 520), (500, 420),
              MM=iso_matrix(34, 22), focus=car + [Part(AS.rail(40.0), ALU)])
    a, b = v((-60, AS.PLATE_FRONT + 20, MZ)), v((70, AS.PLATE_FRONT + 20, MZ))
    arrow2(ax, tuple(a), tuple(b))
    tool(ax, 790, 200, "thin 10 mm spanner  ·  8 mm")
    # preload inset: one eccentric stack, from the side, with the spanner turn
    ecc = [p for p in AS.carriage(0.0, show=("ecc", "plate"))]
    MMi = iso_matrix(90, 6)
    vi = inset(ax, 770, 340, 340, 360, [railp(160.0)] + AS.carriage(80.0),
               MMi, focus=[railp(160.0)] + AS.carriage(80.0), label="end view: wheels ride the top and bottom grooves")
    ax.add_patch(FancyBboxPatch((770, 236), 340, 92, boxstyle="round,pad=0,rounding_size=10",
                                facecolor="white", edgecolor="#9aa7b0", lw=1.0, zorder=320))
    rows = [("LOOSE", "#9aa3a9", "wheel spins free, carriage rocks"),
            ("RIGHT", "#15803d", "turns with light finger drag"),
            ("TIGHT", "#b91c1c", "hard to turn, wears flats in the wheel")]
    for i, (k, c_, t) in enumerate(rows):
        ax.text(786, 306 - i * 26, k, fontsize=9.6, fontweight="bold", color=c_, zorder=321)
        ax.text(850, 306 - i * 26, t, fontsize=8.8, color=DIM, zorder=321)
    body(ax, "Turn each eccentric until its wheel just grips the groove, then back off until it turns with\n"
             "light finger drag. Tighten the nyloc and re-check. Run the carriage the full length by hand:\n"
             "even resistance, no rock, no tight spot. Too loose is slop, and slop defeats hand-eye\n"
             "calibration: the camera says where the leaf is and the arm arrives somewhere else.")
    save(fig, ax, pdf, "04")


@page
def s5(pdf):
    fig, ax = new_page(5, "Build the second carriage",
                       "Identical. It rides the 1500 mm Z mast.")
    car = AS.carriage(260.0)
    scene(ax, [railp(ZL)] + car, (470, 500), (360, 330), focus=car)
    tag(ax, 830, 640, "repeat steps 1 to 4")
    body(ax, "Build and preload it on the mast now, while the method is fresh, then slide it off again: at\n"
             "step 11 the nut block goes on its back, and from then on it only goes on from the mast's end.")
    save(fig, ax, pdf, "05")


# ============================================================ X drive
@page
def s6(pdf):
    fig, ax = new_page(6, "X motor onto its plate",
                       "Four M5 × 10, from the MOTOR side, into the plate.")
    parts = AS.x_motor_plate(screws=False, tnuts=False)
    mot = AS.x_motor(explode=0.0, hi=False, screws=False)
    scr = AS.x_motor(explode=40.0, hi="screws")[1:]
    MMv = iso_matrix(214, 26)
    v = scene(ax, parts + mot + scr, (470, 480), (520, 520), MM=MMv)
    for sx in (-1, 1):
        for sy in (-1, 1):
            hx, hz = AS.X_MOTOR_X + sx * P.NEMA_HOLE_SQ / 2, MZ + sy * P.NEMA_HOLE_SQ / 2
            axis3(ax, v, (hx, AS.FRONT, hz), (hx, AS.FRONT + 120, hz))
    tag(ax, 800, 680, "M5 × 10 socket cap", 4, hi=True)
    tool(ax, 800, 610, "4 mm hex")
    body(ax, "NEMA 23 flanges are drilled through, so the heads seat on the BACK of the motor flange,\n"
             "in the pockets beside the body, and the thread takes in the plate. If the plate's four motor\n"
             "holes are plain, tap them M5 first. The boss locates in the 38.1 bore: if it will not seat,\n"
             "something is between the faces.")
    save(fig, ax, pdf, "06")


@page
def s7(pdf):
    fig, ax = new_page(7, "Pulley onto the shaft",
                       "Now, while you can reach the grub screws. After step 8 you cannot.")
    base = AS.x_motor_plate(screws=False, tnuts=False) + AS.x_motor()
    pul = AS.x_pulley(explode=26.0, hi=True)
    MMv = iso_matrix(262, 24)
    v = scene(ax, base + pul, (470, 480), (520, 520), MM=MMv)
    axis3(ax, v, (AS.X_MOTOR_X, 50, MZ), (AS.X_MOTOR_X, -20, MZ))
    tag(ax, 800, 690, "GT2 pulley 20T, 6.35 bore", 1, hi=True)
    tag(ax, 800, 642, "M5 × 6 grub screw", 2, hi=True)
    tool(ax, 800, 574, "2.5 mm hex")
    body(ax, "Boss toward the motor, flanges outboard: the toothed hub must finish 22 to 32 mm from the\n"
             "plate's back face, which is where the belt runs inside the rail. Seat the FIRST grub on the\n"
             "shaft flat. A grub on the round creeps under load and loses steps exactly like a current\n"
             "problem would.")
    save(fig, ax, pdf, "07")


@page
def s8(pdf):
    fig, ax = new_page(8, "Motor onto the rail's left end",
                       "Four M5 × 10 into T-nuts in the front-lip grooves. Pulley into the channel.")
    motor = AS.x_motor() + AS.x_pulley()
    plate = AS.x_motor_plate(explode=0.0, hi=True)
    MMv = iso_matrix(28, 22)
    focus = plate + motor
    scene(ax, [railp()] + plate + motor, (470, 500), (500, 470), MM=MMv, focus=focus)
    tag(ax, 800, 690, "M5 × 10 socket cap", 4, hi=True)
    tag(ax, 800, 642, "M5 T-nut", 4, hi=True)
    body(ax, "Flush with the rail's end. The plate sits on the two front lips and its four screws drop into\n"
             "the lip grooves, 60 mm apart. The motor never moves: the belt does the travelling, and the\n"
             "carriage stops 5 mm short of this plate.")
    save(fig, ax, pdf, "08")


@page
def s9(pdf):
    fig, ax = new_page(9, "Idler at the far end",
                       "Drill 5.2 through the web, 50 from the end. M5 × 40 from the back.")
    xi = XL - AS.X_IDLER_INSET
    stack = AS.x_idler(XL, hi=True)
    scr, rest = stack[0], stack[1:]
    out_ = [Part(mv(p.mesh, 0, 46.0 + 14.0 * k, 0), p.color) for k, p in enumerate(rest)]
    MMv = iso_matrix(-28, 22)
    v = scene(ax, [railp(), scr] + out_, (450, 500), (460, 440), MM=MMv,
              focus=out_ + [Part(mv(AS.rail(90.0), XL - 90, 0, 0), ALU)])
    axis3(ax, v, (xi, 0, MZ), (xi, 140, MZ))
    inset(ax, 790, 196, 300, 220, [railp(), scr] + AS.x_idler(XL)[1:], iso_matrix(150, 20),
          focus=[scr, Part(mv(AS.rail(70.0), XL - 70, 0, 0), ALU)],
          label="from behind: the head on the back face")
    tag(ax, 800, 690, "M5 × 40 socket cap", 1, hi=True)
    tag(ax, 800, 642, "M5 washer", 2, hi=True)
    tag(ax, 800, 594, "Idler, 9 mm", 1, hi=True)
    tag(ax, 800, 546, "M5 nyloc", 1, hi=True)
    tool(ax, 800, 480, "5.2 drill  ·  4 mm")
    body(ax, "Head on the back face, then inside the channel: washer, idler, washer, nyloc. Centre the\n"
             "hole on the web's mid-height so the idler lines up with the pulley at the other end. The\n"
             "nyloc snug, not tight: the idler has to spin freely.")
    save(fig, ax, pdf, "09")


@page
def s10(pdf):
    fig, ax = new_page(10, "Belt and clamps",
                       "Teeth in, width along the pulley axis. Both ends clamp to the carriage.")
    cx = 520.0
    drive = AS.x_motor_plate() + AS.x_motor() + AS.x_pulley() + AS.x_idler(XL)
    car = AS.carriage(cx, clamp_holes=True)
    cl = AS.x_clamps(cx, hi=True)
    belt = AS.x_belt(XL, cx, hi=False)
    MMv = iso_matrix(30, 14)
    scene(ax, [railp()] + drive + car + cl + belt, (480, 540), (560, 360), MM=MMv,
          focus=car)
    # inset: from behind, rail hidden, so the clamps and both runs read
    MMi = iso_matrix(204, 16)
    inset(ax, 760, 236, 350, 250, car[:1] + cl + AS.x_belt(XL, cx), MMi,
          focus=car[:1] + cl, label="from behind, rail hidden")
    tag(ax, 790, 710, "Belt clamp block", 2, hi=True)
    tag(ax, 790, 662, "M5 × 25 low profile", 4, hi=True)
    tag(ax, 790, 614, "GT2 9 mm, 2.8 m")
    body(ax, "Each clamp takes two screws through holes the plate already has: 10 and 30 either side of the "
             "centre, on the row 10 above it.\nClamp one end. Run the belt left inside the channel, round "
             "the pulley, back along the bottom of the channel, round the idler,\nand into the second "
             "clamp. Pull it through to tension and lock: plucked, a low clear note. Over-tension bends the "
             "motor shaft.")
    save(fig, ax, pdf, "10")


# ============================================================ Z drive
@page
def s11(pdf):
    fig, ax = new_page(11, "Nut block onto the Z carriage",
                       "Carriage OFF the mast. The block ends up inside the mast's channel, around the screw.")
    MMv = iso_matrix(244, 16)                      # side-on, from the wheel side
    car = AS.carriage(0.0)
    e = 30.0
    nb = AS.z_nut(0.0, explode=e, hi=True)
    v = scene(ax, car + nb, (420, 480), (560, 520), MM=MMv, focus=car + nb)
    for dz in (-10.0, 10.0):
        axis3(ax, v, (-10.0, AS.PLATE_FRONT + 1.4 * e, MZ + dz), (-10.0, AS.NB_Y - 2.2 * e, MZ + dz))
    # inset: true end view down the mast: the block in the channel round the screw
    MMi = iso_matrix(90, 0)
    scr = Part(AS.along_px(P.lead_screw(120.0), (20.0, AS.SCREW_Y, MZ)), STEEL)
    inset(ax, 760, 222, 350, 270, [railp(160.0)] + AS.carriage(80.0) + AS.z_nut(80.0) + [scr], MMi,
          focus=[Part(AS.rail(40.0), ALU)] + AS.carriage(80.0, show=("plate",)),
          label="end view down the mast: block in the channel")
    tag(ax, 790, 712, "M5 × 25 low profile", 2, hi=True)
    tag(ax, 790, 664, "Aluminium spacer 6 mm", 2, hi=True)
    tag(ax, 790, 616, "Anti-backlash nut block", 1, hi=True)
    tag(ax, 790, 568, "M5 hex nut, in the block's pockets", 2, hi=True)
    tool(ax, 790, 522, "3 mm hex  ·  8 mm")
    body(ax, "Screws from the plate's outer face, through the two nut holes nearest one edge of the recess "
             "(20 apart, across the\nmast), then a spacer each, the block, and a nut in each pocket. The bore "
             "runs ALONG the mast, 9.5 mm behind its mouth.\nThen slide the carriage back on from the mast's "
             "end and re-check the preload. Leave the block's tension screw for step 12.")
    save(fig, ax, pdf, "11")

@page
def s12(pdf):
    fig, ax = new_page(12, "Lead screw through the nut",
                       "Thread it in by hand, through the carriage, along the channel.")
    cx = 700.0
    car = AS.carriage(cx) + AS.z_nut(cx)
    scr = AS.z_screw(ZL, hi=True)
    MMv = iso_matrix(30, 18)
    scene(ax, [railp(ZL)] + car + scr, (470, 520), (560, 380), MM=MMv, focus=car)
    tag(ax, 800, 690, "Lead screw Tr8x8, 1500", 1, hi=True)
    body(ax, "It runs in the channel, 9.5 mm behind the mouth. Turn it through the nut by hand until it runs "
             "the full length\nwith even drag, then snug the block's tension screw until the play is gone "
             "and the drag is still light.\nA tight spot now is a bent screw or a block out of line, both "
             "cheaper to find before the motor is on.")
    save(fig, ax, pdf, "12")


@page
def s13(pdf):
    fig, ax = new_page(13, "Top end  ·  the screw hangs here",
                       "C-Beam End Mount on the mast's end, a thrust bearing in its recess, one underneath.")
    top = AS.z_end_plate(ZL, False, hi=True) + AS.z_top_bearings(ZL, hi=True)
    rest = AS.z_screw(ZL)
    MMv = iso_matrix(146, 22)
    scene(ax, [railp(ZL)] + rest + top, (450, 500), (440, 440), MM=MMv,
          focus=top + [Part(mv(AS.rail(40.0), ZL - 40, 0, 0), ALU)])
    tag(ax, 790, 700, "C-Beam End Mount 80 × 50 × 12", 1, hi=True)
    tag(ax, 790, 652, "M5 × 25 low profile, into the end taps", 4, hi=True)
    tag(ax, 790, 604, "Thrust bearing 8 × 16 × 5", 2, hi=True)
    tag(ax, 790, 556, "Lock collar 8 mm, 14 × 7", 2, hi=True)
    tool(ax, 790, 488, "3 mm hex  ·  2.5 mm hex")
    body(ax, "The mount overhangs the mast's mouth by 10 mm, toward the carriage. One bearing sits in the "
             "16.1 recess on top with a\ncollar above it; the other goes under the mount with a collar below. "
             "Tighten the collars against the bearings with the\nscrew pulled up: then it hangs from here and "
             "the coupler at the foot only ever carries torque.")
    save(fig, ax, pdf, "13")


@page
def s14(pdf):
    fig, ax = new_page(14, "Foot  ·  braked motor and coupler",
                       "Motor plate across the end, motor outside, coupler inside.")
    foot = AS.z_end_plate(0.0, True) + AS.z_motor(hi="coupler")
    scr = AS.z_screw(ZL)
    MMv = iso_matrix(34, 22)
    scene(ax, [railp(ZL)] + scr + foot, (500, 500), (480, 440), MM=MMv,
          focus=foot + [Part(AS.rail(40.0), ALU)])
    tag(ax, 820, 690, "Coupler 6.35 → 8", 1, hi=True)
    tag(ax, 820, 642, "M4 × 6 grub", 4, hi=True)
    tag(ax, 820, 594, "M5 × 12 into the end taps", 4)
    tool(ax, 820, 526, "2 mm hex")
    body(ax, "Leave 2 mm between the shaft ends inside the coupler, so it can flex. Test the brake BEFORE\n"
             "coupling: 24 V releases it, no power grips it. If it does not grip you find out when the\n"
             "power blinks and the arm lands on a tray.")
    save(fig, ax, pdf, "14")


# ============================================================ electronics
def limit_switches(xs):
    """Microswitches on the rail's top face, in the BACK top groove (the
    front one is the wheels'), lever toward the carriage, two M3 x 10 each."""
    out = []
    for x, face in xs:
        sw = P.limit_switch()
        if face < 0:
            sw = rot(sw, rz=math.pi)
        out.append(Part(mv(sw, x, 10.0, P.CB_H), HILITE))
        for dx in (-7.0, 7.0):
            out.append(Part(mv(P.socket_cap(3, 10), x + dx, 10.0, P.CB_H + 10.5), HILITE))
    return out


@page
def s15(pdf):
    fig, ax = new_page(15, "Limit switches  ·  all four",
                       "X min and X max on the rail; Z min and Z max the same way on the mast.")
    cx = 600.0
    sw = limit_switches([(Fr.X_MIN - 12.0, 1), (Fr.X_MAX + 12.0, -1)])
    base = [railp()] + AS.x_motor_plate() + AS.x_motor() + AS.carriage(cx) + AS.x_idler(XL)
    MMv = iso_matrix(18, 22)
    scene(ax, base + sw, (560, 560), (980, 260), MM=MMv, focus=[railp()] + AS.x_motor())
    MMi = iso_matrix(24, 26)
    inset(ax, 70, 236, 330, 220, base + sw, MMi,
          focus=sw[:3] + AS.carriage(Fr.X_MIN, show=("plate",)), label="X min, by the motor")
    inset(ax, 740, 236, 330, 220, base + sw, MMi,
          focus=sw[3:] + AS.x_idler(XL)[:1], label="X max, by the idler")
    tag(ax, 430, 400, "M3 × 10 + T-nut", 8, hi=True)
    body(ax, "In the rail's back top groove: the front one is where the wheels run. Each trips 5 to 10 mm\n"
             "BEFORE the hard stop. Wire them NORMALLY CLOSED, in series per axis: a cut wire then reads\n"
             "as a trip instead of silently disabling the limit.")
    save(fig, ax, pdf, "15")


@page
def s16(pdf):
    fig, ax = new_page(16, "Controller on standoffs",
                       "Panel, standoffs, board, screws. Keep the board's ground off the frame.")
    holes = [(10.0 + 80.0 * sx, 8.0 + 54.0 * sy) for sx in (0, 1) for sy in (0, 1)]
    ox, oy = 25.0, 20.0                            # board on the panel
    panel = Part(P.mounting_panel(150, 110, 3, [(x + ox, y + oy) for x, y in holes]), ALU_D)
    zb, zs, zn = 46.0, 12.0, -16.0                 # exploded heights: board, standoffs, nuts
    brd = Part(mv(P.controller_board(), ox, oy, zb), PCB)
    so = [Part(mv(P.standoff_mf(10.0), x + ox, y + oy, zs), HILITE) for x, y in holes]
    sc = [Part(mv(P.socket_cap(3, 6), x + ox, y + oy, zb + 1.8 + 30.0), HILITE) for x, y in holes]
    nu = [Part(mv(P.hex_nut(3), x + ox, y + oy, zn - 2.4), HILITE) for x, y in holes]
    MMv = iso_matrix(28, 26)
    v = scene(ax, [panel, brd] + so + sc + nu, (430, 470), (560, 540), MM=MMv)
    for x, y in holes:
        axis3(ax, v, (x + ox, y + oy, zn - 10.0), (x + ox, y + oy, zb + 46.0))
    tag(ax, 780, 712, "M3 × 6 socket cap", 4, hi=True)
    tag(ax, 780, 664, "Controller (Elecrow 4-axis FluidNC)", 1)
    tag(ax, 780, 616, "M3 hex standoff, male-female, 10", 4, hi=True)
    tag(ax, 780, 568, "Mounting panel, inside the enclosure", 1)
    tag(ax, 780, 520, "M3 nut", 4, hi=True)
    tool(ax, 780, 452, "2.5 mm hex  ·  5.5 mm")
    body(ax, "Standoffs through the panel, nuts underneath, board on top, screws down into the standoffs. "
             "Use the board's own four\nholes: the pattern drawn here is the footprint block, not the board's "
             "drawing. Never screw a board straight to the\nextrusion: its ground plane on the frame makes a loop "
             "with the motor shields. Connections: the wiring pages, next.")
    save(fig, ax, pdf, "16")


@page
def s17(pdf):
    fig, ax = new_page(17, "First motion, before the arm",
                       "Jog, calibrate steps, home. Nothing heavy on the gantry yet.")
    steps = [("Set driver current", "X 1.5 A, Z 1.8 A run, half that to hold (wiring page). Too high cooks the TMC2209s."),
             ("Jog 5 mm", "confirm direction on both axes before anything longer."),
             ("Command 100 mm", "start at X 80, Z 400 steps/mm (16 µsteps), measure, correct until commanded equals actual."),
             ("Home both axes", "and home on every power-up. FluidNC does not know where it is otherwise."),
             ("Run full travel", "ten times, both axes. Listen for a tight spot.")]
    for i, (a, b) in enumerate(steps):
        y = 660 - i * 96
        ax.add_patch(Circle((110, y), 21, facecolor="#eef2f5", edgecolor="#c3ccd2", lw=1.0))
        ax.text(110, y, str(i + 1), ha="center", va="center", fontsize=12,
                fontweight="bold", color=INK)
        ax.text(150, y + 11, a, fontsize=12.5, fontweight="bold", color=INK)
        ax.text(150, y - 13, b, fontsize=10.2, color=DIM)
    body(ax, "If the gantry is going to bind, lose steps or trip a limit wrongly, it does it now, when nothing\n"
             "expensive is bolted to it. That is the point of doing this before step 18.")
    save(fig, ax, pdf, "17")


@page
def s18(pdf):
    fig, ax = new_page(18, "Arm plate onto the Z carriage",
                       "Four M5 × 10 flat head into the plate's own tapped holes. Flush, so the arm sits flat.")
    car = AS.carriage(0.0) + AS.z_nut(0.0)
    e = 40.0
    ap = Part(AS.place(P.arm_plate(), AS.Z, AS.X, AS.Y, (0, AS.PLATE_FRONT + e, MZ)), HILITE)
    # arm plate local (x, y) = (across, along) -> bench (z, x): tapped holes at plate (+/-50.3, +/-30)
    pts = [(sx * 50.3, MZ + sy * 30.0) for sx in (-1, 1) for sy in (-1, 1)]
    sc = [Part(AS.along_py(P.flat_head(5, 10), (x, AS.PLATE_FRONT + e + 6.35 + 26.0, z)), HILITE)
          for x, z in pts]
    v = scene(ax, [railp(ZL)] + car + [ap] + sc, (450, 480), (520, 500),
              MM=iso_matrix(58, 18), focus=car + [ap] + sc)
    for x, z in pts:
        axis3(ax, v, (x, AS.PLATE_FRONT + e + 50.0, z), (x, AS.PLATE_FRONT, z))
    tag(ax, 800, 690, "Arm plate Rev B, 160 × 160 × 6.35", 1, hi=True)
    tag(ax, 800, 642, "M5 × 10 flat head, ISO 10642", 4, hi=True)
    tool(ax, 800, 574, "3 mm hex")
    body(ax, "The XL plate has four tapped M5 holes at its corners, 100.6 apart along the mast and 60 across: "
             "the arm plate's countersunk\nholes land on them. Rev A's edge slots met no hole in the real "
             "plate. Order the Rev B file (arm_plate_revB.dxf) with\nthe M3 and M4 holes TAPPED and the four "
             "M5 holes COUNTERSUNK 90° on the arm side: SendCutSend's drawing sizes are already in the file.")
    save(fig, ax, pdf, "18")


ARM_COL = {"g_base": ALU_D, "joint1": BLACKPART, "joint2": ARM, "joint3": ARM,
           "joint4": ARM, "joint5": ARM, "joint6": ARM, "joint6_flange": BLACKPART}


def arm_bench(q, y, z=MZ, x=0.0):
    T = np.eye(4)
    T[:3, :3] = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    T[:3, 3] = (x, y, z)
    out = []
    for name, (V, F) in A.pose(q, grid=0.0):
        Vw = (np.hstack([V, np.ones((len(V), 1))]) @ T.T)[:, :3]
        out.append(Part((Vw, F), ARM_COL[name], ang=33, lw=0.4))
    return out


@page
def s19(pdf):
    fig, ax = new_page(19, "The arm, last",
                       "Its G base onto the plate: four M3 × 35 through the base's outer corner holes.")
    car = AS.carriage(0.0)
    ap = Part(AS.place(P.arm_plate(), AS.Z, AS.X, AS.Y, (0, AS.PLATE_FRONT, MZ)), ALU)
    e = 70.0
    y0 = AS.PLATE_FRONT + Fr.ARM_PLATE_T + Fr.MOUNT_OFF + e
    q = list(Fr.TIGHT_Q); q[0] = 180.0           # folded, swung clear of the corner screws
    arm = arm_bench(tuple(q), y0)
    # G base local (x, y) -> bench (z, x); its top face is at local z = +2
    pts = [(gy, MZ + gx) for gx, gy in P.ARM_GBASE_HOLES]
    sc = [Part(AS.along_py(P.socket_cap(3, 35), (bx, y0 + 2.0 + 40.0, bz)), HILITE) for bx, bz in pts]
    v = scene(ax, [railp(ZL)] + car + [ap] + arm + sc, (430, 470), (560, 540),
              MM=iso_matrix(40, 24), focus=car + [ap] + arm + sc)
    for bx, bz in pts:
        axis3(ax, v, (bx, y0 + 90.0, bz), (bx, AS.PLATE_FRONT, bz))
    tag(ax, 806, 690, "myCobot 280 Pi on its G base", 1, hi=True)
    tag(ax, 806, 642, "M3 × 35 socket cap", 4, hi=True)
    tag(ax, 806, 594, "SIDE mounted: J1 horizontal")
    tool(ax, 806, 526, "2.5 mm hex, long")
    body(ax, "The G base's four outer holes are Ø 3.5 straight through its 32 mm; the arm plate has M3 taps "
             "under them. Unpowered,\nJ1 turns by hand: swing the folded arm clear of each corner in turn. "
             "Without the G base, the arm bolts to the four M4 taps\non the 44 mm square and sits 30 mm closer "
             "to the plate. Power it from its OWN brick, never the 24 V bus, and confirm\nit answers over TCP "
             "before any coordinated motion. Folded for every Z move: J2 −110, J3 −80, J4 −140, J5 −90.")
    save(fig, ax, pdf, "19")

@page
def s20(pdf):
    fig, ax = new_page(20, "Before you trust it",
                       "The safety circuit, and the checks that catch the usual faults.")
    rows = [("E-stop wired, both channels", "Two M22-K01 blocks into the G9SE-201. It cross-monitors them; one is not enough."),
            ("Two contacts, two jobs", "13-14 feeds the controller, 23-24 the Z brake (wiring pages). Sensing and lighting stay alive."),
            ("E-stop mid-move", "Motion stops, brake grips, no restart until the head is pulled up AND reset is pressed."),
            ("Power-cut test", "Pull the plug mid-travel. The mast must hold, not fall."),
            ("Limit test", "Trip each switch by hand with the axis moving toward it."),
            ("Backlash check", "Jog Z up, then down, to the same commanded point. Measure the difference.")]
    for i, (a, b) in enumerate(rows):
        y = 690 - i * 92
        ax.add_patch(Rectangle((78, y - 30), 1000, 66, facecolor="#fbfcfc",
                               edgecolor="#c3ccd2", lw=0.9))
        ax.add_patch(Rectangle((96, y - 8), 18, 18, facecolor="white", edgecolor=INK, lw=1.4))
        ax.text(136, y + 10, a, fontsize=12, fontweight="bold", color=INK)
        ax.text(136, y - 13, b, fontsize=9.8, color=DIM)
    body(ax, "Bench-testing the gantry without the safety relay is fine. Running the ARM without it is not.",
         color="#b91c1c", fs=11)
    save(fig, ax, pdf, "20")


# ============================================================ install
def cab_scene(ax, extra, box_xy, box_wh, az=32, el=20, trays=True,
              zlo=0.0, zhi=Fr.H, xlo=0.0, xhi=Fr.W, focus=None):
    base = [Part(Fr.cabinet(zlo, zhi, xlo, xhi), ALU, lw=0.45)]
    if trays:
        t = Fr.trays(zlo, zhi, xlo, xhi)
        if len(t[1]):
            base.append(Part(t, ALU_D, lw=0.4))
    return scene(ax, base + list(extra), box_xy, box_wh, MM=iso_matrix(az, el),
                 focus=focus, px=2.2)


def locator(ax, cx, cy, w=118.0, mark=None):
    s = w / Fr.W
    h = Fr.H * s
    x0, y0 = cx - w / 2, cy - h / 2
    ax.add_patch(Rectangle((x0, y0), w, h, facecolor="#f5f7f8", edgecolor="#9aa7b0",
                           lw=0.9, zorder=310))
    for z in Fr.LEVELS:
        ax.plot([x0, x0 + w], [y0 + z * s, y0 + z * s], color="#9aa7b0", lw=0.7, zorder=311)
    if mark is not None:
        a, b = mark
        ax.add_patch(Rectangle((x0 - 4, y0 + a * s), w + 8, (b - a) * s, facecolor="none",
                               edgecolor="#c2410c", lw=1.8, zorder=312))
    ax.text(cx, y0 - 14, "where this is", ha="center", fontsize=8, color=DIM, zorder=312)


@page
def s21(pdf):
    fig, ax = new_page(21, "The cabinet the gantry lands on",
                       "1397 × 559 × 1829, 40-series V-slot, five rail levels.")
    cab_scene(ax, [], (420, 468), (560, 560))
    rows = [("4 × 1829", "uprights"),
            ("13 × 1317", "width rails: 5 front, 5 back, 3 under the tray's rear edge"),
            ("11 × 479", "depth rails (were 377 at 457 deep)"),
            ("3 × 123", "short rails under the tray laps"),
            ("Tray line", "y = 203 from the front. NOTHING of the frame behind it."),
            ("Corridor", "356 mm, y = 203 to 559, all of it the gantry's")]
    for i, (a, b) in enumerate(rows):
        y = 690 - i * 60
        ax.text(746, y + 9, a, fontsize=11.6, fontweight="bold", color=INK)
        ax.text(746, y - 12, b, fontsize=9.0, color=DIM)
    body(ax, "30.07 m of 4040, still 17 sticks of 2000 mm: 11 × [1317 + 479], 3 × [1829 + 123], 2 × [1317],\n"
             "1 × [1829]. Only the eleven depth rails changed. The growing trays did not.")
    save(fig, ax, pdf, "21")


@page
def s22(pdf):
    fig, ax = new_page(22, "Why the cabinet got deeper",
                       "The one clearance that cannot be shimmed out later.")
    x0, sc = 120.0, 1.08
    yb, hb = 524.0, 148.0

    def band(y0, y1, label, fc, up=0, fs=9.0):
        ax.add_patch(Rectangle((x0 + y0 * sc, yb), (y1 - y0) * sc, hb, facecolor=fc,
                               edgecolor="#9aa7b0", lw=0.9))
        ax.text(x0 + (y0 + y1) / 2 * sc, yb + hb + 16 + up, label, ha="center",
                fontsize=fs, color=INK)

    band(0, 203, "tray  203", "#dbe7f0")
    band(203, 559, "gantry corridor  356", "#f3f6f8")
    band(Fr.RAIL_Y, Fr.RAIL_Y + 40, "X rail", "#cfd8de", up=22, fs=8)
    band(519, 559, "rear upright", "#c3ccd2", fs=8)
    af0, af1 = Fr.J1_Y - Fr.FOLD_L, Fr.J1_Y + Fr.MOUNT_OFF
    ax.add_patch(Rectangle((x0 + af0 * sc, yb + 26), (af1 - af0) * sc, hb - 52,
                           facecolor="#fde8cf", edgecolor="#c2410c", lw=1.6))
    ax.text(x0 + (af0 + af1) / 2 * sc, yb + hb / 2,
            "280 folded, no self-contact\n162.6", ha="center", va="center", fontsize=9.4,
            color="#7c2d12")
    c559 = Fr.clearances(559.0)
    ax.annotate("", xy=(x0 + 203 * sc, yb - 16), xytext=(x0 + af0 * sc, yb - 16),
                arrowprops=dict(arrowstyle="<->", color="#166534", lw=1.6))
    ax.text(x0 + (203 + af0) / 2 * sc, yb - 40, f"{c559['transit']:.1f} mm daylight",
            ha="center", fontsize=10, color="#166534", fontweight="bold")
    ax.text(x0, yb + hb + 56, "PLAN SECTION  ·  front of the cabinet at the left  ·  mm",
            fontsize=9.5, color=DIM)
    cols = [Fr.clearances(d) for d in (457.0, 533.0, 559.0)]
    tbl = [("Cabinet depth", "457  (Rev A)", "533", "559  (Rev E)")]
    for lab, k in (("Arm J1 axis, from the front", "j1_y"),
                   ("Folded arm clears the tray by", "transit"),
                   ("Flange reaches forward to", "flange_front"),
                   ("Gripper reaches forward to", "gripper_front")):
        tbl.append((lab,) + tuple(f"{c[k]:.1f}".replace("-", "−") for c in cols))
    for i, r in enumerate(tbl):
        y = 418 - i * 40
        ax.add_patch(Rectangle((78, y - 16), 1000, 36, facecolor="#eef2f5" if i == 0 else "#f5f7f8",
                               edgecolor="#c3ccd2", lw=0.8))
        ax.text(94, y, r[0], fontsize=10.2, va="center",
                fontweight="bold" if i == 0 else "normal", color=INK)
        for k, v_ in enumerate(r[1:]):
            neg = v_.startswith("−") and i in (2,)
            ax.text(640 + k * 150, y, v_, fontsize=10.2, va="center", ha="center",
                    color="#b91c1c" if neg else INK, fontweight="bold" if i == 0 else "normal")
    body(ax, "The arm crosses a tray plane every time it changes tier, and the shortest fold it can reach\n"
             "without one link touching another is 162.6 mm, set by its own shoulder. At 457 deep it would\n"
             f"overlap the tray by {-cols[0]['transit']:.0f} mm. Measured on Elephant Robotics' mesh, collision checked.")
    save(fig, ax, pdf, "22")


@page
def s23(pdf):
    fig, ax = new_page(23, "X rail onto the rear uprights",
                       "Cut to 1397. Two bent brackets at each end. This one must be level.")
    rail = Part(Fr.x_rail(), HILITE)
    br = [Part(m, (0.33, 0.52, 0.80) if nm == "bracket" else STEEL)
          for nm, m in Fr.x_rail_brackets(explode=0.0)]
    brx = [Part(m, (0.33, 0.52, 0.80) if nm == "bracket" else STEEL)
           for nm, m in Fr.x_rail_brackets(explode=9.0)]
    cab = Part(Fr.cabinet(1560.0, Fr.H, 0.0, Fr.W, 330.0, Fr.D), ALU, lw=0.45)
    v = scene(ax, [cab, rail] + br, (560, 655), (900, 190), MM=iso_matrix(200, 24),
              focus=np.array([[0.0, 330.0, 1600.0], [Fr.W, Fr.D, Fr.H]]), clip=(24, 560, 1128, 772))
    ax.text(40, 750, "from the front, above", fontsize=8.6, color=DIM, zorder=320)
    cabL = Part(Fr.cabinet(1610.0, Fr.H, 0.0, 170.0, 430.0, Fr.D), ALU, lw=0.45)
    cabR = Part(Fr.cabinet(1610.0, Fr.H, Fr.W - 170.0, Fr.W, 430.0, Fr.D), ALU, lw=0.45)
    inset(ax, 40, 196, 520, 350, [cabL, rail] + brx, iso_matrix(150, 22),
          focus=np.array([[0.0, 440.0, 1640.0], [130.0, Fr.D, Fr.H]]),
          label="LEFT end, from the front-right: top bracket just inboard of the depth rail")
    inset(ax, 590, 196, 520, 350, [cabR, rail] + brx, iso_matrix(210, 22),
          focus=np.array([[Fr.W - 130.0, 440.0, 1640.0], [Fr.W, Fr.D, Fr.H]]),
          label="RIGHT end, from the front-left: the same, mirrored")
    body(ax, "The rail's last 40 mm at each end sit UNDER the top depth rails, so nothing can bolt to its top "
             "face there. TOP bracket: leg on the rail's top face just inboard,\n2 × M5 into T-nuts in the "
             "front top groove; leg up the top back rail's front face, 2 × M5 into slot-8 T-nuts. BOTTOM "
             "bracket: under the rail, 2 × M5 in the front\nbottom groove; leg down the rear upright, 2 × M5 "
             "into its slot. All M5 × 10. Level the top face before the last screw: tilt becomes height "
             f"error across {Fr.X_TRAVEL:.0f} mm of travel.", fs=9.4)
    save(fig, ax, pdf, "23")


@page
def s24(pdf):
    fig, ax = new_page(24, "Hang the Z mast",
                       "X carriage and X drive on the rail first, then the mast onto the carriage.")
    pr = Fr.gantry_parts(x=700.0, z=1300.0, hi="mast")
    cab_scene(ax, pr, (420, 500), (560, 540), az=-36, el=16, trays=False)
    tag(ax, 790, 700, "C-Beam mast, 1500, Z drive built", 1, hi=True)
    tag(ax, 790, 652, "M5 × 10 low profile + T-nut", 6, hi=True)
    body(ax, "Six bolts through the X plate's holes at (±30, −30 / 0 / +30), heads on the rail side: low profile "
             "heads are 1.5 mm and the gap\nto the rail is 2.5. T-nuts in the mast's two outer back grooves. Top "
             "at 1789, foot at 289. Check plumb both ways with the carriage\nmid-rail, then at each end. If "
             "plumb changes across the travel, the rail is not level.")
    save(fig, ax, pdf, "24")


@page
def s25(pdf):
    fig, ax = new_page(25, "The Z drive, installed",
                       "Motor at the foot, screw hung from the top. Nothing above the cabinet.")
    pr = Fr.gantry_parts(x=700.0, z=1300.0, hi="zmotor")
    MMv = iso_matrix(90, 0)                     # right-hand elevation
    v = cab_scene(ax, pr, (400, 470), (300, 600), az=90, el=0, trays=True)
    top_cab, top_mast = Fr.H, Fr.MAST_Z0 + Fr.MAST_L
    foot = Fr.MAST_Z0
    mot_bot = foot - 6.0 - 76.0 - 43.0
    yref = Fr.MAST_Y0 - 140.0
    for zz, lab, dy in ((top_cab, f"cabinet top  {top_cab:.0f}", 10),
                        (top_mast + 19.5, f"top collar  {top_mast + 19.5:.1f}", -10),
                        (foot, f"mast foot  {foot:.0f}", 8),
                        (mot_bot, f"motor bottom  {mot_bot:.0f}", -8)):
        p0 = v((700.0, Fr.MAST_Y0 - 10.0, zz))
        ax.plot([p0[0], 630, 640], [p0[1], p0[1], p0[1] + dy], color=DIM, lw=0.7,
                ls=(0, (3, 3)), zorder=200)
        ax.text(648, p0[1] + dy, lab, fontsize=9.4, color=INK, va="center", zorder=201)
    tag(ax, 830, 690, "Braked NEMA 23 + coupler", 1, hi=True)
    body(ax, "Seen from the right-hand side, front of the cabinet to the LEFT. The top collar finishes\n"
             f"{top_cab - top_mast - 19.5:.1f} mm under the cabinet's top: a motor up there would stand "
             "proud of it. The screw\nhangs from the top bearings, so the coupler at the foot only ever "
             "carries torque.")
    save(fig, ax, pdf, "25")


@page
def s26(pdf):
    fig, ax = new_page(26, "Z carriage, arm plate, arm",
                       "Fold the arm before the first Z move, and keep it folded between tiers.")
    pr = Fr.gantry_parts(x=700.0, z=880.0, q=Fr.TIGHT_Q, hi="zcar")
    cab_scene(ax, pr, (420, 520), (580, 440), az=32, el=14,
              zlo=700.0, zhi=1060.0, xlo=520.0, xhi=880.0,
              focus=np.array([[540, 150, 700.0], [860, Fr.D, 1060.0]]))
    locator(ax, 1000, 290, mark=(700, 1060))
    ax.text(1000, 150, "mast and frame shown cut", ha="center", fontsize=8.4, color=DIM,
            zorder=312)
    tag(ax, 742, 700, "Z carriage", 1, hi=True)
    tag(ax, 742, 652, "Arm plate, 160 sq × 6.35", 1)
    tag(ax, 742, 604, "myCobot 280 Pi, side mounted", 1)
    body(ax, "J1 horizontal, pointing into the tier: upright, the base radius would eat 80 mm of reach and the\n"
             "arm would stand 437 mm tall in a 341 mm opening. Fold: J2 −110, J3 −80, J4 −140, J5 −90,\n"
             "collision checked. An extended arm crossing a tray plane is the one crash this machine can do\n"
             "to itself at full torque.")
    save(fig, ax, pdf, "26")


@page
def s27(pdf):
    fig, ax = new_page(27, "Commissioned",
                       "Working envelope, and the six checks before you walk away.")
    pr = Fr.gantry_parts(x=700.0, z=560.0, q=(-90, -40, -55, -85, 0, 0))
    cab_scene(ax, pr, (300, 462), (470, 540), az=214, el=18)
    c = Fr.clearances()
    rows = [("X travel", f"{Fr.X_TRAVEL:.0f}, motor plate to idler"),
            ("Z travel", "1350 usable; tiers at 345, 1005, 1437"),
            ("Flange reach", f"292.6 from J1, forward to y = {c['flange_front']:.0f}"),
            ("With the gripper", f"forward to y = {c['gripper_front']:.0f}: the whole tray"),
            ("Folded transit", f"162.6 long, {c['transit']:.1f} clear of the tray line"),
            ("Working height", "263, inside the 341 tier opening")]
    for i, (a, b) in enumerate(rows):
        y = 752 - i * 52
        ax.text(576, y + 8, a, fontsize=10.4, fontweight="bold", color=INK, zorder=302)
        ax.text(576, y - 10, b, fontsize=8.8, color=DIM, zorder=302)
    checks = ["Home X and Z, power-cycle, home again. Same zero both times.",
              "Fold the arm, run Z full travel. Nothing touches anything.",
              "E-stop mid-move: motion stops, brake grips, no reset until released.",
              "Pull the plug mid-travel. The mast holds.",
              "Jog to each tier, check the arm reaches the back row of pots.",
              "Hand-eye calibrate AT the tier it works at, not once at the top."]
    for i, c_ in enumerate(checks):
        y = 410 - i * 34
        ax.add_patch(Rectangle((578, y - 8), 15, 15, facecolor="white", edgecolor=INK,
                               lw=1.3, zorder=302))
        ax.text(608, y, c_, fontsize=9.3, color=INK, va="center", zorder=302)
    body(ax, "The mast is a 1.5 m cantilever off four V wheels. Expect 1 to 2 mm of forward lean at the\n"
             "foot that is not there at the top, which is why calibration is per tier.")
    save(fig, ax, pdf, "27")


# ================================================================ wiring
import wiring_pages as WR
_MS = sys.modules[__name__]


import tools_page as TL

COVER_PNG = os.environ.get("GANTRY_COVER",
                           os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover", "cover.png"))


@page
def p_cover(pdf):
    """Full-bleed render on top, title block underneath."""
    fig = plt.figure(figsize=(11.5, 9.0), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1150); ax.set_ylim(0, 900)
    if os.path.exists(COVER_PNG):
        img = plt.imread(COVER_PNG)
        h, w = img.shape[:2]
        H = 1150.0 * h / w
        ax.imshow(img, extent=(0, 1150, 900 - H, 900), zorder=1, interpolation="lanczos")
        y0 = 900 - H
    else:
        ax.add_patch(Rectangle((0, 190), 1150, 710, facecolor="#e8edf0", edgecolor="none"))
        ax.text(575, 545, "cover render not found:\n" + COVER_PNG, ha="center", va="center", color=DIM)
        y0 = 190
    ax.set_aspect("auto")
    t = ax.text(48, y0 - 50, "Maag", fontsize=34, fontweight="bold", family=TITLE_FONT, color=INK, va="center")
    fig.canvas.draw()
    bb = t.get_window_extent().transformed(ax.transData.inverted())
    ax.text(bb.x1 + 18, y0 - 47, "Modular Agentic Autonomous Greenhouse", fontsize=14, fontweight="medium",
            family=TITLE_FONT, color=INK, va="center")
    ax.text(50, y0 - 100, f"Gantry assembly instructions, {REV}.  The X/Z gantry and the myCobot 280 arm "
                          "for the 1397 × 559 × 1829 cabinet.", fontsize=12.5, color=DIM, va="center")
    ax.text(1102, y0 - 46, "27 steps  ·  tools  ·  wiring", fontsize=11, color=INK, ha="right", va="center")
    ax.text(1102, 26, "Rendered from the same models the steps are drawn from: Elephant Robotics' arm and "
                      "gripper meshes, OpenBuilds' C-Beam parts.", fontsize=7.6, color=DIM, ha="right")
    pdf.savefig(fig); fig.savefig(f"{OUT}/d_000_cover.png", dpi=130); plt.close(fig)


@page
def p_tools(pdf):
    TL.page_tools(_MS, pdf)


@page
def w1(pdf):
    WR.page_power(_MS, pdf)


@page
def w2(pdf):
    WR.page_motion(_MS, pdf)


def _order():
    """Wiring goes between the controller (16) and first motion (17)."""
    names = [f.__name__ for f in PAGES]
    for nm in ("w1", "w2"):
        f = PAGES.pop(names.index(nm)); names.remove(nm)
        PAGES.insert(names.index("s17"), f); names.insert(names.index("s17"), nm)
    f = PAGES.pop(names.index("p_tools")); names.remove("p_tools")
    k = names.index("p_inv2") + 1
    PAGES.insert(k, f); names.insert(k, "p_tools")
    f = PAGES.pop(names.index("p_cover")); names.remove("p_cover")
    PAGES.insert(0, f); names.insert(0, "p_cover")


_order()


if __name__ == "__main__":
    only = sys.argv[1:]
    path = f"{OUT}/Gantry_Assembly_Instructions_RevE.pdf"
    if only:
        class _N:
            def savefig(self, *a, **k): pass
        for fn in PAGES:
            if fn.__name__ in only:
                fn(_N()); print(fn.__name__, "ok")
        sys.exit(0)
    with PdfPages(path) as pdf:
        for fn in PAGES:
            fn(pdf); print(fn.__name__, "ok", flush=True)
    print("saved", path, f"({len(PAGES)} pages)")
