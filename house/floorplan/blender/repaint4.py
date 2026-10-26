# Light grey building metals (Vittorio, 2026-10-25): grey corrugated cladding and roofs, FAKRO skylight panels, steel. Re-export.
import bpy, os, sys
OUT = sys.argv[sys.argv.index('--') + 1]
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
NEW = {'rt_clad_grey': ('#AEB2B7', .75), 'rt_skylight': ('#A2A6AC', .6), 'rt_metal': ('#9A9EA4', .55)}
for name, (hx, r) in NEW.items():
    m = bpy.data.materials.get(name)
    if not m: print('missing', name); continue
    b = m.node_tree.nodes['Principled BSDF']; c = lin(hx)
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = r; b.inputs['Metallic'].default_value = 0.0
    m.diffuse_color = (*c, 1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb))
