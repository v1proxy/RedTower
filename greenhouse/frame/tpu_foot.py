"""
TPU feet for T-slot aluminium extrusion, parametric generator.

Presets: 2020 (Red Tower bedside table, built 2026-10-18) and 4040 (the Maag
cabinet's four uprights). Printed in SUNLU TPU 95A Clear.

The 4040 foot is the 2020 foot scaled x2 across, with the height kept at
20 mm (Vittorio, 2026-10-19). Its pin goes into the upright's centre bore,
which nobody has measured yet: industrial slot-8 4040 is cored for an M8
tap (about 6.8), generic profiles are often 8.4 or 10.5. So every bore in
BORES gets its own fit-test coupon. Print the coupons, keep the one that
grips, set BORE_D to it and print the four feet.

Units are millimetres: 1 Blender unit = 1 mm, and the STLs open at true
size in any slicer.

How to use
  Plain Python:  python tpu_foot.py <out_dir> [--profile 4040] [--bore 8.4]
  Blender:       blender -b --factory-startup --python tpu_foot.py -- <out_dir> [--profile 4040]
  From code:     import tpu_foot as T; T.use("4040", bore=8.4); V, F = T.build_foot()

The foot is one closed, watertight mesh (no booleans): rounded-square rings
for the body, a polar zipper across the top face, revolved rings for the
barbed pin. It slices cleanly every time.
"""
import math
import os
import struct
import sys

# ---------------- PARAMETERS (mm) ----------------
PRESETS = {
    # bedside table, SeekLiny 2020: bore and corner measured from the photo
    "2020": dict(SIZE=20.0, CORNER_R=1.2, BORES=(5.0,),
                 PIN_LEN=10.0, N_BARBS=3, BARB_INTERF=0.4, CORE_CLEAR=0.2,
                 LEAD_IN=0.8, TIP_GAP=1.0, EDGE_SEGS=12, CORNER_SEGS=8),
    # Maag, EU slot-8 4040: the 2020 foot x2 across, height kept at 20.
    # Bore unmeasured: 6.8 (cored for M8), 8.4 and 10.5 are all in the wild.
    "4040": dict(SIZE=40.0, CORNER_R=2.4, BORES=(6.8, 8.4, 10.5),
                 PIN_LEN=20.0, N_BARBS=4, BARB_INTERF=0.5, CORE_CLEAR=0.3,
                 LEAD_IN=1.2, TIP_GAP=1.2, EDGE_SEGS=16, CORNER_SEGS=10),
}
PROFILE = "4040"

HEIGHT = 20.0          # foot height, same for every preset
BOTTOM_CHAMFER = 0.5   # elephant-foot relief on the bed side
TOP_CHAMFER = 0.4      # small reveal where the profile sits

# PETG pin (optional): vertical crush ribs that shave to fit, for rigid filament
RIB_INTERF = 0.2       # rib crest is this much bigger than the bore
N_RIBS = 6
RIB_WIDTH = 0.7        # rib base width
RIB_FADE = 1.0         # ribs ramp in over this length below the lead-in

MATERIALS = ("TPU",)          # add "PETG" for a rigid crush-rib version
DENSITY = {"TPU": 1.21, "PETG": 1.27}   # g/cm3, for the mass estimate

FIT_TEST_HEIGHT = 3.0  # quick coupon: same pin on a thin base
PIN_SEGS = 144         # resolution of the pin (multiple of N_RIBS)
# -------------------------------------------------


def use(profile, bore=None):
    """Load a preset into the module globals; the bore defaults to the first."""
    p = PRESETS[profile]
    g = globals()
    g["PROFILE"] = profile
    for k, v in p.items():
        g[k] = v
    g["PLATE_PITCH"] = p["SIZE"] + 10.0
    set_bore(bore if bore is not None else p["BORES"][0])


def set_bore(bore):
    g = globals()
    g["BORE_D"] = float(bore)
    g["TIP_D"] = float(bore) - g["TIP_GAP"]


use(PROFILE)

TAU = 2.0 * math.pi


def pin_profile(material="TPU"):
    """(radius, height above top face, rib fraction) from root to tip."""
    rc = (BORE_D - CORE_CLEAR) / 2.0
    rt = TIP_D / 2.0
    if material == "PETG":
        z_lead = PIN_LEN - LEAD_IN
        pts = [(rc, 0.0, 1.0), (rc, z_lead - RIB_FADE, 1.0), (rc, z_lead, 0.0), (rt, PIN_LEN, 0.0)]
    elif N_BARBS <= 0:
        rp = (BORE_D + BARB_INTERF / 2.0) / 2.0
        pts = [(rp, 0.0, 0.0), (rp, PIN_LEN - LEAD_IN, 0.0), (rt, PIN_LEN, 0.0)]
    else:
        rb = (BORE_D + BARB_INTERF) / 2.0
        sh = rb - rc                      # 45 degree shoulder
        z0 = 0.4
        z1 = PIN_LEN - LEAD_IN - 0.2
        pitch = (z1 - z0) / N_BARBS
        ramp = pitch - sh - 0.2
        if ramp <= sh:
            raise ValueError("Pin too short for %d barbs" % N_BARBS)
        pts = [(rc, 0.0, 0.0)]
        for k in range(N_BARBS):
            s = z0 + k * pitch
            # sharp shoulder facing the foot, long ramp facing the tip:
            # easy to push on, hard to pull off
            pts += [(rc, s, 0.0), (rb, s + sh, 0.0), (rc, s + sh + ramp, 0.0)]
        pts += [(rc, PIN_LEN - LEAD_IN, 0.0), (rt, PIN_LEN, 0.0)]
    out = []
    for p in pts:
        if not out or any(abs(a - b) > 1e-9 for a, b in zip(p, out[-1])):
            out.append(p)
    return out


def pin_ring(r, frac, n):
    """2D points of one pin ring; crush ribs scaled by frac."""
    h = frac * ((BORE_D + RIB_INTERF) / 2.0 - r) if frac > 0 else 0.0
    half_ang = (RIB_WIDTH / 2.0) / r
    pitch = TAU / N_RIBS
    pts = []
    for j in range(n):
        a = TAU * j / n
        phi = abs(((a + pitch / 2.0) % pitch) - pitch / 2.0)   # distance to nearest rib
        rr = r + h * max(0.0, 1.0 - phi / half_ang)
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return pts


def rounded_square(half, r, cs, es):
    """CCW loop of (x, y, nx, ny) on a rounded square, outward normals."""
    c = half - r
    centers = [(c, c), (-c, c), (-c, -c), (c, -c)]
    pts = []
    for k, (cx, cy) in enumerate(centers):
        a0 = math.pi / 2.0 * k
        for j in range(cs + 1):
            a = a0 + (math.pi / 2.0) * j / cs
            nx, ny = math.cos(a), math.sin(a)
            pts.append((cx + r * nx, cy + r * ny, nx, ny))
        nxt = centers[(k + 1) % 4]
        a1 = a0 + math.pi / 2.0
        nx, ny = math.cos(a1), math.sin(a1)
        sx, sy = cx + r * nx, cy + r * ny
        ex, ey = nxt[0] + r * nx, nxt[1] + r * ny
        for j in range(1, es):
            t = j / es
            pts.append((sx + (ex - sx) * t, sy + (ey - sy) * t, nx, ny))
    return pts


def build_foot(height=HEIGHT, material="TPU"):
    """Return (verts, faces) of one closed foot. Bottom face at z = 0."""
    half = SIZE / 2.0
    if CORNER_R <= max(BOTTOM_CHAMFER, TOP_CHAMFER) + 0.05:
        raise ValueError("CORNER_R must be larger than both chamfers")
    if height <= BOTTOM_CHAMFER + TOP_CHAMFER + 0.5:
        raise ValueError("Foot too short for its chamfers")

    loop = rounded_square(half, CORNER_R, CORNER_SEGS, EDGE_SEGS)
    ang = [math.atan2(p[1], p[0]) % TAU for p in loop]
    s = min(range(len(loop)), key=lambda i: ang[i])
    loop = loop[s:] + loop[:s]            # start on the +X face, angle 0

    verts, faces = [], []

    def ring(pts2d, z):
        i0 = len(verts)
        verts.extend((x, y, z) for x, y in pts2d)
        return list(range(i0, len(verts)))

    def inset(d):
        return [(x - d * nx, y - d * ny) for x, y, nx, ny in loop]

    levels = []
    if BOTTOM_CHAMFER > 0:
        levels.append((0.0, BOTTOM_CHAMFER))
    levels.append((BOTTOM_CHAMFER, 0.0))
    if TOP_CHAMFER > 0:
        levels.append((height - TOP_CHAMFER, 0.0))
    levels.append((height, TOP_CHAMFER))
    rings = [ring(inset(d), z) for z, d in levels]
    M = len(rings[0])

    # bottom cap, fan around the centre
    cb = len(verts)
    verts.append((0.0, 0.0, 0.0))
    r0 = rings[0]
    for i in range(M):
        faces.append((cb, r0[(i + 1) % M], r0[i]))

    # body walls
    for a, b in zip(rings, rings[1:]):
        for i in range(M):
            i1 = (i + 1) % M
            faces.append((a[i], a[i1], b[i1], b[i]))

    # pin rings
    prof = pin_profile(material)
    N = PIN_SEGS
    pin_rings = [ring(pin_ring(r, frac, N), height + dz) for r, dz, frac in prof]

    # top face: polar zipper between the body's top ring and the pin root
    O, C = rings[-1], pin_rings[0]
    oa = [math.atan2(verts[k][1], verts[k][0]) % TAU for k in O]
    ob = oa + [oa[0] + TAU]
    cbk = [TAU * j / N for j in range(N)] + [TAU]
    i = j = 0
    while i < M or j < N:
        if j == N or (i < M and ob[i + 1] <= cbk[j + 1]):
            faces.append((O[i], O[(i + 1) % M], C[j % N]))
            i += 1
        else:
            faces.append((O[i % M], C[(j + 1) % N], C[j]))
            j += 1

    # pin walls
    for a, b in zip(pin_rings, pin_rings[1:]):
        for k in range(N):
            k1 = (k + 1) % N
            faces.append((a[k], a[k1], b[k1], b[k]))

    # pin tip cap
    ct = len(verts)
    verts.append((0.0, 0.0, height + prof[-1][1]))
    t = pin_rings[-1]
    for k in range(N):
        faces.append((ct, t[k], t[(k + 1) % N]))
    return verts, faces


def triangles(verts, faces, offset=(0.0, 0.0, 0.0)):
    ox, oy, oz = offset
    out = []
    for f in faces:
        p = [(verts[k][0] + ox, verts[k][1] + oy, verts[k][2] + oz) for k in f]
        for k in range(1, len(p) - 1):
            out.append((p[0], p[k], p[k + 1]))
    return out


def check_mesh(verts, faces, density=1.21):
    """Watertight test, signed volume and bounding box."""
    edges = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            edges[(a, b)] = edges.get((a, b), 0) + 1
    bad = sum(1 for (a, b), n in edges.items() if n != 1 or edges.get((b, a), 0) != 1)
    vol = 0.0
    for p0, p1, p2 in triangles(verts, faces):
        vol += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6.0
    xs, ys, zs = zip(*verts)
    return {
        "watertight": bad == 0,
        "bad_edges": bad,
        "volume_mm3": round(vol, 1),
        "mass_g_at_100pct": round(vol / 1000.0 * density, 1),
        "bbox_mm": [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3)],
        "verts": len(verts),
        "faces": len(faces),
    }


def write_stl(path, tris, name="tpu_foot"):
    with open(path, "wb") as fh:
        fh.write(name.encode("ascii")[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fh.write(struct.pack("<12fH", nx / ln, ny / ln, nz / ln, *a, *b, *c, 0))


def export_stls(out_dir, bores=None):
    """Foot, 2 x 2 plate and fit-test coupon for every bore in `bores`
    (default: the preset's BORES), named foot_<profile>_b<bore>_<mat>*.stl."""
    os.makedirs(out_dir, exist_ok=True)
    report = {}
    keep = BORE_D
    for bore in (bores or BORES):
        set_bore(bore)
        for mat in MATERIALS:
            tag = "%s_b%s_%s" % (PROFILE, ("%g" % bore), mat.lower())
            v, f = build_foot(HEIGHT, mat)
            tv, tf = build_foot(FIT_TEST_HEIGHT, mat)
            write_stl(os.path.join(out_dir, "foot_%s.stl" % tag), triangles(v, f), "foot_" + tag)
            plate = []
            for ix in (-0.5, 0.5):
                for iy in (-0.5, 0.5):
                    plate += triangles(v, f, (ix * PLATE_PITCH, iy * PLATE_PITCH, 0.0))
            write_stl(os.path.join(out_dir, "foot_%s_x4.stl" % tag), plate, "foot_%s_x4" % tag)
            write_stl(os.path.join(out_dir, "foot_%s_fit_test.stl" % tag), triangles(tv, tf), "fit_" + tag)
            rho = DENSITY.get(mat, 1.25)
            report[tag] = {"foot": check_mesh(v, f, rho), "fit_test": check_mesh(tv, tf, rho),
                           "pin_profile": pin_profile(mat)}
    set_bore(keep)
    return report


# ---------------- Blender part ----------------

# T-slot cavity, (across, depth) from the face. 2020: B-type slot 6.
# 4040: EU slot 8, the same section the Maag cabinet model draws
# (greenhouse/frame/cabinet.py, SLOT8).
CAVITY = {
    "2020": [(-3.1, 0.0), (-3.1, 1.8), (-6.0, 1.8), (-6.0, 2.6), (-2.5, 6.1),
             (2.5, 6.1), (6.0, 2.6), (6.0, 1.8), (3.1, 1.8), (3.1, 0.0)],
    "4040": [(-4.1, 0.0), (-4.1, 4.3), (-8.25, 4.3), (-8.25, 7.0), (-3.0, 12.25),
             (3.0, 12.25), (8.25, 7.0), (8.25, 4.3), (4.1, 4.3), (4.1, 0.0)],
}


def profile_outline(half=10.0, r=1.2, seg=8):
    """The profile's outline as one polygon, slots as notches, outer corners
    rounded to r, the same radius as the foot."""
    cav = CAVITY[PROFILE]
    sides = [((0, -half), (1, 0), (0, 1), (half, -half)),
             ((half, 0), (0, 1), (-1, 0), (half, half)),
             ((0, half), (-1, 0), (0, -1), (-half, half)),
             ((-half, 0), (0, -1), (1, 0), (-half, -half))]
    out = []
    for k, (c, t, n, corner) in enumerate(sides):
        for u, v in cav:
            out.append((c[0] + u * t[0] + v * n[0], c[1] + u * t[1] + v * n[1]))
        cx = corner[0] - math.copysign(r, corner[0])
        cy = corner[1] - math.copysign(r, corner[1])
        a0 = -math.pi / 2.0 + k * math.pi / 2.0
        for j in range(seg + 1):
            a = a0 + (math.pi / 2.0) * j / seg
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def build_blender(out_dir):
    import bpy
    from mathutils import Vector

    sc = bpy.context.scene
    us = sc.unit_settings
    us.system = "METRIC"
    us.scale_length = 0.001
    us.length_unit = "MILLIMETERS"

    if bpy.app.background and not bpy.data.filepath:
        for name in ("Cube",):
            ob = bpy.data.objects.get(name)
            if ob:
                bpy.data.objects.remove(ob, do_unlink=True)

    def fresh_collection(name, parent):
        c = bpy.data.collections.get(name)
        if c is None:
            c = bpy.data.collections.new(name)
            parent.children.link(c)
        for ob in list(c.objects):
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)
        return c

    def material(name, rgba, metal=0.0, rough=0.5):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.diffuse_color = rgba
        m.metallic = metal
        m.roughness = rough
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
            bsdf.inputs["Metallic"].default_value = metal
            bsdf.inputs["Roughness"].default_value = rough
        return m

    def mesh_object(name, verts, faces, coll, mat, loc):
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.validate()
        me.update()
        try:
            me.shade_smooth()
            me.set_sharp_from_angle(angle=math.radians(35))
        except Exception:
            pass
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        ob.location = loc
        coll.objects.link(ob)
        return ob

    root = sc.collection
    feet = fresh_collection("TPU Feet", root)
    ref = fresh_collection("Reference (not printed)", root)

    mats = {
        "TPU": material("TPU_95A_clear", (0.93, 0.95, 0.95, 1.0), 0.0, 0.6),
        "PETG": material("PETG_clear", (0.70, 0.82, 0.88, 1.0), 0.0, 0.15),
    }
    alu = material("Aluminium_profile", (0.50, 0.52, 0.55, 1.0), 0.0, 0.35)

    layout = {  # foot location, fit-test location
        "TPU": ((0.0, 0.0, 0.0), (28.0, -10.0, 0.0)),
        "PETG": ((-30.0, 0.0, 0.0), (-2.0, -24.0, 0.0)),
    }
    objs = {}
    report = {}
    for mat in MATERIALS:
        v, f = build_foot(HEIGHT, mat)
        tv, tf = build_foot(FIT_TEST_HEIGHT, mat)
        loc, tloc = layout.get(mat, ((0.0, 30.0 * len(objs), 0.0), (30.0, 30.0 * len(objs), 0.0)))
        objs[mat] = (mesh_object("Foot_%s_" % PROFILE + mat, v, f, feet, mats[mat], loc),
                     mesh_object("Foot_FitTest_" + mat, tv, tf, feet, mats[mat], tloc))
        rho = DENSITY.get(mat, 1.25)
        report[mat] = {"foot": check_mesh(v, f, rho), "fit_test": check_mesh(tv, tf, rho)}

    # reference 2020 stub, exploded above the foot
    L, gap = 2.0 * SIZE, PIN_LEN + 6.0
    cu = bpy.data.curves.new("Profile_%s_ref" % PROFILE, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = L / 2.0
    outline = profile_outline(SIZE / 2.0, CORNER_R)
    sp = cu.splines.new("POLY")
    sp.points.add(len(outline) - 1)
    for p, (x, y) in zip(sp.points, outline):
        p.co = (x, y, 0.0, 1.0)
    sp.use_cyclic_u = True
    hole = cu.splines.new("POLY")
    n = 64
    hole.points.add(n - 1)
    for k, p in enumerate(hole.points):
        a = TAU * k / n
        p.co = (BORE_D / 2.0 * math.cos(a), BORE_D / 2.0 * math.sin(a), 0.0, 1.0)
    hole.use_cyclic_u = True
    cu.materials.append(alu)
    prof = bpy.data.objects.new("Profile_%s_ref" % PROFILE, cu)
    prof.location = (0.0, 0.0, HEIGHT + gap + L / 2.0)
    ref.objects.link(prof)

    # viewport framing for when the file is opened
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                space.clip_start = 0.1
                space.clip_end = 10000.0
                r3d = getattr(space, "region_3d", None)
                if r3d is not None:
                    r3d.view_location = (10.0, -4.0, 32.0)
                    r3d.view_distance = 190.0

    if out_dir:
        report["stl"] = export_stls(out_dir) and "written"

    if bpy.app.background and out_dir:
        # embed this script so it can be re-run from the Text Editor
        try:
            src = open(__file__, "r", encoding="utf-8").read()
            t = bpy.data.texts.get("tpu_foot.py") or bpy.data.texts.new("tpu_foot.py")
            t.from_string(src)
        except Exception as e:
            report["embed_error"] = str(e)

        # previews, Workbench
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = True
        sh.show_shadows = True
        sh.show_object_outline = True
        sc.display.render_aa = "16"
        if sc.world is None:
            sc.world = bpy.data.worlds.new("World")
        sc.world.color = (0.78, 0.79, 0.81)
        sc.render.resolution_x = 1200
        sc.render.resolution_y = 1500
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"

        cam_data = bpy.data.cameras.new("Cam_TPU")
        cam_data.lens = 50
        cam_data.clip_start = 1.0
        cam_data.clip_end = 10000.0
        cam = bpy.data.objects.new("Cam_TPU", cam_data)
        ref.objects.link(cam)
        sc.camera = cam

        everything = [o for pair in objs.values() for o in pair] + [prof]

        def shot(path, target, direction, dist, show):
            for ob in everything:
                ob.hide_render = ob not in show
            d = Vector(direction).normalized()
            cam.location = Vector(target) + d * dist
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)

        try:
            shot(os.path.join(out_dir, "render_assembly.png"), (10, -4, 36), (1.0, -1.35, 0.5), 215, everything)
            for mat in MATERIALS:
                foot_ob = objs[mat][0]
                tgt = foot_ob.location + Vector((0, 0, HEIGHT + PIN_LEN * 0.35))
                shot(os.path.join(out_dir, "render_pin_%s.png" % mat.lower()), tgt, (1.0, -1.15, 0.8), 56, [foot_ob])
            report["renders"] = "ok"
        except Exception as e:
            report["render_error"] = str(e)
        for ob in everything:
            ob.hide_render = False

        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "tpu_foot_%s.blend" % PROFILE))

    print("TPU_FOOT_REPORT", report)
    return report


def _args(argv):
    """<out_dir> [--profile 2020|4040] [--bore D]"""
    out, prof, bore = None, PROFILE, None
    i = 0
    while i < len(argv):
        if argv[i] == "--profile":
            prof = argv[i + 1]; i += 2; continue
        if argv[i] == "--bore":
            bore = float(argv[i + 1]); i += 2; continue
        out = argv[i]; i += 1
    use(prof, bore)
    return out, ([bore] if bore else None)


def main():
    try:
        import bpy  # noqa: F401
    except ImportError:
        out, bores = _args(sys.argv[1:])
        print("TPU_FOOT_REPORT", export_stls(out or os.getcwd(), bores))
        return
    import bpy
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    argv_out, _b = _args(argv)
    argv = [argv_out] if argv_out else []
    if argv:
        out = argv[0]
    elif bpy.data.filepath:
        out = os.path.dirname(bpy.data.filepath)
    else:
        out = None
    build_blender(out)


if __name__ == "__main__":
    main()
