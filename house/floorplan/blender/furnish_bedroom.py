# Bedroom furniture from Vittorio's photos (2026-10-25): IKEA TARVA queen bed, two bedside tables
# (2020 aluminium extrusion frame, frosted drawers), two Flos Parentesi (red). Runs on redtower_ha.blend (cm).
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
OUT = sys.argv[sys.argv.index('--') + 1]
FT = 30.48
OX, OY, OZ = 1680.5275, -708.9085, 30.48          # finalize.py translation (cm)
def W(x_ft, y_ft, z_ft=18.0):                      # plan feet -> blend cm
    return Vector((x_ft * FT + OX, y_ft * FT + OY, z_ft * FT + OZ))
FLOOR = 18.0
coll = bpy.data.objects['lvl002room_bedroom'].users_collection[0]

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
def mat(name, hx, rough=0.6, back_cull=False):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; c = lin(hx)
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0; m.diffuse_color = (*c, 1); m.use_backface_culling = back_cull
    return m
M = {
 'pine': mat('rt_pine', '#D8B27C', 0.7), 'linen': mat('rt_linen', '#F1F0EC', 0.9),
 'alu': mat('rt_alu', '#BFC3C7', 0.4), 'frosted': mat('rt_frosted', '#DDE2E6', 0.5),
 'red': mat('rt_parentesi_red', '#B3262A', 0.45), 'black': mat('rt_black', '#1E1E1E', 0.5),
 'bulb': mat('rt_bulb', '#FFF4DC', 0.3),
}
for nm in [o.name for o in bpy.data.objects if o.name.startswith(('lvl002bed_bedroom', 'lvl002mattress_bedroom',
            'lvl002nightstand_', 'lvl002parentesi_', 'lvl002light_bedroom_'))]:
    bpy.data.objects.remove(bpy.data.objects[nm])      # idempotent re-run (old lamps would block the ceiling ray cast)

def emit(name, bm, matkey):
    full = 'lvl002' + name
    if full in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[full])
    me = bpy.data.meshes.new(full + '_geo'); bm.to_mesh(me); bm.free()
    me.materials.append(M[matkey]); me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
    ob = bpy.data.objects.new(full, me); coll.objects.link(ob); return ob

def add_box(bm, origin, x0, x1, y0, y1, z0, z1):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r['verts']
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=vs)
    bmesh.ops.translate(bm, vec=origin + Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), verts=vs)

# ---------------------------------------------------------------- TARVA queen: 160 W x 209 L, headboard 92, footboard 32 (cm)
BED_X0, BED_Y0 = -38.8, 0.47                         # headboard against the south wall, west edge 3 ft from the west wall
o = W(BED_X0, BED_Y0)
bm = bmesh.new()
for x0 in (0, 153):                                  # head posts
    add_box(bm, o, x0, x0 + 7, 0, 7, 0, 92)
add_box(bm, o, 0, 160, 1, 6, 84, 92)                 # top rail
for z in (48, 60, 72):                               # horizontal slats
    add_box(bm, o, 7, 153, 2, 5, z, z + 6)
add_box(bm, o, 7, 153, 1, 6, 28, 40)                 # bottom rail
add_box(bm, o, 77, 83, 1.5, 5.5, 40, 84)             # centre divider
for x0 in (0, 153):                                  # foot posts
    add_box(bm, o, x0, x0 + 7, 202, 209, 0, 32)
add_box(bm, o, 7, 153, 203, 207, 16, 32)             # footboard
add_box(bm, o, 0, 3.5, 7, 202, 14, 28); add_box(bm, o, 156.5, 160, 7, 202, 14, 28)   # side rails
emit('bed_bedroom', bm, 'pine')
bm = bmesh.new()
add_box(bm, o, 4, 156, 7, 205, 24, 47)               # mattress
add_box(bm, o, 1, 159, 50, 207, 47, 53)              # duvet
add_box(bm, o, 10, 76, 9, 52, 47, 59); add_box(bm, o, 84, 150, 9, 52, 47, 59)   # pillows
emit('mattress_bedroom', bm, 'linen')

# ---------------------------------------------------------------- bedside tables: 2020 extrusion frame around a MUJI
# PP storage case, shallow, 3 drawers (26 W x 37 D x 32.5 H cm, muji.us). Frame 30 x 41 x 52.5 cm, drawers face the room (north).
CW, CD, CH = 26.0, 37.0, 32.5
FW, FD, Z0 = CW + 4, CD + 4, 18.0                    # outer frame; case sits on the bottom ring at 18 cm (photo: ~17 cm legs)
def nightstand(tag, x_ft):
    o = W(x_ft, 0.5); fr = bmesh.new(); dr = bmesh.new()
    top = Z0 + CH + 2
    for x0, y0 in ((0, 0), (FW - 2, 0), (0, FD - 2), (FW - 2, FD - 2)):
        add_box(fr, o, x0, x0 + 2, y0, y0 + 2, 0, top)   # 2020 posts, TPU feet included
    for z in (Z0 - 2, Z0 + CH):                          # bottom and top rings
        add_box(fr, o, 2, FW - 2, 0, 2, z, z + 2); add_box(fr, o, 2, FW - 2, FD - 2, FD, z, z + 2)
        add_box(fr, o, 0, 2, 2, FD - 2, z, z + 2); add_box(fr, o, FW - 2, FW, 2, FD - 2, z, z + 2)
    add_box(dr, o, 2, 2 + CW, 2, 2 + CD, Z0, Z0 + 1.5)                   # case bottom
    for i in range(3):                                                   # three shallow drawers, fronts to the north
        z0 = Z0 + 1.5 + i * 10.3
        add_box(dr, o, 2.5, 1.5 + CW, 2.5, 2 + CD + 0.5, z0, z0 + 9.8)
    add_box(dr, o, 2, 2 + CW, 2, 2 + CD, Z0 + CH - 0.8, Z0 + CH)        # case top
    emit('nightstand_%s_frame' % tag, fr, 'alu'); emit('nightstand_%s' % tag, dr, 'frosted')
NS_W = FW / FT
nightstand('w', BED_X0 - NS_W - 0.05)
nightstand('e', BED_X0 + 160 / FT + 0.05)

# ---------------------------------------------------------------- Flos Parentesi: cable ceiling to floor, base 11 cm, 58 cm red element with R125 spot
dg = bpy.context.evaluated_depsgraph_get()
def ceiling_z(x_ft, y_ft):
    p = W(x_ft, y_ft, FLOOR + 6.0)
    hit, loc, *_ = bpy.context.scene.ray_cast(dg, p, Vector((0, 0, 1)))
    return loc.z if hit else W(0, 0, FLOOR + 8.0).z
def cyl(bm, p0, p1, r, seg=10):
    d = p1 - p0; L = d.length
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=L)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.rotate(bm, verts=res['verts'], cent=Vector((0, 0, 0)), matrix=q.to_matrix())
    bmesh.ops.translate(bm, verts=res['verts'], vec=(p0 + p1) / 2)
def parentesi(tag, x_ft, y_ft, tube_z, face):
    base = W(x_ft, y_ft); top = ceiling_z(x_ft, y_ft)
    out = Vector(face).normalized()
    blk, red, bulb = bmesh.new(), bmesh.new(), bmesh.new()
    cyl(blk, base, base + Vector((0, 0, 4)), 5.5, 20)                 # floor weight
    cyl(blk, base + Vector((0, 0, 4)), Vector((base.x, base.y, top)), 0.6, 6)   # steel cable
    cyl(red, Vector((base.x, base.y, top - 2)), Vector((base.x, base.y, top)), 5, 16)   # ceiling rose
    pts = [(0, 0), (0, 10), (3.5, 16), (4.5, 26), (4.5, 40), (3.5, 48), (0, 52), (0, 58)]   # "(" profile, cm
    P = [base + out * a + Vector((0, 0, tube_z + b)) for a, b in pts]
    for a, b in zip(P[:-1], P[1:]):
        cyl(red, a, b, 0.9, 8)
    clamp = base + out * 5 + Vector((0, 0, tube_z + 30))
    add_box(blk, clamp, -2, 2, -2, 2, -3, 3)
    axis = (out * 0.8 + Vector((0, 0, -0.6))).normalized()            # spot aimed outward and down
    head = clamp + out * 3
    res = bmesh.ops.create_cone(bulb, cap_ends=True, cap_tris=False, segments=16, radius1=3.0, radius2=6.25, depth=14)
    q = Vector((0, 0, 1)).rotation_difference(axis)
    bmesh.ops.rotate(bulb, verts=res['verts'], cent=Vector((0, 0, 0)), matrix=q.to_matrix())
    bmesh.ops.translate(bulb, verts=res['verts'], vec=head + axis * 7)
    emit('parentesi_%s' % tag, red, 'red'); emit('parentesi_%s_hw' % tag, blk, 'black')
    emit('light_bedroom_%s' % tag, bulb, 'bulb')
parentesi('w', -40.95, 1.35, 125, (1, 0.6, 0))       # SW corner between the west table and the wall
parentesi('e', -31.65, 1.25, 100, (-1, 0.5, 0))      # beside the east table

# ---------------------------------------------------------------- Asimov (Roborock S5) docks on the west wall by the NW corner
v = bpy.data.objects['lvl002vacuum_asimov']
bb = [v.matrix_world @ Vector(c) for c in v.bound_box]
cur = sum(bb, Vector()) / 8
tgt = W(-41.15, 12.9); tgt.z = cur.z
v.data.transform(Matrix.Translation(tgt - cur))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb), 'ceiling W/E', round(ceiling_z(-40.95, 1.35) - W(0, 0).z), round(ceiling_z(-31.65, 1.25) - W(0, 0).z))
