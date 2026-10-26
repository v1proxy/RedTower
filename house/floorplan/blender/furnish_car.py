# Polestar 2 parked nose-in on the east (right) side of the garage, light grey (Vittorio, 2026-10-25).
# Shown by the card only while the car is connected. Polestar 2: L 4606, W 1859 (body), H 1479, wheelbase 2735 mm,
# 245/45 R19 tyres. Built as a lofted body from side/plan profiles; one material per object so the card can show/hide
# them as an object group. Runs on redtower_ha.blend (cm). Idempotent.
import bpy, bmesh, math, os, sys
from mathutils import Vector
OUT = sys.argv[sys.argv.index('--') + 1]
FT = 30.48; OX, OY, OZ = 1680.5275, -708.9085, 30.48
def W(x_ft, y_ft, z_ft=0.0): return Vector((x_ft * FT + OX, y_ft * FT + OY, z_ft * FT + OZ))
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
M = {'body': mat('rt_car_body', '#C3C6C9', 0.3), 'glass': mat('rt_car_glass', '#1A1F25', 0.1),
     'tires': mat('rt_car_tire', '#161616', 0.9), 'rims': mat('rt_car_rim', '#9DA1A6', 0.4),
     'tail': mat('rt_car_tail', '#B0141B', 0.3)}
for nm in [o.name for o in bpy.data.objects if o.name.startswith('lvl000car_polestar')]:
    bpy.data.objects.remove(bpy.data.objects[nm])
coll = bpy.data.objects['lvl000room_garage'].users_collection[0]

# ---- placement: garage x -19.3..0.3 ft, y 0.5..19.5 ft. Right side 85 cm off the east wall, nose 60 cm off the north wall.
L, HW = 4606.0, 929.5
CX = 0.3 - (85 + 93) / FT; FY = 19.5 - 60 / FT
C0 = W(CX, FY)
def P(X, Y, Z):  # car mm (X back from the nose, Y to the car's left... mapped to +x east, Z up) -> blend cm
    return Vector((C0.x + Y / 10, C0.y - X / 10, C0.z + Z / 10))

def interp(pts, x):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1: return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[0][1] if x < pts[0][0] else pts[-1][1]
TOP = [(0, 560), (60, 700), (250, 790), (890, 880), (1350, 960), (2050, 1440), (2450, 1479), (2900, 1440), (3800, 1090), (4450, 1070), (4520, 1085), (4606, 1000)]
BELT = [(0, 560), (1350, 960), (3800, 1060), (4606, 1000)]
HALF = [(0, 760), (80, 860), (300, 910), (900, 929.5), (4300, 925), (4550, 860), (4606, 780)]
ROOFH = [(1350, 820), (2050, 640), (2900, 630), (3800, 760)]
AX = [(890, 352), (890 + 2735, 352)]; RA = 395
def bottom(x):
    b = interp([(0, 300), (200, 200), (600, 170), (4300, 170), (4606, 380)], x)
    for ax, az in AX:
        if abs(x - ax) < RA: b = max(b, az + math.sqrt(RA * RA - (x - ax) ** 2))
    return b
GH = (1350, 3800)
xs = sorted(set([0, 30, 60, 120, 180, 250, 400, 600] + list(range(400, 4300, 60)) + [AX[0][0] + d for d in range(-RA, RA + 1, 30)]
               + [AX[1][0] + d for d in range(-RA, RA + 1, 30)] + [1350, 2050, 2450, 2900, 3800, 4300, 4450, 4520, 4560, 4590, 4606]))
def ring(x):
    hw = interp(HALF, x); t = interp(TOP, x); b = bottom(x)
    gh = GH[0] <= x <= GH[1]
    bl = interp(BELT, x) if gh else t - 15
    bl = min(bl, t)
    rh = interp(ROOFH, x) if gh else hw * 0.7
    sh = max(b + 40, min(bl - 60, t - 60))
    half = [(hw - 60, b), (hw, min(b + 90, sh)), (hw, sh), (hw - 35, bl), (rh, t - (25 if gh else 5))]
    pts = [(0, b)] + half + [(0, t)] + [(-y, z) for y, z in reversed(half)]
    return pts, gh
bm = bmesh.new(); rings = []; flags = []
for x in xs:
    pts, gh = ring(x); rings.append([bm.verts.new(P(x, y, z)) for y, z in pts]); flags.append(gh)
n = len(rings[0]); GLASS_IDX = {4, 5, 6, 7}  # quads from belt (4) over the roof to the other belt (8)
for i in range(len(rings) - 1):
    gh = flags[i] and flags[i + 1]
    for j in range(n):
        f = bm.faces.new((rings[i][j], rings[i][(j + 1) % n], rings[i + 1][(j + 1) % n], rings[i + 1][j]))
        f.material_index = 1 if (gh and j in GLASS_IDX) else 0
for r in (rings[0], rings[-1]):
    f = bm.faces.new(r); f.material_index = 0
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# mirrors (body colour)
for s in (1, -1):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']: v.co = P(1520 + v.co.x * 160, s * (HW + 70) + v.co.y * 140 * s, 1010 + v.co.z * 110)
    for f in {f for v in r['verts'] for f in v.link_faces}: f.material_index = 0

def emit(name, src_bm, idx, key, smooth):
    b2 = src_bm.copy()
    bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.material_index != idx], context='FACES')
    me = bpy.data.meshes.new('lvl000' + name + '_geo'); b2.to_mesh(me); b2.free()
    me.materials.append(M[key]); me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    ob = bpy.data.objects.new('lvl000' + name, me); coll.objects.link(ob); return ob
emit('car_polestar_body', bm, 0, 'body', True)
emit('car_polestar_glass', bm, 1, 'glass', True)
bm.free()

# wheels: tyre cylinders and rim discs on the outer faces
tb = bmesh.new(); rb = bmesh.new(); TW = 245; TR = 352; TY = 800
for ax, az in AX:
    for s in (1, -1):
        seg = 24
        for b_, r_, y0, y1 in ((tb, TR, s * (TY - TW / 2), s * (TY + TW / 2)), (rb, 235, s * (TY + TW / 2), s * (TY + TW / 2 + 6))):
            a = [b_.verts.new(P(ax + r_ * math.cos(2 * math.pi * k / seg), y0, az + r_ * math.sin(2 * math.pi * k / seg))) for k in range(seg)]
            c = [b_.verts.new(P(ax + r_ * math.cos(2 * math.pi * k / seg), y1, az + r_ * math.sin(2 * math.pi * k / seg))) for k in range(seg)]
            for k in range(seg):
                b_.faces.new((a[k], a[(k + 1) % seg], c[(k + 1) % seg], c[k]))
            b_.faces.new(a); b_.faces.new(c)
for b_ in (tb, rb): bmesh.ops.recalc_face_normals(b_, faces=b_.faces)
def emit_bm(name, b_, key):
    me = bpy.data.meshes.new('lvl000' + name + '_geo'); b_.to_mesh(me); b_.free(); me.materials.append(M[key])
    ob = bpy.data.objects.new('lvl000' + name, me); coll.objects.link(ob); return ob
emit_bm('car_polestar_tires', tb, 'tires'); emit_bm('car_polestar_rims', rb, 'rims')
# full-width rear light bar
lb = bmesh.new(); r = bmesh.ops.create_cube(lb, size=1.0)
for v in r['verts']: v.co = P(4596 + v.co.x * 24, v.co.y * 1640, 940 + v.co.z * 28)
emit_bm('car_polestar_tail', lb, 'tail')
print('CAR at', [round(c, 1) for c in C0], 'objects', [o.name for o in bpy.data.objects if o.name.startswith('lvl000car_')])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb))
