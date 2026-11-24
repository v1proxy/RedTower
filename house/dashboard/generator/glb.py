# Minimal GLB reader: every mesh primitive as (node name, positions, triangle indices), in the file's own frame.
import json, struct, sys
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load(path):
    b = open(path, "rb").read()
    magic, ver, length = struct.unpack_from("<III", b, 0)
    assert magic == 0x46546C67, "not a GLB"
    off, js, bin_ = 12, None, None
    while off < length:
        clen, ctype = struct.unpack_from("<II", b, off)
        chunk = b[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen

    def acc(i):
        a = js["accessors"][i]
        v = js["bufferViews"][a["bufferView"]]
        n, dt = NC[a["type"]], CT[a["componentType"]]
        start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = v.get("byteStride")
        cnt = a["count"]
        if stride and stride != n * np.dtype(dt).itemsize:
            raw = np.frombuffer(bin_, dtype=np.uint8, count=stride * cnt, offset=start).reshape(cnt, stride)
            return raw[:, : n * np.dtype(dt).itemsize].copy().view(dt).reshape(cnt, n)
        return np.frombuffer(bin_, dtype=dt, count=cnt * n, offset=start).reshape(cnt, n) if n > 1 else np.frombuffer(bin_, dtype=dt, count=cnt, offset=start)

    out = []
    for node in js.get("nodes", []):
        if "mesh" not in node:
            continue
        assert not any(k in node for k in ("matrix", "rotation", "scale")), "node transforms present"
        t = np.array(node.get("translation", [0, 0, 0]), dtype=np.float64)
        mesh = js["meshes"][node["mesh"]]
        for prim in mesh["primitives"]:
            if prim.get("mode", 4) != 4:
                continue
            p = acc(prim["attributes"]["POSITION"]).astype(np.float64) + t
            idx = acc(prim["indices"]).astype(np.int64).reshape(-1, 3) if "indices" in prim else np.arange(len(p)).reshape(-1, 3)
            mat = js["materials"][prim["material"]]["name"] if "material" in prim else ""
            out.append((node.get("name", ""), mat, p, idx))
    return js, out


if __name__ == "__main__":
    js, prims = load(sys.argv[1])
    names = [p[0] for p in prims]
    print("nodes with meshes:", len(prims), "triangles:", sum(len(p[3]) for p in prims), "children/scene nodes:", len(js["nodes"]))
    allp = np.vstack([p[2] for p in prims])
    print("bbox min", allp.min(0).round(1), "max", allp.max(0).round(1))
    import collections, re
    pre = collections.Counter(re.sub(r"\d+$", "", n)[:28] for n in names)
    for k, v in sorted(pre.items()):
        print(f"{v:5d}  {k}")
