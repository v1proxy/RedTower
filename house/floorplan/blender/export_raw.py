import bpy, numpy as np, sys, json, os
out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(os.path.dirname(out), exist_ok=True)
objs = [o for o in bpy.data.objects if o.type == 'MESH']
mat_names = [m.name for m in bpy.data.materials]
mat_index = {n: i for i, n in enumerate(mat_names)}
V = []; T = []; M = []; O = []
voff = 0
names = []
for oi, o in enumerate(objs):
    me = o.data
    try:
        me.calc_loop_triangles()
    except Exception:
        pass
    nv = len(me.vertices); nt = len(me.loop_triangles)
    co = np.empty(nv * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3).astype(np.float64)
    mw = np.array(o.matrix_world, dtype=np.float64)
    co = (co @ mw[:3, :3].T + mw[:3, 3]).astype(np.float32)
    tri = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', tri)
    mi = np.empty(nt, np.int32); me.loop_triangles.foreach_get('material_index', mi)
    slot_map = np.array([mat_index.get(s.material.name, -1) if s.material else -1 for s in o.material_slots] or [-1], np.int32)
    gm = slot_map[np.clip(mi, 0, len(slot_map) - 1)]
    V.append(co); T.append(tri.reshape(-1, 3) + voff); M.append(gm); O.append(np.full(nt, oi, np.int32))
    voff += nv; names.append(o.name)
np.savez_compressed(out, V=np.concatenate(V), T=np.concatenate(T), M=np.concatenate(M).astype(np.int16), O=np.concatenate(O))
mats = []
for m in bpy.data.materials:
    d = {'name': m.name, 'diffuse': list(m.diffuse_color)}
    try:
        n = m.node_tree.nodes.get('Principled BSDF') if m.node_tree else None
        if n:
            d['base'] = list(n.inputs['Base Color'].default_value)
            d['alpha'] = n.inputs['Alpha'].default_value
            d['metal'] = n.inputs['Metallic'].default_value
            d['rough'] = n.inputs['Roughness'].default_value
            d['base_linked'] = n.inputs['Base Color'].is_linked
    except Exception as e:
        d['err'] = str(e)
    d['blend'] = getattr(m, 'surface_render_method', None)
    mats.append(d)
json.dump({'objects': names, 'materials': mats}, open(out.replace('.npz', '.json'), 'w'))
print('DONE', len(names), voff, sum(len(t) for t in T))
