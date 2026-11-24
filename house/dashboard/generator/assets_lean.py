# The lean house in lines for the live card: per view one SVG whose polylines are grouped by floor and kind
# (c crease, p profile), plus the layout file (outlines, room boxes, openings, anchors). Same crop as before.
#   python -I assets_lean.py views4.json OUTDIR
import json, sys, os
d = json.load(open(sys.argv[1])); out = sys.argv[2]
os.makedirs(out, exist_ok=True)
views = d["views"]
x0 = min(v["bbox"][0] for v in views) - 16; y0 = min(v["bbox"][1] for v in views) - 16
x1 = max(v["bbox"][2] for v in views) + 16; y1 = max(v["bbox"][3] for v in views) + 16
CW, CH = x1 - x0, y1 - y0
r1 = lambda v: round(v - x0, 1)
r2 = lambda v: round(v - y0, 1)


def poly_path(pls):
    return "".join("M" + "L".join(f"{x - x0:.1f} {y - y0:.1f}" for x, y in pts) for pts in pls)


def loops(ls):
    return [[[r1(x), r2(y)] for x, y in pts] for pts in ls]


lay = {"crop": [CW, CH], "views": []}
for k, v in enumerate(views):
    g = []
    for cls, name in (("1", "c"), ("2", "p")):
        for f in (1, 2, 3):
            pls = v["lines"].get(f"{cls}:@{f}", [])
            if pls:
                g.append(f'<path class="{name} f{f}" d="{poly_path(pls)}" vector-effect="non-scaling-stroke"/>')
    open(os.path.join(out, f"axo-v{k}.svg"), "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" fill="none" stroke-linecap="square" stroke-linejoin="miter">' + "".join(g) + "</svg>")
    lay["views"].append({
        "bbox": [r1(v["bbox"][0]), r2(v["bbox"][1]), r1(v["bbox"][2]), r2(v["bbox"][3])],
        "anchors": {a: [r1(p[0]), r2(p[1])] for a, p in v["anchors"].items()},
        "floors": {f: loops(ls) for f, ls in v["contours"].items()},
        "boxes": {r: dict(lvl=b["lvl"], fill=loops(b["fill"]), edges=[[r1(a), r2(b_), r1(c), r2(e)] for a, b_, c, e in b["edges"]], anchor=[r1(b["anchor"][0]), r2(b["anchor"][1])])
                  for r, b in v["boxes"].items()},
        "openings": {o: dict(seen=[[r1(a), r2(b_), r1(c), r2(e)] for a, b_, c, e in x["seen"]], hidden=[[r1(a), r2(b_), r1(c), r2(e)] for a, b_, c, e in x["hidden"]],
                             anchor=[r1(x["anchor"][0]), r2(x["anchor"][1])]) for o, x in v["openings"].items()},
    })
json.dump(lay, open(os.path.join(out, "axo-layout.json"), "w"), separators=(",", ":"))
print("crop", CW, CH, "svg KB", [round(os.path.getsize(os.path.join(out, f"axo-v{k}.svg")) / 1024, 1) for k in range(8)],
      "layout KB", round(os.path.getsize(os.path.join(out, "axo-layout.json")) / 1024))
