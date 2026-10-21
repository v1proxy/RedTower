"""Small signed-distance CAD kernel: primitives, booleans, transforms, and a
marching-cubes mesher. Units mm. Negative is inside.

Every shape is a function f(P) -> d for P of shape (N, 3). Shapes compose by
min / max, so booleans never fail, and the mesher returns a watertight
triangle mesh ready to slice.
"""
from __future__ import annotations
import math
import numpy as np
from skimage.measure import marching_cubes


# ------------------------------------------------------------- primitives
def box(lo, hi, r=0.0):
    """Axis-aligned box from corner lo to corner hi, edges rounded by r."""
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    c = (lo + hi) / 2; h = (hi - lo) / 2 - r

    def f(P):
        q = np.abs(P - c) - h
        return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r
    f.bounds = (lo, hi)
    return f


def cyl(c, r, axis, h0, h1):
    """Cylinder of radius r around an axis line through c ('x', 'y' or 'z'),
    from h0 to h1 along that axis (absolute coordinates)."""
    k = "xyz".index(axis); o = [i for i in range(3) if i != k]
    c = np.asarray(c, float)

    def f(P):
        d_r = np.hypot(P[:, o[0]] - c[o[0]], P[:, o[1]] - c[o[1]]) - r
        mid, half = (h0 + h1) / 2, (h1 - h0) / 2
        d_h = np.abs(P[:, k] - mid) - half
        q = np.stack([d_r, d_h], 1)
        return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)
    lo = c.copy(); hi = c.copy()
    lo[o] -= r; hi[o] += r; lo[k] = h0; hi[k] = h1
    f.bounds = (lo, hi)
    return f


def cone(c, r0, r1, axis, h0, h1):
    """Truncated cone around an axis line through c: radius r0 at h0, r1 at h1 (h0, h1
    absolute along the axis, like cyl). Exact on the side for countersinks; the
    distance is scaled by the slant."""
    c = np.asarray(c, float); k = "xyz".index(axis); o = [i for i in range(3) if i != k]
    R = max(r0, r1)
    lo = c.copy(); hi = c.copy(); lo[o] -= R; hi[o] += R; lo[k] = h0; hi[k] = h1
    slope = (r1 - r0) / (h1 - h0)
    cosb = 1.0 / math.sqrt(1.0 + slope * slope)

    def f(P):
        h = P[:, k]
        rr = np.hypot(P[:, o[0]] - c[o[0]], P[:, o[1]] - c[o[1]])
        rad = r0 + slope * (np.clip(h, h0, h1) - h0)
        return np.maximum((rr - rad) * cosb, np.maximum(h0 - h, h - h1))
    f.bounds = (lo, hi)
    return f


def _poly2d(P2, poly):
    """Exact signed distance to a closed polygon (N, 2) for points (M, 2)."""
    poly = np.asarray(poly, float)
    d = np.full(len(P2), np.inf); s = np.ones(len(P2))
    n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        e = b - a; w = P2 - a
        t = np.clip((w @ e) / (e @ e), 0, 1)
        dd = np.hypot(*(w - np.outer(t, e)).T)
        d = np.minimum(d, dd)
        c1 = P2[:, 1] >= a[1]; c2 = P2[:, 1] < b[1]
        c3 = e[0] * w[:, 1] > e[1] * w[:, 0]
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * d


def prism(poly, axis, h0, h1):
    """2D polygon extruded along an axis. For axis 'y' the polygon is in (x, z);
    for 'z' it is (x, y); for 'x' it is (y, z)."""
    k = "xyz".index(axis); o = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    poly = np.asarray(poly, float)

    def f(P):
        d2 = _poly2d(P[:, list(o)], poly)
        mid, half = (h0 + h1) / 2, (h1 - h0) / 2
        dh = np.abs(P[:, k] - mid) - half
        q = np.stack([d2, dh], 1)
        return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)
    lo = np.zeros(3); hi = np.zeros(3)
    lo[list(o)] = poly.min(0); hi[list(o)] = poly.max(0); lo[k] = h0; hi[k] = h1
    f.bounds = (lo, hi)
    return f


def inset(poly, d):
    """A simple polygon with every edge moved d inward (d < 0 moves it out). Each vertex is
    where its two moved edges meet, so d must stay under the shortest edge's reach."""
    poly = np.asarray(poly, float)
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    s = 1.0 if area > 0 else -1.0                     # counter-clockwise: the inside is left of each edge
    n = len(poly); out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1, e2 = p1 - p0, p2 - p1
        n1 = s * np.array([-e1[1], e1[0]]) / np.hypot(*e1)
        n2 = s * np.array([-e2[1], e2[0]]) / np.hypot(*e2)
        M = np.array([n1, n2]); rhs = np.array([(p1 + d * n1) @ n1, (p1 + d * n2) @ n2])
        out.append(p1 + d * n1 if abs(np.linalg.det(M)) < 1e-6 else np.linalg.solve(M, rhs))
    return np.array(out)


def rprism(poly, axis, h0, h1, r, sharp=(False, False)):
    """prism() with every edge rounded by r: the profile's corners and the rims of both end
    faces. sharp=(True, False) leaves the h0 end square, for a face that mates with another part."""
    k = "xyz".index(axis); o = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    poly = np.asarray(poly, float); pin = inset(poly, r)
    e0 = h0 - (r if sharp[0] else 0.0); e1 = h1 + (r if sharp[1] else 0.0)

    def f(P):
        d2 = _poly2d(P[:, list(o)], pin)
        dh = np.abs(P[:, k] - (e0 + e1) / 2) - ((e1 - e0) / 2 - r)
        q = np.stack([d2, dh], 1)
        d = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r
        if sharp[0]:
            d = np.maximum(d, h0 - P[:, k])
        if sharp[1]:
            d = np.maximum(d, P[:, k] - h1)
        return d
    lo = np.zeros(3); hi = np.zeros(3)
    lo[list(o)] = poly.min(0); hi[list(o)] = poly.max(0); lo[k] = h0; hi[k] = h1
    f.bounds = (lo, hi)
    return f


# ------------------------------------------------------------- profiles (2D) and extrusions
# A profile is a 2D signed distance g(Q) for Q of shape (M, 2), with g.bounds = (lo2, hi2). It is
# drawn in the plane prism() uses for the axis it is extruded along. Profiles blend in 2D, so a
# fillet between two of them is a fillet in the drawing, and extrude() rounds the end faces' rims.
def p_poly(poly):
    poly = np.asarray(poly, float)
    g = lambda Q: _poly2d(Q, poly)
    g.bounds = (poly.min(0), poly.max(0))
    return g


def p_circle(c, r):
    c = np.asarray(c, float)
    g = lambda Q: np.hypot(Q[:, 0] - c[0], Q[:, 1] - c[1]) - r
    g.bounds = (c - r, c + r)
    return g


def p_blend(k, *gs):
    """2D smooth union: a fillet of about k at every inside corner where two profiles meet."""
    def g(Q):
        d = gs[0](Q)
        for h_ in gs[1:]:
            e = h_(Q)
            h = np.clip(0.5 + 0.5 * (e - d) / k, 0, 1)
            d = e * (1 - h) + d * h - k * h * (1 - h)
        return d
    g.bounds = (np.min([h_.bounds[0] for h_ in gs], 0), np.max([h_.bounds[1] for h_ in gs], 0))
    return g


def p_union(*gs):
    g = lambda Q: np.min([h_(Q) for h_ in gs], 0)
    g.bounds = (np.min([h_.bounds[0] for h_ in gs], 0), np.max([h_.bounds[1] for h_ in gs], 0))
    return g


def p_inter(*gs):
    g = lambda Q: np.max([h_(Q) for h_ in gs], 0)
    g.bounds = (np.max([h_.bounds[0] for h_ in gs], 0), np.min([h_.bounds[1] for h_ in gs], 0))
    return g


def p_capsule(a, b, r):
    """2D slot between two points, radius r (exact)."""
    a = np.asarray(a, float); b = np.asarray(b, float); e = b - a; L2 = float(e @ e)

    def g(Q):
        t = np.clip(((Q - a) @ e) / L2, 0, 1)
        return np.hypot(*(Q - a - np.outer(t, e)).T) - r
    g.bounds = (np.minimum(a, b) - r, np.maximum(a, b) + r)
    return g


def _cove(h, h0, c):
    """How far a wall's profile flares out at height h over a fillet of radius c at its foot h0."""
    s = np.clip(h - h0, 0.0, c)
    return c - np.sqrt(np.maximum(0.0, c * c - (c - s) ** 2))


def p_cache(g, step=0.04, margin=None):
    """g sampled once on a raster over its bounds (plus margin) and read back bilinearly: a
    profile drawn from many arcs then costs a lookup per point. Exact g outside the raster."""
    if getattr(g, "cached", False):
        return g
    m = MARGIN + 1.0 if margin is None else margin
    lo = np.asarray(g.bounds[0], float) - m; hi = np.asarray(g.bounds[1], float) + m
    n = np.ceil((hi - lo) / step).astype(int) + 1
    xs = lo[0] + step * np.arange(n[0]); ys = lo[1] + step * np.arange(n[1])
    Q = np.stack(np.meshgrid(xs, ys, indexing="ij"), -1).reshape(-1, 2)
    T = np.concatenate([g(Q[i:i + 2_000_000]) for i in range(0, len(Q), 2_000_000)]).reshape(n[0], n[1])

    def h(Q):
        # off the raster (more than the margin from the shape) the value is the border's plus the
        # way to it: positive, an upper bound, and nothing there is near a surface
        u = (Q[:, 0] - lo[0]) / step; v = (Q[:, 1] - lo[1]) / step
        uc = np.clip(u, 0.0, n[0] - 1.000001); vc = np.clip(v, 0.0, n[1] - 1.000001)
        i = np.floor(uc).astype(int); j = np.floor(vc).astype(int)
        fu = uc - i; fv = vc - j
        out = ((T[i, j] * (1 - fu) + T[i + 1, j] * fu) * (1 - fv) +
               (T[i, j + 1] * (1 - fu) + T[i + 1, j + 1] * fu) * fv)
        return out + step * np.hypot(u - uc, v - vc)
    h.bounds = g.bounds; h.cached = True
    return h


def p_offset(g, d):
    """The profile grown by d (d < 0 shrinks it)."""
    h = lambda Q: g(Q) - d
    h.bounds = (np.asarray(g.bounds[0]) - max(d, 0.0), np.asarray(g.bounds[1]) + max(d, 0.0))
    return h


def p_sweep(g, mats, c, c0=(0.0, 0.0), grow=0.0, step=0.05):
    """The region a profile covers as its part moves: g is drawn in the part's frame, each matrix M
    takes the part to the drawing (Q = c + M (X - c0)), so the swept region is the least g over the
    poses at X = c0 + M^T (Q - c). Grown by grow, and kept on a raster of its own."""
    gc = p_cache(g)
    c = np.asarray(c, float); c0 = np.asarray(c0, float)
    lo, hi = np.asarray(gc.bounds[0]), np.asarray(gc.bounds[1])
    C = np.array([[x, y] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])])
    R = float(np.max(np.hypot(*(C - c0).T))) + grow + 0.5

    def h(Q):
        d = np.full(len(Q), np.inf)
        for M in mats:
            d = np.minimum(d, gc(c0 + (Q - c) @ np.asarray(M)))
        return d - grow
    h.bounds = (c - R, c + R)
    return p_cache(h, step=step)


def p_rise(g, height, step=0.5):
    """The profile and everything above it up to height: the way a part comes down into place."""
    gc = p_cache(g)
    ks = np.arange(0.0, height + 1e-9, step)

    def h(Q):
        d = np.full(len(Q), np.inf)
        for k in ks:
            d = np.minimum(d, gc(Q - np.array([0.0, k])))
        return d
    h.bounds = (np.asarray(gc.bounds[0]), np.asarray(gc.bounds[1]) + np.array([0.0, height]))
    return p_cache(h)


def loft(gA, gB, h0, h1, z0, z1, r=0.0):
    """A body along z whose section is profile gA up to z0 and eases into gB by z1 (fast at first,
    tangent at the end: a waist with a cove at its foot), from h0 to h1, the top rim rounded by r,
    the bottom square."""
    gA = p_cache(gA); gB = p_cache(gB)

    def f(P):
        Q = P[:, :2]; z = P[:, 2]
        s = np.clip((z - z0) / (z1 - z0), 0.0, 1.0)
        w = 1.0 - (1.0 - s) ** 2
        d2 = (1.0 - w) * gA(Q) + w * gB(Q) + r
        dh = z - (h1 - r)
        q = np.stack([d2, dh], 1)
        d = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r
        return np.maximum(d, h0 - z)
    lo = np.minimum(gA.bounds[0], gB.bounds[0]); hi = np.maximum(gA.bounds[1], gB.bounds[1])
    f.bounds = (np.array([lo[0], lo[1], h0]), np.array([hi[0], hi[1], h1]))
    return f


def extrude(g, axis, h0, h1, r=0.0, sharp=(False, False), cove=0.0, cove_at=0, cache=True):
    """A profile extruded along an axis from h0 to h1, the rims of its end faces rounded by r
    (the profile's own corners are whatever the profile drew). An end marked sharp stays square.
    cove > 0 flares the h0 end out into a fillet of that radius, for a wall standing on a face at
    h0: the h0 end is then square, and where the wall stands at the edge of what it stands on,
    the caller trims the flare to it."""
    k = "xyz".index(axis); o = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    if cache:
        g = p_cache(g)
    if cove > 0:
        sharp = (True, sharp[1]) if cove_at == 0 else (sharp[0], True)
    e0 = h0 - (r if sharp[0] else 0.0); e1 = h1 + (r if sharp[1] else 0.0)

    def f(P):
        d2 = g(P[:, list(o)]) + r
        if cove > 0:
            d2 = d2 - (_cove(P[:, k], h0, cove) if cove_at == 0 else _cove(-P[:, k], -h1, cove))
        dh = np.abs(P[:, k] - (e0 + e1) / 2) - ((e1 - e0) / 2 - r)
        q = np.stack([d2, dh], 1)
        d = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r
        if sharp[0]:
            d = np.maximum(d, h0 - P[:, k])
        if sharp[1]:
            d = np.maximum(d, P[:, k] - h1)
        return d
    lo = np.zeros(3); hi = np.zeros(3)
    lo[list(o)] = np.asarray(g.bounds[0]) - cove; hi[list(o)] = np.asarray(g.bounds[1]) + cove
    lo[k] = h0; hi[k] = h1
    f.bounds = (lo, hi)
    return f


def rcyl(c, r, axis, h0, h1, rr, sharp=(False, False)):
    """cyl() with both rims rounded by rr (or left square at an end marked sharp)."""
    k = "xyz".index(axis); o = [i for i in range(3) if i != k]
    c = np.asarray(c, float)
    e0 = h0 - (rr if sharp[0] else 0.0); e1 = h1 + (rr if sharp[1] else 0.0)

    def f(P):
        d_r = np.hypot(P[:, o[0]] - c[o[0]], P[:, o[1]] - c[o[1]]) - (r - rr)
        d_h = np.abs(P[:, k] - (e0 + e1) / 2) - ((e1 - e0) / 2 - rr)
        q = np.stack([d_r, d_h], 1)
        d = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - rr
        if sharp[0]:
            d = np.maximum(d, h0 - P[:, k])
        if sharp[1]:
            d = np.maximum(d, P[:, k] - h1)
        return d
    lo = c.copy(); hi = c.copy()
    lo[o] -= r; hi[o] += r; lo[k] = h0; hi[k] = h1
    f.bounds = (lo, hi)
    return f


def rpoly(pts, n=10):
    """A closed outline from corners (x, y) or (x, y, r): a corner with r > 0 becomes an arc of
    radius r tangent to both its edges, convex or concave. The profile's own fillets."""
    pts = [tuple(p) + (0.0,) * (3 - len(p)) for p in pts]
    out = []
    m = len(pts)
    for i, (x, y, r) in enumerate(pts):
        V = np.array([x, y])
        if r <= 0:
            out.append(V); continue
        A = np.array(pts[i - 1][:2]); B = np.array(pts[(i + 1) % m][:2])
        u1 = (A - V) / np.hypot(*(A - V)); u2 = (B - V) / np.hypot(*(B - V))
        th = math.acos(max(-1.0, min(1.0, float(u1 @ u2)))) / 2
        if th < 1e-6 or abs(th - math.pi / 2) < 1e-6:
            out.append(V); continue
        t = r / math.tan(th)
        T1, T2 = V + u1 * t, V + u2 * t
        bis = (u1 + u2) / np.hypot(*(u1 + u2))
        Cc = V + bis * (r / math.sin(th))
        a1 = math.atan2(*(T1 - Cc)[::-1]); a2 = math.atan2(*(T2 - Cc)[::-1])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi        # the short way round
        for s in np.linspace(0, 1, n):
            a = a1 + s * da
            out.append(Cc + r * np.array([math.cos(a), math.sin(a)]))
    out = np.array(out)
    keep = np.r_[True, np.hypot(*np.diff(out, axis=0).T) > 1e-6]
    return out[keep]


def fillet(axis, corner, dirs, r, h0, h1):
    """A fillet strip for a concave edge along an axis: corner is the edge's point in the other
    two coordinates (in the order prism() uses), dirs the two directions (+1 / -1) that the
    walls run away from it. The strip fills the r x r square there minus the round."""
    c0, c1 = corner; s0, s1 = dirs
    sq = np.array([(c0, c1), (c0 + s0 * r, c1), (c0 + s0 * r, c1 + s1 * r), (c0, c1 + s1 * r)])
    if s0 * s1 < 0:
        sq = sq[::-1]
    k = "xyz".index(axis); o = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    cc = np.zeros(3); cc[o[0]] = c0 + s0 * r; cc[o[1]] = c1 + s1 * r
    return diff(prism(sq, axis, h0, h1), cyl(cc, r, axis, h0 - 1.0, h1 + 1.0))


def bezier(p0, p1, p2, n=16):
    """Quadratic Bezier from p0 to p2 pulled toward p1, as n points (p0 and p2 included)."""
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.asarray(p, float) for p in (p0, p1, p2))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2


def stadium(p0, p1, r):
    """2D slot outline (capsule) between two points, as a polygon."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.hypot(*d); u = d / L if L > 0 else np.array([1.0, 0.0])
    a0 = math.atan2(u[1], u[0])
    pts = [p1 + r * np.array([math.cos(a0 + t), math.sin(a0 + t)]) for t in np.linspace(-math.pi / 2, math.pi / 2, 24)]
    pts += [p0 + r * np.array([math.cos(a0 + t), math.sin(a0 + t)]) for t in np.linspace(math.pi / 2, 3 * math.pi / 2, 24)]
    return np.array(pts)


def circle(c, r, n=48):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)], 1)


# --------------------------------------------------------------- booleans
# Booleans evaluate a child only at points within MARGIN of its bounding box; farther out they
# use the distance to the box, which is a lower bound of the child's own and so keeps every sign
# and every value within MARGIN of a surface exact. MARGIN is more than any blend radius used.
MARGIN = 3.0


def _near(P, b, m=MARGIN):
    lo, hi = b
    return np.all((P >= np.asarray(lo) - m) & (P <= np.asarray(hi) + m), axis=1)


def _box_dist(P, b):
    lo, hi = np.asarray(b[0], float), np.asarray(b[1], float)
    q = np.maximum(np.maximum(lo - P, P - hi), 0.0)
    return np.linalg.norm(q, axis=1)


def _eval(g, P):
    """g at P, exactly near its bounds, its box distance (a lower bound) elsewhere."""
    m = _near(P, g.bounds)
    if m.all():
        return g(P)
    out = _box_dist(P, g.bounds)
    if m.any():
        out[m] = g(P[m])
    return out


def _bb_union(fs):
    lo = np.min([f.bounds[0] for f in fs], 0); hi = np.max([f.bounds[1] for f in fs], 0)
    return lo, hi


def union(*fs):
    def f(P):
        d = _eval(fs[0], P)
        for g in fs[1:]:
            d = np.minimum(d, _eval(g, P))
        return d
    f.bounds = _bb_union(fs)
    return f


def diff(a, *bs):
    def f(P):
        d = _eval(a, P)
        for b in bs:
            m = _near(P, b.bounds)
            if m.any():
                d[m] = np.maximum(d[m], -b(P[m]))
        return d
    f.bounds = a.bounds
    return f


def inter(a, *bs):
    def f(P):
        d = _eval(a, P)
        for b in bs:
            d = np.maximum(d, _eval(b, P))
        return d
    f.bounds = a.bounds
    return f


def smooth_union(a, b, k):
    def f(P):
        da, db = _eval(a, P), _eval(b, P)
        h = np.clip(0.5 + 0.5 * (db - da) / k, 0, 1)
        return db * (1 - h) + da * h - k * h * (1 - h)
    f.bounds = _bb_union([a, b])
    return f


def blend(k, *fs):
    """Smooth union of several shapes: every inside corner where two meet gets a fillet of
    about k. The first shape is blended with the second, the result with the third, and so on."""
    out = fs[0]
    for g in fs[1:]:
        out = smooth_union(out, g, k)
    return out


def smooth_diff(a, b, k):
    """a minus b with the rim of the cut rounded by about k."""
    def f(P):
        da, db = a(P), -b(P)
        h = np.clip(0.5 - 0.5 * (db - da) / k, 0, 1)
        return db * (1 - h) + da * h + k * h * (1 - h)
    f.bounds = a.bounds
    return f


# -------------------------------------------------------------- transforms
def transform(g, R=None, t=(0, 0, 0)):
    """Shape g moved by the rigid motion x -> R x + t."""
    R = np.eye(3) if R is None else np.asarray(R, float); t = np.asarray(t, float)

    def f(P):
        return g((P - t) @ R)          # inverse: R^T (P - t)
    lo, hi = g.bounds
    C = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    W = C @ R.T + t
    f.bounds = (W.min(0), W.max(0))
    return f


def rot_axis(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# ----------------------------------------------------------------- mesher
def _sample_sparse(f, lo, n, res, B=8, safety=2.0, chunk=4_000_000):
    """f on the grid lo + res * (i, j, k), evaluated only in blocks of B^3 cells that the surface
    may cross: a block whose centre lies farther from the surface than safety x its half
    diagonal keeps the centre's value everywhere (the same sign, no crossing)."""
    nb = -(-(n - 1) // B)                                   # blocks per axis
    ctr = [lo[i] + res * (B * np.arange(nb[i]) + B / 2.0) for i in range(3)]
    G = np.stack(np.meshgrid(*ctr, indexing="ij"), -1).reshape(-1, 3)
    fc = np.concatenate([f(G[i:i + chunk]) for i in range(0, len(G), chunk)]).reshape(tuple(nb))
    half = 0.5 * math.sqrt(3.0) * B * res
    active = np.abs(fc) < safety * half
    vol = np.empty(tuple(n), np.float32)
    for bi in np.ndindex(*nb):                              # fill every block with its centre's value
        sl = tuple(slice(B * b, min(B * b + B + 1, n[i])) for i, b in enumerate(bi))
        vol[sl] = fc[bi]
    idx = np.argwhere(active)
    pts, where = [], []
    for bi in idx:
        sl = [np.arange(B * b, min(B * b + B + 1, n[i])) for i, b in enumerate(bi)]
        I = np.stack(np.meshgrid(*sl, indexing="ij"), -1).reshape(-1, 3)
        where.append(I); pts.append(lo + res * I)
    if pts:
        I = np.concatenate(where); Pm = np.concatenate(pts)
        val = np.concatenate([f(Pm[i:i + chunk]) for i in range(0, len(Pm), chunk)])
        vol[I[:, 0], I[:, 1], I[:, 2]] = val
    return vol, float(active.mean())


def mesh(f, res=0.2, pad=1.0, chunk=4_000_000, sparse=True):
    """Marching cubes of f over its bounds. Returns (V, F) in mm, outward normals. sparse=True
    evaluates f only near its surface (_sample_sparse); sparse=False everywhere."""
    lo, hi = f.bounds
    lo = np.asarray(lo) - pad; hi = np.asarray(hi) + pad
    n = np.ceil((hi - lo) / res).astype(int) + 1
    if sparse:
        vol, _ = _sample_sparse(f, lo, n, res, chunk=chunk)
        V, F, _, _ = marching_cubes(vol, 0.0, spacing=(res, res, res))
        return (V + lo).astype(float), F.astype(int)
    xs = [lo[i] + res * np.arange(n[i]) for i in range(3)]
    vol = np.empty(n, np.float32)
    # evaluate slab by slab along x
    per = max(1, chunk // (n[1] * n[2]))
    Y, Z = np.meshgrid(xs[1], xs[2], indexing="ij")
    for i0 in range(0, n[0], per):
        i1 = min(n[0], i0 + per)
        X = np.repeat(xs[0][i0:i1], n[1] * n[2])
        P = np.stack([X, np.tile(Y.ravel(), i1 - i0), np.tile(Z.ravel(), i1 - i0)], 1)
        vol[i0:i1] = f(P).reshape(i1 - i0, n[1], n[2])
    V, F, _, _ = marching_cubes(vol, 0.0, spacing=(res, res, res))
    V = V + lo
    # skimage winds these outward for "inside negative" volumes
    return V.astype(float), F.astype(int)


def volume(V, F):
    T = V[F]
    return float(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0)


def write_stl(path, V, F, name="part"):
    T = V[F].astype(np.float32)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= (np.linalg.norm(n, axis=1)[:, None] + 1e-12)
    rec = np.zeros(len(F), dtype=[("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")])
    rec["n"] = n; rec["v"] = T.reshape(-1, 9)
    with open(path, "wb") as fh:
        hdr = (name.encode()[:80]).ljust(80, b" ")
        fh.write(hdr); fh.write(np.uint32(len(F)).tobytes()); fh.write(rec.tobytes())
