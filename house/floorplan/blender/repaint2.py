# Garage room plane gets its own concrete material; re-export.
import bpy, os, sys
OUT = sys.argv[sys.argv.index('--') + 1]
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
src = bpy.data.materials['rt_room']
m = bpy.data.materials.get('rt_room_concrete') or src.copy()
m.name = 'rt_room_concrete'
c = lin('#8C8984')
m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*c, 1)
m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
m.diffuse_color = (*c, 1)
ob = bpy.data.objects['lvl000room_garage']
ob.data.materials[0] = m
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb))
