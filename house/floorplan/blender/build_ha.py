# Red Tower -> Home Assistant floor3d GLB builder (runs inside Blender 5.x, background)
import bpy, bmesh, math, json, sys, os, time
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
OUT_DIR = args[0]
os.makedirs(OUT_DIR, exist_ok=True)
T0 = time.time()
def log(*a):
    print('[%7.1fs]' % (time.time() - T0), *a, flush=True)

FT2CM = 30.48
BANDS = [(-1e9, 4.0), (4.0, 13.0), (13.0, 22.0), (22.0, 1e9)]   # feet, Z-up: plan cut 4 ft above each floor (0 / 9 / 18)
EAST_X = -19.6                    # east of this, everything above L2 belongs to the roof level
FOOT = (-42.8, 0.9, -0.4, 20.2)   # building footprint x0,x1,y0,y1
STAIR = (-26.3, -16.2, 9.7, 19.6)
LEVEL_FLOOR = [0.0, 9.0, 18.0, 26.0]

def srgb2lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]

PAL = {
 'wall': ('#E4DED4', .9, 0, 1), 'floor': ('#B4936F', .8, 0, 1), 'cut': ('#2A2A2A', 1, 0, 1),
 'clad_red': ('#9B1C1C', .55, .25, 1), 'clad_grey': ('#5F6368', .5, .3, 1), 'clad_white': ('#E9E9E5', .6, 0, 1),
 'glass': ('#A9CFE0', .05, 0, .28), 'frame': ('#D9D3C7', .6, 0, 1), 'metal': ('#4A4D50', .45, .6, 1),
 'casework': ('#EEECE7', .6, 0, 1), 'counter': ('#353535', .4, 0, 1), 'appliance': ('#A9AEB3', .35, .7, 1),
 'sanitary': ('#F5F3EF', .25, 0, 1), 'furniture': ('#C4A27A', .7, 0, 1), 'fixture': ('#8F9194', .5, .3, 1),
 'fixture_light': ('#FFF6E0', .4, 0, 1), 'skylight': ('#3B3F45', .5, .3, 1),
 'site_ground': ('#2A2E28', 1, 0, 1), 'site_paving': ('#5C5A55', .95, 0, 1), 'site_fence': ('#6E5A44', .9, 0, 1),
 'room': ('#B4936F', .8, 0, 1), 'lightdisc': ('#FFF1CC', .5, 0, 1), 'status': ('#3FA34D', .5, 0, 1),
 'device': ('#2B2B2B', .4, .2, 1), 'drop': ('#FF00FF', 1, 0, 1),
}
MATMAP = {
 'Gypsum_Wall_Board': 'wall', 'Default_Wall': 'wall', 'Ceiling_Paint': 'wall', 'Softwood,_Lumber': 'wall', 'Wood_Stud': 'wall',
 'Default_Floor': 'floor', 'Concrete,_Cast-in-Place_gray': 'floor',
 'Steel_ASTM_A36': 'metal', 'Default': 'appliance',
 'Corrugated_Metal_Red': 'clad_red', 'Corrugated_Metal_Grey': 'clad_grey', 'Clad_-_White': 'clad_white',
 'Aluminium_-_FAKRO_-_RAL7016_-_Panel': 'skylight',
 'Aluminium_-_FAKRO_-_RAL7047_-_Actuators': 'drop', 'Aluminium_-_FAKRO_-_RAL7047_-_Guide_rail': 'drop',
 'Aluminium_-_FAKRO_-_RAL9005_-_Bottom_profile': 'drop', 'Rubber_-_FAKRO_-_RAL9005_-_Seal': 'drop',
 'Aluminum': 'drop', 'Cabinets_-_Handles': 'drop',
 'Glass': 'glass', 'Glass,_White,_High_Luminance': 'fixture_light', 'Appliance_-_Window': 'glass',
 'Laminate,_Ivory,_Matte': 'frame', 'Door_-_Frame': 'frame', 'Metal_-_Paint_Finish_-_Grey': 'metal',
 'Laminate,_Linen,_Matte': 'casework', 'Cabinets': 'casework', 'Counter_Top': 'counter',
 'Appliance_-_Stainless_Steel': 'appliance', 'Steel,_Polished': 'appliance', 'Appliance_-_Bronze': 'appliance',
 'Plastic,_Opaque_White': 'appliance', 'Steel,_Paint_Finish,_Ivory,_Glossy': 'appliance',
 'Steel,_Chrome_Plated': 'metal', 'Porcelain,_Ivory': 'sanitary', 'Porcelain,_Linen': 'sanitary',
 'Birch': 'furniture', 'Textile_-_Bamboo_Weave': 'furniture', 'Wood_-_Birch': 'site_fence', 'Chainlink': 'metal',
 'MATERIAL_NOT_DEFINED': 'fixture',
}
CAPKEYS = {'wall', 'floor', 'clad_red', 'clad_grey', 'clad_white', 'casework'}
DISSOLVE_ONLY = {'wall', 'floor', 'cut', 'clad_red', 'clad_grey', 'clad_white', 'glass', 'counter', 'site_ground', 'site_paving', 'site_fence'}
CAPS = {'frame': 8000, 'casework': 8000, 'appliance': 6000, 'sanitary': 3500, 'furniture': 3000, 'fixture': 6000,
        'metal': 3500, 'skylight': 2500, 'fixture_light': 400}
SMOOTH = {'sanitary', 'appliance', 'fixture', 'furniture'}

# ---------------------------------------------------------------- materials
PM = {}
for k, (hx, rough, metal, alpha) in PAL.items():
    m = bpy.data.materials.new('rt_' + k)
    try:
        m.use_nodes = True
    except Exception:
        pass
    col = srgb2lin(hx)
    m.diffuse_color = (*col, alpha)
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Alpha'].default_value = alpha
    if alpha < 1:
        for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
            try: setattr(m, attr, val)
            except Exception: pass
    m.use_backface_culling = (k == 'lightdisc')
    PM[k] = m

coll = bpy.data.collections.get('Collection') or bpy.context.scene.collection
for o in list(bpy.data.objects):
    if o.type != 'MESH':
        bpy.data.objects.remove(o)

def vco(me):
    a = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', a); return a.reshape(-1, 3)

# ---------------------------------------------------------------- classify + remap
objs = []; dead_objs = []
for o in list(bpy.data.objects):
    me = o.data
    if len(me.polygons) == 0:
        dead_objs.append(o); continue
    if o.data.users > 1:
        o.data = o.data.copy()
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    objs.append(o)
bpy.data.batch_remove(dead_objs)
log('meshes', len(objs), 'empty removed', len(dead_objs))

# per-object overrides decided while original material names are still visible
ZR = {}; overrides = []; noslot = []
for o in objs:
    me = o.data
    co = vco(me); mn = co.min(0); mx = co.max(0); c = (mn + mx) / 2
    ZR[o.name] = (float(mn[2]), float(mx[2]))
    outside = not (FOOT[0] < c[0] < FOOT[1] and FOOT[2] < c[1] < FOOT[3])
    exceeds = (mn[0] < FOOT[0] - 3) or (mx[0] > FOOT[1] + 3) or (mn[1] < FOOT[2] - 3) or (mx[1] > FOOT[3] + 3)
    site = mx[2] < 6 and (outside or exceeds)
    in_stair = STAIR[0] <= mn[0] and mx[0] <= STAIR[1] and STAIR[2] <= mn[1] and mx[1] <= STAIR[3]
    if len(me.materials) == 0:
        noslot.append(o); continue
    if not (site or in_stair):
        continue
    for i, m in enumerate(me.materials):
        nm = m.name if m else 'MATERIAL_NOT_DEFINED'
        k = MATMAP.get(nm, 'fixture')
        if site and k not in ('drop', 'appliance'):
            overrides.append((o, i, 'site_ground' if nm == 'Default_Floor' else ('site_paving' if k == 'floor' else 'site_fence')))
        elif in_stair and nm == 'MATERIAL_NOT_DEFINED':
            overrides.append((o, i, 'floor'))
log('overrides', len(overrides), 'no-slot', len(noslot))
# bulk remap of the 41 Revit materials onto the palette (one call per material, not per object)
for m in [m for m in bpy.data.materials if not m.name.startswith('rt_')]:
    m.user_remap(PM[MATMAP.get(m.name, 'fixture')])
for o, i, k in overrides:
    o.data.materials[i] = PM[k]
for o in noslot:
    o.data.materials.append(PM['fixture'])
stats = {'drop_faces': 0}
emptied = []
for o in objs:
    me = o.data
    dropidx = {i for i, m in enumerate(me.materials) if m == PM['drop']}
    if not dropidx:
        continue
    bm = bmesh.new(); bm.from_mesh(me)
    dead = [f for f in bm.faces if f.material_index in dropidx]
    stats['drop_faces'] += len(dead)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free()
    if len(me.polygons) == 0:
        emptied.append(o)
eset = set(emptied)
objs = [o for o in objs if o not in eset]
bpy.data.batch_remove(emptied)
log('classified; dropped faces', stats['drop_faces'], 'emptied', len(emptied), 'remaining objs', len(objs))

# ---------------------------------------------------------------- cut into level bands
def cut(ob, lo, hi, capidx):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for z, keep_above in ((lo, True), (hi, False)):
        if abs(z) > 1e8: continue
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        r = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=(0, 0, z), plane_no=(0, 0, 1),
                                   clear_inner=keep_above, clear_outer=not keep_above)
        if capidx is not None:
            edges = [e for e in r['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_valid and e.is_boundary]
            if edges:
                try:
                    f = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
                    for fa in f['faces']: fa.material_index = capidx
                except Exception as ex:
                    pass
    bm.to_mesh(ob.data); bm.free()

groups = {0: [], 1: [], 2: [], 3: []}
def level_of(ob, b):
    if b == 2:
        co = vco(ob.data)
        if len(co) and (co[:, 0].min() + co[:, 0].max()) / 2 > EAST_X:
            return 3
    return b

ncut = 0; cut_src = []
for o in list(objs):
    z0, z1 = ZR[o.name]
    bands = [i for i, (lo, hi) in enumerate(BANDS) if z1 > lo + 0.02 and z0 < hi - 0.02]
    if not bands:
        zc = (z0 + z1) / 2
        bands = [max(i for i, (lo, hi) in enumerate(BANDS) if zc >= lo)]
    if len(bands) == 1:
        groups[level_of(o, bands[0])].append(o); continue
    ncut += 1
    capidx = None
    keys = [s.material.name[3:] for s in o.material_slots]
    if any(k in CAPKEYS for k in keys):
        o.data.materials.append(PM['cut']); capidx = len(o.data.materials) - 1
    for b in bands:
        c = o.copy(); c.data = o.data.copy(); coll.objects.link(c)
        cut(c, BANDS[b][0], BANDS[b][1], capidx)
        if len(c.data.polygons) == 0:
            cut_src.append(c); continue
        groups[level_of(c, b)].append(c)
    cut_src.append(o)
bpy.data.batch_remove(cut_src)
log('cut objects', ncut, {k: len(v) for k, v in groups.items()})

# ---------------------------------------------------------------- join per level, split by palette material
def join(obs):
    # numpy concatenation; bpy.ops.object.join is ~0.15 s per object on this file
    keys = list(PAL.keys())
    kidx = {'rt_' + k: i for i, k in enumerate(keys)}
    fx = kidx['rt_fixture']
    V = []; LV = []; LS = []; MI = []; voff = 0; loff = 0
    for o in obs:
        me = o.data
        nv = len(me.vertices); npo = len(me.polygons); nl = len(me.loops)
        if npo == 0: continue
        co = np.empty(nv * 3, np.float32); me.vertices.foreach_get('co', co)
        lv = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
        ls = np.empty(npo, np.int32); me.polygons.foreach_get('loop_start', ls)
        mi = np.empty(npo, np.int32); me.polygons.foreach_get('material_index', mi)
        slot = np.array([kidx.get(m.name, fx) if m else fx for m in me.materials] or [fx], np.int32)
        mi = slot[np.clip(mi, 0, len(slot) - 1)]
        V.append(co); LV.append(lv + voff); LS.append(ls + loff); MI.append(mi)
        voff += nv; loff += nl
    co = np.concatenate(V); lv = np.concatenate(LV); ls = np.concatenate(LS); mi = np.concatenate(MI)
    me = bpy.data.meshes.new('joined')
    me.vertices.add(len(co) // 3); me.vertices.foreach_set('co', co)
    me.loops.add(len(lv)); me.loops.foreach_set('vertex_index', lv)
    me.polygons.add(len(ls)); me.polygons.foreach_set('loop_start', ls)
    for k in keys:
        me.materials.append(PM[k])
    me.polygons.foreach_set('material_index', mi)
    me.update(calc_edges=True)
    ob = bpy.data.objects.new('joined', me); coll.objects.link(ob)
    bpy.data.batch_remove(obs)
    return ob

def split_by_material(J, lvl):
    me = J.data
    used = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', used)
    used = set(np.unique(used).tolist())
    bykey = {}
    for i, m in enumerate(me.materials):
        if m and i in used: bykey.setdefault(m.name[3:], set()).add(i)
    out = []
    for key, idxs in bykey.items():
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in idxs], context='FACES')
        if len(bm.faces) == 0:
            bm.free(); continue
        for f in bm.faces: f.material_index = 0
        name = 'lvl%03d%s_l%d' % (lvl, key, lvl + 1)
        nm = bpy.data.meshes.new(name + '_geo'); bm.to_mesh(nm); bm.free()
        nm.materials.append(PM[key])
        ob = bpy.data.objects.new(name, nm); coll.objects.link(ob); ob['key'] = key; ob['lvl'] = lvl
        out.append(ob)
    bpy.data.objects.remove(J)
    return out

def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)

def collapse(ob, ratio):
    mod = ob.modifiers.new('dec', 'DECIMATE'); mod.decimate_type = 'COLLAPSE'; mod.ratio = max(0.01, min(1.0, ratio))
    dg = bpy.context.evaluated_depsgraph_get()
    newme = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); old = ob.data; ob.data = newme; newme.name = old.name; bpy.data.meshes.remove(old)

report = {}
final = []
for lvl in range(4):
    obs = groups[lvl]
    if not obs: continue
    J = join(obs)
    log('level', lvl, 'joined tris', tri_count(J.data))
    parts = split_by_material(J, lvl)
    for ob in parts:
        key = ob['key']; me = ob.data
        t0 = tri_count(me)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.003)
        try:
            bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts, edges=bm.edges, delimit={'NORMAL'})
        except Exception as ex:
            log('dissolve fail', ob.name, ex)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < 1e-7], context='FACES')
        bm.to_mesh(me); bm.free()
        t1 = tri_count(me)
        if key in CAPS and t1 > CAPS[key]:
            collapse(ob, CAPS[key] / t1)
        me = ob.data
        if key in SMOOTH:
            try:
                me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(35))
            except Exception:
                pass
        else:
            me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
        report[ob.name] = [t0, t1, tri_count(me)]
        final.append(ob)
    log('level', lvl, 'parts', [p.name for p in parts])

# ---------------------------------------------------------------- bindable objects (feet, before scaling)
def make_mesh(name, verts, faces, matkey, lvl):
    full = 'lvl%03d%s' % (lvl, name)
    me = bpy.data.meshes.new(full + '_geo'); me.from_pydata(verts, [], faces); me.update()
    me.materials.append(PM[matkey])
    me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
    ob = bpy.data.objects.new(full, me); coll.objects.link(ob)
    report[full] = [len(faces)] * 3
    return ob

def plane(name, poly, z, matkey, lvl):
    return make_mesh(name, [(x, y, z) for x, y in poly], [list(range(len(poly)))], matkey, lvl)

def box(name, x0, x1, y0, y1, z0, z1, matkey, lvl):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return make_mesh(name, v, f, matkey, lvl)

def disc(name, cx, cy, z, r, matkey, lvl, n=16, down=True):
    v = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]
    f = [list(range(n))[::-1]] if down else [list(range(n))]
    return make_mesh(name, v, f, matkey, lvl)

def puck(name, cx, cy, z, r, h, matkey, lvl, n=20):
    v = []
    for zz in (z, z + h):
        v += [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), zz) for i in range(n)]
    f = [list(range(n))[::-1], list(range(n, 2 * n))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return make_mesh(name, v, f, matkey, lvl)

def rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

ROOMS = [  # id, level, polygon, ceiling(ft)
 ('guest_room', 0, rect(-41.8, -35.5, 0.5, 8.2), 8.0),
 ('studio', 0, rect(-42.0, -31.9, 8.8, 19.3), 8.5),
 ('bath_l1', 0, rect(-31.5, -26.7, 7.8, 14.3), 8.5),
 ('entry', 0, rect(-26.4, -19.9, 0.5, 9.8), 8.0),
 ('garage', 0, rect(-19.3, 0.3, 0.5, 19.5), 8.5),
 ('kitchen', 1, rect(-42.0, -26.7, 0.5, 19.3), 17.0),
 ('hall_l2', 1, rect(-26.4, -19.6, 4.4, 19.3), 17.0),
 ('living_room', 1, [(-19.4, 0.5), (0.0, 0.5), (0.0, 19.3), (-16.1, 19.3), (-16.1, 9.8), (-19.4, 9.8)], 19.3),
 ('bedroom', 2, rect(-41.8, -27.2, 0.5, 13.8), 26.0),
 ('bath_l3', 2, rect(-41.8, -36.1, 14.4, 19.3), 26.0),
 ('closet_l3', 2, rect(-35.4, -29.0, 14.2, 17.8), 26.0),
 ('office', 2, rect(-26.4, -19.9, 0.5, 5.5), 26.0),
]
LIGHTS = {'kitchen': (-34.3, 12.45), 'living_room': (-9.0, 10.0), 'hall_l2': (-21.25, 6.95)}
anchors = {}
for rid, lvl, poly, ceil in ROOMS:
    z = LEVEL_FLOOR[lvl] + 0.1
    plane('room_' + rid, poly, z, 'room', lvl)
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    cx, cy = LIGHTS.get(rid, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    disc('light_' + rid, cx, cy, ceil - 0.15, 0.35, 'lightdisc', lvl)
    anchors[rid] = {'level': lvl, 'center_ft': [cx, cy], 'floor_ft': LEVEL_FLOOR[lvl], 'ceiling_ft': ceil}
# status strips and devices
box('door_balcony', -42.95, -42.05, 6.3, 13.9, 9.0, 9.12, 'status', 1)
box('window_guest_room', -41.75, -41.35, 0.7, 3.0, 0.0, 0.12, 'status', 0)
puck('vacuum_sagan', -2.0, 18.3, 9.02, 0.55, 0.3, 'device', 1)
puck('vacuum_asimov', -40.6, 12.6, 18.02, 0.55, 0.3, 'device', 2)

# ---------------------------------------------------------------- scale to centimetres
S = Matrix.Scale(FT2CM, 4)
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        ob.data.transform(S)
log('scaled to cm')

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'redtower_ha.blend'))
glb = os.path.join(OUT_DIR, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
total = sum(v[2] for v in report.values())
json.dump({'objects': report, 'total_tris': total, 'anchors': anchors, 'glb_bytes': os.path.getsize(glb)},
          open(os.path.join(OUT_DIR, 'build_report.json'), 'w'), indent=1)
log('EXPORTED', glb, os.path.getsize(glb), 'bytes', total, 'tris')
