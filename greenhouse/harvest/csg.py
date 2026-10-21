"""Watertight solids for the printed parts, on manifold3d.

kit3d meshes are triangle soups that overlap where parts meet, which is fine
for drawing and wrong for a printer. Everything that becomes an STL is built
here as a real boolean solid, and the same solid is what the booklet draws.

    pip install manifold3d       (3.5 or later)
"""
import math

import numpy as np
import manifold3d as M


def box(x0, y0, z0, x1, y1, z1):
    return M.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def rbox(x0, y0, z0, x1, y1, z1, r, axis="z", n=24):
    """A box with its edges along `axis` rounded to r."""
    if axis == "z":
        prof = rrect(x0, y0, x1, y1, r, n)
        return M.Manifold.extrude(M.CrossSection([prof]), z1 - z0).translate([0, 0, z0])
    if axis == "x":
        prof = rrect(y0, z0, y1, z1, r, n)
        s = M.Manifold.extrude(M.CrossSection([prof]), x1 - x0)
        # extrude runs along +z: turn (y, z, x) into (x, y, z)
        return _uvw(s, (1, 2, 0)).translate([x0, 0, 0])
    prof = rrect(x0, z0, x1, z1, r, n)
    s = M.Manifold.extrude(M.CrossSection([prof]), y1 - y0)
    return _uvw(s, (0, 2, 1)).translate([0, y0, 0])


def _uvw(s, perm):
    """Map a solid built with its profile in (u, v) and its depth along w onto
    world axes: perm = (axis of u, axis of v, axis of w)."""
    m = np.zeros((3, 4))
    for src, dst in enumerate(perm):
        m[dst, src] = 1.0
    return s.transform(m)      # manifold flips the winding itself when det < 0


def rrect(x0, y0, x1, y1, r, n=24):
    r = max(0.0, min(r, (x1 - x0) / 2 - 1e-6, (y1 - y0) / 2 - 1e-6))
    if r <= 0:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    pts = []
    for (cx, cy), a0 in (((x1 - r, y0 + r), -90), ((x1 - r, y1 - r), 0), ((x0 + r, y1 - r), 90), ((x0 + r, y0 + r), 180)):
        for k in range(n // 4 + 1):
            a = math.radians(a0 + 90 * k / (n // 4))
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism(poly, axis, a0, a1):
    """Extrude a 2D polygon, given in the plane normal to `axis`, from a0 to a1.
    Plane coordinates: axis x -> (y, z); y -> (x, z); z -> (x, y)."""
    cs = M.CrossSection([list(map(tuple, poly))], M.FillRule.EvenOdd)
    s = M.Manifold.extrude(cs, a1 - a0)
    if axis == "z":
        return s.translate([0, 0, a0])
    if axis == "x":
        return _uvw(s, (1, 2, 0)).translate([a0, 0, 0])
    return _uvw(s, (0, 2, 1)).translate([0, a0, 0])


def cyl(r, h, axis="z", c=(0, 0, 0), n=40, r2=None):
    s = M.Manifold.cylinder(h, r, r if r2 is None else r2, n)
    if axis == "x":
        s = _uvw(s, (1, 2, 0))
    elif axis == "y":
        s = _uvw(s, (0, 2, 1))
    return s.translate(list(c))


def hexprism(af, h, axis="z", c=(0, 0, 0)):
    R = af / math.sqrt(3)
    poly = [(R * math.cos(math.pi / 6 + k * math.pi / 3), R * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
    s = M.Manifold.extrude(M.CrossSection([poly]), h)
    if axis == "x":
        s = _uvw(s, (1, 2, 0))
    elif axis == "y":
        s = _uvw(s, (0, 2, 1))
    return s.translate(list(c))


def union(*solids):
    out = solids[0]
    for s in solids[1:]:
        out = out + s
    return out


def to_mesh(s):
    m = s.to_mesh()
    V = np.asarray(m.vert_properties, float)[:, :3]
    F = np.asarray(m.tri_verts, int)
    return V, F


def write_stl(s, path, name="maag"):
    """Binary STL, millimetres."""
    V, F = to_mesh(s)
    T = V[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    n = n / np.where(ln > 0, ln, 1)[:, None]
    rec = np.zeros(len(F), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    rec["n"] = n
    rec["v"] = T
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b" "))
        f.write(np.uint32(len(F)).tobytes())
        f.write(rec.tobytes())
    return len(F)


def stats(s):
    V, F = to_mesh(s)
    return dict(volume=s.volume(), tris=len(F), genus=s.genus(), lo=V.min(0), hi=V.max(0))
