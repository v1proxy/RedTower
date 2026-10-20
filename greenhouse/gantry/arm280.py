"""myCobot 280 Pi -- real geometry, posed from the official URDF.

Meshes and kinematics are Elephant Robotics' own `mycobot_description`
pack (mycobot_280_pi.urdf + the eight .dae link meshes). Nothing here is
notional: `pose()` runs the URDF chain and returns the link meshes placed
in millimetres, with the g_base origin at (0, 0, 0).

Joint numbering follows the robot, not the URDF's link names: the URDF
calls the J1 actuator `joint2_to_joint1`, so q[0] drives it.
"""
import math
import os

import numpy as np

import dae

MESH_DIR = os.environ.get(
    "MYCOBOT_MESH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "..", "..", "mycobot_mesh"),
)

# ---------------------------------------------------------------- transforms

def _rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = (math.cos(r), math.sin(r), math.cos(p),
                              math.sin(p), math.cos(y), math.sin(y))
    R = np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp,     cp * sr,                cp * cr],
    ])
    M = np.eye(4)
    M[:3, :3] = R
    return M


def _xf(xyz, rpy):
    M = _rpy(*rpy)
    M[:3, 3] = xyz
    return M


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


# ---------------------------------------------------- URDF chain (metres)
# (link, mesh file, visual origin xyz, visual origin rpy)
LINKS = [
    ("g_base",       "G_base.dae",    (0.0,  0.0,    -0.03),   (0, 0,       1.5708)),
    ("joint1",       "joint1_pi.dae", (0.0,  0.0,     0.0),    (0, 0,       0)),
    ("joint2",       "joint2.dae",    (0.0,  0.0,    -0.06096), (0, 0,      -1.5708)),
    ("joint3",       "joint3.dae",    (0.0,  0.0,     0.03256), (0, -1.5708, 0)),
    ("joint4",       "joint4.dae",    (0.0,  0.0,     0.03056), (0, -1.5708, 0)),
    ("joint5",       "joint5.dae",    (0.0, -0.001,  -0.0345),  (0, -1.5708, 1.5708)),
    ("joint6",       "joint6.dae",    (0.0,  0.0,    -0.038),   (0, 0,       0)),
    ("joint6_flange", "joint7.dae",   (0.0,  0.0,    -0.012),   (0, 0,       0)),
]

# (parent, child, origin xyz, origin rpy, actuated joint index or None)
JOINTS = [
    ("g_base",  "joint1",        (0.0,     0.0,      0.0),     (0, 0, 0),             None),
    ("joint1",  "joint2",        (0.0,     0.0,      0.13956), (0, 0, 0),             0),
    ("joint2",  "joint3",        (0.0,     0.0,     -0.001),   (0, 1.5708, -1.5708),  1),
    ("joint3",  "joint4",        (-0.1104, 0.0,      0.0),     (0, 0, 0),             2),
    ("joint4",  "joint5",        (-0.096,  0.0,      0.06462), (0, 0, -1.5708),       3),
    ("joint5",  "joint6",        (0.0,    -0.07318, -0.001),   (1.5708, -1.5708, 0),  4),
    ("joint6",  "joint6_flange", (0.0,     0.0456,   0.0),     (-1.5708, 0, 0),       5),
]

# Joint limits from the URDF, degrees. J1..J6.
LIMITS = [(-168.0, 168.0), (-140.0, 140.0), (-150.0, 150.0),
          (-150.0, 150.0), (-155.0, 160.0), (-180.0, 180.0)]

MM = 1000.0

_CACHE = {}


def _mesh(fn, grid):
    key = (fn, grid)
    if key not in _CACHE:
        m = dae.load(os.path.join(MESH_DIR, fn))
        if grid:
            m = dae.decimate(m, grid)
        _CACHE[key] = m
    V, F = _CACHE[key]
    return V.copy(), F


def frames(q=(0, 0, 0, 0, 0, 0)):
    """Link-frame transforms, metres, keyed by URDF link name."""
    out = {"g_base": np.eye(4)}
    for parent, child, xyz, rpy, qi in JOINTS:
        T = _xf(xyz, rpy)
        if qi is not None:
            T = T @ _rz(math.radians(q[qi]))
        out[child] = out[parent] @ T
    return out


def pose(q=(0, 0, 0, 0, 0, 0), grid=0.003, base=True, mm=True):
    """Posed arm as a list of (link_name, (V, F)) with V in millimetres."""
    fr = frames(q)
    out = []
    for name, fn, vxyz, vrpy in LINKS:
        if name == "g_base" and not base:
            continue
        V, F = _mesh(fn, grid)
        M = fr[name] @ _xf(vxyz, vrpy)
        V = (np.hstack([V, np.ones((len(V), 1))]) @ M.T)[:, :3]
        if mm:
            V = V * MM
        out.append((name, (V, F)))
    return out


def merged(q=(0, 0, 0, 0, 0, 0), grid=0.003, base=True):
    """The whole posed arm as one (V, F) in millimetres."""
    off, Vs, Fs = 0, [], []
    for _, (V, F) in pose(q, grid, base):
        Vs.append(V)
        Fs.append(F + off)
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs)


def tcp(q=(0, 0, 0, 0, 0, 0)):
    """Flange-centre position in millimetres, in the g_base frame."""
    return frames(q)["joint6_flange"][:3, 3] * MM


def mount_offset():
    """How far below the g_base origin the bottom mounting face sits, mm.

    The arm bolts down through this face, so a mounting plate's top surface
    goes here.
    """
    V, _ = _mesh("G_base.dae", 0.0)
    M = _xf(LINKS[0][2], LINKS[0][3])
    V = (np.hstack([V, np.ones((len(V), 1))]) @ M.T)[:, :3] * MM
    return -V[:, 2].min()


# ------------------------------------------------------------------- poses
# Named joint vectors, degrees, J1..J6.
POSES = {
    # Shipping / stowed fold. This is how the arm must travel the mast:
    # tiers B and C have 341 mm of headroom.
    "folded":  (0, -110, -80, -140, -90, 0),   # collision free, 162.6 long
    # Straight up, for the reach envelope and the height check.
    "zero":    (0, 0, 0, 0, 0, 0),
    # Working reach into a tier, gripper down over a pot.
    "reach":   (0, -40, -55, -85, 0, 0),
    # Half-unfolded, the pose to bolt the base down in.
    "install": (0, -90, 120, -120, 0, 0),
}
