#!/usr/bin/env python3
"""A small sheet-metal unfolder: floor polygon in, flat pattern out.

Rev 3 has four parts with chamfered corners, two of them with two chamfers each, and
hand-tracing outlines was where the mistakes were going to come from. So the outline is
generated: give it the floor polygon and say which edges get a 25 mm lip, and it emits
the flange strips, the bend lines and the relief at every corner where two lips meet.

Relief rule, the same one SendCutSend already accepted on Rev 1 and Rev 2: both cut
edges overrun the bend intersection into the floor and are joined by an arc of radius R,
so the root is radiused rather than knife sharp. Generalised here to corners that are
not 90 degrees, which is what the 45 degree chamfers need.
"""
import math

T, BD, LIP, R = 1.6002, 2.438, 25.0, 2.0
MITRE_GAP = 2.5          # > material thickness, so the laser has room
F = LIP - BD                     # 22.562 flat flange allowance
HOLE_W, HOLE_L = 9.0, 18.0
MAXFLAT, MAXBEND = (30.0 * 25.4, 44.0 * 25.4), 44.0 * 25.4


def unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


def add(p, v, s=1.0):
    return (p[0] + v[0] * s, p[1] + v[1] * s)


class Dxf:
    def __init__(self):
        self.e = []

    def line(self, p, q, dashed=False):
        self.e.append(("LINE", p, q, dashed))

    def arc(self, c, r, a0, a1):
        self.e.append(("ARC", c, r, a0, a1))

    def circle(self, c, r):
        self.e.append(("CIRCLE", c, r))

    def slot(self, a, b, w):
        th = math.atan2(b[1] - a[1], b[0] - a[0])
        r = w / 2.0
        px, py = -math.sin(th) * r, math.cos(th) * r
        self.line((a[0] + px, a[1] + py), (b[0] + px, b[1] + py))
        self.line((b[0] - px, b[1] - py), (a[0] - px, a[1] - py))
        d = math.degrees(th)
        self.arc(b, r, d - 90.0, d + 90.0)
        self.arc(a, r, d + 90.0, d + 270.0)

    def hole(self, cx, cy, along):
        h = (HOLE_L - HOLE_W) / 2.0
        if along == "x":
            self.slot((cx - h, cy), (cx + h, cy), HOLE_W)
        else:
            self.slot((cx, cy - h), (cx, cy + h), HOLE_W)

    def dumps(self):
        o = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4",
             "9", "$MEASUREMENT", "70", "1", "0", "ENDSEC",
             "0", "SECTION", "2", "TABLES",
             "0", "TABLE", "2", "LTYPE", "70", "2",
             "0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line",
             "72", "65", "73", "0", "40", "0.0",
             "0", "LTYPE", "2", "DASHED", "70", "0", "3", "Dashed",
             "72", "65", "73", "2", "40", "9.0", "49", "6.0", "49", "-3.0",
             "0", "ENDTAB", "0", "TABLE", "2", "LAYER", "70", "1",
             "0", "LAYER", "2", "0", "70", "0", "62", "7", "6", "CONTINUOUS",
             "0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        for ent in self.e:
            if ent[0] == "LINE":
                _, p, q, dashed = ent
                o += ["0", "LINE", "8", "0", "6", "DASHED" if dashed else "CONTINUOUS",
                      "10", f"{p[0]:.4f}", "20", f"{p[1]:.4f}", "30", "0.0",
                      "11", f"{q[0]:.4f}", "21", f"{q[1]:.4f}", "31", "0.0"]
            elif ent[0] == "ARC":
                _, c, r, a0, a1 = ent
                o += ["0", "ARC", "8", "0", "6", "CONTINUOUS",
                      "10", f"{c[0]:.4f}", "20", f"{c[1]:.4f}", "30", "0.0",
                      "40", f"{r:.4f}", "50", f"{a0:.4f}", "51", f"{a1:.4f}"]
            else:
                _, c, r = ent
                o += ["0", "CIRCLE", "8", "0", "6", "CONTINUOUS",
                      "10", f"{c[0]:.4f}", "20", f"{c[1]:.4f}", "30", "0.0",
                      "40", f"{r:.4f}"]
        o += ["0", "ENDSEC", "0", "EOF"]
        return "\n".join(o) + "\n"


def relief(P, a, b, r=R):
    """Arc joining two cut edges that leave P along unit directions a and b."""
    v = unit((a[0] + b[0], a[1] + b[1]))
    half = math.acos(max(-1.0, min(1.0, a[0] * v[0] + a[1] * v[1])))
    C = add(P, v, -r / math.sin(half))
    da = (C[0] - P[0]) * a[0] + (C[1] - P[1]) * a[1]
    db = (C[0] - P[0]) * b[0] + (C[1] - P[1]) * b[1]
    ta, tb = add(P, a, da), add(P, b, db)
    aa = math.degrees(math.atan2(ta[1] - C[1], ta[0] - C[0])) % 360
    ab = math.degrees(math.atan2(tb[1] - C[1], tb[0] - C[0])) % 360
    lo, hi = (aa, ab) if (ab - aa) % 360 <= 180 else (ab, aa)
    return ta, tb, (C, r, lo, hi)


def mitre(V, n0, n1, g=MITRE_GAP):
    """Two lips meeting at a re-entrant corner overlap in the flat pattern.

    A 90 degree inside corner is the one case where flange strips collide, so each is
    cut back to a 45 degree mitre with a gap between them. After forming, the two
    upstands close on that mitre and the joint gets the same silicone bead as every
    other corner.
    """
    bis = unit((n0[0] + n1[0], n0[1] + n1[1]))
    perp = (-bis[1], bis[0])
    out = []
    for n in (n0, n1):
        pk = perp if (perp[0] * n[0] + perp[1] * n[1]) > 0 else (-perp[0], -perp[1])
        off = (g / 2.0) * (pk[0] * n[0] + pk[1] * n[1])
        bn = bis[0] * n[0] + bis[1] * n[1]
        base = add(V, pk, g / 2.0)
        inner = add(base, bis, -off / bn)
        outer = add(base, bis, (F - off) / bn)
        out.append((inner, outer))
    return out


def unfold(poly, flanged, holes=(), drain=None, trim=5.0):
    """poly: floor vertices, counter-clockwise. flanged[i]: does edge i get a lip?"""
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] -
               poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    assert area > 0, "floor polygon must be counter-clockwise"
    n = len(poly)
    d = [unit((poly[(i + 1) % n][0] - poly[i][0], poly[(i + 1) % n][1] - poly[i][1]))
         for i in range(n)]
    nrm = [(d[i][1], -d[i][0]) for i in range(n)]        # outward, to the right of travel

    g = Dxf()
    path = []       # (kind, data) walked in order
    mit = {}        # vertex index -> (mitre inner point of prev lip, of next lip)
    for i in range(n):
        P, Q = poly[i], poly[(i + 1) % n]
        prev, nxt = (i - 1) % n, (i + 1) % n
        if flanged[i]:
            start = add(P, nrm[i], F)
            end = add(Q, nrm[i], F)
            cross = d[prev][0] * d[i][1] - d[prev][1] * d[i][0]
            if flanged[prev] and cross < -1e-9:
                # re-entrant corner: mitre the two lips apart
                (in0, out0), (in1, out1) = mitre(P, nrm[prev], nrm[i])
                mit[i] = (in0, in1)
                ta, tb, arc = relief(P, unit((in0[0] - P[0], in0[1] - P[1])),
                                     unit((in1[0] - P[0], in1[1] - P[1])))
                path.append(("L", out0, in0))
                path.append(("L", in0, ta))
                path.append(("A", arc))
                path.append(("L", tb, in1))
                path.append(("L", in1, out1))
                start = out1
            elif flanged[prev]:
                ta, tb, arc = relief(P, nrm[prev], nrm[i])
                path.append(("L", add(P, nrm[prev], F), ta))
                path.append(("A", arc))
                path.append(("L", tb, start))
            else:
                path.append(("L", P, start))
            crossn = d[i][0] * d[nxt][1] - d[i][1] * d[nxt][0]
            if flanged[nxt] and crossn < -1e-9:
                (jn0, jout0), _ = mitre(Q, nrm[i], nrm[nxt])
                end = jout0
            path.append(("L", start, end))
            if not flanged[nxt]:
                path.append(("L", end, Q))
        else:
            a = P if flanged[prev] else P
            path.append(("L", a, Q))
            # a plain edge that follows a flange already got its tie-in above
            if flanged[prev]:
                path[-1] = ("L", P, Q)

    for kind, *rest in path:
        if kind == "L":
            p, q = rest
            if math.dist(p, q) > 1e-9:
                g.line(p, q)
        else:
            C, r, a0, a1 = rest[0]
            g.arc(C, r, a0, a1)

    bends = []
    for i in range(n):
        if not flanged[i]:
            continue
        P, Q = poly[i], poly[(i + 1) % n]
        prev, nxt = (i - 1) % n, (i + 1) % n
        crossp = d[prev][0] * d[i][1] - d[prev][1] * d[i][0]
        crossn = d[i][0] * d[nxt][1] - d[i][1] * d[nxt][0]
        if flanged[prev] and crossp < -1e-9:
            (_, _), (i1, _) = mitre(P, nrm[prev], nrm[i])
            p = add(i1, d[i], trim)
        else:
            p = add(P, d[i], trim if flanged[prev] else R)
        if flanged[nxt] and crossn < -1e-9:
            (i0, _), _ = mitre(Q, nrm[i], nrm[nxt])
            q = add(i0, d[i], -trim)
        else:
            q = add(Q, d[i], -(trim if flanged[nxt] else R))
        g.line(p, q, dashed=True)
        bends.append(math.dist(p, q))

    if drain:
        g.circle(drain, 3.0)
    for cx, cy, al in holes:
        g.hole(cx, cy, al)

    xs = [v[0] for v in poly] + [add(poly[i], nrm[i], F)[0] for i in range(n) if flanged[i]] \
        + [add(poly[(i + 1) % n], nrm[i], F)[0] for i in range(n) if flanged[i]]
    ys = [v[1] for v in poly] + [add(poly[i], nrm[i], F)[1] for i in range(n) if flanged[i]] \
        + [add(poly[(i + 1) % n], nrm[i], F)[1] for i in range(n) if flanged[i]]
    return g, (min(xs), max(xs), min(ys), max(ys)), bends
