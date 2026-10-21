#!/usr/bin/env python3
"""Maag harvest: assembly instructions, Harvest Rev B (design 0.6.1).

The dead-leaf tray on its guide rails in the base bay, and the side feeder on
the right panel at tier B. Every drawing comes from harvest.py on top of
enclosure.py and cabinet.py; the arm is the myCobot 280 Pi's own meshes and
the snip is the Herb Snip's printed body, posed by reach.py (drops.yaml).

    MAAG_ARM_NPZ=... SNIP_STL=... python make_harvest_booklet.py        # whole booklet
    python make_harvest_booklet.py s3 s7                                # just those pages, PNG only
"""
import functools
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
for sub in ("enclosure", "frame", "booklet", "gantry"):
    sys.path.insert(0, os.path.join(_HERE, "..", sub))

import make_enclosure_booklet as EB                                    # noqa: E402
import maagbook as B                                                   # noqa: E402
from maagbook import (new_page, scene, inset, save, arrow2, axis3, tag, tool, note, panel, checkbox_rows,   # noqa: E402
                      Circle, Rectangle, FancyBboxPatch, Polygon, TITLE_FONT, INK, DIM, ACCENT, WARN, OK, AXIS,
                      EDGE, RULE)
from kit3d import Part, iso_matrix, merge, mv, rot, box, cylinder, ALU, ALU_D, STEEL, BLACKPART, HILITE   # noqa: E402
import cabinet as C                                                    # noqa: E402
import enclosure as E                                                  # noqa: E402
import harvest as Hv                                                   # noqa: E402
import csg                                                             # noqa: E402
import reach as R                                                      # noqa: E402

REV = "Harvest Rev B"
DESIGN = "0.6.1"
OUT = os.environ.get("HARVEST_OUT", os.path.join(_HERE, "build"))
B.configure(REV, OUT)

import matplotlib.pyplot as plt                                        # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages                   # noqa: E402

PAGES = []
body = EB.body
FB = EB.FB
F = Hv.FEEDER
NSTEPS = 12
PRINT = np.array([0.93, 0.93, 0.89])         # the printed parts
HARV = np.array([0.80, 0.89, 0.76])          # the feeder's trays, so they read apart from the modules
FROST, CLEARC, WHITEP, EPDM = EB.FROST, EB.CLEARC, EB.WHITEP, EB.EPDM
SHEET = FB.SHEET
ARM_OK = R.load_meshes()
ARM_FULL = R.full_meshes()
DROPS = json.load(open(os.path.join(_HERE, "drops.json"))) if os.path.exists(os.path.join(_HERE, "drops.json")) else None


def page(fn):
    PAGES.append(fn)
    return fn


def view(az, el):
    return iso_matrix(az, el)


FRONT_RIGHT = (146, 18)


# ============================================================ model pieces
@functools.lru_cache(maxsize=None)
def _cab_full():
    return tuple(FB.cab(99, feet=True))


@functools.lru_cache(maxsize=None)
def _cab_box(lo, hi):
    return tuple(FB.cab(99, feet=True, lo=lo, hi=hi))


@functools.lru_cache(maxsize=None)
def _feeder(open_deg=0.0, trays=True, lid=True, fasteners=True):
    return Hv.feeder_meshes(open_deg=open_deg, trays=trays, lid=lid, fasteners=fasteners)


@functools.lru_cache(maxsize=None)
def _tray(out=0.0):
    return Hv.tray_meshes(out)


@functools.lru_cache(maxsize=None)
def _rails():
    return Hv.rail_meshes()


def pan_bolts(skip_rail=True, explode=0.0):
    """The base pan's own fasteners, less the four the rails take over."""
    out = []
    for kind, m in C.sheet_fasteners(0.0, nuts=False):
        V = m[0]
        c = V.mean(0)
        on_rail = any(abs(c[0] - x) < 9 for x in Hv.BOLT_X) and any(abs(c[1] - y) < 9 for y in Hv.BOLT_Y)
        if skip_rail and on_rail:
            continue
        out.append(Part(m, STEEL, lw=0.25, ang=30))
    return out


def col_of(name):
    if name.startswith(("module", "hood", "basin", "skirt")):
        return PRINT
    if name.startswith("tray_"):
        return HARV
    if name in ("lid",):
        return CLEARC
    if name.startswith(("hinge", "m5", "m4", "washer", "handle_bolt", "handle_nyloc", "rail_bolt", "rail_washer")):
        return STEEL
    if name.startswith("wellnut"):
        return BLACKPART
    if name.startswith("reed"):
        return WHITEP
    if name == "handle":
        return PRINT
    return ALU


def parts_of(d, hi=(), ghost=(), lw=0.35, only=None, skip=()):
    out = []
    for k, m in d.items():
        if only and not any(k.startswith(o) for o in only):
            continue
        if any(k.startswith(s) for s in skip):
            continue
        h = any(k.startswith(x) for x in hi)
        g = any(k.startswith(x) for x in ghost) or k == "lid"
        out.append(Part(m, HILITE if h else col_of(k), lw=lw if not k.startswith(("m5", "m4", "washer")) else 0.25,
                        ang=30, ghost=g and not h))
    return out


def enclosure(drop=(), bottom_left=0.0, right_ghost=False):
    """The finished enclosure (EB.enc), the bottom-left door at an angle."""
    parts = EB.enc(EB.NSTEPS, drop=tuple(drop) + ("door_bottom_L",))
    if "door_bottom_L" not in drop:
        parts += EB.door_set("bottom", "L", bottom_left)
    return parts


def arm_parts(pose, hi=False):
    """The gantry, the arm in `pose` (a drops.json entry), and the snip on its flange."""
    import frame as GF
    xc, zj, q = pose["carriage_x"], pose["j1_z"], pose["joints_deg"]
    out = GF.gantry_parts(xc, zj, q=q, grid=0.0 if ARM_FULL else 0.0015)     # the arm's own CAD, undecimated
    T = R.snip_tris()
    if T is not None:
        M = GF.arm_base_frame(xc, zj) @ R.tool_T(q)
        V = T.reshape(-1, 3)
        Vw = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
        Fs = np.arange(len(Vw)).reshape(-1, 3)
        out.append(Part((Vw, Fs), HILITE if hi else np.array([0.85, 0.86, 0.80]), lw=0.3, ang=30))
    return out


def lab(ax, v, p, text, dx=60, dy=0, ha="left", fs=8.8, bold=False):
    EB.lab(ax, v, p, text, dx, dy, ha, fs, bold)


# ============================================================ cover
COVER = EB.COVER


def p_cover(pdf):
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
    ax.text(50, y0 - 100, f"Harvest assembly instructions, {REV}.  The dead-leaf tray in the base, the side "
                          "feeder on the right.", fontsize=12.0, color=DIM, va="center")
    ax.text(1102, y0 - 46, f"{NSTEPS} steps  ·  tools  ·  where every cut goes", fontsize=11, color=INK, ha="right",
            va="center")
    ax.text(1102, 26, f"Design {DESIGN}. The Maag cover render, the same on every booklet. Every drawing inside "
                      "comes from harvest.py, enclosure.py and cabinet.py; the cut files come from the same model.",
            fontsize=7.6, color=DIM, ha="right")
    pdf.savefig(fig); fig.savefig(f"{OUT}/d_000_cover.png", dpi=130); plt.close(fig)


# ============================================================ overview
@page
def p_overview(pdf):
    fig, ax = new_page(None, "Harvest  ·  where every cut goes",
                       "Dead leaves down into a tray in the base. Leaves and veggies out, into a feeder on the right.")
    parts = enclosure(bottom_left=118.0) + parts_of(_feeder()) + parts_of(_tray(230.0)) + parts_of(_rails())
    v = scene(ax, parts, (430, 470), (700, 600), MM=view(*FRONT_RIGHT), px=1.4, clip=(24, 150, 860, 772))
    ym = (F.mods[0][0] + F.mods[1][1]) / 2
    lab(ax, v, (C.W + F.wb + 60, (F.mods[0][0] + F.mods[0][1]) / 2, F.vf + 40), "leaves", dx=90, dy=-40, bold=True)
    lab(ax, v, (C.W + F.wb + 60, (F.mods[1][0] + F.mods[1][1]) / 2, F.vf + 40), "veggies", dx=90, dy=-10, bold=True)
    lab(ax, v, (C.W + F.wb + 90, ym, F.lid_top(90)), "clear lid on a piano hinge, flush\nwith the walls, "
        "lifts to lean on the panel", dx=-40, dy=120, ha="right")
    lab(ax, v, (C.W + F.wb + 30, ym, F.vf - 20), "sloped skirt", dx=70, dy=-60)
    lab(ax, v, (400.0, Hv.TRAY["y0"] - 230 - 10, Hv.HANDLE["z1"] - 10), "dead-leaf tray, slid out\nby its handle",
        dx=-150, dy=40, ha="right", bold=True)
    lab(ax, v, (Hv.RAIL["web"][0], 120.0, Hv.RAIL["run"]), "two guide rails on the base pan", dx=-120, dy=-60,
        ha="right")
    ax.text(880, 740, "What goes where", fontsize=10.5, fontweight="bold", color=INK, family=TITLE_FONT)
    rows = [("Leaves", "Herb leaves to eat: out through the\nright panel, the front compartment."),
            ("Veggies", "Fruit and pods: the back compartment.\nEach has its own lift-out tray."),
            ("Dead leaves", "Down, into the 10 L tray in the base.\nFive drop points spread them along it."),
            ("Collect", "Lift the lid by the scoop, lift a tray\nup and out. The arm has no power\nwhile the lid is open.")]
    for i, (h, t) in enumerate(rows):
        y = 706 - i * 78
        ax.text(880, y, h, fontsize=9.6, fontweight="bold", color=ACCENT)
        ax.text(880, y - 18, t, fontsize=8.6, color=INK, va="top", linespacing=1.4)
    body(ax, "The feeder is two printed compartments side by side on the outside of the right panel at tier B, the "
             "third shelf up from the floor, under one clear lid that\nsits flush with their walls, like the side "
             "feeders on a bird cage: the arm puts the harvest in from the inside, you take it out from the outside, "
             "and the doors\nstay shut. A finger scoop under the lid's edge lifts it; a sloped skirt closes the shape "
             "underneath. The tray in the base slides out of the bottom-left\ndoor alone. The modular cabinet can "
             "put the feeder on the left: it is the same parts, mirrored.", fs=9.4)
    save(fig, ax, pdf, "00a_overview")


# ============================================================ how the arm drops
def _drop(nm, leg="release"):
    if not DROPS:
        return None
    for p in DROPS["feeder"].get(nm, []):
        if p["leg"] == leg:
            return p
    return None


def feeder_cut(u_cut):
    """The feeder cut away in front of u_cut, to see into it from the front."""
    f = F
    out = []
    keep = csg.box(-50, u_cut, f.vf - 50, 400, 2000, f.vt + 400)
    for k in (0, 1):
        m = f.module_solid(k) ^ keep
        if m.volume() > 0:
            out.append(Part(f.to_world(csg.to_mesh(m)), PRINT, lw=0.4, ang=30))
        t = f.tray_solid(k) ^ keep
        if t.volume() > 0:
            out.append(Part(f.to_world(csg.to_mesh(t)), HARV, lw=0.4, ang=30))
    V, Fc = f.lid_mesh()
    V = V.copy()
    V[:, 1] = np.maximum(V[:, 1], u_cut)
    out.append(Part(f.to_world((V, Fc)), CLEARC, lw=0.4, ang=30, ghost=True))
    fixed, leaf = f.hinge_mesh()
    for m in (fixed, leaf):
        Vm = m[0].copy()
        Vm[:, 1] = np.maximum(Vm[:, 1], u_cut)
        out.append(Part(f.to_world((Vm, m[1])), STEEL, lw=0.3, ang=30))
    return out


@page
def p_how(pdf):
    fig, ax = new_page(None, "How the arm drops",
                       "The arm, the snip and every margin from reach.py: posed, then checked against the model.")
    ok = ARM_OK and DROPS
    # left: the feeder, from the front, the arm at the leaves release
    lo, hi = (1100.0, 150.0, 880.0), (1600.0, 560.0, 1320.0)
    cab = list(_cab_box(lo, hi))
    fp = feeder_cut(_drop("leaves")["release_xyz"][1] if _drop("leaves") else 285.0)
    pr = Part(E.panel_mesh("right"), FROST, lw=0.4, ang=30, ghost=True)
    if ok:
        arm = arm_parts(_drop("leaves"))
        v1 = inset(ax, 40, 300, 520, 470, cab + [pr] + fp + arm, view(180, 6), px=1.6,
                   focus=FB.fbox((1150, 0, 900), (1590, 500, 1300)),
                   label="the feeder from the front, the arm at the leaves drop")
        p = _drop("leaves")["release_xyz"]
        q = v1(p)
        ax.add_patch(Circle(tuple(q), 6, facecolor=ACCENT, edgecolor="white", lw=1.0, zorder=330))
        arrow2(ax, (q[0], q[1] - 8), (q[0], v1((p[0], p[1], F.vf + F.FLOOR + 10))[1]), color=ACCENT, lw=1.6)
        lab(ax, v1, (C.W + 2, 300, F.openings[0][3] - 10), "through the opening\nin the right panel", dx=-160,
            dy=60, ha="right")
        lab(ax, v1, (C.W + F.wb + 120, 285, F.vf + 30), "the leaves tray, cut away", dx=10, dy=-70)
    # right: the base bay, the arm at a tray drop
    lo2, hi2 = (60.0, -40.0, -30.0), (760.0, 600.0, 700.0)
    cab2 = list(_cab_box(lo2, hi2))
    tp = parts_of(_tray(0.0)) + parts_of(_rails())
    if ok:
        d = DROPS["tray"].get("drop3") or list(DROPS["tray"].values())[0]
        arm2 = arm_parts(d)
        v2 = inset(ax, 590, 300, 520, 470, cab2 + tp + arm2, view(212, 14), px=1.6,
                   focus=FB.fbox((100, 0, 0), (720, 560, 640)),
                   label="the base bay, the arm at its lowest, over the tray")
        q = v2(d["release_xyz"])
        ax.add_patch(Circle(tuple(q), 6, facecolor=ACCENT, edgecolor="white", lw=1.0, zorder=330))
        arrow2(ax, (q[0], q[1] - 8), (q[0], v2((d["release_xyz"][0], d["release_xyz"][1], Hv.TRAY["z0"] + 5))[1]),
               color=ACCENT, lw=1.6)
    if not ok:
        for x0_ in (40, 590):
            panel(ax, x0_, 300, 520, 470, z=5)
        for x in (300, 850):
            ax.text(x, 530, "arm meshes not found:\nset MAAG_ARM_NPZ and SNIP_STL", ha="center", color=DIM, zorder=330)
    # margins table
    if DROPS:
        ax.text(60, 272, "Tightest gaps, mm (reach.py, the snip's printed body and the arm's own meshes)", fontsize=9.4,
                fontweight="bold", color=INK)
        rows = []
        for nm in F.NAMES:
            for p in DROPS["feeder"].get(nm, []):
                m = sorted((v, k) for k, v in p["margins"].items() if k != "self")[:2]
                rows.append(f"{nm:8s} {p['leg']:8s}  " + "   ".join(f"{k} {v:.0f}" for v, k in m))
        for nm, p in DROPS["tray"].items():
            m = sorted((v, k) for k, v in p["margins"].items() if k != "self")[:2]
            rows.append(f"tray {nm:6s} x {p['release_xyz'][0]:4.0f}  " + "   ".join(f"{k} {v:.0f}" for v, k in m))
        for i, t in enumerate(rows):
            ax.text(60 + (i // 6) * 540, 250 - (i % 6) * 15, t, fontsize=7.6, color=INK, family=TITLE_FONT)
    if DROPS and DROPS.get("tool", "").startswith("provisional"):
        ax.text(1110, 290, "Provisional: the Herb Snip's first printed body. The final poses come from its "
                           "housing version, with the D405.", fontsize=8.4, color=WARN, ha="right", va="center",
                zorder=330)
    ax._body_y = 60.0
    body(ax, "Each drop is three moves at the feeder: the snip level inside the cabinet, out through its "
             "compartment's opening above the tray, then down to 28 over the\ntray's rim and open. The snip's wide "
             "servo end never leaves the cabinet. Dead leaves go at the arm's lowest, jaws down, 55 over the rim. "
             "The poses are\nin drops.yaml for the Herb Snip's software; commissioning jogs to each before the first "
             "harvest.", fs=9.0)
    save(fig, ax, pdf, "00b_how")


# ============================================================ parts
@page
def p_parts(pdf):
    fig, ax = new_page(None, "Harvest  ·  parts",
                       "Count everything first. SendCutSend cuts and bends the metal and the lid; you print the rest.")
    f = F
    hinge = merge(box(E.LEAF_W, E.LEAF_T, 200.0, c=(0, 0, 0)), box(E.LEAF_W, E.LEAF_T, 200.0, c=(-E.LEAF_W, 0, 0)),
                  mv(cylinder(E.KNUCKLE_R, 200.0, n=20), 0, E.LEAF_T / 2, 0))
    lid_flat = box(f.lid_flat()[1], f.lid_flat()[0], Hv.LID_T)
    sw = merge(box(*E.REED["sw"]), mv(box(*E.REED["mag"]), 0, 26, 0))
    items = [("Guide rail L, 5052", "1", Hv.rail_mesh("L"), ALU, (210, 30)),
             ("Guide rail R, 5052", "1", Hv.rail_mesh("R"), ALU, (150, 30)),
             ("Dead-leaf tray, 5052", "1", Hv.tray_mesh(), ALU, (200, 34)),
             ("Handle, printed", "1", Hv.handle_mesh(), PRINT, (200, 16)),
             ("Hood, leaves", "1", csg.to_mesh(f.hood_solid(0)), PRINT, (62, 30)),
             ("Hood, veggies", "1", csg.to_mesh(f.hood_solid(1)), PRINT, (62, 30)),
             ("Basin, printed", "2", csg.to_mesh(f.basin_solid(0)), PRINT, (62, 30)),
             ("Skirt, printed", "2", csg.to_mesh(f.skirt_solid(0)), PRINT, (62, -24)),
             ("Feeder tray, printed", "2", csg.to_mesh(f.tray_solid(0)), HARV, (62, 34)),
             ("Lid, clear 4.5", "1", lid_flat, CLEARC, (30, 30)),
             ("Piano hinge, 1 ft", "1", hinge, STEEL, (30, 30)),
             ("Reed switch 7939WG", "1", sw, WHITEP, (30, 30)),
             ("Rubber well nut M4", "4", Hv.well_nut_mesh(), BLACKPART, (30, 30))]
    for i, (nm, q, m, col, (az, el)) in enumerate(items):
        r, c = divmod(i, 5)
        cx, cy = 92 + c * 212, 712 - r * 150
        scene(ax, [Part(m, col, ang=30, lw=0.5, ghost=col is CLEARC)], (cx + 20, cy + 8), (140, 88),
              MM=iso_matrix(az, el), clip=(cx - 70, cy - 42, cx + 110, cy + 60))
        ax.text(cx - 60, cy - 54, nm, fontsize=8.6, color=INK, va="center")
        ax.text(cx - 60, cy - 72, f"{q}×", fontsize=9.8, color=ACCENT, fontweight="bold", va="center")
    ax.text(60, 214, "Also, no picture needed:", fontsize=9.6, fontweight="bold", color=INK)
    rows = ["VHB 4905, 1/2 in: both hinge leaves and the two skirts (from the enclosure's roll)",
            "Two lever connectors (Wago 221-412) and 3 m of 2-core alarm cable for the switch",
            "Six small adhesive cable clips for the switch's wire inside the cabinet",
            "Print settings: PETG or PLA, 0.2 layers, 4 walls, 20 % gyroid, no supports: hoods standing on their "
            "joint face, basins and trays on their floors, skirts on their open back, the handle flat"]
    for i, t in enumerate(rows):
        ax.text(60, 192 - i * 18, t, fontsize=8.6, color=INK)
    ax._body_y = 60.0
    save(fig, ax, pdf, "00c_parts")


# ============================================================ fasteners
@page
def p_fasteners(pdf):
    fig, ax = new_page(None, "Harvest  ·  fasteners",
                       "Every screw in the build. Lay them out in labelled pots first.")
    items = [("M8 × 16 button head  ·  rails, the pan's\nown washers", "4",
              lambda: [(C.HW.button_head(8, 16.0, detail=True), STEEL)]),
             ("M5 × 10 button head  ·  handle", "3", lambda: [(C.HW.button_head(5, 10.0, detail=True), STEEL)]),
             ("M5 nyloc  ·  handle, in its pockets", "3", lambda: C.HW.nyloc_parts(5)),
             ("M5 × 20 button head  ·  feeder, rail", "4", lambda: [(C.HW.button_head(5, 20.0, detail=True), STEEL)]),
             ("DIN 9021 washer M5  ·  the panel's", "4", lambda: [(E.washer9021(), STEEL)]),
             ("M4 × 20 button head  ·  feeder, top", "4", lambda: [(C.HW.button_head(4, 20.0, detail=True), STEEL)]),
             ("M4 rubber well nut, 10 hole", "4", lambda: [(Hv.well_nut_mesh(), BLACKPART)])]
    for i, (nm, q, fn_) in enumerate(items):
        r, c = divmod(i, 3)
        cx, cy = 96 + c * 352, 700 - r * 118
        scene(ax, [Part(m, col, ang=30, lw=0.5) for m, col in fn_()], (cx, cy), (78, 78), MM=iso_matrix(30, 32),
              clip=(cx - 50, cy - 50, cx + 50, cy + 50), px=7.0)
        ax.text(cx + 60, cy + 11, nm, fontsize=8.3, color=INK, va="center", linespacing=1.3)
        ax.text(cx + 60, cy - 15, f"{q}×", fontsize=10.0, color=ACCENT, fontweight="bold", va="center")
    st = Hv.tray_checks()["rail bolt M8 x 16: stack, reach, spare"]
    fs_ = F.screw_stacks()
    m5 = fs_["M5 x 20, rail"]
    note(ax, 60, 330, f"Rails: the pan's bolts at x 150 and 650, front and back, go from M8 × 12 to M8 × 16: the "
                      f"rail's flange adds 1.6. Stack {st[0]}, reach {st[1]},\n{st[2]} short of the slot floor, as on "
                      f"the pan's UP piece. Feeder: M5 × 20 through the back plate, the panel and the tape: stack "
                      f"{m5['stack']}, {m5['past_lips']} past the\nlips, {m5['spare']} short of the floor, the same as "
                      "every panel screw. The four M5 × 16 the panel wore there until now go back in the spares pot.",
         fs=9.2, color=INK)
    ax._body_y = 60.0
    body(ax, "Well nuts are rubber sleeves with a brass nut moulded in the far end: push one into a 10 mm hole, "
             "turn the screw, and the sleeve folds up behind the panel\nand grips it. Nothing to hold on the "
             "inside, which is why the feeder's top screws use them: there is no frame behind the panel there.",
         fs=9.2, color=WARN)
    save(fig, ax, pdf, "00d_fasteners")


# ============================================================ tools
def _tools():
    import tools_lib as T
    from tools_page import hex_key

    def keys():
        out = []
        for i, (af, L1, L2) in enumerate(((2.5, 112, 20), (3.0, 125, 23), (5.0, 155, 30))):
            for m, c in hex_key(af, L1, L2):
                out.append((mv(m, 0, 0, -i * 10.0), c))
        return out

    return [
        (keys, "Hex keys, ball end", "2.5 · 3 · 5 mm, long series",
         "5: the rails' M8s, 2  ·  3: every M5,\n3, 7  ·  2.5: the M4s, 8", (30, 34)),
        (T.tape_measure, "Tape measure", "5 m", "the switch and the magnet, 5", (32, 26)),
        (T.utility_knife, "Utility knife", "18 mm snap-off, and scissors", "VHB, 5, 9 and 10", (25, 30)),
        (T.ipa_and_cloth, "Isopropyl alcohol", "and microfibre cloths", "every VHB bond, 5, 9 and 10", (25, 28)),
        (T.flush_cutters, "Side cutters", "125 mm, flush cut", "the switch's cable, 11", (25, 40)),
    ]


@page
def p_tools(pdf):
    fig, ax = new_page(None, "Tools",
                       f"Everything the {NSTEPS} steps need, and your printer for the nine printed parts.")
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
    ax.text(330, 300, "And a wire stripper for the switch's cable, a step\nstool for the feeder, and a helper to "
                      "hold each\nbasin while you start its screws.",
            fontsize=9.6, color=INK, va="top", linespacing=1.5)
    ax._body_y = 60.0
    save(fig, ax, pdf, "00e_tools")


# ============================================================ sections
def _rect(ax, x, y, w, h, fc, ec=INK, lw=0.7, z=20, hatch=None, alpha=1.0):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, lw=lw, zorder=z, hatch=hatch, alpha=alpha))


def sec_feeder(ax, ox, oy, s):
    """True-scale section through the leaves compartment, in (w, v): the side
    rail, tape, panel, the basin, hood and skirt, the tray, the lid and hinge,
    the snip's jaws at the release."""
    f = F
    X = lambda w: ox + w * s                                    # noqa: E731
    Y = lambda v: oy + (v - f.vf) * s                           # noqa: E731
    PR = "#f1f1ea"
    for zl in (f.rail_v - 20.0,):
        _rect(ax, X(-40), Y(zl), 40 * s, 40 * s, "#dfe5e9", z=10)
        _rect(ax, X(-C.SLOT_DEPTH), Y(zl + 20 - 4.1), C.SLOT_DEPTH * s, 8.2 * s, "white", ec="none", z=11)
    _rect(ax, X(0), Y(f.rail_v + E.LINE_IN), E.TAPE * s, E.TAPE_W * s, "#33373a", ec="none", z=12)
    a0, a1 = f.openings[0][2], f.openings[0][3]
    for v0, v1 in ((f.v_low - 10, a0), (a1, f.vt + 10)):
        _rect(ax, X(E.TAPE), Y(v0), E.T_PANEL * s, (v1 - v0) * s, "#e6ecef", z=13)
    wb, wo, t, bk = f.wb, f.w_out, f.WALL, f.BACK
    # the basin: back plate, floor, outer wall up to the joint, its lip
    _rect(ax, X(wb), Y(f.vf), bk * s, (f.vj - f.vf) * s, PR, z=14)
    _rect(ax, X(wb), Y(f.vf), (wo - wb) * s, f.FLOOR * s, PR, z=14)
    _rect(ax, X(wo - t), Y(f.vf), t * s, (f.vj - f.vf) * s, PR, z=14)
    lp = f.LIP
    _rect(ax, X(wo - lp["t"]), Y(f.vj), lp["t"] * s, lp["h"] * s, PR, z=14)
    _rect(ax, X(wb), Y(f.vj), lp["t"] * s, lp["h"] * s, PR, z=14)
    # the hood: back plate (cut at the opening), outer wall to the lid line, the ridge
    for v0, v1 in ((f.vj, a0), (a1, f.vt)):
        _rect(ax, X(wb), Y(v0), bk * s, (v1 - v0) * s, PR, z=14)
    ow = [(wo - t, f.vj), (wo - lp["t"] - 0.15, f.vj), (wo - lp["t"] - 0.15, f.vj + lp["h"]), (wo, f.vj + lp["h"])]
    ow += [tuple(p_) for p_ in f.ridge()[:2]] + [(wo - t, float(f.lid_under(wo - t)))]
    ax.add_patch(Polygon([(X(w_), Y(v_)) for w_, v_ in ow], closed=True, facecolor=PR, edgecolor=INK, lw=0.7, zorder=14))
    ax.plot([X(wb) - 3, X(wo) + 3], [Y(f.vj)] * 2, color=DIM, lw=0.6, ls="--", zorder=15)
    # the skirt beyond the floor, hollow
    tri = [(wb, f.vf - f.SKIRT_DROP), (wo, f.vf), (wb, f.vf)]
    ins = Hv._inset(tri, f.SKIRT_T)
    ax.add_patch(Polygon([(X(w_), Y(v_)) for w_, v_ in tri], closed=True, facecolor=PR, edgecolor=INK, lw=0.7, zorder=14))
    ax.add_patch(Polygon([(X(w_), Y(v_)) for w_, v_ in ins], closed=True, facecolor="white", edgecolor=INK, lw=0.5,
                         zorder=14))
    # side wall beyond, in outline
    ax.plot([X(wb + bk), X(wo)], [Y(f.lid_under(wb + bk)), Y(f.lid_under(wo))], color=DIM, lw=0.6, ls=":", zorder=15)
    # tray
    w0, w1, u0, u1, v0, v1 = f.tray_box(0)
    tw = f.TRAY_WALL
    _rect(ax, X(w0), Y(v0), tw * s, (v1 - v0) * s, HARV, z=16)
    _rect(ax, X(w1 - tw), Y(v0), tw * s, (v1 - 30 - v0) * s, HARV, z=16)
    _rect(ax, X(w1 - tw), Y(v1 - 12), tw * s, 12 * s, HARV, z=16)
    _rect(ax, X(w0), Y(v0), (w1 - w0) * s, 2.0 * s, HARV, z=16)
    # lid and hinge
    p0, L = f._lid_span()
    q = [p0, p0 + L * f.d, p0 + L * f.d + Hv.LID_T * f.n, p0 + Hv.LID_T * f.n]
    ax.add_patch(Polygon([(X(w_), Y(v_)) for w_, v_ in q], closed=True, facecolor="#d8e6ee", edgecolor=INK, lw=0.7,
                         zorder=17))
    ax.add_patch(Circle((X(f.pin[0]), Y(f.pin[1])), max(E.KNUCKLE_R * s, 2), facecolor="#9aa3a9", edgecolor=INK,
                        lw=0.6, zorder=18))
    lw_ = E.LEAF_W - E.KNUCKLE_R
    _rect(ax, X(wb + bk), Y(f.pin[1] - E.KNUCKLE_R - lw_), max(E.LEAF_T * s, 1.2), lw_ * s, "#9aa3a9", z=18)
    # M5 on the rail line, through the basin; well nut over the opening, through the hood
    ax.add_patch(Rectangle((X(wb + bk), Y(f.rail_v - 4.75)), 2.75 * s, 9.5 * s, facecolor="#9aa3a9",
                           edgecolor=INK, lw=0.6, zorder=18))
    ax.add_patch(Rectangle((X(-8.1), Y(f.rail_v - 2.5)), (wb + bk + 8.1) * s, 5 * s, facecolor="#b7bec3",
                           edgecolor=INK, lw=0.5, zorder=17))
    ax.add_patch(Rectangle((X(-Hv.WELL["body_l"] + E.OUT), Y(f.v_top_bolt - Hv.WELL["body_d"] / 2)),
                           Hv.WELL["body_l"] * s, Hv.WELL["body_d"] * s, facecolor="#3b3f42", edgecolor=INK, lw=0.5,
                           zorder=17))
    if DROPS and _drop("leaves"):
        p = _drop("leaves")["release_xyz"]
        wr, vr = p[0] - C.W, p[2]
        ax.add_patch(Rectangle((X(wr - 60), Y(vr - 8)), 75 * s, 16 * s, facecolor=HILITE, edgecolor=INK, lw=0.6,
                               zorder=19))
        arrow2(ax, (X(wr), Y(vr - 10)), (X(wr), Y(v0 + 8)), color=ACCENT, lw=1.6)
        ax.text(X(wr + 22), Y(vr + 4), "the snip's jaws,\nat the release", fontsize=7.6, color=INK, zorder=30,
                va="bottom")
    ax.text(X(-20), Y(f.rail_v - 34), "frame", fontsize=8, color=DIM, ha="center", zorder=30)
    ax.text(X(wo + 8), Y(f.lid_under(wo) + 14), "lid, clear 4.5,\nflush", fontsize=8, color=INK, zorder=30)
    ax.text(X(wo + 8), Y(f.vj + 2), "hood on\nbasin", fontsize=8, color=DIM, zorder=30, va="center")
    ax.text(X(wb + 40), Y(f.vf - 22), "skirt", fontsize=8, color=INK, zorder=30, ha="center", va="center")
    ax.text(X(-6), Y((a0 + a1) / 2), "opening", fontsize=8, color=WARN, zorder=30, rotation=90, va="center",
            ha="right")
    ax.text(X((w0 + w1) / 2), Y(v0 + 20), "tray", fontsize=8, color=INK, ha="center", zorder=30)
    ax.text(X(-44), Y(f.rail_v), "M5 × 20\ninto the rail", fontsize=7.6, color=INK, ha="right", va="center", zorder=30)
    ax.text(X(-44), Y(f.v_top_bolt), "M4 × 20,\nwell nut", fontsize=7.6, color=INK, ha="right", va="center", zorder=30)


def sec_tray(ax, ox, oy, s):
    """True-scale section across the dead-leaf tray at mid depth, in (x, z):
    the pan, both rails, the tray hanging by its rims."""
    X = lambda x: ox + x * s                                     # noqa: E731
    Y = lambda z: oy + z * s                                     # noqa: E731
    t, r = Hv.TRAY, Hv.RAIL
    _rect(ax, X(100), Y(0), 600 * s, 40 * s, "#dfe5e9", z=10)                      # the mid rail, for scale
    _rect(ax, X(100), Y(C.SER), 600 * s, C.T_SHEET * s, SHEET * 0.85, z=12)        # pan floor
    for side, sg in (("L", -1), ("R", 1)):
        xw = r["web"][0] if side == "L" else r["web"][1]
        xb = xw + sg * r["bottom"]
        xt = xw + sg * r["top"]
        _rect(ax, X(min(xw, xb)), Y(Hv.PAN_TOP), abs(xb - xw) * s, Hv.T * s, "#cfd6db", z=14)
        _rect(ax, X(xw if sg > 0 else xw - Hv.T), Y(Hv.PAN_TOP), Hv.T * s, (r["run"] - Hv.PAN_TOP) * s, "#cfd6db", z=14)
        _rect(ax, X(min(xw, xt)), Y(r["run"] - Hv.T), abs(xt - xw) * s, Hv.T * s, "#cfd6db", z=14)
    x0, x1, z0 = t["x0"], t["x1"], t["z0"]
    zt = z0 + t["h"]
    _rect(ax, X(x0), Y(z0), (x1 - x0) * s, Hv.T * s, "#e3e8eb", z=15)
    _rect(ax, X(x0), Y(z0), Hv.T * s, t["h"] * s, "#e3e8eb", z=15)
    _rect(ax, X(x1 - Hv.T), Y(z0), Hv.T * s, t["h"] * s, "#e3e8eb", z=15)
    _rect(ax, X(x0 - t["rim"]), Y(zt - Hv.T), t["rim"] * s, Hv.T * s, "#e3e8eb", z=15)
    _rect(ax, X(x1), Y(zt - Hv.T), t["rim"] * s, Hv.T * s, "#e3e8eb", z=15)
    for x in Hv.BOLT_X:
        _rect(ax, X(x - 7), Y(Hv.PAN_TOP + Hv.T + 1.6), 14 * s, 4.4 * s, "#9aa3a9", z=16)
        _rect(ax, X(x - 4), Y(C.SER - 11.2 + 4.8), 8 * s, 11.2 * s, "#b7bec3", z=11)
    ax.text(X(400), Y(z0 + 22), "tray, hung by its two rims", fontsize=8, color=INK, ha="center", zorder=30)
    ax.text(X(r["web"][1] + 30), Y(r["run"] + 18), "rail R", fontsize=8, color=INK, zorder=30)
    ax.text(X(r["web"][0] - 30), Y(r["run"] + 18), "rail L", fontsize=8, color=INK, ha="right", zorder=30)
    ax.text(X(400), Y(12), "base pan, on its rails", fontsize=8, color=DIM, ha="center", zorder=30)


def sec_handle(ax, ox, oy, s):
    """True-scale side section through the handle and the front of the tray, in (y, z)."""
    X = lambda y: ox + y * s                                     # noqa: E731
    Y = lambda z: oy + z * s                                     # noqa: E731
    t, h = Hv.TRAY, Hv.HANDLE
    _rect(ax, X(0), Y(0), 40 * s, 40 * s, "#dfe5e9", z=10)                       # F0
    _rect(ax, X(0), Y(C.LEVELS[1]), 40 * s, 40 * s, "#dfe5e9", z=10)            # F1
    _rect(ax, X(0), Y(C.SER), 120 * s, C.T_SHEET * s, SHEET * 0.85, z=12)
    _rect(ax, X(0), Y(C.SER), C.T_SHEET * s, C.LIP * s, SHEET * 0.85, z=12)      # the pan's front lip
    _rect(ax, X(-E.GAP_F - E.DOOR_T), Y(-5), E.DOOR_T * s, 352 * s, "#d8e6ee", z=12)   # the door
    y0 = t["y0"]
    _rect(ax, X(y0), Y(t["z0"]), 110 * s, Hv.T * s, "#e3e8eb", z=15)
    _rect(ax, X(y0), Y(t["z0"]), Hv.T * s, t["h"] * s, "#e3e8eb", z=15)
    _rect(ax, X(y0 - h["plate"]), Y(h["z0"]), h["plate"] * s, (h["slot"][2] - 12 - h["z0"]) * s, PRINT, z=16)
    _rect(ax, X(y0 - h["frame_t"]), Y(h["slot"][2] - 12), h["frame_t"] * s, 12 * s, PRINT, z=16)
    ax.add_patch(FancyBboxPatch((X(h["bar"][0]), Y(h["bar"][1])), (y0 - h["bar"][0]) * s,
                                (h["z1"] - h["bar"][1]) * s, boxstyle=f"round,pad=0,rounding_size={9 * s}",
                                facecolor=PRINT, edgecolor=INK, lw=0.7, zorder=16))
    ax.text(X(y0 + 60), Y(t["z0"] + 20), "tray", fontsize=8, color=INK, ha="center", zorder=30)
    ax.text(X(y0 + 10), Y(h["bar"][1] - 30), "the hand goes\nthrough here", fontsize=8, color=ACCENT, zorder=30)
    ax.text(X(-14), Y(200), "door", fontsize=8, color=DIM, ha="right", zorder=30, rotation=90, va="center")
    ax.text(X(48), Y(C.LEVELS[1] + 20), "F1", fontsize=8, color=DIM, va="center", zorder=30)
    ax.text(X(48), Y(20), "F0", fontsize=8, color=DIM, va="center", zorder=30)
    ax.text(X(-E.GAP_F - E.DOOR_T - 8), Y(h["z1"]), f"{h['z1']:.0f}", fontsize=7.4, color=DIM, ha="right", zorder=30)


@page
def p_sections(pdf):
    fig, ax = new_page(None, "In section, to scale",
                       "Through the leaves compartment, across the dead-leaf tray, and through its handle.")
    panel(ax, 40, 300, 520, 470, z=5)
    sec_feeder(ax, 250, 393.0, 1.15)
    ax.text(56, 750, "the feeder at the leaves drop, from the front", fontsize=8.6, color=DIM, zorder=330)
    panel(ax, 570, 560, 540, 210, z=5)
    sec_tray(ax, 600, 610, 0.6)
    ax.text(586, 750, "across the tray, from the front", fontsize=8.6, color=DIM, zorder=330)
    panel(ax, 570, 300, 540, 240, z=5)
    sec_handle(ax, 720, 314, 0.55)
    ax.text(586, 520, "through the handle, from the left", fontsize=8.6, color=DIM, zorder=330)
    ck = Hv.tray_checks()
    fc = Hv.feeder_checks()
    ax._body_y = 60.0
    body(ax, f"The tray's floor rides {ck['floor over the pan' + chr(39) + 's front lip']} over the pan's front lip, "
             f"so it slides straight out; its rims and the rails' stops are {ck['rim, rail tops under the gantry']} "
             f"under the gantry's lowest part. The handle\nstops {ck['handle under rail F1']} under F1 and "
             f"{ck['handle grip behind the door']} behind the door's inside face. At the feeder the opening's sill "
             f"is {fc['opening sill over the rail below']} over tier B's rail and the tray's rim\n"
             f"{fc['tray rim over the sill']} above the sill: nothing dropped can fall back into the cabinet.", fs=9.2)
    save(fig, ax, pdf, "00f_sections")


# ============================================================ 1
@page
def s1(pdf):
    fig, ax = new_page(1, "Before you start",
                       "The cabinet finished to the enclosure booklet, the parts printed and cut. Six checks.")
    rows = [("Enclosure Rev A done", "Step 18 signed off, with the right panel that has the feeder's two openings "
             "and its four green screws on tier B's rail."),
            ("Robot off", "Gantry homed and parked left, the E-stop pressed. Nothing in this booklet needs it powered."),
            ("Metal in", "From SendCutSend: guide rails L and R, the dead-leaf tray (5052, bent), the clear lid. "
             "Check the rails mirror each other."),
            ("Printed", "Handle; the leaves and veggies hoods; two basins, two skirts, two trays: PETG or PLA, 4 walls, "
             "20 %, no supports."),
            ("Fasteners", "Against the fasteners page: four M8 × 16, three M5 × 10 and nylocs, four M5 × 20, four M4 × 20 "
             "and well nuts."),
            ("The switch", "One more 7939WG reed switch and its magnet (as on the doors), two lever connectors, "
             "3 m of 2-core cable, a roll of VHB 4905.")]
    checkbox_rows(ax, rows, y0=690, dy=90)
    body(ax, "Work in this order: the rails and the tray in the base first, then the feeder on the right panel. The "
             "tray needs only the bottom-left door open; the feeder is\nall done from outside, except the switch's "
             "cable, which runs inside the cabinet to the utility node.", fs=10.0)
    save(fig, ax, pdf, "01")


# ============================================================ 2
@page
def s2(pdf):
    fig, ax = new_page(2, "Base pan  ·  the guide rails",
                       "Four of the pan's own bolts come out; the rails go under them; M8 × 16 go back in.")
    lo, hi = (-40.0, -60.0, -30.0), (820.0, 620.0, 360.0)
    cab = list(_cab_box(lo, hi))
    ex = 70.0
    rails = []
    for side in "LR":
        rails.append(Part(mv(Hv.rail_mesh(side), 0, 0, ex), HILITE, lw=0.4, ang=30))
        for kind, m in Hv.rail_bolts(side, explode=ex * 2):
            rails.append(Part(m, HILITE, lw=0.25, ang=30))
    parts = cab + pan_bolts() + rails
    v = scene(ax, parts, (380, 470), (680, 600), MM=view(212, 36), px=1.5,
              focus=FB.fbox((60, 0, 30), (740, 559, 200)), clip=(24, 150, 770, 772))
    for x in Hv.BOLT_X:
        for y in Hv.BOLT_Y:
            axis3(ax, v, (x, y, Hv.PAN_TOP), (x, y, Hv.PAN_TOP + ex * 2 + 20))
    lab(ax, v, (Hv.RAIL["web"][1] + 1, Hv.RAIL["stop"] + 20, Hv.RAIL["tab"] + ex - 5), "stop tab at the back",
        dx=40, dy=50)
    tag(ax, 790, 700, "Guide rail L, channel open to the left", 1, hi=True)
    tag(ax, 790, 652, "Guide rail R, channel open to the right", 1, hi=True)
    tag(ax, 790, 604, "M8 × 16 button head, the old washer", 4, hi=True)
    tool(ax, 790, 548, "5 mm hex")
    note(ax, 790, 508, "x 150 and x 650, front line (y 20)\nand back line (y 539): the pan's\nown T-nuts stay in "
                       "the rails\nunderneath. Keep the M8 × 12s.", fs=9.2, color=INK)
    body(ax, "Take out the four bolts at x 150 and 650 on the pan's front and back lines; keep their washers, the "
             "T-nuts stay put in the frame. Lay each rail on the\npan with its bottom flange over the two holes, the "
             "stop tab at the back, the channel opening away from the middle. Washer, bolt through the rail's flange "
             "and\nthe pan into the old nut; snug both, check the rails are parallel (460 between the webs), then "
             "tighten.")
    save(fig, ax, pdf, "02")


# ============================================================ 3
@page
def s3(pdf):
    fig, ax = new_page(3, "The tray  ·  its handle",
                       "On the bench. Three M5 × 10 from inside the tray, three nylocs pressed into the handle's pockets.")
    tr = Hv.tray_mesh()
    ex = 60.0
    hd = mv(Hv.handle_mesh(), 0, -ex, 0)
    parts = [Part(tr, ALU, lw=0.45, ang=30), Part(hd, HILITE, lw=0.45, ang=30)]
    for kind, m in Hv.handle_bolts():
        if kind == "bolt":
            parts.append(Part(mv(m, 0, 40, 0), HILITE, lw=0.25, ang=30))
        else:
            parts.append(Part(mv(m, 0, -ex - 30, 0), HILITE, lw=0.25, ang=30))
    v = scene(ax, parts, (360, 462), (600, 600), MM=view(204, 26), px=1.6,
              focus=FB.fbox((150, -120, 60), (650, 520, 300)), clip=(24, 150, 760, 772))
    for x, z in Hv.HANDLE["bolts"]:
        axis3(ax, v, (x, Hv.TRAY["y0"] + 60, z), (x, Hv.TRAY["y0"] - ex - 50, z))
    tag(ax, 790, 700, "Handle, printed", 1, hi=True)
    tag(ax, 790, 652, "M5 × 10 button head", 3, hi=True)
    tag(ax, 790, 604, "M5 nyloc", 3, hi=True)
    tool(ax, 790, 548, "3 mm hex")
    note(ax, 790, 508, "Press each nyloc into its hex pocket,\nnylon side out: the pocket holds it\nwhile you turn "
                       "the screw from\ninside the tray.", fs=9.2, color=INK)
    sx0, sx1, sz0, sz1 = Hv.HANDLE["slot"]
    body(ax, f"The handle stands up off the tray's front wall: its slot is {sx1 - sx0:.0f} wide and {sz1 - sz0:.0f} "
             "tall, a whole hand through it, the bar rounded over the top. Its flat\nback goes against the wall's "
             "outside, its foot just clear of the bend. Screws from inside, heads on the tray's inside face; "
             "tighten until the handle\ndoes not rock, not until the plastic whitens.")
    save(fig, ax, pdf, "03")


# ============================================================ 4
@page
def s4(pdf):
    fig, ax = new_page(4, "The tray  ·  slide it in",
                       "Bottom-left door open. Rims on the rails, push it home to the stops.")
    lo, hi = (-40.0, -400.0, -30.0), (900.0, 620.0, 420.0)
    cab = list(_cab_box(lo, hi))
    doors = EB.door_set("bottom", "L", 150.0)
    trayp = parts_of(_tray(260.0), hi=("tray", "handle"))
    parts = cab + pan_bolts() + parts_of(_rails()) + trayp + doors
    v = scene(ax, parts, (380, 470), (680, 600), MM=view(158, 26), px=1.5,
              focus=FB.fbox((60, -300, 0), (760, 559, 320)), clip=(24, 150, 770, 772))
    q0 = v((400.0, -120.0, 200.0))
    q1 = v((400.0, 120.0, 200.0))
    arrow2(ax, tuple(q0), tuple(q1), color=ACCENT)
    tag(ax, 790, 700, "Dead-leaf tray with its handle", 1, hi=True)
    note(ax, 790, 640, f"Floor {Hv.tray_checks()[chr(102) + 'loor over the pan' + chr(39) + 's front lip']} over the "
                       "pan's front lip,\nrims on the rails' top flanges,\n1.5 of play each side.\nOnly the left door "
                       "need be open:\nthe tray clears the astragal by\n"
                       f"{Hv.tray_checks()['tray past the astragal, left door only']}.", fs=9.2, color=INK)
    panel(ax, 790, 220, 330, 200, z=5)
    sec_tray(ax, 760, 262, 0.5)
    ax.text(802, 402, "across, from the front", fontsize=8.6, color=DIM, zorder=330)
    body(ax, "Hold the tray by its handle, tip the back up a little, and set both rims on the rails' top flanges at "
             "the front. Push it back until its back wall touches the\nstop tabs. To empty it, pull it straight out "
             "by the handle; past half way the rails no longer balance it, so take its weight and lift it clear. The "
             "leak\nsensor stays where it was, on the pan left of the left rail.")
    save(fig, ax, pdf, "04")


# ============================================================ 5
CAB_LO, CAB_HI = (1250.0, 100.0, 800.0), (1450.0, 560.0, 1330.0)
FOCUS = FB.fbox((1397, 150, 840), (1560, 500, 1240))


def _right_bay():
    return list(_cab_box(CAB_LO, CAB_HI)) + [Part(E.panel_mesh("right"), FROST, lw=0.45, ang=30, ghost=True)]


def _fast(d, k=None, kinds=("m5", "m4", "washer", "wellnut"), ex=0.0):
    """The feeder's fasteners of these kinds, module k only (None: both)."""
    out = []
    for name, m in d.items():
        if not name.startswith(kinds):
            continue
        c = m[0].mean(0)
        if k is not None and not (F.mods[k][0] <= c[1] <= F.mods[k][1]):
            continue
        out.append((name, m))
    return out


@page
def s5(pdf):
    fig, ax = new_page(5, "The feeder  ·  on the bench",
                       "The switch inside the veggies hood, its magnet under the lid, the hinge's lid leaf on VHB.")
    f = F
    d = _feeder(trays=False, fasteners=False)
    sh = lambda m: mv(m, -C.W + 40.0, 0, 0)                       # noqa: E731
    parts = []
    for k in ("hood_leaves", "hood_veggies"):
        parts.append(Part(sh(d[k]), PRINT, lw=0.45, ang=30))
    parts.append(Part(sh(d["reed_switch"]), HILITE, lw=0.4, ang=30))
    lift, out = 230.0, 150.0
    for k in ("lid", "hinge_lid", "reed_magnet"):
        parts.append(Part(mv(sh(d[k]), out, 0, lift), HILITE if k != "lid" else CLEARC, lw=0.4, ang=30,
                          ghost=(k == "lid")))
    parts.append(Part(sh(d["hinge_fixed"]), STEEL, lw=0.4, ang=30))
    v = scene(ax, parts, (360, 462), (600, 600), MM=view(122, 34), px=1.6, clip=(24, 150, 760, 772))
    sw = f._sw_box()
    lab(ax, v, (40 + sw[3], (sw[1] + sw[4]) / 2, sw[5]), "reed switch, inside the\nveggies hood's back plate",
        dx=-90, dy=90, ha="right")
    lab(ax, v, (40 + f.wb + f.BACK, f.wire_hole[0], f.wire_hole[1]), "its cable out here", dx=90, dy=-70)
    tag(ax, 790, 700, "Reed switch 7939WG, its own adhesive", 1, hi=True)
    tag(ax, 790, 652, "Its magnet, under the lid", 1, hi=True)
    tag(ax, 790, 604, "Piano hinge 1 ft: lid leaf on VHB", 1, hi=True)
    tool(ax, 790, 548, "isopropyl  ·  utility knife  ·  tape")
    gap = Hv.feeder_checks()["reed gap, lid down (7939WG wide gap)"]
    al, fb = f.magnet_place()
    top_dn = f.vt - sw[5]
    end_in = sw[1] - f.mods[1][0]
    note(ax, 790, 508, f"Switch: long side level, its top {top_dn:.0f}\nunder the back plate's top edge,\nits end {end_in:.0f} "
                       f"from the hood's leaves\nside. Magnet: {al:.0f} from the lid's hinge\nedge to its near edge, "
                       f"its centre\n{fb:.0f} from the lid's leaves end.\nLid down they are {gap:.0f} apart.", fs=9.0,
         color=INK)
    body(ax, "Stand the two hoods side by side, leaves toward the cabinet's front. Inside the veggies hood, clean the "
             "back plate between the two upper M4 holes and stick\nthe switch there as the note says, its cable end "
             "at the 8 hole; push the cable out through it. On the lid: clean it, the magnet on the underside where "
             "the note\nsays, parallel to the switch; then one VHB strip on the hinge's lid leaf, the knuckle along "
             "the lid's hinge edge, on its top face. Press each for 30 s.")
    save(fig, ax, pdf, "05")


# ============================================================ 6
@page
def s6(pdf):
    fig, ax = new_page(6, "Right panel  ·  well nuts in, temporary screws out",
                       "Four well nuts into the 10 holes over the openings; the four green M5 × 16 come out.")
    f = F
    ex = 60.0
    parts = _right_bay() + [Part(E.tape_mesh("right"), EPDM, lw=0.25, ang=30)]
    for i, (kind, (w, u, v_), M, L) in enumerate(f.screws()):
        if kind == "m4":
            parts.append(Part(f.to_world(mv(rot(Hv.well_nut_mesh(), ry=math.pi / 2), E.OUT + ex, u, v_)), HILITE,
                              lw=0.3, ang=30))
        else:
            parts.append(Part(f.to_world(mv(rot(E.button5(16), ry=math.pi / 2), E.OUT + E.WASH["t"] + ex * 1.6, u, v_)),
                              STEEL, lw=0.25, ang=30))
            parts.append(Part(f.to_world(mv(rot(E.washer9021(), ry=math.pi / 2), E.OUT + ex * 1.3, u, v_)), STEEL,
                              lw=0.25, ang=30))
    v = scene(ax, parts, (360, 462), (600, 600), MM=view(112, 14), px=1.5,
              focus=FB.fbox((1397, 150, 900), (1480, 500, 1260)), clip=(24, 150, 760, 772))
    for kind, (w, u, v_), M, L in f.screws():
        axis3(ax, v, (C.W, u, v_), (C.W + E.OUT + ex * 2, u, v_))
    tag(ax, 790, 700, "M4 rubber well nut, into a 10 hole", 4, hi=True)
    tag(ax, 790, 652, "M5 × 16 + washer: out, keep the washers", 4)
    tool(ax, 790, 596, "3 mm hex")
    note(ax, 790, 556, "Take the M5s out one at a time.\nTheir T-nuts stay in the slot behind\nthe panel: the panel "
                       "covers the slot,\nso a nut can turn loose but not\nfall out. The M5 × 20s find them.", fs=9.2,
         color=INK)
    body(ax, "Push each well nut into its hole from outside until its flange sits on the panel. Then the four M5 "
             "screws on tier B's rail line, under the openings:\nunscrew and keep their DIN 9021 washers for the "
             "feeder. The panel stays put: every other screw still holds it, and its tape is stuck.")
    save(fig, ax, pdf, "06")


# ============================================================ 7
@page
def s7(pdf):
    fig, ax = new_page(7, "Feeder  ·  hang the two basins",
                       "Each basin's back plate on the panel, two M5 × 20 and washers into tier B's rail.")
    f = F
    d = _feeder(trays=False, lid=False)
    ex = 80.0
    parts = _right_bay()
    for nm in f.NAMES:
        parts.append(Part(mv(d[f"basin_{nm}"], ex, 0, 0), HILITE, lw=0.45, ang=30))
    for name, m in _fast(d, kinds=("m5", "washer")):
        parts.append(Part(mv(m, ex * 2.0, 0, 0), HILITE, lw=0.25, ang=30))
    for name, m in _fast(d, kinds=("wellnut",)):
        parts.append(Part(m, BLACKPART, lw=0.25, ang=30))
    v = scene(ax, parts, (360, 462), (600, 600), MM=view(124, 16), px=1.5, focus=FOCUS, clip=(24, 150, 760, 772))
    for kind, (w, u, v_), M, L in f.screws():
        if kind == "m5":
            axis3(ax, v, (C.W, u, v_), (C.W + f.wb + f.BACK + ex * 2.2, u, v_))
    tag(ax, 790, 700, "Basin, printed", 2, hi=True)
    tag(ax, 790, 652, "M5 × 20 + DIN 9021 washer", 4, hi=True)
    tool(ax, 790, 596, "3 mm hex")
    note(ax, 790, 556, "The four holes place them: leaves\nbasin in front, veggies behind,\ntheir side walls "
                       "touching.", fs=9.2, color=INK)
    body(ax, "A helper holds the first basin against the panel, its back plate's two holes over the panel's. Start "
             "both M5 × 20s through their washers into the T-nuts behind\n(turn until each nut swings across and "
             "grips). The second basin the same, its wall against the first's: the two walls make the 6 divider. Snug "
             "all four,\ncheck the two floors are level with each other, then tighten firmly.")
    save(fig, ax, pdf, "07")


# ============================================================ 8
@page
def s8(pdf):
    fig, ax = new_page(8, "Feeder  ·  the two hoods",
                       "Each hood down onto its basin's lip, two M4 × 20 into the well nuts over the openings.")
    f = F
    d = _feeder(trays=False, lid=False)
    up = 90.0
    parts = _right_bay()
    for nm in f.NAMES:
        parts.append(Part(d[f"basin_{nm}"], PRINT, lw=0.45, ang=30))
        parts.append(Part(mv(d[f"hood_{nm}"], 0, 0, up), HILITE, lw=0.45, ang=30))
    parts.append(Part(mv(f.to_world(f.reed_switch()[0]), 0, 0, up), WHITEP, lw=0.35, ang=30))
    for name, m in _fast(d, kinds=("m5", "washer")):
        parts.append(Part(m, STEEL, lw=0.25, ang=30))
    for name, m in _fast(d, kinds=("m4",)):
        parts.append(Part(mv(m, 70.0, 0, up), HILITE, lw=0.25, ang=30))
    for name, m in _fast(d, kinds=("wellnut",)):
        parts.append(Part(m, BLACKPART, lw=0.25, ang=30))
    v = scene(ax, parts, (360, 462), (600, 600), MM=view(124, 16), px=1.5,
              focus=FB.fbox((1397, 150, 900), (1580, 500, 1330)), clip=(24, 150, 760, 772))
    for k in (0, 1):
        c = (C.W + f.w_out - 20, (f.mods[k][0] + f.mods[k][1]) / 2)
        axis3(ax, v, (c[0], c[1], f.vj + 4), (c[0], c[1], f.vj + up))
    tag(ax, 790, 700, "Hood, leaves", 1, hi=True)
    tag(ax, 790, 652, "Hood, veggies, the switch inside", 1, hi=True)
    tag(ax, 790, 604, "M4 × 20 button head", 4, hi=True)
    tool(ax, 790, 548, "2.5 mm hex")
    note(ax, 790, 508, "Veggies first: feed the switch's\ncable through the panel's 8 hole\nas the hood comes down, "
                       "and pull\nthe slack into the cabinet.", fs=9.2, color=INK)
    body(ax, "Lower each hood straight down onto its basin: the basin's walls stand 4 above the joint on their outer "
             "half and the hood's walls drop inside that lip. Its\nback plate's two holes come over the well nuts; turn "
             "the two M4 × 20s in from inside the hood until the rubber bulges behind the panel. The hinge needs both\n"
             "hoods' top edges level: check them with a straightedge before you tighten.")
    save(fig, ax, pdf, "08")


# ============================================================ 9
@page
def s9(pdf):
    fig, ax = new_page(9, "Feeder  ·  the skirts",
                       "A strip of VHB on each skirt's top, pressed up under its basin's floor, its back on the panel.")
    f = F
    d = _feeder(trays=False, lid=False)
    dn = 80.0
    parts = _right_bay()
    for nm in f.NAMES:
        parts.append(Part(d[f"basin_{nm}"], PRINT, lw=0.45, ang=30))
        parts.append(Part(d[f"hood_{nm}"], PRINT, lw=0.45, ang=30))
        parts.append(Part(mv(d[f"skirt_{nm}"], 0, 0, -dn), HILITE, lw=0.45, ang=30))
    for name, m in _fast(d):
        parts.append(Part(m, BLACKPART if name.startswith("wellnut") else STEEL, lw=0.25, ang=30))
    v = scene(ax, parts, (360, 462), (600, 600), MM=view(128, -14), px=1.5,
              focus=FB.fbox((1397, 150, 760), (1560, 500, 1240)), clip=(24, 150, 760, 772))
    for k in (0, 1):
        c = (C.W + f.wb + 50, (f.mods[k][0] + f.mods[k][1]) / 2)
        axis3(ax, v, (c[0], c[1], f.vf - dn), (c[0], c[1], f.vf))
    tag(ax, 790, 700, "Skirt, printed", 2, hi=True)
    tag(ax, 790, 652, "VHB 4905, two strips on each", 4, hi=True)
    tool(ax, 790, 596, "isopropyl  ·  utility knife")
    note(ax, 790, 556, "Only for looks: it carries nothing.\nIts slope runs from the outer wall\nback down to the "
                       "panel and hides\nthe floor's underside.", fs=9.2, color=INK)
    body(ax, "Clean each skirt's top face and its basin's floor underneath. Two strips of VHB along the skirt's top, "
             "one near each end. Hold it with its open back on the\npanel and its ends in line with the basin's walls, "
             "push it up under the floor and press it there for 30 s. The two skirts meet under the divider.")
    save(fig, ax, pdf, "09")


# ============================================================ 10
@page
def s10(pdf):
    fig, ax = new_page(10, "Feeder  ·  the lid",
                       "The hinge's fixed leaf on VHB inside both back plates' top band. The lid comes down flush.")
    f = F
    d = _feeder(open_deg=60.0, trays=False)
    parts = _right_bay() + parts_of(d, hi=("lid", "hinge"), skip=("m5", "m4", "washer", "wellnut"))
    v = scene(ax, parts, (360, 462), (600, 600), MM=view(128, 18), px=1.5,
              focus=FB.fbox((1397, 150, 840), (1600, 500, 1400)), clip=(24, 150, 760, 772))
    lab(ax, v, (C.W + f.wb + f.BACK, (f.mods[0][0] + f.mods[1][1]) / 2, f.vt - 8), "fixed leaf inside the back\n"
        "plates' top band, VHB", dx=-60, dy=70, ha="right")
    lab(ax, v, (C.W + f.w_out, f.mods[0][1], f.lid_under(f.w_out) - 8), "finger scoop", dx=70, dy=-50)
    tag(ax, 790, 700, "Lid, with its leaf and magnet", 1, hi=True)
    tag(ax, 790, 652, "VHB 4905 strip, the fixed leaf", 1, hi=True)
    tool(ax, 790, 596, "isopropyl  ·  utility knife")
    L, Wd = f.lid_flat()
    note(ax, 790, 556, f"Lid {Wd:.1f} × {L:.1f}, falling {F.LID_ANGLE:.0f}° away\nfrom the panel; its lower edge "
                       "is\nflush with the walls' outer faces.\nLifted, it turns past upright and\nleans on the panel "
                       "by itself.", fs=9.2, color=INK)
    body(ax, "Clean the inner face of both back plates' top band, where the side walls are slotted for the leaf. Hold "
             "the lid down on the walls, its lower edge in the outer\nwall's ridge, and mark where the fixed leaf "
             "lands; lift it, put VHB on the fixed leaf, lower the lid and press the leaf onto both back plates along "
             "its length.\nLeave it shut for an hour before you lift it: VHB takes most of its strength in that time "
             "and all of it in a day.")
    save(fig, ax, pdf, "10")


# ============================================================ 11
def _chain(ax, x0, y0):
    """The door chain with the lid switch in it."""
    items = ["door, bottom left", "door, bottom right", "door, top left", "door, top right", "feeder lid"]
    w, h, gap = 112, 40, 26
    for i, t in enumerate(items):
        x = x0 + i * (w + gap)
        hi_ = i == 4
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0,rounding_size=6",
                                    facecolor=B.NEW_FILL if hi_ else "white", edgecolor=B.NEW_EDGE if hi_ else RULE,
                                    lw=1.0, zorder=20))
        ax.text(x + w / 2, y0 + h / 2, t, fontsize=8.0, ha="center", va="center", color=INK, zorder=21)
        if i:
            ax.plot([x - gap, x], [y0 + h / 2] * 2, color=INK, lw=1.2, zorder=19)
    xe = x0 + 5 * (w + gap) - gap
    ax.plot([x0 - 30, x0], [y0 + h / 2] * 2, color=INK, lw=1.2, zorder=19)
    ax.plot([xe, xe + 30], [y0 + h / 2] * 2, color=INK, lw=1.2, zorder=19)
    ax.text(x0 - 36, y0 + h / 2, "from the\nsafety relay", fontsize=7.8, color=DIM, ha="right", va="center")
    ax.text(xe + 36, y0 + h / 2, "E-stop, relay,\nMCP23017 A4", fontsize=7.8, color=DIM, ha="left", va="center")


@page
def s11(pdf):
    fig, ax = new_page(11, "Trays in, the switch into the door chain",
                       "The lid joins the four door switches in series: lift it and the arm loses power.")
    f = F
    d = _feeder(open_deg=F.lid_rest_deg())
    lift = 180.0
    parts = _right_bay()
    for k, m in d.items():
        if k.startswith("tray_"):
            parts.append(Part(mv(m, 0, 0, lift), HILITE, lw=0.4, ang=30))
        elif not k.startswith(("m5", "m4", "washer", "wellnut")):
            parts.append(Part(m, col_of(k), lw=0.4, ang=30, ghost=(k == "lid")))
    v = scene(ax, parts, (330, 520), (540, 480), MM=view(128, 26), px=1.5,
              focus=FB.fbox((1397, 150, 860), (1600, 500, 1460)), clip=(24, 300, 700, 772))
    for k in (0, 1):
        w0, w1, u0, u1, v0, v1 = f.tray_box(k)
        c = (C.W + (w0 + w1) / 2, (u0 + u1) / 2, v1)
        axis3(ax, v, c, (c[0], c[1], c[2] + lift))
    tag(ax, 760, 700, "Feeder tray, leaves and veggies", 2, hi=True)
    tag(ax, 760, 652, "Lever connector, Wago 221-412", 2, hi=True)
    tool(ax, 760, 596, "side cutters  ·  wire stripper")
    note(ax, 760, 556, f"Each tray's grip slot faces you.\nThe trays are the same part; mark\none L and one V. Lift "
                       f"them straight\nup {f.lid_under(f.w_out) - f.tray_box(0)[4]:.0f}, clear of the outer wall,\nthen out.",
         fs=9.2, color=INK)
    _chain(ax, 150, 220)
    ax.text(60, 286, "The door chain, after this step", fontsize=9.4, fontweight="bold", color=INK)
    body(ax, "Inside the cabinet, run the switch's cable from the panel's 8 hole down the back right post to the "
             "utility node, clipped every 300. At the door chain,\nopen the loop at one end and put the lid switch in "
             "it with the two lever connectors: five switches in series. The Doors sensor in Home Assistant now\n"
             "reads open when any door or the lid is open, and the safety relay cuts the gantry and the arm.")
    save(fig, ax, pdf, "11")


# ============================================================ 12
@page
def s12(pdf):
    fig, ax = new_page(12, "Before the first harvest",
                       "The checks that catch the usual faults, with nothing in the trays yet.")
    rows = [("Tray", "Slides out with the left door alone and back to the stops; nothing scrapes; the leak sensor "
             "still reads dry."),
            ("Lid", "Lifts by the scoop, turns past upright, leans on the panel; drops shut flush, its edge in the ridge."),
            ("Switch", "Lid open: Doors reads open, the relay drops, the arm will not move. Lid shut: it resets."),
            ("Air", "Fans on: a tissue at the lid's gap barely moves. The feeder is part of the cabinet's air."),
            ("Drops", "Commissioning: jog to each pose in drops.yaml at 20 % speed, lid shut. The jaws pass the "
             "openings' middles."),
            ("Software", "The Herb Snip sends leaves and veggies to the feeder, dead leaves to the tray, five drop "
             "points in turn.")]
    checkbox_rows(ax, rows, y0=690, dy=90)
    body(ax, "Empty the feeder's trays as often as you harvest; wash them like any food container (no dishwasher for "
             "PLA). The dead-leaf tray holds about 10 L:\nempty it into the compost when the leaves reach its rims. "
             "Never reach into the feeder from inside the cabinet with the robot powered.", fs=10.0)
    save(fig, ax, pdf, "12")


PAGES.insert(0, p_cover)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:]
    if only:
        class _N:
            def savefig(self, *a, **k):
                pass
        for fn in PAGES:
            if fn.__name__ in only:
                fn(_N()); print(fn.__name__, "ok", flush=True)
        sys.exit(0)
    path = f"{OUT}/Maag_Harvest_Assembly_Instructions_RevB.pdf"
    # HARVEST_SKIP=p_how builds every other page (into a part file); HARVEST_PAGES=p_how just those
    skip = [x for x in os.environ.get("HARVEST_SKIP", "").split(",") if x]
    want = [x for x in os.environ.get("HARVEST_PAGES", "").split(",") if x]
    pages = [fn for fn in PAGES if fn.__name__ not in skip and (not want or fn.__name__ in want)]
    if skip or want:
        path = f"{OUT}/part_{'_'.join(want) if want else 'skip_' + '_'.join(skip)}.pdf"
    with PdfPages(path) as pdf:
        for fn in pages:
            fn(pdf); print(fn.__name__, "ok", flush=True)
    print("saved", path, f"({len(pages)} pages)")
