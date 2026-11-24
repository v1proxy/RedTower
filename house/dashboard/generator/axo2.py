# Red Tower line axonometry, all eight views (the 3D card's isometric camera turned in 45 degree steps around the
# vertical axis; view 0 is the card's own, from the street). Hidden lines removed with a z-buffer; a triangle edge is
# drawn where its two sides show different surfaces. Also: each floor's room outlines and the watched objects, seen
# and hidden parts apart, and anchor points, all in one frame centred on the house so the views turn about its axis.
#   python -I axo2.py GLB OUT.json
import json, sys, math, time, os, warnings
warnings.filterwarnings('ignore', category=FutureWarning)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from glb import load

SKIP = ("room_", "light_", "cut_", "car_", "appliance", "casework", "fixture", "sanitary", "furniture", "books_", "shelf_", "sofa_", "arco_",
        "bed_", "mattress_", "nightstand_", "parentesi_", "counter", "stair", "tv_living_room", "site_")
WATCH = ("window_guest_room", "door_balcony", "vacuum_asimov", "vacuum_sagan", "tv_living_room_screen")
LEVEL_Y = {1: 33.5, 2: 307.8, 3: 582.2}
PXCM = 1.2          # raster pixels per cm, the same for every view
ANCHORS = {"asimov": (426.3, 584.3, 315.8), "bedroom": None, "kitchen": None, "greenhouse": None}
TOWER = (370.0, 1095.0, 85.0, 735.0)
ROOM_H = 244.0                          # a room's box: from its floor up 8 ft
# the openings with a sensor, as drawn on the outside wall: the frame's outer rectangle and the glass (cm, from the GLB)
OPENINGS = {"window_guest_room": dict(x=376.0, rects=[((110.0, 187.0), (611.0, 698.0)), ((117.0, 180.0), (618.0, 681.0))]),
            "door_balcony": dict(x=379.0, rects=[((305.0, 503.0), (285.0, 524.0)), ((310.0, 498.0), (290.0, 518.0))])}    # x0, x1, z0, z1 (cm): the third floor and the tower roof stand only on this footprint


def band_of(P):
    """The floor each 3D point belongs to: 1 ground, 2 second, 3 third (the east block's roof stays with the second)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    tower = (x >= TOWER[0]) & (x <= TOWER[1]) & (z >= TOWER[2]) & (z <= TOWER[3])
    return np.where(y < LEVEL_Y[2] - 0.5, 1, np.where((y >= LEVEL_Y[3] - 0.5) & tower, 3, 2)).astype(np.int8)


def trace(m, min_area=250, tol=0.9, fill=False):
    """Outline of a pixel region as polylines (screen px), small specks and pinholes dropped."""
    from scipy import ndimage as ndi
    from skimage import measure, morphology
    m = ndi.binary_closing(np.pad(m, 2), structure=np.ones((3, 3), bool))[2:-2, 2:-2]
    m = ndi.binary_fill_holes(m) if fill else morphology.remove_small_holes(m, area_threshold=min_area)
    m = morphology.remove_small_objects(m, min_size=min_area)
    out = []
    for cnt in measure.find_contours(np.pad(m, 1).astype(np.float32), 0.5):
        cnt = measure.approximate_polygon(cnt, tol)
        if len(cnt) < 3:
            continue
        out.append([[round(float(cc) - 0.5, 1), round(float(r) - 0.5, 1)] for r, cc in cnt])
    return out


def base(n):
    return n[6:] if n.startswith("lvl") else n


def axes(az_deg):
    a = math.radians(az_deg)
    Z = np.array([math.cos(a) * math.sqrt(2 / 3), math.sqrt(1 / 3), math.sin(a) * math.sqrt(2 / 3)])
    X = np.array([math.sin(a), 0.0, -math.cos(a)])
    Y = np.cross(Z, X)
    return X, Y, Z


def prepare(prims):
    keep, rooms = [], {}
    for name, mat, p, idx in prims:
        b = base(name)
        if b.startswith("room_"):
            lvl = int(name[3:6]) + 1
            rooms.setdefault(lvl, []).append((b[5:], p, idx))
            continue
        w = next((k for k in WATCH if b == k), None)
        if w or not any(b.startswith(s) for s in SKIP):
            keep.append((name, mat, p, idx, w))
    P, F, fobj, fmat = [], [], [], []
    mats, off = {}, 0
    for oi, (name, mat, p, idx, w) in enumerate(keep):
        P.append(p); F.append(idx + off); off += len(p)
        fobj.append(np.full(len(idx), oi)); fmat.append(np.full(len(idx), mats.setdefault(mat, len(mats))))
    P = np.vstack(P); F = np.vstack(F); fobj = np.concatenate(fobj); fmat = np.concatenate(fmat)
    tri = P[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    a2 = np.linalg.norm(n, axis=1)
    g = a2 > 1e-6
    F, fobj, fmat, n = F[g], fobj[g], fmat[g], n[g] / a2[g, None]
    fo = np.einsum("ij,ij->i", n, P[F[:, 0]])
    # every triangle edge once per object
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    eobj = np.concatenate([fobj, fobj, fobj])
    q = np.round(P / 0.05).astype(np.int64)
    ka, kb = q[E[:, 0]], q[E[:, 1]]
    sw = (ka[:, 0] > kb[:, 0]) | ((ka[:, 0] == kb[:, 0]) & ((ka[:, 1] > kb[:, 1]) | ((ka[:, 1] == kb[:, 1]) & (ka[:, 2] > kb[:, 2]))))
    A = np.where(sw[:, None], kb, ka); B = np.where(sw[:, None], ka, kb)
    key = np.concatenate([A, B, eobj[:, None]], 1)
    _, first, inv, cnt = np.unique(key, axis=0, return_index=True, return_inverse=True, return_counts=True)
    E, eobj = E[first], eobj[first]
    # watched objects: only their outline and creases (edges with one face, or two faces bent > 20 degrees)
    fidx3 = np.concatenate([np.arange(len(F))] * 3)
    efaces = [[] for _ in range(len(first))]
    for fi, ei in zip(fidx3, inv.ravel()):
        if keep[fobj[fi]][4]:
            efaces[ei].append(fi)
    wcrease = np.zeros(len(first), bool)
    for ei, fl in enumerate(efaces):
        if not fl:
            continue
        if len(fl) != 2 or abs(np.dot(n[fl[0]], n[fl[1]])) < math.cos(math.radians(20)):
            wcrease[ei] = True
    # room outlines per level: boundary edges of each room's plane
    rl = {}
    for lvl, lst in rooms.items():
        segs = []
        for rname, p, idx in lst:
            e = np.concatenate([idx[:, [0, 1]], idx[:, [1, 2]], idx[:, [2, 0]]])
            qq = np.round(p / 0.5).astype(np.int64)
            k2 = [tuple(sorted((tuple(qq[a]), tuple(qq[b])))) for a, b in e]
            from collections import Counter
            c = Counter(k2)
            for (a, b), kk in zip(e, k2):
                if c[kk] == 1:
                    segs.append((p[a], p[b], rname))
        rl[lvl] = segs
    centers = {}
    for lvl, lst in rooms.items():
        for rname, p, idx in lst:
            centers[rname] = ((p[:, 0].min() + p[:, 0].max()) / 2, p[:, 1].mean(), (p[:, 2].min() + p[:, 2].max()) / 2)
    # each room as a box: its floor plane, raised ROOM_H; the boundary and the corners where the boundary turns
    boxes = {}
    for lvl, lst in rooms.items():
        for rname, p, idx in lst:
            segs = [(a, b) for a, b, rn in rl[lvl] if rn == rname]
            q = lambda v: (round(float(v[0]), 1), round(float(v[2]), 1))
            nb = {}
            for a, b in segs:
                nb.setdefault(q(a), []).append(b); nb.setdefault(q(b), []).append(a)
            corners = []
            for a, b in segs:
                for v in (a, b):
                    lst2 = nb[q(v)]
                    if len(lst2) != 2:
                        corners.append(v); continue
                    d1 = np.array(lst2[0]) - v; d2 = np.array(lst2[1]) - v
                    d1 = d1 / (np.linalg.norm(d1) + 1e-9); d2 = d2 / (np.linalg.norm(d2) + 1e-9)
                    if abs(d1[0] * d2[2] - d1[2] * d2[0]) > math.sin(math.radians(10)):
                        corners.append(v)
            uniq = {}
            for v in corners:
                uniq[q(v)] = v
            boxes[rname] = dict(lvl=lvl, y0=float(p[:, 1].mean()), tri=p[idx], segs=segs, corners=list(uniq.values()))
    wc = {}
    for name, mat, p, idx, w in keep:
        if w:
            wc.setdefault(w, []).append(p)
    wcent = {w: ((np.vstack(ps).min(0) + np.vstack(ps).max(0)) / 2) for w, ps in wc.items()}
    return dict(keep=keep, P=P, F=F, fobj=fobj, fmat=fmat, n=n, fo=fo, E=E, eobj=eobj, wcrease=wcrease, rooms=rl, centers=centers,
                boxes=boxes, wcent=wcent)


def view(M, az, W, H, cx3):
    X, Y, Z = axes(az)
    P, F = M["P"], M["F"]
    c = np.array([cx3 @ X, cx3 @ Y])
    px = (P @ X - c[0]) * PXCM + W / 2
    py = (c[1] - P @ Y) * PXCM + H / 2
    sd = P @ Z
    zb = np.full((H, W), -np.inf)
    fid = np.full((H, W), -1, dtype=np.int64)
    V = np.stack([px, py, sd], 1)[F]
    for i in range(len(F)):
        a, b, cc = V[i]
        xmin, xmax = int(max(0, math.floor(min(a[0], b[0], cc[0])))), int(min(W - 1, math.ceil(max(a[0], b[0], cc[0]))))
        ymin, ymax = int(max(0, math.floor(min(a[1], b[1], cc[1])))), int(min(H - 1, math.ceil(max(a[1], b[1], cc[1]))))
        if xmax < xmin or ymax < ymin:
            continue
        den = (b[1] - cc[1]) * (a[0] - cc[0]) + (cc[0] - b[0]) * (a[1] - cc[1])
        if abs(den) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
        l1 = ((b[1] - cc[1]) * (gx - cc[0]) + (cc[0] - b[0]) * (gy - cc[1])) / den
        l2 = ((cc[1] - a[1]) * (gx - cc[0]) + (a[0] - cc[0]) * (gy - cc[1])) / den
        l3 = 1 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            continue
        d = l1 * a[2] + l2 * b[2] + l3 * cc[2]
        sub = zb[ymin:ymax + 1, xmin:xmax + 1]
        upd = m & (d > sub)
        sub[upd] = d[upd]
        fid[ymin:ymax + 1, xmin:xmax + 1][upd] = i
    n, fo, fmat = M["n"], M["fo"], M["fmat"]

    def look(xx, yy):
        jx, jy = np.clip(xx.astype(np.int64), 0, W - 1), np.clip(yy.astype(np.int64), 0, H - 1)
        return fid[jy, jx], zb[jy, jx]

    def sample(pa, pb, step=0.7):
        L = np.hypot(pb[:, 0] - pa[:, 0], pb[:, 1] - pa[:, 1])
        ns = np.maximum(2, np.ceil(L / step).astype(np.int64))
        eid = np.repeat(np.arange(len(pa)), ns)
        start = np.cumsum(ns) - ns
        k = np.arange(ns.sum()) - np.repeat(start, ns)
        t = (k + 0.5) / np.repeat(ns, ns)
        S = pa[eid] + (pb[eid] - pa[eid]) * t[:, None]
        return L, ns, eid, k, t, S

    def runs(cls, eid, k, t, ns, pa, pb, tag):
        out = {}
        order = np.lexsort((k, eid))
        cl, ei = cls[order], eid[order]
        brk = np.flatnonzero((np.diff(cl) != 0) | (np.diff(ei) != 0)) + 1
        st = np.concatenate([[0], brk]); en = np.concatenate([brk, [len(cl)]])
        for a_, b_ in zip(st, en):
            cc_ = int(cl[a_])
            if cc_ == 0:
                continue
            e = int(ei[a_])
            i0, i1 = order[a_], order[b_ - 1]
            ta = t[i0] - 0.5 / ns[e]; tb = t[i1] + 0.5 / ns[e]
            p0 = pa[e] + (pb[e] - pa[e]) * ta; p1 = pa[e] + (pb[e] - pa[e]) * tb
            if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 1.0:
                continue
            out.setdefault(tag(cc_, e), []).append([round(float(p0[0]), 1), round(float(p0[1]), 1), round(float(p1[0]), 1), round(float(p1[1]), 1)])
        return out

    def close_gaps(cls, eid, k, maxgap=2):
        # fill short undrawn gaps inside a run of the same drawn class along one edge (visibility flicker)
        order = np.lexsort((k, eid))
        c = cls[order].copy(); e = eid[order]
        for g in range(1, maxgap + 1):
            for sh in range(1, g + 1):
                pass
        i = 0
        nn = len(c)
        while i < nn:
            if c[i] == 0 and i > 0 and c[i - 1] != 0:
                j = i
                while j < nn and c[j] == 0 and e[j] == e[i - 1] and j - i < maxgap + 1:
                    j += 1
                if j < nn and j - i <= maxgap and c[j] == c[i - 1] and e[j] == e[i - 1]:
                    c[i:j] = c[i - 1]
                i = j if j > i else i + 1
            else:
                i += 1
        out = cls.copy(); out[order] = c
        return out

    E, eobj, keep = M["E"], M["eobj"], M["keep"]
    pts = np.stack([px, py, sd], 1)
    pa, pb = pts[E[:, 0]], pts[E[:, 1]]
    L, ns, eid, k, t, S = sample(pa, pb)
    ix = np.clip(S[:, 0].astype(np.int64), 0, W - 1); iy = np.clip(S[:, 1].astype(np.int64), 0, H - 1)
    vis = S[:, 2] >= zb[iy, ix] - 3.0
    Lz = np.maximum(L, 1e-9)
    dx = (pb[:, 0] - pa[:, 0]) / Lz; dy = (pb[:, 1] - pa[:, 1]) / Lz
    nx, ny = -dy[eid] * 1.6, dx[eid] * 1.6
    f1, z1 = look(S[:, 0] + nx, S[:, 1] + ny)
    f2, z2 = look(S[:, 0] - nx, S[:, 1] - ny)
    ok = (f1 >= 0) & (f2 >= 0)
    a1, a2 = np.where(ok, f1, 0), np.where(ok, f2, 0)
    dot = np.einsum("ij,ij->i", n[a1], n[a2])
    same = ok & (np.abs(dot) > math.cos(math.radians(4))) & (np.abs(fo[a1] - np.sign(dot) * fo[a2]) < 2.0) & (fmat[a1] == fmat[a2])
    feat = ~same
    profile = (f1 < 0) | (f2 < 0) | (np.abs(np.where(np.isfinite(z1), z1, 0) - np.where(np.isfinite(z2), z2, 0)) > 40)
    watched = np.array([w is not None for *_, w in keep])
    wm = watched[eobj[eid]]
    wc = M["wcrease"][eid]
    cls = np.where(wm, np.where(wc, np.where(vis, 3, 4), 0), np.where(vis & feat, np.where(profile, 2, 1), 0))
    A3, B3 = P[E[:, 0]], P[E[:, 1]]
    sband = band_of(A3[eid] + (B3[eid] - A3[eid]) * t[:, None])
    cls = np.where(cls > 0, cls * 10 + sband, 0)
    cls = close_gaps(cls, eid, k)
    segs = runs(cls, eid, k, t, ns, pa, pb, lambda c_, e: f"{c_ // 10}:{keep[eobj[e]][4] or ''}@{c_ % 10}")
    # room outlines per level, seen (5) and hidden (6)
    for lvl, lst in M["rooms"].items():
        if not lst:
            continue
        A3 = np.array([s[0] for s in lst]); B3 = np.array([s[1] for s in lst])
        qa = np.stack([(A3 @ X - c[0]) * PXCM + W / 2, (c[1] - A3 @ Y) * PXCM + H / 2, A3 @ Z], 1)
        qb = np.stack([(B3 @ X - c[0]) * PXCM + W / 2, (c[1] - B3 @ Y) * PXCM + H / 2, B3 @ Z], 1)
        L2, ns2, eid2, k2, t2, S2 = sample(qa, qb)
        jx = np.clip(S2[:, 0].astype(np.int64), 0, W - 1); jy = np.clip(S2[:, 1].astype(np.int64), 0, H - 1)
        v2 = S2[:, 2] >= zb[jy, jx] - 3.0
        cls2 = np.where(v2, 5, 6)
        segs.update(runs(cls2, eid2, k2, t2, ns2, qa, qb, lambda c_, e, lvl=lvl: f"{c_}:L{lvl}"))
    # anchors in this view (screen x, y; and whether seen)
    anc = {}
    for nm, p3 in list(M["centers"].items()) + [("asimov", ANCHORS["asimov"])]:
        p3 = np.array(p3)
        x_, y_ = (p3 @ X - c[0]) * PXCM + W / 2, (c[1] - p3 @ Y) * PXCM + H / 2
        anc[nm] = [round(float(x_), 1), round(float(y_), 1)]
    # rooms as boxes, seen through the walls: the outline of everything the box covers, its edges, its centre
    from PIL import Image, ImageDraw
    proj = lambda Q: np.stack([(Q @ X - c[0]) * PXCM + W / 2, (c[1] - Q @ Y) * PXCM + H / 2], -1)
    boxes = {}
    for rname, b in M["boxes"].items():
        lift = np.array([0.0, ROOM_H, 0.0])
        tri = b["tri"]
        polys = [proj(t) for t in tri] + [proj(t + lift) for t in tri]
        for a3, b3 in b["segs"]:
            polys.append(proj(np.array([a3, b3, b3 + lift, a3 + lift])))
        allp = np.vstack(polys)
        x0_, y0_ = np.floor(allp.min(0)).astype(int) - 4
        x1_, y1_ = np.ceil(allp.max(0)).astype(int) + 4
        img = Image.new("1", (int(x1_ - x0_), int(y1_ - y0_)), 0)
        dr = ImageDraw.Draw(img)
        for pg in polys:
            dr.polygon([(float(px_ - x0_), float(py_ - y0_)) for px_, py_ in pg], fill=1, outline=1)
        m = np.array(img, bool)
        loops = [[[round(x + x0_, 1), round(y + y0_, 1)] for x, y in lp] for lp in trace(m, min_area=20, tol=0.8)]
        edges = []
        for a3, b3 in b["segs"]:
            for off in (np.zeros(3), lift):
                pa_, pb_ = proj(np.array([a3 + off, b3 + off]))
                edges.append([round(float(pa_[0]), 1), round(float(pa_[1]), 1), round(float(pb_[0]), 1), round(float(pb_[1]), 1)])
        for v in b["corners"]:
            pa_, pb_ = proj(np.array([v, v + lift]))
            edges.append([round(float(pa_[0]), 1), round(float(pa_[1]), 1), round(float(pb_[0]), 1), round(float(pb_[1]), 1)])
        cen = np.array([(tri[:, :, 0].min() + tri[:, :, 0].max()) / 2, b["y0"] + ROOM_H / 2, (tri[:, :, 2].min() + tri[:, :, 2].max()) / 2])
        cx_, cy_ = proj(cen[None, :])[0]
        boxes[rname] = dict(lvl=b["lvl"], fill=loops, edges=edges, anchor=[round(float(cx_), 1), round(float(cy_), 1)])
    # openings: their rectangles on the wall, seen or hidden
    opens = {}
    for oname, o in OPENINGS.items():
        A, B = [], []
        for (ya, yb), (za, zb_) in o["rects"]:
            cs = [np.array([o["x"], ya, za]), np.array([o["x"], ya, zb_]), np.array([o["x"], yb, zb_]), np.array([o["x"], yb, za])]
            for i_ in range(4):
                A.append(cs[i_]); B.append(cs[(i_ + 1) % 4])
        A = np.array(A); B = np.array(B)
        qa = np.concatenate([proj(A), (A @ Z)[:, None]], 1); qb = np.concatenate([proj(B), (B @ Z)[:, None]], 1)
        L_, ns_, eid_, k_, t_, S_ = sample(qa, qb, step=0.5)
        jx_ = np.clip(S_[:, 0].astype(np.int64), 0, W - 1); jy_ = np.clip(S_[:, 1].astype(np.int64), 0, H - 1)
        seen_ = S_[:, 2] >= zb[jy_, jx_] - 4.0
        r_ = runs(np.where(seen_, 1, 2), eid_, k_, t_, ns_, qa, qb, lambda c_, e: "seen" if c_ == 1 else "hidden")
        cen_ = proj(np.array([[o["x"], sum(o["rects"][0][0]) / 2, sum(o["rects"][0][1]) / 2]]))[0]
        opens[oname] = dict(seen=r_.get("seen", []), hidden=r_.get("hidden", []), anchor=[round(float(cen_[0]), 1), round(float(cen_[1]), 1)])
    wanc = {}
    for w, p3 in M["wcent"].items():
        x_, y_ = proj(np.array(p3)[None, :])[0]
        wanc[w] = [round(float(x_), 1), round(float(y_), 1)]
    # the floor of the visible surface under every pixel, and each floor's outline as seen (plus the whole house's)
    valid = fid >= 0
    ii, jj = np.nonzero(valid)
    uu = (jj + 0.5 - W / 2) / PXCM + c[0]
    vv = c[1] - (ii + 0.5 - H / 2) / PXCM
    P3 = np.outer(uu, X) + np.outer(vv, Y) + np.outer(zb[ii, jj], Z)
    bimg = np.zeros((H, W), np.int8)
    bimg[ii, jj] = band_of(P3)
    contours = {str(b): trace(bimg == b) for b in (1, 2, 3)}
    contours["all"] = trace(valid, fill=True)
    # silhouette extent per floor band: leftmost / rightmost drawn pixel between the floor and the next
    occ = np.isfinite(zb)
    cols = np.where(occ.any(0))[0]; rows_ = np.where(occ.any(1))[0]
    bbox = [int(cols.min()), int(rows_.min()), int(cols.max()), int(rows_.max())]
    rows_ext = {}
    for yy in range(0, H, 10):
        r = np.where(occ[yy])[0]
        if len(r):
            rows_ext[yy] = [int(r.min()), int(r.max())]
    return dict(segs=segs, anchors=anc, bbox=bbox, rows=rows_ext, contours=contours, boxes=boxes, wanchors=wanc, openings=opens)


def main(glb, out):
    t0 = time.time()
    js, prims = load(glb)
    M = prepare(prims)
    P = M["P"]
    cx3 = (P.min(0) + P.max(0)) / 2
    W = H = int(math.ceil(np.linalg.norm(P.max(0) - P.min(0)) * PXCM)) + 40
    res = {"W": W, "H": H, "px_per_cm": PXCM, "views": []}
    for k in range(8):
        az = 45 + 45 * k
        v = view(M, az, W, H, cx3)
        v["az"] = az
        res["views"].append(v)
        print(f"view {k} az {az}: " + ", ".join(f"{kk} {len(vv)}" for kk, vv in sorted(v["segs"].items())), f"bbox {v['bbox']}  {time.time() - t0:.0f}s", flush=True)
    json.dump(res, open(out, "w"))




# ---- the house as two plain volumes (Consumption): no wall thickness, no openings --------------------------------
MASS = [((378.0, 0.0, 94.0), (1094.0, 1062.0, 727.0)),        # the tower
        ((1094.0, 0.0, 95.0), (1703.0, 737.0, 730.0))]        # the east block (garage, living room)


def box_prim(name, lo, hi):
    x0, y0, z0 = lo; x1, y1, z1 = hi
    p = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    f = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [3, 7, 6], [3, 6, 2], [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5]])
    return (name, name, p, f)


def massing(out, az=45):
    prims = [box_prim(f"mass_{i}", lo, hi) for i, (lo, hi) in enumerate(MASS)]
    M = prepare(prims)
    P = M["P"]
    cx3 = (P.min(0) + P.max(0)) / 2
    W = H = int(math.ceil(np.linalg.norm(P.max(0) - P.min(0)) * PXCM)) + 40
    v = view(M, az, W, H, cx3)
    json.dump({"W": W, "H": H, "segs": {k: s for k, s in v["segs"].items() if k[0] in "12"}, "bbox": v["bbox"], "all": v["contours"]["all"]}, open(out, "w"))
    print("massing", {k: len(s) for k, s in v["segs"].items()}, v["bbox"])


if __name__ == "__main__":
    if sys.argv[1] == "--massing":
        massing(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
