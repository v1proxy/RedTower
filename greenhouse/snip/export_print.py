"""Write every printed part as a binary STL, oriented the way it prints and
standing on z = 0. The raw marching-cubes meshes are dense; the print files are
made from decimate.py's output, which merges the flat faces and keeps the
curved and sharp ones, closed, adding at most 0.05 mm to the meshing error.

    python export_print.py <out_dir>
"""
from __future__ import annotations
import os, sys
import numpy as np
import sdf as S
import snip_cad as C

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

# tool frame -> print frame (proper rotations only: never a mirror)
ROT = {
    "body": np.eye(3),                                                   # its flat base down
    "ring": np.array([[0, -1, 0], [0, 0, 1], [-1, 0, 0]], float),         # on its side: the +x face down
    "mj_a": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float),          # outer face down, blade pocket up
    "mj_b": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float),          # jaw face down
    "link": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float),
    "crank": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float),         # horn pocket up
    "anvil": np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float),         # anvil face down
    "pad": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float),           # on its side: every layer the profile
}
NAMES = {"body": "snip_body", "ring": "snip_camera_ring", "mj_a": "snip_jaw_A", "mj_b": "snip_jaw_B", "link": "snip_link",
         "crank": "snip_crank", "anvil": "snip_anvil", "pad": "snip_pad_TPU_x2"}


def clean(V, F):
    """Weld vertices that sit on the same point, drop the faces a collapse left with no area
    between two equal corners, and the face pairs folded back on each other. The decimated mesh
    is closed by index already; this makes it closed by position, which is what a slicer reads."""
    U, inv = np.unique(V, axis=0, return_inverse=True)
    F = inv.reshape(-1)[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    _, idx, cnt = np.unique(np.sort(F, 1), axis=0, return_index=True, return_counts=True)
    F = F[np.sort(idx[cnt == 1])]
    return U, F


def edge_check(F):
    """Edges not shared by exactly two faces."""
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    _, c = np.unique(E, axis=0, return_counts=True)
    return int((c != 2).sum())


def load(nm):
    """The decimated mesh (decimate.py) when there is one, else the raw one."""
    src = nm
    for p in (os.path.join(BUILD, f"mesh_{src}_dec.npz"), os.path.join(BUILD, f"mesh_{src}.npz")):
        if os.path.exists(p):
            d = np.load(p)
            return d["V"], d["F"]
    raise FileNotFoundError(f"no mesh for {nm}: run build_meshes.py, then decimate.py")


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for nm, R in ROT.items():
        assert abs(np.linalg.det(R) - 1.0) < 1e-9, nm
        V, F = load(nm)
        W = V @ R.T
        W -= np.array([(W[:, 0].min() + W[:, 0].max()) / 2, (W[:, 1].min() + W[:, 1].max()) / 2, W[:, 2].min()])
        W, F = clean(W.astype(np.float32), F)          # welded at the precision the STL stores
        W = W.astype(float)
        S.write_stl(os.path.join(out, NAMES[nm] + ".stl"), W, F, NAMES[nm])
        print(nm, len(F), "tris", np.round(W.max(0) - W.min(0), 1), "vol", round(S.volume(W, F) / 1000, 2), "cm3,",
              edge_check(F), "edges not shared by two faces")
