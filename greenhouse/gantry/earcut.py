"""Constrained polygon triangulation: ear clipping with hole bridging.

The Delaunay-plus-filter cap in kit3d.extrude() is unconstrained, so a thin
feature (the 0.35 mm lip of a V-slot T-groove) can be bridged by a triangle
whose centroid happens to land inside. Ear clipping only ever cuts along the
polygon's own diagonals, so the boundary is kept exactly.

triangulate(outer, holes) -> (P, T): P the stacked points (outer then each
hole, in the order given), T an (m, 3) index array into P.
"""
import numpy as np


def _area(L):
    x, y = L[:, 0], L[:, 1]
    return 0.5 * (x @ np.roll(y, -1) - np.roll(x, -1) @ y)


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _seg_hit(p, q, a, b):
    """Proper intersection of segments pq and ab (shared endpoints excluded)."""
    d1, d2 = _cross(a, b, p), _cross(a, b, q)
    d3, d4 = _cross(p, q, a), _cross(p, q, b)
    return (d1 * d2 < -1e-12) and (d3 * d4 < -1e-12)


_ALL_E = None


def _bridge(poly, hole):
    """Splice `hole` (index list, CW) into `poly` (index list, CCW) through a
    visible pair: the hole's rightmost vertex to the nearest outer vertex
    whose connecting segment crosses no edge of the polygon so far."""
    P = _PTS
    hi = max(hole, key=lambda i: (P[i][0], -P[i][1]))
    h = P[hi]
    pa = np.asarray(poly)
    E0, E1 = P[pa], P[np.roll(pa, -1)]
    if _ALL_E is not None:
        E0 = np.vstack([E0, _ALL_E[0]]); E1 = np.vstack([E1, _ALL_E[1]])
    d = ((P[pa] - h) ** 2).sum(1)
    for k in np.argsort(d):
        ci = pa[k]
        c = P[ci]
        # vectorised proper-intersection test against every edge
        def cr(o, a, b):
            return (a[..., 0] - o[..., 0]) * (b[..., 1] - o[..., 1]) - (a[..., 1] - o[..., 1]) * (b[..., 0] - o[..., 0])
        d1 = cr(E0, E1, h[None, :]); d2 = cr(E0, E1, c[None, :])
        d3 = cr(h[None, :], c[None, :], E0); d4 = cr(h[None, :], c[None, :], E1)
        hit = (d1 * d2 < -1e-12) & (d3 * d4 < -1e-12)
        if not hit.any():
            hk = hole.index(hi)
            hr = hole[hk:] + hole[:hk]
            pk = poly.index(ci)
            return poly[:pk + 1] + hr + [hi, ci] + poly[pk + 1:]
    raise ValueError("no bridge found")


_PTS = None


def triangulate(outer, holes=()):
    global _PTS
    outer = np.asarray(outer, float)
    holes = [np.asarray(h, float) for h in holes]
    loops = [outer] + holes
    P = np.vstack(loops)
    _PTS = P
    off = np.cumsum([0] + [len(L) for L in loops])
    idx_loops = [list(range(off[k], off[k + 1])) for k in range(len(loops))]
    # outer CCW, holes CW
    if _area(outer) < 0:
        idx_loops[0] = idx_loops[0][::-1]
    for k in range(1, len(loops)):
        if _area(loops[k]) > 0:
            idx_loops[k] = idx_loops[k][::-1]
    poly = idx_loops[0]
    global _ALL_E
    ha = [np.asarray(L) for L in idx_loops[1:]]
    if ha:
        _ALL_E = (np.vstack([P[L] for L in ha]), np.vstack([P[np.roll(L, -1)] for L in ha]))
    else:
        _ALL_E = None
    # bridge holes from the rightmost one leftward
    order = sorted(range(1, len(loops)), key=lambda k: -loops[k][:, 0].max())
    for k in order:
        poly = _bridge(poly, idx_loops[k])
    idx = np.array(poly)
    Q = P[idx]
    n = len(idx)
    prv = np.r_[n - 1, np.arange(n - 1)]
    nxt = np.r_[np.arange(1, n), 0]
    alive = np.ones(n, bool)
    tris = []
    i = 0
    left = n
    stall = 0
    while left > 3:
        a, c = prv[i], nxt[i]
        A, B, C = Q[a], Q[i], Q[c]
        ok = _cross(A, B, C) > 1e-12
        if ok:
            # any other live vertex inside ABC (or on it, unless a duplicate
            # of a corner from a bridge) kills the ear
            live = np.flatnonzero(alive)
            live = live[(live != a) & (live != i) & (live != c)]
            X = Q[live]
            d1 = (B[0] - A[0]) * (X[:, 1] - A[1]) - (B[1] - A[1]) * (X[:, 0] - A[0])
            d2 = (C[0] - B[0]) * (X[:, 1] - B[1]) - (C[1] - B[1]) * (X[:, 0] - B[0])
            d3 = (A[0] - C[0]) * (X[:, 1] - C[1]) - (A[1] - C[1]) * (X[:, 0] - C[0])
            inside = (d1 >= -1e-12) & (d2 >= -1e-12) & (d3 >= -1e-12)
            if inside.any():
                dup = (np.all(np.isclose(X, A), 1) | np.all(np.isclose(X, B), 1)
                       | np.all(np.isclose(X, C), 1))
                ok = not (inside & ~dup).any()
        if ok:
            tris.append((idx[a], idx[i], idx[c]))
            alive[i] = False
            nxt[a], prv[c] = c, a
            left -= 1
            i = a
            stall = 0
        else:
            i = c
            stall += 1
            if stall > left:          # no ear anywhere: drop a sliver vertex
                alive[i] = False
                a, c = prv[i], nxt[i]
                nxt[a], prv[c] = c, a
                left -= 1
                i = c
                stall = 0
    live = np.flatnonzero(alive)
    if len(live) == 3:
        tris.append(tuple(idx[live]))
    return P, np.array(tris, int)
