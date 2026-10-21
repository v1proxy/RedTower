"""The Herb Snip on the arm: the transit fold with the tool on, jaws closed and open, at
every J6 angle; and the folded drop over the dead-leaf tray. Writes build/arm_checks.json.

Cabinet numbers from greenhouse/gantry/frame.py: the tray line is y = 203 and the fold
must stay 20 behind it (y >= 223). Harvest Rev B's dead-leaf tray hangs on its rails in the
base bay, rims at z 120, 457 wide on cabinet x 400. A dead leaf rides in the folded arm's
closed jaws; the carriage stops over one of the tray's five drops at the lowest Z and the
jaws open. Z full travel there must clear the rims with the jaws open or closed.
"""
from __future__ import annotations
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gantry"))
import collide as CL
import frame as Fr
import armcheck as AC
import ik
import snip_cad as C

X_MIN = 163.5                        # carriage centre at its left limit (frame.X_MIN)
X_MAX = 1249.75                      # and at its right limit (Gantry Rev E)
J1_LOW = Fr.MAST_Z0 + 12.0 + Fr.WHEEL_REACH + 5.0   # mast foot, end mount, wheels, 5 of margin
TRAY_LINE, FOLD_MIN_Y = 203.0, 223.0


def transit():
    out = []
    for j6 in range(-180, 181, 30):
        q = tuple(Fr.TIGHT_Q[:5]) + (j6,)
        row = dict(j6=j6)
        for phi in (0.0, 55.0):
            r = AC.transit_report(q, phi)
            row[f"clash_{phi:.0f}"] = AC.clashes(q, phi=phi)
            row[f"tool_ymin_{phi:.0f}"] = round(r["tool_ymin"], 1)
        out.append(row)
    return out


def tray():
    """The folded arm over the dead-leaf tray at the lowest J1, the carriage over each of its
    five drops: the jaws' clearance over the rim, where they open, the margin to the tray's side
    walls, and the carriage's X for each drop. The fold is the transit fold, so nothing new
    moves: only the gantry's X changes from one drop to the next."""
    fold = tuple(Fr.TIGHT_Q[:5]) + (0.0,)
    T = C.TRAY
    res = dict(j1_low=round(J1_LOW, 1), rim_z=T["rim_z"])
    for phi in (0.0, 55.0):
        tool = AC.to_cabinet(AC.tool_in_base(fold, phi), X_MIN, J1_LOW)
        res[f"tool_low_{phi:.0f}"] = round(float(tool[:, 2].min()), 1)
        res[f"tool_x_{phi:.0f}"] = [round(float(tool[:, 0].min() - X_MIN), 1), round(float(tool[:, 0].max() - X_MIN), 1)]
        res[f"clash_{phi:.0f}"] = AC.clashes(fold, phi=phi)
    tcp = ik.base_to_cab(ik.tcp(np.array(fold))[0], x=X_MIN, z=J1_LOW)
    res["cut_point_at_x_min"] = [round(float(v), 1) for v in tcp]
    res["over_rim"] = round(float(tcp[2] - T["rim_z"]), 1)
    res["clearance"] = round(min(res["tool_low_0"], res["tool_low_55"]) - T["rim_z"], 1)
    inner = (T["x"][0] + T["wall"], T["x"][1] - T["wall"])
    drops = []
    for xd in T["drops_x"]:
        X = X_MIN + (xd - float(tcp[0]))
        lo = res["tool_x_55"][0] + X; hi = res["tool_x_55"][1] + X
        drops.append(dict(x=xd, carriage_x=round(X, 1), in_travel=bool(X_MIN <= X <= X_MAX),
                          jaws_to_walls=round(min(xd - inner[0], inner[1] - xd), 1),      # where the leaf falls
                          tool_to_walls=round(min(lo - inner[0], inner[1] - hi), 1)))     # the whole fold, in x
    res["drops"] = drops
    res["drop_y_vs_doc"] = round(float(tcp[1] - T["drop_y"]), 1)
    res["jaws_to_front_back"] = round(min(float(tcp[1]) - T["y"][0] - T["wall"], T["y"][1] - T["wall"] - float(tcp[1])), 1)
    return res


if __name__ == "__main__":
    t = transit() if "--no-transit" not in sys.argv else []
    for row in t:
        print(row, flush=True)
    d = tray()
    print(d, flush=True)
    path = os.path.join(HERE, "build", "arm_checks.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    json.dump(dict(transit=t or old.get("transit", []), tray=d), open(path, "w"), indent=1, default=float)
