"""Every number the Herb Snip booklet quotes, recomputed from the model.

    python checks.py            # writes build/checks.json and prints a summary

Force: the linkage (snip_cad) against the MG90S derated to 0.15 N m (stall is
0.216 N m at 6 V). Mass: printed volumes at PETG density with the infill used,
plus the purchased parts' datasheet masses. Interference: every moving part
against the body's signed distance over the jaw travel. Arm: Elephant's link
meshes, the transit fold at every J6 angle, and a drop pose over the harvest bin.
"""
from __future__ import annotations
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gantry"))
import snip_cad as C
import sdf as S
import assembly as AS

TAU = 0.15                  # N m, MG90S derated (stall 0.216 N m at 6 V)
RHO = 1.27e-3               # PETG, g / mm3
RHO_TPU = 1.21e-3           # TPU 95A
FILL = {"body": 0.50, "ring": 0.75}   # 4 walls + 25 % gyroid: the housing half full, the thin ring mostly
                                     # walls; small parts print near solid
COTS_G = {
    "MG90S servo": 13.4, "Pololu D24V10F6": 1.0, "OLFA AB 9 mm blade, 34 long": 0.9,
    "M3 shoulder screw, 4 x 6": 1.3, "M3 heat-set insert": 0.4, "M2 heat-set insert": 0.15,
    "M2 x 6 countersunk (blade clamp)": 0.15, "M2 x 6 countersunk (crank)": 0.2,
    "2 x M3 x 5 countersunk (camera)": 0.6, "2 dowel pins 2 x 6, 2 x 5": 0.3,
    "4 LEGO Technic pins": 1.4, "servo leads, ties": 3.5,
}
TOOL_PRINTED = ("body", "ring", "mj_a", "mj_b", "link", "crank", "anvil", "pad")
D405_G = 58.0
PAYLOAD = 250.0


def force_curve():
    rows = []
    for deg in np.arange(0.0, 60.01, 0.5):
        rows.append((deg, math.degrees(C.crank_angle(math.radians(deg)))))
    phis = np.radians([r[0] for r in rows]); th = np.radians([r[1] for r in rows])
    MA = np.abs(np.gradient(th, phis))
    out = {}
    for r_mm in (10.0, 20.0, 30.0):
        F = TAU * MA / (r_mm / 1000.0)
        cut = phis <= math.asin(min(1.0, 4.5 / r_mm))
        out[f"r{int(r_mm)}"] = dict(F_min_cut=float(F[cut].min()), F_closed=float(F[0]))
    out["servo_span_deg"] = float(abs(th[-1] - th[0]) * 180 / math.pi)
    out["crank_deg_closed"] = float(rows[0][1]); out["crank_deg_open55"] = float(dict(rows)[55.0])
    return out


def masses():
    printed = {}
    for nm in TOOL_PRINTED:
        d = np.load(os.path.join(AS.BUILD, f"mesh_{nm}.npz"))
        v = abs(S.volume(d["V"], d["F"]))
        rho, fill = (RHO_TPU, 1.0) if nm == "pad" else (RHO, FILL.get(nm, 0.85))
        printed[nm] = dict(vol_cm3=round(v / 1000, 2), g=round(v * rho * fill, 1))
    tool_printed = sum(printed[k]["g"] * (2 if k == "pad" else 1) for k in TOOL_PRINTED)
    tool = tool_printed + sum(COTS_G.values())
    return dict(printed=printed, cots=COTS_G, tool_g=round(tool, 1), d405_g=D405_G,
                on_flange_g=round(tool + D405_G, 1), left_for_harvest_g=round(PAYLOAD - tool - D405_G, 1))


STATIC = ("body", "ring", "d405", "usb_plug", "servo", "regulator", "anvil", "tab_screws", "cam_screws", "lego",
          "pad_fj", "insert_pivot")


def fixed():
    """What everything moves against: the body and the camera's ring under it."""
    return S.union(C.body(), C.camera_ring())


def interference():
    """Every moving part against the body and the ring over the jaw's travel; then the parts that
    sit in them, each against both (a seated part touches its seat: 0.05 is allowed), and the
    ring against the body alone: they meet on one plane."""
    body = fixed()
    worst, at = 0.0, None
    for phi in range(0, 61, 5):
        for nm, m, _ in AS.parts(phi, cots=True):
            if nm in STATIC or nm in ("horn",):
                continue
            d = float(-body(m[0]).min())
            if d > worst:
                worst, at = d, (nm, phi)
    seated = {}
    for nm, m, _ in AS.parts(0.0, cots=True):
        if nm in ("pad_fj", "anvil", "servo", "d405", "cam_screws", "pivot", "regulator", "tab_screws"):
            seated[nm] = round(max(0.0, float(-body(m[0]).min())), 3)
        if nm == "ring":
            seated["ring_on_body"] = round(max(0.0, float(-C.body()(m[0]).min())), 3)
    return dict(worst_penetration_mm=round(max(0.0, worst), 3), worst_at=at, seated=seated)


def assembly_paths():
    """The ways in, each against everything already fitted at that step of the booklet: the jaw
    (with its blade and pad) comes down from above, then across onto the cheek, past the fixed
    pad and the anvil (step 4); the link with its dowel comes down beside its layer and across,
    past the jaw (step 5); the servo with its horn and crank slides in from the back, its dowel
    into the link (step 7). Deepest touch on each."""
    R0, t0 = C.jaw3(0.0)
    fitted = S.union(fixed(), C.anvil(), C.tpu_pad())
    jaws = S.union(S.transform(C.mj_half_a(), R0, t0), S.transform(C.mj_half_b(), R0, t0))
    phi, th, T, Cp = AS.state(0.0)
    a = math.atan2(Cp[1] - T[1], Cp[0] - T[0]); c, s_ = math.cos(a), math.sin(a)
    link = S.transform(C.link(), np.array([[c, 0, -s_], [0, 1, 0], [s_, 0, c]]), np.array([T[0], 0.0, T[1]]))
    against = {"jaw_from_above": fitted, "link_from_above": S.union(fitted, jaws),
               "servo_from_back": S.union(fitted, jaws, link)}
    closed = dict((n, m) for n, m, _ in AS.parts(0.0, cots=True))
    opened = dict((n, m) for n, m, _ in AS.parts(JAW_IN[0], cots=True))
    servo = ("servo", "horn", "crank", "crank_screw", "dowel_crank")
    jaw = ("mj_a", "mj_b", "blade", "pad_mj", "clamp", "insert_clamp")
    link = ("link", "dowel_tail")
    # The jaw held open, down from above JAW_IN[1] toward its opening side (its root disc clear of
    # the fixed jaw over it), then across onto the pivot. Then, the jaw closed, the link with its
    # dowel down beside its layer and across, the dowel into the lug. Last the servo, from the back.
    dx = JAW_IN[1]
    paths = {"jaw_from_above": (opened, jaw, [(dx, 0.0, s) for s in np.arange(50.0, -1e-9, -0.5)] +
                                [(s, 0.0, 0.0) for s in np.arange(dx, -1e-9, -0.25)]),
             "link_from_above": (closed, link, [(0.0, LINK_IN, s) for s in np.arange(45.0, -1e-9, -0.5)] +
                                 [(0.0, s, 0.0) for s in np.arange(LINK_IN, -1e-9, -0.25)]),
             "servo_from_back": (closed, servo, [(0.0, s, 0.0) for s in np.arange(32.0, -1e-9, -0.5)])}
    out = {}
    for name, (parts, group, steps) in paths.items():
        V = np.vstack([parts[n][0] for n in group])
        worst = 0.0
        for d in steps:
            worst = max(worst, float(-against[name](V + np.array(d)).min()))
        out[name] = round(max(0.0, worst), 3)
    return out


JAW_IN = (30.0, 7.0)            # the jaw's opening (deg) and its offset toward +x on the way down:
                                # 7 keeps its tail lug 0.8 off the fixed pad's fins (5 touched them)
LINK_IN = 6.0                   # the link comes down this far to the servo side of its layer: its
                                # dowel clears jaw B's pad rib (at 3.6 it met it)


def pads():
    """The TPU pads as springs: each fin a cantilever, slanted, loaded at its tip across the jaw.
    Linear, so an upper bound: a fin bent further lies flatter and gives more easily."""
    T = C.PADT
    (A, B) = C.pad_fins()[0]
    L = float(np.hypot(*(B - A))) - 0.6                     # free length, base to the tip's centre
    a = math.radians(T["ang"])
    I = (T["y"][1] - T["y"][0]) * T["t"] ** 3 / 12.0
    k_fin = 3 * T["E"] * I / (L ** 3 * math.sin(a) ** 2)     # N / mm, across the jaw
    overlap = 2 * T["proud"] - (C.MJ_RIB_EDGE - C.FJ_RIB_EDGE)        # tip lines past each other, closed
    over = -BLADE_PAST                                        # blade edge past the anvil face, closed
    tip_h = (C.FJ_RIB_EDGE + T["proud"]) - (C.FJ_RIB_EDGE - T["slot"] + T["base"])
    stack = math.ceil(L / T["pitch"]) * T["t"]               # fins lying flat on each other
    travel = tip_h - stack
    out = dict(E_MPa=T["E"], fin_free_mm=round(L, 2), k_fin=round(k_fin, 3), n_fins=T["n"],
               overlap_closed=round(overlap, 2), travel_per_pad=round(travel, 2))
    for d in (2.0, 4.5, 6.0):
        n = min(T["n"], int(d // T["pitch"]) + 1)            # fins under the stem, on each pad
        k = n * k_fin / 2                                     # the two pads in series
        crush_cut = d + overlap - over                        # when the blade reaches the anvil face
        crush_hold = d + overlap                              # closed
        out[f"d{d:g}"] = dict(fins=n, F_end_of_cut=round(k * crush_cut, 2), F_hold=round(k * crush_hold, 2),
                              per_pad=round(crush_hold / 2, 2), bottoms=crush_cut / 2 > travel)
    out["F_closed_empty"] = round(T["n"] * k_fin / 2 * overlap, 2)
    return out


BLADE_PAST = C.BLADE["x0"] - C.ANVIL_X                      # -0.3: the edge closes 0.3 past the anvil face


def camera_clear(phi=30.0):
    """Sight lines from the D405's glass to points in the open mouth, against the body and the
    moving jaw: how many are blocked."""
    body = fixed()
    jaws = S.union(C.mj_half_a(), C.mj_half_b())
    R, t = C.jaw3(math.radians(phi))
    pts = [(x, y, z) for x in (1.0, 3.0, 5.0) for y in (-0.2, 3.0, 6.0) for z in (78.0, 86.0, 94.0, 102.0)]
    blocked = []
    for p in pts:
        p = np.array(p); s = np.linspace(0.0, 1.0, 400)[:, None]
        ray = C.CAM_G + s * (p - C.CAM_G)
        ray = ray[np.linalg.norm(ray - p, axis=1) > 2.5]
        d = np.minimum(body(ray), jaws((ray - t) @ R))      # the jaw's own frame: R^T (x - t)
        if d.min() < 0:
            blocked.append([round(float(v), 1) for v in p])
    # Rev A before the refinement blocked the same 12 of these 36: all of the z 78 row and three at
    # y 6, z 86, behind the cheek's disc. The hub on the cheek adds none.
    return dict(phi=phi, rays=len(pts), blocked=blocked, clear=len(pts) - len(blocked))


def camera():
    """Where the cut zone sits in the D405's view (depth along the optical axis)."""
    Rc = C.cam_R(); g = C.CAM_G
    pts = {"cut zone centre": (0.0, -0.19, 88.0), "blade start": (0.0, -0.19, 72.0), "jaw tips": (0.0, 0.0, 107.5)}
    out = {}
    for k, p in pts.items():
        v = Rc.T @ (np.array(p) - g)
        out[k] = dict(depth_mm=round(float(v[2]), 1), ang_x=round(math.degrees(math.atan2(v[0], v[2])), 1),
                      ang_y=round(math.degrees(math.atan2(v[1], v[2])), 1))
    out["fov_half_deg"] = dict(x=43.5, y=29.0)
    out["min_range_mm"] = 70.0
    return out


if __name__ == "__main__":
    res = dict(force=force_curve(), mass=masses(), camera=camera(), pads=pads())
    print(json.dumps(res, indent=1))
    res["camera_clear"] = camera_clear()
    print("camera", res["camera_clear"])
    res["interference"] = interference()
    res["assembly"] = assembly_paths()
    print("assembly", res["assembly"])
    print("interference", res["interference"])
    json.dump(res, open(os.path.join(AS.BUILD, "checks.json"), "w"), indent=1)
