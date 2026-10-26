# Living room furniture from Vittorio's photos (2026-10-25): L-shaped modular sofa, two white steel bookcases
# in the corner of the stair wall and the north wall, Flos Arco (Carrara base), wall TV. Runs on redtower_ha.blend (cm).
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix
OUT = sys.argv[sys.argv.index('--') + 1]
FT = 30.48
OX, OY, OZ = 1680.5275, -708.9085, 30.48
FLOOR = 9.0
def W(x_ft, y_ft, z_ft=FLOOR):
    return Vector((x_ft * FT + OX, y_ft * FT + OY, z_ft * FT + OZ))
coll = bpy.data.objects['lvl001room_living_room'].users_collection[0]

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
def mat(name, hx, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; c = lin(hx)
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0; m.diffuse_color = (*c, 1)
    return m
M = {
 'sofa': mat('rt_sofa_grey', '#A3A6AB', 0.95), 'sofa_d': mat('rt_sofa_grey_dark', '#8E9197', 0.95),
 'shelf': mat('rt_shelf_white', '#EEEEEA', 0.5),
 'book_a': mat('rt_book_a', '#3E4A5A', 0.8), 'book_b': mat('rt_book_b', '#8C2F2A', 0.8), 'book_c': mat('rt_book_c', '#D8D2C4', 0.8),
 'marble': mat('rt_marble', '#ECECEA', 0.3), 'steel': mat('rt_steel', '#B9BDC1', 0.35),
 'tv': mat('rt_tv_black', '#121212', 0.3), 'screen': mat('rt_tv_screen', '#1C1E22', 0.2),
}
PREFIXES = ('lvl001sofa_', 'lvl001shelf_', 'lvl001books_', 'lvl001arco_', 'lvl001light_living_arco', 'lvl001tv_')
for nm in [o.name for o in bpy.data.objects if o.name.startswith(PREFIXES)]:
    bpy.data.objects.remove(bpy.data.objects[nm])

def emit(name, bm, matkey, smooth=False):
    full = 'lvl001' + name
    me = bpy.data.meshes.new(full + '_geo'); bm.to_mesh(me); bm.free()
    me.materials.append(M[matkey]); me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    ob = bpy.data.objects.new(full, me); coll.objects.link(ob); return ob
def add_box(bm, origin, x0, x1, y0, y1, z0, z1):
    r = bmesh.ops.create_cube(bm, size=1.0); vs = r['verts']
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=vs)
    bmesh.ops.translate(bm, vec=origin + Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), verts=vs)
def cyl(bm, p0, p1, r, seg=12):
    d = p1 - p0
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.rotate(bm, verts=res['verts'], cent=Vector((0, 0, 0)), matrix=q.to_matrix())
    bmesh.ops.translate(bm, verts=res['verts'], vec=(p0 + p1) / 2)

# ---------------------------------------------------------------- L sofa: grey modular "cloud" sectional, seats face the TV (east)
# Long run 290 cm along y, 100 cm deep; chaise at the north end, 165 cm deep x 95 cm. Estimated from the photos.
SX, SY = -12.6, 7.6                                   # SW corner of the long run (back against nothing, mid-room)
o = W(SX, SY)
L, D, CD, CW = 290, 100, 165, 95
seat, base = bmesh.new(), bmesh.new()
mods = [(0, 96), (97, 193), (194, L - CW - 1)]        # three seat modules on the long run
for y0, y1 in mods:
    add_box(seat, o, 26, D, y0 + 0.5, y1 - 0.5, 8, 42)
add_box(seat, o, 26, CD, L - CW, L, 8, 42)            # chaise module
add_box(base, o, 2, D - 2, 2, L - CW - 2, 0, 8)       # recessed plinth
add_box(base, o, 2, CD - 2, L - CW + 2, L - 2, 0, 8)
emit('sofa_seat', seat, 'sofa')
back = bmesh.new()
add_box(back, o, 0, 26, 0, L, 8, 72)                  # backrest along the west side
for yc in (48, 145, 240):                             # bolsters
    cyl(back, o + Vector((36, yc - 42, 54)), o + Vector((36, yc + 42, 54)), 11, 16)
for yc in (70, 170):                                  # loose back pillows
    add_box(back, o, 22, 40, yc - 25, yc + 25, 42, 88)
emit('sofa_back', back, 'sofa_d')

# ---------------------------------------------------------------- bookcases: white steel grid shelving with books (estimated sizes)
random.seed(7)
def bookcase(tag, origin, cols, along, cell=36.5, rows=5, depth=35):
    # local a = along the wall, d = 0 at the wall to `depth` at the open front
    fr, bk = bmesh.new(), {'book_a': bmesh.new(), 'book_b': bmesh.new(), 'book_c': bmesh.new()}
    Wd = cols * cell; H = rows * 36 + 2
    def box(a0, a1, d0, d1, z0, z1, bm):
        if along == 'x':     # back on a north wall: a -> +x, d -> -y
            add_box(bm, origin, a0, a1, -d1, -d0, z0, z1)
        else:                # back on a west-facing... east-facing wall: a -> +y, d -> +x
            add_box(bm, origin, d0, d1, a0, a1, z0, z1)
    for i in range(cols + 1):                          # posts, front and back
        a = min(i * cell, Wd - 1.6)
        box(a, a + 1.6, 0, 1.6, 0, H, fr); box(a, a + 1.6, depth - 1.6, depth, 0, H, fr)
        box(a, a + 1.6, 1.6, depth - 1.6, 0, 1.6, fr); box(a, a + 1.6, 1.6, depth - 1.6, H - 1.6, H, fr)
    for r in range(rows + 1):                          # shelves
        z = 2 + r * 36
        box(0, Wd, 0, depth, z - 1.2, z, fr)
    for r in range(rows):
        for c in range(cols):
            if random.random() < 0.15: continue
            z = 2 + r * 36; a0 = c * cell + 2.5
            wfill = (cell - 5) * random.uniform(0.45, 0.95)
            a = a0
            while a < a0 + wfill:
                w = random.uniform(2.5, 6.0); h = random.uniform(20, 30)
                key = random.choice(['book_a', 'book_a', 'book_b', 'book_c', 'book_c'])
                box(a, a + w, depth - 26, depth - 3, z, z + h, bk[key]); a += w + 0.3
    emit('shelf_%s' % tag, fr, 'shelf')
    for k, bm in bk.items():
        emit('books_%s_%s' % (tag, k[-1]), bm, k)
# north wall unit: 4 x 5 cells, back on the north wall (y 19.3), from the stair wall (x -16.05) east
bookcase('n', W(-16.05, 19.3), cols=4, along='x')
# stair wall unit: 3 x 5 cells, back on the stair wall (x -16.05), running south from the north unit
bookcase('e', W(-16.05, 19.3 - 36 / FT - 0.03 - 3 * 36.5 / FT), cols=3, along='y')

# ---------------------------------------------------------------- Flos Arco: Carrara base 42 x 26 x 65 cm, height 240, reach 215, shade 32
BX, BY = -10.6, 6.5                                   # base south of the sofa, arc reaching north over the seats
bo = W(BX, BY)
base = bmesh.new(); add_box(base, bo, -21, 21, -13, 13, 0, 65); emit('arco_base', base, 'marble')
arc = bmesh.new()
pts = [Vector((0, 0, 65)), Vector((0, 0, 95))]
cu, cz, a, b = 150.0, 95.0, 150.0, 145.0               # ellipse: vertical at the base, apex 240 cm, end 215 cm out
end_th = math.acos((215 - cu) / a)
for i in range(1, 29):
    t = math.pi + (end_th - math.pi) * i / 28
    pts.append(Vector((0, cu + a * math.cos(t), cz + b * math.sin(t))))
for p0, p1 in zip(pts[:-1], pts[1:]):
    cyl(arc, bo + p0, bo + p1, 1.6, 8)
tip = bo + pts[-1]
cyl(arc, tip, tip + Vector((0, 0, -12)), 0.8, 6)
emit('arco_arc', arc, 'steel')
shade = bmesh.new()
res = bmesh.ops.create_uvsphere(shade, u_segments=20, v_segments=8, radius=16)
bmesh.ops.delete(shade, geom=[v for v in res['verts'] if v.co.z < -0.01], context='VERTS')
bmesh.ops.translate(shade, verts=shade.verts[:], vec=tip + Vector((0, 0, -28)))
emit('light_living_arco', shade, 'steel', smooth=True)   # bindable: future light entity

# ---------------------------------------------------------------- TV on the east wall (65", centred on the sofa)
TVY = 12.4
to = W(-0.02, TVY, FLOOR + 4.6)
tv = bmesh.new(); add_box(tv, to, -4, 0, -73, 73, -42, 42); emit('tv_living_room', tv, 'tv')
sc = bmesh.new(); add_box(sc, to, -4.6, -4.0, -71, 71, -40, 40); emit('tv_living_room_screen', sc, 'screen')

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb))
