#!/usr/bin/env python3
"""Maag frame and trays: assembly instructions, Frame Rev A (design 0.4.0).

Every drawing is generated from cabinet.py, the same model the gantry's
cabinet uses, so a frame page and a gantry page cannot disagree.

Frame Rev A is the first booklet for the cabinet. It carries the bracket
schedule Rev 6 (cabinet.py explains why the Rev 5 end taps are gone) and the
tray DXFs Rev 4, with the base pan DXFs regenerated for the 559 depth.

    python make_frame_booklet.py              # whole booklet
    python make_frame_booklet.py s3 s7        # just those pages, PNG only
"""
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "booklet"))
sys.path.insert(0, os.path.join(_HERE, "..", "gantry"))

import maagbook as B                                                   # noqa: E402
from maagbook import (new_page, scene, inset, save, arrow2, axis3, tag, body, tool, note,   # noqa: E402
                      panel, leader, checkbox_rows, Circle, Rectangle, FancyBboxPatch, Polygon,
                      TITLE_FONT, INK, DIM, ACCENT, WARN, OK, AXIS, EDGE, RULE, CHIP, PANEL)
from kit3d import (Part, iso_matrix, merge, mv, rot, box, cylinder, ALU, ALU_D, STEEL,   # noqa: E402
                   BLACKPART, HILITE)
import cabinet as C                                                    # noqa: E402

import matplotlib.pyplot as plt                                        # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages                   # noqa: E402

REV = "Frame Rev A"
DESIGN = "0.4.0"
OUT = os.environ.get("FRAME_OUT", os.path.join(_HERE, "build"))
B.configure(REV, OUT)
PAGES = []

BRACKET = np.array([0.58, 0.61, 0.65])     # cast gusset
HIDDEN = np.array([0.44, 0.47, 0.50])      # zinc hidden connector
SHEET = np.array([0.95, 0.96, 0.97])       # 5052 sheet: light, its top face reads mid grey
TPU = np.array([0.90, 0.93, 0.94])
NUTC = np.array([0.66, 0.69, 0.72])
INKISH = np.array([0.22, 0.24, 0.26])     # zip ties

LV = C.LEVELS
TOP = LV[-1]
POSTS = ("FL", "FR", "BL", "BR")


def page(fn):
    PAGES.append(fn)
    return fn


# ============================================================ build states
def level_members(k):
    labs = [f"F{k}", f"B{k}", f"L{k}", f"R{k}"]
    if LV[k] in C.TIERS:
        labs += [f"S{k}", f"M{k}"]
    if k == 0:
        labs += ["M0"]
    return labs


def level_joints(k, kind=None, posts=None):
    out = []
    for j in C.joints():
        if j.level != k:
            continue
        if kind and j.kind != kind:
            continue
        if posts is True and j.b not in POSTS:
            continue
        if posts is False and j.b in POSTS:
            continue
        out.append(j.label)
    return out


def state(upto):
    """Members, joints, sheets and feet present after step `upto` (the
    booklet's own step numbers)."""
    m, j, sh, feet = set(), set(), set(), False
    if upto >= 5:
        m |= {"F0", "B0", "M0"}; j |= {"M0-F0", "M0-B0"}
    if upto >= 6:
        m |= {"L0", "R0"}; j |= set(level_joints(0, "hidden"))
    if upto >= 7:
        m |= set(POSTS)
    if upto >= 8:
        j |= set(level_joints(4))
    if upto >= 9:
        m |= set(level_members(4))
    for k, (a, b, c) in ((1, (11, 12, 13)), (2, (14, 14, 14)), (3, (14, 14, 14))):
        if upto >= a:
            j |= set(level_joints(k, posts=True))
        if upto >= b:
            m |= {f"F{k}", f"B{k}", f"L{k}", f"R{k}"}
        if upto >= c:
            m |= {f"S{k}", f"M{k}"}; j |= set(level_joints(k, posts=False))
    if upto >= 15:
        feet = True
    if upto >= 19:
        sh |= {("basepan_DOWN", 0.0), ("basepan_UP", 0.0)}
    if upto >= 20:
        for z in C.TIERS:
            sh |= {("tray_DOWN", z), ("tray_UP", z)}
    return m, j, sh, feet


def cab(upto, hi_m=(), hi_j=(), hi_sh=(), lo=None, hi=None, explode_m=None, explode_j=None,
        drop_m=(), drop_j=(), feet=None, lw=0.45, extra_m=(), extra_j=(), nuts_for=()):
    """Parts for the cabinet as built after step `upto`.

    hi_*: drawn in the new-part colour. explode_m: {label: (dx, dy, dz)}.
    lo/hi: trim box for details. extra_*: add parts not yet in the state."""
    m, j, sh, ft = state(upto)
    m = (m | set(extra_m)) - set(drop_m)
    j = (j | set(extra_j)) - set(drop_j)
    explode_m = explode_m or {}
    explode_j = explode_j or {}
    out = []
    lo_a = np.array(lo) if lo is not None else None
    hi_a = np.array(hi) if hi is not None else None
    for mem in C.members():
        if mem.label not in m:
            continue
        mm = mem.mesh(lo_a, hi_a)
        if mm is None:
            continue
        d = explode_m.get(mem.label)
        if d is not None:
            mm = mv(mm, *d)
        out.append(Part(mm, HILITE if mem.label in hi_m else ALU, lw=lw, ang=30))
    for jt in C.joints():
        if jt.label not in j:
            continue
        mm = jt.bracket(explode_j.get(jt.label, 0.0))
        if lo_a is not None and not _inside(mm, lo_a, hi_a):
            continue
        col = HILITE if jt.label in hi_j else (BRACKET if jt.kind == "gusset" else HIDDEN)
        out.append(Part(mm, col, lw=0.45, ang=30))
    for nm, z in sh:
        mm = C.sheet_world(nm, z)
        out.append(Part(mm, HILITE if (nm, z) in hi_sh else SHEET, lw=0.4, ang=30))
    if (ft if feet is None else feet):
        out.append(Part(C.feet_world(), TPU, lw=0.45, ang=30))
    return out


def _inside(mesh, lo, hi):
    V = mesh[0]
    a, b = V.min(0), V.max(0)
    return np.all(b > lo - 1) and np.all(a < hi + 1)


def fbox(lo, hi):
    """The eight corners of a box, for focusing a scene on a region."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])


def view(az=34, el=24):
    return iso_matrix(az, el)


def locator(ax, cx, cy, w=118.0, mark=None, label="where this is"):
    s = w / C.W
    h = C.H * s
    x0, y0 = cx - w / 2, cy - h / 2
    ax.add_patch(Rectangle((x0, y0), w, h, facecolor=PANEL, edgecolor=EDGE, lw=0.9, zorder=310))
    for z in LV:
        ax.plot([x0, x0 + w], [y0 + (z + 20) * s, y0 + (z + 20) * s], color=EDGE, lw=0.7, zorder=311)
    if mark is not None:
        a, b = mark
        ax.add_patch(Rectangle((x0 - 4, y0 + a * s), w + 8, (b - a) * s, facecolor="none",
                               edgecolor=ACCENT, lw=1.8, zorder=312))
    ax.text(cx, y0 - 14, label, ha="center", fontsize=8, color=DIM, zorder=312)


def stub(label, L):
    """A short length of a member's stick for the parts page."""
    return C.stick(L, "x")


# ============================================================ parts
@page
def p_parts(pdf):
    fig, ax = new_page(None, "Frame and trays  ·  parts",
                       "Count everything first. Quantities cover the complete cabinet.")
    items = [("Post  ·  4040, 1829", "4", lambda: C.stick(260, "x"), ALU),
             ("Rail  ·  4040, 1317", "13", lambda: C.stick(200, "x"), ALU),
             ("Rail  ·  4040, 479", "11", lambda: C.stick(150, "x"), ALU),
             ("Rail  ·  4040, 123", "3", lambda: C.stick(123, "x"), ALU),
             ("Gusset 3540, PETOX", "44", C.gusset_local, BRACKET),
             ("Hidden connector, TOCLUX", "10", C.hidden_local, HIDDEN),
             ("Tray, DOWN piece", "3", lambda: C.sheet_local("tray_DOWN"), SHEET),
             ("Tray, UP piece", "3", lambda: C.sheet_local("tray_UP"), SHEET),
             ("Base pan, DOWN piece", "1", lambda: C.sheet_local("basepan_DOWN"), SHEET),
             ("Base pan, UP piece", "1", lambda: C.sheet_local("basepan_UP"), SHEET),
             ("Foot  ·  TPU 95A, printed", "4", C.foot_mesh, TPU),
             ("Drain bulkhead, 1/2 in", "3", bulkhead, BLACKPART)]
    for i, (nm, q, fn_, col) in enumerate(items):
        r, c = divmod(i, 4)
        cx, cy = 96 + c * 262, 700 - r * 168
        MMi = iso_matrix(30, 30) if i not in (6, 7, 8, 9) else iso_matrix(24, 40)
        scene(ax, [Part(fn_(), col, ang=30, lw=0.5)], (cx + 20, cy + 6), (150, 96), MM=MMi,
              clip=(cx - 74, cy - 52, cx + 114, cy + 62))
        ax.text(cx - 60, cy - 66, nm, fontsize=8.6, color=INK, va="center")
        ax.text(cx - 60, cy - 86, f"{q}×", fontsize=9.8, color=ACCENT, fontweight="bold", va="center")
    body(ax, "4040 is EU slot 8, one slot per face. 30.075 m in all: 31 pieces from 17 sticks of 2000 (step 2). "
             "Gussets: 20 owned plus two more PETOX\nsets of 20, so 16 spare. Sheets: 5052-H32, 0.063 in (1.6), "
             "laser cut and bent from the Rev 4 DXFs. Feet: printed, step 4.", fs=9.0, color=DIM)
    save(fig, ax, pdf, "00_parts")


def slot_section(ax, cx, cy, s, case, label):
    """True-scale section through a sheet bolt in the rail's top slot:
    rail, T-nut, sheet(s), washer, screw. s = px per mm, (cx, cy) = slot mouth."""
    from matplotlib.patches import Polygon as Poly
    z = cy
    # rail top band, 40 wide, 18 deep, with the slot cut
    outer = [(-20, 0), (-4.1, 0), (-4.1, -4.3), (-8.25, -4.3), (-8.25, -7.0), (-3.0, -12.25),
             (3.0, -12.25), (8.25, -7.0), (8.25, -4.3), (4.1, -4.3), (4.1, 0), (20, 0), (20, -18), (-20, -18)]
    P = [(cx + u * s, z + v * s) for u, v in outer]
    ax.add_patch(Poly(P, closed=True, facecolor="#dde3e7", edgecolor=INK, lw=0.8, zorder=20))
    ax.plot([cx - 20 * s, cx + 20 * s], [z - 18 * s, z - 18 * s], color="white", lw=2.0, zorder=21)
    # T-nut under the lips
    ax.add_patch(Rectangle((cx - 7.9 * s, z - 8.3 * s), 15.8 * s, 4.0 * s, facecolor="#9aa6ae", edgecolor=INK, lw=0.7, zorder=22))
    ax.add_patch(Rectangle((cx - 3.9 * s, z - 4.3 * s), 7.8 * s, 0.0001, facecolor="none", edgecolor="none", zorder=22))
    t = C.T_SHEET
    layers = [("sheet", t)]
    if case == "UP":
        layers = [("shim", 1.6), ("sheet", t)]
    if case == "lap":
        layers = [("sheet", t), ("sheet", t)]
    y = 0.0
    for nm, th in layers:
        w = 8.0 if nm == "shim" else 20.0
        col = "#c9d1d6" if nm == "shim" else "#eef1f3"
        ax.add_patch(Rectangle((cx - w * s, z + y * s), 2 * w * s, th * s, facecolor=col, edgecolor=INK, lw=0.7, zorder=23))
        y += th
    ax.add_patch(Rectangle((cx - 8 * s, z + y * s), 16 * s, 1.6 * s, facecolor="#c9d1d6", edgecolor=INK, lw=0.7, zorder=24))
    y += 1.6
    L = 12.0 if case == "DOWN" else 16.0
    ax.add_patch(Rectangle((cx - 4 * s, z + (y - L) * s), 8 * s, L * s, facecolor="#7d8890", edgecolor=INK, lw=0.7, zorder=25))
    hd = [(-7, 0), (7, 0), (7, 1.1), (5.3, 3.4), (2.8, 4.4), (2.5, 4.4), (2.5, 1.8), (-2.5, 1.8), (-2.5, 4.4),
          (-2.8, 4.4), (-5.3, 3.4), (-7, 1.1)]
    ax.add_patch(Poly([(cx + u * s, z + (y + v) * s) for u, v in hd], closed=True, facecolor="#7d8890",
                      edgecolor=INK, lw=0.7, zorder=25))
    ax.add_patch(Rectangle((cx - 4 * s, z + y * s), 8 * s, 1.8 * s - 0.01, facecolor="#7d8890", edgecolor="none",
                           zorder=25.5))
    tip = y - L
    spare = C.SLOT_DEPTH + tip
    xd = cx + 24 * s
    for yy in (z + tip * s, z - C.SLOT_DEPTH * s):
        ax.plot([cx + 4 * s, xd + 4], [yy, yy], color=OK, lw=0.6, ls=(0, (2, 2)), zorder=30)
    ax.plot([xd, xd], [z + tip * s, z - C.SLOT_DEPTH * s], color=OK, lw=1.3, zorder=30)
    for yy in (z + tip * s, z - C.SLOT_DEPTH * s):
        ax.plot([xd - 4, xd + 4], [yy, yy], color=OK, lw=1.3, zorder=30)
    ax.text(xd + 8, z + (tip - C.SLOT_DEPTH) / 2 * s, f"{spare:.1f} clear", fontsize=8.4, color=OK,
            va="center", fontweight="bold", zorder=30)
    ax.text(cx, z - 23 * s, label, fontsize=8.6, color=INK, ha="center", zorder=30)


def bulkhead():
    """1/2 in bulkhead: flange, threaded body, nut. Axis along z."""
    return C.bulkhead_mesh(0.0, 0.0, 0.0)


@page
def p_fasteners(pdf):
    fig, ax = new_page(None, "Frame and trays  ·  fasteners",
                       "Every screw in the build. Lay them out in labelled pots first.")
    items = [("M8 × 16 cap screw  ·  gussets", "88", lambda: C.cap_screw(8, 16, detail=True)),
             ("M8 washer  ·  gussets", "88", C.washer8),
             ("M8 drop-in T-nut  ·  gussets", "88", C.tnut8),
             ("M6 grub  ·  hidden connectors", "20", lambda: C.grub6(8, detail=True)),
             ("M8 × 12 button head  ·  one sheet", "28", lambda: C.button_head(8, 12, detail=True)),
             ("M8 × 16 button head  ·  two layers", "32", lambda: C.button_head(8, 16, detail=True)),
             ("M8 washer  ·  under sheet heads", "60", C.washer8),
             ("M8 washer  ·  shims, UP pieces", "28", C.washer8),
             ("M8 drop-in T-nut  ·  sheets", "60", C.tnut8)]
    for i, (nm, q, fn_) in enumerate(items):
        r, c = divmod(i, 3)
        cx, cy = 96 + c * 352, 700 - r * 118
        scene(ax, [Part(fn_(), STEEL, ang=30, lw=0.5)], (cx, cy), (78, 78), MM=iso_matrix(30, 32),
              clip=(cx - 50, cy - 50, cx + 50, cy + 50), px=7.0)
        ax.text(cx + 60, cy + 11, nm, fontsize=8.3, color=INK, va="center")
        ax.text(cx + 60, cy - 11, f"{q}×", fontsize=10.0, color=ACCENT, fontweight="bold", va="center")
    ax.text(60, 398, "Cap screws, gusset washers and grubs come in the PETOX and TOCLUX boxes. Buy 150 "
                     "drop-in T-nuts: 88 for the gussets, 60 for the sheets.", fontsize=9.4, color=INK)
    ax.text(60, 374, "The PETOX boxes come with SLIDE-IN nuts, which only enter a slot from its end: keep them "
                     "as spares. DIN 125 washers are 1.6 thick: that is the shim.", fontsize=9.4, color=INK)
    ax.text(60, 350, "Also: neutral-cure silicone, 1 tube (steps 16 and 18); the anti-tip brackets and wall anchors, "
                     "BOM G015 (step 21).", fontsize=9.4, color=INK)
    for k, (case, lab) in enumerate((("DOWN", "one sheet  ·  M8 × 12"), ("UP", "UP piece on its shim  ·  M8 × 16"),
                                     ("lap", "the lap, two sheets  ·  M8 × 16"))):
        slot_section(ax, 230 + k * 330, 232, 3.7, case, lab)
    d = C.screw_depths()
    body(ax, "Never let a screw bottom in the slot: it feels tight and clamps nothing. On a 12.25 deep slot "
             f"the M8 × 12 stops {d['DOWN']['spare']:.1f} short of\nthe floor, the M8 × 16 through two layers "
             f"{d['UP']['spare']:.1f} short. If step 1 measures your slot shallower, shorten both by the "
             "difference.", fs=9.2, color=WARN)
    save(fig, ax, pdf, "00b_fasteners")



# ============================================================ tools
def _tools():
    import tools_lib as T
    from tools_page import hex_key, spirit_level
    hacksaw = T.hacksaw

    def keys():
        out = []
        for i, (af, L1, L2) in enumerate(((3.0, 125, 23), (5.0, 160, 34), (6.0, 172, 38))):
            for m, c in hex_key(af, L1, L2):
                out.append((mv(m, 0, 0, -i * 11.0), c))
        return out

    return [
        (T.calipers, "Calipers", "150 mm, digital", "the profile, 1; the feet's\nbore and fit, 4", (20, 45)),
        (T.tape_measure, "Tape measure", "5 m", "the cut list, 2; the level marks, 3;\nthe diagonals, 10", (32, 26)),
        (T.combination_square, "Square", "300 mm combination", "every mark squared round the post, 3;\nevery cut checked, 2",
         (25, 40)),
        (hacksaw, "Saw", "mitre saw, non-ferrous blade,\nor hacksaw and mitre box", "31 cuts, 2. Deburr every end", (20, 40)),
        (keys, "Hex keys, ball end", "3 · 5 · 6 mm, long series",
         "3: hidden connector grubs, 6 to 9\n5: sheet screws, 17 to 19\n6: gusset screws, 5 to 14", (30, 34)),
        (spirit_level, "Spirit level", "600 mm, with a plumb vial", "posts plumb, 7 and 10;\nthe falls and the top, 21", (25, 30)),
        (T.f_clamps, "Clamps", "2 F-clamps, 300", "a rail on its ledges while you\nbolt it, 9 and 12", (25, 22)),
        (T.pry_bar_and_block, "Bar and a block", "flat bar and a wood offcut", "lifting each corner\n25 mm for its foot, 15",
         (25, 35)),
        (T.step_drill, "Step drill", "to the bulkhead's hole size", "the Ø 6 drain pilots, 16", (25, 25)),
        (T.caulking_gun, "Caulking gun", "and neutral-cure silicone", "tray corners and laps, 16 to 19", (28, 18)),
    ]


@page
def p_tools(pdf):
    fig, ax = new_page(None, "Tools",
                       "Everything the 21 steps need. Metric throughout; nothing is inch but the drain fittings.")
    for i, (fn, name, size, steps, (az, el)) in enumerate(_tools()):
        r, c = divmod(i, 4)
        x0, ytop = 40 + c * 270, 762 - r * 228
        ax.add_patch(FancyBboxPatch((x0, ytop - 218), 258, 218, boxstyle="round,pad=0,rounding_size=8",
                                    facecolor="none", edgecolor=B.FRAMEC, lw=1.0, zorder=5))
        parts = [Part(m, col, ang=30, lw=0.45) for m, col in fn()]
        scene(ax, parts, (x0 + 129, ytop - 62), (226, 100), MM=iso_matrix(az, el),
              clip=(x0 + 2, ytop - 120, x0 + 256, ytop - 2), px=5.0)
        ax.text(x0 + 14, ytop - 132, name, fontsize=9.2, fontweight="semibold", family=TITLE_FONT,
                color=INK, va="top")
        ax.text(x0 + 14, ytop - 149, size, fontsize=7.8, color=INK, va="top", linespacing=1.3)
        ny = ytop - 149 - 14.5 * (size.count("\n") + 1) - 4
        ax.text(x0 + 14, ny, "steps: " + steps, fontsize=7.4, color=DIM, va="top", linespacing=1.35)
    ax.text(600, 200, "And a 3D printer for the feet (step 4),\na helper for steps 7 to 9, and a\n"
                      "few 5 mm packers for the base (step 7).", fontsize=9.6, color=INK, va="top", linespacing=1.5)
    ax._body_y = 60.0
    save(fig, ax, pdf, "00c_tools")


# ============================================================ every joint
@page
def p_joints(pdf):
    fig, ax = new_page(None, "Every joint, and what holds it",
                       "54 joints, 44 gussets, 10 hidden connectors. No end taps, no drilling, any order.")
    parts = cab(99, feet=True)
    hid = [p for p in parts]
    v = scene(ax, hid, (330, 470), (520, 560), MM=view(212, 18), px=2.2)
    J = C.joints()
    from collections import Counter
    rows = [("16", "gusset under each front and back rail end, levels 1 to 4, leg down the post"),
            ("14", "gusset under each side rail end, levels 1 to 4, leg down the post"),
            ("12", "gusset on the front side of each shelf and tier mid rail end"),
            ("2", "gusset on the left side of the base mid rail, each end"),
            ("8", "hidden connector, every floor corner: no room below, the pan on top"),
            ("2", "hidden connector, top side rails at the back: the X rail sits under them")]
    ax.text(640, 706, "Gussets", fontsize=10.4, fontweight="bold", color=INK)
    ax.text(640, 520, "Hidden connectors", fontsize=10.4, fontweight="bold", color=INK)
    y = 676
    for i, (q, t) in enumerate(rows):
        if i == 4:
            y = 490
        ax.text(640, y, f"{q}×", fontsize=10.4, fontweight="bold", color=ACCENT, va="center")
        ax.text(682, y, t, fontsize=8.8, color=INK, va="center", wrap=True)
        y -= 34
    c = Counter(j.kind for j in J)
    assert c["gusset"] == 44 and c["hidden"] == 10
    note(ax, 640, 400, "Two rules decide every position.\nNo bracket on a top face: every top face is a "
                       "tray seat\nor the slot its nut sits in.\nNothing behind the tray line, y = 203, between "
                       "the posts:\nthat is the gantry's corridor.", fs=9.0, color=INK)
    body(ax, "Rev 5 had an M8 end tap on every member end. Its screw head has to enter the mating slot from that "
             "slot's open end,\nand in this cabinet the shelf rails tie both sides together, so no order of "
             "assembly works. Brackets on drop-in nuts go\non in any order, need no machining, and do not care "
             "what the profile's centre bore is.", fs=9.4)
    save(fig, ax, pdf, "00d_joints")


# ============================================================ 1  the profile
@page
def s1(pdf):
    fig, ax = new_page(1, "Know your profile",
                       "Measure one offcut before you cut anything. Four numbers decide four things.")
    from matplotlib.patches import Polygon as Poly
    s = 9.0
    cx, cy = 300.0, 470.0
    out = C.profile_outline()
    P = [(cx + (x - 20) * s, cy + (y - 20) * s) for x, y in out]
    ax.add_patch(Poly(P, closed=True, facecolor="#dde3e7", edgecolor=INK, lw=1.1, zorder=20))
    ax.add_patch(Circle((cx, cy), C.BORE_DRAW / 2 * s, facecolor="white", edgecolor=INK, lw=1.1, zorder=21))

    def dim_h(x0, x1, y, txt, col=INK, up=True):
        ax.plot([x0, x1], [y, y], color=col, lw=1.0, zorder=30)
        for xx in (x0, x1):
            ax.plot([xx, xx], [y - 6, y + 6], color=col, lw=1.0, zorder=30)
        ax.text((x0 + x1) / 2, y + (10 if up else -10), txt, ha="center", va="bottom" if up else "top",
                fontsize=10, color=col, fontweight="bold", zorder=30)

    def dim_v(y0, y1, x, txt, col=INK):
        ax.plot([x, x], [y0, y1], color=col, lw=1.0, zorder=30)
        for yy in (y0, y1):
            ax.plot([x - 6, x + 6], [yy, yy], color=col, lw=1.0, zorder=30)
        ax.text(x + 10, (y0 + y1) / 2, txt, ha="left", va="center", fontsize=10, color=col,
                fontweight="bold", zorder=30)

    dim_h(cx - 20 * s, cx + 20 * s, cy - 20 * s - 30, "40.0", up=False)
    dim_h(cx - 4.1 * s, cx + 4.1 * s, cy + 20 * s + 22, "A  slot opening  8.0 to 8.2", ACCENT)
    dim_v(cy + 20 * s, cy + (20 - C.SLOT_DEPTH) * s, cx + 20 * s + 24, "B  slot depth\n    about 12", ACCENT)
    ax.plot([cx, cx + 6 * s], [cy, cy - 9 * s], color=ACCENT, lw=1.0, zorder=31)
    ax.text(cx + 6 * s + 6, cy - 9 * s - 4, "C  centre bore", fontsize=10, color=ACCENT,
            fontweight="bold", va="top", zorder=31)
    ax.plot([cx - 20 * s + 6, cx - 20 * s - 30], [cy - 20 * s + 6, cy - 20 * s - 60], color=ACCENT, lw=1.0, zorder=31)
    ax.text(cx - 20 * s - 34, cy - 20 * s - 66, "D  corner radius", fontsize=10, color=ACCENT,
            fontweight="bold", va="top", ha="center", zorder=31)
    rows = [("A  Slot opening", "8.0 to 8.2", "whether the gussets, hidden connectors\nand T-nuts in this book fit. "
             "6 or 10: stop,\nyou have a different series"),
            ("B  Slot depth, face to floor", "about 12", "the sheet screws: shorten them by any\nshortfall "
             "(fasteners page)"),
            ("C  Centre bore", "6.8, 8.4 or 10.5", "which fit-test coupon and which feet\nto print (step 4)"),
            ("D  Corner radius", "about 2.4", "nothing structural: the feet are drawn\nto it. Hold a coupon "
             "against the end")]
    for i, (a, b, c) in enumerate(rows):
        y = 712 - i * 116
        ax.text(640, y, a, fontsize=11, fontweight="bold", color=INK, va="top")
        ax.text(1100, y, b, fontsize=11, color=ACCENT, fontweight="bold", va="top", ha="right")
        ax.text(640, y - 24, "decides " + c, fontsize=9.2, color=DIM, va="top", linespacing=1.4)
    tool(ax, 640, 236, "calipers")
    body(ax, "EU slot 8, one slot per face: the brackets you own are made for it. Drawn nine times size: the "
             "generic slot-8 section, yours may have\nhollow corners, which change nothing here. Measure a clean "
             "sawn end, not the factory end, and write the four numbers on the\noffcut: it is the test piece for "
             "the feet in step 4.")
    save(fig, ax, pdf, "01")


# ============================================================ 2  cut and label
@page
def s2(pdf):
    fig, ax = new_page(2, "Cut and label",
                       "31 pieces from 17 sticks of 2000. Label both ends of every piece.")
    sticks = C.cut_plan()
    pats = {}
    for st in sticks:
        key = tuple(round(m.length, 1) for m in st["cuts"])
        pats.setdefault(key, []).append(st)
    x0, sc = 150.0, 0.40
    y = 700.0
    for key, group in sorted(pats.items(), key=lambda kv: -len(kv[1])):
        n = len(group)
        ax.text(x0 - 20, y, f"{n}×", fontsize=13, fontweight="bold", color=ACCENT, ha="right", va="center")
        xx = x0
        for L in key:
            ax.add_patch(Rectangle((xx, y - 15), L * sc, 30, facecolor="#e4e9ec", edgecolor=INK, lw=0.9))
            ax.text(xx + L * sc / 2, y, f"{L:g}", fontsize=10, ha="center", va="center", color=INK,
                    fontweight="bold")
            xx += L * sc + 3.0 * sc
        drop = 2000.0 - sum(key) - 3.0 * len(key)
        ax.add_patch(Rectangle((xx, y - 15), drop * sc, 30, facecolor="white", edgecolor=EDGE, lw=0.8,
                               hatch="////"))
        ax.text(xx + drop * sc + 10, y, f"drop {drop:.0f}", fontsize=8.6, color=DIM, va="center")
        labs = []
        for st in group:
            labs += [m.label for m in st["cuts"]]
        order = {k: i for i, k in enumerate(["FL", "FR", "BL", "BR"] + [f"{a}{k}" for a in "FBSLRM" for k in range(5)])}
        by_len = {}
        for st in group:
            for m in st["cuts"]:
                by_len.setdefault(round(m.length, 1), []).append(m.label)
        txt = "     ".join(f"{L:g}: " + " ".join(sorted(v, key=lambda t: order.get(t, 99)))
                           for L, v in by_len.items())
        ax.text(x0, y - 30, txt, fontsize=8.6, color=DIM, va="top")
        y -= 92
    # the label key, on the frame
    parts = cab(99, feet=False, lw=0.35)
    MMv = view(214, 20)
    v = scene(ax, parts, (995, 262), (280, 250), MM=MMv, px=1.8, clip=(830, 118, 1125, 398))
    lab = {"FL": (20, 20, 1650), "FR": (C.W - 20, 20, 1650), "BL": (20, C.D - 20, 1650),
           "BR": (C.W - 20, C.D - 20, 1650), "F1": (250, 0, 325), "B1": (1000, C.D, 325),
           "L1": (0, 300, 325), "S1": (420, 183, 345), "M1": (680, 100, 345), "F4": (400, 0, 1810)}
    for t, p in lab.items():
        q = v(p)
        ax.text(q[0], q[1], t, fontsize=8.4, fontweight="bold", color="white", ha="center", va="center",
                zorder=320, bbox=dict(boxstyle="round,pad=0.2", fc=INK, ec="none"))
    note(ax, 560, 330, "F front, B back, L left, R right,\nS shelf (the tray's back edge),\nM mid (under the "
                       "sheet laps),\nposts by corner. The number is\nthe level: 0 the floor, 4 the top.", fs=9.0,
         color=INK)
    tool(ax, 560, 170, "mitre saw  ·  square")
    body(ax, "Bought cut to length? Check every piece against this list instead. Otherwise cut all pieces of one "
             "length in a single setup against\na stop, square to 0.5, and deburr both ends: a raised burr on an "
             "end stops a rail seating square on its post.")
    save(fig, ax, pdf, "02")


# ============================================================ 3  level marks
@page
def s3(pdf):
    fig, ax = new_page(3, "Mark the levels",
                       "On all four posts, from the BOTTOM end, squared all the way round.")
    posts = []
    gap = 170.0
    order = ["FL", "BL", "BR", "FR"]
    for i, lab in enumerate(order):
        posts.append(Part(mv(C.stick(C.H, "z"), i * gap, 0, 0), ALU, lw=0.5, ang=30))
    MMv = iso_matrix(200, 8)
    v = scene(ax, posts, (330, 494), (380, 520), MM=MMv, px=2.0)
    right = {"FR", "BR"}
    for i, lab in enumerate(order):
        p = v((i * gap + 20, 0, -40))
        ax.text(p[0], p[1] - 6, lab, ha="center", va="top", fontsize=11, fontweight="bold",
                family=TITLE_FONT, color=INK)
        for k, z in enumerate(C.LEVELS):
            zz = z + (C.DRAIN_FALL if (lab in right and k < 4) else 0.0)
            if k == 0:
                continue
            a = v((i * gap - 2, 0, zz)); b = v((i * gap + 42, 0, zz))
            c_ = v((i * gap + 42, 40, zz))
            ax.plot([a[0], b[0], c_[0]], [a[1], b[1], c_[1]], color=ACCENT, lw=1.8, zorder=200)
    rows = [("level 4", "1789.0", "1789.0", "top: dead level, the X rail hangs here"),
            ("level 3", "1397.0", "1402.0", "tier C"),
            ("level 2", "965.2", "970.2", "tier B"),
            ("level 1", "304.8", "309.8", "tier A"),
            ("level 0", "0", "5.0", "the floor: packers, step 7")]
    ax.text(700, 712, "rail bottom, from the post's bottom end", fontsize=9.0, color=DIM)
    ax.text(860, 688, "FL, BL", fontsize=9.6, fontweight="bold", color=INK, ha="right")
    ax.text(960, 688, "FR, BR", fontsize=9.6, fontweight="bold", color=INK, ha="right")
    for i, (a, l, r, t) in enumerate(rows):
        y = 650 - i * 62
        ax.text(700, y, a, fontsize=10.4, fontweight="bold", color=INK, va="center")
        ax.text(860, y, l, fontsize=10.4, color=INK, va="center", ha="right")
        ax.text(960, y, r, fontsize=10.4, color=ACCENT if l != r else INK, va="center", ha="right",
                fontweight="bold")
        ax.text(700, y - 22, t, fontsize=8.6, color=DIM, va="center")
    tool(ax, 700, 300, "tape  ·  square  ·  fine marker")
    body(ax, "The mark is the BOTTOM face of the rail, which is the top of the gusset that carries it. The two "
             "right-hand posts are marked 5 higher\non levels 0 to 3: every tray falls 5 mm to its drain at the left end "
             f"(BOM G090), the pan to its leak sensor. Level 4 does not fall. Use one\ntape for all four posts and "
             "hook it on the same end each time: a 1 mm slip between posts is a twisted tier.")
    save(fig, ax, pdf, "03")


# ============================================================ 4  feet
@page
def s4(pdf):
    fig, ax = new_page(4, "Print the feet",
                       "Fit-test coupons first, then four feet. SUNLU TPU 95A, pin up, no supports.")
    foot = Part(C.foot_mesh(), HILITE, lw=0.5, ang=35)
    stubm = mv(C.stick(70, "z"), -20, -20, 20 + C.TF.PIN_LEN + 18)
    stub_p = Part(stubm, ALU, lw=0.5, ang=30)
    MMv = iso_matrix(30, 22)
    v = scene(ax, [foot, stub_p], (330, 470), (380, 560), MM=MMv, px=3.0)
    axis3(ax, v, (0, 0, -8), (0, 0, 20 + C.TF.PIN_LEN + 100))
    # the coupons, one per bore
    C.TF.use("4040")
    for i, bore in enumerate(C.TF.BORES):
        C.TF.set_bore(bore)
        vv, ff = C.TF.build_foot(C.TF.FIT_TEST_HEIGHT, "TPU")
        tris = [(f[0], f[k], f[k + 1]) for f in ff for k in range(1, len(f) - 1)]
        cp = Part((np.array(vv), np.array(tris)), HILITE, lw=0.5, ang=35)
        cx = 700 + i * 140
        scene(ax, [cp], (cx, 640), (110, 110), MM=MMv, clip=(cx - 66, 570, cx + 66, 720))
        ax.text(cx, 566, f"bore {bore:g}", ha="center", fontsize=9.4, fontweight="bold", color=INK)
    C.TF.use("4040")
    tag(ax, 640, 512, "Fit-test coupon, one per bore", 3, hi=True)
    tag(ax, 640, 466, "Foot 40 × 40 × 20, 20 mm barbed pin", 4, hi=True)
    rows = [("Material", "SUNLU TPU 95A Clear"), ("Infill", "100 %, so a foot cannot creep"),
            ("Speed", "20 to 25 mm/s, retraction short"), ("Orientation", "flat face down, pin up"),
            ("Each foot", "about 40 g, so 160 g for four")]
    for i, (a, b) in enumerate(rows):
        y = 404 - i * 26
        ax.text(640, y, a, fontsize=9.4, fontweight="bold", color=INK, va="center")
        ax.text(760, y, b, fontsize=9.4, color=INK, va="center")
    tool(ax, 640, 250, "calipers")
    body(ax, "Push each coupon into the bore of the offcut from step 1. Keep the one that needs a firm push "
             "and will not pull out by hand; print\nthe four feet in that bore (tpu_foot.py --profile 4040 --bore "
             "D). Loose: raise BARB_INTERF to 0.6 or 0.7. Too tight to start: lower it.\nThe feet do not adjust: "
             "check the floor where the cabinet will stand with the level now, and plan a shim, not a softer foot.")
    save(fig, ax, pdf, "04")



# ============================================================ helpers for the build pages
JD = {j.label: j for j in C.joints()}
MD = C.by_label()
VIEW = (212, 22)              # front-left, above: the default build view


def fasteners_parts(labels, explode=26.0, nut_explode=18.0, bracket_explode=0.0, hi=True, legs=(0, 1)):
    """legs: 0 = the screw into the rail (face A), 1 = the screw into the post or second member."""
    out = []
    for lab in labels:
        f = C.gusset_fasteners(JD[lab], explode, nut_explode, bracket_explode)
        f = [f[3 * k + i] for k in legs for i in range(3)]
        for kind, m in f:
            col = (HILITE if hi else STEEL) if kind != "tnut" else (HILITE if hi else NUTC)
            out.append(Part(m, col, lw=0.4, ang=30))
    return out


def hidden_grubs(labels, hi=True):
    return []


def gusset_axes(ax, v, labels, out=70.0, into=22.0):
    for lab in labels:
        j = JD[lab]
        for p, d in j.bolt_points():
            d = np.asarray(d, float)
            axis3(ax, v, p - d * out, p + d * into)


def member_mid(lab, dz=0.0):
    m = MD[lab]
    lo, hi = m.bbox()
    return (lo + hi) / 2 + np.array([0, 0, dz])


# ============================================================ 5  the base
@page
def s5(pdf):
    fig, ax = new_page(5, "The base  ·  front, back and the mid rail",
                       "On a flat floor. The mid rail sits under the base pan's lap.")
    j2 = ["M0-F0", "M0-B0"]
    parts = cab(5, hi_m=("M0",), hi_j=j2, explode_j={k: 26.0 for k in j2})
    parts += fasteners_parts(j2, explode=44.0, nut_explode=24.0, bracket_explode=18.4)
    MMv = view(212, 34)
    v = scene(ax, parts, (440, 470), (640, 520), MM=MMv, px=2.0,
              focus=fbox([300, 0, 0], [1100, C.D, 40]))
    p0 = v((C.SER, 0, 0)); p1 = v((C.MID[0], 0, 0))
    ax.annotate("", xy=(p1[0], p1[1] - 26), xytext=(p0[0], p0[1] - 26),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=1.0))
    ax.text((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 - 44, "620 from F0's end to M0's left face",
            fontsize=9.4, ha="center", color=INK, rotation=math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])))
    MMi = iso_matrix(236, 30)
    j = JD["M0-F0"]
    det = cab(5, hi_m=("M0",), hi_j=("M0-F0",), explode_j={"M0-F0": 30.0},
              lo=(560, 0, -5), hi=(760, 160, 60))
    det += fasteners_parts(["M0-F0"], explode=46.0, nut_explode=26.0, bracket_explode=21.2)
    vi = inset(ax, 760, 176, 350, 250, det, MMi, focus=fbox([590, 0, 0], [720, 120, 40]),
               label="M0 meets F0: the gusset on M0's left")
    tag(ax, 790, 704, "F0, B0  ·  1317", 2)
    tag(ax, 790, 660, "M0  ·  479", 1, hi=True)
    tag(ax, 790, 616, "Gusset 3540", 2, hi=True)
    tag(ax, 790, 572, "M8 × 16 cap screw + washer", 4, hi=True)
    tag(ax, 790, 528, "M8 drop-in T-nut", 4, hi=True)
    tool(ax, 790, 474, "6 mm hex  ·  tape")
    body(ax, "Lay F0 and B0 parallel, top slots up, 479 apart inside. M0 goes between them with its LEFT face 620 "
             "from F0's left end: its centre line,\n680 from the frame's left edge, is where the pan's lap bolt lands. "
             "Drop each T-nut into its slot, turn it a quarter, and snug the screws:\nfinal tightening comes at "
             "step 10, once the box is square.")
    save(fig, ax, pdf, "05")


# ============================================================ 6  floor connectors
@page
def s6(pdf):
    fig, ax = new_page(6, "Hidden connectors in the eight floor ends",
                       "One leg into each rail's TOP slot from its end, the other leg standing up.")
    hid = level_joints(0, "hidden")
    parts = cab(6, hi_m=("L0", "R0"), hi_j=hid, explode_j={k: (-34.0, 46.0) for k in hid})
    MMv = view(*VIEW)
    v = scene(ax, parts, (430, 480), (640, 500), MM=MMv, px=2.0)
    for lab in hid:
        j = JD[lab]
        axis3(ax, v, j.local_point(-34.0 - 12.0, -6.0), j.local_point(30.0, -6.0))
    MMi = iso_matrix(224, 34)
    lab = "F0-FL"
    det = cab(6, hi_j=hid, explode_j={k: (-30.0, 40.0) for k in hid}, lo=(-10, -10, -10), hi=(150, 150, 120))
    vi = inset(ax, 760, 190, 350, 290, det, MMi, focus=fbox([0, 0, 0], [130, 130, 100]),
               label="the FL corner: two connectors, two rails")
    for lab_ in ("F0-FL", "L0-FL"):
        j = JD[lab_]
        axis3(ax, vi, j.local_point(-60.0, -6.0), j.local_point(20.0, -6.0))
    tag(ax, 790, 700, "L0, R0  ·  479", 2, hi=True)
    tag(ax, 790, 652, "Hidden connector, TOCLUX", 8, hi=True)
    tag(ax, 790, 604, "M6 grub, finger tight", 16, hi=True)
    tool(ax, 790, 540, "3 mm hex")
    body(ax, "Slide each connector into the rail's top slot from the end until its upright leg stands 11 clear of "
             "the end face: that much of it sits inside\nthe post's slot. Lay L0 and R0 in line with the ends of F0 "
             "and B0, leaving a 40 × 40 square empty at each corner for a post.\nGrubs finger tight only: they lock "
             "at step 7. The connectors live inside the slots, so the base pan will lie flat over them.")
    save(fig, ax, pdf, "06")


# ============================================================ 7  the posts
@page
def s7(pdf):
    fig, ax = new_page(7, "Stand the posts",
                       "Lower each post straight down onto its two connector legs. A helper holds it plumb.")
    up = 260.0
    parts = cab(7, hi_m=POSTS, explode_m={"FR": (0, 0, up)})
    MMv = view(*VIEW)
    v = scene(ax, parts, (420, 450), (600, 560), MM=MMv, px=1.9,
              focus=fbox([0, 0, 0], [C.W, C.D, 900]))
    a, b = v((C.W - 20, 20, up + 420)), v((C.W - 20, 20, 300))
    arrow2(ax, (a[0] + 34, a[1]), (b[0] + 34, b[1]))
    MMi = iso_matrix(214, 26)
    det = cab(7, explode_m={"FL": (0, 0, 70)}, lo=(-10, -10, -10), hi=(130, 130, 170), hi_m=("FL",))
    vi = inset(ax, 760, 236, 350, 290, det, MMi, focus=fbox([0, 0, 0], [110, 110, 230]),
               label="the legs enter the post's two inner slots")
    tag(ax, 790, 700, "Post 1829, FL FR BL BR", 4, hi=True)
    tag(ax, 790, 652, "5 mm packer, base, right end", 3)
    tool(ax, 790, 590, "3 mm hex  ·  level")
    body(ax, "Before the right-hand posts go on, prop R0 and the right ends of F0 and B0 on 5 mm packers: that is "
             "the base's fall to the left\n(step 3). Lower the post until it stands on the floor, plumb it both "
             "ways and lock both connectors' grubs, two each. Until step 9\nthe posts are only held at the foot: "
             "clamp a batten across the tops, or keep the helper.")
    save(fig, ax, pdf, "07")


# ============================================================ 8  top ledges
@page
def s8(pdf):
    fig, ax = new_page(8, "Ledges for the top",
                       "Six gussets on the level 4 marks. Two hidden connectors into the top side rails.")
    g4 = level_joints(4, "gusset")
    h4 = level_joints(4, "hidden")
    parts = cab(8, hi_j=g4, drop_j=h4)
    MMv = view(*VIEW)
    v = scene(ax, parts, (360, 470), (480, 560), MM=MMv, px=1.9)
    # inset 1: a top ledge pair at FL, exploded
    MMi = iso_matrix(222, 16)
    jl = ["F4-FL", "L4-FL"]
    det = cab(8, hi_j=jl, explode_j={k: 22.0 for k in jl}, lo=(-10, -10, 1650), hi=(140, 140, 1835), drop_j=h4)
    det += fasteners_parts(jl, explode=34.0, nut_explode=20.0, bracket_explode=15.6, legs=(1,))
    vi = inset(ax, 680, 384, 430, 226, det, MMi, focus=fbox([0, 0, 1700], [120, 120, 1800]),
               label="FL, level 4: one ledge per rail, gusset top on the mark")
    # inset 2: the hidden connector on L4's back end
    MMi2 = iso_matrix(150, 18)
    l4 = Part(MD["L4"].mesh(np.array([-5, 380, 1700]), np.array([60, 600, 1900])), HILITE, lw=0.5, ang=30)
    hc = Part(JD["L4-BL"].bracket((0.0, 0.0)), HILITE, lw=0.5, ang=30)
    l4m = Part(mv(l4.mesh, 0, -40, 60), HILITE, lw=0.5, ang=30)
    hcm = Part(mv(hc.mesh, 0, -40, 60), HILITE, lw=0.5, ang=30)
    post = Part(MD["BL"].mesh(np.array([-5, 500, 1600]), np.array([60, 600, 1900])), ALU, lw=0.5, ang=30)
    xr = Part(C.GF.x_rail(), ALU, ghost=True, lw=0.35, ang=30)
    vi2 = inset(ax, 680, 150, 430, 220, [post, xr, l4m, hcm], MMi2,
                focus=fbox([0, 420, 1690], [40, 559, 1890]),
                label="L4's back end: the X rail (pale) runs below it")
    tag(ax, 680, 700, "Gusset 3540", 6, hi=True)
    tag(ax, 880, 700, "Hidden connector", 2, hi=True)
    tool(ax, 680, 648, "6 mm hex  ·  3 mm hex")
    body(ax, "Gusset TOP edge on the mark, its leg down the post; snug, then check with the square that the "
             "upper leg is level. At the two back\ncorners the side rails get no gusset: the X rail's ends run in "
             "front of BL and BR right under them. Slide a hidden connector into\nthe BOTTOM slot of L4 and of R4 "
             "at the back end, leg pointing down, grubs loose.")
    save(fig, ax, pdf, "08")


# ============================================================ 9  top ring
@page
def s9(pdf):
    fig, ax = new_page(9, "The top ring",
                       "Lift each rail onto its ledges. The back of L4 and R4 slides down into BL and BR.")
    top = level_members(4)
    lift = 300.0
    parts = cab(9, hi_m=top, explode_m={k: (0, 0, lift) for k in top},
                hi_j=level_joints(4, "hidden"), explode_j={k: (0.0, -lift) for k in level_joints(4, "hidden")})
    MMv = view(*VIEW)
    v = scene(ax, parts, (430, 470), (560, 560), MM=MMv, px=1.9)
    for lab in top:
        c = member_mid(lab, lift - 18)
        c2 = member_mid(lab, 34)
        a, b = v(c), v(c2)
        arrow2(ax, tuple(a), tuple(b), ms=12, lw=1.8)
    tag(ax, 800, 700, "F4, B4  ·  1317", 2, hi=True)
    tag(ax, 800, 652, "L4, R4  ·  479", 2, hi=True)
    tag(ax, 800, 604, "M8 × 16 cap screw + washer + T-nut", 6, hi=True)
    tool(ax, 800, 540, "6 mm hex  ·  2 clamps")
    note(ax, 800, 480, "One screw per gusset goes in now, the\nupper leg into the rail's bottom slot.\nThe "
                       "lower leg went on at step 8.", fs=9.2, color=INK)
    body(ax, "F4 and B4 first: clamp each to its ledges and drop a T-nut under each gusset's upper leg. Then L4 and "
             "R4: front end on its gusset, back\nend lowered so the connector's leg slides down the post's front "
             "slot. Lock those grubs. Now the box stands on its own: the batten\ncan come off.")
    save(fig, ax, pdf, "09")


# ============================================================ 10 square
@page
def s10(pdf):
    fig, ax = new_page(10, "Square it, then tighten",
                       "Diagonals equal, posts plumb. Only then the final turn on every screw so far.")
    W_, D_, H_ = C.W, C.D, C.H
    parts = cab(9)
    MMv = view(212, 20)
    v = scene(ax, parts, (400, 470), (560, 560), MM=MMv, px=1.9)
    diags = [((0, 0, 0), (W_, 0, H_), f"{math.hypot(W_, H_):.1f}", "front face"),
             ((W_, 0, 0), (0, 0, H_), None, None),
             ((0, 0, H_), (W_, D_, H_), f"{math.hypot(W_, D_):.1f}", "top ring"),
             ((W_, 0, H_), (0, D_, H_), None, None),
             ((0, 0, 0), (0, D_, H_), f"{math.hypot(D_, H_):.1f}", "left face"),
             ((0, D_, 0), (0, 0, H_), None, None)]
    for a3, b3, val, nm in diags:
        a, b = v(a3), v(b3)
        ax.plot([a[0], b[0]], [a[1], b[1]], color=ACCENT, lw=1.4, ls=(0, (6, 3)), zorder=210)
    for a3, b3, val, nm in diags:
        if val:
            m = (np.asarray(a3, float) + np.asarray(b3, float)) / 2
            q = v(m)
            ax.text(q[0], q[1], f"{nm}  {val}", fontsize=9.6, fontweight="bold", color=ACCENT, ha="center",
                    va="center", zorder=320, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none"))
    rows = [("Diagonals", "within 2 of each other, every face"),
            ("Posts", "plumb both ways, on two faces each"),
            ("Top ring", "dead level both ways: the gantry\nhangs from it"),
            ("Then", "tighten every gusset screw so far")]
    for i, (a, b) in enumerate(rows):
        y = 696 - i * 84
        ax.text(800, y, a, fontsize=11, fontweight="bold", color=INK)
        ax.text(800, y - 10, b, fontsize=9.2, color=DIM, va="top", linespacing=1.4)
    tool(ax, 800, 340, "tape  ·  level  ·  6 mm hex")
    body(ax, "Measure corner to corner on the outside of the posts, the tape hooked the same way both times. The "
             "base ring's diagonals are the same\nas the top's. Long diagonal long: push that corner in, gently, "
             "with the screws still snug. A cabinet that starts out of square stays out\nof square, and the trays "
             "will not drop in at step 19. The right-hand base packers stay in until the feet go on at step 15.")
    save(fig, ax, pdf, "10")


# ============================================================ 11 to 13: tier A
TIER_LOCK = {1: "A", 2: "B", 3: "C"}


@page
def s11(pdf):
    fig, ax = new_page(11, "Tier A  ·  eight ledges",
                       "On the level 1 marks: 304.8 on the left posts, 309.8 on the right.")
    g = level_joints(1, posts=True)
    parts = cab(11, hi_j=g)
    MMv = view(*VIEW)
    v = scene(ax, parts, (360, 470), (480, 560), MM=MMv, px=1.9)
    MMi = iso_matrix(232, 14)
    jl = ["F1-FL", "L1-FL"]
    det = cab(11, hi_j=jl, explode_j={k: 22.0 for k in jl}, lo=(-10, -10, 180), hi=(140, 140, 360))
    det += fasteners_parts(jl, explode=34.0, nut_explode=20.0, bracket_explode=15.6, legs=(1,))
    vi = inset(ax, 680, 300, 430, 330, det, MMi, focus=fbox([0, 0, 230], [120, 120, 330]),
               label="FL: a ledge for F1, a ledge for L1")
    locator(ax, 1060, 210, mark=(260, 360))
    tag(ax, 680, 700, "Gusset 3540", 8, hi=True)
    tag(ax, 680, 652, "M8 × 16 + washer + T-nut, lower legs", 8, hi=True)
    tool(ax, 680, 240, "6 mm hex  ·  square")
    body(ax, "Same as step 8: TOP edge of each gusset on the mark, lower leg down the post, one screw. Two ledges "
             "at every post, on the two inner\nfaces. The 5 mm between the left and right marks is the tray's fall to "
             "its drain: do not level it out.")
    save(fig, ax, pdf, "11")


@page
def s12(pdf):
    fig, ax = new_page(12, "Tier A  ·  front, back and side rails",
                       "Onto the ledges, clamp, one screw up through each gusset into the rail.")
    rails = ["F1", "B1", "L1", "R1"]
    lift = 300.0
    parts = cab(12, hi_m=rails, explode_m={k: (0, 0, lift) for k in rails})
    MMv = view(*VIEW)
    v = scene(ax, parts, (430, 470), (560, 560), MM=MMv, px=1.9)
    for lab in rails:
        a, b = v(member_mid(lab, lift - 18)), v(member_mid(lab, 34))
        arrow2(ax, tuple(a), tuple(b), ms=12, lw=1.8)
    locator(ax, 1060, 210, mark=(260, 360))
    tag(ax, 800, 700, "F1, B1  ·  1317", 2, hi=True)
    tag(ax, 800, 652, "L1, R1  ·  479", 2, hi=True)
    tag(ax, 800, 604, "M8 × 16 + washer + T-nut, upper legs", 8, hi=True)
    tool(ax, 800, 540, "6 mm hex  ·  2 clamps")
    body(ax, "Each rail sits on two ledges and butts the posts at both ends. Push it hard against the post while "
             "you snug the screw, so the end\nface seats square. Gaps at the ends mean the posts have spread: "
             "loosen the ledges, close the gap, re-check the diagonals.")
    save(fig, ax, pdf, "12")


@page
def s13(pdf):
    fig, ax = new_page(13, "Tier A  ·  the tray rails",
                       "S1 carries the tray's back edge, M1 its lap. Four gussets, all on the tray side.")
    tj = level_joints(1, posts=False)
    parts = cab(13, hi_m=("S1", "M1"), hi_j=tj, explode_j={k: 20.0 for k in tj})
    MMv = view(*VIEW)
    v = scene(ax, parts, (360, 480), (600, 520), MM=MMv, px=1.9,
              focus=fbox([0, 0, 200], [C.W, C.D, 460]), clip=(24, 150, 660, 772))
    MMi = iso_matrix(236, 30)
    jl = ["S1-L1"]
    det = cab(13, hi_m=("S1",), hi_j=jl, explode_j={"S1-L1": 24.0}, lo=(-10, 60, 250), hi=(200, 300, 400))
    det += fasteners_parts(jl, explode=36.0, nut_explode=22.0, bracket_explode=17.0)
    inset(ax, 690, 396, 420, 200, det, MMi, focus=fbox([0, 100, 300], [140, 240, 350]),
          label="S1 meets L1: the gusset on S1's front")
    # plan of the tier, scaled
    s = 0.27
    x0, y0 = 714.0, 196.0
    ax.add_patch(Rectangle((x0, y0), C.W * s, C.D * s, facecolor="white", edgecolor=INK, lw=0.8, zorder=10))
    def r(x, y, w, h, fc, ec=INK):
        ax.add_patch(Rectangle((x0 + x * s, y0 + y * s), w * s, h * s, facecolor=fc,
                               edgecolor=ec, lw=0.6, zorder=11))
    for m in ("F1", "B1", "L1", "R1"):
        mm = MD[m]; lo_, hi_ = mm.bbox(); r(lo_[0], lo_[1], hi_[0] - lo_[0], hi_[1] - lo_[1], "#dde3e7")
    for m in ("S1", "M1"):
        mm = MD[m]; lo_, hi_ = mm.bbox(); r(lo_[0], lo_[1], hi_[0] - lo_[0], hi_[1] - lo_[1], "#fbd3a7", HILITE * 0 + 0.3)
    for p in POSTS:
        mm = MD[p]; lo_, hi_ = mm.bbox(); r(lo_[0], lo_[1], 40, 40, "#9aa6ae")
    r(40, C.TRAY_D, C.W - 80, C.D - 40 - C.TRAY_D, "none", ACCENT)
    ax.text(x0 + C.W * s / 2, y0 + (C.TRAY_D + (C.D - 40 - C.TRAY_D) / 2) * s, "gantry corridor\nnothing here",
            ha="center", va="center", fontsize=9.0, color=ACCENT, zorder=12)
    ax.text(x0 + C.W * s / 2, y0 - 16, "plan, front at the bottom: S1 at y 163 to 203, M1 at x 660 to 700",
            ha="center", fontsize=8.4, color=DIM)
    tag(ax, 690, 712, "S1  ·  1317", 1, hi=True)
    tag(ax, 850, 712, "M1  ·  123", 1, hi=True)
    tag(ax, 690, 666, "Gusset 3540", 4, hi=True)
    tag(ax, 850, 666, "M8 × 16 + washer + T-nut", 8, hi=True)
    tool(ax, 690, 622, "6 mm hex  ·  tape")
    body(ax, "S1's back face lands on the tray line, 203 from the front: measure it at both ends. These four "
             "gussets stand on edge in the inside\ncorners, on the FRONT side of S1 and the LEFT side of M1. One on "
             "the back of S1 would sit in the gantry's corridor, which must stay\nempty from 203 back to the posts. "
             "Bolt S1 to L1 and R1 first, then fit M1 between F1 and S1, its left face 620 from F1's end.")
    save(fig, ax, pdf, "13")


@page
def s14(pdf):
    fig, ax = new_page(14, "Tiers B and C  ·  the same three steps",
                       "Repeat 11 to 13 on the level 2 and level 3 marks.")
    hm = [f"{a}{k}" for k in (2, 3) for a in "FBLRSM"]
    hj = level_joints(2) + level_joints(3)
    parts = cab(14, hi_m=hm, hi_j=hj)
    MMv = view(*VIEW)
    v = scene(ax, parts, (430, 470), (560, 560), MM=MMv, px=1.9)
    rows = [("Tier B, level 2", "965.2 left posts, 970.2 right"), ("Tier C, level 3", "1397.0 left posts, 1402.0 right")]
    for i, (a, b) in enumerate(rows):
        y = 690 - i * 60
        ax.text(800, y, a, fontsize=11, fontweight="bold", color=INK)
        ax.text(800, y - 22, b, fontsize=9.4, color=DIM)
    tag(ax, 800, 540, "F, B, S  ·  1317", 6, hi=True)
    tag(ax, 800, 492, "L, R  ·  479", 4, hi=True)
    tag(ax, 800, 444, "M  ·  123", 2, hi=True)
    tag(ax, 800, 396, "Gusset 3540", 24, hi=True)
    tag(ax, 800, 348, "M8 × 16 + washer + T-nut", 48, hi=True)
    locator(ax, 1060, 210, mark=(925, 1440))
    body(ax, "Work bottom up so you are never reaching through a finished tier. When tier C is in, re-check the "
             "diagonals, then tighten every gusset\nscrew in the cabinet. 44 gussets, 88 screws: tick them off on "
             "the cut list as you go.")
    save(fig, ax, pdf, "14")



# ============================================================ 15 the feet
@page
def s15(pdf):
    fig, ax = new_page(15, "The feet",
                       "One corner at a time: lift 25, push the foot's pin up into the post, lower.")
    drop = 90.0
    parts = cab(14, feet=False)
    feet = Part(C.feet_world(explode=drop), HILITE, lw=0.45, ang=35)
    MMv = view(212, 16)
    v = scene(ax, parts + [feet], (380, 470), (620, 560), MM=MMv, px=1.9,
              focus=fbox([0, 0, -140], [C.W, C.D, 420]), clip=(24, 150, 700, 772))
    for m in C.members():
        if m.kind == "upright":
            cx, cy = m.x + 20, m.y + 20
            axis3(ax, v, (cx, cy, -C.FOOT_H - drop - 20), (cx, cy, 30))
    # inset: the FL corner, lifted, the foot below on its axis
    MMi = iso_matrix(222, 14)
    det = cab(14, feet=False, lo=(-10, -10, -10), hi=(130, 130, 130))
    ft = Part(mv(C.foot_mesh(), 20, 20, -C.FOOT_H - 40), HILITE, lw=0.5, ang=35)
    det = [Part(mv(p_.mesh, 0, 0, 25), p_.color, lw=p_.lw, ang=30) for p_ in det] + [ft]
    vi = inset(ax, 720, 220, 390, 320, det, MMi, focus=fbox([0, 0, -70], [110, 110, 110]),
               label="FL lifted 25: the pin goes up into the bore")
    axis3(ax, vi, (20, 20, -C.FOOT_H - 60), (20, 20, 60))
    tag(ax, 720, 700, "Foot, printed in step 4", 4, hi=True)
    tool(ax, 720, 640, "bar and a block")
    note(ax, 720, 596, "Pull the 5 mm base packers out as\neach right-hand corner comes up.", fs=9.2, color=INK)
    body(ax, "Lift no more than 25: the corner only has to clear the pin. Line the foot up square with the post, "
             "push until its top face meets the\npost's end all round, then lower it onto the foot. Do the "
             "diagonal corner next, then the other two. The whole cabinet now stands 20\nhigher: everything above "
             "is measured from the bottom of the posts, so none of the marks move.")
    save(fig, ax, pdf, "15")


# ============================================================ 16 sheets: check, drill, seal
def silicone_corners(name):
    """Inside corners where two lips meet (where the bead goes), in the sheet's frame."""
    poly, flags = C.SHEETS[name]
    P = np.array(poly, float)
    n = len(P)
    pts = []
    for i in range(n):
        if flags[i] and flags[(i - 1) % n]:
            pts.append(P[i])
    return pts


@page
def s16(pdf):
    fig, ax = new_page(16, "The sheets  ·  check, drill, seal",
                       "Eight pieces from SendCutSend. Drain holes opened, every corner sealed, before any goes in.")
    up_y = 300.0
    dn = Part(C.sheet_local("tray_DOWN"), SHEET, lw=0.5, ang=30)
    upm = mv(C.sheet_local("tray_UP"), C.MID[0], up_y, 0)
    up = Part(upm, SHEET, lw=0.5, ang=30)
    MMv = view(206, 34)
    v = scene(ax, [dn, up], (420, 510), (640, 440), MM=MMv, px=2.0)
    for name, dx, dy in (("tray_DOWN", 0.0, 0.0), ("tray_UP", C.MID[0], up_y)):
        for p in silicone_corners(name):
            q = v((p[0] + dx, p[1] + dy, 14.0))
            ax.add_patch(Circle(tuple(q), 6.5, facecolor=ACCENT, edgecolor="white", lw=1.0, zorder=210))
    d = C.DRAIN["tray_DOWN"]
    q = v((d[0], d[1], 1.6))
    ax.add_patch(Circle(tuple(q), 10, facecolor="none", edgecolor=ACCENT, lw=2.0, zorder=210))
    ax.plot([q[0], q[0] + 40], [q[1], q[1] - 80], color=DIM, lw=0.8, zorder=205)
    ax.text(q[0] + 44, q[1] - 84, "drain pilot Ø 6, tray DOWN pieces only", fontsize=9.0, color=INK, ha="left", va="top")
    ax.text(v((350, 0, 0))[0], v((350, 0, 0))[1] - 26, "tray DOWN", fontsize=10, fontweight="bold", color=INK,
            ha="center")
    ax.text(v((1050, up_y, 0))[0] + 30, v((1050, up_y, 0))[1] - 20, "tray UP", fontsize=10, fontweight="bold",
            color=INK, ha="center")
    rows = [("tray DOWN", "3", "700 × 203, notch at the left"), ("tray UP", "3", "737 × 203, tongue at the left"),
            ("base pan DOWN", "1", "700 × 559, two notches"), ("base pan UP", "1", "737 × 559, two notches")]
    ax.text(800, 712, "Check off the order", fontsize=10.4, fontweight="bold", color=INK)
    for i, (a, q_, b) in enumerate(rows):
        y = 682 - i * 30
        ax.text(800, y, f"{q_}×", fontsize=10, fontweight="bold", color=ACCENT, va="center")
        ax.text(830, y, a, fontsize=9.6, fontweight="bold", color=INK, va="center")
        ax.text(940, y, b, fontsize=8.8, color=DIM, va="center")
    ax.add_patch(Circle((808, 532), 6.5, facecolor=ACCENT, edgecolor="white", lw=1.0))
    ax.text(824, 532, "a bead of silicone, inside", fontsize=9.2, color=INK, va="center")
    tool(ax, 800, 480, "step drill  ·  caulking gun")
    tag(ax, 800, 424, "Neutral-cure silicone", 1)
    body(ax, "Every bend 90° and every lip 25 tall: a soft bend lifts the floor off its rails. Step-drill the Ø 6 "
             "pilot in each of the three tray DOWN pieces\nto the bulkhead's own hole size (on its packet, usually "
             "about 22) and deburr both faces. Then a bead of neutral-cure silicone into every\ninside corner "
             "where two lips meet, tooled smooth: the mitres there are cut 2.5 open. Let it skin over before "
             "the sheets go in.")
    save(fig, ax, pdf, "16")


# ============================================================ 17 base pan DOWN
def nut_parts(z, which, explode=0.0, hi=True):
    out = []
    for kind, m in C.sheet_fasteners(z, which=which, explode=explode, bolts=False):
        if kind == "tnut":
            out.append(Part(mv(m, 0, 0, -explode * 0.0), HILITE if hi else NUTC, lw=0.35, ang=30))
    return out


def bolt_parts(z, which, explode=0.0, hi=True, shims=True, lap=True):
    out = []
    for kind, m in C.sheet_fasteners(z, which=which, explode=explode, nuts=False):
        if kind == "shim" and not shims:
            continue
        col = HILITE if hi else STEEL
        out.append(Part(m, col, lw=0.35, ang=30))
    return out


@page
def s17(pdf):
    fig, ax = new_page(17, "Base pan  ·  T-nuts, then the DOWN piece",
                       "Eight drop-in nuts under the DOWN piece's holes, the piece on top, seven screws.")
    lift = 120.0
    parts = cab(16, lo=(-10, -10, -30), hi=(C.W + 10, C.D + 10, 260))
    parts += nut_parts(0.0, ("DOWN",))
    pan = Part(mv(C.sheet_world("basepan_DOWN", 0.0), 0, 0, lift), HILITE, lw=0.45, ang=30)
    bolts = bolt_parts(0.0, ("DOWN",), explode=lift + 40, shims=False)
    MMv = view(206, 34)
    v = scene(ax, parts + [pan] + bolts, (400, 470), (620, 520), MM=MMv, px=2.0,
              focus=fbox([0, 0, 0], [800, C.D, 200]), clip=(24, 150, 770, 772))
    for x, y, zz, al in C.sheet_holes_world("basepan_DOWN", 0.0):
        axis3(ax, v, (x, y, C.SER - 6), (x, y, C.SER + lift + 50))
    tag(ax, 790, 700, "Base pan, DOWN piece", 1, hi=True)
    tag(ax, 790, 652, "M8 drop-in T-nut", 8, hi=True)
    tag(ax, 790, 604, "M8 × 12 button head + washer", 7, hi=True)
    tool(ax, 790, 540, "5 mm hex")
    note(ax, 790, 500, "The eighth hole, on M0 at x 680, is\nthe lap: its nut goes in now, its screw\nat step 18, "
                       "through both pieces.", fs=9.2, color=INK)
    body(ax, "Drop a nut into the top slot under each hole, a quarter turn to lock it, then slide it along until "
             "it sits under the hole. Lay the DOWN\npiece on with its notches round FL and BL, its lap end on M0. "
             "Start all seven screws before tightening any, then snug them\nfrom the middle outward. The "
             "slotted holes take up 4 mm either way: centre the piece in them, do not force it.")
    save(fig, ax, pdf, "17")


# ============================================================ 18 base pan UP
@page
def s18(pdf):
    fig, ax = new_page(18, "Base pan  ·  the UP piece over the lap",
                       "A shim on every one of its seven slots, a bead along the lap, then the piece, eight screws.")
    lift = 110.0
    parts = cab(17, lo=(-10, -10, -30), hi=(C.W + 10, C.D + 10, 260), extra_m=())
    parts.append(Part(C.sheet_world("basepan_DOWN", 0.0), SHEET, lw=0.4, ang=30))
    parts += nut_parts(0.0, ("DOWN", "UP"), hi=False)
    shims = [p for p in bolt_parts(0.0, ("UP",), explode=0.0) if True]
    sh = []
    for kind, m in C.sheet_fasteners(0.0, which=("UP",), explode=0.0, nuts=False):
        if kind == "shim":
            sh.append(Part(m, HILITE, lw=0.35, ang=30))
    up = Part(mv(C.sheet_world("basepan_UP", 0.0), 0, 0, lift), HILITE, lw=0.45, ang=30)
    bolts = [Part(m, HILITE, lw=0.35, ang=30) for kind, m in
             C.sheet_fasteners(0.0, which=("UP",), explode=lift + 40, nuts=False) if kind != "shim"]
    MMv = view(206, 34)
    v = scene(ax, parts + sh + [up] + bolts, (420, 470), (620, 520), MM=MMv, px=2.0,
              focus=fbox([560, 0, 0], [C.W, C.D, 200]), clip=(24, 150, 770, 772))
    for x, y, zz, al in C.sheet_holes_world("basepan_UP", 0.0):
        axis3(ax, v, (x, y, C.SER - 6), (x, y, C.SER + lift + 50))
    # the lap, in section
    panel(ax, 790, 190, 320, 230, z=5)
    slot_section(ax, 950, 300, 4.0, "lap", "")
    ax.text(802, 400, "the lap at x 680, in section", fontsize=8.6, color=DIM, zorder=320)
    ax.text(950, 216, "UP on DOWN on M0  ·  M8 × 16", fontsize=8.6, color=INK, ha="center", zorder=320)
    tag(ax, 790, 700, "Base pan, UP piece", 1, hi=True)
    tag(ax, 790, 652, "M8 washer as a shim, under the sheet", 7, hi=True)
    tag(ax, 790, 604, "M8 × 16 button head + washer", 8, hi=True)
    tool(ax, 790, 540, "5 mm hex  ·  caulking gun")
    body(ax, "The UP piece lies on the DOWN piece over the 40 lap, so the rest of it stands 1.6 proud of its rails: "
             "a washer under each of its other\nseven slots fills that, or the screw pulls the sheet down into a "
             "dent. Run a bead of silicone along the DOWN piece 10 in from its edge before\nthe UP piece goes "
             "down. The UP piece is on top because water runs left, down the fall: it sheds over the lap, never "
             "under it.")
    save(fig, ax, pdf, "18")


# ============================================================ 19 trays
@page
def s19(pdf):
    fig, ax = new_page(19, "Trays  ·  the same, three times",
                       "Steps 17 and 18 on tiers A, B and C. 203 deep: the tray stops at the tray line.")
    lift = 90.0
    parts = cab(18, extra_m=(), feet=True)
    parts.append(Part(C.sheet_world("basepan_DOWN", 0.0), SHEET, lw=0.4, ang=30))
    parts.append(Part(C.sheet_world("basepan_UP", 0.0), SHEET, lw=0.4, ang=30))
    for z in C.TIERS:
        parts += nut_parts(z, ("DOWN", "UP"), hi=True)
        parts.append(Part(mv(C.sheet_world("tray_DOWN", z), 0, 0, lift), HILITE, lw=0.4, ang=30))
        parts.append(Part(mv(C.sheet_world("tray_UP", z), 0, 0, lift * 1.6), HILITE, lw=0.4, ang=30))
    MMv = view(212, 22)
    v = scene(ax, parts, (400, 470), (560, 560), MM=MMv, px=1.9)
    rows = [("Each tray", "8 nuts, DOWN piece and 7 × M8 × 12,\n7 shims, UP piece and 8 × M8 × 16"),
            ("All three", "24 nuts, 21 × M8 × 12, 21 shims,\n24 × M8 × 16"),
            ("Check", "the tray's back lip on S's back face,\nflush with the tray line at 203")]
    for i, (a, b) in enumerate(rows):
        y = 700 - i * 92
        ax.text(780, y, a, fontsize=11, fontweight="bold", color=INK)
        ax.text(780, y - 10, b, fontsize=9.2, color=DIM, va="top", linespacing=1.45)
    tag(ax, 780, 420, "Tray, DOWN piece", 3, hi=True)
    tag(ax, 780, 372, "Tray, UP piece", 3, hi=True)
    tool(ax, 780, 316, "5 mm hex  ·  caulking gun")
    body(ax, "Bottom tier first, so nothing you drop lands in a finished tray. Each tray hugs FL and FR with its "
             "41 × 41 notches and stops at the\ntray line: its back lip must not lean into the corridor. If a tray "
             "will not sit flat, a ledge is off its mark: fix the frame, not the tray.")
    save(fig, ax, pdf, "19")


# ============================================================ 20 drains
def bulkhead_at(x, y, z_floor):
    return C.bulkhead_mesh(x, y, z_floor)


TUBE = np.array([0.52, 0.74, 0.90])
FITTING = np.array([0.93, 0.93, 0.90])


@page
def s20(pdf):
    fig, ax = new_page(20, "Drains  ·  one riser on the FL post",
                       "A bulkhead in each tray, a short branch out of the side, one riser zip-tied to the post.")
    from kit3d import tube
    parts = cab(20, feet=True, lo=(-60, -60, -40), hi=(560, C.D + 60, 1840))
    dx, dy = C.DRAIN["tray_DOWN"]
    r = C.drain_routes()
    parts += [Part(bulkhead_at(dx, dy, z + C.SER), HILITE, lw=0.4, ang=30) for z in C.TIERS]
    parts += [Part(tube(P, C.TUBE_R, 12), TUBE, lw=0.4, ang=30) for P in r["branches"] + [r["riser"]]]
    parts += [Part(m, HILITE if k != "tie" else INKISH, lw=0.4, ang=30) for k, m in C.drain_fittings()]
    parts.append(Part(C.bucket_mesh(), np.array([0.30, 0.32, 0.34]), lw=0.4, ang=30))
    MMv = view(222, 14)
    v = scene(ax, parts, (320, 462), (520, 610), MM=MMv, px=2.0,
              focus=fbox([-280, 0, -40], [420, 300, 1480]), clip=(24, 150, 600, 772))
    for lab, z in (("C", C.TIERS[2]), ("B", C.TIERS[1]), ("A", C.TIERS[0])):
        q = v((dx + 40, dy, z + C.SER + 30))
        ax.text(q[0], q[1], f"tier {lab}", fontsize=8.6, fontweight="bold", color=INK, zorder=320,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    q = v((C.RISER[0] - 20, C.RISER[1], (C.TIERS[1] + C.TIERS[2]) / 2))
    ax.plot([q[0], q[0] - 60], [q[1], q[1]], color=DIM, lw=0.8, zorder=320)
    ax.text(q[0] - 64, q[1], "riser, zip-tied\nto FL", fontsize=8.6, color=INK, ha="right", va="center",
            zorder=320, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    bk = v((C.BUCKET["x"] - C.BUCKET["r_top"], C.BUCKET["y"], 80.0))
    ax.plot([bk[0], bk[0] - 40], [bk[1], bk[1] - 20], color=DIM, lw=0.8, zorder=320)
    ax.text(bk[0] - 44, bk[1] - 20, "bucket, on the floor", fontsize=8.6, color=INK, ha="right", va="center",
            zorder=320, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    # inset 1: one drain, exploded: flange and washer above the floor, washer and nut below
    from kit3d import revolve, ring
    b_ = C.BULKHEAD
    zf = C.TIERS[1] + C.SER
    tr = Part(C.sheet_world("tray_DOWN", C.TIERS[1]), SHEET, lw=0.45, ang=30)
    rails = cab(19, lo=(-10, -10, zf - 60), hi=(260, 240, zf + 40))
    e = 34.0
    fl = mv(rot(revolve([(0, 0), (b_["flange_r"], 0), (b_["flange_r"], 3), (b_["body_r"], 3),
                         (b_["body_r"], 26), (0, 26)]), rx=math.pi), dx, dy, zf + C.T_SHEET + 3 + e)
    wa = mv(ring(b_["flange_r"] - 1, 11.2, 2.0), dx, dy, zf + C.T_SHEET + e * 0.45)
    wb = mv(ring(b_["flange_r"] - 1, 11.2, 2.0), dx, dy, zf - 2.0 - e * 0.45)
    nt = mv(cylinder(b_["nut_r"], b_["nut_t"], n=6), dx, dy, zf - 10.0 - e)
    det = rails + [tr] + [Part(m, HILITE, lw=0.45, ang=30) for m in (fl, wa, wb, nt)]
    vi = inset(ax, 620, 174, 236, 236, det, iso_matrix(212, 26), focus=fbox([20, 40, zf - 70], [120, 150, zf + 60]),
               label="one drain, exploded")
    axis3(ax, vi, (dx, dy, zf - e - 30), (dx, dy, zf + e + 40))
    # inset 2: tier B's branch meeting the riser at FL
    zl = C.TIERS[1]
    lo_, hi_ = (-40, -10, zl - 120), (120, 140, zl + 60)
    det2 = cab(20, lo=lo_, hi=hi_)
    det2 += [Part(tube(P, C.TUBE_R, 12), TUBE, lw=0.45, ang=30) for P in r["branches"] + [r["riser"]]]
    det2 += [Part(m, HILITE if k != "tie" else INKISH, lw=0.45, ang=30) for k, m in C.drain_fittings()]
    det2.append(Part(bulkhead_at(dx, dy, zl + C.SER), HILITE, lw=0.45, ang=30))
    inset(ax, 868, 174, 242, 236, det2, iso_matrix(252, 16), focus=fbox([-30, 0, zl - 70], [90, 110, zl + 45]),
          label="B's branch: under L2, a tee")
    tag(ax, 620, 712, "Bulkhead 1/2 in, EPDM washers", 3, hi=True)
    tag(ax, 620, 668, "Elbow 90°, 1/2 in MNPT × 1/2 in barb", 3, hi=True)
    tag(ax, 620, 624, "Barbed elbow 1/2 in", 1, hi=True)
    tag(ax, 870, 624, "Barbed tee 1/2 in", 2, hi=True)
    tag(ax, 620, 580, "Drain tube 1/2 in ID, 10 ft", 1)
    tag(ax, 870, 580, "Zip tie 300", 5)
    tag(ax, 620, 536, "Bucket, 2 gal, lidded", 1)
    note(ax, 870, 548, "BOM G090 to G090c.", fs=9.0)
    rows = [("C", "elbow at the top of the riser"), ("B, A", "a tee each, 40 under the rail"),
            ("Pan", "no drain: the dry catch tray")]
    for i, (a, b) in enumerate(rows):
        y = 486 - i * 26
        ax.text(620, y, a, fontsize=9.6, fontweight="bold", color=INK, va="center")
        ax.text(680, y, b, fontsize=9.0, color=DIM, va="center")
    body(ax, "Flange and one washer inside the tray, the second washer and the nut underneath; hand tight plus a "
             "quarter turn. Screw an elbow into each\nbulkhead, run its branch under the left rail and out of the "
             "side, falling all the way. Zip-tie the riser to FL every 300 or so, never kinked, and\nlead its end "
             "through a hole in the bucket lid. Every tray drains on its own: no tray takes another's runoff. "
             "Never plumb it back to the reservoir.")
    save(fig, ax, pdf, "20")


# ============================================================ 21 before you load it
@page
def s21(pdf):
    fig, ax = new_page(21, "Before you load it",
                       "The checks that catch the usual faults, while the cabinet is still empty.")
    rows = [("Anchored to the wall", "Two anti-tip brackets into studs, BOM G015. 1.85 m tall and 0.56 deep tips "
             "forward with the trays full."),
            ("Every screw tight", "88 gusset screws, 60 sheet screws, 20 grubs. A paint mark on each as you go."),
            ("The falls", "A level on each tray floor: the bubble sits toward the right. Water stands nowhere."),
            ("Water test", "1 L into each tray. Each one empties down its branch and the riser into the bucket. "
             "The pan stays dry."),
            ("The corridor", "A tape run along the tray line at 203: nothing of the frame behind it but the "
             "back posts and back rails."),
            ("The top", "Level both ways across F4 and B4: the gantry's X rail hangs below B4 (Gantry Rev E, "
             "step 23).")]
    checkbox_rows(ax, rows, y0=690, dy=90)
    body(ax, "Leak sensors: one in the base pan, one beside the bucket (BOM G074). The panels and doors are the "
             "next booklet; the gantry\nbooklet starts from here at its step 21.", fs=10.2)
    save(fig, ax, pdf, "21")



# ============================================================ cover
# Every Maag booklet carries the same cover: the gantry booklet's render.
COVER = os.environ.get("MAAG_COVER", os.path.join(_HERE, "..", "gantry", "cover", "cover.png"))


def p_cover(pdf):
    """The Maag cover render full-bleed on top, title block underneath, as on the gantry booklet."""
    fig = plt.figure(figsize=(11.5, 9.0), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1150); ax.set_ylim(0, 900)
    if os.path.exists(COVER):
        img = plt.imread(COVER)
        h, w = img.shape[:2]
        Hh = 1150.0 * h / w
        ax.imshow(img, extent=(0, 1150, 900 - Hh, 900), zorder=1, interpolation="lanczos")
        y0 = 900 - Hh
    else:
        ax.add_patch(Rectangle((0, 190), 1150, 710, facecolor="#e8edf0", edgecolor="none"))
        ax.text(575, 545, "cover render not found:\n" + COVER, ha="center", va="center", color=DIM)
        y0 = 190
    ax.set_aspect("auto")
    t = ax.text(48, y0 - 50, "Maag", fontsize=34, fontweight="bold", family=TITLE_FONT, color=INK, va="center")
    fig.canvas.draw()
    bb = t.get_window_extent().transformed(ax.transData.inverted())
    ax.text(bb.x1 + 18, y0 - 47, "Modular Agentic Autonomous Greenhouse", fontsize=14, fontweight="medium",
            family=TITLE_FONT, color=INK, va="center")
    ax.text(50, y0 - 100, f"Frame and trays assembly instructions, {REV}.  The 4040 cabinet, 1397 × 559 × 1829, "
                          "with brackets, trays and feet.", fontsize=12.0, color=DIM, va="center")
    ax.text(1102, y0 - 46, "21 steps  ·  tools  ·  every joint", fontsize=11, color=INK, ha="right", va="center")
    ax.text(1102, 26, f"Design {DESIGN}. The Maag cover render, the same on every booklet. Every drawing inside "
                      "comes from cabinet.py, the Rev 4 sheet-metal outlines and the TPU foot generator.",
            fontsize=7.6, color=DIM, ha="right")
    pdf.savefig(fig); fig.savefig(f"{OUT}/d_000_cover.png", dpi=130); plt.close(fig)


PAGES.insert(0, p_cover)


if __name__ == "__main__":
    only = sys.argv[1:]
    if only:
        class _N:
            def savefig(self, *a, **k):
                pass
        for fn in PAGES:
            if fn.__name__ in only:
                fn(_N()); print(fn.__name__, "ok", flush=True)
        sys.exit(0)
    path = f"{OUT}/Maag_Frame_Assembly_Instructions_RevA.pdf"
    with PdfPages(path) as pdf:
        for fn in PAGES:
            fn(pdf); print(fn.__name__, "ok", flush=True)
    print("saved", path, f"({len(PAGES)} pages)")
