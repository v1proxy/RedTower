import bpy, os, sys
import numpy as np
from mathutils import Vector
OUT = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
mn = np.array([1e18] * 3); mx = -mn
for o in meshes:
    a = np.empty(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', a); a = a.reshape(-1, 3)
    mn = np.minimum(mn, a.min(0)); mx = np.maximum(mx, a.max(0))
# building (not site) centre in this file's coordinates: x -42.6..0.8 ft, y 0..20 ft
off = Vector((1680.53, -708.91, 30.48))
bc = Vector((-21 * 30.48, 10 * 30.48, 0)) + off
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_cavity = True; sh.cavity_type = 'WORLD'
try: sh.show_shadows = True
except Exception: pass
sc.render.resolution_x = 1280; sc.render.resolution_y = 800
if sc.world is None: sc.world = bpy.data.worlds.new('w')
sc.world.color = (0.02, 0.02, 0.02)
tgt = bpy.data.objects.new('tgt', None); sc.collection.objects.link(tgt)
cam_d = bpy.data.cameras.new('cam'); cam_d.lens = 30; cam_d.clip_start = 10; cam_d.clip_end = 100000
cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
views = [
 ('full_front', [0, 1, 2, 3], Vector((1500, -2200, 1300)), 350),
 ('full_back', [0, 1, 2, 3], Vector((-1700, 1900, 1300)), 350),
 ('L1', [0], Vector((600, -1500, 1900)), 0),
 ('L2', [0, 1], Vector((600, -1500, 2100)), 274),
 ('L3', [0, 1, 2], Vector((600, -1500, 2300)), 548),
]
for name, lv, rel, zc in views:
    for o in meshes:
        L = int(o.name[3:6]) if o.name.startswith('lvl') else 0
        o.hide_render = L not in lv
    tgt.location = bc + Vector((0, 0, zc + 60))
    cam.location = tgt.location + rel
    sc.render.filepath = os.path.join(OUT, 'pv_%s.png' % name)
    bpy.ops.render.render(write_still=True)
    print('rendered', name, flush=True)
