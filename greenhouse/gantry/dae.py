"""Minimal COLLADA (.dae) reader, enough for the Elephant Robotics myCobot meshes.

Returns (V, F) in metres, Z-up, in the file's own local frame.

Handles the two exporters present in the official mesh pack:
  * Blender 2.79  -- <triangles>, unit metre, flat node tree
  * Rhinoceros 7  -- <polygons> (one <p> per n-gon), unit millimetre,
                     <instance_node> indirection into <library_nodes>

Deliberately ignores materials, normals and UVs: the renderer computes its
own normals, and these parts are drawn as line art.
"""
import re
import xml.etree.ElementTree as ET

import numpy as np

NS = "{http://www.collada.org/2005/11/COLLADASchema}"


def _tag(e):
    return e.tag.split("}")[-1]


def _floats(txt):
    return np.fromstring(txt.replace("\n", " "), sep=" ")


def _ints(txt):
    return np.fromstring(txt.replace("\n", " "), sep=" ", dtype=float).astype(int)


def _node_matrix(node):
    """Compose a node's local transform from its transform elements, in order."""
    M = np.eye(4)
    for ch in node:
        t = _tag(ch)
        if t == "matrix":
            M = M @ _floats(ch.text).reshape(4, 4)
        elif t == "translate":
            v = _floats(ch.text)
            T = np.eye(4)
            T[:3, 3] = v[:3]
            M = M @ T
        elif t == "rotate":
            v = _floats(ch.text)
            ax, ang = v[:3], np.radians(v[3])
            n = np.linalg.norm(ax)
            if n < 1e-12:
                continue
            ax = ax / n
            c, s = np.cos(ang), np.sin(ang)
            K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
            R = np.eye(4)
            R[:3, :3] = np.eye(3) * c + s * K + (1 - c) * np.outer(ax, ax)
            M = M @ R
        elif t == "scale":
            v = _floats(ch.text)
            S = np.eye(4)
            S[0, 0], S[1, 1], S[2, 2] = v[:3]
            M = M @ S
    return M


class _Doc:
    def __init__(self, path):
        self.root = ET.parse(path).getroot()
        self.by_id = {}
        for e in self.root.iter():
            i = e.get("id")
            if i:
                self.by_id[i] = e
        a = self.root.find(f"{NS}asset")
        self.unit = 1.0
        self.up = "Y_UP"
        if a is not None:
            u = a.find(f"{NS}unit")
            if u is not None and u.get("meter"):
                self.unit = float(u.get("meter"))
            z = a.find(f"{NS}up_axis")
            if z is not None and z.text:
                self.up = z.text.strip()

    def ref(self, url):
        return self.by_id.get((url or "").lstrip("#"))

    # ---- geometry ----------------------------------------------------
    def positions(self, mesh, vert_src):
        """Resolve a <vertices> or <source> url to an (n,3) position array."""
        e = self.ref(vert_src)
        if e is None:
            return None
        if _tag(e) == "vertices":
            for inp in e.findall(f"{NS}input"):
                if inp.get("semantic") == "POSITION":
                    e = self.ref(inp.get("source"))
                    break
        if e is None or _tag(e) != "source":
            return None
        fa = e.find(f"{NS}float_array")
        acc = e.find(f"{NS}technique_common/{NS}accessor")
        stride = int(acc.get("stride", 3)) if acc is not None else 3
        d = _floats(fa.text)
        return d.reshape(-1, stride)[:, :3]

    def geometry(self, gid):
        """(V, F) for one <geometry>, local to the geometry."""
        g = self.by_id.get(gid)
        if g is None:
            return None
        mesh = g.find(f"{NS}mesh")
        if mesh is None:
            return None
        Vs, Fs = [], []
        for prim in mesh:
            kind = _tag(prim)
            if kind not in ("triangles", "polylist", "polygons"):
                continue
            inputs = prim.findall(f"{NS}input")
            stride = max(int(i.get("offset", 0)) for i in inputs) + 1
            voff, vsrc = 0, None
            for i in inputs:
                if i.get("semantic") == "VERTEX":
                    voff = int(i.get("offset", 0))
                    vsrc = i.get("source")
            P = self.positions(mesh, vsrc)
            if P is None:
                continue
            base = sum(len(v) for v in Vs)
            tris = []
            if kind == "triangles":
                p = _ints(prim.find(f"{NS}p").text)
                idx = p.reshape(-1, stride)[:, voff]
                tris = idx.reshape(-1, 3)
            elif kind == "polylist":
                counts = _ints(prim.find(f"{NS}vcount").text)
                p = _ints(prim.find(f"{NS}p").text).reshape(-1, stride)[:, voff]
                o = 0
                for c in counts:
                    poly = p[o:o + c]
                    o += c
                    for k in range(1, c - 1):
                        tris.append((poly[0], poly[k], poly[k + 1]))
            else:  # polygons: one <p> per polygon
                for pe in prim.findall(f"{NS}p"):
                    poly = _ints(pe.text).reshape(-1, stride)[:, voff]
                    for k in range(1, len(poly) - 1):
                        tris.append((poly[0], poly[k], poly[k + 1]))
            tris = np.asarray(tris, dtype=int).reshape(-1, 3)
            Vs.append(P)
            Fs.append(tris + base)
        if not Vs:
            return None
        return np.vstack(Vs), np.vstack(Fs)

    # ---- scene walk --------------------------------------------------
    def walk(self, node, M, out):
        M = M @ _node_matrix(node)
        for ch in node:
            t = _tag(ch)
            if t == "instance_geometry":
                gm = self.geometry((ch.get("url") or "").lstrip("#"))
                if gm is not None:
                    V, F = gm
                    Vh = np.hstack([V, np.ones((len(V), 1))]) @ M.T
                    out.append((Vh[:, :3], F))
            elif t == "instance_node":
                tgt = self.ref(ch.get("url"))
                if tgt is not None:
                    self.walk(tgt, M, out)
            elif t == "node":
                self.walk(ch, M, out)

    def scene(self):
        out = []
        vs = self.root.find(f"{NS}library_visual_scenes")
        if vs is None:
            return out
        for sc in vs.findall(f"{NS}visual_scene"):
            for n in sc.findall(f"{NS}node"):
                self.walk(n, np.eye(4), out)
        return out


def load(path, weld=1e-7):
    """Read a .dae. Returns (V, F) in metres, Z-up."""
    doc = _Doc(path)
    parts = doc.scene()
    if not parts:
        # No usable visual scene: fall back to every geometry in the library.
        lg = doc.root.find(f"{NS}library_geometries")
        if lg is not None:
            for g in lg.findall(f"{NS}geometry"):
                gm = doc.geometry(g.get("id"))
                if gm is not None:
                    parts.append(gm)
    if not parts:
        raise ValueError(f"no geometry in {path}")

    off, Vs, Fs = 0, [], []
    for V, F in parts:
        Vs.append(V)
        Fs.append(F + off)
        off += len(V)
    V = np.vstack(Vs) * doc.unit
    F = np.vstack(Fs)

    if doc.up == "Y_UP":            # COLLADA Y-up -> Z-up
        V = V[:, [0, 2, 1]]
        V[:, 1] *= -1.0
    elif doc.up == "X_UP":
        V = V[:, [1, 0, 2]]
        V[:, 0] *= -1.0

    if weld:
        V, F = _weld(V, F, weld)
    return V, F


def _weld(V, F, tol):
    """Merge coincident vertices and drop degenerate faces."""
    q = np.round(V / tol).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    V2 = V[first]
    F2 = inv[F]
    ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    return V2, F2[ok]


def decimate(mesh, grid):
    """Vertex-clustering decimation: quantise to `grid` (model units) and weld.

    Keeps the silhouette, which is all the line-art renderer needs, and cuts
    the triangle count by an order of magnitude on these CAD exports.
    """
    V, F = mesh
    q = np.round(V / grid)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    # Snapped positions read cleaner than cluster centroids on machined parts.
    V2 = q[first] * grid
    F2 = inv[F]
    ok = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    F2 = F2[ok]
    # Drop zero-area slivers the snap created.
    T = V2[F2]
    a = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    F2 = F2[a > (grid * grid * 1e-3)]
    used = np.unique(F2)
    remap = np.zeros(len(V2), dtype=int)
    remap[used] = np.arange(len(used))
    return V2[used], remap[F2]
