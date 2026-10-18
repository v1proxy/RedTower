#!/usr/bin/env python3
"""Hand-eye calibration: where the D405 sits relative to the arm's flange.

Everything the tender agent decides is expressed in camera coordinates. To move the arm
there you need one fixed 4x4 transform, flange -> camera. This script measures it.

Method: a chessboard target sits still somewhere in the cabinet. The arm looks at it from
N different poses. At each pose we know two things: where the flange is in the base frame
(from the arm's own forward kinematics) and where the target is in the camera frame (from
solvePnP). Tsai's method then solves for the one transform that makes all of those agree.

What you need:
  - a chessboard printed and glued flat to a rigid card. Default is 7x5 inner corners
    (8x6 squares) at 10 mm, which is about 80 x 60 mm and fits the D405's close field.
    Measure a printed square with calipers and pass the real number; a 3 % scale error in
    the print becomes a 3 % error in every reach.
  - the target clamped or taped where it cannot shift. If it moves between poses the
    result is garbage, and the residual below is how you find out.
  - 10 to 15 poses with genuinely different wrist orientations, not just translations.
    Rotation variety is what makes the solve well conditioned.

Usage:
    python handeye_calibrate.py --manual            # jog by hand, press Enter at each pose
    python handeye_calibrate.py --poses poses.json  # walk a saved list of joint angles
    python handeye_calibrate.py --verify            # re-check an existing calibration

It writes cam_to_flange (a 4x4 row-major list) into /opt/greenhouse/robot.json and keeps
the raw captures in handeye/ so a bad run can be re-solved without re-posing the arm.

    pip install opencv-python numpy pyrealsense2 pymycobot
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs

CFG_PATH = Path("/opt/greenhouse/robot.json")
CFG = json.loads(CFG_PATH.read_text()) if CFG_PATH.exists() else {}
HCFG = CFG.get("handeye", {})
OUT = Path(HCFG.get("dir", "/opt/greenhouse/handeye"))

COLS = int(HCFG.get("board_cols", 7))          # inner corners across
ROWS = int(HCFG.get("board_rows", 5))          # inner corners down
SQUARE_MM = float(HCFG.get("square_mm", 10.0))
MIN_POSES = 8
W, H, FPS = 848, 480, 30

OBJP = np.zeros((COLS * ROWS, 3), np.float32)
OBJP[:, :2] = np.mgrid[0:COLS, 0:ROWS].T.reshape(-1, 2) * (SQUARE_MM / 1000.0)


# ---------------------------------------------------------------- pose conversions

def rpy_to_R(rx, ry, rz, order="xyz"):
    """Euler degrees to a rotation matrix.

    The myCobot controller reports rx, ry, rz in degrees but the composition order is not
    documented identically across firmware versions, so we solve with both and keep the
    one whose residual is smaller. That is cheaper than guessing.
    """
    a, b, c = np.radians([rx, ry, rz])
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx if order == "xyz" else Rx @ Ry @ Rz


def coords_to_T(coords, order="xyz"):
    """myCobot [x, y, z, rx, ry, rz] (mm, degrees) to a 4x4 in metres."""
    x, y, z, rx, ry, rz = coords
    T = np.eye(4)
    T[:3, :3] = rpy_to_R(rx, ry, rz, order)
    T[:3, 3] = np.array([x, y, z]) / 1000.0
    return T


def Rt_to_T(R, t):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = np.asarray(t).reshape(3)
    return T


# ---------------------------------------------------------------- capture

class Camera:
    def __init__(self):
        self.pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.color, W, H, rs.format.bgr8, FPS)
        cfg.enable_stream(rs.stream.depth, W, H, rs.format.z16, FPS)
        profile = self.pipe.start(cfg)
        intr = profile.get_stream(rs.stream.color).as_video_stream_profile().intrinsics
        self.K = np.array([[intr.fx, 0, intr.ppx], [0, intr.fy, intr.ppy], [0, 0, 1]], float)
        self.dist = np.zeros(5)                 # RealSense colour is already rectified
        for _ in range(15):                     # let auto-exposure settle
            self.pipe.wait_for_frames()

    def frame(self):
        for _ in range(5):                      # a few frames, keep the last: less motion blur
            frames = self.pipe.wait_for_frames()
        return np.asanyarray(frames.get_color_frame().get_data())

    def close(self):
        self.pipe.stop()


def find_board(bgr):
    """Target pose in the camera frame, or None if the board is not clearly visible."""
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ok, corners = cv2.findChessboardCornersSB(grey, (COLS, ROWS), cv2.CALIB_CB_EXHAUSTIVE)
    if not ok:
        ok, corners = cv2.findChessboardCorners(
            grey, (COLS, ROWS), cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)
        if ok:
            corners = cv2.cornerSubPix(
                grey, corners, (11, 11), (-1, -1),
                (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
    return (corners if ok else None)


def solve_target(corners, K, dist):
    ok, rvec, tvec = cv2.solvePnP(OBJP, corners, K, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None
    R, _ = cv2.Rodrigues(rvec)
    return Rt_to_T(R, tvec)


# ---------------------------------------------------------------- solve

def solve_handeye(samples, order):
    """samples: list of (T_base_flange, T_cam_target). Returns (T_flange_cam, residual_mm)."""
    R_g2b = [s[0][:3, :3] for s in samples]
    t_g2b = [s[0][:3, 3] for s in samples]
    R_t2c = [s[1][:3, :3] for s in samples]
    t_t2c = [s[1][:3, 3] for s in samples]
    R_c2g, t_c2g = cv2.calibrateHandEye(R_g2b, t_g2b, R_t2c, t_t2c,
                                        method=cv2.CALIB_HAND_EYE_TSAI)
    T_flange_cam = Rt_to_T(R_c2g, t_c2g)

    # The target never moved, so its base-frame position must come out the same every pose.
    pts = []
    for T_bf, T_ct in samples:
        p = T_bf @ T_flange_cam @ np.append(T_ct[:3, 3], 1.0)
        pts.append(p[:3])
    pts = np.array(pts)
    residual_mm = float(np.linalg.norm(pts - pts.mean(axis=0), axis=1).max() * 1000)
    return T_flange_cam, residual_mm, pts.mean(axis=0) * 1000


def report(T, residual_mm, order, target_mm):
    t = T[:3, 3] * 1000
    print(f"\nEuler order tried      : {order}")
    print(f"Camera offset from flange (mm): x {t[0]:+.1f}  y {t[1]:+.1f}  z {t[2]:+.1f}")
    print(f"Target in base frame (mm)     : {target_mm[0]:+.1f} {target_mm[1]:+.1f} {target_mm[2]:+.1f}")
    print(f"Worst-pose spread             : {residual_mm:.1f} mm")
    if residual_mm < 3:
        print("Good. That is tighter than the arm's own repeatability.")
    elif residual_mm < 8:
        print("Usable for leaf work. Tighten it before trusting a cut: more rotation variety,")
        print("and check the board is truly rigid and the square size is the measured one.")
    else:
        print("Too loose to reach with. Usual causes, in order: the board moved, the square size")
        print("is wrong, or the poses are mostly translations with little rotation change.")


# ---------------------------------------------------------------- collection modes

def connect_arm():
    from pymycobot import MyCobot280Socket
    arm = MyCobot280Socket(CFG["arm_ip"], 9000)
    time.sleep(1)
    return arm


def collect_manual(cam, arm):
    print("Jog the arm by hand or from the myStudio pendant so the board fills a good part of the")
    print("frame from a different angle each time. Press Enter to capture, 'q' then Enter to solve.\n")
    samples, shots = [], []
    while True:
        if input(f"[{len(samples)} captured] Enter to capture, q to finish: ").strip().lower() == "q":
            break
        bgr = cam.frame()
        corners = find_board(bgr)
        if corners is None:
            print("  board not found: move so all inner corners are visible and lit, no glare.")
            continue
        T_ct = solve_target(corners, cam.K, cam.dist)
        if T_ct is None:
            print("  solvePnP failed on that view, try again from a slightly different angle.")
            continue
        coords = arm.get_coords()
        if not coords or len(coords) != 6:
            print("  the arm did not return coordinates; is it powered and out of alarm?")
            continue
        dist_mm = np.linalg.norm(T_ct[:3, 3]) * 1000
        print(f"  captured: board at {dist_mm:.0f} mm, arm at {['%.0f' % c for c in coords[:3]]}")
        samples.append((coords, T_ct))
        shots.append(bgr)
    return samples, shots


def collect_poses(cam, arm, pose_file):
    poses = json.loads(Path(pose_file).read_text())
    samples, shots = [], []
    for i, angles in enumerate(poses, 1):
        print(f"Pose {i}/{len(poses)}: {angles}")
        arm.send_angles(angles, 30)
        time.sleep(4)
        bgr = cam.frame()
        corners = find_board(bgr)
        if corners is None:
            print("  board not visible from this pose, skipping")
            continue
        T_ct = solve_target(corners, cam.K, cam.dist)
        coords = arm.get_coords()
        if T_ct is None or not coords or len(coords) != 6:
            print("  skipping: no pose or no solve")
            continue
        samples.append((coords, T_ct))
        shots.append(bgr)
    return samples, shots


def save(samples, shots, T, residual_mm, order):
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (bgr, (coords, T_ct)) in enumerate(zip(shots, samples)):
        cv2.imwrite(str(OUT / f"pose{i:02d}.png"), bgr)
    (OUT / "samples.json").write_text(json.dumps(
        [{"coords": list(map(float, c)), "T_cam_target": T_ct.tolist()} for c, T_ct in samples], indent=1))
    (OUT / "result.json").write_text(json.dumps(
        {"cam_to_flange": T.tolist(), "residual_mm": residual_mm, "euler_order": order,
         "board": {"cols": COLS, "rows": ROWS, "square_mm": SQUARE_MM},
         "poses": len(samples)}, indent=1))

    cfg = json.loads(CFG_PATH.read_text()) if CFG_PATH.exists() else {}
    cfg["cam_to_flange"] = T.tolist()
    cfg.setdefault("handeye", {}).update({"residual_mm": round(residual_mm, 2),
                                          "euler_order": order, "poses": len(samples)})
    CFG_PATH.write_text(json.dumps(cfg, indent=1))
    print(f"\nWrote cam_to_flange into {CFG_PATH} and the raw captures into {OUT}")


def verify(cam, arm):
    """Point the camera at the board once and compare the base-frame answer to the stored one."""
    T = np.array(CFG.get("cam_to_flange"))
    if T is None or T.shape != (4, 4):
        print("No cam_to_flange in the config yet. Run a calibration first.")
        return 1
    order = CFG.get("handeye", {}).get("euler_order", "xyz")
    bgr = cam.frame()
    corners = find_board(bgr)
    if corners is None:
        print("Board not visible.")
        return 1
    T_ct = solve_target(corners, cam.K, cam.dist)
    T_bf = coords_to_T(arm.get_coords(), order)
    p = (T_bf @ T @ np.append(T_ct[:3, 3], 1.0))[:3] * 1000
    print(f"Board origin in base frame: {p[0]:+.1f} {p[1]:+.1f} {p[2]:+.1f} mm")
    print("Move the arm, run this again: the three numbers should barely change. Drift of more")
    print("than a few millimetres means the camera has shifted on the flange, so recalibrate.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", action="store_true", help="jog by hand, Enter at each pose")
    ap.add_argument("--poses", help="JSON file: list of 6-joint angle lists to walk")
    ap.add_argument("--verify", action="store_true", help="check the stored calibration")
    ap.add_argument("--resolve", action="store_true", help="re-solve from handeye/samples.json")
    args = ap.parse_args()

    if args.resolve:
        raw = json.loads((OUT / "samples.json").read_text())
        samples_raw = [(r["coords"], np.array(r["T_cam_target"])) for r in raw]
        shots = []
    else:
        cam = Camera()
        arm = connect_arm()
        if args.verify:
            rc = verify(cam, arm)
            cam.close()
            return rc
        samples_raw, shots = (collect_manual(cam, arm) if args.manual
                              else collect_poses(cam, arm, args.poses))
        cam.close()

    if len(samples_raw) < MIN_POSES:
        print(f"\nOnly {len(samples_raw)} usable poses. Tsai's method needs variety; {MIN_POSES} is the "
              f"floor and 12 is comfortable. Nothing written.")
        return 1

    best = None
    for order in ("xyz", "zyx"):
        samples = [(coords_to_T(c, order), T_ct) for c, T_ct in samples_raw]
        T, res, target = solve_handeye(samples, order)
        report(T, res, order, target)
        if best is None or res < best[1]:
            best = (T, res, order)

    T, res, order = best
    print(f"\nKeeping the {order} solve at {res:.1f} mm.")
    save(samples_raw, shots, T, res, order)
    return 0 if res < 8 else 2


if __name__ == "__main__":
    sys.exit(main())
