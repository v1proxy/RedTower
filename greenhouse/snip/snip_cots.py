"""Purchased parts of the Herb Snip, in the tool frame, as kit3d meshes.

D405: Intel's own mesh (realsense-ros, realsense2_description/meshes/d405.stl).
Flange and wrist: Elephant Robotics' joint7.dae / joint6.dae, posed by arm280.
MG90S: TowerPro's datasheet envelope (22.8 x 12.2 x 28.5, tabs 32.2, holes 27.8);
TowerPro publishes no CAD. Blade: 9 mm snap-off, 0.38 thick, cut to 35.
"""
from __future__ import annotations
import os, sys, math, struct
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gantry"))
import kit3d as K
import snip_cad as C

HERE = os.path.dirname(os.path.abspath(__file__))
# Intel's mesh (realsense-ros, Apache 2.0), kept beside the repo like the arm meshes.
D405_STL = os.environ.get("D405_STL", os.path.join(HERE, "..", "..", "..", "..", "realsense_mesh", "d405.stl"))


def _stl(path):
    d = open(path, "rb").read(); n = struct.unpack("<I", d[80:84])[0]
    a = np.frombuffer(d[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    V = a["v"].reshape(-1, 3).astype(float)
    return K.weld((V, np.arange(len(V)).reshape(-1, 3)), tol=1e-3)


def xf(mesh, R=None, t=(0, 0, 0)):
    V, F = mesh
    R = np.eye(3) if R is None else np.asarray(R)
    return (V @ R.T + np.asarray(t), F)


def d405():
    return xf(_stl(D405_STL), C.cam_R(), C.CAM_G)


def usb_plug():
    """Envelope of a straight USB-C plug and its overmould in the D405's side socket:
    12 x 7 in section, 28 out from the USB face (the mesh's +x face, x = 21)."""
    m = K.box(28.0, 12.0, 7.0, c=(21.0, -6.0, -15.0))
    return xf(m, C.cam_R(), C.CAM_G)


def servo():
    x0, x1 = C.SERVO_X; z0, z1 = C.SERVO_Z
    y0, y1 = C.SERVO_TOP, C.SERVO_TOP + C.SERVO_H
    case = K.box(x1 - x0, y1 - y0, z1 - z0, c=(x0, y0, z0))                 # kit3d.box: c is the min corner
    zc = (z0 + z1) / 2
    tabs = K.box(x1 - x0, C.TAB[1] - C.TAB[0], C.TAB_SPAN, c=(x0, C.TAB[0], zc - C.TAB_SPAN / 2))
    boss = K.rot(K.cylinder(5.9, 4.0, n=48, c=(0, 0, 0)), rx=-math.pi / 2)      # along +y
    boss = K.mv(boss, C.SV[0], y0 - 4.0, C.SV[1])
    spline = K.mv(K.rot(K.cylinder(2.4, 1.2, n=24), rx=-math.pi / 2), C.SV[0], y0 - 5.2, C.SV[1])
    return K.merge(case, tabs, boss, spline)


def horn_and_screw(theta):
    """Single-arm horn in the crank pocket, plus the M2 crank screw, at crank angle theta."""
    arm = K.extrude(np.array([(0, -3.0), (16.0, -2.1), (16.0, 2.1), (0, 3.0)]), C.HORN[1] - C.HORN[0])
    hub = K.cylinder(3.7, C.SERVO_TOP - 0.5 - C.HORN[0], n=36)
    m = K.merge(arm, hub)
    m = K.rot(m, rx=-math.pi / 2)                       # extrusion z -> +y
    m = K.mv(m, 0, C.HORN[0], 0)
    m = _in_jaw_plane(m, theta, C.SV)
    return m


def _in_jaw_plane(mesh, ang, at):
    """Rotate a mesh modelled along +x (in the x-z plane) by ang toward +z, then place at (x, z)."""
    V, F = mesh
    c, s = math.cos(ang), math.sin(ang)
    R = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])    # +x -> (cos, 0, sin)
    return (V @ R.T + np.array([at[0], 0, at[1]]), F)


def blade():
    """The snapped OLFA AB piece: 0.38 thick, its cutting-edge bevel on the -y face."""
    b = C.BLADE
    poly = C.blade_outline()[::-1]                 # (x, z), counter-clockwise; nominal 59 deg score angle
    V, F = K.extrude(poly, b["t"])                 # extruded along +z
    V = np.c_[V[:, 0], -V[:, 2], V[:, 1]]          # (x, z_profile, h) -> (x, -h, z): a rotation, blade at y -t .. 0
    return K.weld((V, F), tol=1e-6)


# ------------------------------------------------------------------ fasteners, with their drives
# Heads from the standards (ISO 4762 socket head, ISO 7380 button head, ISO 10642 countersunk)
# and the servo's own self-tappers (pan head, Phillips). Each head is meshed from a signed
# distance model so its drive is a real recess, cached in build/. Local frame: the head's
# bearing face at z = 0 and the head toward +z (a countersunk head's wide face at z = k), the
# shank down -z, built as a plain cylinder.
HEADS = {
    "iso4762_M2": dict(kind="socket", dk=3.8, k=2.0, s=1.5, t=1.0),
    "iso4762_M3": dict(kind="socket", dk=5.5, k=3.0, s=2.5, t=1.3),
    "iso7380_M3": dict(kind="button", dk=5.7, k=1.65, s=2.0, t=1.04),
    "iso10642_M2": dict(kind="csk", dk=4.4, k=1.2, s=1.3, t=0.8, d=2.0),
    "iso10642_M3": dict(kind="csk", dk=6.72, k=1.86, s=2.0, t=1.1, d=3.0),
    "iso7379_M3": dict(kind="socket", dk=7.0, k=3.0, s=2.0, t=1.6),       # the 4 mm shoulder screw's head
    "pan_ph_M2": dict(kind="phillips", dk=3.6, k=1.4, w=0.55, l=2.5, t=0.9),
}


def _hex(s):
    a = np.radians(np.arange(6) * 60.0 + 30.0)
    return np.c_[np.cos(a), np.sin(a)] * (s / math.sqrt(3.0))


def _head_sdf(h):
    import sdf as S
    r, k = h["dk"] / 2, h["k"]
    if h["kind"] == "socket":
        solid = S.cyl((0, 0, 0), r, "z", 0.0, k)
    elif h["kind"] == "button":                          # a low dome: a cylinder rim, then a cone
        solid = S.union(S.cyl((0, 0, 0), r, "z", 0.0, 0.5), S.cone((0, 0, 0), r, r * 0.77, "z", 0.5, k))
    elif h["kind"] == "csk":                             # 90 deg: from the shank at z 0 to dk at z k
        solid = S.cone((0, 0, 0), h["d"] / 2, r, "z", 0.0, k)
    else:                                                # pan head
        solid = S.union(S.cyl((0, 0, 0), r, "z", 0.0, k * 0.6), S.cone((0, 0, 0), r, r * 0.72, "z", k * 0.6, k))
    if h["kind"] == "phillips":
        w, l, t = h["w"], h["l"], h["t"]
        drive = S.union(S.box((-l / 2, -w / 2, k - t), (l / 2, w / 2, k + 1.0)),
                        S.box((-w / 2, -l / 2, k - t), (w / 2, l / 2, k + 1.0)))
    else:
        drive = S.prism(_hex(h["s"]), "z", k - h["t"], k + 1.0)
    return S.diff(solid, drive)


_HEAD_CACHE = {}


def head_mesh(name, res=0.04):
    """A fastener head with its drive, meshed once and kept in build/."""
    if name in _HEAD_CACHE:
        return _HEAD_CACHE[name]
    build = os.environ.get("SNIP_BUILD", os.path.join(HERE, "build"))
    p = os.path.join(build, f"head_{name}.npz")
    if os.path.exists(p):
        d = np.load(p); m = (d["V"], d["F"])
    else:
        import sdf as S
        import decimate as DC
        V, F = S.mesh(_head_sdf(HEADS[name]), res=res, pad=0.2)
        V, F = DC.decimate(V, F, tol=0.004, verbose=False)
        os.makedirs(build, exist_ok=True)
        np.savez_compressed(p, V=V, F=F); m = (V, F)
    _HEAD_CACHE[name] = m
    return m


def screw(name, L, d=None):
    """Head plus shank, local frame as above. L from the bearing face (for a countersunk
    screw, from the narrow end of the head: its length is overall, so the shank is L - k)."""
    h = HEADS[name]
    d = d if d is not None else float(name.split("_M")[1])
    sh = L - h["k"] if h["kind"] == "csk" else L
    return K.merge(head_mesh(name), K.cylinder(d / 2, sh, n=20, c=(0, 0, -sh)))


def lego_pin(x, y):
    """LEGO 2780: hollow, a collar at mid-length."""
    shaft = K.ring(2.4, 1.55, 15.8, c=(x, y, -7.9 + 0.3), n=36)
    collar = K.ring(2.95, 1.55, 0.6, c=(x, y, 0.0), n=36)
    return K.merge(shaft, collar)


# local +z (a head's direction) to the tool's +y, or to its -y; both proper rotations
TO_PY = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])
TO_MY = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])


def shoulder_screw():
    """Head (7 x 3, 2 hex), the 4 x 6 shoulder and the M3 thread, in the local screw frame."""
    sh = C.SHOULDER
    return K.merge(head_mesh("iso7379_M3"), K.cylinder(sh["d"] / 2, sh["L"], n=28, c=(0, 0, -sh["L"])),
                   K.cylinder(1.5, sh["thread"] - 0.5, n=20, c=(0, 0, -sh["L"] - sh["thread"])))


def pivot_screw():
    """The shoulder screw from jaw B's side: head flush in the lug's counterbore, the shoulder's
    end on the cheek's insert at y -3."""
    V, F = shoulder_screw()
    return (V @ TO_PY.T + np.array([C.P[0], C.JAW[0] + C.SHOULDER["L"], C.P[1]]), F)


def insert(spec, n=28):
    """A knurled brass heat-set insert, local frame: from z 0 down to -L."""
    od, L = spec["od"], spec["L"]
    body = K.ring(od / 2 - 0.15, od * 0.32, L, c=(0, 0, -L), n=n)
    bands = [K.ring(od / 2, od * 0.32, L * 0.22, c=(0, 0, -L * (0.12 + 0.45 * i) - L * 0.22), n=n) for i in (0, 1)]
    return K.merge(body, *bands)


def insert_pivot():
    """The M3 insert in the cheek, flush with its jaw-side face, going -y."""
    V, F = insert(C.INSERT_M3)
    return (V @ TO_PY.T + np.array([C.P[0], C.JAW[0], C.P[1]]), F)


def insert_clamp():
    """The M2 insert through jaw B at the clamp screw, flush with its outer face."""
    V, F = insert(C.INSERT_M2)
    x, z = C.CLAMP
    return (V @ TO_PY.T + np.array([x, C.JAW[1], z]), F)


def dowel(xz, y0, L):
    return K.mv(K.rot(K.cylinder(1.0, L, n=20), rx=-math.pi / 2), xz[0], y0, xz[1])


def clamp_screw():
    """The one blade-clamp screw: an ISO 10642 M2 x 6, its head flush in jaw A's outer face, the
    shank through both halves into jaw B's insert."""
    V, F = screw("iso10642_M2", 6.0)
    k = HEADS["iso10642_M2"]["k"]
    x, z = C.CLAMP
    return (V @ TO_MY.T + np.array([x, C.JAW[0] + k, z]), F)


def regulator():
    """Pololu D24V10F6, 17.8 x 12.7 x 3.6, in the housing's bay on a square of foam tape, 1 thick
    (footprint block)."""
    x = C.REG_BAY["x"][0] + 1.0
    return K.box(3.6, 12.7, 17.8, c=(x, 33.0 - 6.35, 38.0 - 8.9))      # centred on (x + 1.8, 33, 38)


def wrist(q6=0.0):
    """Elephant's flange (joint7) and the joint6 housing, in the tool frame."""
    import arm280 as A
    q = (0, 0, 0, 0, 0, q6)
    fr = A.frames(q); Tf = fr["joint6_flange"].copy(); Tf[:3, 3] *= 1000.0
    Ti = np.linalg.inv(Tf)
    out = {}
    for name, (V, F) in A.pose(q, grid=0.0):
        if name in ("joint5", "joint6", "joint6_flange"):
            Vl = (np.hstack([V, np.ones((len(V), 1))]) @ Ti.T)[:, :3] - np.array([0, 0, 1.7])
            out[name] = (Vl, F)
    return out


def mv0(m):
    return m


def tab_screws():
    """The servo's two supplied self-tappers, through its tabs into the ledge, heads on +y."""
    zc = (C.SERVO_Z[0] + C.SERVO_Z[1]) / 2
    out = []
    for dz in (-C.TAB_HOLE / 2, C.TAB_HOLE / 2):
        out.append(K.mv(K.rot(screw("pan_ph_M2", 8.0, d=1.8), rx=-math.pi / 2), C.SV[0], C.TAB[1], zc + dz))
    return K.merge(*out)


def crank_screw():
    """ISO 10642 M2 x 6 countersunk through the crank's centre into the servo spline,
    head flush with the crank's -y face."""
    m = K.mv(screw("iso10642_M2", 6.0), 0, 0, -HEADS["iso10642_M2"]["k"])       # wide face at z 0
    return K.mv(K.rot(m, rx=math.pi / 2), C.SV[0], C.CRANK[0], C.SV[1])         # down -z -> +y, into the spline


def cam_screws():
    """2 x ISO 10642 M3 x 5 through the bracket plate into the D405's back, heads flush in the
    plate's far face, 2 of thread in the camera."""
    Rc = C.cam_R(); back = C.CAM_G - 23.0 * Rc[:, 2]
    flip = np.diag([1.0, -1.0, -1.0])                    # head toward -z, the shank toward the camera
    k = HEADS["iso10642_M3"]["k"]
    out = []
    for sx in (-10.0, 10.0):
        V, F = screw("iso10642_M3", 5.0)
        m = (V @ flip.T + np.array([sx, 0.0, -C.CAM_PLATE + k]), F)    # a rotation: faces keep their winding
        out.append(xf(m, Rc, back))
    return K.merge(*out)
