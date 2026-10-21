"""Fasteners drawn the way they are made: ISO head dimensions, a real hex
socket you can see into, a helical thread when the drawing is close enough to
show it, chamfered nuts with their bores, the nylon ring in a nyloc.

Conventions, the same as cabinet.py's:
    button_head, cap_screw   bearing face on z = 0, head up, shank down to -L
    flat_head                the top of the head on z = 0, countersink below,
                             L measured from the top (as ISO 10642 is)
    grub                     z 0 .. L, the socket at the top
    nut, nyloc, washer       bottom face on z = 0
Every builder returns one (V, F) mesh; nyloc_parts returns (mesh, colour)
pairs so the nylon ring can be drawn white.

`detail=True` sweeps a helical thread along the shank (about ten thousand
triangles a screw): for a fasteners page. Leave it off in assembly scenes.
"""
import math

import numpy as np

from kit3d import extrude, merge, mv, circle_pts, cylinder, revolve

# ISO 7380-1 button head: dk, k, s (hex across flats), t (socket depth)
BUTTON = {3: (5.7, 1.65, 2.0, 1.04), 4: (7.6, 2.2, 2.5, 1.3), 5: (9.5, 2.75, 3.0, 1.56),
          6: (10.5, 3.3, 4.0, 2.08), 8: (14.0, 4.4, 5.0, 2.6)}
# ISO 4762 socket head cap: dk, k, s, t
CAP = {3: (5.5, 3.0, 2.5, 1.3), 4: (7.0, 4.0, 3.0, 2.0), 5: (8.5, 5.0, 4.0, 2.5),
       6: (10.0, 6.0, 5.0, 3.0), 8: (13.0, 8.0, 6.0, 4.0)}
# ISO 10642 countersunk: dk (theoretical), k, s, t
FLAT = {3: (6.72, 1.86, 2.0, 1.1), 4: (8.96, 2.48, 2.5, 1.5), 5: (11.2, 3.1, 3.0, 1.9),
        6: (13.44, 3.72, 4.0, 2.2), 8: (17.92, 4.96, 5.0, 3.0)}
PITCH = {3: 0.5, 4: 0.7, 5: 0.8, 6: 1.0, 8: 1.25}
NUT = {3: (5.5, 2.4), 4: (7.0, 3.2), 5: (8.0, 4.7), 6: (10.0, 5.2), 8: (13.0, 6.8)}     # ISO 4032: s, m
NYLOC = {3: (5.5, 4.0), 4: (7.0, 5.0), 5: (8.0, 5.0), 6: (10.0, 6.0), 8: (13.0, 8.0)}  # DIN 985: s, h
GRUB_S = {3: 1.5, 4: 2.0, 5: 2.5, 6: 3.0, 8: 4.0}
NYLON = np.array([0.95, 0.95, 0.92])


def _hex(s, cx=0.0, cy=0.0):
    """Hexagon, across flats s."""
    return circle_pts(s / math.sqrt(3), 6, cx, cy, start=math.pi / 6)


def _socket(s, t, z_top, rf):
    """A hex socket in a flat top of radius rf at z_top: the top ring with
    the hex cut through it (its hole walls are the socket's walls) and the
    socket's floor, with a shallow drill point."""
    ring = extrude(circle_pts(rf, 48), t + 0.3, z0=z_top - t - 0.3, holes=[_hex(s)])
    floor_ = extrude(_hex(s * 0.999), 0.2, z0=z_top - t - 0.2)
    R = s / math.sqrt(3)
    cone = cylinder(R * 0.95, 0.35, n=6, c=(0, 0, z_top - t - 0.2), r2=0.05)
    return merge(ring, floor_, cone)


def _shank(M, z_top, z_bot, detail, chamfer=True, chamfer_top=False):
    """Plain or threaded shank from z_top down to z_bot (z_bot < z_top)."""
    L = z_top - z_bot
    r = M / 2
    if not detail:
        if chamfer:
            body = cylinder(r, L - 0.4 * PITCH.get(int(M), 0.8), c=(0, 0, z_bot + 0.4 * PITCH.get(int(M), 0.8)), n=40)
            tip = cylinder(r * 0.82, 0.4 * PITCH.get(int(M), 0.8), c=(0, 0, z_bot), r2=r, n=40)
            return merge(body, tip)
        return cylinder(r, L, c=(0, 0, z_bot), n=40)
    P = PITCH.get(int(M), M * 0.15)
    depth = 0.54 * P
    n = 36
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    steps = 10
    zs = np.arange(z_bot, z_top + 1e-9, P / steps)
    if zs[-1] < z_top - 1e-6:
        zs = np.append(zs, z_top)
    rings = []
    for z in zs:
        ph = ((z - z_bot) / P - th / (2 * math.pi)) % 1.0
        rr = r - depth * np.abs(2 * ph - 1.0)
        cham = min(1.0, (z - z_bot) / (0.6 * P) * 0.25 + 0.75) if z - z_bot < 0.6 * P else 1.0
        rr = np.minimum(rr, r * cham)
        if chamfer_top and z_top - z < 0.6 * P:
            rr = np.minimum(rr, r * (0.75 + 0.25 * (z_top - z) / (0.6 * P)))
        rings.append(np.c_[rr * np.cos(th), rr * np.sin(th), np.full(n, z)])
    V = np.vstack(rings)
    F = []
    for k in range(len(rings) - 1):
        a0, b0 = k * n, (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            F += [[a0 + i, a0 + j, b0 + j], [a0 + i, b0 + j, b0 + i]]
    cb, ct = len(V), len(V) + 1
    V = np.vstack([V, [[0, 0, zs[0]], [0, 0, zs[-1]]]])
    top0 = (len(rings) - 1) * n
    for i in range(n):
        j = (i + 1) % n
        F += [[cb, j, i], [ct, top0 + i, top0 + j]]
    return (V, np.array(F, int))


def button_head(M=8, L=16.0, detail=False):
    """ISO 7380-1, bearing face on z = 0, head up, shank down to -L."""
    dk, k, s, t = BUTTON.get(int(M), (M * 1.75, M * 0.55, M * 0.6, M * 0.31))
    rf = max(s / math.sqrt(3) + 0.35, 0.36 * dk)
    prof = [(rf, k), (dk * 0.40, k * 0.93), (dk * 0.46, k * 0.72), (dk * 0.495, k * 0.42), (dk / 2, k * 0.18),
            (dk / 2, 0.0), (0.0, 0.0)]
    head = revolve(prof, n=48)
    return merge(head, _socket(s, t, k, rf), _shank(M, 0.0, -L, detail))


def cap_screw(M=8, L=16.0, detail=False):
    """ISO 4762, bearing face on z = 0, head up, shank down to -L. The head's
    side is knurled as the real one is."""
    dk, k, s, t = CAP.get(int(M), (M * 1.5, M * 1.0, M * 0.75, M * 0.5))
    c = 0.06 * dk
    rf = dk / 2 - c
    n = 96
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rr = dk / 2 - 0.12 * (np.cos(a * 32) > 0)
    knurl = extrude(np.c_[rr * np.cos(a), rr * np.sin(a)], k - c - 0.3, z0=0.3)
    prof = [(rf, k), (dk / 2, k - c), (dk / 2 - 0.12, k - c - 0.01), (dk / 2 - 0.12, 0.3), (dk / 2 - 0.3, 0.0),
            (0.0, 0.0)]
    head = revolve(prof, n=48)
    return merge(head, knurl, _socket(s, t, k, rf), _shank(M, 0.0, -L, detail))


def flat_head(M=3, L=12.0, detail=False):
    """ISO 10642 countersunk, 90 degrees: the head's top on z = 0, the cone
    below it, the shank on down to -L."""
    dk, k, s, t = FLAT.get(int(M), (M * 2.2, M * 0.62, M * 0.6, M * 0.37))
    prof = [(dk / 2, 0.0), (dk / 2, -0.25), (M / 2, -k), (0.0, -k)]
    head = revolve(prof, n=48)
    return merge(head, _socket(s, t, 0.0, dk / 2), _shank(M, -k, -L, detail))


def grub(M=6, L=8.0, detail=False):
    """ISO 4026 flat point set screw, z 0 .. L, the socket at the top."""
    s = GRUB_S.get(int(M), M * 0.5)
    t = min(L * 0.5, s * 1.1)
    body = _shank(M, L - 0.3, 0.0, detail, chamfer_top=True)
    top = cylinder(M / 2 * 0.78, 0.3, c=(0, 0, L - 0.3), r2=M / 2 * 0.74, n=48)
    return merge(body, top, _socket(s, t, L, M / 2 * 0.74))


def _hex_nut_body(s, m, bore, cham=True):
    """A hex prism with its 30 degree chamfers drawn as a turned edge both
    faces, and the bore."""
    body = extrude(_hex(s), m - 0.4, z0=0.2, holes=[circle_pts(bore, 40)])
    rc = s / 2 * 0.95
    rim_b = extrude(circle_pts(rc, 48), 0.2, z0=0.0, holes=[circle_pts(bore, 40)])
    rim_t = extrude(circle_pts(rc, 48), 0.2, z0=m - 0.2, holes=[circle_pts(bore, 40)])
    return merge(body, rim_b, rim_t)


def nut(M=5):
    s, m = NUT.get(int(M), (M * 1.6, M * 0.8))
    return _hex_nut_body(s, m, M / 2 * 0.84)


def nyloc_parts(M=4):
    """DIN 985: the hex, the crimped collar and the nylon ring, bottom on z = 0."""
    s, h = NYLOC.get(int(M), (M * 1.6, M * 1.25))
    m = h * 0.62
    steel = _hex_nut_body(s, m, M / 2 * 0.84)
    collar = extrude(circle_pts(s * 0.47, 48), h - m - 0.3, z0=m, holes=[circle_pts(M / 2 * 1.05, 40)])
    lip = revolve([(M / 2 * 1.05, h - 0.3), (s * 0.47, h - 0.3), (s * 0.42, h), (M / 2 * 1.35, h),
                   (M / 2 * 1.35, h - 0.3)], n=48)
    ring = extrude(circle_pts(M / 2 * 1.32, 40), 0.25, z0=h - 0.55, holes=[circle_pts(M / 2 * 0.86, 40)])
    from kit3d import STEEL
    return [(merge(steel, collar, lip), STEEL), (ring, NYLON)]


def nyloc(M=4):
    return merge(*[m for m, _ in nyloc_parts(M)])


def washer(d_in, d_out, t):
    """Flat washer, its outer edge broken."""
    return merge(extrude(circle_pts(d_out / 2, 64), t, holes=[circle_pts(d_in / 2, 48)]))


def hammer_tnut(M=5, slot=8):
    """Drop-in hammer-head T-nut for slot 8, in its own frame: the wings' top
    face on z = 0 (against the slot's lips), the wings below, the locating rib
    above (up in the slot's mouth). Two opposite corners are rounded: that is
    what lets it turn into the slot as the screw tightens."""
    wl, ww, wt = 16.0, 11.0, 3.6
    r = ww / 2 - 0.2
    pts = [(-wl / 2, -ww / 2), (wl / 2 - r, -ww / 2)]
    for k in range(1, 9):
        a = -math.pi / 2 + k * math.pi / 2 / 8
        pts.append((wl / 2 - r + r * math.cos(a), -ww / 2 + r + r * math.sin(a)))
    pts += [(wl / 2, ww / 2), (-wl / 2 + r, ww / 2)]
    for k in range(1, 9):
        a = math.pi / 2 + k * math.pi / 2 / 8
        pts.append((-wl / 2 + r + r * math.cos(a), ww / 2 - r + r * math.sin(a)))
    bore = M / 2 * 0.84
    wings = extrude(np.array(pts), wt, z0=-wt, holes=[circle_pts(bore, 40)])
    rib = extrude(np.array([(-wl / 2 + 2, -3.6), (wl / 2 - 2, -3.6), (wl / 2 - 2, 3.6), (-wl / 2 + 2, 3.6)]),
                  1.8, z0=0.0, holes=[circle_pts(bore, 40)])
    return merge(wings, rib)
