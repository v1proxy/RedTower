"""Self-collision for the posed 280, from the real link meshes.

Each link's surface is sampled densely and dropped into a voxel grid. Two
links that share voxels are touching or interpenetrating. Adjacent links
always touch at their joint, so only pairs two or more apart in the chain
are checked. The meshes are open CAD shells, so an inside/outside test is
not trustworthy; surface overlap is, and a fold that drives one link
through another always crosses surfaces.
"""
import numpy as np
import arm280 as A

ORDER = ["g_base", "joint1", "joint2", "joint3", "joint4", "joint5",
         "joint6", "joint6_flange"]


def _surface_points(V, F, step):
    """Sample a triangle soup at roughly `step` spacing."""
    T = V[F]
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)
    n = np.maximum(1, np.ceil(area / (step * step) * 2.0)).astype(int)
    idx = np.repeat(np.arange(len(F)), n)
    r1 = np.random.default_rng(0).random(len(idx))
    r2 = np.random.default_rng(1).random(len(idx))
    flip = r1 + r2 > 1
    r1[flip], r2[flip] = 1 - r1[flip], 1 - r2[flip]
    P = T[idx, 0] + e1[idx] * r1[:, None] + e2[idx] * r2[:, None]
    return np.vstack([P, V])


def voxels(q, vox=2.0, grid=0.0012):
    out = {}
    for name, (V, F) in A.pose(q, grid=grid):
        P = _surface_points(V, F, vox * 0.6)
        out[name] = set(map(tuple, np.floor(P / vox).astype(np.int64)))
    return out


def clashes(q, vox=2.0, gap=2):
    """Pairs of links at least `gap` apart in the chain that share voxels."""
    vx = voxels(q, vox)
    bad = []
    for i in range(len(ORDER)):
        for j in range(i + gap, len(ORDER)):
            n = len(vx[ORDER[i]] & vx[ORDER[j]])
            if n:
                bad.append((ORDER[i], ORDER[j], n))
    return bad


# ------------------------------------------------------- fast pose sweeps
_LOCAL = {}


def _local_pts(n_hi=6000, n_lo=300, grid=0.0012):
    """Surface samples per link in the LINK frame (visual origin applied)."""
    if _LOCAL:
        return _LOCAL
    import math
    for name, fn, vxyz, vrpy in A.LINKS:
        V, F = A._mesh(fn, grid)
        M = A._xf(vxyz, vrpy)
        Vl = (np.hstack([V, np.ones((len(V), 1))]) @ M.T)[:, :3] * A.MM
        P = _surface_points(Vl, F, 1.2)
        rng = np.random.default_rng(7)
        hi = P[rng.choice(len(P), min(n_hi, len(P)), replace=False)]
        lo = P[rng.choice(len(P), min(n_lo, len(P)), replace=False)]
        _LOCAL[name] = (P, hi, lo)
    return _LOCAL


def posed_pts(q, which=1):
    fr = A.frames(q)
    L = _local_pts()
    out = {}
    for name in ORDER:
        P = L[name][which]
        T = fr[name].copy()
        T[:3, 3] *= A.MM
        out[name] = (np.hstack([P, np.ones((len(P), 1))]) @ T.T)[:, :3]
    return out


def height(q):
    """Arm length along its own J1 axis, from the g_base origin, mm."""
    pts = posed_pts(q, which=2)
    return max(p[:, 2].max() for p in pts.values())


def clean(q, vox=2.0, gap=2):
    pts = posed_pts(q, which=0)
    vx = {k: set(map(tuple, np.floor(p / vox).astype(np.int64)))
          for k, p in pts.items()}
    for i in range(len(ORDER)):
        for j in range(i + gap, len(ORDER)):
            if vx[ORDER[i]] & vx[ORDER[j]]:
                return False
    return True
