#!/usr/bin/env python3
"""Build a rigged, IK-driven myCobot 280 Pi in Blender and save it as a .blend.

Run inside Blender (its Python), either through the MCP addon or:
    blender --background --python rig_mycobot.py

Geometry is Elephant Robotics' own COLLADA from mycobot_description; the bone
positions, axes and rotation limits are read from mycobot_280_pi.urdf, so the
rig matches the real robot rather than an eyeballed skeleton.

Result: an armature "myCobot280" with six revolute bones plus a flange, an IK
constraint on the wrist driven by an empty called "IK_target", a pole target
"IK_pole", and per-bone limits taken from the URDF. Move IK_target and the arm
follows it the way the real one would.
"""
import os, math, sys
import xml.etree.ElementTree as ET

import bpy
from mathutils import Matrix, Vector, Euler

# ----------------------------------------------------------------- settings
MESH_DIR = os.environ.get("MYCOBOT_MESH",
                          r"C:\Users\archv\greenhouse-esphome\mycobot_mesh")
URDF = os.path.join(MESH_DIR, "mycobot_280_pi.urdf")
OUT = os.environ.get("MYCOBOT_BLEND",
                     os.path.join(MESH_DIR, "mycobot280_rigged.blend"))
IK_CHAIN = 5          # bones from the wrist back that the solver may move

BONES = [  # bone name, the URDF joint that positions it, the link it carries
    ("J1", "g_base_to_joint1", "joint1"),
    ("J2", "joint2_to_joint1", "joint2"),
    ("J3", "joint3_to_joint2", "joint3"),
    ("J4", "joint4_to_joint3", "joint4"),
    ("J5", "joint5_to_joint4", "joint5"),
    ("J6", "joint6_to_joint5", "joint6"),
    ("FLANGE", "joint6output_to_joint6", "joint6_flange"),
]


def rpy_matrix(r, p, y):
    return Euler((r, p, y), "XYZ").to_matrix().to_4x4()


def read_urdf(path):
    root = ET.parse(path).getroot()
    links, joints = {}, {}
    for l in root.findall("link"):
        v = l.find("visual")
        if v is None:
            continue
        m = v.find("geometry/mesh")
        o = v.find("origin")
        xyz = [float(x) for x in (o.get("xyz", "0 0 0").split())] if o is not None else [0]*3
        rpy = [float(x) for x in (o.get("rpy", "0 0 0").split())] if o is not None else [0]*3
        links[l.get("name")] = dict(mesh=os.path.basename(m.get("filename")),
                                    xyz=xyz, rpy=rpy)
    for j in root.findall("joint"):
        o, a, lim = j.find("origin"), j.find("axis"), j.find("limit")
        xyz = [float(x) for x in (o.get("xyz", "0 0 0").split())] if o is not None else [0]*3
        rpy = [float(x) for x in (o.get("rpy", "0 0 0").split())] if o is not None else [0]*3
        joints[j.get("name")] = dict(
            type=j.get("type"), parent=j.find("parent").get("link"),
            child=j.find("child").get("link"), xyz=xyz, rpy=rpy,
            axis=[float(x) for x in (a.get("xyz", "0 0 1").split())] if a is not None else [0, 0, 1],
            lower=float(lim.get("lower")) if lim is not None else None,
            upper=float(lim.get("upper")) if lim is not None else None)
    return links, joints


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"


def import_link(mesh_file, name):
    """Import one .dae and return a single joined object named `name`."""
    before = set(bpy.data.objects)
    bpy.ops.wm.collada_import(filepath=os.path.join(MESH_DIR, mesh_file))
    new = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
    for o in set(bpy.data.objects) - before:
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    if not new:
        raise RuntimeError(f"no mesh came out of {mesh_file}")
    for o in new:
        o.select_set(True)
    bpy.context.view_layer.objects.active = new[0]
    if len(new) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    # COLLADA import leaves a transform on the object; bake it in
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def build():
    links, joints = read_urdf(URDF)
    fresh_scene()

    # --- world transform of every link, following the URDF chain
    world, order = {"g_base": Matrix.Identity(4)}, []
    for bname, jname, lname in BONES:
        j = joints[jname]
        M = (Matrix.Translation(Vector(j["xyz"])) @ rpy_matrix(*j["rpy"]))
        world[j["child"]] = world[j["parent"]] @ M
        order.append((bname, jname, lname, world[j["child"]]))

    # --- meshes, each placed in world space
    objs = {}
    for lname, info in links.items():
        o = import_link(info["mesh"], f"mesh_{lname}")
        local = Matrix.Translation(Vector(info["xyz"])) @ rpy_matrix(*info["rpy"])
        o.matrix_world = world.get(lname, Matrix.Identity(4)) @ local
        objs[lname] = o

    # --- armature, one bone per revolute joint, heads at the real joint origins
    arm_data = bpy.data.armatures.new("myCobot280")
    arm = bpy.data.objects.new("myCobot280", arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")

    eb, prev = {}, None
    for i, (bname, jname, lname, W) in enumerate(order):
        b = arm_data.edit_bones.new(bname)
        head = W.translation
        nxt = order[i + 1][3].translation if i + 1 < len(order) else None
        # point the bone at the next joint; fall back to its own local Z
        if nxt is not None and (nxt - head).length > 1e-5:
            tail = nxt
        else:
            tail = head + (W.to_3x3() @ Vector((0, 0, 0.03)))
        b.head, b.tail = head, tail
        b.align_roll(W.to_3x3() @ Vector((0, 0, 1)))   # roll so local Z is the joint axis
        if prev is not None:
            b.parent = prev
            b.use_connect = (prev.tail - b.head).length < 1e-6
        eb[bname] = b
        prev = b
    bpy.ops.object.mode_set(mode="OBJECT")

    # --- skin: parent each mesh rigidly to its bone
    for bname, jname, lname, W in order:
        o = objs.get(lname)
        if o is None:
            continue
        o.parent = arm
        o.parent_type = "BONE"
        o.parent_bone = bname
        o.matrix_parent_inverse = (arm.matrix_world @
                                   arm.pose.bones[bname].matrix @
                                   Matrix.Translation(Vector((0, arm.pose.bones[bname].length, 0)))).inverted()
    if "g_base" in objs:
        objs["g_base"].parent = arm

    # --- rotation limits straight off the URDF
    for bname, jname, lname, W in order:
        j = joints[jname]
        pb = arm.pose.bones[bname]
        pb.rotation_mode = "XYZ"
        if j["lower"] is None:
            continue
        c = pb.constraints.new("LIMIT_ROTATION")
        c.use_limit_x = c.use_limit_y = True
        c.min_x = c.max_x = c.min_y = c.max_y = 0.0
        c.use_limit_z = True
        c.min_z, c.max_z = j["lower"], j["upper"]
        c.owner_space = "LOCAL"
        pb.lock_ik_x = pb.lock_ik_y = True       # revolute: local Z only
        pb.use_ik_limit_z = True
        pb.ik_min_z, pb.ik_max_z = j["lower"], j["upper"]

    # --- IK target and pole
    tip = order[-1][3].translation
    tgt = bpy.data.objects.new("IK_target", None)
    tgt.empty_display_type = "PLAIN_AXES"
    tgt.empty_display_size = 0.03
    tgt.location = tip
    bpy.context.collection.objects.link(tgt)

    pole = bpy.data.objects.new("IK_pole", None)
    pole.empty_display_type = "SPHERE"
    pole.empty_display_size = 0.02
    pole.location = order[1][3].translation + Vector((0.25, 0, 0.05))
    bpy.context.collection.objects.link(pole)

    pb = arm.pose.bones[order[-2][0]]            # solve to J6, flange rides along
    ik = pb.constraints.new("IK")
    ik.target = tgt
    ik.pole_target = pole
    ik.pole_angle = 0.0
    ik.chain_count = IK_CHAIN
    ik.use_tail = True

    arm["source"] = "elephantrobotics/mycobot_ros · mycobot_description"
    arm["urdf"] = os.path.basename(URDF)
    arm["note"] = "Bone positions, axes and limits read from the URDF. Move IK_target."

    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    return OUT, len(order), [o.name for o in objs.values()]


if __name__ == "__main__":
    path, nb, meshes = build()
    print(f"saved {path}  bones={nb}  meshes={len(meshes)}")
