#!/usr/bin/env python3
"""Robot supervisor: the only process allowed to move the gantry or the arm.

Accepts task commands from Home Assistant on greenhouse/robot/cmd, re-checks the interlocks
it can see, drives the FluidNC gantry (G-code over USB serial) and the myCobot 280 Pi
(pymycobot over the network), and publishes greenhouse/robot/busy for HA.

The hardware safety chain (door reeds + E-stop -> safety relay -> gantry and arm power)
is the real protection. This software check is a second layer, never the only one.

Tasks:
    home                      re-home the gantry
    inspect   [tier|plant]    park over each pot, capture a close-up, no decisions
    tend      [tier|plant]    capture, measure, ask Claude, act on what it allows
    harvest   <plant>         force a harvest attempt on the best leaf candidate
    prune     <plant>         force a tip pinch on the best tip candidate

The division of labour that matters: plant_perception measures the plant and produces
labelled candidate points; plant_tender asks Claude to pick one; this file is the only
thing that converts a chosen label into motion, and it refuses anything outside the
reach box or without a current hand-eye calibration.

pip install paho-mqtt pyserial pymycobot pyrealsense2 opencv-python anthropic
"""
import json
import threading
import time

import cv2
import numpy as np
import paho.mqtt.client as mqtt
import pyrealsense2 as rs
import serial
from pymycobot import MyCobot280Socket

import plant_perception as pp
import plant_tender as pt

CFG = json.load(open("/opt/greenhouse/robot.json"))
PREFIX = "homeassistant"
DEVICE = {"identifiers": ["greenhouse_robot"], "name": "Greenhouse Robot",
          "manufacturer": "RedTower", "model": "4080 gantry + myCobot 280 Pi"}

# Gantry coordinates (mm) of each tier's working height and each plant's X position.
TIER_Z = {"A": 180.0, "B": 830.0, "C": 1260.0}         # measure after assembly
PLANT_X = CFG["plant_x"]                                # e.g. {"A01": 95, ..., "C10": 1235}

# Arm base frame limits (mm). Anything outside is a bug or a bad calibration, not a plant.
BOX = CFG.get("reach_box", {"x": [-140, 140], "y": [-80, 260], "z": [-60, 240]})
TOOL_MM = float(CFG.get("tool_offset_mm", 45))          # flange face to fingertips, closed
EULER = CFG.get("handeye", {}).get("euler_order", "xyz")
CAM_TO_FLANGE = np.array(CFG["cam_to_flange"]) if CFG.get("cam_to_flange") else None

state = {"doors_open": True, "watering": True, "busy": False, "moisture": {}}
lock = threading.Lock()
CLOSEUPS = CFG.get("closeup_dir", "/opt/greenhouse/closeups")


class Wrist:
    """RealSense D405 on the arm flange: colour for the vision pass, depth for grasping.

    Useful range is roughly 70 mm to 500 mm. Inside 70 mm the depth image goes blank, so
    approach the last stretch on the arm's own kinematics, not on depth.
    """

    def __init__(self):
        self.pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 30)
        cfg.enable_stream(rs.stream.color, 848, 480, rs.format.bgr8, 30)
        self.profile = self.pipe.start(cfg)
        self.align = rs.align(rs.stream.color)

    def capture(self, pid):
        frames = self.align.process(self.pipe.wait_for_frames())
        color = np.asanyarray(frames.get_color_frame().get_data())
        depth = frames.get_depth_frame()
        cv2.imwrite(f"{CLOSEUPS}/{pid}_rgb.png", color)
        np.save(f"{CLOSEUPS}/{pid}_depth.npy", np.asanyarray(depth.get_data()))
        return color, depth

    def look(self, pid, settle=1.0):
        """Capture, then measure. Returns (geometry, annotated image) and saves the annotation."""
        time.sleep(settle)                         # let auto-exposure catch up after the move
        color, depth = self.capture(pid)
        geo, annotated = pp.from_realsense(pid, color, depth)
        cv2.imwrite(f"{CLOSEUPS}/{pid}_annotated.png", annotated)
        return geo, annotated

    def point_at(self, depth, u, v):
        """Pixel plus depth to a 3D point in camera coordinates, for a grasp pose."""
        z = depth.get_distance(int(u), int(v))
        if z <= 0.07 or z > 0.5:
            return None                            # outside the D405's honest range
        intr = depth.profile.as_video_stream_profile().intrinsics
        return rs.rs2_deproject_pixel_to_point(intr, [float(u), float(v)], z)


class Gantry:
    def __init__(self, port):
        self.s = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)
        self.cmd("$X")                                  # clear alarm after power-up

    def cmd(self, line, wait_ok=True):
        self.s.write((line + "\n").encode())
        while wait_ok:
            resp = self.s.readline().decode().strip()
            if resp.startswith("ok"):
                return
            if resp.startswith(("error", "ALARM")):
                raise RuntimeError(f"FluidNC: {resp}")

    def home(self):
        self.cmd("$H")

    def move(self, x=None, z=None, feed=3000):
        axes = "".join(f" {a}{v:.1f}" for a, v in (("X", x), ("Z", z)) if v is not None)
        self.cmd(f"G90 G1{axes} F{feed}")
        self.cmd("G4 P0")                               # wait until motion completes


class Arm:
    """myCobot wrapper that keeps every motion inside the reach box and settles before returning."""

    def __init__(self, ip):
        self.mc = MyCobot280Socket(ip, 9000)
        time.sleep(1)

    def angles(self, pose, speed=40, settle=2.5):
        self.mc.send_angles(list(pose), speed)
        time.sleep(settle)

    def coords(self):
        c = self.mc.get_coords()
        if not c or len(c) != 6:
            raise RuntimeError("the arm did not report coordinates; check power and alarm state")
        return list(c)

    def flange_T(self):
        from handeye_calibrate import coords_to_T
        return coords_to_T(self.coords(), EULER)

    def move_to(self, xyz_mm, speed=25, settle=2.5):
        x, y, z = (float(v) for v in xyz_mm)
        for name, v in (("x", x), ("y", y), ("z", z)):
            lo, hi = BOX[name]
            if not lo <= v <= hi:
                raise RuntimeError(f"refusing {name}={v:.0f} mm, outside the reach box {lo}..{hi}")
        rx, ry, rz = self.coords()[3:]      # keep the looking orientation: top-down over the pot
        self.mc.send_coords([x, y, z, rx, ry, rz], speed, 1)   # 1 = linear interpolation
        time.sleep(settle)

    def grip(self, closed, speed=40, settle=1.5):
        self.mc.set_gripper_state(1 if closed else 0, speed)
        time.sleep(settle)


def publish_busy(client, busy):
    client.publish("greenhouse/robot/busy", "ON" if busy else "OFF", retain=True)


def plants_in(target):
    """Resolve a task target into an ordered list of plant ids."""
    if target in PLANT_X:
        return [target]
    tiers = [target] if target in TIER_Z else list(TIER_Z)
    return [pid for t in tiers for pid in sorted(PLANT_X) if pid.startswith(t)]


def park_over(gantry, arm, pid):
    gantry.move(z=TIER_Z[pid[0]])
    gantry.move(x=PLANT_X[pid])
    arm.angles(CFG["pose_look"], 40)                   # D405 over the pot, about 200 mm off


def reach(arm, target):
    """Move the fingertips to a candidate point, approaching along its surface normal.

    The orientation stays as the looking pose, so the gripper comes down on the plant from
    above. That suits pinching a tip and taking a leaf; a side approach would need a wrist
    solve from the normal, which is the next thing to add if a plant ever needs it.
    """
    if CAM_TO_FLANGE is None:
        raise RuntimeError("no hand-eye calibration in robot.json; run handeye_calibrate.py first")
    p_mm, n = pt.camera_to_arm(target["point_m"], target["normal"], CAM_TO_FLANGE, arm.flange_T())
    standoff = float(target.get("approach_mm", 40))
    approach = p_mm + n * (standoff + TOOL_MM)
    contact = p_mm + n * TOOL_MM
    arm.move_to(approach, speed=30)
    arm.move_to(contact, speed=12)                     # slow for the last stretch, depth is blind here
    return approach, contact


def act(arm, decision, wrist, pid):
    """Carry out a decision the tender already cleared. Returns a short outcome string."""
    name = decision["action"]["action"]
    target = decision.get("target")

    if name == "closer_look":
        _, contact = reach(arm, {**target, "approach_mm": 90})
        geo, _ = wrist.look(pid, settle=1.2)
        arm.angles(CFG["pose_look"], 30)
        return f"second look: {geo.leaf_count} leaves, {geo.canopy_height_mm:.0f} mm canopy"

    if name in ("pinch_tip", "harvest_leaf", "remove_dead_leaf"):
        arm.grip(False)
        approach, _ = reach(arm, target)
        arm.grip(True)
        arm.move_to(approach, speed=12)                # pull straight back along the approach
        arm.angles(CFG["pose_drop"], 35)               # over the collection cup in the base bay
        arm.grip(False)
        arm.angles(CFG["pose_look"], 40)
        return f"{name} at {target['label']}"

    return name                                        # watering nudges and flags are HA's job


def run_task(client, gantry, arm, wrist, task, target):
    llm = None
    try:
        publish_busy(client, True)
        arm.angles(CFG["pose_stow"], 40, settle=3)     # folded inside the lane before any gantry move
        if task == "home":
            gantry.home()

        elif task == "inspect":
            for pid in plants_in(target):
                park_over(gantry, arm, pid)
                wrist.look(pid)
                arm.angles(CFG["pose_stow"], 40)

        elif task == "tend":
            import anthropic
            llm = anthropic.Anthropic(api_key=pt.CFG["anthropic_api_key"])
            for pid in plants_in(target):
                park_over(gantry, arm, pid)
                geo, annotated = wrist.look(pid)
                if not geo.ok:
                    client.publish("greenhouse/tender/skipped",
                                   json.dumps({"plant_id": pid, "reason": geo.reason}))
                    arm.angles(CFG["pose_stow"], 40)
                    continue

                decision = pt.consider(geo, annotated,
                                       soil_moisture_pct=state["moisture"].get(pid), llm=llm)
                outcome = None
                if decision["verdict"]["execute"] and decision.get("target"):
                    try:
                        outcome = act(arm, decision, wrist, pid)
                    except Exception as exc:           # one plant failing must not end the round
                        outcome = f"aborted: {exc}"
                        decision["verdict"]["execute"] = False
                        decision["verdict"]["blocked"] = str(exc)
                        arm.angles(CFG["pose_look"], 30)
                decision["outcome"] = outcome
                pt.publish(client, decision)
                pt.record_visit(decision)
                arm.angles(CFG["pose_stow"], 40)

        elif task in ("harvest", "prune"):
            pid = target
            park_over(gantry, arm, pid)
            geo, _ = wrist.look(pid)
            want = "tip" if task == "prune" else "leaf"
            cand = next((c for c in geo.candidates if c.kind == want), None)
            if cand is None:
                raise RuntimeError(f"no {want} candidate on {pid}: {geo.reason or 'nothing suitable'}")
            decision = {"plant_id": pid, "identify": None, "health": None,
                        "action": {"action": "pinch_tip" if task == "prune" else "harvest_leaf",
                                   "candidate": cand.label, "reason": f"manual {task} from HA"},
                        "verdict": {"execute": True, "propose": False, "blocked": None},
                        "target": {"label": cand.label, "kind": cand.kind, "point_m": cand.point_m,
                                   "normal": cand.normal, "approach_mm": CFG.get("approach_mm", 40)}}
            decision["outcome"] = act(arm, decision, wrist, pid)
            pt.record_visit(decision)
            arm.angles(CFG["pose_stow"], 40)

        gantry.move(x=CFG["park_x"], z=CFG["park_z"])
    except Exception as exc:                            # any fault: stop, stow, report
        client.publish("greenhouse/robot/error", str(exc))
        try:
            arm.angles(CFG["pose_stow"], 30)
        except Exception:
            pass
    finally:
        with lock:
            state["busy"] = False
        publish_busy(client, False)


def main():
    gantry = Gantry(CFG["fluidnc_port"])
    arm = Arm(CFG["arm_ip"])
    wrist = Wrist()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="greenhouse-robot")
    client.username_pw_set(CFG["mqtt"]["user"], CFG["mqtt"]["password"])

    def on_connect(c, *_):
        c.publish(f"{PREFIX}/binary_sensor/gh_robot/busy/config", json.dumps({
            "name": "Robot busy", "unique_id": "gh_robot_busy", "object_id": "greenhouse_robot_busy",
            "state_topic": "greenhouse/robot/busy", "device_class": "running", "device": DEVICE}), retain=True)
        c.subscribe("greenhouse/robot/cmd")
        # Mirror interlock states from HA (HA mqtt_statestream, base_topic: hass_state, publish_attributes: false)
        c.subscribe("hass_state/binary_sensor/greenhouse_utility_doors/state")
        c.subscribe("hass_state/binary_sensor/greenhouse_utility_watering_active/state")
        c.subscribe("hass_state/sensor/greenhouse_tier_+/state")        # per-plant moisture
        publish_busy(c, False)

    def on_message(c, _u, msg):
        if msg.topic.endswith("doors/state"):
            state["doors_open"] = msg.payload.decode() == "on"
            return
        if msg.topic.endswith("watering_active/state"):
            state["watering"] = msg.payload.decode() == "on"
            return
        if msg.topic.endswith("_moisture/state"):
            # hass_state/sensor/greenhouse_tier_a_a01_moisture/state -> A01
            part = msg.topic.split("/")[2].replace("_moisture", "").split("_")[-1].upper()
            try:
                state["moisture"][part] = float(msg.payload.decode())
            except ValueError:
                pass
            return
        if not msg.topic.endswith("robot/cmd"):
            return
        cmd = json.loads(msg.payload)
        with lock:
            if state["busy"] or state["doors_open"] or state["watering"]:
                c.publish("greenhouse/robot/error", f"refused {cmd}: interlock")
                return
            state["busy"] = True
        threading.Thread(target=run_task, args=(c, gantry, arm, wrist, cmd["task"], cmd.get("target")),
                         daemon=True).start()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(CFG["mqtt"]["host"], 1883)
    client.loop_forever()


if __name__ == "__main__":
    main()
