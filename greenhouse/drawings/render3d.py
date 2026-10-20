"""A small z-buffer renderer for axis-aligned boxes in isometric projection.

A painter's-algorithm sort by face centroid gets long members wrong: a 1317 mm rail
sorts as if it sat at mid-span, so it draws over an upright that is actually in front
of its far end. Per-pixel depth removes the whole class of error and gives hidden-line
removal for free.

    screen x = (x - y) cos30
    screen y = (x + y) sin30 + z
    depth    = x + y + z          (larger is nearer the viewer)

Faces are axis-aligned, so the inverse of the projection within a face's plane is
closed form, which is what makes the depth cheap to evaluate per pixel.
"""
import math
import numpy as np

C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))
YREF = 559.0           # mirror depth: the viewer stands in front of the cabinet


def proj(x, y, z):
    return ((x - y) * C30, (x + y) * S30 + z)


class Scene:
    def __init__(self):
        self.faces = []      # (kind, const, quad3d, rgb)

    def face(self, pts, rgb, mirrored=False):
        """One planar convex polygon. Kept only if it faces the viewer at (1,1,1)."""
        q = pts if mirrored else [(x, YREF - y, z) for x, y, z in pts]
        a = [q[1][i] - q[0][i] for i in range(3)]
        b = [q[2][i] - q[0][i] for i in range(3)]
        n = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
        if n[0] + n[1] + n[2] < 0:
            n = (-n[0], -n[1], -n[2])
            q = q[::-1]
        if abs(n[0] + n[1] + n[2]) < 1e-9:
            return self                                  # edge-on, invisible
        c = sum(n[i] * q[0][i] for i in range(3))
        self.faces.append((n, c, q, rgb))
        return self

    def box(self, x0, x1, y0, y1, z0, z1, pal):
        y0, y1 = YREF - y1, YREF - y0          # mirror so we see the front
        self.face([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], pal[0], True)
        self.face([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], pal[1], True)
        self.face([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], pal[2], True)
        return self


def _hex(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i+2], 16) for i in (0, 2, 4)], dtype=np.float64)


def render(scene, width=1500, ss=2, bg="#FBFCFA", edge="#1B2629", pad=0.02):
    pts = [proj(*p) for _, _, q, _ in scene.faces for p in q]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mx, my = (x1 - x0) * pad, (y1 - y0) * pad
    x0, x1, y0, y1 = x0 - mx, x1 + mx, y0 - my, y1 + my
    W = width * ss
    scale = W / (x1 - x0)
    H = int(round((y1 - y0) * scale))
    H += (-H) % ss          # keep H divisible by the supersample factor

    depth = np.full((H, W), -np.inf)
    fid = np.full((H, W), -1, dtype=np.int32)
    col = np.zeros((H, W, 3))
    col[:] = _hex(bg)

    # pixel centres in screen coords; row 0 is the TOP of the image, so y descends
    px = x0 + (np.arange(W) + 0.5) / scale
    py = y1 - (np.arange(H) + 0.5) / scale

    for i, (nrm, cst, quad, rgb) in enumerate(scene.faces):
        q = np.array([proj(*p) for p in quad])
        bx0 = max(0, int((q[:, 0].min() - x0) * scale) - 1)
        bx1 = min(W, int((q[:, 0].max() - x0) * scale) + 2)
        by0 = max(0, int((y1 - q[:, 1].max()) * scale) - 1)
        by1 = min(H, int((y1 - q[:, 1].min()) * scale) + 2)
        if bx1 <= bx0 or by1 <= by0:
            continue
        gx, gy = np.meshgrid(px[bx0:bx1], py[by0:by1])

        m = len(q)
        inside = np.ones(gx.shape, dtype=bool)
        sign = 0.0
        for k in range(m):
            ax, ay = q[k]
            bx, by = q[(k + 1) % m]
            cr = (bx - ax) * (gy - ay) - (by - ay) * (gx - ax)
            if sign == 0.0:
                t = (bx - ax) * (q[(k + 2) % m][1] - ay) - (by - ay) * (q[(k + 2) % m][0] - ax)
                sign = 1.0 if t >= 0 else -1.0
            inside &= (cr * sign) >= -1e-9
        if not inside.any():
            continue

        # invert the projection inside this face's plane:
        #   x - y = sx / cos30,   z = sy - (x + y) sin30,   n . X = c
        nx, ny, nz = nrm
        u = gx / C30
        den = (nx + ny) / 2.0 - nz * S30
        if abs(den) < 1e-12:
            continue
        ssum = (cst - u * (nx - ny) / 2.0 - nz * gy) / den
        d = ssum * (1.0 - S30) + gy

        sub = depth[by0:by1, bx0:bx1]
        win = inside & (d > sub)
        if not win.any():
            continue
        sub[win] = d[win]
        fid[by0:by1, bx0:bx1][win] = i
        col[by0:by1, bx0:bx1][win] = _hex(rgb)

    # edges wherever the visible face changes, which is also the silhouette
    e = np.zeros((H, W), dtype=bool)
    e[:, 1:] |= fid[:, 1:] != fid[:, :-1]
    e[1:, :] |= fid[1:, :] != fid[:-1, :]
    col[e] = _hex(edge)

    img = col.reshape(H // ss, ss, W // ss, ss, 3).mean(axis=(1, 3))

    def to_px(x, y, z):
        """Model point -> pixel coordinates in the returned image, for leader lines."""
        sx, sy = proj(x, YREF - y, z)
        return ((sx - x0) * scale / ss - 0.5, (y1 - sy) * scale / ss - 0.5)

    return np.clip(img / 255.0, 0, 1), to_px


# --------------------------------------------------------------------------
# True 40-series T-slot section.
#
# 80/20's own STEP for 40-4040 sits behind a PartCommunity login that this
# sandbox cannot reach, so the section is built from the published slot-8
# figures: 8 mm slot opening, 12 mm slot depth, 40 mm square. What the drawing
# needs from it is the thing a plain box was hiding: the top face is NOT a flat
# 40 mm land. It is two 16 mm lands with an 8 mm groove between them, and that
# groove is where the T-nut goes.
#
# The section is decomposed into axis-aligned rectangles so it extrudes into
# ordinary boxes and the z-buffer handles the rest. Internal ribs, the core
# bore and the corner radii are left out: none of them is visible at assembly
# scale, and none of them changes where a fastener lands.

SLOT_OPEN, SLOT_DEPTH, SER = 8.0, 12.0, 40.0
_a = (SER - SLOT_OPEN) / 2.0          # 16.0 land either side of a slot
_b = SER - SLOT_DEPTH                 # 28.0
SECTION = [
    (0, _a, 0, SLOT_DEPTH), (SER - _a, SER, 0, SLOT_DEPTH),
    (0, SER, SLOT_DEPTH, _a),
    (_a - 4, SER - _a + 4, _a, SER - _a),
    (0, SER, SER - _a, _b),
    (0, _a, _b, SER), (SER - _a, SER, _b, SER),
]


def tslot(sc, axis, a0, a1, p, q, pal):
    """A 40-4040 run from a0 to a1 along `axis`; p,q locate the section corner."""
    for u0, u1, v0, v1 in SECTION:
        if axis == "x":
            sc.box(a0, a1, p + u0, p + u1, q + v0, q + v1, pal)
        elif axis == "y":
            sc.box(p + u0, p + u1, a0, a1, q + v0, q + v1, pal)
        else:
            sc.box(p + u0, p + u1, q + v0, q + v1, a0, a1, pal)
    return sc
