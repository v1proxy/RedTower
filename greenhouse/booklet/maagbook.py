"""The Maag booklet page kit: one page, the house style, shared by every booklet.

Lifted from the Gantry Rev E generator (greenhouse/gantry/make_steps4.py),
value for value, with the footer made a parameter so the frame booklet and
any later one print their own name. make_steps4.py still carries its own
copy; it can import this one at its next revision.

House style (Design System artifact, project/README.md): IBM Plex Mono for
titles, step numerals and tool names; Inter for everything read. Page 1150 x
900 (11.5 x 9 in), frame 18 in, header band 128, footer "Maag  ·  <doc>".
"""
import glob as _glob
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib import font_manager as _fm                          # noqa: E402
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch, FancyBboxPatch, Polygon   # noqa: E402,F401

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "gantry"))
from kit3d import Part, render, iso_matrix, INK, DIM                # noqa: E402,F401

# ------------------------------------------------------------------ type
for _d in (os.environ.get("MAAG_FONTS", ""), os.path.join(_HERE, "..", "..", "..", "..", "_fonts")):
    for _f in _glob.glob(os.path.join(_d, "*.ttf")) if _d else []:
        _fm.fontManager.addfont(_f)
TITLE_FONT = ("IBM Plex Mono" if any(f.name == "IBM Plex Mono" for f in _fm.fontManager.ttflist)
              else "DejaVu Sans Mono")
plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]

# ------------------------------------------------------------------ colour
ACCENT = "#c2410c"          # motion and count only
WARN = "#b91c1c"
OK = "#15803d"
AXIS = "#6b7780"
EDGE = "#9aa7b0"
FRAMEC = "#dfe5e9"
RULE = "#c3ccd2"
NEW_FILL, NEW_EDGE = "#fff4e8", "#e08a3c"
CHIP = "#eef2f5"
PANEL = "#f5f7f8"

WIN_TOP = 772.0
DOC = "Frame Rev A"
OUT = "build"


def configure(doc, out):
    global DOC, OUT
    DOC, OUT = doc, out
    os.makedirs(OUT, exist_ok=True)


def new_page(step, title, sub=""):
    fig = plt.figure(figsize=(11.5, 9.0), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(0, 1150); ax.set_ylim(0, 900)
    ax.add_patch(Rectangle((18, 18), 1114, 864, facecolor="none",
                           edgecolor=FRAMEC, lw=1.2, zorder=300))
    if step is not None:
        ax.add_patch(Circle((78, 812), 34, facecolor=INK, edgecolor="none", zorder=301))
        ax.text(78, 812, str(step), ha="center", va="center", color="white",
                fontsize=24, fontweight="bold", family=TITLE_FONT, zorder=302)
    title = title.replace("  ·  ", " · ")
    ax.text(132 if step is not None else 48, 822, title, fontsize=17.5,
            fontweight="semibold", family=TITLE_FONT, color=INK, va="center", zorder=302)
    if sub:
        ax.text(132 if step is not None else 48, 790, sub, fontsize=11,
                color=DIM, va="center", zorder=302)
    ax.text(1114, 30, f"Maag  ·  {DOC}", fontsize=8, color=DIM, ha="right", zorder=302)
    ax._geom = []
    return fig, ax


class View:
    """The mapping a scene used, so arrows and axis lines can be placed in 3D."""

    def __init__(self, MM, s, c, xy):
        self.MM, self.s, self.c, self.xy = MM, s, np.asarray(c), np.asarray(xy)

    def __call__(self, p):
        q = np.asarray(p, float) @ self.MM.T
        return (q[..., :2] - self.c) * self.s + self.xy


def scene(ax, parts, box_xy, box_wh, MM=None, focus=None, clip=None, px=3.0, scale=None):
    """Render `parts`, scaled so `focus` fills the box (or at `scale` px/mm).
    Whatever lies outside runs on and is clipped at the drawing window."""
    MM = iso_matrix(34, 24) if MM is None else MM
    if focus is None:
        pts = np.vstack([p.mesh[0] for p in parts if len(p.mesh[1])])
    elif isinstance(focus, np.ndarray):
        pts = focus
    else:
        pts = np.vstack([p.mesh[0] for p in focus if len(p.mesh[1])])
    Q = pts @ MM.T
    lo, hi = Q[:, :2].min(0), Q[:, :2].max(0)
    ext = np.maximum(hi - lo, 1e-9)
    s = scale if scale else min(box_wh[0] / ext[0], box_wh[1] / ext[1])
    c = (lo + hi) / 2
    sp = [Part(((p.mesh[0] @ MM.T - np.array([c[0], c[1], 0])) * s
                + np.array([box_xy[0], box_xy[1], 0]), p.mesh[1]),
               p.color, p.edges, p.alpha, p.ghost, p.ang, p.lw) for p in parts if len(p.mesh[1])]
    before = set(map(id, ax.images + ax.collections))
    render(ax, sp, M=np.eye(3), px=px)
    new = [a for a in ax.images + ax.collections if id(a) not in before]
    ax._geom.append((new, clip))
    return View(MM, s, c, box_xy)


def inset(ax, x, y, w, h, parts, MM, focus=None, label=None, px=3.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=10",
                                facecolor="white", edgecolor=EDGE, lw=1.0, zorder=150))
    v = scene(ax, parts, (x + w / 2, y + h / 2 - (8 if label else 0)),
              (w * 0.86, h * 0.80), MM=MM, focus=focus, clip=(x, y, x + w, y + h), px=px)
    for a in ax._geom[-1][0]:
        a.set_zorder(a.get_zorder() + 150)
    if label:
        ax.text(x + 12, y + h - 16, label, fontsize=8.6, color=DIM, zorder=330,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    return v


def panel(ax, x, y, w, h, z=150):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=10",
                                facecolor="white", edgecolor=EDGE, lw=1.0, zorder=z))


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


def arrow2(ax, p0, p1, color=ACCENT, lw=2.3, rad=0.0, ms=16):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                 lw=lw, color=color, zorder=200,
                                 connectionstyle=f"arc3,rad={rad}"))


def axis3(ax, v, p0, p1, color=AXIS):
    """Dashed assembly axis between two 3D points."""
    a, b = v(p0), v(p1)
    ax.plot([a[0], b[0]], [a[1], b[1]], ls=(0, (5, 4)), lw=0.9, color=color, zorder=120)


def tag(ax, x, y, text, qty=None, fs=10.2, hi=False):
    t = f"{qty}×   {text}" if qty else text
    ax.text(x, y, t, fontsize=fs, color=INK, va="center", zorder=201,
            bbox=dict(boxstyle="round,pad=0.4",
                      fc=NEW_FILL if hi else "white",
                      ec=NEW_EDGE if hi else RULE, lw=0.9))


def body(ax, txt, color=INK, fs=10.5):
    base = getattr(ax, "_body_y", 44.0)
    ax.text(60, base, txt, fontsize=fs, color=color, va="bottom",
            linespacing=1.62, zorder=302)
    ax._body_y = base + (txt.count("\n") + 1) * fs * 2.25 + 14.0


def tool(ax, x, y, label):
    w = max(140.0, 8.6 * len(label) + 24.0)
    ax.add_patch(Rectangle((x, y - 16), w, 32, facecolor=CHIP,
                           edgecolor=RULE, lw=0.9, zorder=200))
    ax.text(x + w / 2, y, label, ha="center", va="center", fontsize=9.5,
            color="#334", zorder=201, fontweight="bold", family=TITLE_FONT)


def note(ax, x, y, txt, fs=8.8, color=DIM):
    ax.text(x, y, txt, fontsize=fs, color=color, va="top", linespacing=1.45, zorder=302)


def leader(ax, p, q, color=DIM, lw=0.8):
    ax.plot([p[0], q[0]], [p[1], q[1]], color=color, lw=lw, zorder=200)


def checkbox_rows(ax, rows, y0=690, dy=92, x0=78, w=1000):
    for i, (a, b) in enumerate(rows):
        y = y0 - i * dy
        ax.add_patch(Rectangle((x0, y - 30), w, 66, facecolor="#fbfcfc", edgecolor=RULE, lw=0.9))
        ax.add_patch(Rectangle((x0 + 18, y - 8), 18, 18, facecolor="white", edgecolor=INK, lw=1.4))
        ax.text(x0 + 58, y + 10, a, fontsize=12, fontweight="bold", color=INK)
        ax.text(x0 + 58, y - 13, b, fontsize=9.8, color=DIM)
