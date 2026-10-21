"""Place every Herb Snip part, printed and purchased, at a jaw opening phi."""
from __future__ import annotations
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gantry"))
import kit3d as K
import snip_cad as C
import snip_cots as Q

BUILD = os.environ.get("SNIP_BUILD", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build"))
PETG = K.ARM                                 # white PETG, the arm's own white
PETG_HI = K.HILITE
TPU = np.array([0.36, 0.38, 0.40])          # the pads: TPU 95A, dark grey
BRASS = K.BRASS
STEEL = K.STEEL
BLADE_C = np.array([0.80, 0.82, 0.85])


def load(name):
    """A printed part's mesh from build/. The pad and the camera ring are drawn from their
    decimated print meshes: the raw ones run to a million faces for nothing a page can show."""
    names = {"pad": ("pad_dec", "pad"), "ring": ("ring_dec", "ring")}.get(name, (name,))
    for nm in names:
        p = os.path.join(BUILD, f"mesh_{nm}.npz")
        if os.path.exists(p):
            d = np.load(p)
            return (d["V"], d["F"])
    raise FileNotFoundError(f"no mesh for {name}: run build_meshes.py")


def _R3(mesh, R, t):
    V, F = mesh
    return (V @ R.T + t, F)


def state(phi_deg):
    phi = math.radians(phi_deg)
    th = C.crank_angle(phi)
    T = C.P + C.jaw_R(phi) @ (C.T0 - C.P)
    Cp = C.SV + C.A_CRANK * np.array([math.cos(th), math.sin(th)])
    return phi, th, T, Cp


def parts(phi_deg=0.0, cots=True, wrist=False, hi=None, colors=None):
    """List of (name, mesh, color) in the tool frame."""
    phi, th, T, Cp = state(phi_deg)
    R, t = C.jaw3(phi)
    col = lambda n, c: PETG_HI if (hi and n in hi) else (colors or {}).get(n, c)
    out = [("body", load("body"), col("body", PETG)),
           ("ring", load("ring"), col("ring", PETG)),
           ("anvil", load("anvil"), col("anvil", np.array([0.92, 0.92, 0.88]))),
           ("mj_a", _R3(load("mj_a"), R, t), col("mj_a", PETG)),
           ("mj_b", _R3(load("mj_b"), R, t), col("mj_b", PETG)),
           ("pad_fj", load("pad"), col("pad_fj", TPU)),
           ("pad_mj", _R3(_R3(load("pad"), *C.PAD_FLIP), R, t), col("pad_mj", TPU))]
    ang_link = math.atan2(Cp[1] - T[1], Cp[0] - T[0])
    out.append(("link", Q._in_jaw_plane(load("link"), ang_link, T), col("link", PETG)))
    out.append(("crank", Q._in_jaw_plane(load("crank"), th, C.SV), col("crank", PETG)))
    if cots:
        out += [("d405", Q.d405(), col("d405", np.array([0.55, 0.57, 0.60]))),
                ("usb_plug", Q.usb_plug(), col("usb_plug", np.array([0.15, 0.15, 0.16]))),
                ("servo", Q.servo(), col("servo", np.array([0.18, 0.30, 0.62]))),
                ("horn", Q.horn_and_screw(th), col("horn", np.array([0.95, 0.95, 0.95]))),
                ("blade", _R3(Q.blade(), R, t), col("blade", BLADE_C)),
                ("pivot", Q.pivot_screw(), col("pivot", STEEL)),
                ("insert_pivot", Q.insert_pivot(), col("insert_pivot", BRASS)),
                ("insert_clamp", _R3(Q.insert_clamp(), R, t), col("insert_clamp", BRASS)),
                ("dowel_tail", Q.dowel(T, 3.3, 6.0), col("dowel", STEEL)),
                ("dowel_crank", Q.dowel(Cp, 6.7, 5.0), col("dowel", STEEL)),
                ("clamp", _R3(Q.clamp_screw(), R, t), col("clamp", STEEL)),
                ("regulator", Q.regulator(), col("regulator", K.PCB)),
                ("tab_screws", Q.tab_screws(), col("tab_screws", STEEL)),
                ("crank_screw", Q._in_jaw_plane(Q.mv0(Q.crank_screw()), 0.0, (0, 0)), col("crank_screw", STEEL)),
                ("cam_screws", Q.cam_screws(), col("cam_screws", STEEL))]
        for x, y in C.LEGO:
            out.append(("lego", Q.lego_pin(x, y), col("lego", np.array([0.12, 0.12, 0.13]))))
    if wrist:
        W = Q.wrist()
        out += [("flange", W["joint6_flange"], K.BLACKPART), ("joint6", W["joint6"], K.ARM),
                ("joint5", W["joint5"], K.ARM)]
    return out


def kparts(lst, ang=30.0, lw=None):
    return [K.Part(m, c, ang=ang, lw=lw) for _, m, c in lst]
