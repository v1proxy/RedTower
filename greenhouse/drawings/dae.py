"""Minimal COLLADA reader: vertices and triangles, with node transforms applied.

Written because the container has no package index, so trimesh/pycollada are not
installable. Handles the subset the Elephant Robotics meshes actually use:
float_array sources, <vertices> indirection, <triangles> and <polylist>, and
<matrix>/<translate>/<rotate>/<scale> node transforms in the visual scene.
"""
import numpy as np
import xml.etree.ElementTree as ET

NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}


def _floats(el):
    return np.fromstring(el.text.replace("\n", " "), sep=" ")


def _ints(el):
    return np.fromstring(el.text.replace("\n", " "), sep=" ", dtype=np.int64)


def _node_matrix(node):
    """Compose a node's local transform from its ordered transform elements."""
    M = np.eye(4)
    for ch in node:
        tag = ch.tag.split("}")[-1]
        if tag == "matrix":
            M = M @ _floats(ch).reshape(4, 4)
        elif tag == "translate":
            t = _floats(ch)
            T = np.eye(4); T[:3, 3] = t
            M = M @ T
        elif tag == "scale":
            s = _floats(ch)
            S = np.eye(4); S[0, 0], S[1, 1], S[2, 2] = s
            M = M @ S
        elif tag == "rotate":
            v = _floats(ch)
            axis, ang = v[:3], np.radians(v[3])
            if np.linalg.norm(axis) > 0:
                axis = axis / np.linalg.norm(axis)
                x, y, z = axis
                c, s = np.cos(ang), np.sin(ang)
                R = np.array([
                    [c + x*x*(1-c),   x*y*(1-c)-z*s, x*z*(1-c)+y*s],
                    [y*x*(1-c)+z*s,   c + y*y*(1-c), y*z*(1-c)-x*s],
                    [z*x*(1-c)-y*s,   z*y*(1-c)+x*s, c + z*z*(1-c)]])
                T = np.eye(4); T[:3, :3] = R
                M = M @ T
    return M


def load(path):
    """Return (vertices Nx3 in metres, triangles Mx3 int) for one .dae file."""
    root = ET.parse(path).getroot()

    unit = root.find(".//c:asset/c:unit", NS)
    scale = float(unit.get("meter", 1.0)) if unit is not None else 1.0
    up = root.findtext(".//c:asset/c:up_axis", default="Y_UP", namespaces=NS).strip()

    # --- geometry id -> (verts, tris) in geometry space
    geoms = {}
    for g in root.findall(".//c:library_geometries/c:geometry", NS):
        mesh = g.find("c:mesh", NS)
        if mesh is None:
            continue
        srcs = {}
        for s in mesh.findall("c:source", NS):
            fa = s.find("c:float_array", NS)
            if fa is None:
                continue
            acc = s.find("c:technique_common/c:accessor", NS)
            stride = int(acc.get("stride", 3)) if acc is not None else 3
            srcs["#" + s.get("id")] = _floats(fa).reshape(-1, stride)

        vmap = {}
        for v in mesh.findall("c:vertices", NS):
            for inp in v.findall("c:input", NS):
                if inp.get("semantic") == "POSITION":
                    vmap["#" + v.get("id")] = srcs[inp.get("source")]

        V, T = None, []
        for prim in list(mesh.findall("c:triangles", NS)) + \
                    list(mesh.findall("c:polylist", NS)) + \
                    list(mesh.findall("c:polygons", NS)):
            inputs = prim.findall("c:input", NS)
            noff = max(int(i.get("offset", 0)) for i in inputs) + 1
            voff, vsrc = 0, None
            for i in inputs:
                if i.get("semantic") == "VERTEX":
                    voff = int(i.get("offset", 0))
                    vsrc = vmap.get(i.get("source"))
                    if vsrc is None:
                        vsrc = srcs.get(i.get("source"))
            if vsrc is None:
                continue
            V = vsrc if V is None else V

            if prim.tag.endswith("polygons"):         # one <p> per polygon
                for pel in prim.findall("c:p", NS):
                    idx = _ints(pel).reshape(-1, noff)[:, voff]
                    for j in range(1, len(idx) - 1):
                        T.append([idx[0], idx[j], idx[j + 1]])
                continue

            p = _ints(prim.find("c:p", NS))
            idx = p.reshape(-1, noff)[:, voff]
            if prim.tag.endswith("polylist"):
                counts = _ints(prim.find("c:vcount", NS))
                k = 0
                for n in counts:                      # fan-triangulate
                    for j in range(1, n - 1):
                        T.append([idx[k], idx[k + j], idx[k + j + 1]])
                    k += n
            else:
                T.extend(idx.reshape(-1, 3).tolist())
        if V is not None and T:
            geoms[g.get("id")] = (V.astype(np.float64), np.asarray(T, dtype=np.int64))

    # --- place every instance found in the visual scene
    out_v, out_t, base = [], [], 0
    by_id = {n.get("id"): n for n in root.iter() if n.tag.endswith("}node") and n.get("id")}

    def walk(node, parent, depth=0):
        nonlocal base
        if depth > 32:                                # guard against cyclic instance_node
            return
        M = parent @ _node_matrix(node)
        for inst in node.findall("c:instance_geometry", NS):
            gid = inst.get("url", "").lstrip("#")
            if gid in geoms:
                V, T = geoms[gid]
                Vh = np.c_[V, np.ones(len(V))] @ M.T
                out_v.append(Vh[:, :3])
                out_t.append(T + base)
                base += len(V)
        for inst in node.findall("c:instance_node", NS):
            tgt = by_id.get(inst.get("url", "").lstrip("#"))
            if tgt is not None:
                walk(tgt, M, depth + 1)
        for ch in node.findall("c:node", NS):
            walk(ch, M, depth + 1)

    scenes = root.findall(".//c:library_visual_scenes/c:visual_scene", NS)
    for sc in scenes:
        for n in sc.findall("c:node", NS):
            walk(n, np.eye(4))

    if not out_v:                                     # no scene graph: take raw geometry
        for V, T in geoms.values():
            out_v.append(V)
            out_t.append(T + base)
            base += len(V)

    V = np.vstack(out_v) * scale
    T = np.vstack(out_t)
    if up.startswith("Y"):                            # bring Y_UP into Z_UP
        V = V[:, [0, 2, 1]]
        V[:, 1] *= -1.0
    elif up.startswith("X"):
        V = V[:, [2, 1, 0]]
        V[:, 0] *= -1.0
    return V, T
