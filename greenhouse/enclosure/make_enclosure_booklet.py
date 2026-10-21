#!/usr/bin/env python3
"""Maag enclosure: assembly instructions, Enclosure Rev A (design 0.6.1).

Every drawing is generated from enclosure.py on top of cabinet.py, so a page,
a DXF and the frame they fit cannot disagree.

    python make_enclosure_booklet.py              # whole booklet
    python make_enclosure_booklet.py s3 s7        # just those pages, PNG only
"""
import functools
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "frame"))
sys.path.insert(0, os.path.join(_HERE, "..", "booklet"))
sys.path.insert(0, os.path.join(_HERE, "..", "gantry"))

import maagbook as B                                                   # noqa: E402
from maagbook import (new_page, scene, inset, save, arrow2, axis3, tag, body, tool, note,   # noqa: E402
                      panel, leader, checkbox_rows, Circle, Rectangle, FancyBboxPatch, Polygon,
                      TITLE_FONT, INK, DIM, ACCENT, WARN, OK, AXIS, EDGE, RULE, CHIP, PANEL)
from kit3d import (Part, iso_matrix, merge, mv, rot, box, cylinder, ring, tube, ALU, ALU_D, STEEL,   # noqa: E402
                   BLACKPART, HILITE)
import cabinet as C                                                    # noqa: E402
import enclosure as E                                                  # noqa: E402

REV = "Enclosure Rev A"
DESIGN = "0.6.1"
OUT = os.environ.get("ENCLOSURE_OUT", os.path.join(_HERE, "build"))

import make_frame_booklet as FB                                        # noqa: E402
B.configure(REV, OUT)

import matplotlib.pyplot as plt                                        # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages                   # noqa: E402

PAGES = []
_body = body


def body(ax, txt, color=INK, fs=10.5):
    """maagbook.body, wrapped to the page: about 148 characters a line at 10.5."""
    import textwrap
    width = int(146 * 10.5 / fs)
    paras = [textwrap.fill(p_.replace("\n", " "), width) for p_ in txt.split("\n\n")]
    _body(ax, "\n".join(paras), color=color, fs=fs)


FROST = np.array([0.87, 0.90, 0.92])       # frosted polycarbonate
CLEARC = np.array([0.80, 0.88, 0.94])      # clear polycarbonate, the doors
EPDM = np.array([0.24, 0.25, 0.26])
NUTC = FB.NUTC
TUBE, FITTING, INKISH, SHEET = FB.TUBE, FB.FITTING, FB.INKISH, FB.SHEET
WHITEP = np.array([0.95, 0.95, 0.93])
VIEW = (212, 20)
BACKV = (32, 20)


def page(fn):
    PAGES.append(fn)
    return fn


def view(az, el):
    return iso_matrix(az, el)


@functools.lru_cache(maxsize=None)
def swing_max(pair, side):
    return E.door_swing(pair, side)


fbox = FB.fbox

# ============================================================ build state
ST = dict(seal=2, tape_back=3, back_bottom=4, back_rest=5, battens=6, right_bench=7, right=8,
          riser_off=9, left=10, riser_on=11, fans_bench=12, top=13, doors_bench=14, frame_side=15,
          hang=16)
NSTEPS = 18


@functools.lru_cache(maxsize=None)
def _cab():
    return tuple(FB.cab(99, feet=True))


@functools.lru_cache(maxsize=None)
def _panel(name):
    return E.panel_mesh(name)


@functools.lru_cache(maxsize=None)
def _tape(face):
    return E.tape_mesh(face)


@functools.lru_cache(maxsize=None)
def _fast(face, only=None):
    return tuple(E.fasteners(face, nuts=False, only=only))


@functools.lru_cache(maxsize=None)
def _fan_clear():
    try:
        return f"{E.fan_clearance()['clear, heads to the highest']:.0f}"
    except Exception:                                       # the arm's meshes are not on this machine
        return "38"


@functools.lru_cache(maxsize=None)
def _fan():
    return E.fan_mesh()


def right_kit(on_panel=True, explode=0.0):
    """Glands, intake grill and filter, duct collar: placed on the right panel."""
    out = []
    w0 = E.OUT
    for u, v in E.GLANDS:
        out.append(("gland", E.to_face("right", mv(E.gland_mesh(), u, v, w0 + explode))))
    gu, gv = E.INTAKE
    out.append(("grill", E.to_face("right", mv(E.grill_mesh(), gu, gv, w0 + explode))))
    rim, mesh_ = E.filter_mesh()
    out.append(("filter", E.to_face("right", mv(merge(rim), gu, gv, w0 + 1.6 + explode * 1.6))))
    out.append(("filter_mesh", E.to_face("right", mv(mesh_, gu, gv, w0 + 1.6 + explode * 1.6))))
    out.append(("collar", E.to_face("right", mv(E.collar_mesh(), E.DUCT[0], E.DUCT[1], w0 + explode))))
    du, dv = E.DUCT
    spig = E.COLLAR["flange_t"] + E.COLLAR["spigot_l"]
    path = [(du, dv, w0 + 8.0), (du, dv, w0 + spig + 40.0), (du, dv - 40, w0 + spig + 110.0),
            (du, dv - 160, w0 + spig + 150.0), (du, dv - 330, w0 + spig + 160.0)]
    duct = tube(np.array(path), 27.0, 28)
    out.append(("duct", E.to_face("right", mv(duct, 0, 0, explode))))
    return out


def top_kit(explode=0.0):
    """The fans as they hang under the top panel, one grill under each fan and
    one on the panel's outer face over it; moved up with the panel by `explode`."""
    out = []
    fm, bo = _fan()
    z_in = C.H + E.TAPE                                  # the top panel's inner face
    for x, y in E.FANS:
        zf = z_in - E.FAN_T + explode                    # inlet down, outlet (the struts) against the panel
        out.append(("fan", mv(fm, x, y, zf)))
        out.append(("fan", mv(bo, x, y, zf)))
        out.append(("grill", mv(E.grill_mesh(), x, y, zf - 1.6)))
        out.append(("grill", mv(E.grill_mesh(), x, y, C.H + E.OUT + explode)))
    return out


def drains(mode, hi=False):
    """'old': on the FL post (frame booklet); 'inner': branches only, riser
    off; 'new': through the grommets to the riser on the P-clips."""
    out = []
    dx, dy = C.DRAIN["tray_DOWN"]
    for z in C.TIERS:
        out.append(Part(C.bulkhead_mesh(dx, dy, z + C.SER), BLACKPART, lw=0.35, ang=30))
    if mode == "old":
        r = C.drain_routes()
        out += [Part(tube(P, C.TUBE_R, 12), TUBE, lw=0.35, ang=30) for P in r["branches"] + [r["riser"]]]
        out += [Part(m, INKISH if k == "tie" else FITTING, lw=0.35, ang=30) for k, m in C.drain_fittings()]
    elif mode == "inner":
        for zl in C.TIERS:
            P = np.array(E._branch_inner(zl) + [(-30.0, E.DRAIN_DY, zl - 40.0), (-40.0, E.DRAIN_DY, zl - 90.0)])
            out.append(Part(tube(P, C.TUBE_R, 12), TUBE, lw=0.35, ang=30))
        out += [Part(m, FITTING, lw=0.35, ang=30) for k, m in E.drain_fittings() if k == "elbow"][:3]
    else:
        r = E.drain_routes()
        col = HILITE if hi else TUBE
        out += [Part(tube(P, C.TUBE_R, 12), col, lw=0.35, ang=30) for P in r["branches"] + [r["riser"]]]
        out += [Part(m, FITTING, lw=0.35, ang=30) for k, m in E.drain_fittings()]
    out.append(Part(C.bucket_mesh(), np.array([0.30, 0.32, 0.34]), lw=0.35, ang=30))
    return out


def door_set(pair, side, angle=0.0, hi=False, parts=("door", "hinge_frame", "hinge_door", "spacer", "pull",
                                                      "discs", "reed_magnet", "astragal")):
    dp = E.door_parts(pair, side, angle)
    out = []
    cols = dict(door=CLEARC, hinge_frame=STEEL, hinge_door=STEEL, spacer=CLEARC, pull=BLACKPART, discs=STEEL,
                reed_magnet=WHITEP, astragal=CLEARC)
    for k in parts:
        if k in dp:
            out.append(Part(dp[k], HILITE if hi else cols[k], lw=0.4 if k == "door" else 0.3, ang=30,
                            ghost=(not hi and cols[k] is CLEARC)))
    return out


def enc(upto, hi=(), door_angle=0.0, drop=(), frame=True, drain=None):
    """Parts for the cabinet and enclosure as built after step `upto`.
    hi: names drawn in the new-part colour. drop: names left out."""
    out = list(_cab()) if frame else []
    H_ = set(hi)

    def P(name, mesh, col, lw=0.35):
        if name in drop or mesh is None or len(mesh[1]) == 0:
            return
        hi_ = name in H_
        out.append(Part(mesh, HILITE if hi_ else col, lw=lw, ang=30, ghost=(col is FROST and not hi_)))

    # drains
    mode = drain or ("old" if upto < ST["riser_off"] else "inner" if upto < ST["riser_on"] else "new")
    if "drains" not in drop:
        out += drains(mode, hi="drains" in H_)
    faces = [("back", ST["tape_back"]), ("right", ST["right"]), ("left", ST["left"]), ("top", ST["top"])]
    for f, k in faces:
        if upto >= k:
            P(f"tape_{f}", _tape(f), EPDM, 0.25)
    if upto >= ST["back_bottom"]:
        P("back_bottom", _panel("back_bottom"), FROST, 0.45)
    if upto >= ST["back_rest"]:
        P("back_middle", _panel("back_middle"), FROST, 0.45)
        P("back_upper", _panel("back_upper"), FROST, 0.45)
    if upto >= ST["battens"]:
        for s in E.SEAMS_V:
            P("battens", E.batten_mesh(s), ALU, 0.35)
    if upto >= ST["right"]:
        P("right", _panel("right"), FROST, 0.45)
        for k, m in right_kit():
            P("right_kit", m, {"filter_mesh": np.array([0.55, 0.57, 0.60]), "collar": WHITEP,
                               "duct": np.array([0.78, 0.80, 0.82])}.get(k, BLACKPART), 0.3)
    if upto >= ST["left"]:
        P("left", _panel("left"), FROST, 0.45)
        P("grommets", E.grommets_world(), BLACKPART, 0.3)
    if upto >= ST["riser_on"]:
        st_, rb = E.clips_world()
        P("clips", st_, STEEL, 0.3)
        P("clips", rb, BLACKPART, 0.3)
    if upto >= ST["top"]:
        P("top", _panel("top"), FROST, 0.45)
        for k, m in top_kit():
            P("fans", m, BLACKPART, 0.3)
        for u in E.ANTITIP_U:
            m, c = E.antitip_mesh(u)
            P("antitip", m, BLACKPART, 0.3)
            P("antitip", c, STEEL, 0.3)
    # panel fasteners
    for f, k in (("back", ST["back_bottom"]), ("right", ST["right"]), ("left", ST["left"]), ("top", ST["top"])):
        if upto < k:
            continue
        for kind, m in _fast(f):
            if f == "back":
                # screws arrive with their panel: bottom, then the rest, then the battens
                V = m[0]
                zc = V[:, 2].mean()
                if kind == "batten_screw":
                    if upto < ST["battens"]:
                        continue
                    P("batten_screws", m, STEEL, 0.25)
                    continue
                if zc > E.SEAMS_V[0] and upto < ST["back_rest"]:
                    continue
                P("back_screws" if zc <= E.SEAMS_V[0] else "back_screws2", m, STEEL, 0.25)
                continue
            if kind == "clip_screw" and upto < ST["riser_on"]:
                continue
            P(f"{f}_screws" if kind != "clip_screw" else "clip_screws", m, STEEL, 0.25)
    # doors
    if upto >= ST["frame_side"]:
        for pair in ("bottom", "top"):
            fs = E.frame_side(pair)
            P("magnets", fs["magnets"], STEEL, 0.3)
            P("strips", fs["strips"], EPDM, 0.25)
            P("reeds", fs["reeds"], WHITEP, 0.3)
    if upto >= ST["hang"]:
        for pair, side in E.DOORS:
            if f"door_{pair}_{side}" in drop:
                continue
            for p in door_set(pair, side, door_angle, hi="doors" in H_):
                out.append(p)
    return out


def lab(ax, v, p, text, dx=60, dy=0, ha="left", fs=8.8, bold=False):
    """A label with a leader from a 3D point."""
    q = v(p)
    t = (q[0] + dx, q[1] + dy)
    ax.plot([q[0], t[0] - (4 if ha == "left" else -4)], [q[1], t[1]], color=DIM, lw=0.8, zorder=320)
    ax.text(t[0], t[1], text, fontsize=fs, color=INK, ha=ha, va="center", zorder=321,
            fontweight="bold" if bold else "normal",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))


def dots(ax, v, pts, r=5.5, col=ACCENT):
    for p in pts:
        q = v(p)
        ax.add_patch(Circle(tuple(q), r, facecolor=col, edgecolor="white", lw=1.0, zorder=315))


# ============================================================ 2D: face maps
def _map_x(face, u):
    s = E.FACES[face]["size"][0]
    return s - u if face in ("left", "back") else u


def draw_face(ax, face, x0, y0, s, title, sub=""):
    """A face as seen from outside, to scale: members (light), tape (dark),
    panels' outlines, screws by kind, cutouts. Returns the drawing box."""
    fw, fh = E.FACES[face]["size"]
    X = lambda u: x0 + _map_x(face, u) * s                       # noqa: E731
    Y = lambda v: y0 + v * s                                     # noqa: E731
    for u0, v0, u1, v1 in E.members_on(face) if face != "front" else []:
        a, b = sorted((X(u0), X(u1)))
        ax.add_patch(Rectangle((a, Y(v0)), b - a, Y(v1) - Y(v0), facecolor="#e6ebee", edgecolor="none", zorder=10))
    for u0, v0, u1, v1 in E.tapes(face):
        a, b = sorted((X(u0), X(u1)))
        ax.add_patch(Rectangle((a, Y(v0)), b - a, Y(v1) - Y(v0), facecolor="#33373a", edgecolor="none", zorder=12))
    for n, (f, u0, v0, u1, v1) in E.panels().items():
        if f != face:
            continue
        a, b = sorted((X(u0), X(u1)))
        ax.add_patch(Rectangle((a, Y(v0)), b - a, Y(v1) - Y(v0), facecolor="none", edgecolor=INK, lw=0.9, zorder=14))
    if face == "back":
        for sv in E.SEAMS_V:
            ax.add_patch(Rectangle((X(E.W), Y(sv - E.BATTEN["w"] / 2)), E.W * s, E.BATTEN["w"] * s,
                                   facecolor="#b9c2c8", edgecolor=INK, lw=0.6, zorder=15, alpha=0.9))
    colk = {"panel": INK, "batten": "#4b5563", "clip": ACCENT, "antitip": OK}
    for p in E.screws(face):
        ax.add_patch(Circle((X(p["u"]), Y(p["v"])), 3.2 if p["kind"] == "panel" else 3.8,
                            facecolor="white" if p["kind"] == "panel" else colk[p["kind"]],
                            edgecolor=colk[p["kind"]], lw=0.9, zorder=17))
    for u, v, d, what in E.cutouts(face):
        if what == "feeder M5":
            ax.add_patch(Circle((X(u), Y(v)), 3.2, facecolor="white", edgecolor=OK, lw=1.1, zorder=17))
        elif d < 6:
            ax.add_patch(Circle((X(u), Y(v)), 1.4, facecolor=INK, edgecolor="none", zorder=17))
        else:
            ax.add_patch(Circle((X(u), Y(v)), d / 2 * s, facecolor="white", edgecolor=WARN, lw=1.1, zorder=16))
    for u0, v0, u1, v1, r, what in E.rect_cutouts(face):
        a, b = sorted((X(u0), X(u1)))
        ax.add_patch(FancyBboxPatch((a, Y(v0)), b - a, Y(v1) - Y(v0), boxstyle=f"round,pad=0,rounding_size={r * s}",
                                    facecolor="white", edgecolor=WARN, lw=1.1, zorder=16))
    ax.text(x0 + fw * s / 2, y0 + fh * s + 22, title, fontsize=10.2, fontweight="bold", color=INK, ha="center",
            family=TITLE_FONT)
    if sub:
        ax.text(x0 + fw * s / 2, y0 + fh * s + 8, sub, fontsize=7.8, color=DIM, ha="center")
    return (x0, y0, fw * s, fh * s)


def face_legend(ax, x, y):
    items = [("circle", INK, "white", "M5 × 16 + DIN 9021 washer"), ("circle", "#4b5563", "#4b5563", "M5 × 20, batten"),
             ("circle", ACCENT, ACCENT, "M5 × 16, P-clip"), ("circle", OK, OK, "M5 × 16, anti-tip bracket"),
             ("rect", "#33373a", "#33373a", "EPDM tape, 3/16 × 1/2 in"), ("rect", "#e6ebee", "#e6ebee", "frame behind"),
             ("big", WARN, "white", "cutout"), ("circle", OK, "white", "feeder: × 16, later × 20")]
    for i, (k, ec, fc, t) in enumerate(items):
        yy = y - i * 20
        if k == "circle":
            ax.add_patch(Circle((x + 6, yy), 4.2, facecolor=fc, edgecolor=ec, lw=1.0))
        elif k == "rect":
            ax.add_patch(Rectangle((x, yy - 4), 12, 8, facecolor=fc, edgecolor="none"))
        else:
            ax.add_patch(Circle((x + 6, yy), 6.0, facecolor=fc, edgecolor=ec, lw=1.1))
        ax.text(x + 20, yy, t, fontsize=8.4, color=INK, va="center")


# ============================================================ 2D: sections
def sec_panel_screw(ax, cx, cy, s, kind="panel", label=""):
    """True-scale section across a slot: rail, T-nut, tape on the land, panel,
    washer (or batten / clip tab), button head. (cx, cy) = the rail's face on
    the slot line."""
    from matplotlib.patches import Polygon as Poly
    outer = [(-20, 0), (-4.1, 0), (-4.1, -4.3), (-8.25, -4.3), (-8.25, -7.0), (-3.0, -12.25),
             (3.0, -12.25), (8.25, -7.0), (8.25, -4.3), (4.1, -4.3), (4.1, 0), (20, 0), (20, -18), (-20, -18)]
    ax.add_patch(Poly([(cx + u * s, cy + v * s) for u, v in outer], closed=True, facecolor="#dde3e7",
                      edgecolor=INK, lw=0.8, zorder=20))
    ax.plot([cx - 20 * s, cx + 20 * s], [cy - 18 * s, cy - 18 * s], color="white", lw=2.0, zorder=21)
    ax.add_patch(Rectangle((cx - 7.5 * s, cy - 7.9 * s), 15 * s, 3.6 * s, facecolor="#9aa6ae", edgecolor=INK,
                           lw=0.7, zorder=22))
    ax.add_patch(Rectangle((cx - 5.0 * s, cy - 9.9 * s), 10 * s, 2.0 * s, facecolor="#9aa6ae", edgecolor=INK,
                           lw=0.7, zorder=22))
    # tape on the land, panel on the tape
    if kind in ("batten", "seam"):
        for sgn in (-1, 1):
            ax.add_patch(Rectangle((cx + sgn * E.LINE_IN * s if sgn > 0 else cx - (E.LINE_IN + E.TAPE_W) * s, cy),
                                   E.TAPE_W * s, E.TAPE * s, facecolor="#33373a", edgecolor=INK, lw=0.6, zorder=23))
        g = E.SEAM_GAP / 2
        ax.add_patch(Rectangle((cx - 22 * s, cy + E.TAPE * s), (22 - g) * s, E.T_PANEL * s, facecolor="#eef1f3",
                               edgecolor=INK, lw=0.7, zorder=23))
        ax.add_patch(Rectangle((cx + g * s, cy + E.TAPE * s), (22 - g) * s, E.T_PANEL * s, facecolor="#eef1f3",
                               edgecolor=INK, lw=0.7, zorder=23))
        top = E.OUT
        if kind == "seam":
            ax.annotate("", xy=(cx - g * s, cy + (E.OUT + 2.5) * s), xytext=(cx + g * s, cy + (E.OUT + 2.5) * s),
                        arrowprops=dict(arrowstyle="<->", color=OK, lw=1.1), zorder=30)
            ax.text(cx, cy + (E.OUT + 4.5) * s, f"{E.SEAM_GAP:g} gap on the slot line", fontsize=8.2, color=OK,
                    ha="center", fontweight="bold", zorder=30)
            if label:
                ax.text(cx, cy - 25 * s, label, fontsize=8.6, color=INK, ha="center", zorder=30)
            return
        ax.add_patch(Rectangle((cx - E.BATTEN["w"] / 2 * s, cy + top * s), E.BATTEN["w"] * s, E.BATTEN["t"] * s,
                               facecolor="#c9d1d6", edgecolor=INK, lw=0.7, zorder=24))
        top += E.BATTEN["t"]
        L = 20.0
    else:
        ax.add_patch(Rectangle((cx + E.LINE_IN * s, cy), E.TAPE_W * s, E.TAPE * s, facecolor="#33373a",
                               edgecolor=INK, lw=0.6, zorder=23))
        ax.add_patch(Rectangle((cx - 22 * s, cy + E.TAPE * s), 44 * s, E.T_PANEL * s, facecolor="#eef1f3",
                               edgecolor=INK, lw=0.7, zorder=23))
        ax.add_patch(Rectangle((cx - 4.0 * s, cy + E.TAPE * s), 8.0 * s, E.T_PANEL * s, facecolor="white",
                               edgecolor="none", zorder=23.5))
        top = E.OUT
        ax.add_patch(Rectangle((cx - 7.5 * s, cy + top * s), 15 * s, E.WASH["t"] * s, facecolor="#c9d1d6",
                               edgecolor=INK, lw=0.7, zorder=24))
        top += E.WASH["t"]
        L = 16.0
    ax.add_patch(Rectangle((cx - 2.5 * s, cy + (top - L) * s), 5 * s, L * s, facecolor="#7d8890", edgecolor=INK,
                           lw=0.7, zorder=25))
    hd = [(-4.75, 0), (4.75, 0), (4.75, 0.7), (3.6, 2.1), (1.9, 2.75), (1.5, 2.75), (1.5, 1.19), (-1.5, 1.19),
          (-1.5, 2.75), (-1.9, 2.75), (-3.6, 2.1), (-4.75, 0.7)]
    ax.add_patch(Poly([(cx + u * s, cy + (top + v) * s) for u, v in hd], closed=True, facecolor="#7d8890",
                      edgecolor=INK, lw=0.7, zorder=25))
    ax.add_patch(Rectangle((cx - 2.5 * s, cy + top * s), 5 * s, 1.19 * s - 0.01, facecolor="#7d8890",
                           edgecolor="none", zorder=25.5))
    tip = top - L
    xd = cx + 24 * s
    ax.plot([cx + 3 * s, xd + 4], [cy + tip * s, cy + tip * s], color=OK, lw=0.6, ls=(0, (2, 2)), zorder=30)
    ax.plot([cx + 3 * s, xd + 4], [cy - C.SLOT_DEPTH * s, cy - C.SLOT_DEPTH * s], color=OK, lw=0.6,
            ls=(0, (2, 2)), zorder=30)
    ax.plot([xd, xd], [cy + tip * s, cy - C.SLOT_DEPTH * s], color=OK, lw=1.3, zorder=30)
    for yy in (cy + tip * s, cy - C.SLOT_DEPTH * s):
        ax.plot([xd - 4, xd + 4], [yy, yy], color=OK, lw=1.3, zorder=30)
    ax.text(xd + 8, cy + (tip - C.SLOT_DEPTH) / 2 * s, f"{C.SLOT_DEPTH + tip:.1f} clear", fontsize=8.0, color=OK,
            va="center", fontweight="bold", zorder=30)
    if label:
        ax.text(cx, cy - 25 * s, label, fontsize=8.6, color=INK, ha="center", zorder=30)


def sec_door_plan(ax, ox, oy, s):
    """Plan section at the left door's hinge, true scale, looking down: the FL
    post, the side panel, spacer, leaves, knuckle, VHB, door, weatherstrip."""
    from matplotlib.patches import Polygon as Poly
    X = lambda x: ox + x * s                                     # noqa: E731
    Y = lambda y: oy + y * s                                     # noqa: E731
    pts = [(X(px), Y(py)) for px, py in C.profile_outline()]
    ax.add_patch(Poly(pts, closed=True, facecolor="#dde3e7", edgecolor=INK, lw=0.7, zorder=20))
    ax.add_patch(Circle((X(20), Y(20)), C.BORE_DRAW / 2 * s, facecolor="white", edgecolor=INK, lw=0.6, zorder=21))
    # side panel on its tape
    ax.add_patch(Rectangle((X(-E.TAPE), Y(E.LINE_IN + 20)), E.TAPE * s, E.TAPE_W * s, facecolor="#33373a",
                           edgecolor="none", zorder=21))
    ax.add_patch(Rectangle((X(-E.OUT), Y(0)), E.T_PANEL * s, 46 * s, facecolor="#eef1f3", edgecolor=INK, lw=0.7,
                           zorder=22))
    # spacer, frame leaf, door leaf, VHB, door
    a_ = E.PIN_U + E.KNUCKLE_R + 0.3
    ax.add_patch(Rectangle((X(a_), Y(-E.SPACER_T)), (E.PIN_U + E.LEAF_W - a_) * s, E.SPACER_T * s,
                           facecolor="#d6e9f5", edgecolor=INK, lw=0.6, zorder=22))
    for k, y0 in enumerate((-E.SPACER_T - E.LEAF_T, -E.SPACER_T - 2 * E.LEAF_T)):
        ax.add_patch(Rectangle((X(E.PIN_U + E.KNUCKLE_R), Y(y0)), (E.LEAF_W - E.KNUCKLE_R) * s, E.LEAF_T * s,
                               facecolor="#9aa6ae", edgecolor=INK, lw=0.5, zorder=23))
    ax.add_patch(Circle((X(E.PIN_U), Y(-E.PIN_W)), E.KNUCKLE_R * s, facecolor="#9aa6ae", edgecolor=INK, lw=0.6,
                        zorder=23))
    ax.add_patch(Circle((X(E.PIN_U), Y(-E.PIN_W)), 0.6 * s, facecolor=INK, edgecolor="none", zorder=24))
    x0d = E.door_x("L")[0]
    ax.add_patch(Rectangle((X(E.PIN_U + E.KNUCKLE_R), Y(-E.GAP_F)), (E.LEAF_W - E.KNUCKLE_R) * s, E.VHB_T * s,
                           facecolor=ACCENT, edgecolor="none", zorder=23))
    ax.add_patch(Rectangle((X(x0d), Y(-E.GAP_F - E.DOOR_T)), (60 - x0d) * s, E.DOOR_T * s, facecolor="#d6e9f5",
                           edgecolor=INK, lw=0.7, zorder=22))
    xs0 = E.strips("bottom")[2][0]
    ax.add_patch(Rectangle((X(xs0), Y(-E.GAP_F)), E.STRIP["w"] * s, E.GAP_F * s, facecolor="#33373a",
                           edgecolor="none", zorder=22))
    # screw on the slot line
    ax.add_patch(Rectangle((X(20 - 1.5), Y(-E.SPACER_T - E.LEAF_T - 0.01)), 3 * s, (12 - 1.7) * s * -1 * -1,
                           facecolor="none", edgecolor="none"))
    ax.add_patch(Rectangle((X(19.0), Y(-E.SPACER_T - E.LEAF_T)), 2.0 * s, 1.1 * s, facecolor="white",
                           edgecolor=INK, lw=0.5, zorder=26))
    ax.add_patch(Poly([(X(17), Y(-E.SPACER_T - E.LEAF_T)), (X(23), Y(-E.SPACER_T - E.LEAF_T)),
                       (X(21.5), Y(-E.SPACER_T - E.LEAF_T + 1.7)), (X(21.5), Y(-E.SPACER_T - E.LEAF_T + 12)),
                       (X(18.5), Y(-E.SPACER_T - E.LEAF_T + 12)), (X(18.5), Y(-E.SPACER_T - E.LEAF_T + 1.7))],
                      closed=True, facecolor="#7d8890", edgecolor=INK, lw=0.6, zorder=25))
    ax.add_patch(Rectangle((X(20 - 7.5), Y(4.3)), 15 * s, 3.6 * s, facecolor="#9aa6ae", edgecolor=INK, lw=0.6,
                           zorder=24))


def sec_catch(ax, ox, oy, s):
    """Side section through F0 at a magnet, true scale: front to the left.
    Page x = -y (the door's outer face leftmost), page y = z."""
    from matplotlib.patches import Polygon as Poly
    X = lambda y: ox + y * s                                     # noqa: E731
    Y = lambda z: oy + z * s                                     # noqa: E731
    pts = [(X(py), Y(px)) for px, py in C.profile_outline()]
    ax.add_patch(Poly(pts, closed=True, facecolor="#dde3e7", edgecolor=INK, lw=0.7, zorder=20))
    ax.add_patch(Circle((X(20), Y(20)), C.BORE_DRAW / 2 * s, facecolor="white", edgecolor=INK, lw=0.6, zorder=21))
    zc = 20.0
    ax.add_patch(Rectangle((X(-E.MAG["t"]), Y(zc - E.MAG["d"] / 2)), E.MAG["t"] * s, E.MAG["d"] * s,
                           facecolor="#9aa6ae", edgecolor=INK, lw=0.6, zorder=23))
    ax.add_patch(Rectangle((X(-E.GAP_F), Y(zc - E.DISC["d"] / 2)), E.DISC["t"] * s,
                           E.DISC["d"] * s, facecolor="#6b7780", edgecolor=INK, lw=0.6, zorder=23))
    ax.add_patch(Rectangle((X(-E.GAP_F - E.DOOR_T), Y(-8)), E.DOOR_T * s, 56 * s, facecolor="#d6e9f5",
                           edgecolor=INK, lw=0.7, zorder=22))
    zs0, zs1 = E.strips("bottom")[0][1], E.strips("bottom")[0][3]
    ax.add_patch(Rectangle((X(-E.GAP_F), Y(zs0)), E.GAP_F * s, (zs1 - zs0) * s, facecolor="#33373a",
                           edgecolor="none", zorder=22))
    ax.add_patch(Poly([(X(-E.MAG["t"]), Y(zc - 3.0)), (X(-E.MAG["t"]), Y(zc + 3.0)), (X(-E.MAG["t"] + 1.7), Y(zc + 1.5)),
                       (X(12 - E.MAG["t"]), Y(zc + 1.5)), (X(12 - E.MAG["t"]), Y(zc - 1.5)),
                       (X(-E.MAG["t"] + 1.7), Y(zc - 1.5))], closed=True, facecolor="#7d8890",
                      edgecolor=INK, lw=0.5, zorder=24))
    ax.add_patch(Rectangle((X(4.3), Y(zc - 7.5)), 3.6 * s, 15 * s, facecolor="#9aa6ae", edgecolor=INK,
                           lw=0.5, zorder=24))
    ax.add_patch(Rectangle((X(-E.MAG["t"]), Y(zc - 1.0)), 1.1 * s, 2.0 * s, facecolor="white", edgecolor=INK,
                           lw=0.5, zorder=25))


# ============================================================ cover
COVER = os.environ.get("MAAG_COVER", os.path.join(_HERE, "..", "gantry", "cover", "cover.png"))


def p_cover(pdf):
    """The Maag cover render full-bleed on top, title block underneath, as on every booklet."""
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
    ax.text(50, y0 - 100, f"Enclosure assembly instructions, {REV}.  Frosted panels on the back, sides and top, "
                          "four clear doors.", fontsize=12.0, color=DIM, va="center")
    ax.text(1102, y0 - 46, f"{NSTEPS} steps  ·  tools  ·  every hole", fontsize=11, color=INK, ha="right",
            va="center")
    ax.text(1102, 26, f"Design {DESIGN}. The Maag cover render, the same on every booklet. Every drawing inside "
                      "comes from enclosure.py and cabinet.py; the DXFs come from the same model.",
            fontsize=7.6, color=DIM, ha="right")
    pdf.savefig(fig); fig.savefig(f"{OUT}/d_000_cover.png", dpi=130); plt.close(fig)


# ============================================================ overview
@page
def p_overview(pdf):
    fig, ax = new_page(None, "The enclosure  ·  what goes where",
                       "Six frosted panels, four clear doors. Everything surface mounted on the frame's outer faces.")
    parts = enc(NSTEPS)
    v1 = scene(ax, parts, (300, 470), (450, 600), MM=view(212, 16), px=1.5, clip=(24, 150, 575, 772))
    v2 = scene(ax, parts, (850, 470), (450, 600), MM=view(32, 16), px=1.5, clip=(575, 150, 1126, 772))
    lab(ax, v1, (-E.OUT, 300, 1500), "left panel", dx=-50, ha="right", bold=True)
    lab(ax, v1, (-20, E.RISER[1], 700), "drain riser,\non P-clips", dx=-60, ha="right")
    for txt, z in (("top pair", 1400.0), ("bottom pair", 640.0)):
        q = v1((350.0, -E.GAP_F - 5, z))
        ax.text(q[0], q[1], txt, fontsize=9.2, fontweight="bold", color=INK, ha="center", va="center", zorder=330,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none"))
    lab(ax, v1, (E.FANS[0][0], E.FANS[0][1], C.H + E.OUT + 2), "exhaust fans, under the top", dx=110, dy=-34)
    lab(ax, v2, (E.W / 2, C.D + E.OUT, E.SEAMS_V[1]), "seam batten", dx=150, dy=30)
    lab(ax, v2, (E.W / 2, C.D + E.OUT, E.SEAMS_V[0]), "seam batten", dx=150, dy=-20)
    lab(ax, v2, (C.W + E.OUT, E.INTAKE[0], E.INTAKE[1]), "filtered intake", dx=-80, dy=-40, ha="right")
    lab(ax, v2, (C.W + E.OUT, E.DUCT[0], E.DUCT[1]), "humidifier duct", dx=-90, dy=10, ha="right")
    lab(ax, v2, (C.W + E.OUT, E.GLANDS[1][0], E.GLANDS[1][1]), "cable glands", dx=-90, ha="right")
    lab(ax, v2, (E.ANTITIP_U[1], C.D - 20, C.H + 30), "anti-tip, to the wall", dx=60, dy=40)
    ax.text(300, 160, "from the front left", fontsize=9, color=DIM, ha="center")
    ax.text(850, 160, "from the back right", fontsize=9, color=DIM, ha="center")
    body(ax, "Back, sides and top: 1/8 in frosted polycarbonate (TUFFAK GP Matte), cut and drilled by A&C Plastics "
             "from the DXFs. Doors: 4.5 clear polycarbonate,\nSendCutSend. Every panel sits on EPDM foam tape beside "
             "each slot and is held by M5 screws into drop-in T-nuts, never more than 300 apart.\nFit order: back, "
             "right, left, top, doors. The fans pull air out of the top; it comes in through the filter low on the "
             "right. The gantry is not drawn.", fs=9.4)
    save(fig, ax, pdf, "00a_overview")


# ============================================================ parts
def _flat_panel(name):
    face, u0, v0, u1, v1 = E.panels()[name]
    V, F = E.panel_mesh(name, w0=0.0)
    f = E.FACES[face]
    M = np.array([f["eu"], f["ev"], f["ew"]], float)
    loc = (V - np.asarray(f["O"], float)) @ np.linalg.inv(M)
    return (loc - np.array([u0, v0, 0.0]), F)


def _flat_door(pair, side):
    from kit3d import extrude, circle_pts
    holes = [circle_pts(E.PULL["screw"] / 2, 32, x, z) for x, z in E.pull_holes(pair, side)]
    return extrude(E.door_outline(pair, side), E.DOOR_T, holes=holes)


@page
def p_parts(pdf):
    fig, ax = new_page(None, "Enclosure  ·  parts",
                       "Count everything first. Quantities cover the complete enclosure.")
    from kit3d import extrude, circle_pts
    sp_o, sp_s = E.spacer_outline()
    spacer = extrude(sp_o, E.SPACER_T, holes=[sp_s[::-1]])
    hinge = merge(box(E.LEAF_W, E.LEAF_T, 200.0, c=(0, 0, 0)), box(E.LEAF_W, E.LEAF_T, 200.0, c=(-E.LEAF_W, 0, 0)),
                  mv(cylinder(E.KNUCKLE_R, 200.0, n=20), 0, E.LEAF_T / 2, 0))
    from kit3d import revolve
    cup = revolve([(0, 0), (E.MAG["d"] / 2, 0), (E.MAG["d"] / 2, E.MAG["t"]), (3.0, E.MAG["t"]),
                   (1.7, E.MAG["t"] - 1.7), (1.7, 0)], n=48)
    rim, fmesh = E.filter_mesh()
    fm, bo = _fan()
    items = [("Side panels, frosted", "2", _flat_panel("left"), FROST),
             ("Back panels, frosted", "3", _flat_panel("back_upper"), FROST),
             ("Top panel, frosted", "1", _flat_panel("top"), FROST),
             ("Doors, clear 4.5", "4", _flat_door("bottom", "L"), CLEARC),
             ("Seam batten, 5052", "4", mv(E.batten_mesh(E.SEAMS_V[0]), 0, 0, 0), ALU),
             ("Hinge spacer, clear 3.0", "8", spacer, CLEARC),
             ("Astragal, clear 3.0", "2", box(40.0, 300.0, 3.0), CLEARC),
             ("Piano hinge, 1 ft", "8", hinge, STEEL),
             ("Cup magnet Ø16, M3", "8", cup, STEEL),
             ("Exhaust fan NF-F12", "2", merge(fm, bo), BLACKPART),
             ("Fan grill NA-FG1-12", "5", E.grill_mesh(), BLACKPART),
             ("Dust filter 120", "1", merge(rim, fmesh), BLACKPART),
             ("Duct collar, printed", "1", E.collar_mesh(), WHITEP),
             ("Cable gland PG21", "3", E.gland_mesh(), BLACKPART),
             ("Grommet 7/8 in", "3", E.grommet_mesh(), BLACKPART),
             ("P-clip 5/8 in", "5", E.clip_mesh()[0], STEEL)]
    for i, (nm, q, m, col) in enumerate(items):
        r, c = divmod(i, 4)
        cx, cy = 96 + c * 262, 712 - r * 136
        MMi = iso_matrix(30, 30)
        scene(ax, [Part(m, col, ang=30, lw=0.5, ghost=col is FROST)], (cx + 20, cy + 8), (150, 78), MM=MMi,
              clip=(cx - 74, cy - 38, cx + 114, cy + 54))
        ax.text(cx - 60, cy - 50, nm, fontsize=8.6, color=INK, va="center")
        ax.text(cx - 60, cy - 68, f"{q}×", fontsize=9.8, color=ACCENT, fontweight="bold", va="center")
    tl = E.tape_lengths()
    ax.text(60, 168, "Also, no picture needed:", fontsize=9.6, fontweight="bold", color=INK)
    rows = [f"EPDM foam strip 3/16 × 1/2 in, 50 ft  ×3  ({tl['panel_tape_m']:.1f} m used)",
            f"EPDM weatherstrip 5/16 × 1/4 in, 17 ft  ×2  ({tl['door_strip_m']:.1f} m used)",
            "VHB 4905 tape, 1/2 in  ·  steel discs Ø16 × 1, adhesive  ×8",
            "Door pulls, 96 centres  ×4  ·  reed switches 7939WG  ×4 (BOM G047)",
            "Anti-tip kit, steel cable  ×2  ·  neutral silicone (from the frame build)"]
    for i, t in enumerate(rows):
        ax.text(60 + (i // 3) * 520, 146 - (i % 3) * 18, t, fontsize=8.6, color=INK)
    ax._body_y = 60.0
    save(fig, ax, pdf, "00b_parts")


@page
def p_fasteners(pdf):
    fig, ax = new_page(None, "Enclosure  ·  fasteners",
                       "Every screw in the build. Lay them out in labelled pots first.")
    cnt = E.counts()
    items = [("M5 × 16 button head  ·  panels, clips", str(cnt["M5 x 16 button head"]),
              lambda: [(E.button5(16, detail=True), STEEL)]),
             ("DIN 9021 washer M5  ·  15 OD", str(cnt["DIN 9021 M5 washer"]), lambda: [(E.washer9021(), STEEL)]),
             ("M5 drop-in T-nut, hammer head", str(cnt["M5 drop-in T-nut"]), lambda: [(E.tnut(5), STEEL)]),
             ("M5 × 20 button head  ·  battens", str(cnt["M5 x 20 button head"]),
              lambda: [(E.button5(20, detail=True), STEEL)]),
             ("M3 × 12 flat head  ·  hinges, magnets", "40+", lambda: [(E.flat3(12, detail=True), STEEL)]),
             ("M3 drop-in T-nut", "40+", lambda: [(E.tnut(3), STEEL)]),
             ("M4 × 40 button head  ·  fans", "8", lambda: [(C.button_head(4, 40, detail=True), STEEL)]),
             ("M4 × 16 button head  ·  grill, collar", "7", lambda: [(C.button_head(4, 16, detail=True), STEEL)]),
             ("M4 nyloc + 2 washers", "15", lambda: C.HW.nyloc_parts(4))]
    for i, (nm, q, fn_) in enumerate(items):
        r, c = divmod(i, 3)
        cx, cy = 96 + c * 352, 700 - r * 112
        el = 12 if "flat head" in nm else 32
        scene(ax, [Part(m, col, ang=30, lw=0.5) for m, col in fn_()], (cx, cy), (78, 78), MM=iso_matrix(30, el),
              clip=(cx - 50, cy - 50, cx + 50, cy + 50), px=7.0)
        ax.text(cx + 60, cy + 11, nm, fontsize=8.3, color=INK, va="center")
        ax.text(cx + 60, cy - 11, f"{q}×", fontsize=10.0, color=ACCENT, fontweight="bold", va="center")
    ax.text(60, 386, "Hinges: one M3 in every hole of the frame leaf (count them on yours; the drawings show four a "
                     "hinge). Buy 50 M3 flat heads and 50 M3 T-nuts.", fontsize=9.2, color=INK)
    ax.text(60, 364, "Pulls come with their own screws: use M4 × 10 instead, the door is only 4.5 thick. Drop-in "
                     "T-nuts must be the kind that turns into the slot as you tighten.", fontsize=9.2, color=INK)
    for k, (kind, lab_) in enumerate((("panel", "a panel screw  ·  M5 × 16"), ("batten", "a seam  ·  M5 × 20"))):
        sec_panel_screw(ax, 300 + k * 520, 236, 4.2, kind, lab_)
    st = E.screw_stack()
    body(ax, f"Tape squeezed from 4.8 to {E.TAPE}, panel {E.T_PANEL}, washer {E.WASH['t']}: an M5 × 16 reaches "
             f"{st['panel']['reach']:.1f} below the face, {st['panel']['past_lip']:.1f} past the lips into\nthe "
             f"nut and {st['panel']['spare']:.1f} short of the slot floor. Never let a screw bottom: it feels tight "
             "and clamps nothing.", fs=9.2, color=WARN)
    save(fig, ax, pdf, "00c_fasteners")


# ============================================================ tools
def _tools():
    import tools_lib as T
    from tools_page import hex_key, spanner

    def keys():
        out = []
        for i, (af, L1, L2) in enumerate(((2.0, 100, 18), (2.5, 112, 20), (3.0, 125, 23))):
            for m, c in hex_key(af, L1, L2):
                out.append((mv(m, 0, 0, -i * 9.0), c))
        return out

    def spanner7():
        return spanner(7.0, 8.0, 110.0)

    return [
        (keys, "Hex keys, ball end", "2 · 2.5 · 3 mm, long series",
         "3: every M5, 4 to 13  ·  2.5: M4, 7, 12, 14\n2: the M3 flat heads, 15, 16", (30, 34)),
        (spanner7, "Spanner", "7 mm", "the M4 nylocs inside: fans,\ngrill, collar, 7 and 12", (20, 40)),
        (T.calipers, "Calipers", "150 mm, digital", "the hinge's hole line, 1;\nthe centre gap, 17", (20, 45)),
        (T.tape_measure, "Tape measure", "5 m", "T-nut positions off the face maps,\n3 to 13", (32, 26)),
        (T.utility_knife, "Utility knife", "18 mm snap-off, and scissors", "tape and weatherstrip ends,\n3, 8, 10, 13, 15",
         (25, 30)),
        (T.flush_cutters, "Side cutters", "125 mm, flush cut", "the riser's zip ties, 9", (25, 40)),
        (T.ipa_and_cloth, "Isopropyl alcohol", "and microfibre cloths", "every land before tape, every\nbond before "
                                                                          "VHB, 2 and 14", (25, 28)),
        (T.caulking_gun, "Caulking gun", "and neutral-cure silicone", "the post tops, 2", (28, 18)),
        (T.kettle_and_mug, "Hot water", "a kettle and a mug", "softening the drain tube\nends, 9 and 11", (25, 18)),
    ]


@page
def p_tools(pdf):
    fig, ax = new_page(None, "Tools",
                       f"Everything the {NSTEPS} steps need. Metric throughout; the tubing and tapes are sold in inches.")
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
    ax.text(330, 200, "And a step ladder for the top, a soft surface\nto lay panels on, painter's tape for labels, "
                      "and\na helper for every panel and door: they are\nlarge, light and flex.",
            fontsize=9.6, color=INK, va="top", linespacing=1.5)
    ax._body_y = 60.0
    save(fig, ax, pdf, "00d_tools")


# ============================================================ face maps
@page
def p_faces1(pdf):
    fig, ax = new_page(None, "Where every screw goes  ·  sides and back",
                       "Each face as you see it from outside. Drop a T-nut in the slot under every circle.")
    s = 0.316
    draw_face(ax, "left", 60, 150, s, "LEFT", "front edge on the right")
    draw_face(ax, "back", 268, 150, s, "BACK", "seen from behind")
    draw_face(ax, "right", 734, 150, s, "RIGHT", "front edge on the left")
    face_legend(ax, 945, 720)
    n = {f: len(E.screws(f)) + len([c for c in E.cutouts(f) if c[3] == "feeder M5"]) for f in ("left", "right", "back")}
    note(ax, 945, 560, f"T-nuts: left {n['left']}, right {n['right']},\nback {n['back']}. The P-clips (orange)\n"
                       "are panel screws too: they go\nin at step 11.", fs=8.8, color=INK)
    ax._body_y = 60.0
    body(ax, "Every circle is on a slot centreline, 20 in from an edge or on a rail's middle. Seams: the back's "
             "three panels meet on B1 and B2 with a 6 gap; the\nbatten screws pass through the gap. Cutouts: glands, "
             "intake, duct and the harvest feeder's two openings on the right; the three drain grommets on the left.",
         fs=9.0)
    save(fig, ax, pdf, "00e_faces1")


@page
def p_faces2(pdf):
    fig, ax = new_page(None, "Where every screw goes  ·  top and front",
                       "The top seen from above, front edge down. The front: what the doors close on.")
    s = 0.36
    draw_face(ax, "top", 60, 520, s, "TOP", "front edge at the bottom")
    face_legend(ax, 620, 744)
    # front: posts and rails, hinges, magnets, strips, switches
    x0, y0, sf = 640, 118, 0.24
    X = lambda x: x0 + x * sf                                    # noqa: E731
    Y = lambda z: y0 + z * sf                                    # noqa: E731
    for m in C.members():
        lo, hi = m.bbox()
        if lo[1] > 1:
            continue
        ax.add_patch(Rectangle((X(lo[0]), Y(lo[2])), (hi[0] - lo[0]) * sf, (hi[2] - lo[2]) * sf, facecolor="#e6ebee",
                               edgecolor="none", zorder=10))
    for pair in ("bottom", "top"):
        for xa, za, xb, zb in E.strips(pair):
            ax.add_patch(Rectangle((X(xa), Y(za)), (xb - xa) * sf, (zb - za) * sf, facecolor="#33373a",
                                   edgecolor="none", zorder=12))
        for side in ("L", "R"):
            x0d, x1d = E.door_x(side)
            z0d, z1d = E.door_z(pair)
            ax.add_patch(Rectangle((X(x0d), Y(z0d)), (x1d - x0d) * sf, (z1d - z0d) * sf, facecolor="none",
                                   edgecolor="#5b8db8", lw=0.8, ls=(0, (4, 2)), zorder=13))
            for z0h, z1h in E.hinge_z(pair):
                xh = E.PIN_U if side == "L" else E.W - E.PIN_U
                ax.add_patch(Rectangle((X(xh) - 2.5, Y(z0h)), 5, (z1h - z0h) * sf, facecolor="#9aa6ae",
                                       edgecolor=INK, lw=0.5, zorder=14))
            for z in E.MAG_Z[pair]:
                ax.add_patch(Circle((X(E.MAG_X[side]), Y(z)), 3.6, facecolor=ACCENT, edgecolor="white", lw=0.8,
                                    zorder=15))
            xr = E.REED_X[side]
            ax.add_patch(Rectangle((X(xr - 32), Y(E.REED_RAIL[pair] - 13)), 64 * sf, 13 * sf, facecolor=OK,
                                   edgecolor="none", zorder=15))
            z0a, z1a = E.astragal_span(pair)
        ax.add_patch(Rectangle((X(E.W / 2 - 20), Y(z0a)), 40 * sf, (z1a - z0a) * sf, facecolor="#d6e9f5",
                               edgecolor="#5b8db8", lw=0.6, zorder=13))
    ax.text(X(E.W / 2), Y(E.H) + 22, "FRONT", fontsize=10.2, fontweight="bold", color=INK, ha="center",
            family=TITLE_FONT)
    ax.text(X(E.W / 2), Y(E.H) + 8, "the frame face, doors dashed", fontsize=7.8, color=DIM, ha="center")
    items = [("rect", "#9aa6ae", "hinge, frame leaf on its spacer"), ("dot", ACCENT, "cup magnet, on the slot line"),
             ("rect", "#33373a", "weatherstrip 5/16 × 1/4 in"), ("rect", OK, "reed switch, under the rail"),
             ("rect", "#d6e9f5", "astragal, on the right door")]
    for i, (k, c, t) in enumerate(items):
        yy = 420 - i * 20
        if k == "dot":
            ax.add_patch(Circle((66, yy), 4.2, facecolor=c, edgecolor="white"))
        else:
            ax.add_patch(Rectangle((60, yy - 4), 12, 8, facecolor=c, edgecolor="none"))
        ax.text(80, yy, t, fontsize=8.4, color=INK, va="center")
    note(ax, 60, 300, "Bottom pair: magnets on F0 and F1,\nswitch under F2. Top pair: magnets on\nF3 and F4, switch "
                      "under F4. F2 carries\nthe split, so its slot holds nothing.", fs=8.8, color=INK)
    ax._body_y = 60.0
    body(ax, f"Top: {len(E.screws('top'))} T-nuts, none on the post ends (no slot there); the two green ones hold the "
             "anti-tip brackets. Fans at x 420 and 977, 310 back from the\nfront, hung inside: over the folded arm, clear of the "
             "gantry's mast. Front: the doors meet 3 apart at the middle; the right door's astragal covers the gap.",
         fs=9.0)
    save(fig, ax, pdf, "00f_faces2")


# ============================================================ sections
@page
def p_sections(pdf):
    fig, ax = new_page(None, "How it closes  ·  the door, in section",
                       "True scale, looking down on the bottom left door's hinge. Every number is the model's.")
    s = 6.4
    ox, oy = 250.0, 470.0
    panel(ax, 40, 300, 700, 470, z=5)
    sec_door_plan(ax, ox, oy, s)
    X = lambda x: ox + x * s                                     # noqa: E731
    Y = lambda y: oy + y * s                                     # noqa: E731
    gb = E.gap_budget()
    xs0 = E.strips("bottom")[2][0]
    labels = [((-E.OUT + 1.5, 36), (120, 700), "side panel\non its tape", "right"),
              ((20, 34), (470, 735), "FL post, its front slot", "left"),
              ((26, -1.5), (520, 560), f"spacer, clear PC {E.SPACER_T}", "left"),
              ((E.PIN_U, -E.PIN_W), (200, 380), "piano hinge:\nknuckle, two leaves", "right"),
              ((24, -E.GAP_F + 0.25), (300, 340), "VHB 4905, 0.5", "right"),
              ((50, -E.GAP_F - E.DOOR_T / 2), (560, 360), f"door, clear PC {E.DOOR_T}", "left"),
              ((xs0 + 4, -E.GAP_F / 2), (560, 500), "weatherstrip,\nsqueezed 11 %", "left"),
              ((20, 6), (470, 650), "M3 T-nut, M3 × 12 flat head", "left")]
    for (px, py), (tx, ty), t, ha in labels:
        ax.plot([X(px), tx + (-6 if ha == "left" else 6)], [Y(py), ty], color=DIM, lw=0.7, zorder=40)
        ax.text(tx, ty, t, fontsize=8.6, color=INK, ha=ha, va="center", zorder=41, linespacing=1.3,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    xd = X(64)
    ax.annotate("", xy=(xd, Y(0)), xytext=(xd, Y(-E.GAP_F)), arrowprops=dict(arrowstyle="<->", color=OK, lw=1.2),
                zorder=40)
    ax.plot([X(40), xd + 6], [Y(0), Y(0)], color=OK, lw=0.6, ls=(0, (2, 2)), zorder=39)
    ax.text(xd + 8, Y(-E.GAP_F / 2), f"{E.GAP_F:.2f}", fontsize=9, color=OK, va="center", fontweight="bold",
            zorder=41)
    ax.text(52, 316, "the door's outer face is at the bottom; inside the cabinet at the top", fontsize=8.2, color=DIM)
    rows = [("Hinge stack", f"spacer {E.SPACER_T} + leaves 2 × {E.LEAF_T:.2f} + VHB {E.VHB_T} = {E.GAP_F:.2f}"),
            ("Catch", f"cup magnet {E.MAG['t']} + steel disc {E.DISC['t']}: {gb['air_at_magnet']:.2f} of air"),
            ("Seal", f"weatherstrip {E.STRIP['t']} to {E.GAP_F:.2f}: light,\nso the magnets win"),
            ("Astragal", f"{gb['astragal_to_frame']:.2f} clear of the rails,\n{gb['astragal_to_left_door']} "
                         "under the left door"),
            ("Swing", f"{swing_max('bottom', 'L'):.0f}° before the door meets the post")]
    for i, (a, b) in enumerate(rows):
        y = 750 - i * 58
        ax.text(770, y, a, fontsize=9.8, fontweight="bold", color=INK, va="center")
        ax.text(770, y - 12, b, fontsize=8.4, color=DIM, va="top", linespacing=1.3)
    panel(ax, 770, 150, 340, 300, z=5)
    sec_catch(ax, 870, 220, 4.4)
    ax.text(782, 432, "the catch on F0, in section", fontsize=8.6, color=DIM, zorder=40)
    for (py, pz), (tx, ty), t in (((-E.GAP_F - E.DOOR_T / 2, 44), (820, 412), "door"),
                                    ((-E.GAP_F + 0.5, 14), (820, 172), "steel disc"),
                                    ((-2.2, 14), (990, 172), "cup magnet, M3 into a T-nut"),
                                    ((-2.8, 32), (990, 412), "weatherstrip, F0's upper land")):
        q = (870 + py * 4.4, 220 + pz * 4.4)
        ax.plot([q[0], tx], [q[1], ty], color=DIM, lw=0.7, zorder=40)
        ax.text(tx, ty, t, fontsize=8.2, color=INK, ha="center", va="center", zorder=41,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))
    body(ax, f"The hinge's leaf holes sit {E.HOLE_LINE} from its pin, so with the pin {E.PIN_U:.1f} in from the "
             "post's outer face the screws land on the slot line. If yours measure\nother than 9.5 (step 1), the "
             "spacer's slot still takes them from 8 to 11; the door then sits that much further in or out, and the "
             "centre gap\nchanges by twice the difference. Open the left door of a pair first: its edge is over the "
             "right door's astragal.", fs=9.2)
    save(fig, ax, pdf, "00g_sections")


# ============================================================ 1
@page
def s1(pdf):
    fig, ax = new_page(1, "Before you start",
                       "The cabinet finished to the frame and gantry booklets. Five checks, then label everything.")
    rows = [("Frame Rev A done", "Step 21 of the frame booklet signed off: square, plumb, drains water-tested."),
            ("Gantry in", "Gantry Rev E finished and homed. The panels close it in: no reaching in from the back "
             "after step 5."),
            ("Parts counted", "Six frosted panels, four doors, eight spacers, two astragals, four battens: against "
             "the parts page."),
            ("Hinge measured", f"Calipers from the pin to the centre of a hole: {E.HOLE_LINE} expected, 8 to 11 works "
             "(page 'How it closes')."),
            ("Panels labelled", "Painter's tape on each, its name and OUT on the outer face. Keep the film on until "
             "it is on the cabinet.")]
    checkbox_rows(ax, rows, y0=690, dy=92)
    body(ax, "Work in this order: back (from the inside out, while you can still reach round it), right, left, "
             "top, then the doors. Polycarbonate\nscratches easily and flexes: lay panels on a blanket, carry them on "
             "edge, two people for anything over 1 m.", fs=10.0)
    save(fig, ax, pdf, "01")


# ============================================================ 2
@page
def s2(pdf):
    fig, ax = new_page(2, "Clean every land, seal the post tops",
                       "Tape and VHB stick to clean aluminium only. The post tops are the one leak the tape misses.")
    parts = enc(1, drop=("drains",))
    MMv = view(212, 34)
    v = scene(ax, parts, (330, 462), (520, 600), MM=MMv, px=1.6, clip=(24, 150, 610, 772))
    corners = [(20.0, 20.0), (C.W - 20.0, 20.0), (20.0, C.D - 20.0), (C.W - 20.0, C.D - 20.0)]
    dots(ax, v, [(x, y, C.H) for x, y in corners], r=7)
    # inset: a post top, the two inward slots
    lo, hi = (-10, -10, C.H - 120), (140, 140, C.H + 10)
    det = FB.cab(99, lo=lo, hi=hi)
    vi = inset(ax, 640, 380, 460, 380, det, view(212, 46), focus=fbox([0, 0, C.H - 80], [90, 90, C.H]),
               label="FL from above: fill the two inward slot ends")
    for p in ((40.0, 20.0, C.H), (20.0, 40.0, C.H)):
        q = vi(p)
        ax.add_patch(Circle(tuple(q), 9, facecolor="none", edgecolor=ACCENT, lw=2.0, zorder=330))
    tag(ax, 640, 300, "Isopropyl alcohol, lint-free cloth", hi=False)
    tag(ax, 640, 256, "Neutral-cure silicone, a dab at each post top", 8, hi=True)
    tool(ax, 640, 206, "caulking gun")
    body(ax, "Wipe the outer face of every post and outer rail, both lands either side of each slot, with alcohol "
             "until the cloth comes away clean. At\neach post top, push a dab of silicone into the two slot ends that "
             "face into the cabinet and strike it flush with the end: under the top panel\nthose slot ends would "
             "otherwise let air round the tape. Let it skin over (an hour) before step 13.")
    save(fig, ax, pdf, "02")


# ============================================================ 3
@page
def s3(pdf):
    fig, ax = new_page(3, "Back  ·  tape",
                       "EPDM strip on the land beside every slot, on the side toward the bay; both lands on B1 and B2.")
    parts = enc(3, hi=("tape_back",), drop=("drains",))
    MMv = view(*BACKV)
    v = scene(ax, parts, (330, 462), (520, 600), MM=MMv, px=1.6, clip=(24, 150, 610, 772))
    for k, lv in enumerate(C.LEVELS):
        q = v((C.W + 70, C.D, lv + 20))
        ax.text(q[0], q[1], f"B{k}", fontsize=8.6, fontweight="bold", color=INK, va="center", ha="right",
                zorder=320)
    panel(ax, 640, 300, 470, 470, z=5)
    sec_panel_screw(ax, 875, 560, 6.5, "panel", "")
    ax.text(652, 750, "one rail, in section, once the panel is on", fontsize=8.6, color=DIM, zorder=330)
    ax.text(875, 405, f"strip {E.TAPE_W} wide, {E.LINE_IN} off the slot line,\nsqueezed from 4.8 to {E.TAPE}",
            fontsize=8.6, color=INK, ha="center", zorder=330)
    tag(ax, 640, 260, "EPDM foam strip 3/16 × 1/2 in", hi=True)
    tool(ax, 640, 210, "utility knife  ·  tape measure")
    body(ax, "Posts first, full height on the land toward the middle; then each rail between them. Lay it straight "
             "off the roll with the liner still on its\nback, then peel and press as you go: never stretch it, "
             "stretched foam creeps back and opens a gap. B0 and B4 on their inner land, B3 on its\nupper land, B1 "
             "and B2 on both: a panel edge lands on each. Butt the ends, do not overlap them.")
    save(fig, ax, pdf, "03")


# ============================================================ 4
@page
def s4(pdf):
    fig, ax = new_page(4, "Back  ·  the bottom panel",
                       "T-nuts on their screws, the panel on the tape, every screw started, then tightened.")
    parts = enc(3, drop=("drains",))
    out = 90.0
    pm = Part(mv(_panel("back_bottom"), 0, out, 0), HILITE, lw=0.45, ang=30)
    scr = []
    for kind, m in _fast("back"):
        V = m[0]
        if V[:, 2].mean() < E.SEAMS_V[0] - 5 and kind != "batten_screw":
            scr.append(Part(mv(m, 0, out + 40, 0), HILITE, lw=0.3, ang=30))
    MMv = view(*BACKV)
    v = scene(ax, parts + [pm] + scr, (340, 462), (560, 600), MM=MMv, px=1.5, clip=(24, 150, 760, 772))
    for p in E.screws("back"):
        if p["v"] < E.SEAMS_V[0] - 5:
            axis3(ax, v, (p["u"], C.D, p["v"]), (p["u"], C.D + out + 60, p["v"]))
    n = len([p for p in E.screws("back") if p["v"] < E.SEAMS_V[0] - 5])
    tag(ax, 790, 700, "Back bottom panel  ·  1397 × 321.8", 1, hi=True)
    tag(ax, 790, 652, "M5 × 16 + DIN 9021 washer", n, hi=True)
    tag(ax, 790, 604, "M5 drop-in T-nut", n, hi=True)
    tool(ax, 790, 548, "3 mm hex")
    note(ax, 790, 508, "The panel's top edge stops 3 short\nof B1's slot line: the seam gap.\nIts holes are 20 in "
                       "from the sides\nand the floor edge.", fs=9.2, color=INK)
    body(ax, f"Peel the film off the inner face only. Put each screw through a washer and the panel from outside "
             "and spin a T-nut two turns onto its tip. Offer\nthe panel to the frame, push each nut into its slot, "
             "and turn each screw until the nut swings across and grips. Centre each screw in its 8 hole\n(the panel "
             f"grows {E.expansion()['back, 1397 over 20 C']} across for 20 °C), then tighten from the middle out "
             "until the tape is about 3.5: a 3 mm hex key slides under the panel's edge, a 4 does not.")
    save(fig, ax, pdf, "04")


# ============================================================ 5
@page
def s5(pdf):
    fig, ax = new_page(5, "Back  ·  the middle and upper panels",
                       "The same, twice. Each lands on its own land of B1 or B2; the 6 gap stays open for the battens.")
    parts = enc(4, drop=("drains",))
    out = 90.0
    pm = [Part(mv(_panel("back_middle"), 0, out, 0), HILITE, lw=0.45, ang=30),
          Part(mv(_panel("back_upper"), 0, out * 1.6, 0), HILITE, lw=0.45, ang=30)]
    MMv = view(*BACKV)
    v = scene(ax, parts + pm, (340, 462), (560, 600), MM=MMv, px=1.5, clip=(24, 150, 760, 772))
    nm = [p for p in E.screws("back") if p["kind"] == "panel" and p["v"] > E.SEAMS_V[0]]
    tag(ax, 790, 700, "Back middle panel  ·  1397 × 654.4", 1, hi=True)
    tag(ax, 790, 652, "Back upper panel  ·  1397 × 840.8", 1, hi=True)
    tag(ax, 790, 604, "M5 × 16 + washer, T-nut", len(nm), hi=True)
    tool(ax, 790, 548, "3 mm hex")
    panel(ax, 790, 190, 320, 300, z=5)
    sec_panel_screw(ax, 930, 330, 4.6, "seam", "")
    ax.text(802, 470, "the seam on B1, before its batten", fontsize=8.6, color=DIM, zorder=330)
    body(ax, "Middle panel next: its bottom edge 3 above B1's slot line, its top edge 3 below B2's, four screws "
             "into the posts only; hold it with two short\nstrips of painter's tape across each seam while you "
             "start them. The upper panel the same, from B2's line to the top. Leave the seam screws\nout: they "
             "go through the battens, next.")
    save(fig, ax, pdf, "05")


# ============================================================ 6
@page
def s6(pdf):
    fig, ax = new_page(6, "Back  ·  two battens over the seams",
                       "Two pieces a seam, butted at the middle. Eight M5 × 20 through each batten and the gap.")
    parts = enc(5, drop=("drains",))
    out = 70.0
    bt = [Part(mv(E.batten_mesh(s), 0, out, 0), HILITE, lw=0.4, ang=30) for s in E.SEAMS_V]
    sc = [Part(mv(m, 0, out + 30, 0), HILITE, lw=0.3, ang=30) for k, m in _fast("back") if k == "batten_screw"]
    MMv = view(*BACKV)
    v = scene(ax, parts + bt + sc, (340, 462), (560, 600), MM=MMv, px=1.5, clip=(24, 150, 760, 772))
    for p in E.screws("back"):
        if p["kind"] == "batten":
            axis3(ax, v, (p["u"], C.D, p["v"]), (p["u"], C.D + out + 50, p["v"]))
    tag(ax, 790, 700, "Seam batten, 698 × 25.4 × 3.2", 4, hi=True)
    tag(ax, 790, 652, "M5 × 20 button head", 16, hi=True)
    tag(ax, 790, 604, "M5 drop-in T-nut", 16, hi=True)
    tool(ax, 790, 548, "3 mm hex")
    panel(ax, 790, 190, 320, 300, z=5)
    sec_panel_screw(ax, 920, 330, 4.6, "batten", "")
    ax.text(802, 470, "a seam, in section", fontsize=8.6, color=DIM, zorder=330)
    body(ax, "The four battens are the same part: the right-hand one of each seam is a left-hand one turned end for "
             "end. Hole 1 sits 20 from its outer end. Each\nscrew passes through the 6 gap between the panels into a "
             "T-nut on the rail's slot line (on the posts at the ends). Snug only: the batten pulls both\nedges onto "
             "their tape.")
    save(fig, ax, pdf, "06")


# ============================================================ 7
@page
def s7(pdf):
    fig, ax = new_page(7, "Right panel  ·  on the bench first",
                       "Three glands, the intake grill and filter, the duct collar: easier flat than standing.")
    pm = _flat_panel("right")
    base = Part(pm, FROST, lw=0.45, ang=30, ghost=True)
    kit = []
    ex = 60.0
    for u, v in E.GLANDS:
        kit.append(Part(mv(E.gland_mesh(), u, v, E.T_PANEL + ex), HILITE, lw=0.35, ang=30))
    gu, gv = E.INTAKE
    kit.append(Part(mv(E.grill_mesh(), gu, gv, E.T_PANEL + ex), HILITE, lw=0.35, ang=30))
    rim, mesh_ = E.filter_mesh()
    kit.append(Part(mv(merge(rim, mesh_), gu, gv, E.T_PANEL + ex * 2.0), HILITE, lw=0.35, ang=30))
    kit.append(Part(mv(E.collar_mesh(), E.DUCT[0], E.DUCT[1], E.T_PANEL + ex), HILITE, lw=0.35, ang=30))
    MMv = view(200, 50)
    v = scene(ax, [base] + kit, (330, 462), (560, 600), MM=MMv, px=1.6, clip=(24, 150, 640, 772))
    for u, vv in E.GLANDS + [E.INTAKE, E.DUCT]:
        axis3(ax, v, (u, vv, 0.0), (u, vv, E.T_PANEL + ex + 10))
    q = v((0.0, 30.0, 0.0))
    ax.text(q[0] - 10, q[1], "front edge", fontsize=8.6, color=DIM, ha="right", zorder=320)
    tag(ax, 680, 712, "Cable gland PG21, nylon, its locknut inside", 3, hi=True)
    tag(ax, 680, 664, "Fan grill NA-FG1-12, outside", 1, hi=True)
    tag(ax, 680, 616, "Magnetic dust filter 120, on the grill", 1, hi=True)
    tag(ax, 680, 568, "Duct collar, PETG, printed", 1, hi=True)
    tag(ax, 680, 520, "M4 × 16 + washers + nyloc", 7, hi=True)
    tool(ax, 680, 470, "2.5 mm hex  ·  7 mm spanner")
    note(ax, 680, 432, "Print the collar from print/duct_collar.stl:\nPETG, 4 walls, 30 % infill, flange down.",
         fs=9.0, color=INK)
    body(ax, "Lay the panel outer face up (OUT on your label). Glands: body from outside, locknut inside, hand tight "
             "plus a quarter. Grill outside over the\nintake opening, four M4 × 16 with a washer each side and the "
             "nyloc inside; the filter's magnetic frame sticks to the steel grill. Collar flange outside,\nthree M4 × "
             "16. The 2 in duct slides over the spigot later and takes a zip tie.")
    save(fig, ax, pdf, "07")


# ============================================================ 8
@page
def s8(pdf):
    fig, ax = new_page(8, "Right panel  ·  tape, then the panel",
                       "The same land pattern as the back: posts full height, rails between, inner lands at top and floor.")
    parts = enc(6, drop=("drains",))
    parts.append(Part(_tape("right"), HILITE, lw=0.3, ang=30))
    out = 110.0
    parts.append(Part(mv(_panel("right"), out, 0, 0), HILITE, lw=0.45, ang=30))
    for k, m in right_kit():
        if k != "duct":
            parts.append(Part(mv(m, out, 0, 0), BLACKPART if k != "collar" else WHITEP, lw=0.3, ang=30))
    MMv = view(118, 18)
    v = scene(ax, parts, (340, 462), (560, 600), MM=MMv, px=1.5, clip=(24, 150, 760, 772))
    for p in E.screws("right"):
        axis3(ax, v, (C.W, p["u"], p["v"]), (C.W + out + 30, p["u"], p["v"]))
    tag(ax, 790, 700, "EPDM foam strip, right face", hi=True)
    tag(ax, 790, 652, "Right panel, with its glands and intake", 1, hi=True)
    nf = len([c for c in E.cutouts("right") if c[3] == "feeder M5"])
    tag(ax, 790, 604, "M5 × 16 + washer, T-nut", len(E.screws("right")) + nf, hi=True)
    tool(ax, 790, 548, "3 mm hex  ·  utility knife")
    note(ax, 790, 508, f"The {nf} screws on tier B's rail under\nthe two openings (green on the face\nmap) only hold "
                       "the panel until the\nharvest feeder goes on: keep them\nloose-ish, the feeder swaps them.",
         fs=9.0, color=INK)
    body(ax, "Tape as at step 3, on the right face. Then the panel: the front edge (glands at the back) flush with "
             "the front of the cabinet, screws and nuts as at\nstep 4. Feed the duct over the collar's spigot and "
             "zip-tie it; its other end goes over the humidifier's outlet, standing on the floor to the\nright. Cables "
             "come through the glands later: tighten the dome nuts only then.")
    save(fig, ax, pdf, "08")


# ============================================================ 9
@page
def s9(pdf):
    fig, ax = new_page(9, "Left side  ·  take the riser off the post",
                       "The riser moves outside the panel. Cut its five ties, pull the three branches off their fittings.")
    parts = enc(8)
    MMv = view(232, 14)
    rx, ry = C.RISER
    v = scene(ax, parts, (330, 462), (520, 600), MM=MMv, px=1.6, focus=fbox([-280, -40, -20], [300, 400, 1480]),
              clip=(24, 150, 620, 772))
    for z in C.drain_ties():
        q = v((rx - 12, ry, z))
        ax.add_patch(Circle(tuple(q), 8, facecolor="none", edgecolor=ACCENT, lw=2.0, zorder=320))
    for zl in C.TIERS:
        jz = zl - 40.0
        q = v((rx, ry + 12, jz))
        ax.add_patch(Circle(tuple(q), 10, facecolor="none", edgecolor=WARN, lw=1.6, ls=(0, (3, 2)), zorder=320))
    lab(ax, v, (rx - 20, ry, C.drain_ties()[0]), "cut each zip tie", dx=-80, ha="right")
    lab(ax, v, (rx, ry + 20, C.TIERS[1] - 40.0), "pull each branch off\nits tee or elbow", dx=-90, ha="right")
    # inset: after, the branches hanging, the riser set aside
    det = enc(9, drop=())
    inset(ax, 650, 230, 450, 530, det, view(232, 14), focus=fbox([-280, -40, -20], [300, 400, 1480]),
          label="then: branches free, riser set aside")
    tool(ax, 650, 196, "side cutters  ·  a mug of hot water")
    body(ax, "Cut the five ties round FL and the riser. Dip each branch's end in hot water for half a minute and pull "
             "it straight off its stub: never lever it, a\nsplit barb leaks. Lift the riser, with its elbow, tees and "
             "the bucket line, off the post and lay it on the floor by the bucket. The branches stay on\ntheir "
             "bulkheads; leave their ends hanging out of the side.")
    save(fig, ax, pdf, "09")


# ============================================================ 10
@page
def s10(pdf):
    fig, ax = new_page(10, "Left side  ·  tape, grommets, the panel",
                       "Grommets into the panel first, then the panel on, each branch end through its grommet.")
    parts = enc(9)
    parts.append(Part(_tape("left"), HILITE, lw=0.3, ang=30))
    out = 120.0
    parts.append(Part(mv(_panel("left"), -out, 0, 0), HILITE, lw=0.45, ang=30))
    parts.append(Part(mv(E.grommets_world(), -out, 0, 0), HILITE, lw=0.35, ang=30))
    MMv = view(242, 16)
    v = scene(ax, parts, (330, 462), (540, 600), MM=MMv, px=1.5, clip=(24, 150, 640, 772))
    for u, vv in E.grommets():
        axis3(ax, v, (0.0, u, vv), (-out - 40, u, vv))
    tag(ax, 680, 712, "EPDM foam strip, left face", hi=True)
    tag(ax, 680, 664, "Grommet, 7/8 in hole, 5/8 in bore", 3, hi=True)
    tag(ax, 680, 616, "Left panel", 1, hi=True)
    n = len([p for p in E.screws("left") if p["kind"] == "panel"])
    tag(ax, 680, 568, "M5 × 16 + washer, T-nut", n, hi=True)
    tool(ax, 680, 512, "3 mm hex")
    note(ax, 680, 472, "Leave out the five screws on FL's line\nfrom 325 to 1201: they are the P-clips'\n(step 11). "
                       "Drop their T-nuts in now.", fs=9.2, color=INK)
    body(ax, "Tape the left face as before. Press the three grommets into the panel. With a helper holding the "
             "panel off the frame, feed each branch's end out\nthrough its grommet from the inside (A lowest, C "
             "highest), then bring the panel onto the tape and screw it as at step 4. A little dish soap on\nthe "
             "tube makes it slide.")
    save(fig, ax, pdf, "10")


# ============================================================ 11
@page
def s11(pdf):
    fig, ax = new_page(11, "Left side  ·  the riser on its P-clips",
                       "Five cushioned clips on FL's line hold the riser 2 off the panel. Trim each branch 8, refit.")
    parts = enc(11, hi=("clips", "clip_screws", "drains"))
    MMv = view(236, 14)
    v = scene(ax, parts, (330, 462), (520, 600), MM=MMv, px=1.6, focus=fbox([-280, -40, -20], [300, 400, 1480]),
              clip=(24, 150, 620, 772))
    for z in E.CLIP_V:
        lab(ax, v, (E.RISER[0] - 10, E.RISER[1], z), f"{z:.0f}", dx=-46, ha="right", fs=8.2)
    # inset: one clip, close
    rx, ry = E.RISER
    zc = E.CLIP_V[2]
    det = enc(11, hi=("clips", "clip_screws"))
    inset(ax, 650, 380, 450, 380, det, view(250, 20), focus=fbox([rx - 30, 0, zc - 40], [5, 70, zc + 40]),
          label="a P-clip: tab on the slot line, loop round the riser")
    tag(ax, 650, 340, "P-clip 5/8 in, EPDM cushioned", 5, hi=True)
    tag(ax, 650, 292, "M5 × 16, no washer, into its T-nut", 5, hi=True)
    tool(ax, 650, 240, "3 mm hex  ·  hot water  ·  knife")
    tb = E.branch_trim()
    body(ax, f"Clip the riser on at the five heights, its tees facing back toward the grommets. Each branch now has "
             f"a shorter run: cut {abs(tb['B']):.0f} off its end, square,\nwarm it, and push it fully onto its stub. "
             "Check the fall: from every grommet down to the riser, never up. The riser stays clear of the panel "
             "(vinyl\nagainst polycarbonate clouds it over time) and drops into the bucket lid as before.")
    save(fig, ax, pdf, "11")


# ============================================================ 12
@page
def s12(pdf):
    fig, ax = new_page(12, "Top panel  ·  fans on the bench",
                       "The panel inner face up on two boards: a grill under it, a fan and a grill on it, at each hole.")
    pm = _flat_panel("top")
    face, u0, v0, u1, v1 = E.panels()["top"]
    Lv = v1 - v0
    # turned over: the inner face up, the front edge at the back of the bench
    flip = lambda m: mv(rot(m, rx=math.pi), 0, Lv, E.T_PANEL)            # noqa: E731
    base = Part(flip(pm), FROST, lw=0.45, ang=30, ghost=True)
    kit = []
    ex = 70.0
    fm, bo = _fan()
    for x, y in E.FANS:
        xl, yl = x - u0, Lv - (y - v0)
        fan_dn = lambda m: mv(rot(m, rx=math.pi), xl, yl, E.T_PANEL + E.FAN_T + ex)    # noqa: E731  outlet down
        kit.append(Part(fan_dn(fm), HILITE, lw=0.3, ang=30))
        kit.append(Part(fan_dn(bo), HILITE, lw=0.3, ang=30))
        kit.append(Part(mv(E.grill_mesh(), xl, yl, E.T_PANEL + E.FAN_T + ex * 1.8), HILITE, lw=0.3, ang=30))
        kit.append(Part(mv(E.grill_mesh(), xl, yl, -1.6 - ex * 0.8), HILITE, lw=0.3, ang=30))
        for sx in (-1, 1):
            for sy in (-1, 1):
                px_, py_ = xl + sx * E.FAN_PITCH / 2, yl + sy * E.FAN_PITCH / 2
                kit.append(Part(mv(C.button_head(4, 40), px_, py_, E.T_PANEL + E.FAN_T + 1.6 + ex * 2.5), STEEL,
                                lw=0.3, ang=30))
    MMv = view(206, 40)
    v = scene(ax, [base] + kit, (340, 470), (600, 560), MM=MMv, px=1.6, clip=(24, 150, 660, 772))
    for x, y in E.FANS:
        xl, yl = x - u0, Lv - (y - v0)
        for sx in (-1, 1):
            for sy in (-1, 1):
                p = (xl + sx * E.FAN_PITCH / 2, yl + sy * E.FAN_PITCH / 2)
                axis3(ax, v, (p[0], p[1], -1.6 - ex * 0.8 - 20), (p[0], p[1], E.T_PANEL + E.FAN_T + ex * 2.5 + 30))
    q = v((700.0, Lv, E.T_PANEL))
    ax.text(q[0], q[1] + 14, "front edge", fontsize=8.6, color=DIM, ha="center", zorder=320)
    tag(ax, 690, 712, "Noctua NF-F12 PWM, label side down", 2, hi=True)
    tag(ax, 690, 664, "Fan grill NA-FG1-12, one under, one on", 4, hi=True)
    tag(ax, 690, 616, "M4 × 40 + washers + nyloc", 8, hi=True)
    tool(ax, 690, 560, "2.5 mm hex  ·  7 mm spanner")
    note(ax, 690, 520, "Air leaves upward, out of the cabinet:\nthe fan's label (the outlet side's\nstruts) faces "
                       "the panel. Lead each\ncable to the back right, along B4, to\nthe tier C node.", fs=9.2,
         color=INK)
    body(ax, "Turn the panel inner face up on two boards, the boards clear of the holes. Drop each screw from above "
             "through a washer, the grill's tab, the fan's corner\nflange and the panel; under it, the outer grill's "
             "tab, a washer and the nyloc. Snug, not tight: the fan's frame is plastic. Both fans run off the tier C\n"
             f"node's exhaust output (BOM G022), in parallel. They hang 25 under the panel, {_fan_clear()} over the arm folded at "
             "the top of its travel; the gantry's mast never passes under them.")
    save(fig, ax, pdf, "12")


# ============================================================ 13
@page
def s13(pdf):
    fig, ax = new_page(13, "Top panel  ·  on, and anchored to the wall",
                       "Tape on F4, B4, L4 and R4, the panel on it, then two anti-tip brackets into wall studs.")
    parts = enc(11, drop=())
    parts.append(Part(_tape("top"), HILITE, lw=0.3, ang=30))
    up = 140.0
    parts.append(Part(mv(_panel("top"), 0, 0, up), HILITE, lw=0.45, ang=30))
    for k, m in top_kit(explode=up):
        parts.append(Part(m, BLACKPART, lw=0.3, ang=30))
    for u in E.ANTITIP_U:
        m, c_ = E.antitip_mesh(u, explode=up + 60)
        parts += [Part(m, HILITE, lw=0.3, ang=30), Part(c_, STEEL, lw=0.3, ang=30)]
    MMv = view(212, 34)
    v = scene(ax, parts, (340, 470), (580, 580), MM=MMv, px=1.5, clip=(24, 150, 680, 772))
    for p in E.screws("top"):
        axis3(ax, v, (p["u"], p["v"], C.H), (p["u"], p["v"], C.H + up + 30))
    tag(ax, 700, 712, "EPDM foam strip, top face", hi=True)
    tag(ax, 700, 664, "Top panel, fans on", 1, hi=True)
    tag(ax, 700, 616, "M5 × 16 + washer, T-nut", len([p for p in E.screws("top") if p["kind"] == "panel"]), hi=True)
    tag(ax, 700, 568, "Anti-tip kit: bracket, cable, wall bracket", 2, hi=True)
    tag(ax, 700, 520, "M5 × 16 into B4, through the bracket", 2, hi=True)
    tool(ax, 700, 466, "3 mm hex  ·  step ladder  ·  stud finder")
    note(ax, 700, 428, "The silicone at the post tops (step 2)\nmust have skinned. No screw goes into\na post end: "
                       "the corner screws sit\n60 in, on the rails.", fs=9.2, color=INK)
    body(ax, "The top's strips run on each top rail's inner land. Lift the panel up, fans down, with its front edge to the front "
             "(the fans nearer the front than\nthe back), centre it, screw it as at step 4. The two brackets go on "
             f"B4's line at x {E.ANTITIP_U[0]:.0f} and {E.ANTITIP_U[1]:.0f}, in place of two panel screws; their "
             "cables run to wall brackets screwed into\nstuds, pulled taut. The cabinet is 1.85 m tall and only "
             "0.56 deep: this is not optional.")
    save(fig, ax, pdf, "13")


# ============================================================ 14
@page
def s14(pdf):
    fig, ax = new_page(14, "Doors  ·  on the bench",
                       "Each door gets two hinges, two steel discs, a pull and a reed magnet; each right door its astragal.")
    # the bottom right door, flat, inner face up
    pair, side = "bottom", "R"
    dp = E.door_parts(pair, side, 0.0)
    T = lambda m: (np.c_[m[0][:, 0], -m[0][:, 2], m[0][:, 1]], m[1])          # noqa: E731  inner face up
    parts = [Part(T(dp["door"]), CLEARC, lw=0.4, ang=30, ghost=True)]
    ex = 40.0
    for k in ("hinge_door", "discs", "reed_magnet", "astragal"):
        V, F = T(dp[k])
        parts.append(Part((V + np.array([0, 0, ex]), F), HILITE, lw=0.3, ang=30))
    fr, dl, sp = E.hinge_meshes(pair, side)
    V, F = T(fr)
    parts.append(Part((V + np.array([0, 0, ex]), F), HILITE, lw=0.3, ang=30))
    pl = T(dp["pull"])
    parts.append(Part((pl[0] + np.array([0, 0, -ex]), pl[1]), BLACKPART, lw=0.3, ang=30))
    MMv = view(20, 52)
    v = scene(ax, parts, (340, 470), (600, 560), MM=MMv, px=1.6, clip=(24, 150, 680, 772))
    tag(ax, 700, 712, "Piano hinge 1 ft, door leaf on VHB", 8, hi=True)
    tag(ax, 700, 664, "Steel disc Ø16, adhesive", 8, hi=True)
    tag(ax, 700, 616, "Reed magnet, its own adhesive", 4, hi=True)
    tag(ax, 700, 568, "Astragal, right doors, on VHB", 2, hi=True)
    tag(ax, 700, 520, "Pull, 96 centres, M4 × 10 button head", 4)
    tool(ax, 700, 466, "alcohol  ·  2.5 mm hex  ·  a square")
    note(ax, 700, 428, "Drawn: the bottom right door, inner\nface up. The left doors mirror it,\nwithout the "
                       "astragal.", fs=9.2, color=INK)
    body(ax, f"Peel the inner film and wipe each bond spot with half alcohol, half water. Hinges: VHB on the door leaf, knuckle 0.5 off the hinge edge, square to it, at "
             f"the heights on the front map; press hard for\n30 s each. Discs where the magnets will meet them, "
             f"{E.MAG_X['L']:.0f} from the cabinet's left (mirror for right doors). Astragal: VHB on its outer 18.5, "
             "overhanging the\nright door's edge by 21.5 toward the left door. Reed magnet under its switch's spot. "
             "VHB reaches full strength in 72 h: hang the doors tomorrow.")
    save(fig, ax, pdf, "14")


# ============================================================ 15
@page
def s15(pdf):
    fig, ax = new_page(15, "Front  ·  weatherstrip, magnets, switches",
                       "What the doors close on: strips on the lands, cup magnets on the slot lines, a switch under F2 and F4.")
    parts = enc(15, hi=("strips", "magnets", "reeds"))
    MMv = view(206, 16)
    v = scene(ax, parts, (330, 462), (520, 600), MM=MMv, px=1.6, clip=(24, 150, 620, 772))
    for pair in ("bottom", "top"):
        for side in ("L", "R"):
            for z in E.MAG_Z[pair]:
                q = v((E.MAG_X[side], 0.0, z))
                ax.add_patch(Circle(tuple(q), 8, facecolor="none", edgecolor=ACCENT, lw=1.8, zorder=320))
    det = enc(15, hi=("strips", "magnets"))
    inset(ax, 650, 380, 450, 380, det, view(200, 26), focus=fbox([560, -10, -5], [740, 40, 360]),
          label="F0 and F1 at the middle: magnets, the strip")
    tag(ax, 650, 340, "EPDM weatherstrip 5/16 × 1/4 in", hi=True)
    tag(ax, 650, 292, "Cup magnet Ø16 × 4.5, M3 × 12 + T-nut", 8, hi=True)
    tag(ax, 650, 244, "Reed switch 7939WG, under F2 and F4", 4, hi=True)
    tool(ax, 650, 196, "2 mm hex  ·  knife")
    body(ax, "Strips: one loop for each pair, on the land beside each post's front slot and on the rails' lands: F0's "
             "upper, F2's lower and upper, F4's lower.\nMagnets on F0, F1, F3 and F4, 640 in from each side, face flush "
             "and tight. Switches on the underside of F2 and F4, 592 in from each side, on\ntheir adhesive; wire the "
             "four in series as the door chain (utility node, MCP23017 A4, wiring sheet E-03).")
    save(fig, ax, pdf, "15")


# ============================================================ 16
@page
def s16(pdf):
    fig, ax = new_page(16, "Front  ·  hang the doors",
                       "Bottom pair first. Spacer on the post, the hinge's frame leaf on the spacer, one M3 in every hole.")
    parts = enc(15)
    parts += door_set("bottom", "L", 70.0, hi=True)
    parts += door_set("bottom", "R", 30.0, hi=True)
    MMv = view(204, 16)
    v = scene(ax, parts, (330, 462), (520, 600), MM=MMv, px=1.6, clip=(24, 150, 620, 772))
    # inset: the hinge, exploded off the post
    det = FB.cab(99, lo=(-20, -10, 600), hi=(80, 60, 800))
    fr, dl, sp = E.hinge_meshes("bottom", "L")
    det += [Part(mv(sp, 0, -12, 0), HILITE, lw=0.35), Part(mv(fr, 0, -30, 0), HILITE, lw=0.35),
            Part(mv(dl, 0, -30, 0), HILITE, lw=0.35)]
    for u, z in E.hinge_screws("bottom", "L"):
        if 600 < z < 800:
            det.append(Part(mv(C.place_axis(E.flat3(12), (u, -E.SPACER_T - E.LEAF_T, z), (0, 1, 0)), 0, -60, 0),
                            STEEL, lw=0.3))
            det.append(Part(C.place_axis(E.tnut(3), (u, C.SLOT_LIP, z), (0, 1, 0)), NUTC, lw=0.3))
    inset(ax, 650, 380, 450, 380, det, view(214, 22), focus=fbox([-10, -70, 630], [60, 30, 770]),
          label="post, spacer, hinge: M3 into a T-nut")
    tag(ax, 650, 340, "Hinge spacer, slot on the slot line", 8, hi=True)
    tag(ax, 650, 292, "M3 × 12 flat head + M3 T-nut, every hole", "40+", hi=True)
    tool(ax, 650, 240, "2 mm hex  ·  a helper")
    body(ax, "Drop M3 T-nuts in the post's front slot, one per hinge hole. A helper holds the door open at 90°, "
             "hinges against the post; slip each spacer\nbehind its frame leaf, slot over the slot line, and start "
             "every screw through the leaf, the spacer's slot and into its nut. Close the door gently:\nits free "
             "edge should meet both magnets together. Then the top pair, the same. Snug every screw once all four "
             "hang true.")
    save(fig, ax, pdf, "16")


# ============================================================ 17
@page
def s17(pdf):
    fig, ax = new_page(17, "Doors  ·  adjust and check",
                       "Close each pair left door last. The gaps, the catch, the seal, the switch.")
    parts = enc(16)
    MMv = view(206, 14)
    v = scene(ax, parts, (330, 462), (520, 600), MM=MMv, px=1.6, clip=(24, 150, 620, 772))
    rows = [("Centre gap", "3 between each pair, top to bottom (2 to 5 is fine). Off? Re-seat the hinge in its "
             "spacer slot."),
            ("Split gap", "3 between the pairs, even across. Off? A door's hinges sit at different heights."),
            ("Catch", "Each door's free edge pulls in onto both magnets with a click; no door rests on its strip."),
            ("Seal", "A strip of paper shut in the door anywhere round the loop drags as you pull it out."),
            ("Swing", f"Each door opens to {swing_max('bottom', 'L'):.0f}° and touches nothing on the way."),
            ("Switches", "The door chain reads open with any one door ajar, closed with all four shut.")]
    import textwrap
    y0 = 722
    for i, (a, b) in enumerate(rows):
        y = y0 - i * 92
        ax.add_patch(Rectangle((640, y - 42), 470, 80, facecolor="#fbfcfc", edgecolor=RULE, lw=0.9))
        ax.add_patch(Rectangle((654, y - 8), 16, 16, facecolor="white", edgecolor=INK, lw=1.3))
        ax.text(684, y + 16, a, fontsize=10.6, fontweight="bold", color=INK, va="center")
        ax.text(684, y + 2, textwrap.fill(b, 66), fontsize=8.2, color=DIM, va="top", linespacing=1.35)
    body(ax, "Open order: left door, then right (the left door's edge lies over the right one's astragal). Close "
             "order: right, then left. If a door will not stay\nshut, look for something standing proud of the "
             "weatherstrip's plane: a screw head, a strip end lifted. Do not add magnets: find the high spot.")
    save(fig, ax, pdf, "17")


# ============================================================ 18
@page
def s18(pdf):
    fig, ax = new_page(18, "Before you plant",
                       "The checks that catch the usual faults, while the cabinet is still empty.")
    rows = [("Every screw snug", f"{E.counts()['M5 drop-in T-nut']} M5s, the hinge M3s, the fan and grill M4s. "
             "A paint mark on each as you go."),
            ("Anchored", "Both anti-tip cables taut, both wall brackets in studs. Pull the top forward: it does not "
             "move."),
            ("Air", "Fans on: a tissue held at the intake filter is drawn in; nothing whistles at a door or seam."),
            ("Water", "1 L into each tray. It drains through its grommet into the riser and the bucket; the panel "
             "stays dry."),
            ("Humidity", "Humidifier on through the duct for 10 minutes: mist in tier A, no drips at the collar."),
            ("Cables", "Everything in through the glands, the dome nuts tight on each bundle; no cable on a "
             "door's swing.")]
    checkbox_rows(ax, rows, y0=690, dy=90)
    body(ax, "Clean the doors and panels with lukewarm water and a little dish soap, a soft cloth, no scraping. "
             "Isopropyl alcohol is fine for a spot; never\nglass cleaner (ammonia), acetone or thinners: they craze "
             "polycarbonate. The film comes off the outer faces last, once all the work is done.", fs=10.2)
    save(fig, ax, pdf, "18")


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
    path = f"{OUT}/Maag_Enclosure_Assembly_Instructions_RevA.pdf"
    with PdfPages(path) as pdf:
        for fn in PAGES:
            fn(pdf); print(fn.__name__, "ok", flush=True)
    print("saved", path, f"({len(PAGES)} pages)")
