# Translate model so its bbox min sits at the glTF origin (floor3d centers by size, not by min),
# export the GLB, write anchor coordinates, and render preview images with Workbench.
import bpy, json, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

OUT = sys.argv[sys.argv.index('--') + 1]
FT = 30.48
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
mn = np.array([1e18] * 3); mx = -mn
for o in meshes:
    a = np.empty(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', a); a = a.reshape(-1, 3)
    if len(a):
        mn = np.minimum(mn, a.min(0)); mx = np.maximum(mx, a.max(0))
off = Vector((-mn[0], -mx[1], -mn[2]))
for o in meshes:
    o.data.transform(Matrix.Translation(off))
size = mx - mn
# glTF: X = bx, Y = bz, Z = -by.  Card then shifts by (-sizeX/2, 0, -sizeZ/2).
def ft_to_card(x, y, z):
    bx, by, bz = x * FT + off.x, y * FT + off.y, z * FT + off.z
    return [round(bx - size[0] / 2, 1), round(bz, 1), round(-by - size[1] / 2, 1)]
rep = json.load(open(os.path.join(OUT, 'build_report.json')))
card = {k: {'center': ft_to_card(v['center_ft'][0], v['center_ft'][1], v['floor_ft']), 'level': v['level']} for k, v in rep['anchors'].items()}
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'redtower_ha.blend'))
glb = os.path.join(OUT, 'redtower.glb')
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_texcoords=False,
                          export_normals=True, export_materials='EXPORT', export_extras=False, export_animations=False)
json.dump({'offset_cm': list(off), 'size_cm': [float(s) for s in size], 'card_coords': card, 'glb_bytes': os.path.getsize(glb)},
          open(os.path.join(OUT, 'card_coords.json'), 'w'), indent=1)
print('GLB', os.path.getsize(glb), 'size_cm', size)

# ---------------- previews
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_cavity = True; sh.cavity_type = 'WORLD'
sh.show_object_outline = False
try: sh.show_shadows = True
except Exception: pass
sc.render.resolution_x = 1280; sc.render.resolution_y = 800; sc.render.resolution_percentage = 100
sc.render.film_transparent = False
if sc.world is None: sc.world = bpy.data.worlds.new('w')
sc.world.color = (0.02, 0.02, 0.02)
center = Vector((size[0] / 2, -size[1] / 2, 300))
tgt = bpy.data.objects.new('tgt', None); sc.collection.objects.link(tgt); tgt.location = center
cam_d = bpy.data.cameras.new('cam'); cam_d.lens = 35
cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
views = [
 ('full_front', [0, 1, 2, 3], Vector((1100, -2300, 1500))),
 ('full_back', [0, 1, 2, 3], Vector((-900, 2000, 1500))),
 ('L1', [0], Vector((700, -1700, 2100))),
 ('L2', [0, 1], Vector((700, -1700, 2400))),
 ('L3', [0, 1, 2], Vector((700, -1700, 2700))),
]
for name, lv, rel in views:
    for o in meshes:
        L = int(o.name[3:6]) if o.name.startswith('lvl') else 0
        o.hide_render = L not in lv
    tgt.location = center + Vector((0, 0, 90 * max(lv)))
    cam.location = center + rel
    sc.render.filepath = os.path.join(OUT, 'preview_%s.png' % name)
    bpy.ops.render.render(write_still=True)
    print('rendered', name)
