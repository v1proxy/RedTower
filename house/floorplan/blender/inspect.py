import bpy, collections, re, json, sys, mathutils
out_path = sys.argv[sys.argv.index('--')+1]
sc = bpy.context.scene
objs = list(bpy.data.objects)
types = collections.Counter(o.type for o in objs)
def tris(o):
    if o.type != 'MESH' or o.data is None: return 0
    return sum(len(p.vertices)-2 for p in o.data.polygons)
meshes = [o for o in objs if o.type == 'MESH']
T = {o.name: tris(o) for o in meshes}
def walk(c, d=0, out=None):
    out = [] if out is None else out
    out.append(('  '*d) + c.name + ' [%d obj, %d tri, hide_render=%s]' % (len(c.objects), sum(T.get(o.name,0) for o in c.objects), c.hide_render))
    for ch in c.children: walk(ch, d+1, out)
    return out
stems = collections.Counter(re.sub(r'[\.\d_ ]+$', '', o.name) for o in objs)
big = sorted(meshes, key=lambda o: T[o.name], reverse=True)[:30]
mins=[1e9]*3; maxs=[-1e9]*3
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3): mins[i]=min(mins[i],w[i]); maxs[i]=max(maxs[i],w[i])
res = {
 'version': bpy.app.version_string,
 'scenes': [s.name for s in bpy.data.scenes],
 'units': [sc.unit_settings.system, sc.unit_settings.length_unit, sc.unit_settings.scale_length],
 'n_objects': len(objs), 'types': dict(types), 'total_tris': sum(T.values()),
 'bbox': [mins, maxs],
 'collections': walk(sc.collection)[:120],
 'name_stems': stems.most_common(80),
 'biggest': [(o.name, T[o.name], [m.name for m in o.data.materials if m][:3], [round(v,2) for v in o.dimensions], o.parent.name if o.parent else None) for o in big],
 'n_meshdata': len(bpy.data.meshes),
 'n_materials': len(bpy.data.materials), 'materials': [m.name for m in bpy.data.materials][:150],
 'images': [(i.name, list(i.size), i.filepath, i.packed_file is not None) for i in bpy.data.images][:60],
 'lights': [(o.name, o.data.type, [round(v,2) for v in o.matrix_world.translation]) for o in objs if o.type == 'LIGHT'][:80],
 'cameras': [o.name for o in objs if o.type == 'CAMERA'],
 'empties': [o.name for o in objs if o.type == 'EMPTY'][:60],
 'custom_props_sample': [(o.name, {k: str(o[k])[:60] for k in o.keys()}) for o in objs[:5000] if len(o.keys())][:30],
 'modifiers': collections.Counter(m.type for o in objs for m in getattr(o,'modifiers',[])).most_common(),
}
json.dump(res, open(out_path, 'w'), indent=1, default=str)
print('WROTE', out_path)
