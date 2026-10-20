"""Blender (4.2+ / 5.x) script: build and render the Maag cover.

    blender -b --factory-startup --python render_cover.py -- \
        --npz cover_scene.npz --out cover.png --res 2400 1500 --samples 256

The npz holds one mesh per material, metres, z up, cabinet front at y = 0.
The script saves cover.blend next to the PNG so the scene can be reopened.
"""
import sys, os, math, json, argparse
import numpy as np
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--npz", default="cover_scene.npz")
ap.add_argument("--out", default="cover.png")
ap.add_argument("--res", nargs=2, type=int, default=(2400, 1500))
ap.add_argument("--samples", type=int, default=256)
ap.add_argument("--cam", default="")
ap.add_argument("--look", default="", help='JSON overrides, e.g. {"mist": 3.5, "frost": 0.3}')
a = ap.parse_args(argv)
HERE = os.path.dirname(os.path.abspath(a.npz))

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
data = np.load(a.npz, allow_pickle=False)
meta = json.loads(str(data["meta"]))
if a.look:
    meta.update(json.loads(a.look))


# ---------------------------------------------------------------- materials
def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m


def leaf_mat(name, color, trans):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = 0.38
    b.inputs["Coat Weight"].default_value = 0.15
    t = nt.nodes.new("ShaderNodeBsdfTranslucent")
    t.inputs["Color"].default_value = (*trans, 1.0)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.25
    out = nt.nodes["Material Output"]
    nt.links.new(b.outputs["BSDF"], mix.inputs[1])
    nt.links.new(t.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def bumpy(m, scale=900.0, strength=0.35, vary=None):
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    if vary:
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*vary[0], 1)
        ramp.color_ramp.elements[1].color = (*vary[1], 1)
        nz2 = nt.nodes.new("ShaderNodeTexNoise")
        nz2.inputs["Scale"].default_value = scale / 40.0
        nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
        nt.links.new(nz2.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


MAT = {
    "frame": principled("frame", (0.80, 0.81, 0.83), 0.32, 1.0),
    "alu": principled("alu", (0.82, 0.83, 0.85), 0.28, 1.0),
    "alu_dark": principled("alu_dark", (0.55, 0.57, 0.60), 0.35, 1.0),
    "steel": principled("steel", (0.70, 0.71, 0.73), 0.22, 1.0),
    "black": principled("black", (0.025, 0.026, 0.03), 0.45),
    "pom": principled("pom", (0.86, 0.84, 0.78), 0.4),
    "arm_white": principled("arm_white", (0.86, 0.87, 0.88), 0.33, 0.0, coat=0.3),
    "brass": principled("brass", (0.80, 0.62, 0.30), 0.3, 1.0),
    "pcb": principled("pcb", (0.05, 0.25, 0.12), 0.4),
    "rubber": principled("rubber", (0.03, 0.03, 0.03), 0.7),
    "grip_body": principled("grip_body", (0.04, 0.04, 0.045), 0.5),
    "grip_link": principled("grip_link", (0.10, 0.10, 0.11), 0.35, 0.6),
    "tray": principled("tray", (0.12, 0.13, 0.14), 0.55, 0.0, coat=0.1),
    "pot": bumpy(principled("pot", (0.018, 0.018, 0.02), 0.6), 400, 0.08),
    "soil": bumpy(principled("soil", (0.06, 0.04, 0.025), 0.95), 1200, 0.6,
                  vary=((0.035, 0.024, 0.016), (0.09, 0.065, 0.04))),
    "stem": principled("stem", (0.16, 0.30, 0.07), 0.5),
    "leaf_a": leaf_mat("leaf_a", (0.028, 0.12, 0.014), (0.16, 0.40, 0.05)),
    "leaf_b": leaf_mat("leaf_b", (0.036, 0.15, 0.018), (0.20, 0.45, 0.06)),
    "leaf_c": leaf_mat("leaf_c", (0.05, 0.19, 0.022), (0.25, 0.50, 0.07)),
    "pepper_red": principled("pepper_red", (0.55, 0.02, 0.01), 0.18, 0.0, coat=0.6),
    "pepper_green": principled("pepper_green", (0.06, 0.25, 0.03), 0.2, 0.0, coat=0.6),
    "led_body": principled("led_body", (0.75, 0.76, 0.78), 0.4, 1.0),
    "led_emit": principled("led_emit", (1.0, 0.95, 0.88), 0.5, emit=(1.0, 0.90, 0.80), strength=meta.get("led", 18.0)),
    "floor": bumpy(principled("floor", (0.42, 0.40, 0.37), 0.42), 60, 0.05,
                   vary=((0.36, 0.34, 0.31), (0.46, 0.44, 0.41))),
    "wall": principled("wall", (0.40, 0.39, 0.36), 0.9),
    # more plants
    "leaf_purple": leaf_mat("leaf_purple", (0.060, 0.012, 0.040), (0.25, 0.04, 0.12)),
    "leaf_purple2": leaf_mat("leaf_purple2", (0.090, 0.020, 0.060), (0.30, 0.05, 0.15)),
    "leaf_thai": leaf_mat("leaf_thai", (0.030, 0.110, 0.015), (0.15, 0.38, 0.05)),
    "leaf_mint": leaf_mat("leaf_mint", (0.070, 0.220, 0.035), (0.25, 0.55, 0.08)),
    "leaf_mint2": leaf_mat("leaf_mint2", (0.060, 0.190, 0.030), (0.22, 0.50, 0.07)),
    "leaf_parsley": leaf_mat("leaf_parsley", (0.018, 0.090, 0.012), (0.10, 0.32, 0.04)),
    "leaf_parsley2": leaf_mat("leaf_parsley2", (0.025, 0.110, 0.015), (0.12, 0.36, 0.05)),
    "leaf_thyme": leaf_mat("leaf_thyme", (0.080, 0.120, 0.060), (0.25, 0.35, 0.15)),
    "leaf_oregano": leaf_mat("leaf_oregano", (0.050, 0.140, 0.040), (0.18, 0.40, 0.10)),
    "leaf_lettuce": leaf_mat("leaf_lettuce", (0.200, 0.420, 0.070), (0.50, 0.80, 0.20)),
    "leaf_lettuce2": leaf_mat("leaf_lettuce2", (0.150, 0.360, 0.050), (0.45, 0.75, 0.16)),
    "leaf_lettuce_red": leaf_mat("leaf_lettuce_red", (0.220, 0.030, 0.050), (0.50, 0.10, 0.10)),
    "chive": leaf_mat("chive", (0.040, 0.160, 0.030), (0.15, 0.45, 0.08)),
    "flower_purple": principled("flower_purple", (0.35, 0.12, 0.45), 0.6),
    "stem_purple": principled("stem_purple", (0.15, 0.04, 0.09), 0.5),
    "stem_woody": principled("stem_woody", (0.22, 0.14, 0.08), 0.7),
    "stem_light": principled("stem_light", (0.20, 0.38, 0.10), 0.5),
    "pepper_yellow": principled("pepper_yellow", (0.80, 0.55, 0.02), 0.18, 0.0, coat=0.6),
    "pepper_orange": principled("pepper_orange", (0.80, 0.25, 0.02), 0.18, 0.0, coat=0.6),
    # the enclosure: frosted polycarbonate
    "frosted": principled("frosted", (0.96, 0.97, 0.98), meta.get("frost", 0.45)),
    # the room behind it
    "room_floor": bumpy(principled("room_floor", (0.42, 0.28, 0.16), 0.45), 30, 0.05,
                        vary=((0.34, 0.22, 0.12), (0.50, 0.34, 0.20))),
    "room_wall": principled("room_wall", (0.80, 0.77, 0.70), 0.9),
    "room_ceiling": principled("room_ceiling", (0.85, 0.85, 0.83), 0.9),
    "room_frame": principled("room_frame", (0.08, 0.08, 0.08), 0.5),
    "room_window": principled("room_window", (0.85, 0.92, 1.0), 0.5, emit=(0.85, 0.92, 1.0),
                              strength=meta.get("window", 7.0)),
    "room_sofa": principled("room_sofa", (0.12, 0.24, 0.26), 0.9),
    "room_cushion": principled("room_cushion", (0.16, 0.30, 0.32), 0.9),
    "room_rug": principled("room_rug", (0.55, 0.42, 0.30), 1.0),
    "room_wood": principled("room_wood", (0.35, 0.22, 0.12), 0.5),
    "room_dark": principled("room_dark", (0.03, 0.03, 0.03), 0.4, 0.5),
    "room_book1": principled("room_book1", (0.55, 0.12, 0.10), 0.6),
    "room_book2": principled("room_book2", (0.12, 0.25, 0.45), 0.6),
    "room_book3": principled("room_book3", (0.75, 0.65, 0.45), 0.6),
    "room_book4": principled("room_book4", (0.15, 0.35, 0.20), 0.6),
    "room_lamp": principled("room_lamp", (1.0, 0.85, 0.65), 0.5, emit=(1.0, 0.78, 0.50),
                            strength=meta.get("lamp", 10.0)),
    "room_terracotta": principled("room_terracotta", (0.55, 0.25, 0.14), 0.8),
}
# the window looks onto a garden: sky above, sunlit foliage below, blotchy
_w = MAT["room_window"].node_tree
_wb = _w.nodes["Principled BSDF"]
_tc = _w.nodes.new("ShaderNodeTexCoord")
_sep = _w.nodes.new("ShaderNodeSeparateXYZ")
_w.links.new(_tc.outputs["Generated"], _sep.inputs["Vector"])
_nz = _w.nodes.new("ShaderNodeTexNoise"); _nz.inputs["Scale"].default_value = 6.0
_w.links.new(_tc.outputs["Generated"], _nz.inputs["Vector"])
_mx = _w.nodes.new("ShaderNodeMath"); _mx.operation = "ADD"
_w.links.new(_sep.outputs["Z"], _mx.inputs[0])
_w.links.new(_nz.outputs["Fac"], _mx.inputs[1])
_rp = _w.nodes.new("ShaderNodeValToRGB")
_rp.color_ramp.elements[0].position = 0.75; _rp.color_ramp.elements[0].color = (0.16, 0.30, 0.10, 1)
_rp.color_ramp.elements[1].position = 1.05; _rp.color_ramp.elements[1].color = (0.80, 0.88, 1.00, 1)
_w.links.new(_mx.outputs[0], _rp.inputs["Fac"])
_w.links.new(_rp.outputs["Color"], _wb.inputs["Emission Color"])
_w.links.new(_rp.outputs["Color"], _wb.inputs["Base Color"])
_f = MAT["frosted"].node_tree.nodes["Principled BSDF"]
_f.inputs["Transmission Weight"].default_value = 1.0
_f.inputs["IOR"].default_value = 1.49

SMOOTH_ALL = {"leaf_a", "leaf_b", "leaf_c", "stem", "pepper_red", "pepper_green", "soil",
              "leaf_purple", "leaf_purple2", "leaf_thai", "leaf_mint", "leaf_mint2", "leaf_parsley",
              "leaf_parsley2", "leaf_thyme", "leaf_oregano", "leaf_lettuce", "leaf_lettuce2", "leaf_lettuce_red",
              "chive", "flower_purple", "stem_purple", "stem_woody", "stem_light", "pepper_yellow", "pepper_orange"}


def make_obj(name, V, F):
    me = bpy.data.meshes.new(name)
    try:
        nv, nf = len(V), len(F)
        me.vertices.add(nv)
        me.vertices.foreach_set("co", V.astype(np.float32).ravel())
        me.loops.add(nf * 3)
        me.loops.foreach_set("vertex_index", F.astype(np.int32).ravel())
        me.polygons.add(nf)
        me.polygons.foreach_set("loop_start", np.arange(0, nf * 3, 3, dtype=np.int32))
        me.update(calc_edges=True)
        me.validate(clean_customdata=False)
    except Exception as e:
        print("foreach_set failed, from_pydata:", e)
        me = bpy.data.meshes.new(name)
        me.from_pydata(V.tolist(), [], F.tolist())
        me.update()
    ob = bpy.data.objects.new(name, me)
    scn.collection.objects.link(ob)
    me.materials.append(MAT.get(name.split("#")[0], MAT["alu"]))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    if name.split("#")[0] not in SMOOTH_ALL:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        try:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(32))
        except Exception as e:
            print("smooth by angle unavailable:", e)
    return ob


for key in data.files:
    if key.startswith("V_"):
        nm = key[2:]
        make_obj(nm, data["V_" + nm], data["F_" + nm])
        print("mesh", nm, len(data["F_" + nm]), flush=True)

# room: floor and the wall behind the cabinet
if "V_room_floor" not in data.files:      # older scene files: a plain floor and wall
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0.7, 1.0, 0.0))
    fl = bpy.context.active_object; fl.name = "floor"; fl.data.materials.append(MAT["floor"])
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0.7, meta["wall_y"], 3.0), rotation=(math.pi / 2, 0, 0))
    wl = bpy.context.active_object; wl.name = "wall"; wl.data.materials.append(MAT["wall"])


# ---------------------------------------------------------------- humidity
def mist(peak=meta.get("mist", 1.1), base=meta.get("mist_base", 0.05)):
    """Volumetric haze inside the enclosure: wispy noise, densest in a band
    just above each tray (where the humidifier's fog pools), fading to
    nothing at the open front."""
    x0, x1, y0, y1, z0, z1 = 0.041, 1.356, 0.0, 0.556, 0.045, 1.79
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    ob = bpy.context.active_object
    ob.name = "mist"
    ob.scale = (x1 - x0, y1 - y0, z1 - z0)
    m = bpy.data.materials.new("mist")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    out = N("ShaderNodeOutputMaterial")
    vol = N("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.93, 0.96, 1.0, 1.0)
    vol.inputs["Anisotropy"].default_value = 0.35
    geo = N("ShaderNodeNewGeometry")
    nz = N("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.2
    nz.inputs["Detail"].default_value = 5.0
    nz.inputs["Roughness"].default_value = 0.6
    nz.inputs["Distortion"].default_value = 0.9
    L(geo.outputs["Position"], nz.inputs["Vector"])
    ramp = N("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[1].position = 0.78
    L(nz.outputs["Fac"], ramp.inputs["Fac"])
    sep = N("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs["Vector"])

    def math_(op, a, b=None):
        n = N("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]
    band = None
    for zt in (0.345 + 0.085, 1.007 + 0.085, 1.437 + 0.085):     # just above each tray
        g = math_("EXPONENT", math_("MULTIPLY", math_("POWER", math_("DIVIDE", math_("SUBTRACT", sep.outputs["Z"], zt), 0.10), 2.0), -1.0))
        band = g if band is None else math_("ADD", band, g)
    front = N("ShaderNodeMapRange")
    front.inputs["From Min"].default_value = 0.0
    front.inputs["From Max"].default_value = 0.12
    L(sep.outputs["Y"], front.inputs["Value"])
    dens = math_("ADD", math_("MULTIPLY", math_("MULTIPLY", ramp.outputs["Color"], math_("ADD", band, 0.25)), peak), base)
    dens = math_("MULTIPLY", dens, front.outputs["Result"])
    L(dens, vol.inputs["Density"])
    L(vol.outputs["Volume"], out.inputs["Volume"])
    ob.data.materials.append(m)
    return ob


if meta.get("mist", 1.1) > 0:
    mist()

# ---------------------------------------------------------------- lights
def area(name, loc, target, size, power, color=(1, 1, 1), shape="RECTANGLE", size_y=None):
    L = bpy.data.lights.new(name, "AREA")
    L.shape = shape
    L.size = size
    if size_y:
        L.size_y = size_y
    L.energy = power
    L.color = color
    ob = bpy.data.objects.new(name, L)
    scn.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


area("key", (-1.6, -2.2, 2.6), (0.7, 0.2, 1.1), 1.8, meta.get("key", 420), (1.0, 0.97, 0.93), size_y=1.2)
area("fill", (2.8, -1.8, 1.2), (0.8, 0.2, 1.0), 2.0, meta.get("fill", 110), (0.92, 0.95, 1.0), size_y=1.2)
area("top", (0.7, -0.6, 2.8), (0.7, 0.3, 0.9), 2.0, meta.get("top", 60), (1.0, 1.0, 1.0), size_y=1.0)

w = bpy.data.worlds.new("world")
scn.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.42, 0.44, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = meta.get("world", 0.12)

# ---------------------------------------------------------------- camera
cam = meta["camera"]
if a.cam:
    cam.update(json.loads(a.cam))
cd = bpy.data.cameras.new("cam")
cd.lens = cam["lens"]
cd.sensor_width = 36.0
cd.dof.use_dof = True
cd.dof.aperture_fstop = cam.get("fstop", 5.6)
co = bpy.data.objects.new("cam", cd)
scn.collection.objects.link(co)
co.location = cam["loc"]
d = Vector(cam["target"]) - Vector(cam["loc"])
co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cd.dof.focus_distance = (Vector(cam["focus"]) - Vector(cam["loc"])).length
cd.shift_x = cam.get("shift_x", 0.0)
cd.shift_y = cam.get("shift_y", 0.0)
scn.camera = co

# ---------------------------------------------------------------- render
scn.render.engine = "CYCLES"
scn.cycles.samples = a.samples
scn.cycles.volume_step_rate = 1.0
scn.cycles.volume_max_steps = 512
scn.cycles.max_bounces = 16
scn.cycles.transmission_bounces = 16
scn.cycles.volume_bounces = 2
scn.cycles.use_denoising = True
try:
    scn.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass
prefs = bpy.context.preferences.addons["cycles"].preferences
dev = "NONE"
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d_ in prefs.devices:
                d_.use = d_.type == kind
            dev = kind
            break
    except Exception as e:
        print("device", kind, e)
scn.cycles.device = "GPU" if dev != "NONE" else "CPU"
print("render device:", dev, flush=True)
scn.render.resolution_x, scn.render.resolution_y = a.res
scn.render.resolution_percentage = 100
scn.render.film_transparent = False
try:
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scn.view_settings.exposure = cam.get("exposure", 0.0)
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = os.path.abspath(a.out)
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(os.path.abspath(a.out))[0] + ".blend")
bpy.ops.render.render(write_still=True)
print("DONE", scn.render.filepath, flush=True)
