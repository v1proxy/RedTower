# Floors: ground level raw concrete (stairs stay wood), second and third floors light wood.
import bpy, bmesh, os, sys
OUT = sys.argv[sys.argv.index('--') + 1]
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
def paint(m, hx, rough):
    c = lin(hx); b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0
    m.diffuse_color = (*c, 1)
WOOD, CONCRETE = '#CFAF82', '#9C9890'
mats = bpy.data.materials
paint(mats['rt_floor'], WOOD, 0.7)
paint(mats['rt_room'], WOOD, 0.7)
paint(mats['rt_room_concrete'], CONCRETE, 0.95)
conc = mats.get('rt_floor_concrete') or mats['rt_room_concrete'].copy()
conc.name = 'rt_floor_concrete'; paint(conc, CONCRETE, 0.95)

# ground-floor rooms -> concrete
for ob in bpy.data.objects:
    if ob.type == 'MESH' and ob.name.startswith('lvl000room_'):
        ob.data.materials[0] = mats['rt_room_concrete']

# ground-floor slab -> concrete; anything standing above the slab top (stair treads) -> separate wood object
src = bpy.data.objects['lvl000floor_l1']
SLAB_TOP = 30.48 + 4.0   # cm: L1 finished floor sits at 30.48 after finalize.py's translation
if 'lvl000stair_l1' not in bpy.data.objects:
    bm = bmesh.new(); bm.from_mesh(src.data)
    up = [f for f in bm.faces if f.calc_center_median().z > SLAB_TOP]
    bm2 = bmesh.new(); bm2.from_mesh(src.data)
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if f.calc_center_median().z <= SLAB_TOP], context='FACES')
    me2 = bpy.data.meshes.new('lvl000stair_l1_geo'); bm2.to_mesh(me2); bm2.free()
    bmesh.ops.delete(bm, geom=up, context='FACES'); bm.to_mesh(src.data); bm.free()
    if len(me2.polygons):
        me2.materials.clear(); me2.materials.append(mats['rt_floor'])
        st = bpy.data.objects.new('lvl000stair_l1', me2); src.users_collection[0].objects.link(st)
        print('stair faces', len(me2.polygons))
src.data.materials[0] = conc
print('slab faces', len(src.data.polygons))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb))
