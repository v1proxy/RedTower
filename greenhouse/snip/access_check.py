"""Can every part inside the Herb Snip go in from outside, and can every tool reach its screw?
Each part is moved along the way the booklet puts it in, against everything already fitted at
that step (signed distances from the models in snip_cad.py), and each tool is a cylinder along
its axis. Reports the tightest gap on the way in (the last 0.5 mm, where a part meets its seat,
is reported apart) and where it is.

    python access_check.py      -> build/access.json
"""
from __future__ import annotations
import json, math, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gantry"))
import sdf as S
import snip_cad as C
import assembly as AS
import collide as CL

STEP = 0.3                   # surface sampling, mm


def surf(meshes):
    return np.vstack([CL._surface_points(V, F, STEP) for V, F in meshes])


def placed(g, R, t):
    return S.transform(g, R, t)


def in_plane(ang, at):
    c, s = math.cos(ang), math.sin(ang)
    return np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]]), np.array([at[0], 0.0, at[1]])


def path(points, fixed, offsets, seat=0.5):
    """Tightest gap along the way, and at the seat (the last `seat` mm of travel)."""
    total = np.cumsum([0.0] + [float(np.linalg.norm(np.subtract(b, a))) for a, b in zip(offsets, offsets[1:])])
    best_way, best_seat = (1e9, None), (1e9, None)
    for d, s_ in zip(offsets, total):
        Q = points + np.asarray(d)
        dist = fixed(Q)
        i = int(np.argmin(dist)); v = float(dist[i])
        if total[-1] - s_ > seat:
            if v < best_way[0]:
                best_way = (v, [round(float(x), 1) for x in Q[i]])
        elif v < best_seat[0]:
            best_seat = (v, [round(float(x), 1) for x in Q[i]])
    return dict(way_min_mm=round(best_way[0], 2), way_at=best_way[1],
                seat_min_mm=round(best_seat[0], 2), seat_at=best_seat[1])


def rod(a, b, r, n_ring=16, step=0.5):
    """Points on the surface of a cylinder from a to b, radius r (a tool's shaft)."""
    a = np.asarray(a, float); b = np.asarray(b, float); ax = b - a; L = np.linalg.norm(ax); ax /= L
    u = np.cross(ax, [1, 0, 0] if abs(ax[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); v = np.cross(ax, u)
    th = np.linspace(0, 2 * math.pi, n_ring, endpoint=False)
    s = np.arange(0, L + 1e-9, step)
    P = a + s[:, None, None] * ax + r * (np.cos(th)[None, :, None] * u + np.sin(th)[None, :, None] * v)
    return P.reshape(-1, 3)


def clear(points, fixed):
    d = fixed(points); i = int(np.argmin(d))
    return dict(min_gap_mm=round(float(d[i]), 2), at=[round(float(x), 1) for x in points[i]])


def main():
    t0 = time.time()
    body = C.body()
    anvil, pad = C.anvil(), C.tpu_pad()
    R0, t0_ = C.jaw3(0.0); R30, t30 = C.jaw3(math.radians(30.0))
    jaws0 = S.union(placed(C.mj_half_a(), R0, t0_), placed(C.mj_half_b(), R0, t0_))
    jaws30 = S.union(placed(C.mj_half_a(), R30, t30), placed(C.mj_half_b(), R30, t30))
    closed = {n: m for n, m, _ in AS.parts(0.0, cots=True)}
    opened = {n: m for n, m, _ in AS.parts(30.0, cots=True)}
    phi, th, T, Cp = AS.state(0.0)
    Rl, tl = in_plane(math.atan2(Cp[1] - T[1], Cp[0] - T[0]), T)
    link = placed(C.link(), Rl, tl)
    out = {}

    # step 4: the pads, the anvil, the pivot's insert, into the bare body
    out["pad_into_rib_from_+y"] = path(surf([closed["pad_fj"]]), body, [(0, s, 0) for s in np.arange(14.0, -1e-9, -0.5)])
    out["anvil_into_pocket_from_+x"] = path(surf([closed["anvil"]]), body, [(s, 0, 0) for s in np.arange(10.0, -1e-9, -0.5)])
    fix4 = S.union(body, anvil, pad)
    py = C.JAW[0]
    # an iron under 8 thick for its first 50: the insert tip, then the iron's shaft
    out["iron_onto_pivot_insert_from_+y"] = clear(np.vstack([rod((C.P[0], py, C.P[1]), (C.P[0], 22.0, C.P[1]), 2.6),
                                                             rod((C.P[0], 22.0, C.P[1]), (C.P[0], 47.0, C.P[1]), 3.9)]), fix4)

    # step 5: the jaw, then the pivot screw, then the link
    import checks as CK
    opened = {n: m for n, m, _ in AS.parts(CK.JAW_IN[0], cots=True)}
    dx = CK.JAW_IN[1]
    jaw = ("mj_a", "mj_b", "blade", "pad_mj", "clamp", "insert_clamp")
    out["jaw_down_then_across"] = path(surf([opened[n] for n in jaw]), fix4,
                                       [(dx, 0, s) for s in np.arange(50.0, -1e-9, -0.5)] +
                                       [(s, 0, 0) for s in np.arange(dx, -1e-9, -0.25)])
    head_face = C.JAW[1]
    for nm, jw in (("closed", jaws0), ("open_30", jaws30)):
        f = S.union(fix4, jw)
        # a 2 mm key: the short leg along the pivot axis out of jaw B's counterbore, the long leg up
        key = np.vstack([rod((C.P[0], head_face + 0.05, C.P[1]), (C.P[0], 21.0, C.P[1]), 1.2),
                         rod((C.P[0], 21.0, C.P[1]), (C.P[0], 21.0, C.P[1] + 90.0), 1.2)])
        out[f"pivot_key_jaw_{nm}"] = clear(key, f)
    fix5 = S.union(fix4, jaws0)
    out["link_down_then_across"] = path(surf([closed[n] for n in ("link", "dowel_tail")]), fix5,
                                        [(0, CK.LINK_IN, s) for s in np.arange(45.0, -1e-9, -0.5)] +
                                        [(0, s, 0) for s in np.arange(CK.LINK_IN, -1e-9, -0.25)])

    # step 7: the servo with its horn, crank and dowel, in from the back; the crank's dowel slips
    # into the link along the same axis. Then its two tab screws from the back.
    fix7 = S.union(fix5, link)
    servo = ("servo", "horn", "crank", "crank_screw", "dowel_crank")
    out["servo_from_back"] = path(surf([closed[n] for n in servo]), fix7,
                                  [(0, s, 0) for s in np.arange(32.0, -1e-9, -0.5)])
    sv = closed["servo"][0]
    zc = (C.SERVO_Z[0] + C.SERVO_Z[1]) / 2
    for dz in (-C.TAB_HOLE / 2, C.TAB_HOLE / 2):
        a = (C.SV[0], C.TAB[1] + 1.6, zc + dz)
        out[f"tab_screwdriver_z{zc + dz:.1f}"] = clear(rod(a, (C.SV[0], 80.0, zc + dz), 2.4),
                                                      S.union(body, S.box((C.SERVO_X[0], C.TAB[1], C.SERVO_Z[0]),
                                                                          (C.SERVO_X[1], sv[:, 1].max(), C.SERVO_Z[1]))))

    # step 8: the regulator into its bay through the +x face, past the servo
    case = S.box((C.SERVO_X[0], C.TAB[1], C.SERVO_Z[0]), (C.SERVO_X[1], sv[:, 1].max(), C.SERVO_Z[1]))
    out["regulator_into_bay_from_+x"] = path(surf([closed["regulator"]]), S.union(body, case),
                                             [(s, 0, 0) for s in np.arange(14.0, -1e-9, -0.5)])
    out["seconds"] = round(time.time() - t0)
    json.dump(out, open(os.path.join(AS.BUILD, "access.json"), "w"), indent=1)
    for k, v in out.items():
        print(k, v, flush=True)


if __name__ == "__main__":
    main()
