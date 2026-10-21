"""Mesh every printed part from snip_cad.py into build/mesh_<part>.npz, the meshes the
booklet, the checks and export_print.py all read. Each part has the resolution its smallest
feature needs: the crank's countersink and the blade pocket's 0.3 step want under 0.1 mm,
the pad's 0.8 fins 0.05.

    python build_meshes.py              every part
    python build_meshes.py crank mj_a   just those
"""
from __future__ import annotations
import os, sys, time
import numpy as np
import sdf as S
import snip_cad as C

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
RES = {"body": 0.2, "ring": 0.15, "mj_a": 0.08, "mj_b": 0.1, "link": 0.1, "crank": 0.09, "anvil": 0.1, "pad": 0.05}
PRINT_RES = {}                     # parts whose print file wants another resolution than their drawing


def open_edges(F):
    """Edges not shared by exactly two faces: 0 for a closed, printable mesh."""
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _, n = np.unique(E, axis=0, return_counts=True)
    return int((n != 2).sum())


def build(nm, res, tag=""):
    t = time.time()
    V, F = S.mesh(C.PARTS[nm](), res=res)
    np.savez_compressed(os.path.join(BUILD, f"mesh_{nm}{tag}.npz"), V=V, F=F)
    print(f"{nm}{tag}: {len(F)} faces at {res} mm, {S.volume(V, F) / 1000:.3f} cm3, "
          f"{open_edges(F)} open edges ({time.time() - t:.0f} s)", flush=True)


if __name__ == "__main__":
    os.makedirs(BUILD, exist_ok=True)
    for nm in sys.argv[1:] or list(RES):
        build(nm, RES[nm])
        if nm in PRINT_RES:
            build(nm, PRINT_RES[nm], "_print")
