#!/usr/bin/env python3
"""Mounting slot schedule, read back out of the shipped DXFs (not re-drawn from the model)."""
import math
import brackets as BK
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, LINE, DIM, HOLE = "#1B2629", "#5E6E70", "#1F6F8B", "#B3261E"
SRC = "/home/claude/greenhouse/sendcutsend"


def parse(path):
    t = open(path).read().split("\n")
    pairs = [(t[j].strip(), t[j + 1].strip()) for j in range(0, len(t) - 1, 2)]
    cur, out = None, []
    for code, val in pairs:
        if code == "0":
            if cur:
                out.append(cur)
            cur = {"type": val} if val in ("LINE", "ARC", "CIRCLE") else None
        elif cur is not None:
            cur.setdefault(code, []).append(val)
    if cur:
        out.append(cur)
    return out


def read(path):
    ents = parse(path)
    caps = [(float(e["10"][0]), float(e["20"][0])) for e in ents
            if e["type"] == "ARC" and abs(float(e["40"][0]) - 4.5) < 1e-6]
    slots = []
    for i, a in enumerate(caps):
        for j, b in enumerate(caps):
            if i < j and abs(math.dist(a, b) - 9.0) < 0.01:
                slots.append((((a[0] + b[0]) / 2, (a[1] + b[1]) / 2),
                              "x" if abs(a[1] - b[1]) < 1e-6 else "y"))
    cut, bend, arcs, drain = [], [], [], []
    for e in ents:
        if e["type"] == "LINE":
            seg = ((float(e["10"][0]), float(e["20"][0])),
                   (float(e["11"][0]), float(e["21"][0])))
            (bend if e.get("6", [""])[0] == "DASHED" else cut).append(seg)
        elif e["type"] == "ARC":
            r = float(e["40"][0])
            if abs(r - 4.5) > 1e-6:
                arcs.append(((float(e["10"][0]), float(e["20"][0])), r,
                             float(e["50"][0]), float(e["51"][0])))
        else:
            drain.append(((float(e["10"][0]), float(e["20"][0])), float(e["40"][0])))
    return slots, cut, bend, arcs, drain


GAP = {}
for _p, _m, _x, _y, _r, _g in BK.clearances():
    _k = (_p, round(_x), round(_y, 1))
    GAP[_k] = min(GAP.get(_k, 1e9), _g)

LANDS = {20.0: "front longitudinal", 183.0: "shelf rail", 437.0: "back longitudinal"}
PARTS = [("tray_DOWN", 3, 0.0, "tray"), ("tray_UP", 3, 660.0, "tray"),
         ("basepan_DOWN", 1, 0.0, "base pan"), ("basepan_UP", 1, 660.0, "base pan")]

fig = plt.figure(figsize=(13.6, 13.2), facecolor="#FBFCFA")
fig.suptitle("Herb Tower  ·  mounting slot schedule  ·  Rev 5",
             fontsize=15, fontweight="bold", color=INK, x=.045, ha="left", y=.982)
fig.text(.045, .958,
         "Parsed straight out of the four .dxf files that go to SendCutSend, so this drawing cannot show a hole the cutter will not make.\n"
         "Every slot is 9 x 18 mm, on the top-face slot centreline of the profile it lands on. Dashed = bend lines. Open ring = drain pilot.\n"
         "The last column is the clear slot between that fastener and the nearest Rev 5 bracket in the same channel.",
         fontsize=8.4, color=LINE, va="top", linespacing=1.6)

total = 0
for k, (name, qty, dx, piece) in enumerate(PARTS):
    slots, cut, bend, arcs, drain = read(f"{SRC}/{name}.dxf")
    total += len(slots) * qty
    xs = [p[0] for s in cut for p in s]; ys = [p[1] for s in cut for p in s]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)

    ax = fig.add_axes([.045, .715 - k * .218, .615, .175])
    for p, q in cut:
        ax.plot([p[0], q[0]], [p[1], q[1]], "-", color=INK, lw=1.3, zorder=3)
    for c, r, a0, a1 in arcs:
        a1x = a1 if a1 > a0 else a1 + 360
        th = [math.radians(a0 + (a1x - a0) * j / 24) for j in range(25)]
        ax.plot([c[0] + r * math.cos(t) for t in th],
                [c[1] + r * math.sin(t) for t in th], "-", color=INK, lw=1.3, zorder=3)
    for p, q in bend:
        ax.plot([p[0], q[0]], [p[1], q[1]], "--", color="#9DB3BC", lw=.9, zorder=1)
    for (cx, cy), al in slots:
        w, h = (18, 9) if al == "x" else (9, 18)
        ax.add_patch(plt.Rectangle((cx - w / 2, cy - h / 2), w, h, fc=HOLE,
                                   ec="none", zorder=5))
    for c, r in drain:
        ax.add_patch(plt.Circle(c, r, fill=False, color=HOLE, lw=1.6, zorder=5))
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(x0 - 15, x1 + 15); ax.set_ylim(y0 - 15, y1 + 15)
    ax.set_title(f"{name}.dxf   ·   qty {qty}   ·   {len(slots)} mounting slots"
                 + ("   + drain pilot" if drain else ""),
                 fontsize=10.5, fontweight="bold", color=INK, loc="left", pad=3)

    tx = fig.add_axes([.675, .715 - k * .218, .30, .175])
    tx.axis("off")
    rows = sorted(slots, key=lambda s: (round(s[0][1]), s[0][0]))
    tx.text(0, 1.0, "slot (frame)  lands on          gap", fontsize=7.6, color=LINE,
            family="monospace", va="top", transform=tx.transAxes)
    for i, ((cx, cy), al) in enumerate(rows):
        gx = cx + dx
        lab = LANDS.get(round(cy, 1))
        if lab is None:
            lab = "mid rail" if 650 <= gx <= 710 else "side member"
        gap = GAP.get((piece, round(gx), round(cy, 1)))
        g = f"{gap:5.0f}" if gap is not None else "    -"
        tx.text(0, .90 - i * .105, f"({gx:>5.0f},{cy:>5.0f})   {lab:<18}{g}",
                fontsize=7.6, color=INK, family="monospace", va="top",
                transform=tx.transAxes)

fig.text(.045, .028, f"{BK.SLOTS} slots across the 8 pieces, but {BK.BOLTS} fasteners: the four lap bolts each pierce two sheets into one T-nut. Tightest bracket clearance anywhere: 16 mm.",
         fontsize=8.4, color=LINE)
fig.text(.955, .015, "Rev 5  ·  2026-10-10", fontsize=7.5, color=LINE, ha="right")
fig.savefig("slot_schedule.png", dpi=150, facecolor="#FBFCFA")
print("total fasteners", total)
