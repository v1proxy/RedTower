"""Hand-eye calibration against ground truth: chessboard images rendered from known camera
poses, flange poses derived from a known flange-to-camera transform."""
import math
import unittest

import cv2
import numpy as np

import rig  # noqa: F401  (puts the jetson folder on the path)
from gh import handeye as H

INTR = {"fx": 430.0, "fy": 430.0, "cx": 320.0, "cy": 240.0}
K = np.array([[430.0, 0, 320.0], [0, 430.0, 240.0], [0, 0, 1]])
CORNERS, SQ = (6, 4), 10.0                  # a 7 by 5 square board, 10 mm squares
# The truth to recover: camera 60 mm ahead of the flange, 25 mm off axis, tilted 15 degrees.
X_TRUE = H.transform(H.euler_to_R(15, -5, 90), [25.0, -10.0, 60.0])
BOARD_IN_BASE = H.transform(H.euler_to_R(180, 0, 0), [260.0, 40.0, 120.0])


def render(T_cam_board, size=(640, 480), k=8):
    """The board as the camera sees it: a texture warped by K [r1 r2 t]."""
    cols, rows = CORNERS
    m = SQ                                                     # white margin
    w, h = int((cols + 1) * SQ + 2 * m) * k, int((rows + 1) * SQ + 2 * m) * k
    tex = np.full((h, w), 255, np.uint8)
    for a in range(cols + 1):
        for b in range(rows + 1):
            if (a + b) % 2 == 0:
                x0, y0 = int((m + a * SQ) * k), int((m + b * SQ) * k)
                tex[y0:y0 + int(SQ * k), x0:x0 + int(SQ * k)] = 20
    S = np.array([[1 / k, 0, -m - SQ], [0, 1 / k, -m - SQ], [0, 0, 1]])      # texture px -> board mm
    Rt = np.column_stack([T_cam_board[:3, 0], T_cam_board[:3, 1], T_cam_board[:3, 3]])
    img = cv2.warpPerspective(tex, K @ Rt @ S, size, flags=cv2.INTER_AREA, borderValue=120)
    return cv2.GaussianBlur(img, (3, 3), 0)


def camera_looking_at_board(rng, tilt_deg=25, roll_deg=30):
    """A camera pose in the base frame, 180 to 240 mm from the board centre, facing its front."""
    centre = (BOARD_IN_BASE @ np.array([2.5 * SQ, 1.5 * SQ, 0, 1]))[:3]
    n = BOARD_IN_BASE[:3, 2]
    tilt, az = math.radians(rng.uniform(0, tilt_deg)), rng.uniform(0, 2 * math.pi)
    u = BOARD_IN_BASE[:3, 0] * math.cos(az) + BOARD_IN_BASE[:3, 1] * math.sin(az)
    look = n * math.cos(tilt) + u * math.sin(tilt)                # camera z, into the board
    pos = centre - look * rng.uniform(180, 240)
    x0 = BOARD_IN_BASE[:3, 0]
    x = x0 - look * (x0 @ look)
    x /= np.linalg.norm(x)
    roll = math.radians(rng.uniform(-roll_deg, roll_deg))
    x = x * math.cos(roll) + np.cross(look, x) * math.sin(roll)
    return H.transform(np.column_stack([x, np.cross(look, x), look]), pos)


def poses(n=12, seed=1, order="xyz", **kw):
    """coords as the arm would report them, and the true T_cam_board for each pose."""
    rng = np.random.default_rng(seed)
    coords, boards = [], []
    for _ in range(n):
        C = camera_looking_at_board(rng, **kw)
        F = C @ np.linalg.inv(X_TRUE)
        coords.append(list(F[:3, 3]) + H.R_to_euler(F[:3, :3], order))
        boards.append(np.linalg.inv(C) @ BOARD_IN_BASE)
    return coords, boards


def angle_deg(A, B):
    R = A[:3, :3].T @ B[:3, :3]
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


class TestHandEye(unittest.TestCase):
    def test_euler_round_trip_both_orders(self):
        for order in H.CONVENTIONS:
            R = H.euler_to_R(20, -35, 120, order)
            self.assertTrue(np.allclose(H.euler_to_R(*H.R_to_euler(R, order), order), R))

    def test_exact_transforms_recover_the_truth(self):
        coords, boards = poses()
        r = H.solve_any(coords, boards)
        self.assertEqual(r["convention"], "xyz")
        self.assertLess(np.linalg.norm(r["T_flange_cam"][:3, 3] - X_TRUE[:3, 3]), 0.01)
        self.assertLess(r["spread_mm"], 0.01)
        self.assertGreater(r["other_spread_mm"], 10)              # the wrong order is far off
        self.assertTrue(H.verdict(r)[0])

    def test_the_arms_euler_order_is_found_either_way(self):
        coords, boards = poses(order="zyx")
        self.assertEqual(H.solve_any(coords, boards)["convention"], "zyx")

    def test_rendered_board_gives_its_true_pose(self):
        rng = np.random.default_rng(7)
        for _ in range(6):
            C = camera_looking_at_board(rng, roll_deg=40)
            truth = np.linalg.inv(C) @ BOARD_IN_BASE
            found = H.find_board(render(truth), INTR, CORNERS, SQ)
            self.assertIsNotNone(found)
            T, rms = found
            self.assertLess(rms, 0.5)
            self.assertLess(np.linalg.norm(T[:3, 3] - truth[:3, 3]), 1.0)
            self.assertLess(angle_deg(T, truth), 1.0)              # never the 180 degree twin

    def test_whole_calibration_from_rendered_images(self):
        coords, truths = poses(n=12, seed=3, tilt_deg=40, roll_deg=45)
        boards = [H.find_board(render(T), INTR, CORNERS, SQ)[0] for T in truths]
        r = H.solve_any(coords, boards)
        ok, text = H.verdict(r)
        self.assertTrue(ok, text)
        self.assertLess(r["spread_mm"], H.GOOD_MM)
        leaf = np.array([0, 0, 200.0, 1])                         # what matters: a leaf 200 mm ahead
        self.assertLess(np.linalg.norm((r["T_flange_cam"] @ leaf - X_TRUE @ leaf)[:3]), 2.0)
        self.assertLess(r["rotation_spread_deg"], 2.0)

    def test_board_moved_during_calibration_is_caught(self):
        coords, boards = poses()
        boards[4] = H.transform(np.eye(3), [20, 0, 0]) @ boards[4]
        r = H.solve_any(coords, boards)
        ok, text = H.verdict(r)
        self.assertFalse(ok)
        self.assertIn("worst at pose 5", text)

    def test_translation_only_poses_are_refused(self):
        coords, boards = poses(tilt_deg=1, roll_deg=1)
        ok, text = H.verdict(H.solve_any(coords, boards))
        self.assertFalse(ok)
        self.assertIn("degrees", text)

    def test_too_few_poses(self):
        coords, boards = poses(n=5)
        self.assertFalse(H.verdict(H.solve_any(coords, boards))[0])

    def test_save_and_load(self):
        import tempfile
        from pathlib import Path
        coords, boards = poses()
        r = H.solve_any(coords, boards)
        with tempfile.TemporaryDirectory() as d:
            H.save(r, Path(d) / "handeye.json")
            back = H.load(Path(d) / "handeye.json")
        self.assertTrue(np.allclose(back["T_flange_cam"], r["T_flange_cam"], atol=1e-5))
        self.assertEqual(back["convention"], "xyz")


if __name__ == "__main__":
    unittest.main()
