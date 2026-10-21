#!/usr/bin/env python3
"""Cut and print files for Maag harvest, Rev B, all from harvest.py.

    sendcutsend/  guide_rail_L.dxf, guide_rail_R.dxf   5052 H32 0.063 in, two bends each
                  deadleaf_tray.dxf                     5052 H32 0.063 in, six bends
                  feeder_lid.dxf                        polycarbonate 0.177 in, clear, flat
    print/        deadleaf_handle.stl; feeder_hood_leaves.stl, feeder_hood_veggies.stl;
                  feeder_basin.stl, feeder_skirt.stl, feeder_tray.stl (print two of each)

The right panel's openings and holes are in the enclosure's own files:
run greenhouse/enclosure/make_enclosure_files.py after any change here.

    python make_harvest_files.py
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "sendcutsend"))
import harvest as Hv                                       # noqa: E402
import csg                                                 # noqa: E402
from unfold import Dxf                                     # noqa: E402

SCS = os.path.join(_HERE, "sendcutsend")
PRN = os.path.join(_HERE, "print")
for d in (SCS, PRN):
    os.makedirs(d, exist_ok=True)

BD, HB = Hv.BD, Hv.BD / 2


def poly(dx, pts, closed=True):
    n = len(pts)
    for i in range(n if closed else n - 1):
        dx.line(pts[i], pts[(i + 1) % n])


# ------------------------------------------------------------------ guide rails
def rail_flat():
    """The right rail's flat pattern in (s, y): s = 0 the bottom flange's free
    edge, y as in the cabinet. Returns (outline, holes, bend lines, notes)."""
    r = Hv.RAIL
    s1 = r["bottom"] - HB
    s2 = s1 + (r["run"] - Hv.PAN_TOP) - BD
    s3 = s2 + r["top"] - HB
    st = s1 + (r["tab"] - Hv.PAN_TOP) - HB
    y0, y1, ys = r["y0"], r["y1"], r["stop"]
    rel = 1.0
    out = [(0.0, y0), (s3, y0), (s3, ys - 1.0), (s2 - 2.0, ys - 1.0), (s2 - 2.0, ys + 1.0), (st, ys + 1.0),
           (st, y1), (0.0, y1)]
    holes = [(r["bottom"] - 20.0, y, r["hole"] / 2) for y in Hv.BOLT_Y]
    bends = [((s1, y0 + rel), (s1, y1 - rel)), ((s2, y0 + rel), (s2, ys - 1.0 - rel))]
    return out, holes, bends, dict(s1=s1, s2=s2, s3=s3, tab=st, width=st, length=y1 - y0)


def rail_dxf(side):
    out, holes, bends, info = rail_flat()
    if side == "L":                       # the mirror image: flip the flat, bend the same way
        out = [(info["width"] - s, y) for s, y in out]
        holes = [(info["width"] - s, y, rr) for s, y, rr in holes]
        bends = [((info["width"] - a[0], a[1]), (info["width"] - b[0], b[1])) for a, b in bends]
    d = Dxf()
    poly(d, out)
    for s, y, rr in holes:
        d.circle((s, y), rr)
    for a, b in bends:
        d.line(a, b, dashed=True)
    path = os.path.join(SCS, f"guide_rail_{side}.dxf")
    open(path, "w").write(d.dumps())
    return path, info


# ------------------------------------------------------------------ the tray
def tray_flat():
    """The dead-leaf tray's flat pattern in (p, q): p along x from the floor's
    outside left edge, q along y from its outside front edge."""
    t = Hv.TRAY
    Wf, Df, h = t["x1"] - t["x0"], t["y1"] - t["y0"], t["h"]
    rim_leg = t["rim"] + Hv.T               # the rim's leg runs from the wall's INSIDE face (Z bend)
    qf = BD - h                             # front wall's free edge
    qb = Df - BD + h
    l2L = HB - (h - BD)                     # the rim bends, left and right
    l2R = Wf - HB + (h - BD)
    reL = l2L - (rim_leg - HB)
    reR = l2R + (rim_leg - HB)
    g = 2.1                                 # front and back walls stop short of the side walls' inside
    c = 0.2                                 # corner relief into the side wall's root
    k = 1.5                                 # rim relief past its bend line
    e = 2.0                                 # rims inset from the wall ends
    out = [(g, qf), (Wf - g, qf), (Wf - g, e), (Wf - c, e), (Wf - c, 0.0), (l2R - k, 0.0), (l2R - k, e),
           (reR, e), (reR, Df - e), (l2R - k, Df - e), (l2R - k, Df), (Wf - c, Df), (Wf - c, Df - e),
           (Wf - g, Df - e), (Wf - g, qb), (g, qb), (g, Df - e), (c, Df - e), (c, Df), (l2L + k, Df),
           (l2L + k, Df - e), (reL, Df - e), (reL, e), (l2L + k, e), (l2L + k, 0.0), (c, 0.0), (c, e), (g, e)]
    holes = []
    for x, z in Hv.HANDLE["bolts"]:
        holes.append((x - t["x0"], BD - (z - t["z0"]), 2.75))
    bends = [((g + 1, HB), (Wf - g - 1, HB)), ((g + 1, Df - HB), (Wf - g - 1, Df - HB)),
             ((HB, e + 0.5), (HB, Df - e - 0.5)), ((Wf - HB, e + 0.5), (Wf - HB, Df - e - 0.5)),
             ((l2L, e + 1), (l2L, Df - e - 1)), ((l2R, e + 1), (l2R, Df - e - 1))]
    return out, holes, bends, dict(width=reR - reL, length=qb - qf, x0=reL, y0=qf)


def tray_dxf():
    out, holes, bends, info = tray_flat()
    d = Dxf()
    poly(d, out)
    for p, q, rr in holes:
        d.circle((p, q), rr)
    for a, b in bends:
        d.line(a, b, dashed=True)
    path = os.path.join(SCS, "deadleaf_tray.dxf")
    open(path, "w").write(d.dumps())
    return path, info


# ------------------------------------------------------------------ the feeder lid
def lid_dxf():
    L, Wd = Hv.FEEDER.lid_flat()
    d = Dxf()
    r = 3.0
    d.line((r, 0), (Wd - r, 0)); d.arc((Wd - r, r), r, 270, 360)
    d.line((Wd, r), (Wd, L - r)); d.arc((Wd - r, L - r), r, 0, 90)
    d.line((Wd - r, L), (r, L)); d.arc((r, L - r), r, 90, 180)
    d.line((0, L - r), (0, r)); d.arc((r, r), r, 180, 270)
    path = os.path.join(SCS, "feeder_lid.dxf")
    open(path, "w").write(d.dumps())
    return path, (Wd, L)


# ------------------------------------------------------------------ prints
def stls():
    f = Hv.FEEDER
    rep = {}
    s = Hv.handle_solid()
    rep["deadleaf_handle.stl"] = (csg.write_stl(_lay_handle(s), os.path.join(PRN, "deadleaf_handle.stl"),
                                                "maag_deadleaf_handle"), s.volume())
    import numpy as np
    for k, nm in enumerate(f.NAMES):
        # the hood stands on its joint face, as it hangs
        m = f.hood_solid(k).translate([-f.wb, -f.mods[k][0], -f.vj])
        rep[f"feeder_hood_{nm}.stl"] = (csg.write_stl(m, os.path.join(PRN, f"feeder_hood_{nm}.stl"),
                                                      f"maag_feeder_hood_{nm}"), m.volume())
    # the two basins are the same part, and so are the two skirts
    m = f.basin_solid(0).translate([-f.wb, -f.mods[0][0], -f.vf])
    rep["feeder_basin.stl"] = (csg.write_stl(m, os.path.join(PRN, "feeder_basin.stl"), "maag_feeder_basin"), m.volume())
    # the skirt on its open back: (w, u, v) -> (vf - v, u, w), a proper rotation
    sk = f.skirt_solid(0)
    R = np.array([[0, 0, -1, f.vf], [0, 1, 0, -f.mods[0][0]], [1, 0, 0, -f.wb]], float)
    m = sk.transform(R)
    rep["feeder_skirt.stl"] = (csg.write_stl(m, os.path.join(PRN, "feeder_skirt.stl"), "maag_feeder_skirt"), m.volume())
    w0, w1, u0, u1, v0, v1 = f.tray_box(0)
    t = f.tray_solid(0).translate([-w0, -u0, -v0])
    rep["feeder_tray.stl"] = (csg.write_stl(t, os.path.join(PRN, "feeder_tray.stl"), "maag_feeder_tray"), t.volume())
    return rep


def _lay_handle(s):
    """Print flat, the back face (against the tray) on the bed."""
    yb = Hv.TRAY["y0"]
    # (x, y, z) -> (x, z, yb - y): the back face y = yb lands on z = 0
    import numpy as np
    m = np.array([[1, 0, 0, -Hv.HANDLE["x0"]], [0, 0, 1, -Hv.HANDLE["z0"]], [0, -1, 0, yb]], float)
    return s.transform(m)


def main():
    rep = {}
    for side in ("L", "R"):
        p, info = rail_dxf(side)
        rep[os.path.relpath(p, _HERE)] = (f"flat {info['width']:.1f} x {info['length']:.1f}, bends at "
                                          f"{info['s1']:.2f} and {info['s2']:.2f}, both 90 up")
    p, info = tray_dxf()
    rep[os.path.relpath(p, _HERE)] = f"flat {info['width']:.1f} x {info['length']:.1f}, 4 walls up, 2 rims down"
    p, wh = lid_dxf()
    rep[os.path.relpath(p, _HERE)] = f"{wh[0]:.1f} x {wh[1]:.1f}"
    for k, (n, v) in stls().items():
        rep["print/" + k] = f"{n} triangles, {v / 1000:.0f} cm3 solid"
    for k, v in rep.items():
        print(f"  {k:34s} {v}")


if __name__ == "__main__":
    main()
