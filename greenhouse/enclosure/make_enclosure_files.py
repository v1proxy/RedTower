#!/usr/bin/env python3
"""Cut and print files for the Maag enclosure, Rev A, all from enclosure.py.

    acplastics/   six frosted panels, 1/8 in TUFFAK GP Matte, as DXF (mm),
                  each drawn as seen from OUTSIDE the cabinet, plus
                  Maag_Enclosure_Panels_RevA.pdf: the nest, every panel with
                  its hole table, for A&C Plastics' quote form
    sendcutsend/  doors (polycarbonate 0.177 in, clear), hinge spacers and
                  astragals (polycarbonate 0.118 in, clear), seam battens
                  (5052 aluminium 0.125 in)
    print/        duct_collar.stl, PETG

    python make_enclosure_files.py
"""
import math
import os
import struct
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "sendcutsend"))
import enclosure as E                                      # noqa: E402
from unfold import Dxf                                     # noqa: E402

AC = os.path.join(_HERE, "acplastics")
SCS = os.path.join(_HERE, "sendcutsend")
PRN = os.path.join(_HERE, "print")
for d in (AC, SCS, PRN):
    os.makedirs(d, exist_ok=True)


def rrect(dx, x0, y0, x1, y1, r):
    """Rectangle with radius-r corners, as lines and arcs."""
    if r <= 0:
        for p, q in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            dx.line(p, q)
        return
    dx.line((x0 + r, y0), (x1 - r, y0)); dx.arc((x1 - r, y0 + r), r, 270, 360)
    dx.line((x1, y0 + r), (x1, y1 - r)); dx.arc((x1 - r, y1 - r), r, 0, 90)
    dx.line((x1 - r, y1), (x0 + r, y1)); dx.arc((x0 + r, y1 - r), r, 90, 180)
    dx.line((x0, y1 - r), (x0, y0 + r)); dx.arc((x0 + r, y0 + r), r, 180, 270)


def outside(name, u, v):
    """Panel face (u, v) to the DXF's (x, y), the panel seen from outside,
    origin at the panel's lower left corner as you look at it."""
    face, u0, v0, u1, v1 = E.panels()[name]
    if face == "left":           # from outside the left face, the front is on your right: +y runs left
        return (u1 - u), (v - v0)
    if face == "back":           # from behind, +x runs left
        return (u1 - u), (v - v0)
    return (u - u0), (v - v0)


def panel_dxf(name):
    face, u0, v0, u1, v1 = E.panels()[name]
    d = Dxf()
    rrect(d, 0.0, 0.0, u1 - u0, v1 - v0, 3.0)
    rows = []
    for u, v, dia, what in E.panel_holes(name):
        x, y = outside(name, u, v)
        d.circle((x, y), dia / 2)
        rows.append((x, y, dia, what))
    for ra, rb, rc, rd, r, what in E.panel_rects(name):
        xa, ya = outside(name, ra, rb)
        xb, yb = outside(name, rc, rd)
        x0, x1 = sorted((xa, xb))
        y0, y1 = sorted((ya, yb))
        rrect(d, x0, y0, x1, y1, r)
        rows.append(((x0 + x1) / 2, (y0 + y1) / 2, ("rect", x1 - x0, y1 - y0, r), what))
    path = os.path.join(AC, f"panel_{name}.dxf")
    open(path, "w").write(d.dumps())
    return path, rows, (u1 - u0, v1 - v0)


def door_dxf(pair, side):
    d = Dxf()
    x0, x1 = E.door_x(side)
    z0, z1 = E.door_z(pair)
    rrect(d, 0.0, 0.0, x1 - x0, z1 - z0, 3.0)
    for x, z in E.pull_holes(pair, side):
        d.circle((x - x0, z - z0), E.PULL["screw"] / 2)
    path = os.path.join(SCS, f"door_{pair}_{side}.dxf")
    open(path, "w").write(d.dumps())
    return path, (x1 - x0, z1 - z0)


def spacer_dxf():
    out, slot = E.spacer_outline()
    d = Dxf()
    a_, b_ = out[0][0], out[1][0]
    L = out[2][1]
    rrect(d, 0.0, 0.0, b_ - a_, L, 1.0)
    h = E.SPACER_SLOT / 2
    cx = (slot[0][0] + slot[1][0]) / 2 - a_
    d.slot((cx, slot[0][1] + h), (cx, slot[2][1] - h), E.SPACER_SLOT)
    path = os.path.join(SCS, "hinge_spacer.dxf")
    open(path, "w").write(d.dumps())
    return path, (b_ - a_, L)


def astragal_dxf(pair):
    z0, z1 = E.astragal_span(pair)
    d = Dxf()
    rrect(d, 0.0, 0.0, E.ASTRAGAL["w"], z1 - z0, 2.0)
    path = os.path.join(SCS, f"astragal_{pair}.dxf")
    open(path, "w").write(d.dumps())
    return path, (E.ASTRAGAL["w"], z1 - z0)


def batten_dxf():
    u0, u1, hs = E.batten_pieces()[0]
    d = Dxf()
    rrect(d, 0.0, 0.0, u1 - u0, E.BATTEN["w"], 2.0)
    for u in hs:
        d.circle((u - u0, E.BATTEN["w"] / 2), E.BATTEN["hole"] / 2)
    path = os.path.join(SCS, "seam_batten.dxf")
    open(path, "w").write(d.dumps())
    return path, (u1 - u0, E.BATTEN["w"])


def write_stl(path, meshes, name):
    tris = []
    for V, F in meshes:
        for a, b, c in F:
            tris.append((V[a], V[b], V[c]))
    with open(path, "wb") as fh:
        fh.write(name.encode("ascii")[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            n = np.cross(np.subtract(b, a), np.subtract(c, a))
            ln = float(np.linalg.norm(n)) or 1.0
            fh.write(struct.pack("<12fH", *(n / ln), *a, *b, *c, 0))
    return len(tris)


def drawing_pdf(panel_rows):
    """The A&C drawing: the nest, then one page per panel with its hole table."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Rectangle, Circle
    sys.path.insert(0, os.path.join(_HERE, "..", "booklet"))
    import maagbook as B
    INK, DIM = B.INK, B.DIM
    path = os.path.join(AC, "Maag_Enclosure_Panels_RevA.pdf")
    with PdfPages(path) as pdf:
        # ---- page 1: the order and the nest
        fig = plt.figure(figsize=(11, 8.5))
        ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1100); ax.set_ylim(0, 850)
        ax.text(50, 800, "Maag enclosure  ·  frosted panels, Rev A", fontsize=17, family=B.TITLE_FONT,
                fontweight="semibold", color=INK)
        ax.text(50, 770, "TUFFAK GP Matte polycarbonate, 1/8 in (3.175 mm), frosted. Three 48 × 96 in sheets, "
                         "six panels. Cut to size and drill.", fontsize=10.5, color=INK)
        ax.text(50, 748, "All dimensions mm. Hole positions from each panel's lower left corner, seen from the side "
                         "that faces OUT (the DXFs are drawn the same way).", fontsize=10.5, color=INK)
        ax.text(50, 726, "Tolerances: outline ± 1, hole positions ± 0.5, holes + 0.3 / − 0. Corners R3. Keep the "
                         "protective film on until install; please deburr the holes.", fontsize=10.5, color=INK)
        s = 0.24
        for k, (sh, rows, spare_a, spare_l) in enumerate(E.nest()):
            x0, y0 = 70 + k * 340, 80
            ax.add_patch(Rectangle((x0, y0), E.SHEET[0] * s, E.SHEET[1] * s, facecolor="#f5f7f8",
                                   edgecolor=INK, lw=0.9))
            ax.text(x0, y0 + E.SHEET[1] * s + 14, f"Sheet {sh}  ·  48 × 96 in", fontsize=10, color=INK,
                    fontweight="bold")
            cx = x0
            for n, a, b in rows:
                ax.add_patch(Rectangle((cx, y0), a * s, b * s, facecolor="#e6ecef", edgecolor=INK, lw=0.8))
                ax.text(cx + a * s / 2, y0 + b * s / 2, f"{n.replace('_', ' ')}\n{a:.1f} × {b:.1f}", fontsize=7.6,
                        ha="center", va="center", rotation=90, color=INK)
                cx += (a + E.KERF) * s
            ax.text(x0, y0 - 18, f"spare {spare_a:.0f} across, {spare_l:.0f} along", fontsize=8.4, color=DIM)
        ax.text(1050, 30, "Maag  ·  Enclosure Rev A  ·  drawn from enclosure.py", fontsize=8, color=DIM, ha="right")
        pdf.savefig(fig); plt.close(fig)
        # ---- one page per panel
        for name, (dxf, rows, (pw, ph)) in panel_rows.items():
            fig = plt.figure(figsize=(11, 8.5))
            ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1100); ax.set_ylim(0, 850)
            ax.set_aspect("equal")
            ax.text(50, 800, f"Panel  ·  {name.replace('_', ' ')}  ·  {pw:.1f} × {ph:.1f}  ·  qty 1", fontsize=16,
                    family=B.TITLE_FONT, fontweight="semibold", color=INK)
            ax.text(50, 774, f"File: acplastics/{os.path.basename(dxf)}. Seen from outside. "
                             f"{len(rows)} holes.", fontsize=10, color=DIM)
            box_w, box_h = 620, 640
            sc = min(box_w / pw, box_h / ph)
            ox, oy = 50, 80
            ax.add_patch(Rectangle((ox, oy), pw * sc, ph * sc, facecolor="#f5f7f8", edgecolor=INK, lw=1.0))
            for x, y, dia, what in rows:
                if isinstance(dia, tuple):
                    _, rw, rh, rr = dia
                    ax.add_patch(Rectangle((ox + (x - rw / 2) * sc, oy + (y - rh / 2) * sc), rw * sc, rh * sc,
                                           facecolor="white", edgecolor=INK, lw=0.7))
                    continue
                ax.add_patch(Circle((ox + x * sc, oy + y * sc), max(dia / 2 * sc, 1.6), facecolor="white",
                                    edgecolor=INK, lw=0.7))
            ax.text(ox, oy - 22, "lower left corner = (0, 0)", fontsize=8.4, color=DIM)
            face = E.panels()[name][0]
            edges = {"left": ("bottom: floor", "right edge: FRONT of the cabinet"),
                     "right": ("bottom: floor", "left edge: FRONT of the cabinet"),
                     "back": ("bottom: floor side", "seen from behind the cabinet"),
                     "top": ("bottom edge: FRONT of the cabinet", "seen from above")}[face]
            ax.text(ox + pw * sc / 2, oy - 40, edges[0] + "  ·  " + edges[1], fontsize=8.6, color=INK,
                    ha="center")
            # hole table, grouped by size
            groups = {}
            rects = [(x, y, dia, what) for x, y, dia, what in rows if isinstance(dia, tuple)]
            for x, y, dia, what in rows:
                if isinstance(dia, tuple):
                    continue
                groups.setdefault((dia, what if dia > 8 or what not in ("panel", "clip", "antitip") else "screw"),
                                  []).append((x, y))
            tx, ty = 710, 740
            for x, y, (_, rw, rh, rr), what in rects:
                ax.text(tx, ty, f"{rw:g} × {rh:g}, corners R{rr:g}  ·  {what}", fontsize=9.6, fontweight="bold",
                        color=INK)
                ty -= 16
                ax.text(tx + 8, ty, f"centre ({x:.1f}, {y:.1f})", fontsize=7.6, color=INK, family=B.TITLE_FONT)
                ty -= 20
            for (dia, what), pts in sorted(groups.items(), key=lambda kv: -kv[0][0]):
                label = {"screw": "screw holes", "fan": "fan opening", "intake": "intake opening",
                         "duct": "duct", "gland": "cable gland PG21", "grommet": "grommet",
                         "feeder M5": "screw holes, harvest feeder", "feeder well nut": "well nuts, harvest feeder",
                         "reed wire": "feeder switch cable"}.get(what, what)
                ax.text(tx, ty, f"Ø {dia:g}  ×{len(pts)}  ·  {label}", fontsize=9.6, fontweight="bold", color=INK)
                ty -= 16
                line = ""
                for i, (x, y) in enumerate(sorted(pts, key=lambda p: (round(p[1], 1), p[0]))):
                    line += f"({x:.1f}, {y:.1f})  "
                    if (i + 1) % 3 == 0:
                        ax.text(tx + 8, ty, line, fontsize=7.6, color=INK, family=B.TITLE_FONT); ty -= 12.5; line = ""
                if line:
                    ax.text(tx + 8, ty, line, fontsize=7.6, color=INK, family=B.TITLE_FONT); ty -= 12.5
                ty -= 8
            ax.text(1050, 30, "Maag  ·  Enclosure Rev A  ·  drawn from enclosure.py", fontsize=8, color=DIM,
                    ha="right")
            pdf.savefig(fig); plt.close(fig)
    return path


def main():
    report = {}
    rows = {}
    for n in E.panels():
        p, r, wh = panel_dxf(n)
        rows[n] = (p, r, wh)
        report[os.path.relpath(p, _HERE)] = f"{wh[0]:.1f} x {wh[1]:.1f}, {len(r)} holes and openings"
    for pair, side in E.DOORS:
        p, wh = door_dxf(pair, side)
        report[os.path.relpath(p, _HERE)] = f"{wh[0]:.1f} x {wh[1]:.1f}"
    p, wh = spacer_dxf(); report[os.path.relpath(p, _HERE)] = f"{wh[0]:.2f} x {wh[1]:.1f}, qty 8"
    for pair in ("bottom", "top"):
        p, wh = astragal_dxf(pair); report[os.path.relpath(p, _HERE)] = f"{wh[0]:.1f} x {wh[1]:.1f}, qty 1"
    p, wh = batten_dxf(); report[os.path.relpath(p, _HERE)] = f"{wh[0]:.1f} x {wh[1]:.1f}, qty 4"
    fl, sp = E.collar_solid()
    n = write_stl(os.path.join(PRN, "duct_collar.stl"), [fl, sp], "maag_duct_collar")
    report["print/duct_collar.stl"] = f"{n} triangles"
    report[os.path.relpath(drawing_pdf(rows), _HERE)] = f"{1 + len(rows)} pages"
    for k, v in report.items():
        print(f"  {k:44s} {v}")


if __name__ == "__main__":
    main()
