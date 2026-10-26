# Exterior trim colours (Vittorio, 2026-10-25): parapet (inner faces + coping), entry door, awning and downspouts red;
# every window frame aluminium; wall faces left showing on the outside (east roof edge) take the nearest cladding colour.
# Parts are found by geometry: the Revit export has no family names. Runs on redtower_ha.blend (cm, Z up). Idempotent.
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT = sys.argv[sys.argv.index('--') + 1]
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
def mat(name, hx, rough):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; c = lin(hx)
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0; m.diffuse_color = (*c, 1)
    return m
RED = bpy.data.materials['rt_clad_red']; GREY = bpy.data.materials['rt_clad_grey']
ALU = mat('rt_window_alu', '#B7BBBF', 0.45)
FRAME = bpy.data.materials['rt_frame']; WALL = bpy.data.materials['rt_wall']

def slot(me, m):
    for i, x in enumerate(me.materials):
        if x == m: return i
    me.materials.append(m); return len(me.materials) - 1

def parts(bm):
    bm.faces.ensure_lookup_table(); seen = set(); out = []
    for f in bm.faces:
        if f.index in seen: continue
        stack = [f]; comp = []; seen.add(f.index)
        while stack:
            g = stack.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: seen.add(h.index); stack.append(h)
        vs = np.array([v.co[:] for g in comp for v in g.verts])
        out.append((comp, vs.min(0), vs.max(0)))
    return out

def inside(mn, mx, b):  # b = (x0, x1, y0, y1, z0, z1)
    return b[0] <= mn[0] and mx[0] <= b[1] and b[2] <= mn[1] and mx[1] <= b[3] and b[4] <= mn[2] and mx[2] <= b[5]

DOOR = (930, 1045, -722, -690, 25, 245)
AWNING = (905, 1070, -815, -714, 240, 320)
PIPE_X = [(378, 396), (1076, 1094)]
PIPE_Y = (-731, -713)

# glass part boxes (all levels) for window-frame detection
G = []
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('lvl') and o.data.materials and o.data.materials[0] and o.data.materials[0].name == 'rt_glass':
        bm = bmesh.new(); bm.from_mesh(o.data)
        G += [(mn, mx) for _, mn, mx in parts(bm)]; bm.free()
Gmn = np.array([g[0] for g in G]); Gmx = np.array([g[1] for g in G])

stats = {}
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.name[:3] == 'lvl' and o.name[6:].startswith('frame_l')]:
    me = o.data; iF = slot(me, FRAME); iR = slot(me, RED); iA = slot(me, ALU)
    bm = bmesh.new(); bm.from_mesh(me)
    for comp, mn, mx in parts(bm):
        k = iF
        pipe_col = any(a - 2 <= mn[0] and mx[0] <= b + 2 for a, b in PIPE_X) and PIPE_Y[0] <= mn[1] and mx[1] <= PIPE_Y[1]
        pipe_head = (868 <= mn[2] and mx[2] <= 892 and PIPE_Y[0] <= mn[1] and mx[1] <= PIPE_Y[1]
                     and any(mn[0] <= b and mx[0] >= a for a, b in PIPE_X))
        if inside(mn, mx, DOOR) or inside(mn, mx, AWNING) or pipe_col or pipe_head or mn[2] > 1040:
            k = iR
        elif len(G) and np.any(np.all((Gmn - 6 <= mx) & (Gmx + 6 >= mn), axis=1)):
            k = iA
        for f in comp: f.material_index = k
        stats[(o.name, k)] = stats.get((o.name, k), 0) + 1
    bm.to_mesh(me); bm.free()

# ---- wall faces that are seen from outside take the nearest facade cladding colour
def bvh_of(objs, facade_only=False):
    V = []; F = []
    for o in objs:
        me = o.data; base = len(V)
        V += [v.co.copy() for v in me.vertices]
        for p in me.polygons:
            if facade_only and abs(p.normal.z) > 0.5: continue
            F.append([base + i for i in p.vertices])
    return BVHTree.FromPolygons(V, F) if F else None
skip = ('room_', 'light_', 'vacuum_', 'door_balcony', 'window_guest_room', 'car_')
occ = [o for o in bpy.data.objects if o.type == 'MESH' and o.name[:3] == 'lvl' and not o.name[6:].startswith(skip)]
OCC = bvh_of(occ)
clad = lambda key: [o for o in bpy.data.objects if o.type == 'MESH' and o.name[:3] == 'lvl' and o.data.materials and o.data.materials[0] and o.data.materials[0].name == key]
BR = bvh_of(clad('rt_clad_red'), True); BG = bvh_of(clad('rt_clad_grey'), True)
UP20 = math.tan(math.radians(20)); UP45 = 1.0
def escapes(c, d):
    d = d.normalized(); return OCC.ray_cast(c + d * 1.5, d)[0] is None
# split wall faces where roofs cross them, so parapet faces above a roof are separate from the room walls below
def roof_planes():
    out = {}
    for o in clad('rt_clad_grey'):
        for p in o.data.polygons:
            if p.normal.z < 0.9 or p.area < 1: continue
            n = p.normal.normalized(); d = n.dot(p.center)
            key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), round(d / 5))
            vs = [o.data.vertices[i].co for i in p.vertices]
            e = out.setdefault(key, [0.0, n, p.center.copy(), [1e9, 1e9], [-1e9, -1e9]])
            e[0] += p.area; e[3] = [min(e[3][0], *(v.x for v in vs)), min(e[3][1], *(v.y for v in vs))]
            e[4] = [max(e[4][0], *(v.x for v in vs)), max(e[4][1], *(v.y for v in vs))]
    return [e for e in out.values() if e[0] > 5e4]
PLANES = roof_planes()
print('ROOF PLANES', [(round(e[0] / 1e4, 1), [round(c) for c in e[2]], [round(c, 2) for c in e[1]]) for e in PLANES])
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.name[:3] == 'lvl' and o.name[6:].startswith('wall_l')]:
    bm = bmesh.new(); bm.from_mesh(o.data); cuts = 0
    for area, n, co, mn, mx in PLANES:
        fs = []
        for f in bm.faces:
            vs = [v.co for v in f.verts]
            if max(v.x for v in vs) < mn[0] - 60 or min(v.x for v in vs) > mx[0] + 60 or max(v.y for v in vs) < mn[1] - 60 or min(v.y for v in vs) > mx[1] + 60: continue
            s = [n.dot(v - co) for v in vs]
            if min(s) < -2 and max(s) > 2: fs.append(f)
        if fs:
            geom = list(set(fs) | {e for f in fs for e in f.edges} | {v for f in fs for v in f.verts})
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=n); cuts += len(fs)
    bm.to_mesh(o.data); bm.free(); print('BISECT', o.name, cuts)
nwall = {}
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.name[:3] == 'lvl' and o.name[6:].startswith('wall_l')]:
    me = o.data; iW = slot(me, WALL); iR = slot(me, RED); iG = slot(me, GREY)
    for p in me.polygons:
        if p.material_index not in (iW, iR, iG): continue
        c = p.center; n = p.normal; nh = Vector((n.x, n.y, 0))
        ext = False
        if nh.length < 0.3:
            ext = n.z > 0.7 and escapes(c, Vector((0, 0, 1)))
        else:
            nh.normalize()
            for s in (1, -1):
                h = nh * s
                if escapes(c, h + Vector((0, 0, UP20))) or escapes(c, h + Vector((0, 0, UP45))):
                    ext = True; break
        if not ext and p.area < 2500 and (BR or BG):
            # reveal of a small opening through a clad wall (roof scuppers): perpendicular to the cladding, inside the wall
            # thickness, not next to glass (window reveals stay as they are)
            near = [B.find_nearest(c) for B in (BR, BG) if B]
            near = min([x for x in near if x[0] is not None], key=lambda x: x[3], default=None)
            if near is not None and abs(n.dot(near[1])) < 0.3:
                def dist(B, co):
                    r = B.find_nearest(co); return 1e9 if r[0] is None else r[3]
                dmax = max(min(dist(B, me.vertices[i].co) for B in (BR, BG) if B) for i in p.vertices)
                vs = np.array([me.vertices[i].co[:] for i in p.vertices]); mn, mx = vs.min(0), vs.max(0)
                glassy = len(G) and np.any(np.all((Gmn - 10 <= mx) & (Gmx + 10 >= mn), axis=1))
                ext = dmax < 30 and not glassy
        k = iW
        if ext:
            dr = BR.find_nearest(c)[3] if BR else None; dg = BG.find_nearest(c)[3] if BG else None
            dr = 1e9 if dr is None else dr; dg = 1e9 if dg is None else dg
            if min(dr, dg) < 150: k = iR if dr <= dg else iG
        p.material_index = k
        nwall[(o.name, k)] = nwall.get((o.name, k), 0) + 1
for k in sorted(stats): print('FRAME', k, stats[k])
for k in sorted(nwall): print('WALL', k, nwall[k])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb))
