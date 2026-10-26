import bpy
from mathutils import Vector
FT = 30.48; OX, OY, OZ = 1680.5275, -708.9085, 30.48
def W(x, y, z): return Vector((x * FT + OX, y * FT + OY, z * FT + OZ))
dg = bpy.context.evaluated_depsgraph_get()
for (x, y) in [(-40.95, 1.35), (-31.65, 1.25), (-35, 7), (-40.5, 7), (-28, 7)]:
    out = []
    for z0 in (18.5, 20.0, 22.0):
        p = W(x, y, z0)
        hit, loc, nrm, idx, ob, mtx = bpy.context.scene.ray_cast(dg, p, Vector((0, 0, 1)))
        out.append((z0, round((loc.z - OZ) / FT - 18.0, 2) if hit else None, ob.name if hit else None))
    print('PROBE', x, y, out)
