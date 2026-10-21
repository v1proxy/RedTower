"""Quadric edge-collapse decimation, in numpy, for the print files: the meshes come off
marching cubes on a fine grid, so their flat faces are thousands of coplanar triangles that
can merge at no cost, while curved and sharp places keep their triangles. This is what
decimate_blender.py does with Blender's planar decimate, without needing Blender.

Collapses run in batches of edges that share no neighbourhood, cheapest first, and each is
kept only if it keeps the surface closed and manifold (exactly two shared neighbours), flips
no triangle, and moves the surface no more than `tol` mm from every plane it came from.
check() then measures the result against the part's own signed-distance model.

    python decimate.py <part> [<part> ...]     build/mesh_<part>.npz -> build/mesh_<part>_dec.npz
"""
from __future__ import annotations
import os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _planes(V, F):
    T = V[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    n = n / np.maximum(ln, 1e-30)[:, None]
    d = -np.einsum("ij,ij->i", n, T[:, 0])
    return np.c_[n, d], ln


def _quadrics(V, F):
    p, ln = _planes(V, F)
    p[ln < 1e-14] = 0.0
    K = p[:, :, None] * p[:, None, :]
    Q = np.zeros((len(V), 4, 4))
    for k in range(3):
        np.add.at(Q, F[:, k], K)
    return Q


def _edges(F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    return np.unique(E, axis=0)


def _csr(idx_rows, idx_cols, n):
    order = np.argsort(idx_rows, kind="stable")
    r, c = idx_rows[order], idx_cols[order]
    ptr = np.zeros(n + 1, np.int64)
    np.add.at(ptr, r + 1, 1)
    return np.cumsum(ptr), c


def decimate(V, F, tol=0.02, max_pass=60, verbose=True):
    V = V.astype(float).copy(); F = F.astype(np.int64).copy()
    Q = _quadrics(V, F)
    tol2 = tol * tol
    for it in range(max_pass):
        E = _edges(F)
        Qe = Q[E[:, 0]] + Q[E[:, 1]]
        A = Qe[:, :3, :3]; b = -Qe[:, :3, 3]
        det = np.linalg.det(A)
        good = np.abs(det) > 1e-10
        X = 0.5 * (V[E[:, 0]] + V[E[:, 1]])
        if good.any():
            X[good] = np.linalg.solve(A[good], b[good][:, :, None])[:, :, 0]
        # fall back to the better of the two ends and the midpoint where the solve is far off
        cand = [X, V[E[:, 0]], V[E[:, 1]], 0.5 * (V[E[:, 0]] + V[E[:, 1]])]
        far = np.linalg.norm(X - 0.5 * (V[E[:, 0]] + V[E[:, 1]]), axis=1) > \
            np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1) * 2.0

        def cost(P):
            h = np.c_[P, np.ones(len(P))]
            return np.einsum("ni,nij,nj->n", h, Qe, h)
        costs = np.stack([cost(P) for P in cand])
        costs[0, far] = np.inf
        pick = costs.argmin(0)
        X = np.stack(cand)[pick, np.arange(len(E))]
        c = costs[pick, np.arange(len(E))]
        ok = c < tol2
        if not ok.any():
            break
        order = np.where(ok)[0][np.argsort(c[ok], kind="stable")]
        # vertex -> faces and vertex -> neighbours
        fptr, fidx = _csr(F.ravel(), np.repeat(np.arange(len(F)), 3), len(V))
        nb_r = np.r_[E[:, 0], E[:, 1]]; nb_c = np.r_[E[:, 1], E[:, 0]]
        nptr, nidx = _csr(nb_r, nb_c, len(V))
        locked = np.zeros(len(V), bool)
        chosen = []
        for e in order:
            a, bb = E[e]
            if locked[a] or locked[bb]:
                continue
            na = nidx[nptr[a]:nptr[a + 1]]; nbb = nidx[nptr[bb]:nptr[bb + 1]]
            if len(np.intersect1d(na, nbb, assume_unique=True)) != 2:
                continue                                      # the link condition: stays manifold
            fa = fidx[fptr[a]:fptr[a + 1]]; fb = fidx[fptr[bb]:fptr[bb + 1]]
            fs = np.unique(np.r_[fa, fb])
            T = F[fs]
            keep = ~((T == a).any(1) & (T == bb).any(1))
            T = T[keep]
            Vo = V[T]
            n0 = np.cross(Vo[:, 1] - Vo[:, 0], Vo[:, 2] - Vo[:, 0])
            Vn = Vo.copy()
            m = (T == a) | (T == bb)
            Vn[m] = X[e]
            n1 = np.cross(Vn[:, 1] - Vn[:, 0], Vn[:, 2] - Vn[:, 0])
            l0 = np.linalg.norm(n0, axis=1); l1 = np.linalg.norm(n1, axis=1)
            if (l1 < 1e-12).any():
                continue
            if (np.einsum("ij,ij->i", n0, n1) < 0.2 * l0 * l1).any():
                continue                                      # a flip, or a fold too sharp
            chosen.append(e)
            locked[na] = True; locked[nbb] = True; locked[a] = True; locked[bb] = True
        if not chosen:
            break
        ch = np.array(chosen)
        a, bb = E[ch, 0], E[ch, 1]
        V[a] = X[ch]
        Q[a] = Q[a] + Q[bb]
        remap = np.arange(len(V)); remap[bb] = a
        F = remap[F]
        F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
        if verbose:
            print(f"   pass {it}: {len(ch)} collapses, {len(F)} faces", flush=True)
    used = np.unique(F)
    remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))
    return V[used], remap[F]


def open_edges(F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _, n = np.unique(E, axis=0, return_counts=True)
    return int((n != 2).sum())


def check(name, V, F, n_pts=200000):
    """How far the decimated surface strays from the part's own SDF: vertices, edge
    midpoints and random points on the faces."""
    import snip_cad as C
    f = C.PARTS[name]()
    T = V[F]
    r = np.random.default_rng(0)
    idx = r.integers(len(F), size=n_pts)
    u = r.random((n_pts, 2)); flip = u.sum(1) > 1; u[flip] = 1 - u[flip]
    P = T[idx, 0] + (T[idx, 1] - T[idx, 0]) * u[:, :1] + (T[idx, 2] - T[idx, 0]) * u[:, 1:]
    mids = 0.5 * (T[:, 0] + T[:, 1])
    d = np.abs(np.r_[f(V), f(P), f(mids)])
    return float(d.max()), float(np.percentile(d, 99.9))


if __name__ == "__main__":
    import sdf as S
    for nm in sys.argv[1:]:
        src = nm
        d = np.load(os.path.join(HERE, "build", f"mesh_{src}.npz"))
        V, F = d["V"], d["F"]
        t = time.time()
        W, G = decimate(V, F)
        dev = check(nm, W, G)
        np.savez_compressed(os.path.join(HERE, "build", f"mesh_{src}_dec.npz"), V=W, F=G)
        print(f"{nm}: {len(F)} -> {len(G)} faces, volume {S.volume(V, F):.1f} -> {S.volume(W, G):.1f} mm3, "
              f"{open_edges(G)} open edges, off the model by {dev[0]:.3f} max, {dev[1]:.3f} at 99.9 % "
              f"({time.time() - t:.0f} s)", flush=True)
