# The lean axonometry (axo3.py: each boundary drawn once, straightened) as SVG files plus the layout file the boards use.
#   python -I drawings_plain.py VIEWS.json MASSING.json OUTDIR [--red 2,3]
#   (VIEWS from axo3.py; MASSING from axo2.py --massing; the pictures for the notification use axo-plain-v*.svg)
# Round 5 (Vittorio, 23 Nov): no room plans. A floor with something not nominal is outlined in red from the outside,
# even where the tower shows no floor line, and every line of that floor turns red too. When everything is nominal,
# only the house's apparent outline is drawn, in the greenhouse green.
#   axo-v0..7.svg   the eight views as the house is now (the floors in --red drawn red)
#   axo-ok-v0.svg   view 0 with everything nominal: the green outline
#   axo-mass.svg    the house as two plain volumes, for Consumption
#   axo-plain-v0..7.svg  the eight views with no state at all (RedSec draws its alarms, or the green outline, on top)
import json, sys, os, math

args = [a for a in sys.argv[1:] if not a.startswith("--")]
d = json.load(open(args[0]))
mass = json.load(open(args[1]))
out = args[2]
red = set()
if "--red" in sys.argv:
    red = {int(x) for x in sys.argv[sys.argv.index("--red") + 1].split(",") if x}
os.makedirs(out, exist_ok=True)
views = d["views"]
# one crop for all views, so the house turns about its own axis without jumping
x0 = min(v["bbox"][0] for v in views) - 16; y0 = min(v["bbox"][1] for v in views) - 16
x1 = max(v["bbox"][2] for v in views) + 16; y1 = max(v["bbox"][3] for v in views) + 16
CW, CH = x1 - x0, y1 - y0
GRAY, WHITE, RED, GREEN, INK = "#8E9096", "#E6E4DE", "#ED1C24", "#7FD18B", "#F3F1EC"


def segs_path(segs, ox, oy):
    return "".join(f"M{a - ox:.1f} {b - oy:.1f}L{c - ox:.1f} {e - oy:.1f}" for a, b, c, e in segs)


def loops_path(loops, ox, oy):
    return "".join("M" + "L".join(f"{x - ox:.1f} {y - oy:.1f}" for x, y in pts) for pts in loops)


def stroke(dd, col, w, extra=""):
    return (f'<path d="{dd}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="square" stroke-linejoin="round" '
            f'vector-effect="non-scaling-stroke"{extra}/>') if dd else ""


def lines(v, cls, floors):
    return [pl for k, pls in v["lines"].items() if k.startswith(cls + ":@") and int(k.split("@")[1]) in floors for pl in pls]


def poly_path(pls, ox, oy):
    return "".join("M" + "L".join(f"{x - ox:.1f} {y - oy:.1f}" for x, y in pts) for pts in pls)


def svg(v, red_floors, outline=True):
    ok = [f for f in (1, 2, 3) if f not in red_floors]
    bad = sorted(red_floors)
    body = [stroke(poly_path(lines(v, "1", ok), x0, y0), GRAY, 0.8),
            stroke(poly_path(lines(v, "2", ok), x0, y0), WHITE, 1.1),
            stroke(poly_path(lines(v, "1", bad), x0, y0), RED, 0.8, ' stroke-opacity="0.72"'),
            stroke(poly_path(lines(v, "2", bad), x0, y0), RED, 1.1)]
    if bad:
        body += [stroke(loops_path(v["contours"][str(f)], x0, y0), RED, 1.8) for f in bad]
    elif outline:
        body.append(stroke(loops_path(v["contours"]["all"], x0, y0), GREEN, 1.8))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}">' + "".join(body) + "</svg>")


sizes = []
for k, v in enumerate(views):
    s = svg(v, red)
    open(os.path.join(out, f"axo-v{k}.svg"), "w").write(s)
    sizes.append(len(s))
ok0 = svg(views[0], set())
open(os.path.join(out, "axo-ok-v0.svg"), "w").write(ok0)
for k, v in enumerate(views):
    open(os.path.join(out, f"axo-plain-v{k}.svg"), "w").write(svg(v, set(), outline=False))

# the two volumes, cropped to themselves
mx0, my0, mx1, my1 = mass["bbox"]
mx0 -= 14; my0 -= 14; mx1 += 14; my1 += 14
MW, MH = mx1 - mx0, my1 - my0
ms = [s for k, ss in mass["segs"].items() for s in ss]
msvg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {MW} {MH}" width="{MW}" height="{MH}">'
        + stroke(segs_path(ms, mx0, my0), INK, 1.2) + "</svg>")
open(os.path.join(out, "axo-mass.svg"), "w").write(msvg)

lay = {"crop": [x0, y0, CW, CH], "mass": [MW, MH], "red": sorted(red), "views": []}
for v in views:
    lay["views"].append({"az": v["az"],
                         "rooms": {k: v["segs"][k] for k in v["segs"] if k[0] in "56"},
                         "watch": {k: v["segs"][k] for k in v["segs"] if k[0] in "34"},
                         "floors": {k: [[[x - x0, y - y0] for x, y in pts] for pts in loops] for k, loops in v["contours"].items()},
                         "boxes": {r: dict(lvl=b["lvl"], fill=[[[x - x0, y - y0] for x, y in pts] for pts in b["fill"]],
                                           edges=[[a - x0, b_ - y0, c - x0, e - y0] for a, b_, c, e in b["edges"]], anchor=[b["anchor"][0] - x0, b["anchor"][1] - y0])
                                   for r, b in v.get("boxes", {}).items()},
                         "openings": {o: dict(seen=[[a - x0, b_ - y0, c - x0, e - y0] for a, b_, c, e in d_["seen"]],
                                              hidden=[[a - x0, b_ - y0, c - x0, e - y0] for a, b_, c, e in d_["hidden"]],
                                              anchor=[d_["anchor"][0] - x0, d_["anchor"][1] - y0]) for o, d_ in v.get("openings", {}).items()},
                         "anchors": {k: [a - x0, b - y0] for k, (a, b) in v["anchors"].items()},
                         "bbox": [v["bbox"][0] - x0, v["bbox"][1] - y0, v["bbox"][2] - x0, v["bbox"][3] - y0],
                         "rows": {str(int(y) - y0): [a - x0, b - x0] for y, (a, b) in v["rows"].items()}})
json.dump(lay, open(os.path.join(out, "axo-layout.json"), "w"))
print("crop", CW, CH, "svg KB", [round(x / 1024) for x in sizes], "ok KB", round(len(ok0) / 1024), "mass", MW, MH, round(len(msvg) / 1024), "KB")
