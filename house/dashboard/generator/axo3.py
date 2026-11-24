# Red Tower in lines, the lean version (Vittorio's note, Nov 24: "this model needs to be lean, so many artifacts; fix
# those axo models across the whole platform"). Same camera, frame and layout data as axo2.py; only the lines change:
# instead of every triangle edge, the drawing is the boundary between surfaces as seen. Each visible pixel takes a
# surface: the walls and cladding by their facing direction, a window or door (frame, its depth and the glass) as one surface,
# metal and the skylight by their object. Specks and strips thinner than a couple of pixels join their neighbours, so
# grooves, trims, mullions and frame depths disappear. A line runs where two surfaces meet or the depth jumps; each
# boundary is drawn once and straightened (Douglas-Peucker), so no doubled, broken or jittery strokes.
#   python -I axo3.py GLB OUT.json
import json, math, os, sys, time
import numpy as np
from scipy import ndimage as ndi
from skimage.measure import approximate_polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
src = open(os.path.join(HERE, "axo2.py")).read()
src = src.replace('if __name__ == "__main__":', 'if False:')
src = src.replace("return dict(segs=segs, anchors=anc,", "return dict(_fid=fid, _zb=zb, _c=c, segs=segs, anchors=anc,")
A2 = {"__file__": os.path.join(HERE, "axo2.py"), "__name__": "axo2p"}
exec(compile(src, "axo2p", "exec"), A2)
load = A2["load"]; prepare = A2["prepare"]; view = A2["view"]; axes = A2["axes"]; band_of = A2["band_of"]; PXCM = A2["PXCM"]

DEPTH_STEP = 12.0     # cm: same surface kind, but the depth jumps: a line (a façade set back, a parapet)
PROFILE = 40.0        # cm: a jump this big, or the sky behind, is a profile line (drawn stronger)
MIN_AREA = 36         # px: specks smaller than this join their neighbours
MIN_WIDTH = 2.6       # px: strips thinner than this (2 * area / perimeter) join their neighbours
TOL = 1.3             # px: straightening tolerance (a crack-edge staircase strays up to about 0.7 px)
MIN_LEN = 5.0         # px: shorter lines are dropped


def face_labels(M):
    """A surface id per triangle: walls and cladding by facing direction; openings by facing direction; metal, skylight
    and watched objects by object."""
    keep, fobj, n = M["keep"], M["fobj"], M["n"]
    kind = np.zeros(len(keep), np.int64)          # 1 envelope, 2 opening, 3 metal, 4 skylight, 5 interior
    for oi, (name, mat, p, idx, w) in enumerate(keep):
        b = name[6:] if name.startswith("lvl") else name
        if w in ("window_guest_room", "door_balcony") or b.startswith("glass") or (b.startswith("frame") and mat in ("rt_frame", "rt_window_alu")):
            kind[oi] = 2
        elif b.startswith("metal"):
            kind[oi] = 3
        elif b.startswith("skylight"):
            kind[oi] = 4
        elif w:
            kind[oi] = 5
        else:
            kind[oi] = 1
    fk = kind[fobj]
    q = np.round(n * 3).astype(np.int64) + 3                   # facing direction, about 20 degree buckets
    nid = q[:, 0] * 49 + q[:, 1] * 7 + q[:, 2]
    # envelope by facing direction; a window or door (frame, its depth and the glass) as one surface; the rest by object
    lab = np.where(fk == 1, 1000 + nid, np.where(fk == 2, 2000, fk * 1000 + 500 + fobj))
    return lab


def clean(L):
    """Specks and thin strips take the surface of their nearest neighbour; repeated until nothing changes."""
    for _ in range(4):
        bad = np.zeros(L.shape, bool)
        for v in np.unique(L):
            if v < 0:
                continue
            m = L == v
            cc, nc = ndi.label(m)
            if nc == 0:
                continue
            area = ndi.sum(m, cc, index=np.arange(1, nc + 1))
            er = m & ~ndi.binary_erosion(m)
            per = ndi.sum(er, cc, index=np.arange(1, nc + 1))
            width = 2 * area / np.maximum(per, 1)
            small = np.flatnonzero((area < MIN_AREA) | (width < MIN_WIDTH)) + 1
            if len(small):
                bad |= np.isin(cc, small)
        if not bad.any():
            break
        idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
        L = L[idx[0], idx[1]]
    return L


def chains(edges):
    """Crack edges (x0, y0, x1, y1 on the pixel grid) chained into polylines that end at junctions."""
    from collections import defaultdict
    adj = defaultdict(list)
    for i, (a, b, c, d) in enumerate(edges):
        adj[(a, b)].append(i); adj[(c, d)].append(i)
    used = np.zeros(len(edges), bool)
    out = []

    def other(i, v):
        a, b, c, d = edges[i]
        return (c, d) if (a, b) == v else (a, b)

    def walk(v, i):
        pts = [v]
        while True:
            used[i] = True
            v = other(i, v); pts.append(v)
            if len(adj[v]) != 2:
                return pts
            nxt = [j for j in adj[v] if not used[j]]
            if not nxt:
                return pts
            i = nxt[0]
    for v, lst in list(adj.items()):
        if len(lst) != 2:
            for i in lst:
                if not used[i]:
                    out.append(walk(v, i))
    for i in range(len(edges)):
        if not used[i]:
            a, b, c, d = edges[i]
            out.append(walk((a, b), i))
    return out


def lean(M, v, W, H, az):
    fid, zb, c = v["_fid"], v["_zb"], v["_c"]
    L = np.where(fid >= 0, M["_lab"][np.clip(fid, 0, None)], -1)
    L = clean(L)
    Zf = np.where(np.isfinite(zb), zb, -1e9)
    X, Y, Z = axes(az)
    ii, jj = np.nonzero(L >= 0)
    uu = (jj + 0.5 - W / 2) / PXCM + c[0]
    vv = c[1] - (ii + 0.5 - H / 2) / PXCM
    band = np.zeros(L.shape, np.int8)
    band[ii, jj] = band_of(np.outer(uu, X) + np.outer(vv, Y) + np.outer(zb[ii, jj], Z))
    groups = {}

    def add(la, lb, za, zbb, ba, bb, x0, y0, x1, y1):
        diff = (la != lb) | ((la >= 1000) & (la < 2000) & (np.abs(za - zbb) > DEPTH_STEP))
        prof = (la < 0) | (lb < 0) | (np.abs(za - zbb) > PROFILE)
        front = np.where(za >= zbb, ba, bb)
        for k in np.flatnonzero(diff.ravel()):
            key = ("2" if prof.ravel()[k] else "1", int(front.ravel()[k]))
            groups.setdefault(key, []).append((int(x0.ravel()[k]), int(y0.ravel()[k]), int(x1.ravel()[k]), int(y1.ravel()[k])))

    ys, xs = np.mgrid[0:H, 0:W - 1]
    add(L[:, :-1], L[:, 1:], Zf[:, :-1], Zf[:, 1:], band[:, :-1], band[:, 1:], xs + 1, ys, xs + 1, ys + 1)
    ys, xs = np.mgrid[0:H - 1, 0:W]
    add(L[:-1, :], L[1:, :], Zf[:-1, :], Zf[1:, :], band[:-1, :], band[1:, :], xs, ys + 1, xs + 1, ys + 1)
    lines = {}
    for (cls, f), edges in groups.items():
        if f == 0:
            continue
        out = []
        for pts in chains(edges):
            P = np.array(pts, float)
            P = approximate_polygon(P, TOL)
            if len(P) < 2:
                continue
            if np.hypot(*np.diff(P, axis=0).T).sum() < MIN_LEN:
                continue
            out.append([[round(float(x), 1), round(float(y), 1)] for x, y in P])
        lines[f"{cls}:@{f}"] = out
    return lines


def main(glb, out):
    t0 = time.time()
    js, prims = load(glb)
    M = prepare(prims)
    M["_lab"] = face_labels(M)
    P = M["P"]
    cx3 = (P.min(0) + P.max(0)) / 2
    W = H = int(math.ceil(np.linalg.norm(P.max(0) - P.min(0)) * PXCM)) + 40
    res = {"W": W, "H": H, "px_per_cm": PXCM, "views": []}
    for k in range(8):
        az = 45 + 45 * k
        v = view(M, az, W, H, cx3)
        v["lines"] = lean(M, v, W, H, az)
        for key in ("_fid", "_zb", "_c"):
            v.pop(key)
        v["az"] = az
        res["views"].append(v)
        print(f"view {k}: " + ", ".join(f"{kk} {len(vv)}" for kk, vv in sorted(v["lines"].items())), f"{time.time() - t0:.0f}s", flush=True)
    json.dump(res, open(out, "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
