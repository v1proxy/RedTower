# Adjust palette for floor3d's lighting (no environment map: metallic surfaces read black) and re-export.
import bpy, os, sys
OUT = sys.argv[sys.argv.index('--') + 1]
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
NEW = {
 'clad_red': ('#C0282B', .6), 'clad_grey': ('#6F757C', .6), 'clad_white': ('#ECECE8', .6),
 'metal': ('#62666B', .5), 'appliance': ('#B9BEC3', .4), 'fixture': ('#9A9DA1', .5), 'skylight': ('#4A4F56', .5),
 'site_ground': ('#27301F', 1), 'site_paving': ('#4D4B47', .95), 'site_fence': ('#7A6249', .9),
 'wall': ('#E9E3D9', .9), 'floor': ('#A9825C', .8), 'room': ('#A9825C', .8), 'frame': ('#DDD7CB', .6),
}
for m in bpy.data.materials:
    if not m.name.startswith('rt_'): continue
    k = m.name[3:]
    b = m.node_tree.nodes.get('Principled BSDF') if m.node_tree else None
    if not b: continue
    b.inputs['Metallic'].default_value = 0.0
    if k in NEW:
        hx, r = NEW[k]; c = lin(hx)
        b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = r
        m.diffuse_color = (*c, m.diffuse_color[3])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
print('GLB', os.path.getsize(glb))
