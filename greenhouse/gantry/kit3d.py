"""Solid modelling + axonometric line-art renderer.

Meshes are (V, F): V is (n,3) float, F is (m,3) int. Everything is in mm.

The renderer does three things that together give the flat, clean look of an
assembly instruction rather than a CAD screenshot:
  * flat shading from a single light, so faces read as planes
  * painter's algorithm on face depth, so no z-buffer is needed
  * silhouette and feature edges only, so cylinders do not turn into wire wool
"""
from __future__ import annotations
import math
import numpy as np
from scipy.spatial import Delaunay
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

# ------------------------------------------------------------------ palette
INK = "#15191c"
LINE = "#1b2024"
DIM = "#5b6770"
RULE = "#c3ccd2"
ALU = np.array([0.80, 0.83, 0.86])      # anodised aluminium, silver
ALU_D = np.array([0.62, 0.66, 0.70])    # darker alu
STEEL = np.array([0.72, 0.75, 0.78])
BLACKPART = np.array([0.30, 0.32, 0.34])
POM = np.array([0.88, 0.86, 0.80])      # wheel plastic
BRASS = np.array([0.80, 0.68, 0.40])
PCB = np.array([0.22, 0.42, 0.34])
HILITE = np.array([0.97, 0.63, 0.25])   # the part being added this step
ARM = np.array([0.93, 0.93, 0.95])


# =============================================================== primitives
# Anything meant to be round is built with at least SEG facets. Callers that
# ask for fewer than 10 (hexes, square sockets) mean a polygon and keep it.
SEG = 72


def _round(n):
    return n if n < 10 else max(int(n), SEG)


def _mesh(V, F):
    return (np.asarray(V, float), np.asarray(F, int))


def merge(*parts):
    Vs, Fs, off = [], [], 0
    for V, F in parts:
        if len(V) == 0:
            continue
        Vs.append(V); Fs.append(np.asarray(F) + off); off += len(V)
    if not Vs:
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    return np.vstack(Vs), np.vstack(Fs)


def box(sx, sy, sz, c=(0, 0, 0)):
    x, y, z = c
    V = np.array([[x, y, z], [x+sx, y, z], [x+sx, y+sy, z], [x, y+sy, z],
                  [x, y, z+sz], [x+sx, y, z+sz], [x+sx, y+sy, z+sz], [x, y+sy, z+sz]], float)
    F = np.array([[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],
                  [1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]], int)
    return _mesh(V, F[:, ::-1])   # wind outward


def extrude(poly, h, z0=0.0, holes=None, cap=True):
    """Extrude a 2D polygon (n,2) in Z. `holes` is a list of (m,2) loops."""
    poly = np.asarray(poly, float)
    holes = [np.asarray(h_, float) for h_ in (holes or [])]
    V, F = [], []
    loops = [poly] + holes
    # side walls, one loop at a time
    base = 0
    for L in loops:
        n = len(L)
        bot = np.c_[L, np.full(n, z0)]
        top = np.c_[L, np.full(n, z0 + h)]
        V.append(bot); V.append(top)
        for i in range(n):
            j = (i + 1) % n
            a, b, c, d = base + i, base + j, base + n + j, base + n + i
            F += [[a, b, c], [a, c, d]]
        base += 2 * n
    V = np.vstack(V)
    if cap:
        pts = np.vstack(loops)
        keep = None
        try:
            import earcut as _ec
            _P2, keep = _ec.triangulate(poly, holes)
            if len(keep) == 0:
                keep = None
        except Exception:
            keep = None
        if keep is None:
            from matplotlib.path import Path as _P
            tri = Delaunay(pts)
            cen = pts[tri.simplices].mean(1)
            ok = _P(poly).contains_points(cen)
            for hl in holes:
                ok &= ~_P(hl).contains_points(cen)
            keep = tri.simplices[ok]
        else:
            # earcut may reverse loops internally; keep caps wound like
            # Delaunay's (counter-clockwise in xy) for the bottom flip below
            a = pts[keep]
            cr = ((a[:, 1, 0] - a[:, 0, 0]) * (a[:, 2, 1] - a[:, 0, 1])
                  - (a[:, 1, 1] - a[:, 0, 1]) * (a[:, 2, 0] - a[:, 0, 0]))
            keep = np.where((cr < 0)[:, None], keep[:, ::-1], keep)
        if len(keep):
            nb = len(V)
            V = np.vstack([V, np.c_[pts, np.full(len(pts), z0)],
                           np.c_[pts, np.full(len(pts), z0 + h)]])
            np_ = len(pts)
            F += (keep[:, ::-1] + nb).tolist()
            F += (keep + nb + np_).tolist()
    return _mesh(V, np.array(F, int))


def _inside(p, loop):
    x, y = p[0], p[1]
    n = len(loop); ins = False
    j = n - 1
    for i in range(n):
        xi, yi = loop[i]; xj, yj = loop[j]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/(yj-yi+1e-12)+xi):
            ins = not ins
        j = i
    return ins


def circle_pts(r, n=28, cx=0.0, cy=0.0, start=0.0):
    n = _round(n)
    a = np.linspace(start, start + 2*math.pi, n, endpoint=False)
    return np.c_[cx + r*np.cos(a), cy + r*np.sin(a)]


def cylinder(r, h, n=24, c=(0, 0, 0), r2=None):
    """Z-axis cylinder or truncated cone (r at bottom, r2 at top)."""
    r2 = r if r2 is None else r2
    n = _round(n)
    a = np.linspace(0, 2*math.pi, n, endpoint=False)
    bot = np.c_[c[0]+r*np.cos(a), c[1]+r*np.sin(a), np.full(n, c[2])]
    top = np.c_[c[0]+r2*np.cos(a), c[1]+r2*np.sin(a), np.full(n, c[2]+h)]
    V = np.vstack([bot, top, [[c[0], c[1], c[2]]], [[c[0], c[1], c[2]+h]]])
    cb, ct = 2*n, 2*n+1
    F = []
    for i in range(n):
        j = (i+1) % n
        F += [[i, j, n+j], [i, n+j, n+i], [cb, j, i], [ct, n+i, n+j]]
    return _mesh(V, np.array(F, int))


def revolve(profile, n=32, axis="z"):
    """Revolve a 2D (r, z) profile around the Z axis."""
    P = np.asarray(profile, float)
    n = _round(n)
    m = len(P)
    V, F = [], []
    for k in range(n):
        a = 2*math.pi*k/n
        ca, sa = math.cos(a), math.sin(a)
        for (r, z) in P:
            V.append([r*ca, r*sa, z])
    for k in range(n):
        k2 = (k+1) % n
        for i in range(m-1):
            a = k*m+i; b = k*m+i+1; c = k2*m+i+1; d = k2*m+i
            F += [[a, b, c], [a, c, d]]
    return _mesh(np.array(V), np.array(F, int))


def ring(ro, ri, h, c=(0, 0, 0), n=SEG):
    """Z-axis tube: outer radius ro, bore ri, height h, base at c."""
    m = revolve([(ri, 0.0), (ro, 0.0), (ro, h), (ri, h), (ri, 0.0)], n=n)
    return mv(m, *c)


def hexring(af, ri, h, c=(0, 0, 0), bore_off=(0.0, 0.0)):
    """Hex prism across flats `af` with a round bore, optionally offset."""
    R = af / 2 / math.cos(math.pi / 6)
    hx = circle_pts(R, 6, start=math.pi / 6)
    hole = circle_pts(ri, SEG, bore_off[0], bore_off[1])
    return mv(extrude(hx, h, holes=[hole]), *c)


def disc(ro, ri, h, c=(0, 0, 0), bore_off=(0.0, 0.0)):
    """Round disc with an optionally offset bore (eccentrics)."""
    return mv(extrude(circle_pts(ro, SEG), h,
                      holes=[circle_pts(ri, SEG, bore_off[0], bore_off[1])]), *c)


def tube(path, r, n=10):
    """Sweep a circle along a 3D polyline. Used for cables and belts."""
    P = np.asarray(path, float)
    V, F = [], []
    prev_u = None
    for i, p in enumerate(P):
        t = P[min(i+1, len(P)-1)] - P[max(i-1, 0)]
        ln = np.linalg.norm(t)
        t = t/ln if ln > 1e-9 else np.array([1.0, 0, 0])
        ref = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(t, ref); u /= (np.linalg.norm(u) + 1e-12)
        v = np.cross(t, u)
        prev_u = u
        for k in range(n):
            a = 2*math.pi*k/n
            V.append(p + r*(math.cos(a)*u + math.sin(a)*v))
    for i in range(len(P)-1):
        for k in range(n):
            k2 = (k+1) % n
            a = i*n+k; b = i*n+k2; c = (i+1)*n+k2; d = (i+1)*n+k
            F += [[a, b, c], [a, c, d]]
    return _mesh(np.array(V), np.array(F, int))


# ------------------------------------------------------------------ fasteners
def screw_m5_lp(length, head_d=9.5, head_h=2.8, shank_d=5.0, n=16):
    """M5 low-profile socket head cap screw, head at z=0 going down."""
    # the head's side, and its top as a ring round a 3 mm hex socket 1.7 deep
    # with its floor, so the socket reads as a hole (it used to be a solid
    # hex buried inside the head)
    R = 3.0 / math.sqrt(3)
    hexp = circle_pts(R, 6, start=math.pi/6)
    top = extrude(circle_pts(head_d/2, max(n, SEG)), 1.9, z0=head_h - 1.9, holes=[hexp])
    floor_ = extrude(hexp * 0.999, 0.2, z0=head_h - 1.9)
    socket = merge(top, floor_)
    side = cylinder(head_d/2, head_h - 1.9, n=n, c=(0, 0, 0))
    shank = cylinder(shank_d/2, length, n=n, c=(0, 0, -length))
    # thread hint: three shallow rings
    rings = []
    for k in range(4):
        zz = -length + 1.5 + k*(length-3)/4.0
        rings.append(cylinder(shank_d/2+0.18, 0.5, n=n, c=(0, 0, zz)))
    return merge(side, socket, shank, *rings)


def nut_m5(n=6, af=8.0, h=4.0):
    """M5 hex nut with its bore (it used to be a solid hex)."""
    return extrude(circle_pts(af/2/math.cos(math.pi/6), 6), h, holes=[circle_pts(2.1, SEG)])


# ------------------------------------------------------------------ transforms
def rot(mesh, rx=0.0, ry=0.0, rz=0.0):
    V, F = mesh
    for ang, ax in ((rx, 0), (ry, 1), (rz, 2)):
        if abs(ang) < 1e-12:
            continue
        c, s = math.cos(ang), math.sin(ang)
        R = np.eye(3)
        if ax == 0: R = np.array([[1,0,0],[0,c,-s],[0,s,c]])
        if ax == 1: R = np.array([[c,0,s],[0,1,0],[-s,0,c]])
        if ax == 2: R = np.array([[c,-s,0],[s,c,0],[0,0,1]])
        V = V @ R.T
    return (V, F)


def mv(mesh, dx=0.0, dy=0.0, dz=0.0):
    V, F = mesh
    return (V + np.array([dx, dy, dz]), F)


def scale(mesh, s):
    V, F = mesh
    return (V * s, F)


def weld(mesh, tol=1e-4):
    """Merge vertices closer than `tol` and drop faces that collapse.

    extrude() and revolve() emit each cap and wall with its own copy of the
    shared vertices, so without this a plate is a dozen disconnected open
    sheets. Every orientation test downstream assumes closed shells, and an
    open sheet's signed volume is noise: that is what made plates and rails
    render hollow.
    """
    V, F = mesh
    if len(F) == 0:
        return mesh
    q = np.round(np.asarray(V) / tol).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    F2 = inv[np.asarray(F)]
    ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    return (np.asarray(V)[first], F2[ok])


def _edge_graph(F):
    """Face adjacency through shared edges, with a same-direction flag.

    Two faces sharing an edge are consistently wound when they traverse it in
    opposite directions. Returns (i, j, same) for every manifold edge.
    """
    nf = len(F)
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    fid = np.tile(np.arange(nf), 3)
    key = np.sort(E, axis=1)
    fwd = E[:, 0] < E[:, 1]
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True,
                            return_counts=True)
    inv = inv.ravel()
    order = np.argsort(inv, kind="stable")
    start = np.concatenate([[0], np.cumsum(cnt)[:-1]])
    two = np.flatnonzero(cnt == 2)
    a = order[start[two]]
    b = order[start[two] + 1]
    return fid[a], fid[b], fwd[a] == fwd[b]


def orient(mesh):
    """Make winding consistent and outward, shell by shell.

    Walks face adjacency through shared edges, flipping neighbours into
    agreement, then checks each edge-connected shell's signed volume on its
    own. Checking the whole component at once (Rev B) let one inside-out
    shell hide behind a correct one whose volume outweighed it.
    """
    import scipy.sparse as sp
    from scipy.sparse.csgraph import breadth_first_order, connected_components
    V, F = mesh
    if len(F) == 0:
        return mesh
    F = np.array(F, dtype=int, copy=True)
    nf = len(F)
    i, j, same = _edge_graph(F)
    if len(i) == 0:
        return (V, F)
    # parity graph: an edge says "flip relative to me" when same == True
    G = sp.coo_matrix((np.ones(len(i) * 2), (np.r_[i, j], np.r_[j, i])),
                      shape=(nf, nf)).tocsr()
    par_e = {}
    for a_, b_, s_ in zip(i.tolist(), j.tolist(), same.tolist()):
        par_e[(a_, b_)] = s_
        par_e[(b_, a_)] = s_
    ncomp, lab = connected_components(G, directed=False)
    flip = np.zeros(nf, bool)
    for c in range(ncomp):
        root = int(np.flatnonzero(lab == c)[0])
        order, pred = breadth_first_order(G, root, directed=False,
                                          return_predecessors=True)
        for f in order[1:]:
            p_ = pred[f]
            flip[f] = flip[p_] ^ par_e[(int(p_), int(f))]
    F[flip] = F[flip][:, ::-1]
    # per-shell signed volume
    T = V[F]
    sv = np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])) / 6.0
    vol = np.bincount(lab, weights=sv, minlength=ncomp)
    bad = vol[lab] < 0
    F[bad] = F[bad][:, ::-1]
    return (V, F)


def components(mesh, do_orient=True):
    """Split a mesh into connected components, welded and oriented."""
    from scipy.sparse.csgraph import connected_components
    import scipy.sparse as sp
    V, F = weld(mesh)
    if len(F) == 0:
        return []
    nv = len(V)
    r = np.r_[F[:, 0], F[:, 1]]
    c = np.r_[F[:, 1], F[:, 2]]
    G = sp.coo_matrix((np.ones(len(r)), (r, c)), shape=(nv, nv))
    _, lab = connected_components(G, directed=False)
    flab = lab[F[:, 0]]
    out = []
    for g in np.unique(flab):
        sub = F[flab == g]
        used = np.unique(sub)
        remap = np.zeros(nv, int)
        remap[used] = np.arange(len(used))
        m = (V[used], remap[sub])
        out.append(orient(m) if do_orient else m)
    return out


def clip(mesh, lo=None, hi=None):
    """Keep only the triangles whose centroid falls inside the box.

    A cheap cutaway: good enough to zoom a drawing onto one detail of a big
    assembly without modelling the detail separately.
    """
    V, F = mesh
    if len(F) == 0:
        return mesh
    c = V[F].mean(1)
    keep = np.ones(len(F), bool)
    if lo is not None:
        lo = np.where(np.equal(lo, None), -np.inf, lo).astype(float)
        keep &= (c >= lo).all(1)
    if hi is not None:
        hi = np.where(np.equal(hi, None), np.inf, hi).astype(float)
        keep &= (c <= hi).all(1)
    F = F[keep]
    if len(F) == 0:
        return (V[:0], F)
    used = np.unique(F)
    remap = np.zeros(len(V), int)
    remap[used] = np.arange(len(used))
    return (V[used], remap[F])


def bbox(mesh):
    V, _ = mesh
    return V.min(0), V.max(0)


# =============================================================== the renderer
class Part:
    __slots__ = ("mesh", "color", "edges", "alpha", "ghost", "ang", "lw")

    def __init__(self, mesh, color=ALU, edges=True, alpha=1.0, ghost=False,
                 ang=26.0, lw=None):
        self.mesh = mesh
        self.color = np.asarray(color, float)
        self.edges = edges
        self.alpha = alpha
        self.ghost = ghost
        # Dihedral threshold for feature edges, degrees. Raise it for
        # tessellated CAD imports so facet seams on cylinders stay quiet.
        self.ang = ang
        self.lw = lw


def iso_matrix(az=35.0, el=27.0):
    """Axonometric view matrix. Screen = (x, y) of the result, depth = z.

    World +Z maps to screen +y (up) and `el` is the camera's elevation above
    the horizontal, so positive `el` looks down on the model.
    """
    a, b = math.radians(az), math.radians(el)
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
    # The camera sits at (sa, ca, tan el): the depth row points at it. Rev E
    # fix: screen x is the camera's RIGHT, depth x up. Through Rev D the first
    # row was (ca, -sa, 0), whose cross with screen y is MINUS the depth row:
    # a left-handed screen, so every drawing came out mirror imaged.
    return np.array([
        [-ca,      sa,      0.0],   # screen x  (camera right)
        [-sb * sa, -sb * ca, cb],   # screen y  (world +Z -> up)
        [cb * sa,  cb * ca,  sb],   # depth     (larger = nearer)
    ])


LIGHT = np.array([0.42, -0.66, 0.62]); LIGHT /= np.linalg.norm(LIGHT)


def feature_edges(V, F, P2, nrm, ang=math.radians(26), with_depth=False,
                  eps=0.25):
    """Silhouette + sharp-dihedral edges, in projected 2D.

    `F`/`nrm` are the camera-facing faces only, so an edge shared with a
    back-face appears used once and is kept as a silhouette.

    An edge's draw depth is its own nearer endpoint, nudged forward by `eps`.
    Taking it from the adjacent face's centroid instead (the obvious thing)
    floats long edges of large tilted faces in front of geometry that should
    occlude them, which is what see-through artifacts actually are.
    """
    nf = len(F)
    if nf == 0:
        return ([], []) if with_depth else []
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    fid = np.tile(np.arange(nf), 3)
    key = np.sort(E, axis=1)
    uk, inv, cnt = np.unique(key, axis=0, return_inverse=True,
                             return_counts=True)
    inv = inv.ravel()
    order = np.argsort(inv, kind="stable")
    fid_s = fid[order]
    start = np.concatenate([[0], np.cumsum(cnt)[:-1]])

    keep = cnt == 1                                   # silhouette / boundary
    two = np.flatnonzero(cnt == 2)
    if len(two):
        n0 = nrm[fid_s[start[two]]]
        n1 = nrm[fid_s[start[two] + 1]]
        d = np.clip(np.einsum("ij,ij->i", n0, n1), -1.0, 1.0)
        keep[two] = np.arccos(d) > ang

    uk = uk[keep]
    if len(uk) == 0:
        return ([], []) if with_depth else []
    out = np.stack([P2[uk[:, 0]], P2[uk[:, 1]]], axis=1)
    if not with_depth:
        return list(out)
    dep = np.maximum(V[uk[:, 0], 2], V[uk[:, 1], 2]) + eps
    return list(out), list(dep)


def _feature_edges_any(V, F, Q, ang):
    """Silhouette, crease and boundary edges WITHOUT trusting the winding.

    For an edge shared by two faces, the faces agree on winding when they
    traverse it in opposite directions. When they disagree, one normal is
    reversed, so the crease angle and the silhouette test both flip sign.
    Accounting for that per edge means a mesh with patches wound either way
    (every CAD export of the 280) still gets exactly the right lines.

    Returns segment endpoints (m, 2) as vertex ids, and the two adjacent
    face ids per edge (-1 for a boundary edge).
    """
    nf = len(F)
    T = Q[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    n = n / np.maximum(ln, 1e-12)[:, None]
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    fid = np.tile(np.arange(nf), 3)
    key = np.sort(E, axis=1)
    fwd = E[:, 0] < E[:, 1]
    uk, inv, cnt = np.unique(key, axis=0, return_inverse=True,
                             return_counts=True)
    inv = inv.ravel()
    order = np.argsort(inv, kind="stable")
    start = np.concatenate([[0], np.cumsum(cnt)[:-1]])
    m = len(uk)
    adj = np.full((m, 2), -1, int)
    adj[:, 0] = fid[order[start]]
    keep = np.zeros(m, bool)
    keep[cnt == 1] = True                       # open boundary
    keep[cnt > 2] = True                        # non-manifold junction
    two = np.flatnonzero(cnt == 2)
    if len(two):
        e0, e1 = order[start[two]], order[start[two] + 1]
        f0, f1 = fid[e0], fid[e1]
        adj[two, 1] = f1
        sgn = np.where(fwd[e0] != fwd[e1], 1.0, -1.0)   # +1 consistent
        d = np.clip(np.einsum("ij,ij->i", n[f0], n[f1]) * sgn, -1.0, 1.0)
        crease = np.arccos(d) > ang
        face0 = n[f0, 2] > 0
        face1 = (n[f1, 2] * sgn) > 0
        sil = face0 != face1
        keep[two] = crease | sil
    return uk[keep], adj[keep]


def _rasterize(P, Z, shape, chunk=8_000_000):
    """Z-buffer a triangle soup with a vectorised scanline fill.

    P (n,3,2) pixel coords, Z (n,3) depth, larger is nearer. Each pixel ends
    up holding (quantised depth << 24 | face id) of the nearest face, or -1.
    Work is the rows each triangle spans plus the pixels it covers, so a
    sliver of a 1.4 m rail costs what it covers, not its bounding box.
    """
    H, W = shape
    key = np.full(H * W, -1, np.int64)
    n = len(P)
    if n == 0:
        return key, 0.0, 1.0
    zmin, zmax = float(Z.min()), float(Z.max())
    span = max(zmax - zmin, 1e-9)
    QMAX = float(2 ** 38 - 1)
    x, y = P[:, :, 0], P[:, :, 1]
    # depth plane z = zx * x + zy * y + z0 per triangle
    e1 = np.stack([x[:, 1] - x[:, 0], y[:, 1] - y[:, 0], Z[:, 1] - Z[:, 0]], 1)
    e2 = np.stack([x[:, 2] - x[:, 0], y[:, 2] - y[:, 0], Z[:, 2] - Z[:, 0]], 1)
    nn = np.cross(e1, e2)
    ok = np.abs(nn[:, 2]) > 1e-9
    zx = np.where(ok, -nn[:, 0] / np.where(ok, nn[:, 2], 1), 0.0)
    zy = np.where(ok, -nn[:, 1] / np.where(ok, nn[:, 2], 1), 0.0)
    z0 = Z[:, 0] - zx * x[:, 0] - zy * y[:, 0]
    r0 = np.maximum(np.ceil(y.min(1) - 0.5), 0).astype(np.int64)
    r1 = np.minimum(np.floor(y.max(1) - 0.5), H - 1).astype(np.int64)
    live = ok & (r1 >= r0) & (x.max(1) >= 0) & (x.min(1) <= W)
    ids = np.flatnonzero(live)
    nrow = (r1 - r0 + 1)[ids]
    # process triangles in groups so the (triangle, row) expansion stays small
    csum = np.cumsum(nrow)
    starts = np.searchsorted(csum, np.arange(0, csum[-1] if len(csum) else 0,
                                             chunk // 8), side="left")
    bounds = list(np.unique(np.r_[starts, len(ids)]))
    for gi in range(len(bounds) - 1):
        g = ids[bounds[gi]:bounds[gi + 1]]
        if len(g) == 0:
            continue
        nr = (r1 - r0 + 1)[g]
        t = np.repeat(g, nr)
        row = r0[t] + (np.arange(len(t)) - np.repeat(np.cumsum(nr) - nr, nr))
        yc = row + 0.5
        xl = np.full(len(t), np.inf)
        xr = np.full(len(t), -np.inf)
        for i, j in ((0, 1), (1, 2), (2, 0)):
            ya, yb = y[t, i], y[t, j]
            xa, xb = x[t, i], x[t, j]
            hit = ((ya - yc) * (yb - yc) <= 0) & (ya != yb)
            xi = xa + (yc - ya) * (xb - xa) / np.where(ya != yb, yb - ya, 1.0)
            xl = np.where(hit, np.minimum(xl, xi), xl)
            xr = np.where(hit, np.maximum(xr, xi), xr)
        c0 = np.maximum(np.ceil(xl - 0.5 - 1e-7), 0).astype(np.int64)
        c1 = np.minimum(np.floor(xr - 0.5 + 1e-7), W - 1).astype(np.int64)
        good = (c1 >= c0) & np.isfinite(xl)
        t, row, c0, c1 = t[good], row[good], c0[good], c1[good]
        nc = c1 - c0 + 1
        # expand runs into pixels, in sub-chunks
        cs = np.cumsum(nc)
        cut = np.searchsorted(cs, np.arange(0, cs[-1] if len(cs) else 0, chunk),
                              side="left")
        cb = list(np.unique(np.r_[cut, len(t)]))
        for k in range(len(cb) - 1):
            sl = slice(cb[k], cb[k + 1])
            tt, rr, cc0, ncc = t[sl], row[sl], c0[sl], nc[sl]
            if len(tt) == 0:
                continue
            tp = np.repeat(tt, ncc)
            col = np.repeat(cc0, ncc) + (np.arange(len(tp))
                                         - np.repeat(np.cumsum(ncc) - ncc, ncc))
            rp = np.repeat(rr, ncc)
            z = zx[tp] * (col + 0.5) + zy[tp] * (rp + 0.5) + z0[tp]
            q = np.clip((z - zmin) / span * QMAX, 0, QMAX).astype(np.int64)
            np.maximum.at(key, rp * W + col, (q << 24) | tp.astype(np.int64))
    return key, zmin, span


def _corner_normals(F, nrm, area, crease):
    """Crease-aware per-corner normals for smooth (Gouraud) shading.

    Each face corner averages the area-weighted normals of the faces around
    its vertex that lie within `crease` of its own face. A cylinder's facets
    blend into one curved surface; a box edge stays a hard edge. Neighbours
    wound the other way are folded in with their sign flipped, so open CAD
    shells shade smoothly too.
    """
    nf = len(F)
    cv = F.ravel()
    cf = np.repeat(np.arange(nf), 3)
    order = np.argsort(cv, kind="stable")
    cf_s = cf[order]
    _, start, cnt = np.unique(cv[order], return_index=True, return_counts=True)
    grp = np.repeat(np.arange(len(cnt)), cnt)
    reps = cnt[grp]
    left = np.repeat(np.arange(len(cf_s)), reps)
    k = np.arange(len(left)) - np.repeat(np.cumsum(reps) - reps, reps)
    right = start[grp[left]] + k
    fl, fr = cf_s[left], cf_s[right]
    d = np.einsum("ij,ij->i", nrm[fl], nrm[fr])
    w = (np.abs(d) >= math.cos(crease)) * area[fr] * np.where(d >= 0, 1.0, -1.0)
    acc = np.stack([np.bincount(left, weights=nrm[fr, i] * w,
                                minlength=len(cf_s)) for i in range(3)], 1)
    acc /= np.maximum(np.linalg.norm(acc, axis=1), 1e-12)[:, None]
    out = np.empty_like(acc)
    out[order] = acc
    return out.reshape(nf, 3, 3)


def _split_long(P, Z, C, lmax=32.0):
    """Split triangles whose longest screen edge exceeds lmax pixels.

    A sliver of a long rail seen on the diagonal has a bounding box of a
    million pixels and covers a few thousand, and the rasteriser pays for the
    box. Halving the longest edge until every edge is short keeps the boxes
    tight. Depth and colour are linear across a triangle, so splitting at a
    midpoint is exact. Returns the pieces and each piece's parent index.
    """
    parent = np.arange(len(P))
    outP, outZ, outC, outI = [], [], [], []
    while len(P):
        e = np.stack([np.linalg.norm(P[:, 1] - P[:, 0], axis=1),
                      np.linalg.norm(P[:, 2] - P[:, 1], axis=1),
                      np.linalg.norm(P[:, 0] - P[:, 2], axis=1)], 1)
        long_ = e.max(1) > lmax
        outP.append(P[~long_]); outZ.append(Z[~long_]); outC.append(C[~long_])
        outI.append(parent[~long_])
        if not long_.any():
            break
        P, Z, C, parent, e = P[long_], Z[long_], C[long_], parent[long_], e[long_]
        k = e.argmax(1)                       # longest edge k: (k, k+1)
        idx = np.arange(len(P))
        a = k
        b = (k + 1) % 3
        c = (k + 2) % 3
        Pa, Pb, Pc = P[idx, a], P[idx, b], P[idx, c]
        Za, Zb, Zc = Z[idx, a], Z[idx, b], Z[idx, c]
        Ca, Cb, Cc = C[idx, a], C[idx, b], C[idx, c]
        Pm, Zm, Cm = (Pa + Pb) / 2, (Za + Zb) / 2, (Ca + Cb) / 2
        P = np.concatenate([np.stack([Pa, Pm, Pc], 1), np.stack([Pm, Pb, Pc], 1)])
        Z = np.concatenate([np.stack([Za, Zm, Zc], 1), np.stack([Zm, Zb, Zc], 1)])
        C = np.concatenate([np.stack([Ca, Cm, Cc], 1), np.stack([Cm, Cb, Cc], 1)])
        parent = np.concatenate([parent, parent])
    return (np.concatenate(outP), np.concatenate(outZ), np.concatenate(outC),
            np.concatenate(outI))


def render(ax, parts, M=None, lw=0.6, shade=(0.52, 0.46), z0=3, slices=None,
           px=3.0, tol=0.6, view=None):
    """Z-buffered fills plus hidden-line-removed edges.

    Rev B/C used a depth-sliced painter's algorithm. Its flaw is structural:
    a slice's edges are drawn over every face in that slice, so anything
    closer than one slice depth shows through (28 mm on a cabinet page).
    Here the fills come from a real per-pixel depth buffer, and every edge is
    tested against that buffer and drawn only where nothing is in front of
    it. Neither step looks at face winding or back-face culling, so open or
    inconsistently wound meshes (the CAD arm) render as solids.

    `px` is raster pixels per data unit for the fill image; `tol` is how far
    behind the nearest surface an edge may sit and still count as on it.
    """
    M = iso_matrix() if M is None else M
    Ts, Zs, Cs = [], [], []
    EV, EZ, EF, EW = [], [], [], []
    off = 0
    for p in parts:
        V, F = weld(p.mesh)
        if len(F) == 0:
            continue
        Q = np.asarray(V) @ M.T
        T = Q[F]
        nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        ok = ln > 1e-12
        if not ok.all():
            F = F[ok]; T = T[ok]; nrm = nrm[ok]; ln = ln[ok]
        if len(F) == 0:
            continue
        nrm = nrm / ln[:, None]
        cn = _corner_normals(F, nrm, ln * 0.5, math.radians(p.ang))
        sh = np.abs(cn @ LIGHT) * shade[0] + shade[1]          # (nf, 3)
        col = np.clip(sh[:, :, None] * p.color[None, None, :], 0, 1)
        if p.ghost:
            col = 0.70 * col + 0.30
        Ts.append(T[:, :, :2]); Zs.append(T[:, :, 2]); Cs.append(col)
        if p.edges:
            seg, adj = _feature_edges_any(V, F, Q, math.radians(p.ang))
            if len(seg):
                EV.append(Q[seg][:, :, :2])
                EZ.append(Q[seg][:, :, 2])
                EF.append(np.where(adj >= 0, adj + off, -1))
                EW.append(np.full(len(seg), lw if p.lw is None else p.lw))
        off += len(F)
    if not Ts:
        return (0, 0), (1, 1)
    T2 = np.concatenate(Ts); Z = np.concatenate(Zs); C = np.concatenate(Cs)

    lo = T2.reshape(-1, 2).min(0) - 2.0 / px
    hi = T2.reshape(-1, 2).max(0) + 2.0 / px
    # Never rasterise beyond what the axes show: a full-length rail running
    # off the page would otherwise cost a page-sized buffer per metre.
    if view is None and not ax.get_autoscale_on():
        (vx0, vx1), (vy0, vy1) = ax.get_xlim(), ax.get_ylim()
        view = (min(vx0, vx1), max(vx0, vx1), min(vy0, vy1), max(vy0, vy1))
    if view is not None:
        lo = np.maximum(lo, [view[0], view[2]])
        hi = np.minimum(hi, [view[1], view[3]])
        if np.any(hi <= lo):
            return lo, hi
    W_ = int(np.ceil((hi[0] - lo[0]) * px)) + 1
    H_ = int(np.ceil((hi[1] - lo[1]) * px)) + 1
    P = (T2 - lo) * px
    # cull what is wholly off the view, then split what is long on screen
    inview = ((P[:, :, 0].max(1) >= 0) & (P[:, :, 0].min(1) <= W_)
              & (P[:, :, 1].max(1) >= 0) & (P[:, :, 1].min(1) <= H_))
    keep = np.flatnonzero(inview)
    Ps, Zs_, Cs_, par = P[keep], Z[keep], C[keep], keep
    key, zmin, span = _rasterize(Ps, Zs_, (H_, W_))
    sub = np.where(key >= 0, key & ((1 << 24) - 1), -1)
    fidb = np.where(sub >= 0, par[np.maximum(sub, 0)], -1)     # original face
    depb = np.where(key >= 0, (key >> 24).astype(float) / float(2 ** 38 - 1)
                    * span + zmin, -np.inf)

    img = np.zeros((H_ * W_, 4), np.float32)
    hit = np.flatnonzero(sub >= 0)
    f = sub[hit]
    xc = (hit % W_) + 0.5
    yc = (hit // W_) + 0.5
    a, b, c = Ps[f, 0], Ps[f, 1], Ps[f, 2]
    area = ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
            - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    area = np.where(np.abs(area) < 1e-12, 1e-12, area)
    w0 = ((b[:, 0] - xc) * (c[:, 1] - yc) - (b[:, 1] - yc) * (c[:, 0] - xc)) / area
    w1 = ((c[:, 0] - xc) * (a[:, 1] - yc) - (c[:, 1] - yc) * (a[:, 0] - xc)) / area
    w0, w1 = np.clip(w0, 0, 1), np.clip(w1, 0, 1)
    w2 = np.clip(1.0 - w0 - w1, 0, 1)
    ws = np.maximum(w0 + w1 + w2, 1e-12)
    img[hit, :3] = (w0[:, None] * Cs_[f, 0] + w1[:, None] * Cs_[f, 1]
                    + w2[:, None] * Cs_[f, 2]) / ws[:, None]
    img[hit, 3] = 1.0
    img = img.reshape(H_, W_, 4)
    asp = ax.get_aspect()
    ax.imshow(img, origin="lower", extent=(lo[0], lo[0] + W_ / px,
                                           lo[1], lo[1] + H_ / px),
              interpolation="antialiased", zorder=z0, gid="geom")
    ax.set_aspect(asp)

    if EV:
        S2 = np.concatenate(EV); SZ = np.concatenate(EZ)
        SF = np.concatenate(EF); SW = np.concatenate(EW)
        # Liang-Barsky: keep only the part of each edge inside the raster box,
        # so a rail running off the page is not sampled metre by metre
        d = S2[:, 1] - S2[:, 0]
        t0 = np.zeros(len(S2)); t1 = np.ones(len(S2))
        bx0, by0 = lo[0], lo[1]
        bx1, by1 = lo[0] + W_ / px, lo[1] + H_ / px
        for p_, q_ in ((-d[:, 0], S2[:, 0, 0] - bx0), (d[:, 0], bx1 - S2[:, 0, 0]),
                       (-d[:, 1], S2[:, 0, 1] - by0), (d[:, 1], by1 - S2[:, 0, 1])):
            par = np.abs(p_) < 1e-12
            r = np.where(par, 0.0, q_ / np.where(par, 1.0, p_))
            t0 = np.where(~par & (p_ < 0), np.maximum(t0, r), t0)
            t1 = np.where(~par & (p_ > 0), np.minimum(t1, r), t1)
            t1 = np.where(par & (q_ < 0), -1.0, t1)
        okc = t1 > t0
        A_ = S2[:, 0] + d * t0[:, None]
        B_ = S2[:, 0] + d * t1[:, None]
        zA = SZ[:, 0] + (SZ[:, 1] - SZ[:, 0]) * t0
        zB = SZ[:, 0] + (SZ[:, 1] - SZ[:, 0]) * t1
        S2 = np.stack([A_, B_], 1)[okc]; SZ = np.stack([zA, zB], 1)[okc]
        SF = SF[okc]; SW = SW[okc]
        L = np.linalg.norm((S2[:, 1] - S2[:, 0]) * px, axis=1)
        k = np.maximum(2, np.ceil(L / 0.6).astype(int) + 1)
        sid = np.repeat(np.arange(len(S2)), k)
        first = np.concatenate([[0], np.cumsum(k)[:-1]])
        t = (np.arange(len(sid)) - first[sid]) / (k[sid] - 1)
        xy = S2[sid, 0] + (S2[sid, 1] - S2[sid, 0]) * t[:, None]
        zz = SZ[sid, 0] + (SZ[sid, 1] - SZ[sid, 0]) * t
        ij = np.floor((xy - lo) * px).astype(int)
        ij[:, 0] = np.clip(ij[:, 0], 0, W_ - 1)
        ij[:, 1] = np.clip(ij[:, 1], 0, H_ - 1)
        pix = ij[:, 1] * W_ + ij[:, 0]
        bf = fidb[pix]
        vis = ((bf < 0) | (bf == SF[sid, 0]) | (bf == SF[sid, 1])
               | (depb[pix] <= zz + tol))
        # runs of visible samples within each segment
        prev = np.r_[False, vis[:-1]] & np.r_[False, sid[1:] == sid[:-1]]
        nxt = np.r_[vis[1:], False] & np.r_[sid[1:] == sid[:-1], False]
        rs = np.flatnonzero(vis & ~prev)
        re_ = np.flatnonzero(vis & ~nxt)
        if len(rs):
            seg_id = sid[rs]
            half = 0.5 / (k[seg_id] - 1)
            t0 = np.clip(t[rs] - half, 0, 1)
            t1 = np.clip(t[re_] + half, 0, 1)
            A0 = S2[seg_id, 0] + (S2[seg_id, 1] - S2[seg_id, 0]) * t0[:, None]
            A1 = S2[seg_id, 0] + (S2[seg_id, 1] - S2[seg_id, 0]) * t1[:, None]
            segs = np.stack([A0, A1], axis=1)
            ax.add_collection(LineCollection(segs, colors=LINE,
                                             linewidths=SW[seg_id],
                                             zorder=z0 + 1, capstyle="round",
                                             gid="geom"))
    return lo, hi


# ------------------------------------------------------------------ annotation
def arrow(ax, p0, p1, M=None, color="#c2410c", lw=2.0, rad=0.0, zorder=9):
    M = iso_matrix() if M is None else M
    a = np.asarray(p0, float) @ M.T
    b = np.asarray(p1, float) @ M.T
    ax.add_patch(FancyArrowPatch((a[0], a[1]), (b[0], b[1]),
                                 arrowstyle="-|>", mutation_scale=15,
                                 lw=lw, color=color, zorder=zorder,
                                 connectionstyle=f"arc3,rad={rad}"))


def badge(ax, x, y, n, r=16, fc="#15191c", tc="white", fs=16):
    ax.add_patch(Circle((x, y), r, facecolor=fc, edgecolor="none", zorder=20))
    ax.text(x, y, str(n), ha="center", va="center", color=tc, fontsize=fs,
            fontweight="bold", zorder=21)


def callout(ax, x, y, text, qty=None, fs=9.5, color=INK):
    t = f"{qty}x  {text}" if qty else text
    ax.text(x, y, t, fontsize=fs, color=color, va="center", zorder=20,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=RULE, lw=0.8))


def leader(ax, p_from, p_to, color=DIM, lw=0.8):
    ax.plot([p_from[0], p_to[0]], [p_from[1], p_to[1]], color=color, lw=lw,
            zorder=19)
    ax.add_patch(Circle(p_to, 1.6, facecolor=color, edgecolor="none", zorder=19))


def page(w_in=11.0, h_in=14.0, title=None, sub=None, step=None, foot=None):
    fig = plt.figure(figsize=(w_in, h_in), facecolor="white")
    ax = fig.add_axes([0.03, 0.03, 0.94, 0.94])
    ax.set_aspect("equal"); ax.axis("off")
    return fig, ax


def finish(ax, lo, hi, pad=0.10, extra=None):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    if extra is not None:
        e = np.asarray(extra, float)
        lo = np.minimum(lo, e.min(0)); hi = np.maximum(hi, e.max(0))
    span = max(hi - lo)
    cx, cy = (lo + hi) / 2
    r = span * (0.5 + pad)
    ax.set_xlim(cx - r, cx + r); ax.set_ylim(cy - r, cy + r)
