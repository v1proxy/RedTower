"""Small schematic-drawing kit: boxes with named pins, orthogonal wires, buses.

Used by make_wiring.py. Coordinates are arbitrary paper units; every sheet sets
its own extents. Nothing here knows anything about the greenhouse.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon

INK = "#15191c"
DIM = "#5b6770"
RULE = "#aab4bb"
AC = "#b91c1c"          # mains
V24 = "#c2410c"         # 24 V dc
V12 = "#b45309"         # 12 V dc
SIG = "#1d4ed8"         # logic / signal
I2C = "#7c3aed"         # i2c bus
NET = "#0f766e"         # ethernet
SAFE = "#15803d"        # safety circuit
GND = "#374151"

FILL = {
    "ac":    "#fdecec",
    "psu":   "#fff1e6",
    "node":  "#e8eefc",
    "sense": "#f3ecfd",
    "act":   "#eafaf1",
    "safe":  "#e9f7ee",
    "net":   "#e6f4f2",
    "plain": "#f5f7f8",
    "load":  "#fdf6e3",
}


class Box:
    """A part. Pins are placed on the four sides and addressed by name."""

    def __init__(self, ax, x, y, w, h, title, sub=None, tag=None,
                 kind="plain", fs=8.4, title_fs=9.0):
        self.ax, self.x, self.y, self.w, self.h = ax, x, y, w, h
        self.pins = {}
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=3.2",
            linewidth=1.15, edgecolor=INK, facecolor=FILL.get(kind, "#f5f7f8"),
            zorder=3))
        ty = y + h - 11.5
        ax.text(x + w / 2, ty, title, ha="center", va="center",
                fontsize=title_fs, fontweight="bold", color=INK, zorder=5)
        if sub:
            ax.text(x + w / 2, ty - 7.0, sub, ha="center", va="top",
                    fontsize=fs - 0.7, color=DIM, zorder=5, linespacing=1.45)
        if tag:
            ax.text(x + 4.5, y + 4.0, tag, ha="left", va="bottom",
                    fontsize=fs - 1.3, color=DIM, style="italic", zorder=5)

    # ---------------------------------------------------------------- pins
    def _side(self, side, names, fs, pad, start=None, span=None):
        n = len(names)
        if n == 0:
            return
        if side in ("l", "r"):
            lo = (start if start is not None else self.y + pad)
            hi = lo + (span if span is not None else self.h - 2 * pad)
            xs = self.x if side == "l" else self.x + self.w
            for i, nm in enumerate(names):
                t = (i + 0.5) / n
                yy = hi - t * (hi - lo)
                self.pins[nm] = (xs, yy)
                dx = -3.0 if side == "l" else 3.0
                self.ax.plot([xs, xs + dx], [yy, yy], color=INK, lw=0.9, zorder=4)
                self.ax.text(xs + (4.4 if side == "r" else -4.4), yy, nm,
                             ha="left" if side == "r" else "right", va="center",
                             fontsize=fs, color=INK, zorder=5)
        else:
            lo = (start if start is not None else self.x + pad)
            hi = lo + (span if span is not None else self.w - 2 * pad)
            ys = self.y if side == "b" else self.y + self.h
            for i, nm in enumerate(names):
                t = (i + 0.5) / n
                xx = lo + t * (hi - lo)
                self.pins[nm] = (xx, ys)
                dy = -3.0 if side == "b" else 3.0
                self.ax.plot([xx, xx], [ys, ys + dy], color=INK, lw=0.9, zorder=4)
                self.ax.text(xx, ys + (-5.2 if side == "b" else 5.2), nm,
                             ha="center", va="top" if side == "b" else "bottom",
                             fontsize=fs, color=INK, zorder=5, rotation=0)

    def left(self, *names, fs=7.2, pad=8, start=None, span=None):
        self._side("l", list(names), fs, pad, start, span); return self

    def right(self, *names, fs=7.2, pad=8, start=None, span=None):
        self._side("r", list(names), fs, pad, start, span); return self

    def top(self, *names, fs=7.2, pad=10, start=None, span=None):
        self._side("t", list(names), fs, pad, start, span); return self

    def bottom(self, *names, fs=7.2, pad=10, start=None, span=None):
        self._side("b", list(names), fs, pad, start, span); return self

    # silent pins: a connection point with no leader or label
    def port(self, name, side, t):
        if side == "l":
            p = (self.x, self.y + t * self.h)
        elif side == "r":
            p = (self.x + self.w, self.y + t * self.h)
        elif side == "t":
            p = (self.x + t * self.w, self.y + self.h)
        else:
            p = (self.x + t * self.w, self.y)
        self.pins[name] = p
        return p

    def p(self, name):
        return self.pins[name]


# -------------------------------------------------------------------- wires
def wire(ax, pts, color=SIG, lw=1.25, ls="-", label=None, lpos=0.5,
         lfs=7.0, loff=4.2, zorder=2, dots=()):
    """Orthogonal polyline through pts (already axis-aligned by the caller)."""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle="round",
            zorder=zorder)
    for d in dots:
        ax.add_patch(Circle(pts[d], 1.7, facecolor=color, edgecolor="none",
                            zorder=zorder + 1))
    if label:
        # put the label on the longest segment
        best, bl = 0, -1
        for i in range(len(pts) - 1):
            L = abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
            if L > bl:
                bl, best = L, i
        a, b = pts[best], pts[best + 1]
        mx = a[0] + (b[0] - a[0]) * lpos
        my = a[1] + (b[1] - a[1]) * lpos
        horiz = abs(b[1] - a[1]) < 1e-9
        ax.text(mx, my + (loff if horiz else 0),
                label, ha="center" if horiz else "left",
                va="bottom" if horiz else "center",
                fontsize=lfs, color=color, zorder=zorder + 2,
                bbox=dict(boxstyle="round,pad=0.16", facecolor="white",
                          edgecolor="none", alpha=0.88))


def elbow(ax, a, b, color=SIG, lw=1.25, first="h", label=None, **kw):
    """Two-segment orthogonal run between two points."""
    mid = (b[0], a[1]) if first == "h" else (a[0], b[1])
    wire(ax, [a, mid, b], color=color, lw=lw, label=label, **kw)
    return mid


def dogleg(ax, a, b, x=None, y=None, color=SIG, lw=1.25, label=None, **kw):
    """Three-segment run: out, across at x (or y), then in."""
    if x is not None:
        pts = [a, (x, a[1]), (x, b[1]), b]
    else:
        pts = [a, (a[0], y), (b[0], y), b]
    wire(ax, pts, color=color, lw=lw, label=label, **kw)


def bus(ax, x0, x1, y, color=AC, lw=3.4, label=None, lx=None, zorder=1):
    ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt",
            zorder=zorder)
    if label:
        ax.text(lx if lx is not None else x0 - 4, y, label, ha="right",
                va="center", fontsize=8.2, fontweight="bold", color=color,
                zorder=zorder + 2)


def tap(ax, x, y_bus, y_to, color=AC, lw=1.4, dot=True):
    ax.plot([x, x], [y_bus, y_to], color=color, lw=lw, zorder=2)
    if dot:
        ax.add_patch(Circle((x, y_bus), 2.1, facecolor=color,
                            edgecolor="none", zorder=4))


def gnd(ax, x, y, color=GND, size=5.0, label=None):
    ax.plot([x, x], [y, y - size * 0.7], color=color, lw=1.2, zorder=3)
    for i, f in enumerate((1.0, 0.62, 0.28)):
        yy = y - size * 0.7 - i * size * 0.26
        ax.plot([x - size * f * 0.9, x + size * f * 0.9], [yy, yy],
                color=color, lw=1.1, zorder=3)
    if label:
        ax.text(x, y - size * 1.9, label, ha="center", va="top",
                fontsize=6.6, color=color, zorder=3)


def fuse(ax, x, y, w=13, h=5.2, label=None, color=V24):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor="white",
                           edgecolor=color, lw=1.1, zorder=4))
    ax.plot([x - w / 2, x + w / 2], [y, y], color=color, lw=1.0, zorder=5)
    if label:
        ax.text(x, y + h / 2 + 2.0, label, ha="center", va="bottom",
                fontsize=6.4, color=color, zorder=5)


def contact(ax, x, y, label=None, color=SAFE, closed=False, w=11):
    """Relay contact symbol, drawn open by default."""
    ax.plot([x - w, x - w * 0.42], [y, y], color=color, lw=1.3, zorder=4)
    ax.plot([x + w * 0.42, x + w], [y, y], color=color, lw=1.3, zorder=4)
    if closed:
        ax.plot([x - w * 0.42, x + w * 0.42], [y, y], color=color, lw=1.3, zorder=4)
    else:
        ax.plot([x - w * 0.42, x + w * 0.42], [y, y + 4.4], color=color,
                lw=1.3, zorder=4)
    ax.add_patch(Circle((x - w * 0.42, y), 1.5, facecolor=color,
                        edgecolor="none", zorder=5))
    ax.add_patch(Circle((x + w * 0.42, y), 1.5, facecolor=color,
                        edgecolor="none", zorder=5))
    if label:
        ax.text(x, y - 5.6, label, ha="center", va="top", fontsize=6.6,
                color=color, zorder=5)


def estop(ax, x, y, label="E-STOP"):
    ax.add_patch(Circle((x, y), 7.2, facecolor="#dc2626", edgecolor="#7f1d1d",
                        lw=1.3, zorder=5))
    ax.add_patch(Circle((x, y), 3.1, facecolor="#fca5a5", edgecolor="none",
                        zorder=6))
    ax.text(x, y - 10.5, label, ha="center", va="top", fontsize=6.8,
            fontweight="bold", color="#7f1d1d", zorder=5)


def note(ax, x, y, text, fs=7.4, color=DIM, w=None, ha="left", va="top"):
    ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color,
            zorder=6, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.42", facecolor="#fbfcfc",
                      edgecolor=RULE, lw=0.7))


def sheet(w_in, h_in, xlim, ylim, title, subtitle, sheet_no, rev="E"):
    fig = plt.figure(figsize=(w_in, h_in), facecolor="white")
    ax = fig.add_axes([0.012, 0.012, 0.976, 0.976])
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
    ax.add_patch(Rectangle((xlim[0], ylim[0]), xlim[1] - xlim[0],
                           ylim[1] - ylim[0], facecolor="none",
                           edgecolor=RULE, lw=1.2, zorder=0))
    # title block, bottom right
    bw, bh = 300, 52
    bx, by = xlim[1] - bw - 8, ylim[0] + 8
    ax.add_patch(Rectangle((bx, by), bw, bh, facecolor="white",
                           edgecolor=INK, lw=1.1, zorder=7))
    ax.plot([bx, bx + bw], [by + bh - 20, by + bh - 20], color=INK, lw=0.8,
            zorder=8)
    ax.plot([bx + bw - 86, bx + bw - 86], [by, by + bh - 20], color=INK,
            lw=0.8, zorder=8)
    ax.text(bx + 7, by + bh - 10, "RED TOWER  ·  HERB TOWER", fontsize=8.6,
            fontweight="bold", va="center", color=INK, zorder=8)
    ax.text(bx + 7, by + bh - 34, title, fontsize=10.4, fontweight="bold",
            va="center", color=INK, zorder=8)
    ax.text(bx + 7, by + 11, subtitle, fontsize=7.0, va="center", color=DIM,
            zorder=8)
    ax.text(bx + bw - 43, by + bh - 34, sheet_no, fontsize=13,
            fontweight="bold", ha="center", va="center", color=INK, zorder=8)
    ax.text(bx + bw - 43, by + 11, f"Rev {rev}  ·  not to scale",
            fontsize=6.8, ha="center", va="center", color=DIM, zorder=8)
    return fig, ax


def legend(ax, x, y, items, fs=7.2, dy=11.0, title="Nets"):
    ax.text(x, y, title, fontsize=7.8, fontweight="bold", color=INK,
            va="center", zorder=6)
    for i, (c, t) in enumerate(items):
        yy = y - (i + 1) * dy
        ax.plot([x, x + 17], [yy, yy], color=c, lw=2.3, zorder=6)
        ax.text(x + 22, yy, t, fontsize=fs, color=INK, va="center", zorder=6)
