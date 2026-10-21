"""Herb Snip Rev A: the assembly booklet, drawn from the model.

    python make_snip_booklet.py            # whole booklet into ./build/booklet
    python make_snip_booklet.py s3 w1      # just those pages (PNG only)

Every drawing comes from snip_cad.py (the printed parts), snip_cots.py (the
purchased parts, from their makers' data: Intel's D405 mesh, Elephant's flange
and wrist, TowerPro's MG90S envelope) and assembly.py, which poses them at a jaw
opening. The cabinet and the arm come from greenhouse/gantry (frame.py,
arm280.py), the same model the gantry and frame booklets draw.
"""
from __future__ import annotations
import json, math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "..", "booklet"), os.path.join(HERE, "..", "gantry")):
    sys.path.insert(0, p)
os.environ.setdefault("D405_STL", os.path.join(HERE, "..", "..", "..", "..", "realsense_mesh", "d405.stl"))

import maagbook as MB                                                   # noqa: E402
import checks as CK                                                     # noqa: E402
from maagbook import (new_page, scene, inset, panel, save, arrow2, axis3, tag, body, tool, note,   # noqa: E402
                      leader, checkbox_rows, TITLE_FONT, INK, DIM, ACCENT, WARN, OK, EDGE, RULE, CHIP, PANEL)
from matplotlib.backends.backend_pdf import PdfPages                    # noqa: E402
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle        # noqa: E402
import matplotlib.pyplot as plt                                         # noqa: E402
import matplotlib.patheffects as pe                                     # noqa: E402
import kit3d as K                                                       # noqa: E402
from kit3d import Part, iso_matrix                                     # noqa: E402
import snip_cad as C                                                    # noqa: E402
import snip_cots as Q                                                   # noqa: E402
import assembly as AS                                                   # noqa: E402

REV = "Rev A"
DESIGN = "0.7.0"
OUT = os.environ.get("SNIP_OUT", os.path.join(HERE, "build", "booklet"))
MB.configure(f"Herb Snip {REV}", OUT)
PAGES = []
CHECKS = json.load(open(os.path.join(AS.BUILD, "checks.json")))
ARMC = json.load(open(os.path.join(AS.BUILD, "arm_checks.json")))

GREEN = np.array([0.36, 0.62, 0.30])
STEM = np.array([0.50, 0.70, 0.36])
M = iso_matrix(34, 24)


def page(fn):
    PAGES.append(fn)
    return fn


# ------------------------------------------------------------------ parts
def tparts(phi=0.0, names=None, hi=(), offs=None, wrist=False, skip=(), ghost=(), extra=()):
    out = []
    for n, m, c in AS.parts(phi, cots=True, wrist=wrist):
        if (names is not None and n not in names) or n in skip:
            continue
        if offs and n in offs:
            m = K.mv(m, *offs[n])
        out.append(Part(m, K.HILITE if n in hi else c, ang=30, ghost=n in ghost))
    out += list(extra)
    return out


def ycyl(r, y0, y1, x, z, n=28):
    """A cylinder along +y from y0 to y1, axis at (x, z)."""
    V, F = K.cylinder(r, y1 - y0, n=n)
    V = np.c_[V[:, 0], V[:, 2], -V[:, 1]]                  # (x, y, z) -> (x, z, -y): a rotation
    return (V + np.array([x, y0, z]), F)


def leaf(y0, z0, L=34.0, W=20.0, x=2.6, t=0.7):
    """A basil leaf hanging off the petiole's end, in the y-z plane."""
    a = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    u = (np.cos(a) + 1) / 2 * L                            # along y, from the petiole
    v = np.sin(a) * W / 2 * (1 - 0.35 * np.cos(a))         # a little fuller near the tip
    V, F = K.extrude(np.c_[u, v], t)
    V = np.c_[V[:, 2] + x - t / 2, V[:, 0] + y0, V[:, 1] + z0]   # (u, v, w) -> (w, u, v): cyclic, a rotation
    return (V, F)


def stem_and_leaf(cut=False, x=2.4, z=84.0, d=4.5):
    """Petiole across the jaws along y, leaf on the servo side (+y)."""
    r = d / 2
    if cut:
        parts = [Part(ycyl(r, -22.0, -0.9, x - 5.0, z - 2.0), STEM), Part(ycyl(r, 0.4, 12.0, x, z), STEM)]
    else:
        parts = [Part(ycyl(r, -22.0, 12.0, x, z), STEM)]
    parts.append(Part(leaf(11.5, z, L=24.0, W=14.0), GREEN, ang=40))
    return parts


def stl(path):
    d = open(path, "rb").read(); n = struct.unpack("<I", d[80:84])[0]
    a = np.frombuffer(d[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    V = a["v"].reshape(-1, 3).astype(float)
    return K.weld((V, np.arange(len(V)).reshape(-1, 3)), tol=1e-4)


def jaw_view(az=12, el=10):
    return iso_matrix(az, el)


def focus_box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])


# ------------------------------------------------------------------ the arm, placed
def on_flange(mesh, q, x, z):
    """A tool-frame mesh carried by the arm at joint angles q, carriage at x, J1 at z."""
    import ik
    import frame as Fr
    V, F = mesh
    T = ik.flange_T(q)
    W = (V + np.array([0, 0, ik.FLANGE_FACE])) @ T[:3, :3].T + T[:3, 3]
    B = Fr.arm_base_frame(x, z)
    return (W @ B[:3, :3].T + B[:3, 3], F)


# ================================================================== pages
@page
def p_how(pdf):
    fig, ax = new_page(None, "How the Herb Snip works",
                       "One servo closes one jaw. The pads take hold of the leaf's side of the stem, then the blade cuts.")
    states = [(55.0, False, "1  Open", "the stem goes between the jaws,\nthe leaf on the servo side", ()),
              (13.0, False, "2  The pads close first", "they hold the leaf's side of the\nstem before the blade reaches it",
               ("pad_fj", "pad_mj")),
              (0.0, True, "3  Cut, and still held", "the blade meets the anvil; the\nleaf stays in the pads",
               ("blade", "anvil"))]
    names = ["body", "anvil", "mj_a", "mj_b", "link", "blade", "pad_fj", "pad_mj", "pivot", "insert_clamp",
             "dowel_tail", "clamp"]
    MMj = iso_matrix(60, 40)
    for i, (phi, cut, head, sub, hi) in enumerate(states):
        x0 = 40 + i * 362
        ps = tparts(phi, names=names, hi=hi) + stem_and_leaf(cut=cut)
        foc = focus_box((-14, -22, 60), (26, 30, 110))
        v = inset(ax, x0, 235, 346, 520, ps, MMj, focus=foc, label=None, px=3.2)
        ax.text(x0 + 16, 728, head, fontsize=11.5, fontweight="semibold", family=TITLE_FONT, color=INK, va="center",
                zorder=331)
        note(ax, x0 + 16, 712, sub)
        R, t = C.jaw3(math.radians(phi))
        pts = {"blade": R @ np.array([1.0, -0.2, 92.0]) + t, "anvil": np.array([-1.2, 0.0, 99.0]),
               "pads": np.array([-2.0, 6.0, 102.0]), "stem": np.array([2.4, -14.0, 84.0]),
               "moving jaw": R @ np.array([10.0, 0.0, 92.0]) + t, "fixed jaw": np.array([-8.0, 0.0, 80.0])}
        keys = {0: ["pads", "blade", "stem", "moving jaw"], 1: ["pads"], 2: ["blade", "anvil"]}[i]
        off = {"pads": (-95, 55), "blade": (-70, 70) if i == 0 else (85, 70), "anvil": (-95, 30),
               "stem": (-70, -55), "moving jaw": (40, -110)}
        for key in keys:
            p = v(pts[key])
            lx = min(max(p[0] + off[key][0], x0 + 14), x0 + 332)
            ly = p[1] + off[key][1]
            leader(ax, (lx, ly), (p[0], p[1]))
            ax.add_patch(Circle((p[0], p[1]), 2.2, facecolor=DIM, edgecolor="none", zorder=331))
            ax.text(lx, ly, key, fontsize=8.6, color=DIM, ha="right" if off[key][0] < 0 else "left", va="center",
                    zorder=332, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    f20 = CHECKS["force"]["r20"]["F_min_cut"]
    body(ax, f"The servo turns a crank, the crank pulls a link, the link closes the moving jaw: {f20:.0f} N at the middle of "
             "the blade through a 4.5 mm\nstem, with the servo held to 70 % of its stall torque. The pads are the TPU "
             "combs beside the blade, on the servo side. Present the\nplant so the part you want is on that side: it is the "
             "part the tool keeps. The other side is the plant, and stays behind.")
    save(fig, ax, pdf, "00_how")


@page
def p_printed(pdf):
    mass = CHECKS["mass"]["printed"]
    tool_g = sum(mass[k]["g"] * (2 if k == "pad" else 1)
                 for k in ("body", "ring", "mj_a", "mj_b", "link", "crank", "anvil", "pad"))
    fig, ax = new_page(None, "Herb Snip · printed parts",
                       f"Seven parts in white PETG and a TPU pad printed twice: {tool_g:.0f} g printed for the tool.")
    items = [("body", "Body", "one housing: the collar above the\nband, the servo's pocket, the regulator's\nbay, the fixed jaw"),
             ("ring", "Camera ring", "the collar's foot and the D405's chin;\nbetween the flange and the body, on\nthe same four pins"),
             ("mj_a", "Jaw A", "camera side; the blade's pocket,\nthe clamp screw's countersink"),
             ("mj_b", "Jaw B", "servo side; pad rib, tail lug, the\nclamp insert, the pivot's counterbore"),
             (("link", "crank", "anvil"), "Link, crank, anvil", "crank to jaw tail, the crank on the\nhorn; the anvil "
              "is the strip the blade\ncloses on, replace when scored deep"),
             ("pad", "Pad, two", "TPU 95A: a comb of 11 fins on a\ndovetail; one on each jaw")]
    for i, (nm, title, what) in enumerate(items):
        r, c = divmod(i, 4)
        x0, ytop = 40 + c * 270, 762 - r * 300
        ax.add_patch(FancyBboxPatch((x0, ytop - 288), 258, 288, boxstyle="round,pad=0,rounding_size=8",
                                    facecolor="none", edgecolor="#dfe5e9", lw=1.0, zorder=5))
        MMc = iso_matrix(34, 24)
        if nm == "pad":
            ps = [Part(AS.load("pad"), AS.TPU, ang=30)]
            MMc = iso_matrix(70, 20)
        elif isinstance(nm, tuple):
            ps = [Part(K.mv(AS.load("link"), 0, 0, 9.0), AS.PETG, ang=30),
                  Part(K.mv(AS.load("crank"), 0, 0, -9.0), AS.PETG, ang=30),
                  Part(K.mv(AS.load("anvil"), 0, 26.0, -88.0), AS.PETG, ang=30)]
            MMc = iso_matrix(20, 40)
        elif nm == "ring":
            ps = [Part(AS.load("ring"), AS.PETG, ang=30)]
            MMc = iso_matrix(214, 22)
        else:
            ps = [p for p in tparts(0.0, names=[nm])]
        scene(ax, ps, (x0 + 129, ytop - 98), (200, 160), MM=MMc,
              clip=(x0 + 2, ytop - 186, x0 + 256, ytop - 2), px=3.0)
        ax.text(x0 + 14, ytop - 200, title, fontsize=9.2, fontweight="semibold", family=TITLE_FONT, color=INK,
                va="top")
        keys = nm if isinstance(nm, tuple) else (nm,)
        g = sum(mass[k]["g"] for k in keys); vol = sum(mass[k]["vol_cm3"] for k in keys)
        each = "  each" if nm == "pad" else ""
        ax.text(x0 + 14, ytop - 217, f"{g:.1f} g  ·  {vol:.2f} cm³{each}", fontsize=7.8, color=INK, va="top")
        ax.text(x0 + 14, ytop - 234, what, fontsize=7.4, color=DIM, va="top", linespacing=1.35)
    # print settings, in the seventh cell
    x0, ytop = 40 + 2 * 270, 762 - 300
    ax.add_patch(FancyBboxPatch((x0, ytop - 288), 258, 288, boxstyle="round,pad=0,rounding_size=8",
                                facecolor=PANEL, edgecolor="#dfe5e9", lw=1.0, zorder=5))
    rows = [("Material", "white PETG, like the arm;\nPLA creeps under 40 N"),
            ("Pads", "TPU 95A, solid, 20 mm/s,\nlying on their side"),
            ("Layers", "0.20 mm, 0.4 nozzle"),
            ("Walls", "4; small parts solid"),
            ("Infill", "body and ring 25 %"),
            ("Supports", "none; bridging on;\nthe ring a 5 mm brim")]
    ax.text(x0 + 14, ytop - 14, "Print settings", fontsize=9.2, fontweight="semibold", family=TITLE_FONT, color=INK,
            va="top", zorder=20)
    y = ytop - 38
    for a, b in rows:
        ax.text(x0 + 14, y, a, fontsize=8.0, fontweight="semibold", family=TITLE_FONT, color=INK, va="top", zorder=20)
        ax.text(x0 + 100, y, b, fontsize=7.8, color=DIM, va="top", linespacing=1.3, zorder=20)
        y -= 16 + 12.5 * (b.count("\n") + 1)
    ax.text(x0 + 14, y - 2, "snip/print/*.stl, already lying\nas they print", fontsize=7.4, color=DIM, va="top",
            linespacing=1.3, zorder=20)
    ax._body_y = 60.0
    save(fig, ax, pdf, "00a_printed")


BOUGHT = [
    # (mesh builder, name, qty, colour, view)
    (lambda: Q.servo(), "TowerPro MG90S servo, metal gear", "1", np.array([0.18, 0.30, 0.62])),
    (lambda: Q.regulator(), "Pololu D24V10F6, 6 V 1 A step-down", "1", K.PCB),
    (lambda: Q.blade(), "OLFA AB 9 mm blade, a 34 mm piece", "1", AS.BLADE_C),
    (lambda: Q.shoulder_screw(), "M3 shoulder screw, 4 × 6  ·  pivot", "1", K.STEEL),
    (lambda: Q.insert(C.INSERT_M3), "M3 heat-set insert, 5.7 long, 4.6 OD", "1", AS.BRASS),
    (lambda: Q.insert(C.INSERT_M2), "M2 heat-set insert, 3 long, 3.6 OD", "1", AS.BRASS),
    (lambda: Q.screw("iso10642_M2", 6.0), "M2 × 6 countersunk  ·  blade, crank", "2", K.STEEL),
    (lambda: Q.screw("iso10642_M3", 5.0), "M3 × 5 countersunk  ·  camera", "2", K.STEEL),
    (lambda: Q.dowel((0, 0), 0, 6.0), "dowel pin 2 × 6, ISO 8734", "1", K.STEEL),
    (lambda: Q.dowel((0, 0), 0, 5.0), "dowel pin 2 × 5, ISO 8734", "1", K.STEEL),
    (lambda: Q.lego_pin(0, 0), "LEGO Technic pin with friction, 2780", "4", np.array([0.12, 0.12, 0.13])),
]


@page
def p_bought(pdf):
    fig, ax = new_page(None, "Herb Snip · purchased parts",
                       "Everything else on the tool. The D405 and the arm's own LEGO pins may already be in the box.")
    for i, (fn, nm, q, col) in enumerate(BOUGHT):
        r, c = divmod(i, 3)
        cx, cy = 96 + c * 352, 712 - r * 128
        m = fn()
        scene(ax, [Part(m, col, ang=30)], (cx, cy), (78, 78), MM=iso_matrix(30, 30),
              clip=(cx - 50, cy - 50, cx + 50, cy + 50))
        ax.text(cx + 60, cy + 11, nm, fontsize=8.3, color=INK, va="center")
        ax.text(cx + 60, cy - 11, f"{q}×", fontsize=10.0, color=ACCENT, fontweight="bold", va="center")
    body(ax, "Also: 3-wire servo lead to the arm's end connector (2.54 Dupont), a red and black 22 AWG pair from the "
             "12 V wrist line, 2 small\nzip ties, heat-shrink. Already on the arm: the D405 and its high-flex USB-C cable "
             "(BOM G056, G057).", fs=9.0, color=DIM)
    save(fig, ax, pdf, "00b_bought")


@page
def p_tools(pdf):
    import tools_page as TP
    fig, ax = new_page(None, "Tools",
                       "A short list: the Herb Snip is small, and every screw is M2 or M3.")
    cards = [
        (lambda: [(K.mv(m, 0, 0, -i * 8.0), c) for i, (af, L1, L2) in enumerate(((1.3, 86, 14), (2.0, 100, 18)))
                  for m, c in TP.hex_key(af, L1, L2)], "Hex keys", "1.3 · 2 mm",
         "1.3: the two M2 countersunk\n2: the pivot and the camera screws", (30, 34)),
        (TP.calipers, "Calipers", "150 mm, digital", "the blade piece; the horn's fit, 2", (20, 45)),
        (TP.multimeter, "Multimeter", "DC volts", "6.0 V at the regulator before the\nservo goes on, 8", (25, 40)),
        (lambda: TP.screwdriver(2.5, 75.0), "Small screwdrivers", "Phillips 1 and flat 2.5",
         "the servo's tab screws, 7", (25, 30)),
    ]
    for i, (fn, name, size, steps, (az, el)) in enumerate(cards):
        x0, ytop = 40 + i * 270, 762
        ax.add_patch(FancyBboxPatch((x0, ytop - 218), 258, 218, boxstyle="round,pad=0,rounding_size=8",
                                    facecolor="none", edgecolor="#dfe5e9", lw=1.0, zorder=5))
        parts = [Part(m, col, ang=30) for m, col in fn()]
        scene(ax, parts, (x0 + 129, ytop - 62), (222, 92), MM=iso_matrix(az, el),
              clip=(x0 + 2, ytop - 120, x0 + 256, ytop - 2))
        ax.text(x0 + 14, ytop - 132, name, fontsize=9.2, fontweight="semibold", family=TITLE_FONT, color=INK, va="top")
        ax.text(x0 + 14, ytop - 149, size, fontsize=7.8, color=INK, va="top")
        ax.text(x0 + 14, ytop - 167, "steps: " + steps, fontsize=7.4, color=DIM, va="top", linespacing=1.35)
    chips = ["flat-nose pliers  ·  the blade, 3", "cut-resistant gloves  ·  the blade, 3",
             "soldering iron  ·  3, 4, 8", "wire stripper  ·  8",
             "servo tester, or the arm  ·  2, 6"]
    for i, c in enumerate(chips):
        r_, c_ = divmod(i, 3)
        tool(ax, 60 + c_ * 352, 470 - r_ * 52, c)
    note(ax, 60, 380, "No drill, no tap: every hole is printed to size. The two dowels press in with the flat of the "
                      "pliers, the two inserts\nwith the soldering iron at about 230 °C.", fs=9.4, color=INK)
    ax._body_y = 60.0
    save(fig, ax, pdf, "00c_tools")


# ------------------------------------------------------------------ steps
@page
def s1(pdf):
    fig, ax = new_page(1, "Print the parts", "Each file already lies the way it prints. One plate in PETG, then the pads in "
                       "TPU.")
    P2 = 300.0                                                   # plate 2 sits this far right in the drawing
    RING_AT = (-62.0, -40.0)                                     # the camera ring on its side, on plate 1
    files = [("snip_body", (-80, 50), 0, "body"), ("snip_jaw_A", (-32, 45), 0, "jaw A"),
             ("snip_jaw_B", (0, 45), 0, "jaw B"), ("snip_crank", (48, 72), 0, "crank"),
             ("snip_link", (48, 46), 0, "link"), ("snip_anvil", (48, 22), 0, "anvil, two"),
             ("snip_anvil", (48, 10), 0, None), ("snip_camera_ring", RING_AT, 0, "camera ring"),
             ("snip_pad_TPU_x2", (P2 - 6, 0), 90, "pads, two"), ("snip_pad_TPU_x2", (P2 + 6, 0), 90, None)]
    pr = os.path.join(HERE, "print")
    ps = [Part(K.box(256.0, 256.0, 2.0, c=(x0 - 128.0, -128.0, -2.0)), np.array([0.40, 0.42, 0.45]), ang=30)
          for x0 in (0.0, P2)]                                   # a dark textured PEI plate under white PETG
    tops = {}
    for nm, (x, y), rot, lab in files:
        V, F = stl(os.path.join(pr, nm + ".stl"))
        V = V - np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, 0])
        if rot:
            c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            V = V @ np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]]).T
        V = V + np.array([x, y, 0])
        ps.append(Part((V, F), AS.TPU if "TPU" in nm else AS.PETG, ang=30))
        if lab:
            tops[lab] = (x, y, V[:, 2].max())
    light = K.LIGHT
    K.LIGHT = np.array([0.30, 0.55, 0.78]) / np.linalg.norm([0.30, 0.55, 0.78])   # plates seen from high up
    try:
        v = scene(ax, ps, (470, 450), (860, 560), MM=iso_matrix(200, 50))
    finally:
        K.LIGHT = light
    lab_xy = {"body": (90, 640), "camera ring": (110, 330), "jaw A": (230, 150), "jaw B": (340, 150), "crank": (250, 700),
              "link": (455, 700), "anvil, two": (540, 150),
              "pads, two": (720, 150)}
    for lab, (lx, ly) in lab_xy.items():
        p = v(tops[lab])
        ax.plot([lx, p[0]], [ly, p[1]], color=DIM, lw=0.9, zorder=330,
                path_effects=[pe.Stroke(linewidth=2.6, foreground="white"), pe.Normal()])
        ax.add_patch(Circle((p[0], p[1]), 2.2, facecolor=DIM, edgecolor="none", zorder=331))
        ax.text(lx, ly, lab, fontsize=8.6, color=DIM, ha="center", va="center", zorder=332,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    note(ax, 860, 330, "No supports. The body stands on its flat\nbase, the camera ring on its flat side\n"
                       "with a 5 mm brim (it stands 42 tall).\nJaw A outer face down, jaw B and the\n"
                       "anvils working faces down, the crank horn\npocket up. The pads lie on their side, so\n"
                       "every layer is the whole comb: TPU 95A,\nsolid, 20 mm/s, a plate of their own.", fs=8.6)
    body(ax, "A 256 × 256 bed (the Bambu P2S's). The anvil face and both jaw faces print against the "
             "plate: those are the\nfaces that must be flat. Check the crank fits your servo's horn before anything "
             "else is printed (step 2).")
    save(fig, ax, pdf, "01")


@page
def s2(pdf):
    fig, ax = new_page(2, "Fit the crank to your servo's horn",
                       "TowerPro publishes no drawing of the horn. Check it before going on.")
    th = C.crank_angle(0.0)
    names = ["servo", "horn", "crank", "crank_screw", "dowel_crank"]
    offs = {"crank": (0, -14, 0), "crank_screw": (0, -32, 0), "dowel_crank": (0, -26, 0), "horn": (0, -6, 0)}
    ps = tparts(0.0, names=names, offs=offs, hi=("crank",))
    foc = focus_box((C.SV[0] - 20, -36, C.SV[1] - 20), (C.SV[0] + 24, 20, C.SV[1] + 20))
    v = scene(ax, ps, (400, 450), (560, 560), MM=iso_matrix(150, 18), focus=foc)
    sv = np.array([C.SV[0], 0, C.SV[1]])
    axis3(ax, v, sv + (0, -40, 0), sv + (0, 14, 0))
    tag(ax, 790, 690, "single-arm horn, from the servo's bag", 1)
    tag(ax, 790, 642, "crank (printed)", 1, hi=True)
    tag(ax, 790, 594, "M2 × 6 countersunk", 1)
    tag(ax, 790, 546, "dowel pin 2 × 5, pressed into the crank", 1)
    tool(ax, 790, 496, "1.5 mm hex  ·  flat pliers")
    note(ax, 790, 450, "The horn's arm drops into the crank's pocket\nand the crank sits flat on the horn's face.\n"
                       "If the arm will not drop in, or the crank\nrocks, measure the horn and change HORN in\n"
                       "snip_cad.py: the crank reprints in minutes.", fs=8.8)
    body(ax, "Press the 2 × 5 dowel into the crank's small hole until it stands 3 proud on the horn side. Do not fit the "
             "crank to the servo yet:\nit goes on in step 6, at the servo's closed position, so the jaw closes where the "
             "servo stops.")
    save(fig, ax, pdf, "02")


@page
def s3(pdf):
    fig, ax = new_page(3, "The blade between the jaw halves",
                       "One insert, one blade, one screw. Snap a piece with about 34 of cutting edge. Gloves on.")
    names = ["mj_a", "mj_b", "blade", "clamp", "insert_clamp"]
    offs = {"mj_b": (26, 34, 0), "insert_clamp": (26, 50, 0), "blade": (0, 12, 0), "clamp": (0, -16, 0)}
    ps = tparts(0.0, names=names, offs=offs, hi=("blade", "insert_clamp", "clamp"))
    v = scene(ax, ps, (420, 440), (560, 600), MM=iso_matrix(28, 22))
    x, z = C.CLAMP
    axis3(ax, v, (x, -20, z), (x, 2, z))
    axis3(ax, v, (x, 2, z), (x + 26, 34, z))
    axis3(ax, v, (x + 26, 37, z), (x + 26, 50, z))
    tag(ax, 780, 690, "OLFA AB 9 mm blade, a 34 mm piece", 1, hi=True)
    tag(ax, 780, 642, "M2 heat-set insert, into jaw B", 1, hi=True)
    tag(ax, 780, 594, "M2 × 6 countersunk, from jaw A", 1, hi=True)
    tool(ax, 780, 544, "iron  ·  1.3 mm hex  ·  pliers")
    note(ax, 780, 500, "First the insert: into jaw B from its outer face,\nthe iron at about 230 °C, until it sits flush.\n"
                       "Then the blade: grip it in the pliers at a score\nline and bend away from you. The piece's ends\n"
                       "are the score lines, so it is a parallelogram: the\npocket's angled ends take any OLFA piece of\n"
                       "30 to 35. Cutting edge toward the jaw's straight\ninner edge, sticking out 1.5 past it.", fs=8.8)
    body(ax, "Lay the blade in jaw A's pocket, bevel down. Jaw B on top, faces together, and the screw from jaw A's side: "
             "its head sinks flush.\nThe pocket is 0.08 shallower than the blade, so the one screw pinches it: snug, no "
             "more. The thread is brass, so a blade can be\nchanged as often as it needs to be.")
    save(fig, ax, pdf, "03")


@page
def s4(pdf):
    fig, ax = new_page(4, "Pads, anvil and the pivot insert",
                       "The two TPU pads slide in from the servo side. The anvil and an insert go into the body.")
    names = ["body", "anvil", "pad_fj", "insert_pivot", "mj_a", "mj_b", "blade", "pad_mj", "clamp", "insert_clamp"]
    mj = ("mj_a", "mj_b", "blade", "clamp", "insert_clamp")
    offs = {n: (34, 0, 0) for n in mj}
    offs.update({"anvil": (-14, 0, 0), "pad_fj": (0, 30, 0), "pad_mj": (34, 30, 0), "insert_pivot": (0, 18, 0)})
    ps = tparts(0.0, names=names, offs=offs, hi=("anvil", "pad_fj", "pad_mj", "insert_pivot"))
    foc = focus_box((-50, -20, 40), (70, 40, 112))
    v = scene(ax, ps, (430, 450), (640, 560), MM=iso_matrix(34, 18), focus=foc)
    for x in (C.FJ_RIB_EDGE - 2.0, 34 + C.MJ_RIB_EDGE + 2.0):
        axis3(ax, v, (x, 9.5, 88.0), (x, 32.0, 88.0))
    axis3(ax, v, (C.P[0], -3.0, C.P[1]), (C.P[0], 9.3, C.P[1]))
    tag(ax, 820, 690, "pad (printed in TPU 95A)", 2, hi=True)
    tag(ax, 820, 642, "anvil (printed)", 1, hi=True)
    tag(ax, 820, 594, "M3 heat-set insert, into the cheek", 1, hi=True)
    tool(ax, 820, 544, "soldering iron")
    note(ax, 820, 500, "The insert goes in from the jaw side of the\ncheek, flush: the pivot's shoulder bears on it.\n"
                       "The deck is 4 under its axis: an iron under 8\nthick for its first 50 sets it square.\n"
                       "Each pad slides into its rib until it stops on\nthe jaw plate, fins toward the other jaw. The\n"
                       "dovetail is cut one way only: if a pad will not\ngo in, turn it end for end. The anvil slides\n"
                       "into its pocket, smooth face toward the blade;\na drop of thin glue keeps it.", fs=8.8)
    pd = CHECKS["pads"]
    body(ax, f"The fins stand {C.PADT['proud']:.1f} proud of the ribs, so the pads meet the stem before the blade does, "
             f"bend round it and hold the cut-off part:\nabout {pd['d4.5']['F_hold']:.1f} N on a 4.5 mm stem, slanted so a piece "
             "pulled toward the tips digs in. No glue: the dovetail holds them, and a worn\npad slides out for a new one.")
    save(fig, ax, pdf, "04")


@page
def s5(pdf):
    fig, ax = new_page(5, "The jaw on its pivot, and the link",
                       "The jaw goes in open, from above; one shoulder screw into the cheek's insert; then the link.")
    names = ["body", "anvil", "pad_fj", "insert_pivot", "mj_a", "mj_b", "blade", "pad_mj", "clamp", "insert_clamp",
             "pivot", "link", "dowel_tail"]
    up = 52.0                                                    # the link drawn above the deck, on its way in
    offs = {"pivot": (0, 28, 0), "link": (0, CK.LINK_IN, up), "dowel_tail": (0, CK.LINK_IN, up)}
    ps = tparts(30.0, names=names, offs=offs, hi=("pivot", "link", "dowel_tail"))
    foc = focus_box((-16, -30, 30), (24, 40, 125))
    v = scene(ax, ps, (430, 440), (560, 600), MM=iso_matrix(40, 16), focus=foc)
    pv = np.array([C.P[0], 0, C.P[1]])
    axis3(ax, v, pv + (0, -10, 0), pv + (0, 36, 0))
    T = AS.state(30.0)[2]
    axis3(ax, v, (T[0], 4.2 + CK.LINK_IN, T[1] + up), (T[0], 4.2 + CK.LINK_IN, T[1]))
    tag(ax, 790, 690, "M3 shoulder screw, 4 × 6, from the lug side", 1, hi=True)
    tag(ax, 790, 642, "link (printed)", 1, hi=True)
    tag(ax, 790, 594, "dowel pin 2 × 6, pressed into the link", 1, hi=True)
    tool(ax, 790, 544, "2 mm hex")
    note(ax, 790, 500, f"Hold the jaw open about {CK.JAW_IN[0]:.0f}°, lower it into the deck\n{CK.JAW_IN[1]:.0f} toward its "
                       "opening side, clear of the fixed\npad, then slide it across until its bore meets\nthe cheek's insert, and "
                       "drive the screw: its head\nsinks flush into the lug. Close the jaw. Press\nthe dowel into the link, "
                       f"lower the link {CK.LINK_IN:.0f} to the\nservo side of its slot, past jaw B's rib, and\npush it "
                       "across: the dowel drops into the lug.", fs=8.8)
    body(ax, "Tighten the shoulder screw fully: its shoulder bears on the brass insert, not on the jaw, so the jaw keeps "
             "0.2 of play however\ntight it is. Swing the jaw by hand from closed to open: no tight spot, and it should "
             "fall open under its own weight with the tool\nupside down.")
    save(fig, ax, pdf, "05")


@page
def s6(pdf):
    fig, ax = new_page(6, "The crank on the servo, at closed",
                       "Set the servo to its closed position, then fit the crank where it lands.")
    th = C.crank_angle(0.0)
    names = ["servo", "horn", "crank", "crank_screw", "dowel_crank"]
    ps = tparts(0.0, names=names, hi=("crank", "crank_screw"))
    MMs = iso_matrix(180, 4)
    v = scene(ax, ps, (380, 450), (400, 440), MM=MMs)
    sv = np.array([C.SV[0], 8.0, C.SV[1]])
    a = v(sv); b = v(sv + np.array([math.cos(th), 0, math.sin(th)]) * C.A_CRANK * 1.9)
    arrow2(ax, (a[0], a[1]), (b[0], b[1]), color=ACCENT, lw=1.6, ms=12)
    Pp = v(np.vstack([p.mesh[0] for p in ps if len(p.mesh[1])]))
    x0b, x1b = Pp[:, 0].min(), Pp[:, 0].max()
    ax.plot([a[0], x1b + 60], [a[1], a[1]], ls=(0, (4, 3)), lw=0.9, color=DIM, zorder=210)
    ax.text(x1b + 64, a[1], "the jaw opens\nthis way", fontsize=8.6, color=DIM, va="center", zorder=212,
            linespacing=1.3)
    ax.text(b[0] + 10, b[1] - 4, f"crank {abs(math.degrees(th)):.0f}° below it", fontsize=8.6, color=ACCENT,
            va="center", zorder=212, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    arrow2(ax, (x0b - 46, a[1] - 90), (x0b - 46, a[1] + 40), color=DIM, lw=1.2, ms=10)
    ax.text(x0b - 46, a[1] + 54, "toward the\njaw tips", fontsize=8.6, color=DIM, ha="center", va="bottom",
            zorder=212, linespacing=1.3)
    tag(ax, 780, 690, "crank and horn, from step 2", 1, hi=True)
    tag(ax, 780, 642, "M2 × 6 countersunk into the spline", 1, hi=True)
    tool(ax, 780, 592, "1.5 mm hex  ·  servo tester")
    note(ax, 780, 548, "Drive the servo to its closed end first:\npulse 1500, then 2400 (step 12, or a servo\n"
                       "tester). Clockwise seen from the horn means\n2400 is closed; if not, use 600. The spline\n"
                       "has 20 teeth, 18° each: take the tooth that\npoints the crank nearest the arrow. Software\n"
                       "trims the last few degrees.", fs=8.8)
    body(ax, "Seen from the horn side, shaft end toward the jaw tips: the jaw opens to the right. The servo turns the "
             "crank 157° from closed\nto fully open, well inside its 180°. Fit the horn with the crank already over it, "
             "then the screw.")
    save(fig, ax, pdf, "06")


@page
def s7(pdf):
    fig, ax = new_page(7, "The servo into the housing",
                       "Crank first, from the back; the crank's dowel drops into the link's free end.")
    names = ["body", "anvil", "pad_fj", "insert_pivot", "mj_a", "mj_b", "blade", "pad_mj", "clamp", "insert_clamp",
             "pivot", "link",
             "dowel_tail", "servo", "horn", "crank", "crank_screw", "dowel_crank", "tab_screws"]
    mov = ("servo", "horn", "crank", "crank_screw", "dowel_crank")
    offs = {n: (0, 36, 0) for n in mov}
    offs["tab_screws"] = (0, 58, 0)
    ps = tparts(0.0, names=names, offs=offs, hi=mov + ("tab_screws",))
    v = scene(ax, ps, (420, 450), (580, 600), MM=iso_matrix(34, 20))
    sv = np.array([C.SV[0], 0, C.SV[1]])
    axis3(ax, v, sv + (0, 10, 0), sv + (0, 40, 0))
    tag(ax, 790, 690, "servo with crank, from step 6", 1, hi=True)
    tag(ax, 790, 642, "tab screws, from the servo's bag", 2, hi=True)
    tool(ax, 790, 592, "Phillips 1")
    note(ax, 790, 548, "Hold the link's free end over the crank's dowel\nthrough the port on the fixed jaw's side as\n"
                       "the servo slides home. The ledge under the tabs\nis slotted ±1 along the tool: slide the servo\n"
                       "until the jaw is fully closed with the crank at its\nclosed angle, then drive the two screws from\n"
                       "the back: a driver under 5 thick passes the case.", fs=8.8)
    body(ax, "The jaw is now driven: it should not move by hand with the servo unpowered beyond the gearbox's slack. "
             "Leave the servo\nunplugged until the regulator reads 6.0 V (step 8).")
    save(fig, ax, pdf, "07")


@page
def s8(pdf):
    fig, ax = new_page(8, "Regulator and leads", "The servo runs on 6 V from the 12 V wrist line, not on the arm's own supply.")
    names = ["body", "anvil", "pad_fj", "insert_pivot", "mj_a", "mj_b", "blade", "pad_mj", "clamp", "insert_clamp",
             "pivot", "link",
             "dowel_tail", "servo", "horn", "crank", "crank_screw", "dowel_crank", "tab_screws", "regulator"]
    ps = tparts(0.0, names=names, offs={"regulator": (24, 0, 0)}, hi=("regulator",))
    v = scene(ax, ps, (400, 450), (520, 580), MM=iso_matrix(70, 18))
    rc = np.array([C.REG_BAY["x"][0] + 2.8, 33.0, 38.0])
    axis3(ax, v, rc, rc + (24, 0, 0))
    tag(ax, 760, 690, "Pololu D24V10F6, into the bay in the side", 1, hi=True)
    tag(ax, 760, 642, "double-sided foam tape, a 12 mm square", 1)
    tag(ax, 760, 594, "small zip tie, under the bar below the bay", 1)
    tool(ax, 760, 544, "soldering iron  ·  stripper  ·  meter")
    note(ax, 760, 500, "Solder three wires to VIN, GND and VOUT (the\nwiring page has which goes where), sleeve the\n"
                       "board in heat-shrink, put the tape on its back\nand press it into the bay, parts outward. The\n"
                       "wires leave by the channel at the bay's foot and\nare tied under the bar with the servo's lead.\n"
                       "Power it from the 12 V wrist line and read 6.0 V\nat VOUT before the servo goes on.", fs=8.8)
    body(ax, "The MG90S stalls at 0.7 A at 6 V; the regulator gives 1 A. The arm's own 5 V pin at the end connector is "
             "not rated for that,\nso only the servo's signal and ground go to the arm.")
    save(fig, ax, pdf, "08")


@page
def s9(pdf):
    fig, ax = new_page(9, "The camera on its ring", "On the bench: the D405 you already have, two M3 screws into its back.")
    Rc = C.cam_R()
    off = tuple(-22.0 * Rc[:, 2])
    ps = tparts(0.0, names=["ring", "d405", "usb_plug", "cam_screws"],
                offs={"d405": tuple(30.0 * Rc[:, 2]), "usb_plug": tuple(30.0 * Rc[:, 2]), "cam_screws": off},
                hi=("d405", "cam_screws"))
    v = scene(ax, ps, (420, 450), (580, 600), MM=iso_matrix(214, 20))
    back = C.CAM_G - 23.0 * Rc[:, 2]
    for sx in (-10.0, 10.0):
        p = back + Rc[:, 0] * sx
        axis3(ax, v, p - 24 * Rc[:, 2], p + 34 * Rc[:, 2])
    tag(ax, 780, 690, "Intel RealSense D405", 1, hi=True)
    tag(ax, 780, 642, "M3 × 5 countersunk, into the camera's back", 2, hi=True)
    tool(ax, 780, 592, "2 mm hex")
    note(ax, 780, 548, "Before the ring goes on the arm: the screws\ngo in from under the chin, through its two\n"
                       "key holes. The camera looks along the jaws,\ntilted 20° toward the pads; "
                       "its USB-C socket\nfaces away from the jaw's opening side. Five\nlong, no longer: the heads "
                       "sink flush in the\nplate and 2 of thread goes into the camera's\nshallow holes.", fs=8.8)
    cam = CHECKS["camera"]
    body(ax, f"From the camera the cut sits {cam['cut zone centre']['depth_mm']:.0f} away, just past the D405's 70 mm "
             "near limit, and the jaw tips at "
             f"{cam['jaw tips']['depth_mm']:.0f}: it sees the stem in the jaws\nbefore it cuts. Closer than 70 the depth "
             "goes blank, so the last stretch of every approach runs on the arm's kinematics.")
    save(fig, ax, pdf, "09")


@page
def s10(pdf):
    fig, ax = new_page(10, "Onto the arm", "Four LEGO pins through the ring into the body. No screws: the 280's end takes "
                       "accessories this way.")
    names = None
    skip = ()
    ps = tparts(0.0, wrist=True, offs=None)
    # lift the tool off the flange for the exploded view
    tool_names = [n for n, m, c in AS.parts(0.0, cots=True)]
    lift = 44.0
    out = []
    for n, m, c in AS.parts(0.0, cots=True, wrist=True):
        if n in ("flange", "joint6", "joint5"):
            out.append(Part(m, c, ang=33, lw=0.4))
        elif n == "lego":
            out.append(Part(K.mv(m, 0, 0, lift * 0.3), K.HILITE, ang=30))
        elif n in ("ring", "d405", "usb_plug", "cam_screws"):
            out.append(Part(K.mv(m, 0, 0, lift * 0.6), c, ang=30))
        else:
            out.append(Part(K.mv(m, 0, 0, lift), c, ang=30))
    foc = focus_box((-60, -70, -70), (40, 60, 160))
    v = scene(ax, out, (420, 440), (560, 620), MM=iso_matrix(34, 18), focus=foc)
    for x, y in C.LEGO:
        axis3(ax, v, (x, y, -6), (x, y, lift + 10))
    tag(ax, 780, 690, "LEGO Technic pin with friction", 4, hi=True)
    tool(ax, 780, 640, "hands only")
    note(ax, 780, 596, "Take the adaptive gripper off if it is fitted:\nit pulls off its pins the same way. Pins into\n"
                       "the flange first, half their length. Then the\nring with its camera over them, flat on the\n"
                       "flange, and the Herb Snip square onto them,\nservo side toward the arm's J6 cable exit:\n"
                       "the band's groove runs along the line\nbetween them. The pins hold both.", fs=8.8)
    body(ax, "Cables: the D405's USB-C, the 12 V pair and the 3-wire servo lead run together along the arm, tied at each "
             "link, with\none loose loop at the wrist so J6 can turn ±180°. The servo's signal and ground go to the end "
             "connector's G22 and GND.")
    save(fig, ax, pdf, "10")


@page
def s11(pdf):
    import frame as Fr
    import arm_checks as ARC
    fig, ax = new_page(11, "Where the cuts go",
                       "Dead leaves into the dead-leaf tray in the base bay; leaves and veggies out to the feeder at tier B.")
    d = ARMC["tray"]
    T = C.TRAY
    mid = d["drops"][len(d["drops"]) // 2]
    xg, zj = mid["carriage_x"], d["j1_low"]
    fold = tuple(Fr.TIGHT_Q[:5]) + (0.0,)
    x0c, x1c, z0c, z1c = 0.0, 720.0, 0.0, 520.0
    ps = [Part(Fr.cabinet(z0=z0c, z1=z1c, x0=45.0, x1=x1c, y0=206.0), K.ALU, ang=30),    # left side, front cut away
          Part(K.box(x1c - Fr.SER, Fr.D - 4.0, 2.0, c=(Fr.SER, 2.0, Fr.SER)), K.ALU_D, ang=30)]   # the base pan
    for p in Fr.gantry_parts(x=xg, z=zj, q=fold, rail=False):
        V, F = p.mesh
        if ((V[:, 2] > z0c - 50) & (V[:, 2] < z1c + 80)).any():
            ps.append(p)
    for n, m, c in AS.parts(55.0, cots=True):
        ps.append(Part(on_flange(m, fold, xg, zj), K.HILITE if n in ("mj_a", "mj_b") else c, ang=30))
    foc = focus_box((x0c, 0, z0c), (x1c, Fr.D, z1c))
    v = scene(ax, ps, (430, 430), (700, 620), MM=iso_matrix(218, 30), focus=foc, clip=(20, 60, 1130, 772))
    tp = np.array(d["cut_point_at_x_min"]) + np.array([mid["carriage_x"] - ARC.X_MIN, 0.0, 0.0])
    a0 = v(tp); a1 = v((tp[0], tp[1], T["rim_z"]))
    arrow2(ax, (a0[0], a0[1]), (a1[0], a1[1]), color=ACCENT, lw=2.2, ms=14)
    # the tray's rim line at the drops, and the five drops along it: marks, not a part
    r0 = v((T["x"][0], T["drop_y"], T["rim_z"])); r1 = v((T["x"][1], T["drop_y"], T["rim_z"]))
    ax.plot([r0[0], r1[0]], [r0[1], r1[1]], color=ACCENT, lw=1.2, ls=(0, (5, 4)), zorder=330)
    for dr in d["drops"]:
        p = v((dr["x"], T["drop_y"], T["rim_z"]))
        ax.add_patch(Circle((p[0], p[1]), 3.0, facecolor=ACCENT, edgecolor="white", lw=0.8, zorder=331))
    ax.text(840, 120, "Drawn with the cabinet's left side, everything\nin front of the corridor and tier A's tray cut\naway. "
                      "The dashed line is the dead-leaf\ntray's rim line, the dots its five drops.", fontsize=8.0, color=DIM,
            zorder=330, va="bottom", linespacing=1.4)
    tag(ax, 840, 700, "dead-leaf tray, from Harvest Rev B", 1, hi=True)
    tag(ax, 840, 652, "feeder, from Harvest Rev B", 1, hi=True)
    xs = ", ".join(f"{dr['carriage_x'] - ARC.X_MIN:.0f}" for dr in d["drops"])
    note(ax, 840, 600, "Build both from the Harvest booklet. The tray\nhangs on its rails in the base bay and slides\n"
                       "out of the bottom-left door.\n\n"
                       f"A dead leaf rides folded in the closed jaws.\nThe gantry stops over a drop at the lowest Z,\n"
                       f"J1 {zj:.0f} up, and the jaws open {d['over_rim']:.0f} above\nthe rims, at least "
                       f"{min(dr['jaws_to_walls'] for dr in d['drops']):.0f} from a wall. Z full\ntravel there clears the rims "
                       f"by {d['clearance']:.0f}.\nrobot.yaml X of the five drops, from the left\nlimit: {xs}.\n\n"
                       "Leaves go to the feeder's front compartment,\nveggies and peppers to its back one: the arm\n"
                       "reaches out through the right panel at tier B\nwith the piece in its jaws, on the drop poses\n"
                       "the harvest package solves (drops.yaml).", fs=8.6)
    body(ax, "Nothing cut ever leaves the arm's lane except through the feeder's openings. A dead leaf and a harvest never "
             "share a\ndestination: the tray takes what the plants shed, the feeder what you eat.", fs=10.2)
    save(fig, ax, pdf, "11")


@page
def s12(pdf):
    fig, ax = new_page(12, "Commission", "With the cabinet closed, from the Jetson: tools_snip_check.py, then a real stem.")
    rows = [("Find the closed end", "tools_snip_check.py pulse 1500, then 2400: clockwise seen from the horn means 2400 "
                                    "is closed (step 6)."),
            ("Closed and open", "step closed_us until the blade just reaches the anvil, plus one; open_us for 55°. "
                                "Into arm.yaml, calibrated: true."),
            ("PWM from the arm", "tools_snip_check.py pwm  ·  the jaw opens and closes three times on G22's 50 Hz pulses."),
            ("Cut a basil stem", "tools_snip_check.py cut  ·  clean through, and the leaf still in the pads when it opens."),
            ("Cut a chili stem", "the hardest stem in the cabinet. If it only dents it, check the pivot is free (step 5)."),
            ("Stem in the jaws", "tools_snip_check.py stem --empty, then stem: empty reads empty, a stem reads present."),
            ("Transit fold", "fold, then run Z full travel over the dead-leaf tray: clear of the tray line and of "
                             "its rims (step 11)."),
            ("Into the tray and the feeder", "jog to each drop (the tray's five, the feeder's two) and write it into "
                                             "robot.yaml. A release there lands inside."),
            ]
    checkbox_rows(ax, rows, y0=704, dy=76)
    body(ax, "Dead leaves go to the tray, leaves and veggies to the feeder, never the other way. With a door or the "
             "feeder's lid open,\nor the E-stop down, the arm has no power, the end connector sends no pulses, and "
             "the servo goes limp: the jaw\ncannot close on a hand.", fs=10.2)
    save(fig, ax, pdf, "12")


@page
def w1(pdf):
    import wiring_pages as WR
    WR._TF[0] = TITLE_FONT
    fig, ax = new_page(None, "Wiring · the Herb Snip",
                       "Power from the 12 V wrist line, signal from the arm's end connector, video over the D405's USB.")
    V12 = "#b45309"
    BRN, RED, ORG = "#7c4a2d", "#dc2626", "#ea580c"
    WR.box(ax, 60, 520, 200, 190, "12 V wrist line", "from the cabinet's 12 V rail\n(sheet E-01), in the arm's\ncable run")
    p12 = WR.term(ax, 260, 600, "+12 V", "r"); g12 = WR.term(ax, 260, 550, "0 V", "r")
    WR.box(ax, 380, 520, 200, 190, "Regulator", "Pololu D24V10F6\n6 V, 1 A step-down")
    vin = WR.term(ax, 380, 600, "VIN", "l"); gnd = WR.term(ax, 380, 550, "GND", "l")
    vout = WR.term(ax, 580, 600, "VOUT", "r"); gnd2 = WR.term(ax, 580, 570, "GND", "r")
    WR.box(ax, 740, 500, 210, 210, "Servo", "TowerPro MG90S,\nits own lead colours")
    sr = WR.term(ax, 740, 600, "red  +6 V", "l"); sb = WR.term(ax, 740, 570, "brown  GND", "l")
    so = WR.term(ax, 740, 530, "orange  signal", "l")
    WR.box(ax, 380, 290, 200, 180, "Arm end connector", "myCobot 280 Pi, functional\ninterface group 2")
    ga = WR.term(ax, 580, 400, "GND", "r"); g22 = WR.term(ax, 580, 370, "G22", "r")
    WR.term(ax, 580, 340, "5V  (unused)", "r"); WR.term(ax, 580, 312, "3V3  (unused)", "r")
    WR.box(ax, 740, 290, 210, 180, "D405", "Intel RealSense, its\nhigh-flex USB-C to the\nJetson (G057)")
    WR.wire(ax, [p12, vin], V12); WR.lab(ax, 300, 606, "22 AWG", V12)
    WR.wire(ax, [g12, gnd], WR.WGND)
    WR.wire(ax, [vout, sr], RED)
    WR.wire(ax, [gnd2, sb], BRN)
    WR.wire(ax, [g22, (690, 370), (690, 530), so], ORG)
    WR.wire(ax, [ga, (660, 400), (660, 570)], WR.WGND)
    ax.add_patch(Circle((660, 570), 3.2, facecolor=INK, edgecolor="none", zorder=62))
    WR.lab(ax, 596, 352, "3.3 V logic, 50 Hz", WR.WSIG, va="top")
    ax.text(60, 316, "Colours", fontsize=8.4, fontweight="semibold", family=TITLE_FONT, color=INK)
    for i, (t, c) in enumerate((("+12 V, the wrist line", V12), ("0 V", WR.WGND),
                                ("servo +6 V (red)", RED), ("servo ground (brown)", BRN), ("servo signal (orange)", ORG))):
        y = 294 - i * 18
        ax.plot([60, 86], [y, y], color=c, lw=2.2)
        ax.text(94, y, t, fontsize=7.8, color=INK, va="center")
    WR.notes(ax, 160, x1=250, rows=[
        ("Common ground", "The regulator's ground and the end connector's GND meet at the servo's brown wire: the signal "
                          "needs it to mean anything."),
        ("Why not the arm's 5 V", "The end connector's pins are rated in tens of mA; the servo stalls at 0.7 A."),
        ("When the arm is off", "Doors or E-stop cut the arm's power: no pulses, the servo goes limp, the 6 V stays "
                                "harmless."),
        ("Fallback", "If the arm will not give a steady 50 Hz on G22, a Pololu Micro Maestro on the D405's USB run "
                     "drives the same lead.")])
    ax._body_y = 60.0
    save(fig, ax, pdf, "w1")


def _order():
    names = [f.__name__ for f in PAGES]
    f = PAGES.pop(names.index("w1")); names.remove("w1")
    k = names.index("s9")
    PAGES.insert(k, f); names.insert(k, "w1")


_order()


# ================================================================== cover
COVER = os.environ.get("MAAG_COVER", os.path.join(HERE, "..", "gantry", "cover", "cover.png"))


def p_cover(pdf):
    """The Maag cover render on top, the title block underneath: the same cover on every booklet."""
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
    ax.text(50, y0 - 100, f"Herb Snip assembly instructions, {REV}.  The cut-and-hold tool for the myCobot 280.", fontsize=12.0, color=DIM, va="center")
    ax.text(1102, y0 - 46, "12 steps  ·  print files  ·  wiring", fontsize=11, color=INK, ha="right", va="center")
    ax.text(1102, 26, f"Design {DESIGN}. The Maag cover render, the same on every booklet. Every drawing inside comes "
                      "from snip_cad.py, Intel's D405 mesh and Elephant Robotics' arm meshes.",
            fontsize=7.6, color=DIM, ha="right")
    pdf.savefig(fig); fig.savefig(f"{OUT}/d_000_cover.png", dpi=130); plt.close(fig)


PAGES.insert(0, p_cover)


if __name__ == "__main__":
    only = sys.argv[1:]
    if only:
        class _NoPdf:
            def savefig(self, fig):
                pass
        for f in PAGES:
            if f.__name__ in only:
                f(_NoPdf()); print(f.__name__, "ok", flush=True)
    else:
        path = os.path.join(OUT, f"Maag_Herb_Snip_Assembly_Instructions_{REV.replace(' ', '')}.pdf")
        with PdfPages(path) as pdf:
            for f in PAGES:
                f(pdf); print(f.__name__, "ok", flush=True)
        print("wrote", path)
